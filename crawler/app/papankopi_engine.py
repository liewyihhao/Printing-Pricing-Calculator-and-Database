"""Papan Kopi / Sachet Board (Litho) pricing engine. Drivers: size(3) x qty.

  cash_price(size, qty) -> RM
  build_params() -> writes output/papankopi_params.json
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "papankopi_samples.json"
PARAMS = OUT / "papankopi_params.json"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065

SIZES = ["537mm x 334mm", "622mm x 346mm", "547mm x 346mm"]
# Board is typically 300gsm grey board with lamination
BOARD_GSM = 1200  # heavy board
_SIZE_DIMS_MM = {
    "537mm x 334mm": (537, 334),
    "622mm x 346mm": (622, 346),
    "547mm x 346mm": (547, 346),
}
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"data": []}
    return _CACHE["d"]


def _curves() -> dict[str, dict]:
    curves: dict[str, dict] = {}
    for r in _data().get("data", []):
        curves.setdefault(r["size"], {})[str(r["qty"])] = r["cash"]
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


def cash_price(size: str, qty: int) -> float:
    curves = _curves()
    curve = curves.get(size) or next(iter(curves.values()), {})
    return _interp_ll(curve, qty)


def tiers(cash: float) -> dict:
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(size: str, qty: int) -> float:
    dims = _SIZE_DIMS_MM.get(size, (537, 334))
    w_m = dims[0] / 1000.0; h_m = dims[1] / 1000.0
    grams = w_m * h_m * BOARD_GSM * float(qty)
    return round(grams / 1000.0 * WEIGHT_FACTOR, 3)


def loo_audit() -> dict[str, float]:
    curves = _curves(); errs = {}
    for size, curve in curves.items():
        pts = sorted((int(q), c) for q, c in curve.items())
        if len(pts) < 3:
            continue
        e = []
        for i in range(len(pts)):
            rest = {str(q): c for j, (q, c) in enumerate(pts) if j != i}
            pred = _interp_ll(rest, pts[i][0])
            e.append(abs(pred - pts[i][1]) / pts[i][1] * 100)
        e.sort()
        errs[size] = round(e[len(e)//2], 2)
    return errs


def build_params():
    p = {
        "curves": _curves(),
        "sizes": SIZES,
        "size_dims_mm": _SIZE_DIMS_MM,
        "board_gsm": BOARD_GSM,
        "weight_factor": WEIGHT_FACTOR,
    }
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    loo = loo_audit()
    for size, e in loo.items():
        print(f"{size}: LOO {e}%")
    for size in SIZES:
        for q in [100, 500, 1000, 3000]:
            print(f"{size} q{q}: RM{round(cash_price(size, q), 2)} wt={weight_kg(size, q)}kg")
