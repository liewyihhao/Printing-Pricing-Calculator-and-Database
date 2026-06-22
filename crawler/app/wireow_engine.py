"""Wire-O Wall Calendar (Litho) pricing engine.
Fixed spec; price = QUANTITY curve (log-log).
Hole Punching + Wire-O Binding (White) 5/16'' + Hanger compulsory (included).

  cash_price(qty) -> RM
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "wireow_samples.json"
PARAMS = OUT / "wireow_params.json"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
UNIT_KG = 0.30   # nominal kg per Wire-O wall calendar (wire-O + A4 sheets + hanger)
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"core": []}
    return _CACHE["d"]


def _curve():
    return {str(r["qty"]): r["cash"] for r in _data().get("core", [])}


def _interp_ll(curve, qty):
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


def cash_price(qty):
    return _interp_ll(_curve(), qty)


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(qty):
    return round(UNIT_KG * float(qty) * WEIGHT_FACTOR, 3)


def loo_audit():
    pts = sorted((int(r["qty"]), r["cash"]) for r in _data().get("core", []))
    errs = []
    for i in range(len(pts)):
        rest = {str(q): c for j, (q, c) in enumerate(pts) if j != i}
        if len(rest) < 2:
            continue
        pred = _interp_ll(rest, pts[i][0])
        errs.append(abs(pred - pts[i][1]) / pts[i][1] * 100)
    errs.sort()
    return round(errs[len(errs)//2], 2) if errs else 0.0


def build_params():
    p = {"curve": _curve(), "unit_kg": UNIT_KG, "weight_factor": WEIGHT_FACTOR}
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    print(f"wire-o wall cal: LOO median {loo_audit()}%")
    for q in [100, 500, 1000, 5000, 10000]:
        print(f"q{q}: RM{round(cash_price(q), 2)} wt={weight_kg(q)}kg")
