"""L-Shape Plastic Folder (Digital) pricing engine.

Fixed model LSF 001, size 310x442mm, 4C. Price = per-PAPER quantity curve
(Synthetic Paper 180micron / Frosted Plastic 200micron), log-interpolated over qty.

  cash_price(paper, qty) -> RM
"""
from __future__ import annotations
import json, math, re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "lshape_samples.json"
PARAMS = OUT / "lshape_params.json"
SIZE_MM = (310, 442)
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"core": []}
    return _CACHE["d"]


def _interp(curve, qty):
    pts = sorted((int(q), c) for q, c in curve.items())
    if not pts:
        return 0.0
    xs = [p[0] for p in pts]; ys = [math.log(p[1]) for p in pts]; x = float(qty)
    if x <= xs[0]:
        return math.exp(ys[0])
    if x >= xs[-1]:
        return math.exp(ys[-1])
    for i in range(1, len(xs)):
        if x <= xs[i]:
            t = (x - xs[i-1]) / (xs[i] - xs[i-1])
            return math.exp(ys[i-1] + t * (ys[i] - ys[i-1]))
    return math.exp(ys[-1])


def _curves():
    if "c" in _CACHE:
        return _CACHE["c"]
    cv = {}
    for r in _data().get("core", []):
        cv.setdefault(r["paper"], {})[str(r["qty"])] = r["cash"]
    _CACHE["c"] = cv
    return cv


def cash_price(paper, qty):
    cv = _curves()
    key = paper if paper in cv else next((k for k in cv if paper and paper[:9] in k), next(iter(cv), None))
    return _interp(cv[key], qty) if key else 0.0


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(paper, qty):
    w, h = SIZE_MM
    micron = 200 if "200" in (paper or "") else 180
    gsm = micron * 1.0  # ~1 g/m2 per micron for plastic film approx
    return round((w * h / 1e6) * gsm * float(qty) / 1000.0 * WEIGHT_FACTOR, 3)


def build_params():
    p = {"curves": _curves(), "size_mm": SIZE_MM, "weight_factor": WEIGHT_FACTOR}
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    cv = _curves()
    print(f"lshape: {len(cv)} paper curves")
    for k in cv:
        for q in [50, 500, 4000]:
            print(f"  {k[:22]} q{q}: RM{round(cash_price(k, q), 2)} wt={weight_kg(k, q)}kg")
