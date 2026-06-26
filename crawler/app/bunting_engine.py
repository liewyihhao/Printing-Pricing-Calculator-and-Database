"""Bunting (Litho) pricing engine. Drivers: size(3) x paper(2) x qty(1-300).

  cash_price(size, paper, qty) -> RM
  build_params() -> writes output/bunting_params.json
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "bunting_samples.json"
PARAMS = OUT / "bunting_params.json"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
FT_TO_M = 0.3048

SIZES = ["2ft x 5ft", "2ft x 6ft", "2.5ft x 6ft"]
PAPERS = ["Tarpaulin 300gsm", "Synthetic Paper 180micron"]
_PAPER_GSM = {"Tarpaulin 300gsm": 300, "Synthetic Paper 180micron": 180}
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"data": []}
    return _CACHE["d"]


def _ft_dims(size_str: str) -> tuple[float, float]:
    parts = size_str.lower().replace("ft", "").split("x")
    w = float(parts[0].strip()); h = float(parts[1].strip())
    return w * FT_TO_M, h * FT_TO_M


def _curves() -> dict[tuple[str, str], dict]:
    curves: dict[tuple, dict] = {}
    for r in _data().get("data", []):
        key = (r["size"], r["paper"])
        curves.setdefault(key, {})[str(r["qty"])] = r["cash"]
    return curves


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


def cash_price(size: str, paper: str, qty: int) -> float:
    curves = _curves()
    curve = curves.get((size, paper))
    if curve is None:
        return 0.0  # unsampled combination (e.g. Synthetic Paper — headless deferred)
    return _interp_ll(curve, qty)


def tiers(cash: float) -> dict:
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(size: str, paper: str, qty: int) -> float:
    w_m, h_m = _ft_dims(size)
    gsm = _PAPER_GSM.get(paper, 300)
    grams = w_m * h_m * gsm * float(qty)
    return round(grams / 1000.0 * WEIGHT_FACTOR, 3)


def loo_audit() -> dict[str, float]:
    curves = _curves(); errs = {}
    for key, curve in curves.items():
        pts = sorted((int(q), c) for q, c in curve.items())
        if len(pts) < 3:
            continue
        e = []
        for i in range(len(pts)):
            rest = {str(q): c for j, (q, c) in enumerate(pts) if j != i}
            pred = _interp_ll(rest, pts[i][0])
            e.append(abs(pred - pts[i][1]) / pts[i][1] * 100)
        e.sort()
        errs[str(key)] = round(e[len(e)//2], 2)
    return errs


def build_params():
    raw = _curves()
    serialised = {f"{size}|{paper}": curve for (size, paper), curve in raw.items()}
    p = {
        "curves": serialised,
        "sizes": SIZES,
        "papers": PAPERS,
        "paper_gsm": _PAPER_GSM,
        "weight_factor": WEIGHT_FACTOR,
    }
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    loo = loo_audit()
    for key, e in sorted(loo.items()):
        print(f"{key}: LOO {e}%")
    for size in SIZES:
        for paper in PAPERS[:1]:
            for q in [1, 10, 50, 100, 300]:
                print(f"{size} {paper[:8]} q{q}: RM{round(cash_price(size, paper, q), 2)} wt={weight_kg(size, paper, q)}kg")
