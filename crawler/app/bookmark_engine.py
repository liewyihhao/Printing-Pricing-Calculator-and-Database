"""Bookmark (Digital) pricing engine.

Per-config quantity curve keyed (paper|colour), log-interp over qty. Finishing add-ons
(Round Cornering R6 / Hole Punching 6mm) are additive per-qty deltas (interpolated),
stackable. Fixed bookmark size.

  cash_price(paper, colour, qty, round_corner=False, hole_punch=False) -> RM
"""
from __future__ import annotations
import json, math, re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "bookmark_samples.json"
PARAMS = OUT / "bookmark_params.json"
SIZE_MM = (50, 150)   # standard bookmark ~50x150mm (weight only)
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"core": [], "finishing": []}
    return _CACHE["d"]


def _interp(curve, qty):
    """log-log interpolation (log price vs log qty) — bookmark price is ~power-law in qty."""
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
        cv.setdefault(f"{r['paper']}|{r['colour']}", {})[str(r["qty"])] = r["cash"]
    _CACHE["c"] = cv
    return cv


def _fin_delta(kind, qty):
    fd = _CACHE.get("fd")
    if fd is None:
        fin = _data().get("finishing", [])
        base = {r["qty"]: r["cash"] for r in fin if r["kind"] == "base"}
        fd = {}
        for r in fin:
            if r["kind"] != "base" and r["qty"] in base:
                fd.setdefault(r["kind"], []).append((r["qty"], r["cash"] - base[r["qty"]]))
        _CACHE["fd"] = fd
    return _lin(fd.get(kind, [(0, 0.0)]), qty)


def cash_price(paper, colour, qty, round_corner=False, hole_punch=False):
    cv = _curves()
    key = f"{paper}|{colour}"
    if key not in cv:
        key = next((k for k in cv if k.startswith(f"{paper}|")), None) or \
              next((k for k in cv if k.endswith(f"|{colour}")), None) or next(iter(cv), None)
    if not key:
        return 0.0
    cash = _interp(cv[key], qty)
    if round_corner:
        cash += _fin_delta("round_corner", qty)
    if hole_punch:
        cash += _fin_delta("hole_punch", qty)
    return cash


def finishing_cost(qty, round_corner=False, hole_punch=False):
    return (_fin_delta("round_corner", qty) if round_corner else 0.0) + \
           (_fin_delta("hole_punch", qty) if hole_punch else 0.0)


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(paper, qty):
    w, h = SIZE_MM
    m = re.search(r"(\d+)\s*(gsm|micron)", paper or "")
    gsm = int(m.group(1)) if m else 250
    return round((w * h / 1e6) * gsm * float(qty) / 1000.0 * WEIGHT_FACTOR, 3)


def build_params():
    _fin_delta("round_corner", 500)  # warm fd
    fd = _CACHE.get("fd") or {}
    p = {"curves": _curves(), "fin_delta": {k: sorted(v) for k, v in fd.items()},
         "size_mm": SIZE_MM, "weight_factor": WEIGHT_FACTOR}
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    cv = _curves()
    print(f"bookmark: {len(cv)} curves")
    for k in list(cv)[:3]:
        p, c = k.rsplit("|", 1)
        print(f"  {p[:16]} {c} q1000: RM{round(cash_price(p, c, 1000), 2)} "
              f"+RC+HP: RM{round(cash_price(p, c, 1000, True, True), 2)} wt={weight_kg(p, 1000)}")
