"""Paper Bag (Litho) pricing engine. Fixed size. Drivers: paper(2) x qty(50-500).

  cash_price(paper, qty) -> RM
  build_params() -> writes output/paperbag_params.json
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "paperbag_samples.json"
PARAMS = OUT / "paperbag_params.json"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065

PAPERS = ["Gloss Art Paper 157gsm", "Gloss Art Card 190gsm (1 side coated)"]
_PAPER_GSM = {"Gloss Art Paper 157gsm": 157, "Gloss Art Card 190gsm (1 side coated)": 190}
# Standard A4 paper bag flat ~30cm × 40cm + gusset ~10cm → ~120cm² net sheet ~1600cm²
BAG_SHEET_M2 = 0.16
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"data": []}
    return _CACHE["d"]


def _curves() -> dict[str, dict]:
    curves: dict[str, dict] = {}
    for r in _data().get("data", []):
        curves.setdefault(r["paper"], {})[str(r["qty"])] = r["cash"]
    return curves


def _interp_ll(curve: dict, qty: float) -> float:
    pts = sorted((int(q), c) for q, c in curve.items())
    if not pts:
        return 0.0
    xs = [math.log(p[0]) for p in pts]; ys = [math.log(p[1]) for p in pts]
    x = math.log(max(float(qty), 1))
    if x <= xs[0]:
        return math.exp(ys[0])
    if x >= xs[-1]:
        return math.exp(ys[-1])
    for i in range(1, len(xs)):
        if x <= xs[i]:
            t = (x - xs[i-1]) / (xs[i] - xs[i-1])
            return math.exp(ys[i-1] + t * (ys[i] - ys[i-1]))
    return math.exp(ys[-1])


def cash_price(paper: str, qty: int) -> float:
    curves = _curves()
    curve = curves.get(paper) or next(iter(curves.values()), {})
    return _interp_ll(curve, qty)


def tiers(cash: float) -> dict:
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(paper: str, qty: int) -> float:
    gsm = _PAPER_GSM.get(paper, 157)
    grams = BAG_SHEET_M2 * gsm * float(qty)
    return round(grams / 1000.0 * WEIGHT_FACTOR, 3)


def loo_audit() -> dict[str, float]:
    curves = _curves(); errs = {}
    for paper, curve in curves.items():
        pts = sorted((int(q), c) for q, c in curve.items())
        if len(pts) < 3:
            continue
        e = []
        for i in range(len(pts)):
            rest = {str(q): c for j, (q, c) in enumerate(pts) if j != i}
            pred = _interp_ll(rest, pts[i][0])
            e.append(abs(pred - pts[i][1]) / pts[i][1] * 100)
        e.sort()
        errs[paper] = round(e[len(e)//2], 2)
    return errs


def build_params():
    p = {
        "curves": _curves(),
        "papers": PAPERS,
        "paper_gsm": _PAPER_GSM,
        "bag_sheet_m2": BAG_SHEET_M2,
        "weight_factor": WEIGHT_FACTOR,
    }
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    loo = loo_audit()
    for p, e in loo.items():
        print(f"{p}: LOO {e}%")
    for paper in PAPERS:
        for q in [50, 100, 300, 500]:
            print(f"{paper[:20]} q{q}: RM{round(cash_price(paper, q), 2)} wt={weight_kg(paper, q)}kg")
