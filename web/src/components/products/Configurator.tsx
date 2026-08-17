"use client";

import { useMemo, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import type { ProductDetail, ProductField } from "@/lib/pricing-api";
import { fieldShown, allowedOptions as engineAllowed } from "@/lib/engine";
import { QuantityControl } from "@/components/products/QuantityControl";

interface ConfiguratorProps {
  product: ProductDetail;
  values: Record<string, string | number>;
  onChange: (key: string, value: string | number) => void;
  quantity: number;
  onQuantityChange: (q: number) => void;
}

// Group the fields under Excard's questionnaire sections (General / Optional Finishing / Add On …)
// in Excard's order, so the configurator mirrors the supplier's order form exactly.
function groupSections(product: ProductDetail) {
  const order = product.sectionOrder?.length ? [...product.sectionOrder] : [];
  const bySection = new Map<string, ProductField[]>();
  for (const f of product.fields) {
    const s = f.section || "General";
    if (!bySection.has(s)) bySection.set(s, []);
    bySection.get(s)!.push(f);
    if (!order.includes(s)) order.push(s); // append any extra sections in first-appearance order
  }
  return order.filter((s) => bySection.has(s)).map((s) => ({ name: s, fields: bySection.get(s)! }));
}

export function Configurator({ product, values, onChange, quantity, onQuantityChange }: ConfiguratorProps) {
  const sections = useMemo(() => groupSections(product), [product]);

  // Quantity is NOT universally in General — Excard puts it in a spec section only for some products
  // (product.quantitySection); most keep it in the summary. Inline it into the matching section when
  // Excard groups it there; otherwise render it as a standalone block after the sections.
  const qtySection = useMemo(() => {
    if (!product.quantitySection) return null;
    const nrm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, "");
    const target = nrm(product.quantitySection);
    return sections.find((s) => nrm(s.name) === target)?.name ?? null;
  }, [sections, product.quantitySection]);

  return (
    <div className="flex flex-col gap-5">
      {sections.map(({ name, fields }) => {
        // Hide a section entirely when none of its fields currently apply (showWhen).
        const anyVisible = fields.some((f) => fieldShown(f, values));
        const showsQty = name === qtySection;
        if (!anyVisible && !showsQty) return null;
        return (
          <div key={name} className="rounded-lg border border-border overflow-hidden bg-white">
            {/* Excard-style teal section header */}
            <div className="bg-accent-teal text-white text-sm font-semibold px-4 py-2.5">
              {name}
            </div>
            <div className="flex flex-col gap-5 p-4">
              {(() => {
                const qtyEl = (
                  <QuantityControl key="__qty" product={product} quantity={quantity} onChange={onQuantityChange} />
                );
                // Excard orders "… Quantity, Package" — insert Quantity right before the Package field.
                const hasPackage = fields.some((f) => /package/i.test(f.key));
                const out: ReactNode[] = [];
                for (const field of fields) {
                  if (showsQty && /package/i.test(field.key)) out.push(qtyEl);
                  out.push(
                    <FieldRenderer
                      key={field.key}
                      field={field}
                      product={product}
                      values={values}
                      onChange={onChange}
                    />
                  );
                }
                if (showsQty && !hasPackage) out.push(qtyEl);
                return out;
              })()}
            </div>
          </div>
        );
      })}

      {/* When Excard doesn't group Quantity into a spec section, render it on its own (like the
          supplier's summary), NOT inside General. */}
      {!qtySection && (
        <div className="rounded-lg border border-border overflow-hidden bg-white">
          <div className="bg-accent-teal text-white text-sm font-semibold px-4 py-2.5">Quantity</div>
          <div className="p-4">
            <QuantityControl product={product} quantity={quantity} onChange={onQuantityChange} hideLabel />
          </div>
        </div>
      )}
    </div>
  );
}

function FieldRenderer({
  field,
  product,
  values,
  onChange,
}: {
  field: ProductField;
  product: ProductDetail;
  values: Record<string, string | number>;
  onChange: (key: string, value: string | number) => void;
}) {
  // Allowed options via the shared engine (array-validity intersection), and showWhen visibility.
  const allowedOptions = useMemo(
    () => engineAllowed(field, product, values),
    [field, product, values]
  );

  // Conditional field not currently applicable (e.g. lamination only for coated paper) → hide it.
  if (!fieldShown(field, values)) return null;

  const currentValue = values[field.key] ?? "";

  if (field.type === "number") {
    return (
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-medium text-ink-secondary">
          {field.label}
          {field.required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
        <input
          type="number"
          value={currentValue as number}
          min={field.min}
          max={field.max}
          onChange={(e) => onChange(field.key, Number(e.target.value))}
          className="h-10 rounded-lg border border-border bg-white px-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-brand-500 w-full max-w-xs"
        />
        {field.min != null && field.max != null && (
          <p className="text-xs text-ink-muted">
            {field.min} – {field.max} mm
          </p>
        )}
      </div>
    );
  }

  // Image picker
  if (field.images && Object.keys(field.images).length > 0) {
    return (
      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-ink-secondary">
          {field.label}
          {field.required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
          {(allowedOptions ?? []).map((opt) => {
            const imgSrc = field.images![opt];
            const selected = currentValue === opt;
            return (
              <button
                key={opt}
                type="button"
                onClick={() => onChange(field.key, opt)}
                className={cn(
                  "flex flex-col items-center gap-1.5 rounded-lg border-2 p-1.5 transition-all duration-150 text-center",
                  selected
                    ? "border-brand-500 bg-brand-50"
                    : "border-border hover:border-brand-300"
                )}
              >
                {imgSrc ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={imgSrc}
                    alt={opt}
                    className="w-full aspect-square object-cover rounded-md"
                  />
                ) : (
                  <div className="w-full aspect-square bg-surface-subtle rounded-md" />
                )}
                <span className="text-[10px] font-medium text-ink-secondary leading-tight">
                  {opt}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  // Plain select
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-ink-secondary">
        {field.label}
        {field.required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      <div className="flex flex-wrap gap-2">
        {(allowedOptions ?? []).map((opt) => {
          const selected = currentValue === opt;
          return (
            <button
              key={opt}
              type="button"
              onClick={() => onChange(field.key, opt)}
              className={cn(
                "px-3 py-1.5 rounded-lg border text-sm font-medium transition-all duration-150",
                selected
                  ? "border-brand-500 bg-brand-50 text-brand-700"
                  : "border-border text-ink-secondary hover:border-brand-300 hover:text-ink"
              )}
            >
              {opt}
            </button>
          );
        })}
      </div>
    </div>
  );
}
