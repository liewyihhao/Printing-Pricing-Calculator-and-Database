"""Wall Calendar (Litho) pricing engine. Fixed spec; price = QUANTITY curve (log-log).

  cash_price(qty) -> RM
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "wallcal_samples.json"
PARAMS = OUT / "wallcal_params.json"
SIZE_MM = (260, 265)
CONTENT_SHEETS = 12
CONTENT_GSM = 60
BACK_GSM = 300
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"core": []}
    return _CACHE["d"]


def _curve():
    return {str(r["qty"]): r["cash"] for r in _data().get("core", [])}


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


def cash_price(qty):
    return _interp_ll(_curve(), qty)


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(qty):
    w, h = SIZE_MM
    grams = (w * h / 1e6) * (BACK_GSM + CONTENT_SHEETS * CONTENT_GSM)
    return round(grams * float(qty) / 1000.0 * WEIGHT_FACTOR, 3)


def build_params():
    p = {"curve": _curve(), "size_mm": SIZE_MM, "content_sheets": CONTENT_SHEETS,
         "content_gsm": CONTENT_GSM, "back_gsm": BACK_GSM, "weight_factor": WEIGHT_FACTOR}
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    for q in [1000, 5000, 18000]:
        print(f"q{q}: RM{round(cash_price(q), 2)} wt={weight_kg(q)}kg")
