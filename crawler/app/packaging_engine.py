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
OPT_SAMPLES = OUT / "packaging_option_samples.json"
PARAMS = OUT / "packaging_params.json"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
REF_NA = 1200.0   # reference netarea of the option-sample boxes (~120×100×80) for scaling finishing
# material per-piece multipliers vs the default Gloss Art Card (M0024). Sampled where
# available; family-based estimates for materials the API rejected on the sampled boxes.
MAT_MULT_FALLBACK = {"M0024": 1.0, "M0001": 1.275, "M0003": 0.725, "M0006": 1.0, "M0007": 0.9,
                     "M0011": 1.232, "M0012": 1.15, "M0013": 1.063, "M0014": 1.35, "M0015": 1.4,
                     "M0103": 3.016, "M0106": 3.0, "M0109": 3.0, "M0021": 2.5}
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
        # 1) netarea from dims — FULL quadratic basis. netarea is a deterministic quadratic of the
        # box's flat unfold, so with aspect-diverse samples this fits it (near-)exactly, killing the
        # extrapolation blow-ups at unusual shapes (e.g. very wide boxes).
        Amat = np.column_stack([np.ones_like(L), L, W, D, L * W, W * D, L * D, L * L, W * W, D * D])
        n_coef, *_ = np.linalg.lstsq(Amat, na, rcond=None)
        # 2) total = setup(na) + perpiece(na)*qty, where each is CONCAVE in na (a + b*na + c*sqrt(na))
        # — real box cost grows sub-linearly with area, so a purely-linear na fit (dominated by the
        # big-box samples) overshoots small boxes ~15%. Fit RELATIVE error (weight 1/total) so small
        # and large boxes are balanced. t = [s0,s1,s2, p0,p1,p2].
        sq = np.sqrt(na)
        Tmat = np.column_stack([np.ones_like(na), na, sq, qty, na * qty, sq * qty])
        w = 1.0 / np.maximum(tot, 1.0)
        t_coef, *_ = np.linalg.lstsq(Tmat * w[:, None], tot * w, rcond=None)
        # 3) unit weight ~ w0 + w1*na
        w_coef, *_ = np.linalg.lstsq(np.column_stack([np.ones_like(na), na]), uw, rcond=None)
        params[box] = {"n": n_coef.tolist(), "t": t_coef.tolist(), "w": w_coef.tolist(),
                       "na_min": float(na.min()), "na_max": float(na.max())}
    out = {"boxes": params, "options": _calibrate_options()}
    PARAMS.write_text(json.dumps(out, indent=0))
    return out


def _calibrate_options():
    """Material per-piece multipliers + finishing additive deltas (setup + per-piece, the
    per-piece scaled by netarea/REF_NA). Print colour has no price effect (verified)."""
    opt = {"material": dict(MAT_MULT_FALLBACK), "finishing": {}, "ref_na": REF_NA}
    if not OPT_SAMPLES.exists():
        return opt
    o = json.loads(OPT_SAMPLES.read_text())

    def slope(key):
        by = {}
        for r in o.get(key, []):
            by.setdefault(r["box"], []).append((r["qty"], r["total"]))
        res = {}
        for box, pts in by.items():
            q = np.array([p[0] for p in pts], float); t = np.array([p[1] for p in pts], float)
            c, *_ = np.linalg.lstsq(np.column_stack([np.ones_like(q), q]), t, rcond=None)
            res[box] = (float(c[0]), float(c[1]))
        return res
    import statistics
    base = slope("base")
    for k in o:
        if k.startswith("mat:"):
            rs = slope(k); rats = [rs[b][1] / base[b][1] for b in rs if base.get(b) and base[b][1] > 0]
            if rats:
                opt["material"][k[4:]] = round(statistics.median(rats), 4)
        elif k.startswith("fin:"):
            rs = slope(k)
            ds = [rs[b][0] - base[b][0] for b in rs if base.get(b)]
            dp = [rs[b][1] - base[b][1] for b in rs if base.get(b)]
            if ds:
                opt["finishing"][k[4:]] = {"setup": round(statistics.median(ds), 2),
                                           "perpiece": round(statistics.median(dp), 5)}
    return opt


def _netarea(box, L, W, D, p):
    n = p["n"]
    na = (n[0] + n[1] * L + n[2] * W + n[3] * D + n[4] * (L * W)
          + n[5] * (W * D) + n[6] * (L * D) + n[7] * (L * L) + n[8] * (W * W) + n[9] * (D * D))
    # the quadratic can extrapolate to absurd (even negative) netarea for dim combos outside the
    # sampled grid — clamp to the box's sampled netarea band so price stays sane (bounded, not wild).
    lo, hi = p.get("na_min", 1.0), p.get("na_max", 1e9)
    return min(max(na, lo * 0.85), hi * 1.15)


def cash_price(box, L, W, D, qty, material="M0024", colour=4,
               coating="P021", addons=None, finishing=None):
    """Price a folding-carton box. coating = one mutually-exclusive surface coating
    (P021 gloss lam = the calibration baseline / no delta; or none/P022/P023/P024/P036).
    addons = a stackable list of add-on finishings (P033 spot UV / P031 hot stamp /
    P032 emboss) — their deltas SUM (verified additive vs the live API). `finishing` is a
    deprecated single-value alias."""
    fit = _fit(); p = fit["boxes"].get(box) if "boxes" in fit else fit.get(box)
    if not p:
        return 0.0
    na = _netarea(box, L, W, D, p)
    t = p["t"]
    sq = na ** 0.5
    setup = t[0] + t[1] * na + t[2] * sq
    perpiece = (t[3] + t[4] * na + t[5] * sq)
    opt = fit.get("options", {}) if "boxes" in fit else {}
    perpiece *= opt.get("material", {}).get(material, 1.0)   # board cost; colour has no effect
    cash = setup + perpiece * qty
    fdict = opt.get("finishing", {}); ref = opt.get("ref_na", 1200.0); scale = na / ref

    def _delta(key):
        f = fdict.get(key)
        return (f.get("setup", 0) + f.get("perpiece", 0) * scale * qty) if f else 0.0

    # back-compat: a single `finishing` maps to coating (if a swap) or an add-on
    al = list(addons or [])
    if finishing is not None:
        if finishing in fdict and finishing != "P021":
            coating = finishing
        elif finishing not in ("P021", "", None):
            al.append(finishing)
    # coating delta (P021 baseline = 0; none/P022/P023/P024/P036 are swap keys)
    if coating and coating != "P021":
        cash += _delta(coating)
    # stacked add-on deltas
    for a in al:
        cash += _delta("+" + a)
    return max(0.0, cash)


def tiers(cash):
    return {k: round(cash * (1 - d), 2) for k, d in TIER_DISCOUNTS.items()}


def weight_kg(box, L, W, D, qty):
    fit = _fit(); p = fit["boxes"].get(box) if "boxes" in fit else fit.get(box)
    if not p:
        return 0.0
    na = _netarea(box, L, W, D, p)
    uw = max(0.0, p["w"][0] + p["w"][1] * na)
    return round(uw * qty, 3)


if __name__ == "__main__":
    import statistics
    params = build_params()
    box_params = params.get("boxes", params)
    print(f"calibrated {len(box_params)} boxes -> {PARAMS.name}")
    # in-sample audit
    data = json.loads(SAMPLES.read_text())
    ins, loo = [], []
    for box, rows in data.items():
        rows = [r for r in rows if r.get("total") and r.get("netarea")]
        if box not in box_params or len(rows) < 6:
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
