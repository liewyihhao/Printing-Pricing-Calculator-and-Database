"""Wobbler (Digital) pricing engine. Drivers: orient(2) x paper(2) x lam(2) x qty.
Finishing: Round Cornering and Digital Die-Cut priced as delta from base.

  cash_price(orient, paper, lam, qty, finishing="-") -> RM
  build_params() -> writes output/wobbler_params.json
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "wobbler_samples.json"
PARAMS = OUT / "wobbler_params.json"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065

ORIENTS = ["Portrait", "Landscape"]
PAPERS = ["Gloss Art Card 250gsm", "Gloss Art Card 310gsm"]
_PAPER_GSM = {"Gloss Art Card 250gsm": 250, "Gloss Art Card 310gsm": 310}
LAMS = ["Matte Lamination (Front)", "Gloss Lamination (Front)"]
FINISHINGS = ["-", "Round Cornering (R6),4,1", "Digital Die-cutting,0,0"]
# Wobbler standard size: ~9.5cm × 21cm (DL-ish)
WOBBLER_W_M = 0.095; WOBBLER_H_M = 0.21
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"core": [], "finish": []}
    return _CACHE["d"]


def _curves() -> dict[tuple, dict]:
    curves: dict = {}
    for r in _data().get("core", []):
        key = (r["orient"], r["paper"], r["lam"])
        curves.setdefault(key, {})[str(r["qty"])] = r["cash"]
    return curves


def _finish_deltas() -> dict[str, dict]:
    ref_key = ("Portrait", "Gloss Art Card 250gsm", "Matte Lamination (Front)")
    ref_curves = _curves()
    ref_curve = ref_curves.get(ref_key, {})
    deltas: dict[str, dict] = {}
    for r in _data().get("finish", []):
        rc = r["rc"]
        q = str(r["qty"])
        base = _interp_ll(ref_curve, r["qty"])
        deltas.setdefault(rc, {})[q] = r["cash"] - base
    return deltas


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


def _interp_linear(delta_curve: dict, qty: float) -> float:
    pts = sorted((int(q), d) for q, d in delta_curve.items())
    if not pts:
        return 0.0
    if qty <= pts[0][0]:
        return pts[0][1]
    if qty >= pts[-1][0]:
        return pts[-1][1]
    for i in range(1, len(pts)):
        if qty <= pts[i][0]:
            t = (qty - pts[i-1][0]) / (pts[i][0] - pts[i-1][0])
            return pts[i-1][1] + t * (pts[i][1] - pts[i-1][1])
    return pts[-1][1]


def cash_price(orient: str, paper: str, lam: str, qty: int, finishing: str = "-") -> float:
    curves = _curves()
    curve = curves.get((orient, paper, lam))
    if curve is None:
        curve = next(iter(curves.values()), {})
    base = _interp_ll(curve, qty)
    if finishing and finishing != "-":
        deltas = _finish_deltas()
        delta = _interp_linear(deltas.get(finishing, {}), qty)
        base += delta
    return max(base, 0.0)


def tiers(cash: float) -> dict:
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(paper: str, qty: int) -> float:
    gsm = _PAPER_GSM.get(paper, 250)
    grams = WOBBLER_W_M * WOBBLER_H_M * gsm * float(qty)
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
    serialised = {f"{o}|{p}|{l}": curve for (o, p, l), curve in raw.items()}
    p = {
        "curves": serialised,
        "orients": ORIENTS,
        "papers": PAPERS,
        "lams": LAMS,
        "finishings": FINISHINGS,
        "paper_gsm": _PAPER_GSM,
        "wobbler_w_m": WOBBLER_W_M, "wobbler_h_m": WOBBLER_H_M,
        "weight_factor": WEIGHT_FACTOR,
        "finish_deltas": {rc: dict(d) for rc, d in _finish_deltas().items()},
    }
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    loo = loo_audit()
    for key, e in sorted(loo.items()):
        print(f"{key}: LOO {e}%")
    for paper in PAPERS[:1]:
        for q in [50, 100, 500, 1000]:
            print(f"Portrait {paper[:20]} Matte q{q}: RM{round(cash_price('Portrait', paper, LAMS[0], q), 2)}")
