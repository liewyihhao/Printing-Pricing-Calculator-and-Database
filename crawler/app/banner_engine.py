"""Banner (Litho) pricing engine. Fixed material. Drivers: size (10 fixed) x qty (1-300).
Price = per-size log-log qty curve.

  cash_price(size, qty) -> RM
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "banner_samples.json"
PARAMS = OUT / "banner_params.json"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
MATERIAL_GSM = 400   # solvent-printed vinyl/tarpaulin estimate

SIZES = ["3ft x 2ft", "4ft x 2ft", "6ft x 2ft", "4ft x 3ft", "8ft x 3ft",
         "10ft x 3ft", "18ft x 3ft", "8ft x 4ft", "10ft x 4ft", "20ft x 4ft"]

_CACHE: dict = {}
FT_TO_M = 0.3048


def _ft_dims(size_str: str) -> tuple[float, float]:
    parts = size_str.lower().replace("ft", "").split("x")
    return float(parts[0].strip()) * FT_TO_M, float(parts[1].strip()) * FT_TO_M


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
    curve = curves.get(size) or {}
    return _interp_ll(curve, qty)


def tiers(cash: float) -> dict:
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(size: str, qty: int) -> float:
    w, h = _ft_dims(size)
    grams = w * h * MATERIAL_GSM * float(qty)
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
    p = {"curves": _curves(), "sizes": SIZES, "material_gsm": MATERIAL_GSM,
         "ft_to_m": FT_TO_M, "weight_factor": WEIGHT_FACTOR}
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    loo = loo_audit()
    if loo:
        med = sorted(loo.values())[len(loo)//2]
        print(f"Banner LOO median: {med}%")
        for s, e in list(loo.items())[:3]:
            print(f"  {s}: {e}%")
    curves = _curves()
    for size in list(SIZES)[:3]:
        for q in [1, 10, 100]:
            print(f"{size} q{q}: RM{round(cash_price(size, q), 2)} wt={weight_kg(size, q)}kg")
