"""Kad Terima Kasih (Digital) pricing engine — decomposed factor model.

cash = core_curve(qty) x size_f x paper_f x colour_f + holepunch_delta
Reference (factor 1.0): 52x52 / Gloss Art Card 260gsm / 4C (Front). Factors qty-interpolated
(exact at q100/q500); core log-log over qty; hole punch additive delta.
"""
from __future__ import annotations
import json, math, re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "kadterima_samples.json"
PARAMS = OUT / "kadterima_params.json"
REF = dict(size="52mm x 52mm", paper="Gloss Art Card 260gsm (2 sides coated)", colour="4C (Front)")
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


def _hp_delta(qty):
    d = _CACHE.get("hp")
    if d is None:
        rows = _data().get("holepunch", [])
        base = {r["qty"]: r["cash"] for r in rows if r["kind"] == "base"}
        d = sorted((r["qty"], r["cash"] - base[r["qty"]]) for r in rows
                   if r["kind"] != "base" and r["qty"] in base)
        _CACHE["hp"] = d
    v = _lin(_CACHE["hp"], float(qty))
    return v if v is not None else 0.0


def cash_price(size, paper, colour, qty, hole_punch=False):
    base = _interp_ll(_core(), qty)
    base *= _factor("size", size, REF["size"], qty)
    base *= _factor("paper", paper, REF["paper"], qty)
    base *= _factor("colour", colour, REF["colour"], qty)
    if hole_punch:
        base += _hp_delta(qty)
    return max(base, 0.0)


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(size, paper, qty):
    m = re.findall(r"(\d+)", size or "")
    w, h = (int(m[0]), int(m[1])) if len(m) >= 2 else (52, 52)
    g = re.search(r"(\d+)\s*gsm", paper or "")
    gsm = int(g.group(1)) if g else 260
    return round((w * h / 1e6) * gsm * float(qty) / 1000.0 * WEIGHT_FACTOR, 3)


def build_params():
    for s, rk in [("size", REF["size"]), ("paper", REF["paper"]), ("colour", REF["colour"])]:
        _factor(s, rk, rk, 100)
    _hp_delta(100)
    p = {"core": _core(), "size_f": _CACHE.get("f_size", {}), "paper_f": _CACHE.get("f_paper", {}),
         "colour_f": _CACHE.get("f_colour", {}), "hp_delta": _CACHE.get("hp", []),
         "ref": REF, "weight_factor": WEIGHT_FACTOR}
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    for cfg in [dict(size="52mm x 52mm", paper="Gloss Art Card 260gsm (2 sides coated)", colour="4C (Front)", qty=100),
                dict(size="40mm x 86mm", paper="Metal Ice 250gsm", colour="4C (Both)", qty=500, hole_punch=True)]:
        print(cfg["size"], cfg["qty"], "->", round(cash_price(**cfg), 2))
