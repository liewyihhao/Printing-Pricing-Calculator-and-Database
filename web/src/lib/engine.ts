// Printoka configurator runtime — a faithful TS port of the shipped engine's UI logic
// (crawler/ui/_standalone_template.html: condMet / fieldShown / allowedOptions / populateFrom).
// Keeps the Next.js store's valid-combination behaviour byte-identical to the standalone calculator
// and the combo-validity-checker, so what a customer can configure here == what Excard offers.
import type { ProductDetail, ProductField } from "./pricing-api";

export type Values = Record<string, string | number>;
type Cond = { field: string; values?: string[]; notValues?: string[] };
type ShowWhen = Cond | { all: Cond[] };
type RuleSet = { primary: string; fields: string[]; rules: Record<string, Record<string, string[]>> };

function ruleSets(product: ProductDetail): RuleSet[] {
  const v = product.validity as unknown as RuleSet | RuleSet[] | undefined;
  if (!v) return [];
  return Array.isArray(v) ? v : [v];
}

// showWhen: {field, values?|notValues?} OR {all:[cond,...]} (every cond must hold).
function condMet(c: Cond, values: Values): boolean {
  const raw = values[c.field];
  const cur = raw != null && raw !== "" ? String(raw) : "";
  if (c.values) return c.values.indexOf(cur) >= 0;
  if (c.notValues) return c.notValues.indexOf(cur) < 0;
  return true;
}

export function fieldShown(field: ProductField, values: Values): boolean {
  const sw = (field as unknown as { showWhen?: ShowWhen }).showWhen;
  if (!sw) return true;
  return "all" in sw ? sw.all.every((c) => condMet(c, values)) : condMet(sw, values);
}

// The values currently allowed for a field: base options intersected across every validity rule-set
// that constrains it (array-validity → intersection). Empty ⇒ fall back to base.
export function allowedOptions(field: ProductField, product: ProductDetail, values: Values): string[] {
  const base = field.options ?? (field.images ? Object.keys(field.images) : []);
  const list = ruleSets(product);
  if (!list.length) return base;
  let allow = base;
  for (const rs of list) {
    if (!(rs.fields || []).includes(field.key)) continue;
    const pv = values[rs.primary];
    const rule = pv != null && pv !== "" ? rs.rules[String(pv)] : null;
    if (rule && rule[field.key]) allow = allow.filter((o) => rule[field.key].includes(o));
  }
  return allow.length ? allow : base;
}

export function validQuantities(product: ProductDetail): number[] {
  const q = product.quantity as unknown as { options?: number[] } | undefined;
  return q?.options ?? [];
}

export function moq(product: ProductDetail): number {
  const q = product.quantity as unknown as { moq?: number; min?: number } | undefined;
  return q?.moq ?? q?.min ?? 1;
}

export function defaultQuantity(product: ProductDetail): number {
  const opts = validQuantities(product);
  if (opts.length) return opts.includes(100) ? 100 : opts[0];
  return moq(product);
}

// Auto-fill defaults for every currently-applicable field (mirrors template.populateFrom): first
// allowed option, preferring "Normal". Recomputes as it goes so cascades resolve in one pass. Returns
// a NEW values object; only fills missing/now-invalid values, never overrides a valid user choice.
export function resolveDefaults(product: ProductDetail, values: Values): Values {
  const next: Values = { ...values };
  for (const f of product.fields) {
    if (!fieldShown(f, next)) {
      continue; // hidden — leave as-is (stale hidden values don't affect validity/quote)
    }
    if (f.type === "number") {
      const d = (f as unknown as { default?: number }).default;
      if (next[f.key] == null && d != null) next[f.key] = d;
      continue;
    }
    const opts = allowedOptions(f, product, next);
    if (!opts.length) continue;
    const cur = next[f.key];
    if (cur != null && cur !== "" && opts.includes(String(cur))) continue; // keep valid choice
    if ((f as unknown as { optional?: boolean }).optional && (cur == null || cur === "")) continue;
    next[f.key] = opts.includes("Normal") ? "Normal" : opts[0];
  }
  return next;
}

// A config is quotable when every applicable, non-optional, non-number field has a valid value —
// matching template.quote()'s completeness gate.
export function isComplete(product: ProductDetail, values: Values): boolean {
  return product.fields.every((f) => {
    if (f.type === "number") return true;
    if ((f as unknown as { optional?: boolean }).optional) return true;
    if (!fieldShown(f, values)) return true;
    const v = values[f.key];
    return v != null && v !== "";
  });
}
