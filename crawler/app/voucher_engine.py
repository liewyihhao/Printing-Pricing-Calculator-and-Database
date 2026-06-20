"""Voucher (Litho) pricing engine — decomposed factor model.

cash = core_curve(qty) x paper_f x colour_f x sets_f x packform_f x size_f
       + perforation_delta(qty) + numbering_delta(qty)

Reference config (factor = 1.0): Book / 145x210 / Art Paper 100gsm / 4C(Front) / sets 50.
Factors are multiplicative (averaged over the sampled quantities); perforation/numbering
are additive per-qty deltas. core_curve log-interpolated over qty (books/pads).
"""
from __future__ import annotations
import json, math, re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "voucher_samples.json"
PARAMS = OUT / "voucher_params.json"
REF = dict(packform="Book", size="145mm x 210mm", paper="Art Paper 100gsm",
           colour="4C (Front)", sets="50")
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {}
    return _CACHE["d"]


def _interp(curve, qty):
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


def _core():
    if "core" not in _CACHE:
        _CACHE["core"] = {str(r["qty"]): r["cash"] for r in _data().get("core", [])}
    return _CACHE["core"]


def _lin_pts(pts, x):
    pts = sorted(pts)
    if not pts:
        return 1.0
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for i in range(1, len(pts)):
        if x <= pts[i][0]:
            t = (x - pts[i-1][0]) / (pts[i][0] - pts[i-1][0])
            return pts[i-1][1] + t * (pts[i][1] - pts[i-1][1])
    return pts[-1][1]


def _factor(section, keyfield, key, refkey, qty=None):
    """cash[key]/cash[refkey] as a qty-interpolated ratio (exact at the sampled quantities)."""
    cache_k = f"f_{section}"
    if cache_k not in _CACHE:
        rows = _data().get(section, [])
        byk = {}
        for r in rows:
            byk.setdefault(r[keyfield], {})[r["qty"]] = r["cash"]
        ref = byk.get(refkey, {})
        f = {}
        for k, qs in byk.items():
            f[k] = sorted((q, qs[q] / ref[q]) for q in qs if q in ref and ref[q])
        _CACHE[cache_k] = f
    pts = _CACHE[cache_k].get(key)
    if not pts:
        return 1.0
    return _lin_pts(pts, float(qty)) if qty is not None else (sum(p[1] for p in pts) / len(pts))


def _delta(section, keyfield, key, qty):
    """additive delta vs the section's '0'/False baseline, interpolated over qty."""
    cache_k = f"d_{section}"
    if cache_k not in _CACHE:
        rows = _data().get(section, [])
        byk = {}
        for r in rows:
            byk.setdefault(str(r[keyfield]), {})[r["qty"]] = r["cash"]
        base_key = "0" if "0" in byk else ("False" if "False" in byk else None)
        base = byk.get(base_key, {})
        d = {}
        for k, qs in byk.items():
            d[k] = sorted((q, qs[q] - base[q]) for q in qs if q in base)
        _CACHE[cache_k] = d
    pts = _CACHE[cache_k].get(str(key), [])
    if not pts:
        return 0.0
    pts = sorted(pts)
    x = float(qty)
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for i in range(1, len(pts)):
        if x <= pts[i][0]:
            t = (x - pts[i-1][0]) / (pts[i][0] - pts[i-1][0])
            return pts[i-1][1] + t * (pts[i][1] - pts[i-1][1])
    return pts[-1][1]


def _size_factor(size):
    if "f_size" not in _CACHE:
        rows = _data().get("size", [])
        ref = next((r["cash"] for r in rows if r["size"] == REF["size"]), None)
        _CACHE["f_size"] = {r["size"]: (r["cash"] / ref if ref else 1.0) for r in rows}
    return _CACHE["f_size"].get(size, 1.0)


def cash_price(packform, size, paper, colour, sets, qty, perforation="0", numbering=False):
    base = _interp(_core(), qty)
    base *= _factor("paper", "paper", paper, REF["paper"], qty)
    base *= _factor("colour", "colour", colour, REF["colour"], qty)
    base *= _factor("sets", "sets", str(sets), REF["sets"], qty)
    base *= _factor("packform", "packform", packform, REF["packform"], qty)
    base *= _size_factor(size)
    base += _delta("perforation", "perforation", str(perforation), qty)
    base += _delta("numbering", "numbering", "True" if numbering else "False", qty)
    return max(base, 0.0)


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(size, paper, sets, qty):
    m = re.findall(r"(\d+)", size or "")
    w, h = (int(m[0]), int(m[1])) if len(m) >= 2 else (145, 210)
    g = re.search(r"(\d+)\s*gsm", paper or "")
    gsm = int(g.group(1)) if g else 100
    sheets = float(qty) * int(sets)
    return round((w * h / 1e6) * gsm * sheets / 1000.0 * WEIGHT_FACTOR, 3)


def build_params():
    # warm all factor caches
    for s, kf, ref in [("paper", "paper", REF["paper"]), ("colour", "colour", REF["colour"]),
                       ("sets", "sets", REF["sets"]), ("packform", "packform", REF["packform"])]:
        _factor(s, kf, ref, ref)
    _delta("perforation", "perforation", "0", 100)
    _delta("numbering", "numbering", "False", 100)
    _size_factor(REF["size"])
    p = {"core": _core(),
         "paper_f": _CACHE.get("f_paper", {}), "colour_f": _CACHE.get("f_colour", {}),
         "sets_f": _CACHE.get("f_sets", {}), "packform_f": _CACHE.get("f_packform", {}),
         "size_f": _CACHE.get("f_size", {}),
         "perf_d": {k: v for k, v in _CACHE.get("d_perforation", {}).items()},
         "numbering_d": {k: v for k, v in _CACHE.get("d_numbering", {}).items()},
         "ref": REF, "weight_factor": WEIGHT_FACTOR}
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    for cfg in [dict(packform="Book", size="145mm x 210mm", paper="Art Paper 100gsm", colour="4C (Front)", sets="50", qty=100),
                dict(packform="Pad", size="90mm x 140mm", paper="Simili 80gsm", colour="4C (Both)", sets="25", qty=300, perforation="1", numbering=True)]:
        print(cfg, "->", round(cash_price(**cfg), 2))
