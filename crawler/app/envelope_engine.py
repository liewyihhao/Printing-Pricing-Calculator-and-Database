"""Envelope (Litho) pricing engine.

Model (from output/envelope_samples.json):
  * Per-MODEL base quantity curve at 4C(Front), log-interpolated over qty (pieces).
  * COLOUR = ADDITIVE plate-cost delta vs 4C(Front), from a representative model sampled
    across all 12 colours at two quantities, interpolated over qty. Additive (plate cost)
    transfers across models far better than a multiplicative factor — validated on a 2nd
    model (held-out colour error ~3-10% additive vs ~25% multiplicative).
  Compulsory Die-Cutting + Folding + Gluing are included in the sampled price.

  cash_price(model, colour, qty) -> RM
"""
from __future__ import annotations
import json, math, re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "envelope_samples.json"
PARAMS = OUT / "envelope_params.json"

TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
ENV_GSM = 100  # SMPO/Simili-class envelope paper ~100gsm
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"core": [], "colour": [], "check": []}
    return _CACHE["d"]


def _interp(curve: dict, qty):
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


def _lin(pts, x):
    """linear interp over (x,y) points (for the qty-dependent colour factor)."""
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


def _base_curves():
    if "bc" in _CACHE:
        return _CACHE["bc"]
    cv: dict = {}
    for r in _data().get("core", []):
        cv.setdefault(r["model"], {})[str(r["qty"])] = r["cash"]
    _CACHE["bc"] = cv
    return cv


def _sizes():
    if "sz" in _CACHE:
        return _CACHE["sz"]
    sz = {r["model"]: r.get("size", "") for r in _data().get("core", [])}
    _CACHE["sz"] = sz
    return sz


def _colour_delta(colour, qty):
    """Additive plate-cost delta vs 4C(Front), interpolated over qty (from REF-model table)."""
    cd = _CACHE.get("cd")
    if cd is None:
        col = _data().get("colour", [])
        base = {r["qty"]: r["cash"] for r in col if r["colour"] == "4C (Front)"}
        cd = {}
        for r in col:
            if r["qty"] in base:
                cd.setdefault(r["colour"], []).append((r["qty"], r["cash"] - base[r["qty"]]))
        _CACHE["cd"] = cd
    if colour == "4C (Front)":
        return 0.0
    return _lin(cd.get(colour, [(0, 0.0)]), qty)


def _nearest_model_by_size(model):
    """Unsampled models (the 3 OE moulds) map to a sampled model sharing the same 4-digit
    size code (OE4496->EV4496, OE9013->EV9013), else nearest by sampled face area."""
    bc = _base_curves()
    m4 = re.search(r"(\d{4})", model or "")
    if m4:
        same = [c for c in bc if m4.group(1) in c]
        if same:
            return same[0]
    def area(code):
        s = _sizes().get(code, "")
        mm = re.findall(r"(\d+)", s)
        return int(mm[0]) * int(mm[1]) if len(mm) >= 2 else 0
    cands = [(c, area(c)) for c in bc if area(c)]
    return min(cands, key=lambda x: abs(x[1] - area(model)))[0] if cands else next(iter(bc), None)


def _code(model):
    """Accept a bare code or a 'CODE — 110x220mm' UI label; return the bare code."""
    return re.split(r"[\s—\-(]", (model or "").strip(), 1)[0]


def cash_price(model, colour, qty):
    bc = _base_curves()
    model = _code(model)
    if model not in bc:
        model = _nearest_model_by_size(model)
    if not model or model not in bc:
        return 0.0
    base = _interp(bc[model], qty)
    return max(base + _colour_delta(colour, qty), 0.0)


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(model, qty):
    code = _code(model)
    if code not in _sizes():
        code = _nearest_model_by_size(code) or code
    s = _sizes().get(code, "")
    m = re.findall(r"(\d+)", s)
    w, h = (int(m[0]), int(m[1])) if len(m) >= 2 else (110, 220)
    # an envelope is ~2x the flat face area (front+back) of paper
    return round((w * h / 1e6) * 2 * ENV_GSM * float(qty) / 1000.0 * WEIGHT_FACTOR, 3)


def build_params():
    _colour_delta("4C (Front)", 1000)  # warm cd cache
    cd = _CACHE.get("cd") or {}
    p = {"base_curves": _base_curves(), "sizes": _sizes(),
         "colour_delta": {c: sorted(v) for c, v in cd.items()},
         "env_gsm": ENV_GSM, "weight_factor": WEIGHT_FACTOR}
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    bc = _base_curves()
    print(f"envelope: {len(bc)} model curves")
    for m in list(bc)[:3]:
        for col in ["4C (Front)", "1C (Front)"]:
            print(f"  {m} {col} q1000: RM{round(cash_price(m, col, 1000), 2)} wt={weight_kg(m, 1000)}kg")
