"""Roll-Up Stand (Litho) pricing engine. Fixed size stand. Drivers: lamination(2) x qty(1-100).
Price = per-lamination log-log qty curve.

  cash_price(lam, qty) -> RM
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "rollup_samples.json"
PARAMS = OUT / "rollup_params.json"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
# Standard roll-up stand display panel: ~85cm wide × 200cm tall, printed vinyl
STAND_W_M = 0.85
STAND_H_M = 2.00
MATERIAL_GSM = 400   # vinyl estimate

LAMS = ["Matte Lamination", "Gloss Lamination"]
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"data": []}
    return _CACHE["d"]


def _curves() -> dict[str, dict]:
    curves: dict[str, dict] = {}
    for r in _data().get("data", []):
        curves.setdefault(r["lam"], {})[str(r["qty"])] = r["cash"]
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


def cash_price(lam: str, qty: int) -> float:
    curves = _curves()
    curve = curves.get(lam) or next(iter(curves.values()), {})
    return _interp_ll(curve, qty)


def tiers(cash: float) -> dict:
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(qty: int) -> float:
    grams = STAND_W_M * STAND_H_M * MATERIAL_GSM * float(qty)
    return round(grams / 1000.0 * WEIGHT_FACTOR, 3)


def loo_audit() -> dict[str, float]:
    curves = _curves(); errs = {}
    for lam, curve in curves.items():
        pts = sorted((int(q), c) for q, c in curve.items())
        if len(pts) < 3:
            continue
        e = []
        for i in range(len(pts)):
            rest = {str(q): c for j, (q, c) in enumerate(pts) if j != i}
            pred = _interp_ll(rest, pts[i][0])
            e.append(abs(pred - pts[i][1]) / pts[i][1] * 100)
        e.sort()
        errs[lam] = round(e[len(e)//2], 2)
    return errs


def build_params():
    p = {"curves": _curves(), "lams": LAMS, "stand_w_m": STAND_W_M, "stand_h_m": STAND_H_M,
         "material_gsm": MATERIAL_GSM, "weight_factor": WEIGHT_FACTOR}
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    loo = loo_audit()
    for lam, e in loo.items():
        print(f"{lam}: LOO {e}%")
    for lam in LAMS:
        for q in [1, 5, 10, 50, 100]:
            print(f"{lam[:5]} q{q}: RM{round(cash_price(lam, q), 2)} wt={weight_kg(q)}kg")
