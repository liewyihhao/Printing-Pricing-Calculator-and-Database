// Verify pricelist JS engine matches Python pricelist_engine.cash_price()
import { readFileSync } from "fs";

const load = (f) => JSON.parse(readFileSync(`output/${f}`, "utf8"));

function interpLogPts(pts, x) {
  if (!pts || pts.length === 0) return 0;
  const xs = pts.map((p) => p[0]);
  const ys = pts.map((p) => Math.log(p[1]));
  if (x <= xs[0]) return Math.exp(ys[0]);
  if (x >= xs[xs.length - 1]) return Math.exp(ys[ys.length - 1]);
  for (let i = 1; i < xs.length; i++) {
    if (x <= xs[i]) {
      const t = (x - xs[i - 1]) / (xs[i] - xs[i - 1]);
      return Math.exp(ys[i - 1] + t * (ys[i] - ys[i - 1]));
    }
  }
  return Math.exp(ys[ys.length - 1]);
}

function plPrice(params, config, qty) {
  const cv = params.curves || {};
  const key = (params.axis_cols || []).map((c) => config[c] ?? "").join("|");
  let curve = cv[key];
  if (!curve) {
    const pref = key.split("|")[0];
    for (const k in cv) if (k.startsWith(pref)) { curve = cv[k]; break; }
  }
  if (!curve) curve = cv[Object.keys(cv)[0]] || {};
  return Math.round(interpLogPts(Object.keys(curve).map((k) => [+k, curve[k]]), qty) * 100) / 100;
}

const CASES = [
  // [tag, config, qty, expected_cash (from Python)]
  ["tent_card_pl_params", { Model: "TC 003", Lamination: "Matte Lamination (Both)" }, 300, 181.7],
  ["tent_card_pl_params", { Model: "TC 003", Lamination: "Matte Lamination (Both)" }, 750, null], // interpolated
  ["tent_card_pl_params", { Model: "TC 004", Lamination: "Matte Lamination (Both) + Spot UV (Front)" }, 500, 565.8],
  ["letterhead_pl_params", { Paper: "Simili 80gsm", "Print Colour": "4C (Both)", Packing: "Loose" }, 500, null],
  ["letterhead_pl_params", { Paper: "Simili 80gsm", "Print Colour": "4C (Both)", Packing: "Pad 100pcs" }, 500, null],
  ["folder_pl_params", { Model: "FPF 001", Paper: "Gloss Art Card 250gsm (1 side coated)", "Print Colour": "4C (Front)", Lamination: "Matte Lamination (Front)", "Colour Protective Layer": "N/A" }, 250, 678.6],
  ["folder_pl_params", { Model: "FPF 001", Paper: "Gloss Art Card 250gsm (1 side coated)", "Print Colour": "4C (Front)", Lamination: "Matte Lamination (Front)", "Colour Protective Layer": "N/A" }, 500, 921.35],
  ["non_woven_bag_pl_params", { Model: "WN-B5", "Print Colour": "1C (Front)" }, 100, null],
  ["non_woven_bag_pl_params", { Model: "WH-A4", "Print Colour": "4C (Both)" }, 500, null],
  ["papan_kopi_pl_params", { Model: "SB 01" }, 100, null],
  ["money_packet_pl_params", { Model: "MP 101", Package: "Normal", Paper: "Gloss Art Paper 130gsm", Finishing: "N/A" }, 100, null],
];

let pass = 0, fail = 0;
for (const [tag, cfg, qty, expected] of CASES) {
  const p = load(`${tag}.json`);
  const got = plPrice(p, cfg, qty);
  const status = expected === null ? "OK" : (Math.abs(got - expected) < 0.01 ? "PASS" : "FAIL");
  if (status === "FAIL") fail++;
  else pass++;
  const key = (p.axis_cols || []).map(c => cfg[c] ?? "").join("|");
  console.log(`${status} ${tag.replace("_pl_params","")}: ${key} q${qty} -> RM${got}${expected !== null ? ` (exp ${expected})` : ""}`);
}
console.log(`\n${pass} pass, ${fail} fail`);
