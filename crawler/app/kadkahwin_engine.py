"""Kad Kahwin (Digital) pricing engine — decomposed factor model.

cash = core_curve(qty) x size_f x paper_f x colour_f x ordertype_f
Reference (factor 1.0): Standard / A5 / Gloss Art Card 260gsm / 4C (Front). Factors are
qty-interpolated ratios (exact at sampled q100/q500); core is log-log over qty. Folding code
and hot stamping are quoted separately (block charges).
"""
from __future__ import annotations
import json, math, re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "kadkahwin_samples.json"
PARAMS = OUT / "kadkahwin_params.json"
REF = dict(ordertype="1,Standard Kad Kahwin", size="A5 (148mm x 210mm)",
           paper="Gloss Art Card 260gsm (2 sides coated)", colour="4C (Front)")
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


def _core():
    return {str(r["qty"]): r["cash"] for r in _data().get("core", [])}


def _factor(section, keyfield, key, refkey, qty):
    ck = f"f_{section}"
    if ck not in _CACHE:
        rows = _data().get(section, [])
        byk = {}
        for r in rows:
            byk.setdefault(r[keyfield], {})[r["qty"]] = r["cash"]
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


def cash_price(ordertype, size, paper, colour, qty):
    base = _interp_ll(_core(), qty)
    base *= _factor("size", "size", size, REF["size"], qty)
    base *= _factor("paper", "paper", paper, REF["paper"], qty)
    base *= _factor("colour", "colour", colour, REF["colour"], qty)
    base *= _factor("ordertype", "ordertype", ordertype, REF["ordertype"], qty)
    return max(base, 0.0)


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(size, paper, qty):
    m = re.findall(r"(\d+)\s*mm", size or "")
    w, h = (int(m[0]), int(m[1])) if len(m) >= 2 else (148, 210)
    g = re.search(r"(\d+)\s*gsm", paper or "")
    gsm = int(g.group(1)) if g else 260
    return round((w * h / 1e6) * gsm * float(qty) / 1000.0 * WEIGHT_FACTOR, 3)


def build_params():
    for s, kf, rk in [("size", "size", REF["size"]), ("paper", "paper", REF["paper"]),
                      ("colour", "colour", REF["colour"]), ("ordertype", "ordertype", REF["ordertype"])]:
        _factor(s, kf, rk, rk, 100)
    p = {"core": _core(), "size_f": _CACHE.get("f_size", {}), "paper_f": _CACHE.get("f_paper", {}),
         "colour_f": _CACHE.get("f_colour", {}), "ordertype_f": _CACHE.get("f_ordertype", {}),
         "ref": REF, "weight_factor": WEIGHT_FACTOR}
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    for cfg in [dict(ordertype="1,Standard Kad Kahwin", size="A5 (148mm x 210mm)", paper="Gloss Art Card 260gsm (2 sides coated)", colour="4C (Front)", qty=100),
                dict(ordertype="2,Custom Die-cut Kad Kahwin", size="A4 (210mm x 297mm)", paper="Metal Ice 250gsm", colour="4C (Both)", qty=500)]:
        print(cfg["size"], cfg["qty"], "->", round(cash_price(**cfg), 2))
