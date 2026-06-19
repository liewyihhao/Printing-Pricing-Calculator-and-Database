"""Letterhead (Litho) pricing engine.

Fixed size A4 (210x297mm). Price model (from output/letterhead_samples.json):
  * Per-config QUANTITY CURVE keyed (paper|colour), log-interpolated over qty.
    Exact at Excard's order quantities; nearest-colour / cheapest fallback otherwise.

  cash_price(paper, colour, qty) -> RM
"""
from __future__ import annotations
import json, math, re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "letterhead_samples.json"
PARAMS = OUT / "letterhead_params.json"

SIZE_MM = (210, 297)
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"core": []}
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


def _curves():
    if "c" in _CACHE:
        return _CACHE["c"]
    cv: dict = {}
    for r in _data().get("core", []):
        np = "Conqueror" if "Conqueror" in r["paper"] else r["paper"]
        cv.setdefault(f"{np}|{r['colour']}", {})[str(r["qty"])] = r["cash"]
    _CACHE["c"] = cv
    return cv


def _norm_paper(paper):
    """The 4 Conqueror 100gsm variants are price-identical — map to the one sampled."""
    if paper and "Conqueror" in paper:
        return "Conqueror"
    return paper


def cash_price(paper, colour, qty):
    cv = _curves()
    np = _norm_paper(paper)
    key = f"{np}|{colour}"
    if key not in cv:  # fall back: same paper any colour, else any
        key = next((k for k in cv if k.startswith(f"{np}|")), None) or next(iter(cv), None)
    if not key:
        return 0.0
    return _interp(cv[key], qty)


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(paper, qty):
    w, h = SIZE_MM
    m = re.search(r"(\d+)\s*gsm", paper or "")
    gsm = int(m.group(1)) if m else 100
    return round((w * h / 1e6) * gsm * float(qty) / 1000.0 * WEIGHT_FACTOR, 3)


def build_params():
    p = {"curves": _curves(), "size_mm": SIZE_MM, "weight_factor": WEIGHT_FACTOR}
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    cv = _curves()
    print(f"letterhead params: {len(cv)} curves")
    for k in list(cv)[:3]:
        for q in [100, 1000, 5000]:
            p, c = k.split("|")
            print(f"  {p[:18]} {c} q{q}: RM{round(cash_price(p, c, q), 2)} wt={weight_kg(p, q)}kg")
