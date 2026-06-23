"""Generic engine for simple products priced as a per-variant QUANTITY curve (log-log),
with optional price-neutral selectable fields (e.g. lamination). Shared by small
Apparel & Gifts items (Hand Fan, Hanger, Button Badge, ...).

Each product has output/<tag>_samples.json: {"core":[{variant,qty,cash}], "lam":[...]}.
build_params(tag, ...) -> output/<tag>_params.json: {curves, variant_field, unit_wt, note}.

  cash_price(params, variant, qty) -> RM
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065


def _interp_ll(curve: dict, qty) -> float:
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


def _curves_from(samples: dict) -> dict:
    cv: dict = {}
    for r in samples.get("core", []):
        cv.setdefault(r["variant"], {})[str(r["qty"])] = r["cash"]
    return cv


def cash_price(params: dict, variant: str, qty) -> float:
    cv = params.get("curves", {})
    key = variant if variant in cv else next(iter(cv), None)
    if not key:
        return 0.0
    return _interp_ll(cv[key], qty)


def tiers(cash: float) -> dict:
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(params: dict, qty) -> float:
    return round(params.get("unit_wt", 0.05) * float(qty) * WEIGHT_FACTOR, 3)


def loo_audit(curves: dict) -> float:
    errs = []
    for cv in curves.values():
        pts = sorted((int(q), c) for q, c in cv.items())
        for i in range(len(pts)):
            rest = {str(q): c for j, (q, c) in enumerate(pts) if j != i}
            if len(rest) < 2:
                continue
            pred = _interp_ll(rest, pts[i][0])
            errs.append(abs(pred - pts[i][1]) / pts[i][1] * 100)
    errs.sort()
    return round(errs[len(errs)//2], 2) if errs else 0.0


def build_params(tag: str, variant_field: str, unit_wt: float, note: str) -> dict:
    samples = json.loads((OUT / f"{tag}_samples.json").read_text())
    curves = _curves_from(samples)
    p = {"curves": curves, "variant_field": variant_field, "unit_wt": unit_wt,
         "note": note, "weight_factor": WEIGHT_FACTOR}
    (OUT / f"{tag}_params.json").write_text(json.dumps(p, indent=0))
    return p


def check_lam_neutral(tag: str) -> bool:
    """True if all 'lam' rows at the same qty share the same cash (price-neutral)."""
    samples = json.loads((OUT / f"{tag}_samples.json").read_text())
    by_q: dict = {}
    for r in samples.get("lam", []):
        by_q.setdefault(r["qty"], set()).add(r["cash"])
    return all(len(s) == 1 for s in by_q.values())
