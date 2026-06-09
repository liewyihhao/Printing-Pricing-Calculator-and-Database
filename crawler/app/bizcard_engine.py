"""Printoka formula engine — BUSINESS CARD (v4 product).

Business card uses offset gang-up + best-seller-quantity promo pricing, so cash is
NOT a smooth function of quantity (q500/q1000 are discounted; q400/q6000–9000
spike). A smooth area×gsm formula caps ~18% median. Instead we fit a SEPARABLE
multiplicative model in log-space (calibrated coefficients, no runtime API lookup):

  cash = exp( paper_coef[paper] + colour_coef[colour] + M[cardType|size][qty] )

paper_coef/colour_coef are scalars per option; M is a per-(cardType,size) quantity
curve. For arbitrary quantity we log-linearly interpolate M between Excard's
breakpoints (exactly how the real ladder behaves). For a custom die-cut size we use
the nearest sampled size's curve and area-scale. Calibrated on bizcard_samples.json.

  python -m app.bizcard_engine        # fit + held-out report
"""
from __future__ import annotations
import json, re, math
import numpy as np
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
PARAMS = OUT / "bizcard_params.json"
SAMPLES = OUT / "bizcard_samples.json"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065


def _paper_key(paper: str) -> str:
    return re.sub(r"\s*\(.*?\)", "", paper).strip()


def gsm_of(paper: str) -> int:
    m = re.search(r"(\d+)\s*gsm", paper)
    return int(m.group(1)) if m else (300 if "micron" in paper.lower() else 250)


def dims(size: str):
    m = re.search(r"(\d+)\s*mm\s*x\s*(\d+)\s*mm", size)
    return (int(m.group(1)), int(m.group(2))) if m else (54, 89)


def _size_key(size: str) -> str:
    w, h = dims(size)
    return f"{w}x{h}"


# ---------------- prediction ----------------
def _ckey(card_type, size, paper, colour):
    return f"{card_type}|{_size_key(size)}|{_paper_key(paper)}|{colour}"


def cash_price(card_type, size, paper, colour, qty, params=None) -> float:
    """Per-config quantity curve (Excard's exact ladder), log-linearly interpolated
    for arbitrary quantities. Custom-die-cut sizes fall back to the nearest sampled
    size of the same paper/colour and are area-scaled."""
    if params is None:
        params = load_params()
    curves = params["curves"]
    key = _ckey(card_type, size, paper, colour)
    area_adj = 0.0
    if key not in curves:
        w, h = dims(size); area = w * h
        suffix = f"|{_paper_key(paper)}|{colour}"
        cand = [k for k in curves if k.startswith(card_type + "|") and k.endswith(suffix)]
        if not cand:
            cand = [k for k in curves if k.startswith(card_type + "|")] or list(curves)
        def karea(k):
            ww, hh = k.split("|")[1].split("x"); return int(ww) * int(hh)
        key = min(cand, key=lambda k: abs(karea(k) - area))
        area_adj = math.log(max(area, 1) / max(karea(key), 1))
    curve = curves[key]  # {qty: log(cash)}
    qs = sorted(int(q) for q in curve)
    m = _interp(qs, [curve[str(q)] for q in qs], float(qty))
    return float(math.exp(m + area_adj))


def _interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            t = (x - xs[i-1]) / (xs[i] - xs[i-1])
            return ys[i-1] + t * (ys[i] - ys[i-1])
    return ys[-1]


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(size, paper, qty):
    w, h = dims(size)
    return round((w * h / 1e6) * gsm_of(paper) * qty / 1000.0 * WEIGHT_FACTOR, 3)


def load_params():
    if PARAMS.exists():
        return json.loads(PARAMS.read_text())
    raise RuntimeError("Business card not calibrated — run: python -m app.bizcard_engine")


# ---------------- fit (per-config quantity curves) ----------------
def _build_curves(data):
    curves: dict = {}
    for r in data:
        curves.setdefault(_ckey(r["cardType"], r["size"], r["paper"], r["colour"]),
                          {})[str(int(r["qty"]))] = math.log(r["cash"])
    return curves


def calibrate_and_report():
    data = [r for r in json.loads(SAMPLES.read_text()) if r.get("cash")]
    # Final params: full per-config quantity curves (exact at Excard breakpoints).
    params = {"curves": _build_curves(data)}
    PARAMS.write_text(json.dumps(params, indent=1))

    # Honest generalization test = held-out QUANTITIES (the only thing the formula
    # extrapolates, since every selectable option-combo is sampled). Rebuild curves
    # WITHOUT a set of test quantities, then interpolate them and measure error.
    TEST_Q = {400, 700, 2000, 4000, 7000, 9000}
    train = [r for r in data if int(r["qty"]) not in TEST_Q]
    test = [r for r in data if int(r["qty"]) in TEST_Q]
    p_tr = {"curves": _build_curves(train)}
    pred = np.array([cash_price(r["cardType"], r["size"], r["paper"], r["colour"],
                                r["qty"], p_tr) for r in test])
    act = np.array([r["cash"] for r in test])
    e = np.abs(pred - act) / act * 100
    print(f"sampled configs={len(params['curves'])}  points={len(data)}")
    print(f"AT BREAKPOINTS: exact (median 0%) — every sampled qty is stored.")
    print(f"INTERPOLATED (held-out qtys {sorted(TEST_Q)}): n={len(test)} "
          f"MAPE {e.mean():.1f}% median {np.median(e):.1f}% "
          f"<=3% {(e<=3).mean()*100:.0f}% <=5% {(e<=5).mean()*100:.0f}% "
          f"<=10% {(e<=10).mean()*100:.0f}%")
    (OUT / "spot_test_report_bizcard.json").write_text(json.dumps({
        "product": "business_card",
        "test": "held-out quantities (interpolation); option-combos all sampled",
        "sample_points": len(data),
        "median": round(float(np.median(e)), 2),
        "within_3pct": round(float((e <= 3).mean() * 100)),
        "within_5pct": round(float((e <= 5).mean() * 100)),
        "within_10pct": round(float((e <= 10).mean() * 100)),
        "mape": round(float(e.mean()), 2),
        "method": "per-config quantity curve + log interpolation"}, indent=1))
    print("saved -> bizcard_params.json + spot_test_report_bizcard.json")


if __name__ == "__main__":
    calibrate_and_report()
