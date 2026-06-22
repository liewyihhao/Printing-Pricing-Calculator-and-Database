"""Static Cling Window Sticker (Digital) pricing engine — decomposed factor model.
Also serves Car Sticker (same form/pricing).

cash = core_curve(qty) x size_f x direction_f x vdp_f
Reference (factor 1.0): 100x100 / Face Out View / no VDP. Factors qty-interpolated (exact at
q100/q1000); core log-log over qty.
"""
from __future__ import annotations
import json, math, re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "staticcling_samples.json"
PARAMS = OUT / "staticcling_params.json"
REF = dict(size="100mm x 100mm", direction="Face Out View", vdp="Not Required")
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
CLING_GSM = 200  # static-cling vinyl ~200 g/m2 equivalent
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
        return None
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for i in range(1, len(pts)):
        if x <= pts[i][0]:
            t = (x - pts[i-1][0]) / (pts[i][0] - pts[i-1][0])
            return pts[i-1][1] + t * (pts[i][1] - pts[i-1][1])
    return pts[-1][1]


def _core():
    return {str(r["qty"]): r["cash"] for r in _data().get("core", [])}


def _factor(section, key, refkey, qty):
    ck = f"f_{section}"
    if ck not in _CACHE:
        rows = _data().get(section, [])
        byk = {}
        for r in rows:
            byk.setdefault(r[section], {})[r["qty"]] = r["cash"]
        ref = byk.get(refkey, {})
        f = {}
        for k, qs in byk.items():
            f[k] = sorted((q, qs[q] / ref[q]) for q in qs if q in ref and ref[q])
        _CACHE[ck] = f
    pts = _CACHE[ck].get(key)
    if not pts:
        return 1.0
    v = _lin(pts, float(qty))
    return v if v is not None else 1.0


def cash_price(size, direction, qty, vdp="Not Required"):
    base = _interp_ll(_core(), qty)
    base *= _factor("size", size, REF["size"], qty)
    base *= _factor("direction", direction, REF["direction"], qty)
    base *= _factor("vdp", vdp, REF["vdp"], qty)
    return max(base, 0.0)


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(size, qty):
    m = re.findall(r"(\d+)", size or "")
    w, h = (int(m[0]), int(m[1])) if len(m) >= 2 else (100, 100)
    return round((w * h / 1e6) * CLING_GSM * float(qty) / 1000.0 * WEIGHT_FACTOR, 3)


def build_params():
    for s, rk in [("size", REF["size"]), ("direction", REF["direction"]), ("vdp", REF["vdp"])]:
        _factor(s, rk, rk, 100)
    p = {"core": _core(), "size_f": _CACHE.get("f_size", {}), "direction_f": _CACHE.get("f_direction", {}),
         "vdp_f": _CACHE.get("f_vdp", {}), "ref": REF, "cling_gsm": CLING_GSM, "weight_factor": WEIGHT_FACTOR}
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    for cfg in [dict(size="100mm x 100mm", direction="Face Out View", qty=100),
                dict(size="310mm x 445mm", direction="Both Side View", qty=1000, vdp="Variable Data Printing (VDP)")]:
        print(cfg["size"], cfg["qty"], "->", round(cash_price(**cfg), 2))
