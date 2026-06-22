"""Mug (Litho) pricing engine. Fixed spec (standard ceramic mug). Drivers: qty(20-300).

  cash_price(qty) -> RM
  build_params() -> writes output/mug_params.json
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "mug_samples.json"
PARAMS = OUT / "mug_params.json"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
# Standard ceramic mug ~350g each
MUG_KG = 0.35
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"core": []}
    return _CACHE["d"]


def _curve() -> dict:
    curve: dict = {}
    for r in _data().get("core", []):
        curve[str(r["qty"])] = r["cash"]
    return curve


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


def cash_price(qty: int) -> float:
    return _interp_ll(_curve(), qty)


def tiers(cash: float) -> dict:
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(qty: int) -> float:
    return round(MUG_KG * float(qty) * WEIGHT_FACTOR, 3)


def loo_audit() -> dict:
    curve = _curve()
    pts = sorted((int(q), c) for q, c in curve.items())
    if len(pts) < 3:
        return {}
    e = []
    for i in range(len(pts)):
        rest = {str(q): c for j, (q, c) in enumerate(pts) if j != i}
        pred = _interp_ll(rest, pts[i][0])
        e.append(abs(pred - pts[i][1]) / pts[i][1] * 100)
    e.sort()
    return {"mug": round(e[len(e)//2], 2)}


def build_params():
    p = {
        "curve": _curve(),
        "mug_kg": MUG_KG,
        "weight_factor": WEIGHT_FACTOR,
    }
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    print("LOO:", loo_audit())
    for q in [20, 40, 100, 200, 300]:
        print(f"q{q}: RM{round(cash_price(q), 2)} wt={weight_kg(q)}kg")
