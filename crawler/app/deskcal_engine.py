"""Desk Calendar (Litho) pricing engine.

Hard Stand: rdCategory (1=Portrait, 2=Landscape, 3=HotStamping-Portrait) x qty.
Soft Stand: qty only (Wire-O with cardboard cover).

  cash_price(variant, cat, qty) -> RM
  variant: "hard" | "soft"
  cat: "1" | "2" | "3"  (hard only)
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "deskcal_samples.json"
PARAMS = OUT / "deskcal_params.json"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065

# Nominal weight per finished desk calendar (rough estimate; wire-O + A4 sheets + stand)
HARD_UNIT_KG = 0.35
SOFT_UNIT_KG = 0.25

HARD_CATS = {
    "1": "WDCH 001 (Portrait)",
    "2": "WDCH 002 (Landscape)",
    "3": "DCHS 001 (Hot Stamping - Portrait)",
}

_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"hard": [], "soft": []}
    return _CACHE["d"]


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


def _soft_curve() -> dict:
    return {str(r["qty"]): r["cash"] for r in _data().get("soft", [])}


def _hard_curves() -> dict[str, dict]:
    curves: dict[str, dict] = {}
    for r in _data().get("hard", []):
        c = str(r["cat"])
        curves.setdefault(c, {})[str(r["qty"])] = r["cash"]
    return curves


def cash_price(variant: str, qty: int, cat: str = "1") -> float:
    if variant == "soft":
        return _interp_ll(_soft_curve(), qty)
    # hard — find cat curve; fallback to cat "1" if missing
    curves = _hard_curves()
    curve = curves.get(cat) or curves.get("1") or {}
    return _interp_ll(curve, qty)


def tiers(cash: float) -> dict:
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(variant: str, qty: int) -> float:
    unit = HARD_UNIT_KG if variant == "hard" else SOFT_UNIT_KG
    return round(unit * float(qty) * WEIGHT_FACTOR, 3)


def loo_audit(variant: str = "soft") -> float:
    if variant == "soft":
        pts = sorted((int(r["qty"]), r["cash"]) for r in _data().get("soft", []))
    else:
        pts = sorted((int(r["qty"]), r["cash"]) for r in _data().get("hard", []) if r["cat"] == "1")
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
    p = {
        "soft_curve": _soft_curve(),
        "hard_curves": _hard_curves(),
        "hard_cats": HARD_CATS,
        "hard_unit_kg": HARD_UNIT_KG,
        "soft_unit_kg": SOFT_UNIT_KG,
        "weight_factor": WEIGHT_FACTOR,
    }
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    print(f"Soft LOO median: {loo_audit('soft')}%")
    for q in [100, 500, 1000, 5000, 10000]:
        print(f"soft q{q}: RM{round(cash_price('soft', q), 2)} wt={weight_kg('soft', q)}kg")
    curves = _hard_curves()
    if curves:
        print(f"Hard LOO median (cat=1): {loo_audit('hard')}%")
        for q in [100, 500, 1000]:
            for cat in ["1", "2", "3"]:
                c = round(cash_price('hard', q, cat), 2)
                print(f"  hard cat={cat} q{q}: RM{c}")
    else:
        print("Hard: no samples yet")
