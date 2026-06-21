"""Wire-O Notebook (Litho) pricing engine.

Fixed size/paper/pages per cover type. Price = per-COVER quantity curve (log-log over qty,
at the reference Matte Lamination (Front), no additional content) + COVER-LAMINATION delta
+ ADDITIONAL-CONTENT delta (both additive, qty-interpolated). Hot stamping is a block charge
(quoted separately). Wire-O hole punch + binding are compulsory (included).

  cash_price(cover, lamination, addcontent, qty) -> RM
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "wireo_samples.json"
PARAMS = OUT / "wireo_params.json"
REF_LAM = "Matte Lamination (Front)"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
# nominal per-book weight (kg) by cover type (delivery estimate; notebooks ~A5, hard covers heavier)
COVER_WT = {"Hard Cover": 0.32, "VDP Hard Cover": 0.32, "Soft Cover": 0.18, "Exclusive Leather Cover": 0.38}
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {}
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


def _cover_curves():
    if "cc" in _CACHE:
        return _CACHE["cc"]
    cv = {}
    for r in _data().get("core", []):
        cv.setdefault(r["cover"], {})[str(r["qty"])] = r["cash"]
    _CACHE["cc"] = cv
    return cv


def _lam_delta(lam, qty):
    d = _CACHE.get("ld")
    if d is None:
        rows = _data().get("lamination", [])
        base = {r["qty"]: r["cash"] for r in rows if r["lam"] == REF_LAM}
        d = {}
        for r in rows:
            if r["qty"] in base:
                d.setdefault(r["lam"], []).append((r["qty"], r["cash"] - base[r["qty"]]))
        _CACHE["ld"] = d
    if lam == REF_LAM:
        return 0.0
    return _lin(d.get(lam, [(0, 0.0)]), qty)


def _addc_delta(addc, qty):
    d = _CACHE.get("ad")
    if d is None:
        rows = _data().get("addcontent", [])
        base = {r["qty"]: r["cash"] for r in rows if r["addc"] == "None"}
        d = {}
        for r in rows:
            if r["qty"] in base:
                d.setdefault(r["addc"], []).append((r["qty"], r["cash"] - base[r["qty"]]))
        _CACHE["ad"] = d
    if not addc or addc in ("None", "Not Required", "- Not Required -"):
        return 0.0
    return _lin(d.get(addc, [(0, 0.0)]), qty)


def cash_price(cover, lamination=REF_LAM, addcontent=None, qty=10):
    cv = _cover_curves()
    key = cover if cover in cv else next(iter(cv), None)
    if not key:
        return 0.0
    return max(_interp_ll(cv[key], qty) + _lam_delta(lamination, qty) + _addc_delta(addcontent, qty), 0.0)


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(cover, qty):
    return round(COVER_WT.get(cover, 0.3) * float(qty) * WEIGHT_FACTOR, 3)


def build_params():
    _lam_delta(REF_LAM, 50); _addc_delta(None, 50)
    p = {"cover_curves": _cover_curves(),
         "lam_delta": {k: sorted(v) for k, v in (_CACHE.get("ld") or {}).items()},
         "addc_delta": {k: sorted(v) for k, v in (_CACHE.get("ad") or {}).items()},
         "cover_wt": COVER_WT, "ref_lam": REF_LAM, "weight_factor": WEIGHT_FACTOR}
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    cv = _cover_curves()
    print(f"wireo: {len(cv)} cover curves")
    for c in cv:
        print(f"  {c} q50: RM{round(cash_price(c, qty=50), 2)} q500: RM{round(cash_price(c, qty=500), 2)} wt50={weight_kg(c,50)}")
