import { readFileSync } from "fs";
const p = JSON.parse(readFileSync("output/notepad_params.json", "utf8"));

function interpLogPts(pts, x) {
  if (!pts || !pts.length) return 0;
  const xs = pts.map(p => p[0]), ys = pts.map(p => Math.log(p[1]));
  if (x <= xs[0]) return Math.exp(ys[0]);
  if (x >= xs[xs.length-1]) return Math.exp(ys[ys.length-1]);
  for (let i=1;i<xs.length;i++) if(x<=xs[i]){const t=(x-xs[i-1])/(xs[i]-xs[i-1]);return Math.exp(ys[i-1]+t*(ys[i]-ys[i-1]));}
}

function lp(pts, x) {
  if (!pts||!pts.length) return 0;
  if (x <= pts[0][0]) return pts[0][1];
  if (x >= pts[pts.length-1][0]) return pts[pts.length-1][1];
  for (let i=1;i<pts.length;i++) if(x<=pts[i][0]){const t=(x-pts[i-1][0])/(pts[i][0]-pts[i-1][0]);return pts[i-1][1]+t*(pts[i][1]-pts[i-1][1]);}
}

const c = p.curve || {};
const sd = p.spotuv_delta || [];
// Expected from Python: q250 base=338.8, with_suv=360.8; q1000 base=844.8, suv=899.8
const cases = [
  [250, "Matte Lamination (Both)", 338.8],
  [250, "Matte Lamination (Both) + Spot UV (Front Cover)", 360.8],
  [1000, "Matte Lamination (Both)", 844.8],
  [1000, "Matte Lamination (Both) + Spot UV (Front Cover)", 899.8],
  [5000, "Matte Lamination (Both)", 3297.8],
  [5000, "Matte Lamination (Both) + Spot UV (Front Cover)", 3528.8],
];

let pass=0, fail=0;
for (const [qty, lam, expected] of cases) {
  let cash = interpLogPts(Object.keys(c).map(k=>[+k,c[k]]), qty);
  if (/Spot UV/.test(lam)) cash += lp(sd, qty);
  cash = Math.round(cash * 100) / 100;
  const ok = Math.abs(cash - expected) < 0.02;
  if (ok) pass++; else fail++;
  console.log(`${ok?"PASS":"FAIL"} q${qty} ${lam.includes("Spot")?"+SpotUV":""} -> RM${cash} (exp ${expected})`);
}
console.log(`\n${pass} pass, ${fail} fail`);
