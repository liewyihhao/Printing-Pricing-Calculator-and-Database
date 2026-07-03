"""Banner (Litho) pricing engine — exact v4 CheckPrice pricelist.

Drivers: size (20) x qty (1-300). Material is price-neutral (300gsm=380gsm).
Eyelets: (top_eyelet-2)*5 + (bot_eyelet-2)*5 RM per banner (additive delta).

  cash_price(size, qty, top_eyelet=2, bot_eyelet=2) -> RM
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
PLX_PARAMS = OUT / "banner_plx_params.json"   # new exact pricelist
LEGACY_FILE = OUT / "banner_samples.json"      # old sampled curves (fallback)
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
MATERIAL_GSM = 400   # solvent-printed tarpaulin estimate

SIZES = [
    "3ft x 2ft", "4ft x 2ft", "6ft x 2ft", "4ft x 3ft", "8ft x 3ft",
    "10ft x 3ft", "8ft x 4ft", "10ft x 4ft", "18ft x 3ft", "20ft x 4ft",
    "2ft x 3ft", "2ft x 4ft", "2ft x 6ft", "3ft x 4ft", "3ft x 8ft",
    "3ft x 10ft", "4ft x 8ft", "4ft x 10ft", "3ft x 18ft", "4ft x 20ft",
]
MATERIALS = ["Tarpaulin 300gsm", "Tarpaulin 380gsm"]
TOP_EYELET_OPTS = ["2", "3", "4", "5"]
BOT_EYELET_OPTS = ["2", "3", "4", "5"]
EYELET_DELTA_PER_EXTRA = 0.5   # RM per banner per each eyelet above base of 2

_CACHE: dict = {}
FT_TO_M = 0.3048


def _plx() -> dict:
    if "plx" not in _CACHE:
        _CACHE["plx"] = json.loads(PLX_PARAMS.read_text()) if PLX_PARAMS.exists() else {}
    return _CACHE["plx"]


def _legacy_curves() -> dict[str, dict]:
    if "leg" not in _CACHE:
        raw = json.loads(LEGACY_FILE.read_text()) if LEGACY_FILE.exists() else {"data": []}
        curves: dict[str, dict] = {}
        for r in raw.get("data", []):
            curves.setdefault(r["size"], {})[str(r["qty"])] = r["cash"]
        _CACHE["leg"] = curves
    return _CACHE["leg"]


def _ft_dims(size_str: str) -> tuple[float, float]:
    parts = size_str.lower().replace("ft", "").split("x")
    return float(parts[0].strip()) * FT_TO_M, float(parts[1].strip()) * FT_TO_M


def _interp_ll(curve: dict, qty: float) -> float:
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


def cash_price(size: str, qty: int, top_eyelet: int = 2, bot_eyelet: int = 2) -> float:
    plx = _plx()
    sizes_tbl = plx.get("sizes", {})
    if sizes_tbl and size in sizes_tbl:
        # Exact lookup from pricelist
        curve = sizes_tbl[size]
        base = float(curve.get(str(qty), 0))
        if base <= 0 and qty > 300:
            # Extrapolate: last two stored points
            pts = sorted((int(q), p) for q, p in curve.items())
            if len(pts) >= 2:
                q1, p1 = pts[-2]; q2, p2 = pts[-1]
                base = p2 + (qty - q2) * (p2 - p1) / (q2 - q1)
        eyelet_delta = ((top_eyelet - 2) + (bot_eyelet - 2)) * EYELET_DELTA_PER_EXTRA * qty
        return max(round(base + eyelet_delta, 2), 0.0)
    # Fallback to legacy log-log curve
    curve = _legacy_curves().get(size, {})
    if curve:
        return _interp_ll(curve, qty)
    return 0.0


def tiers(cash: float) -> dict:
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(size: str, qty: int) -> float:
    w, h = _ft_dims(size)
    grams = w * h * MATERIAL_GSM * float(qty)
    return round(grams / 1000.0 * WEIGHT_FACTOR, 3)


if __name__ == "__main__":
    plx = _plx()
    if plx:
        print("Using pricelist engine (exact)")
        for sz in SIZES[:3]:
            for q in [1, 10, 50, 100, 300]:
                p = cash_price(sz, q)
                print(f"  {sz} qty={q}: RM{p:.2f}")
    else:
        print("No pricelist — using legacy curves")
