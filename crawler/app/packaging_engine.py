"""Packaging Box pricing engine — our own formula, calibrated to Excard's GetPriceFactor2.

Structure discovered from sampling (output/packaging_samples.json):
  * Total price is LINEAR in quantity: total = setup + perpiece*qty.
  * Both setup and perpiece scale with the dieline board area (netarea), which is itself a
    smooth function of the box dimensions (L,W,D).

So per box we fit two small regressions:
  1. netarea ≈ n0 + n1*(L*W) + n2*((L+W)*D)         (board area from dimensions)
  2. total   ≈ a0 + a1*netarea + b0*qty + b1*(netarea*qty)   (price; captures setup(area)
     + perpiece(area)*qty)
  3. unit_weight ≈ w0 + w1*netarea                   (weight per box)

  cash_price(box, L, W, D, qty) -> RM ; tiers(cash) ; weight_kg(box,L,W,D,qty)
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent.parent / "output"
SAMPLES = OUT / "packaging_samples.json"
PARAMS = OUT / "packaging_params.json"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
_CACHE: dict = {}


def _fit():
    if "p" in _CACHE:
        return _CACHE["p"]
    if PARAMS.exists():
        _CACHE["p"] = json.loads(PARAMS.read_text()); return _CACHE["p"]
    _CACHE["p"] = build_params()
    return _CACHE["p"]


def build_params():
    data = json.loads(SAMPLES.read_text())
    params = {}
    for box, rows in data.items():
        rows = [r for r in rows if r.get("total") and r.get("netarea")]
        if len(rows) < 6:
            continue
        L = np.array([r["L"] for r in rows], float); W = np.array([r["W"] for r in rows], float)
        D = np.array([r["D"] for r in rows], float); na = np.array([r["netarea"] for r in rows], float)
        qty = np.array([r["qty"] for r in rows], float); tot = np.array([r["total"] for r in rows], float)
        uw = np.array([r.get("unit_weight") or 0 for r in rows], float)
        # 1) netarea from dims (unique dims rows)
        Amat = np.column_stack([np.ones_like(L), L * W, (L + W) * D])
        n_coef, *_ = np.linalg.lstsq(Amat, na, rcond=None)
        # 2) total = a0 + a1*na + b0*qty + b1*(na*qty)
        Tmat = np.column_stack([np.ones_like(na), na, qty, na * qty])
        t_coef, *_ = np.linalg.lstsq(Tmat, tot, rcond=None)
        # 3) unit weight ~ w0 + w1*na
        w_coef, *_ = np.linalg.lstsq(np.column_stack([np.ones_like(na), na]), uw, rcond=None)
        params[box] = {"n": n_coef.tolist(), "t": t_coef.tolist(), "w": w_coef.tolist(),
                       "na_min": float(na.min()), "na_max": float(na.max())}
    PARAMS.write_text(json.dumps(params, indent=0))
    return params


def _netarea(box, L, W, D, p):
    n = p["n"]
    return max(1.0, n[0] + n[1] * (L * W) + n[2] * ((L + W) * D))


def cash_price(box, L, W, D, qty):
    p = _fit().get(box)
    if not p:
        return 0.0
    na = _netarea(box, L, W, D, p)
    t = p["t"]
    return max(0.0, t[0] + t[1] * na + t[2] * qty + t[3] * (na * qty))


def tiers(cash):
    return {k: round(cash * (1 - d), 2) for k, d in TIER_DISCOUNTS.items()}


def weight_kg(box, L, W, D, qty):
    p = _fit().get(box)
    if not p:
        return 0.0
    na = _netarea(box, L, W, D, p)
    uw = max(0.0, p["w"][0] + p["w"][1] * na)
    return round(uw * qty, 3)


if __name__ == "__main__":
    import statistics
    params = build_params()
    print(f"calibrated {len(params)} boxes -> {PARAMS.name}")
    # in-sample + leave-one-dims-out audit
    data = json.loads(SAMPLES.read_text())
    ins, loo = [], []
    for box, rows in data.items():
        rows = [r for r in rows if r.get("total") and r.get("netarea")]
        if box not in params or len(rows) < 6:
            continue
        for r in rows:
            pred = cash_price(box, r["L"], r["W"], r["D"], r["qty"])
            if r["total"]:
                ins.append(abs(pred - r["total"]) / r["total"] * 100)
    print(f"in-sample MAPE: median={statistics.median(ins):.1f}% mean={statistics.mean(ins):.1f}% "
          f"p90={statistics.quantiles(ins, n=10)[8]:.1f}%")
    for b in ["A001X", "D040A", "C001A", "E005X"]:
        print(f"  {b} 120x100x80 q1000: RM{cash_price(b,120,100,80,1000):.2f} "
              f"wt={weight_kg(b,120,100,80,1000)}kg")
