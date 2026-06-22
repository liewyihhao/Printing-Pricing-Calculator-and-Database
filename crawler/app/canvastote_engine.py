"""Canvas Tote Bag (Litho) pricing engine. Fixed size. Drivers: colour(2) x qty(100-700).

  cash_price(colour, qty) -> RM
  build_params() -> writes output/canvastote_params.json
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "canvastote_samples.json"
PARAMS = OUT / "canvastote_params.json"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065

COLOURS = ["1C (Front)", "1C (Both)"]
# Standard tote bag ~38cm × 42cm, canvas ~250gsm
BAG_W_M = 0.38; BAG_H_M = 0.42; CANVAS_GSM = 250
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"data": []}
    return _CACHE["d"]


def _curves() -> dict[str, dict]:
    curves: dict[str, dict] = {}
    for r in _data().get("data", []):
        curves.setdefault(r["colour"], {})[str(r["qty"])] = r["cash"]
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


def cash_price(colour: str, qty: int) -> float:
    curves = _curves()
    curve = curves.get(colour) or next(iter(curves.values()), {})
    return _interp_ll(curve, qty)


def tiers(cash: float) -> dict:
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(qty: int) -> float:
    grams = BAG_W_M * BAG_H_M * CANVAS_GSM * float(qty)
    return round(grams / 1000.0 * WEIGHT_FACTOR, 3)


def loo_audit() -> dict[str, float]:
    curves = _curves(); errs = {}
    for colour, curve in curves.items():
        pts = sorted((int(q), c) for q, c in curve.items())
        if len(pts) < 3:
            continue
        e = []
        for i in range(len(pts)):
            rest = {str(q): c for j, (q, c) in enumerate(pts) if j != i}
            pred = _interp_ll(rest, pts[i][0])
            e.append(abs(pred - pts[i][1]) / pts[i][1] * 100)
        e.sort()
        errs[colour] = round(e[len(e)//2], 2)
    return errs


def build_params():
    p = {
        "curves": _curves(),
        "colours": COLOURS,
        "bag_w_m": BAG_W_M, "bag_h_m": BAG_H_M,
        "canvas_gsm": CANVAS_GSM,
        "weight_factor": WEIGHT_FACTOR,
    }
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    loo = loo_audit()
    for c, e in loo.items():
        print(f"{c}: LOO {e}%")
    for colour in COLOURS:
        for q in [100, 300, 500, 700]:
            print(f"{colour} q{q}: RM{round(cash_price(colour, q), 2)} wt={weight_kg(q)}kg")
