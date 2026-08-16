/* our_side.cjs — the checker's "OUR SIDE" oracle.
 *
 * Given a product id and a partial selection V, returns — for EVERY field — the options our
 * configurator would currently offer, exactly as the standalone UI computes them. It reuses the
 * shipped engine's localOptions() (cascade products) and PORTS the template's allowedOptions /
 * fieldShown / condMet so "what we offer" is byte-identical to what the customer sees.
 *
 * The combo_validity_checker.py orchestrator talks to this as a persistent line server:
 *   stdin : one JSON per line -> {id:<int>, V:{fieldKey:value,...}}
 *   stdout: one JSON per line -> {id, fields:[{key,label,section,visible,kind,ready,options:[...]}]}
 * A line {"cmd":"quit"} exits. Run standalone with `node app/our_side.cjs --selftest <id>`.
 */
const path = require("path");
const { DATA, localOptions } = require(path.join(__dirname, "..", "output", "calculator_engine.cjs"));

const PROD = Object.fromEntries(DATA.products.map(p => [p.id, p]));

// Set of field keys constrained by ANY validity rule-set (single object or array of them).
function validityFields(P) {
  const V = P.validity; if (!V) return new Set();
  const list = Array.isArray(V) ? V : [V];
  const s = new Set();
  for (const VV of list) for (const fk of (VV.fields || [])) s.add(fk);
  return s;
}

// Faithful port of template allowedOptions(f): intersect the field's base options across every
// rule-set that names it, keyed on that rule-set's current primary value. Empty -> fall back to base.
function allowedFilter(P, f, V) {
  const base = f.options || (f.images ? Object.keys(f.images) : (f.swatch ? (f.options || []) : []));
  const Vd = P.validity; if (!Vd) return base;
  const list = Array.isArray(Vd) ? Vd : [Vd];
  let allow = base;
  for (const VV of list) {
    if (!(VV.fields || []).includes(f.key)) continue;
    const pv = V[VV.primary], rule = pv ? VV.rules[pv] : null;
    if (rule && rule[f.key]) allow = allow.filter(o => rule[f.key].includes(o));
  }
  return allow.length ? allow : base;
}

// Faithful port of template condMet / fieldShown.
function condMet(c, V) {
  const cur = (V[c.field] != null && V[c.field] !== "") ? V[c.field] : "";
  return c.values ? c.values.indexOf(cur) >= 0 : (c.notValues ? c.notValues.indexOf(cur) < 0 : true);
}
function fieldShown(f, V) {
  const sw = f.showWhen; if (!sw) return true;
  return sw.all ? sw.all.every(c => condMet(c, V)) : condMet(sw, V);
}

// Offered options for one field given V, mirroring populateFrom() + enforceValidity().
function offered(P, f, V, constrained) {
  if (f.type === "number") return { kind: "number", ready: true, options: [] };
  let disp, kind;
  if (f.images) { disp = f.options || Object.keys(f.images); kind = "image"; }
  else if (f.swatch) { disp = f.options || []; kind = "swatch"; }
  else if (f.options) { disp = f.options; kind = "select"; }
  else { // cascade field (optsrc): options come from localOptions once its depends are all set
    kind = "select";
    const deps = f.depends || [];
    const ready = deps.every(d => V[d] != null && V[d] !== "");
    if (!ready) return { kind, ready: false, options: [] };
    disp = localOptions(P, f.key, V) || [];
  }
  if (constrained.has(f.key)) disp = allowedFilter(P, f, V); // enforceValidity replaces innerHTML
  return { kind, ready: true, options: disp };
}

function resolve(id, V) {
  const P = PROD[id];
  if (!P) return { id, error: "unknown id" };
  V = V || {};
  const constrained = validityFields(P);
  const fields = (P.fields || []).map(f => {
    const o = offered(P, f, V, constrained);
    return {
      key: f.key, label: f.label || f.key, section: f.section || "",
      visible: fieldShown(f, V), optional: !!f.optional, addon: !!f.addon,
      depends: f.depends || [], showWhen: f.showWhen || null,
      kind: o.kind, ready: o.ready, options: o.options,
    };
  });
  return { id, name: P.name, order: fields.map(f => f.key), fields };
}

if (process.argv[2] === "--selftest") {
  const id = parseInt(process.argv[3] || "1", 10);
  console.log(JSON.stringify(resolve(id, {}), null, 1));
  process.exit(0);
}

// Persistent line server.
let buf = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => {
  buf += chunk;
  let nl;
  while ((nl = buf.indexOf("\n")) >= 0) {
    const line = buf.slice(0, nl); buf = buf.slice(nl + 1);
    if (!line.trim()) continue;
    let req;
    try { req = JSON.parse(line); } catch (e) { process.stdout.write(JSON.stringify({ error: "bad json" }) + "\n"); continue; }
    if (req.cmd === "quit") { process.exit(0); }
    process.stdout.write(JSON.stringify(resolve(req.id, req.V)) + "\n");
  }
});
process.stdin.on("end", () => process.exit(0));
