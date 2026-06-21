"""Computer Form (Litho NCR) pricing engine — decomposed factor model.

Fixed size 9.5" x 11". Reference (Multi Layer): 2 layers / ups 1 / 1C.
  Multi:  core(qty) x layer_f x ups_f x colour_f + copychange_d + numbering_d
  Single Layer / Pay Slip: own qty curve x ups_f x colour_f + deltas
Factors are qty-interpolated (sampled at q2000 & q10000, exact there). core uses log-log
interpolation over qty. Per-ply tints are price-neutral.
"""
from __future__ import annotations
import json, math, re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "computerform_samples.json"
PARAMS = OUT / "computerform_params.json"
SIZE_MM = (241.3, 279.4)   # 9.5" x 11"
NCR_GSM = 55
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
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


def _curve(section):
    return {str(r["qty"]): r["cash"] for r in _data().get(section, [])}


def _factor(section, keyfield, key, qty):
    """qty-interpolated ratio vs the section's reference (the value matching the core ref)."""
    ck = f"f_{section}"
    if ck not in _CACHE:
        rows = _data().get(section, [])
        byk = {}
        for r in rows:
            byk.setdefault(str(r[keyfield]), {})[r["qty"]] = r["cash"]
        # reference key = whichever matches the Multi ref (layers=2, ups=1, colour=1C)
        refkey = {"layer": "2", "ups": "1", "colour": "1C"}.get(section)
        ref = byk.get(refkey, {})
        f = {}
        for k, qs in byk.items():
            f[k] = sorted((q, qs[q] / ref[q]) for q in qs if q in ref and ref[q])
        _CACHE[ck] = f
    pts = _CACHE[ck].get(str(key))
    if not pts:
        return 1.0
    v = _lin(pts, float(qty))
    return v if v is not None else 1.0


def _delta(section, qty):
    ck = f"d_{section}"
    if ck not in _CACHE:
        rows = _data().get(section, [])
        base = {r["qty"]: r["cash"] for r in rows if r["kind"] == "base"}
        pts = sorted((r["qty"], r["cash"] - base[r["qty"]]) for r in rows
                     if r["kind"] != "base" and r["qty"] in base)
        _CACHE[ck] = pts
    v = _lin(_CACHE[ck], float(qty))
    return v if v is not None else 0.0


def cash_price(package, layers=2, ups="1", colour="1C", qty=2000,
               copychange=False, numbering=False):
    if package == "Single Layer Computer Form":
        base = _interp_ll(_curve("single"), qty)
    elif package == "Pay Slip":
        base = _interp_ll(_curve("payslip"), qty)
    else:  # Multi Layer
        base = _interp_ll(_curve("core"), qty) * _factor("layer", "layers", int(layers), qty)
    base *= _factor("ups", "ups", str(ups), qty) * _factor("colour", "colour", str(colour), qty)
    if copychange:
        base += _delta("copychange", qty)
    if numbering:
        base += _delta("numbering", qty)
    return max(base, 0.0)


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(layers, ups, qty, package="Multi Layer Computer Form"):
    w, h = SIZE_MM
    n = 1 if package != "Multi Layer Computer Form" else int(layers)
    sheets = float(qty) * n
    return round((w * h / 1e6) * NCR_GSM * sheets / 1000.0 * WEIGHT_FACTOR, 3)


def build_params():
    for s, kf in [("layer", "layers"), ("ups", "ups"), ("colour", "colour")]:
        _factor(s, kf, "1", 2000)
    _delta("copychange", 2000); _delta("numbering", 2000)
    p = {"core": _curve("core"), "single": _curve("single"), "payslip": _curve("payslip"),
         "layer_f": _CACHE.get("f_layer", {}), "ups_f": _CACHE.get("f_ups", {}),
         "colour_f": _CACHE.get("f_colour", {}),
         "copychange_d": _CACHE.get("d_copychange", []), "numbering_d": _CACHE.get("d_numbering", []),
         "size_mm": SIZE_MM, "ncr_gsm": NCR_GSM, "weight_factor": WEIGHT_FACTOR}
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    for cfg in [dict(package="Multi Layer Computer Form", layers=2, ups="1", colour="1C", qty=2000),
                dict(package="Multi Layer Computer Form", layers=4, ups="2", colour="2C", qty=10000, numbering=True),
                dict(package="Single Layer Computer Form", qty=5000),
                dict(package="Pay Slip", qty=5000)]:
        print(cfg, "->", round(cash_price(**cfg), 2))
