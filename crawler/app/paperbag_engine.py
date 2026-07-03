"""Paper Bag (Litho) pricing engine — exact v4 CheckPrice pricelist.

Drivers: model(7) x paper(2) x lamination(3) x qty(29 steps: 50-10000).
Rope colour and hot stamping are price-neutral (verified).

  cash_price(model, paper, lamination, qty) -> RM
"""
from __future__ import annotations
import json, math, re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
PLX_PARAMS = OUT / "paperbag_plx_params.json"   # new exact pricelist
LEGACY_PARAMS = OUT / "paperbag_params.json"    # old sampled curves (fallback)
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065

MODEL_SIZE = {
    "PBG 001": "180mm x 80mm x 230mm",
    "PBG 002": "220mm x 80mm x 230mm",
    "PBG 003": "250mm x 95mm x 350mm",
    "PBG 004": "200mm x 95mm x 290mm",
    "PBG 005": "320mm x 95mm x 230mm",
    "PBG 006": "370mm x 120mm x 295mm",
    "PBG 007": "320mm x 120mm x 420mm",
}
MODELS = list(MODEL_SIZE.keys())
PAPERS = ["Gloss Art Paper 157gsm", "Gloss Art Card 190gsm"]
LAMINATIONS = ["Gloss Lamination", "Matte Lamination", "Matte Lamination + Spot UV"]
ROPE_COLOURS = ["Black", "Blue", "Red", "White", "Gold", "Green", "Silver"]

_PAPER_GSM = {"Gloss Art Paper 157gsm": 157, "Gloss Art Card 190gsm": 190}
_CACHE: dict = {}


def _plx() -> dict:
    if "plx" not in _CACHE:
        _CACHE["plx"] = json.loads(PLX_PARAMS.read_text()) if PLX_PARAMS.exists() else {}
    return _CACHE["plx"]


def _legacy() -> dict:
    if "leg" not in _CACHE:
        p = json.loads(LEGACY_PARAMS.read_text()) if LEGACY_PARAMS.exists() else {}
        _CACHE["leg"] = p.get("curves", {})
    return _CACHE["leg"]


def _parse_dims(size: str) -> tuple[int, int, int]:
    nums = [int(x) for x in re.findall(r"\d+", size)]
    return nums[0], nums[1], nums[2] if len(nums) >= 3 else (180, 80, 230)


def _bag_area_m2(model: str) -> float:
    size = MODEL_SIZE.get(model, "180mm x 80mm x 230mm")
    W, D, H = _parse_dims(size)
    # Sheet area: 2*(W+D)*H + 2*D*W (flat net approx, mm²)
    area_mm2 = 2 * (W + D) * H + 2 * D * W
    return area_mm2 / 1_000_000


def _interp_ll(curve: dict, qty: float) -> float:
    pts = sorted((int(q), c) for q, c in curve.items())
    if not pts:
        return 0.0
    xs = [math.log(p[0]) for p in pts]; ys = [math.log(p[1]) for p in pts]
    x = math.log(max(float(qty), 1))
    if x <= xs[0]: return math.exp(ys[0])
    if x >= xs[-1]: return math.exp(ys[-1])
    for i in range(1, len(xs)):
        if x <= xs[i]:
            t = (x - xs[i-1]) / (xs[i] - xs[i-1])
            return math.exp(ys[i-1] + t * (ys[i] - ys[i-1]))
    return math.exp(ys[-1])


def cash_price(model: str, paper: str, lamination: str, qty: int) -> float:
    plx = _plx()
    curves = plx.get("curves", {})
    if curves:
        key = f"{model}|{paper}|{lamination}"
        curve = curves.get(key, {})
        if curve:
            # Exact lookup for orderable qtys; log-log interp for others
            if str(qty) in curve:
                return float(curve[str(qty)])
            return _interp_ll(curve, qty)
    # Fallback to legacy engine
    leg = _legacy()
    curve = leg.get(paper, next(iter(leg.values()), {})) if leg else {}
    return _interp_ll(curve, qty)


def tiers(cash: float) -> dict:
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(model: str, paper: str, qty: int) -> float:
    area = _bag_area_m2(model)
    gsm = _PAPER_GSM.get(paper, 157)
    grams = area * gsm * float(qty)
    return round(grams / 1000.0 * WEIGHT_FACTOR, 3)


if __name__ == "__main__":
    plx = _plx()
    if plx.get("curves"):
        print("Using pricelist engine (exact)")
        for model in ["PBG 001", "PBG 003", "PBG 007"]:
            for lam in ["Gloss Lamination", "Matte Lamination + Spot UV"]:
                for q in [100, 500, 1000]:
                    p = cash_price(model, "Gloss Art Paper 157gsm", lam, q)
                    print(f"  {model} {lam[:8]} q{q}: RM{p:.2f}")
    else:
        print("No pricelist — using legacy curves")
