"""Envelope (Litho) pricing engine — exact v4 CheckPrice pricelist.

All 17 models x colour x qty sampled exactly. Log-log interpolation between
orderable quantities. Compulsory Die-Cutting + Folding + Gluing included.

  cash_price(model, colour, qty) -> RM
"""
from __future__ import annotations
import json, math, re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
PLX_PARAMS = OUT / "envelope_plx_params.json"
LEGACY_FILE = OUT / "envelope_samples.json"
LEGACY_PARAMS = OUT / "envelope_params.json"

TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
ENV_GSM = 100  # Simili-class envelope paper ~100gsm

_CACHE: dict = {}


def _plx() -> dict:
    if "plx" not in _CACHE:
        _CACHE["plx"] = json.loads(PLX_PARAMS.read_text(encoding="utf-8")) if PLX_PARAMS.exists() else {}
    return _CACHE["plx"]


def _interp_ll(curve: dict, qty: float) -> float:
    """Log-log interpolation."""
    pts = sorted((int(q), p) for q, p in curve.items())
    if not pts:
        return 0.0
    xs = [math.log(p[0]) for p in pts]
    ys = [math.log(p[1]) for p in pts]
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


def _legacy_data():
    if "ld" in _CACHE:
        return _CACHE["ld"]
    d = json.loads(LEGACY_FILE.read_text()) if LEGACY_FILE.exists() else {"core": [], "colour": []}
    _CACHE["ld"] = d
    return d


def _legacy_curves() -> dict[str, dict]:
    if "bc" in _CACHE:
        return _CACHE["bc"]
    cv: dict[str, dict] = {}
    for r in _legacy_data().get("core", []):
        cv.setdefault(r["model"], {})[str(r["qty"])] = r["cash"]
    _CACHE["bc"] = cv
    return cv


def _legacy_sizes():
    if "sz" in _CACHE:
        return _CACHE["sz"]
    sz = {r["model"]: r.get("size", "") for r in _legacy_data().get("core", [])}
    _CACHE["sz"] = sz
    return sz


def _legacy_colour_delta(colour, qty):
    """Additive plate-cost delta vs 4C(Front) (legacy fallback)."""
    cd = _CACHE.get("cd")
    if cd is None:
        col = _legacy_data().get("colour", [])
        base = {r["qty"]: r["cash"] for r in col if r["colour"] == "4C (Front)"}
        cd = {}
        for r in col:
            if r["qty"] in base:
                cd.setdefault(r["colour"], []).append((r["qty"], r["cash"] - base[r["qty"]]))
        _CACHE["cd"] = cd
    if colour == "4C (Front)":
        return 0.0
    pts = sorted(cd.get(colour, [(0, 0.0)]))
    x = float(qty)
    if not pts or x <= pts[0][0]:
        return pts[0][1] if pts else 0.0
    if x >= pts[-1][0]:
        return pts[-1][1]
    for i in range(1, len(pts)):
        if x <= pts[i][0]:
            t = (x - pts[i-1][0]) / (pts[i][0] - pts[i-1][0])
            return pts[i-1][1] + t * (pts[i][1] - pts[i-1][1])
    return pts[-1][1]


def _code(model: str) -> str:
    """Accept a bare code or a 'CODE — 110x220mm' UI label; return the bare code."""
    return re.split(r"[\s—\-(]", (model or "").strip(), 1)[0]


def cash_price(model: str, colour: str, qty: int) -> float:
    model = _code(model)
    plx = _plx()
    curves = plx.get("curves", {})
    if curves:
        key = f"{model}|{colour}"
        curve = curves.get(key)
        if curve:
            return round(max(_interp_ll(curve, qty), 0.0), 2)
        # Try 4C (Front) as base + colour delta if exact colour not sampled
        base_key = f"{model}|4C (Front)"
        base_curve = curves.get(base_key)
        if base_curve:
            base = _interp_ll(base_curve, qty)
            # No colour delta in exact engine — use legacy delta as fallback approximation
            return round(max(base + _legacy_colour_delta(colour, qty), 0.0), 2)
    # Legacy formula fallback
    bc = _legacy_curves()
    if model not in bc:
        # Nearest model by 4-digit size code
        m4 = re.search(r"(\d{4})", model or "")
        if m4:
            same = [c for c in bc if m4.group(1) in c]
            if same:
                model = same[0]
    if not model or model not in bc:
        return 0.0
    base = _interp_ll(bc[model], float(qty))
    return round(max(base + _legacy_colour_delta(colour, qty), 0.0), 2)


def tiers(cash: float) -> dict:
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def _model_size(model: str) -> str:
    """Return the size string for a model (from plx model_meta or legacy)."""
    plx = _plx()
    meta = plx.get("model_meta", {})
    if model in meta:
        return meta[model].get("size", "")
    return _legacy_sizes().get(model, "")


def weight_kg(model: str, qty: int) -> float:
    code = _code(model)
    s = _model_size(code)
    m = re.findall(r"(\d+)", s)
    w, h = (int(m[0]), int(m[1])) if len(m) >= 2 else (110, 220)
    return round((w * h / 1e6) * 2 * ENV_GSM * float(qty) / 1000.0 * WEIGHT_FACTOR, 3)


if __name__ == "__main__":
    plx = _plx()
    if plx.get("curves"):
        n = len(plx["curves"])
        print(f"Using exact pricelist ({n} curves)")
        for model in ["EV4496NW", "EV4286NW", "IS4286NW", "OE4496NW"]:
            for colour in ["4C (Front)", "1C (Front)"]:
                p = cash_price(model, colour, 1000)
                print(f"  {model} {colour} q1000: RM{p:.2f}")
    else:
        print("No pricelist — using legacy formula")
