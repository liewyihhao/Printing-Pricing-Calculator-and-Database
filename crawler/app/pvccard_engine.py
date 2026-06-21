"""PVC Card (Digital) pricing engine.

Fixed CR80 card size/material; orientation price-neutral. Per-COLOUR (4C Front / 4C Both)
quantity curve (log-log over qty) + additive Round Cornering / Hole Punching deltas.

  cash_price(colour, qty, round_corner=False, hole_punch=False) -> RM
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "pvccard_samples.json"
PARAMS = OUT / "pvccard_params.json"
CARD_WT = 0.0056   # ~5.6 g per CR80 PVC card
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"core": [], "finishing": []}
    return _CACHE["d"]


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


def _lin(pts, x):
    pts = sorted(pts)
    if not pts:
        return 0.0
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for i in range(1, len(pts)):
        if x <= pts[i][0]:
            t = (x - pts[i-1][0]) / (pts[i][0] - pts[i-1][0])
            return pts[i-1][1] + t * (pts[i][1] - pts[i-1][1])
    return pts[-1][1]


def _curves():
    if "c" in _CACHE:
        return _CACHE["c"]
    cv = {}
    for r in _data().get("core", []):
        cv.setdefault(r["colour"], {})[str(r["qty"])] = r["cash"]
    _CACHE["c"] = cv
    return cv


def _fin_delta(kind, qty):
    d = _CACHE.get("fd")
    if d is None:
        fin = _data().get("finishing", [])
        base = {r["qty"]: r["cash"] for r in fin if r["kind"] == "base"}
        d = {}
        for r in fin:
            if r["kind"] != "base" and r["qty"] in base:
                d.setdefault(r["kind"], []).append((r["qty"], r["cash"] - base[r["qty"]]))
        _CACHE["fd"] = d
    return _lin(d.get(kind, [(0, 0.0)]), qty)


def cash_price(colour, qty, round_corner=False, hole_punch=False):
    cv = _curves()
    key = colour if colour in cv else next(iter(cv), None)
    if not key:
        return 0.0
    cash = _interp_ll(cv[key], qty)
    if round_corner:
        cash += _fin_delta("round_corner", qty)
    if hole_punch:
        cash += _fin_delta("hole_punch", qty)
    return max(cash, 0.0)


def finishing_cost(qty, round_corner=False, hole_punch=False):
    return (_fin_delta("round_corner", qty) if round_corner else 0.0) + \
           (_fin_delta("hole_punch", qty) if hole_punch else 0.0)


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(qty):
    return round(CARD_WT * float(qty) * WEIGHT_FACTOR, 3)


def build_params():
    _fin_delta("round_corner", 100)
    p = {"curves": _curves(), "fin_delta": {k: sorted(v) for k, v in (_CACHE.get("fd") or {}).items()},
         "card_wt": CARD_WT, "weight_factor": WEIGHT_FACTOR}
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    cv = _curves()
    print(f"pvccard: {len(cv)} colour curves")
    for c in cv:
        print(f"  {c} q100: RM{round(cash_price(c, 100), 2)} q1000: RM{round(cash_price(c, 1000), 2)} "
              f"+RC+HP@1000: RM{round(cash_price(c, 1000, True, True), 2)} wt1000={weight_kg(1000)}")
