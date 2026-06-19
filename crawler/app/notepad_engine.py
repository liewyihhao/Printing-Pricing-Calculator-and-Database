"""Notepad (Litho) pricing engine.

Fixed-spec product (Size 80x106mm, content Simili 80gsm 40 sheets, 4C+4C cover / 1C
content, Wire-O punch compulsory). Price model (from output/notepad_samples.json):
  * Price depends ONLY on QUANTITY (books). VERIFIED on the live form: cover paper
    (260gsm vs 310gsm) and lamination (Matte Both vs + Spot UV Front Cover) do NOT change
    the online price (266g & Spot UV are block/included). So one qty curve, log-interp,
    exact at Excard's order quantities. Paper only changes the WEIGHT estimate.

  cash_price(paper, qty, lamination) -> RM
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "notepad_samples.json"
PARAMS = OUT / "notepad_params.json"

SIZE_MM = (80, 106)        # fixed notepad size
CONTENT_SHEETS = 40
CONTENT_GSM = 80           # Simili 80gsm
COVER_GSM = {"260": 260, "310": 310}
LAM_BASE = "Matte Lamination (Both)"
LAM_UV = "Matte Lamination (Both) + Spot UV (Front Cover)"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"core": [], "spotuv": []}
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


def _curve():
    """Single qty->cash curve (paper/lamination verified price-neutral online)."""
    if "c" in _CACHE:
        return _CACHE["c"]
    cv: dict = {}
    for r in _data().get("core", []):
        cv[str(r["qty"])] = r["cash"]   # 260 == 310; either populates the curve
    _CACHE["c"] = cv
    return cv


def cash_price(paper=None, qty=0, lamination=LAM_BASE):
    return _interp(_curve(), qty)


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(paper, qty):
    w, h = SIZE_MM
    area = (w * h) / 1e6
    cover_gsm = 310 if "310" in (paper or "") else 260
    grams_per_book = area * (cover_gsm + CONTENT_SHEETS * CONTENT_GSM)
    return round(grams_per_book * float(qty) / 1000.0 * WEIGHT_FACTOR, 3)


def build_params():
    p = {"curve": _curve(), "size_mm": SIZE_MM, "content_sheets": CONTENT_SHEETS,
         "content_gsm": CONTENT_GSM, "weight_factor": WEIGHT_FACTOR}
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    print("notepad params written.")
    for q in [250, 750, 1000, 5000, 12000]:
        print(f"  q{q}: RM{round(cash_price(qty=q), 2)} wt(260)={weight_kg('260', q)}kg")
