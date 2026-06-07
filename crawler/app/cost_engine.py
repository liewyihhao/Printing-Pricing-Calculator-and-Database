"""Printoka pure-formula cost engine — Litho Offset Loose Sheet / Flyer.

No data lookups at runtime: price is computed from print economics. Parameters
are CALIBRATED against Excard (reference only) and frozen into printoka_params.json.

  cash = margin * ( plate_rate*plates + setup
                    + (paper_RM[cat]*piece_m2*gsm/1000 + ink_rate*plates*piece_m2)
                      * qty**gamma )

  plates  = colours_per_side * sides      (4C+4C = 8, 4C+0 = 4, 1C+0 = 1 ...)
  gamma   < 1  -> economies of scale (per-unit price falls with quantity)
Weight  = piece_m2 * gsm * qty / 1000 * WEIGHT_FACTOR   (physics)
"""
from __future__ import annotations
import re, json
import numpy as np
from pathlib import Path

CATS = ["Simili", "Gloss Art Paper", "Matte Art Paper", "Gloss Art Card"]
PARAMS_FILE = Path(__file__).resolve().parent.parent / "output" / "printoka_params.json"
WEIGHT_FACTOR = 1.2065
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}


def cat_of(p):
    for i, c in enumerate(CATS):
        if c.lower() in p.lower():
            return i
    return 0


def area_m2(size_label):
    m = re.search(r"(\d+)\s*mm\s*x\s*(\d+)\s*mm", size_label)
    return (int(m.group(1)) * int(m.group(2))) / 1e6 if m else 0.0


def gsm_of(p):
    m = re.search(r"(\d+)\s*gsm", p)
    return int(m.group(1)) if m else 128


def plates_of(colour_side):
    colours = 4 if colour_side.startswith("4C") else 1
    sides = 2 if "Both" in colour_side else 1
    return colours * sides


def _predict(p, a, gsm, plates, qty, cat):
    plate_rate, setup, margin, gamma, ink_rate = p[:5]
    paper = np.array(p[5:9])[cat]
    unit = paper * a * gsm / 1000.0 + ink_rate * plates * a
    return margin * (plate_rate * plates + setup + unit * np.power(qty, gamma))


def cash_price(size, paper_label, colour_side, qty, params=None):
    if params is None:
        params = load_params()
    return float(_predict(np.array(params), np.array([area_m2(size)]),
                          np.array([gsm_of(paper_label)]),
                          np.array([plates_of(colour_side)]),
                          np.array([qty]), np.array([cat_of(paper_label)]))[0])


def breakdown(size, paper_label, colour_side, qty, params=None):
    if params is None:
        params = load_params()
    plate_rate, setup, margin, gamma, ink_rate = params[:5]
    a = area_m2(size); g = gsm_of(paper_label); pl = plates_of(colour_side)
    paper = params[5:9][cat_of(paper_label)]
    paper_unit = paper * a * g / 1000.0
    ink_unit = ink_rate * pl * a
    var = (paper_unit + ink_unit) * (qty ** gamma)
    fixed = plate_rate * pl + setup
    cash = margin * (fixed + var)
    return {"plates": pl, "fixed_plate_setup": round(margin * fixed, 2),
            "variable": round(margin * var, 2), "gamma": round(gamma, 3),
            "cash": round(cash, 2)}


def load_params():
    if PARAMS_FILE.exists():
        return json.loads(PARAMS_FILE.read_text())["params"]
    raise RuntimeError("Not calibrated — run: python -m app.cost_engine")


def calibrate_and_report():
    from scipy.optimize import differential_evolution
    from .db import session_scope
    from .models import OrderWork, OrderQuote
    from sqlalchemy import select
    rng = np.random.default_rng(7)
    rows, keys = [], []
    with session_scope() as s:
        works = {w.id: w for w in s.scalars(select(OrderWork).where(OrderWork.package == "Normal")).all()}
        for q in s.scalars(select(OrderQuote).where(OrderQuote.before_discount != None)).all():
            w = works.get(q.order_work_id)
            if not w:
                continue
            a = area_m2(w.size_label); c = float(q.before_discount)
            if a == 0 or c < 1:
                continue
            rows.append((a, gsm_of(w.paper_label), plates_of(w.colour_side), q.quantity,
                         cat_of(w.paper_label), c))
            keys.append((w.size_label, w.paper_label, w.colour_side))
    A = np.array(rows, float)
    a, g, pl, qty, cat, cash = A[:, 0], A[:, 1], A[:, 2], A[:, 3], A[:, 4].astype(int), A[:, 5]
    uniq = list({k for k in keys}); rng.shuffle(uniq)
    hold = set(uniq[: max(1, len(uniq)//5)])
    tr = np.array([i for i, k in enumerate(keys) if k not in hold])
    te = np.array([i for i, k in enumerate(keys) if k in hold])

    def loss(p):
        pred = _predict(p, a[tr], g[tr], pl[tr], qty[tr], cat[tr])
        return float(np.median(np.abs(pred - cash[tr]) / cash[tr]))  # robust

    bounds = [(3, 120), (0, 200), (1.0, 3.0), (0.4, 1.0), (0, 50),
              (1, 18), (1, 18), (1, 18), (1, 18)]
    res = differential_evolution(loss, bounds, maxiter=200, popsize=25, tol=1e-6,
                                 seed=7, workers=1, polish=True)
    p = res.x

    def stat(name, idx):
        pred = _predict(p, a[idx], g[idx], pl[idx], qty[idx], cat[idx])
        e = np.abs(pred - cash[idx]) / cash[idx] * 100
        print(f"{name}: n={len(idx)} MAPE {e.mean():.1f}% median {np.median(e):.1f}% "
              f"<=3% {(e<=3).mean()*100:.0f}% <=5% {(e<=5).mean()*100:.0f}% "
              f"<=10% {(e<=10).mean()*100:.0f}% under {(pred<cash[idx]).mean()*100:.0f}%")

    print(f"params: plate={p[0]:.1f} setup={p[1]:.1f} margin={p[2]:.2f} gamma={p[3]:.3f} "
          f"ink={p[4]:.2f} paper(RM/kg)={[round(x,1) for x in p[5:]]}")
    stat("TRAIN", tr)
    stat("TEST 20% holdout (unseen configs)", te)
    PARAMS_FILE.write_text(json.dumps({"params": list(p), "cats": CATS}, indent=1))
    print(f"saved -> {PARAMS_FILE}")


if __name__ == "__main__":
    calibrate_and_report()
