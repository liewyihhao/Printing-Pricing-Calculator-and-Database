"""Calibrate + validate the Printoka pure formula on a large representative sample.

Reads the price backup (output/orderquotes_backup.json) joined to the kept combos,
splits by CONFIG (so the test set is unseen combos), calibrates the cost engine on
train, and reports the held-out accuracy with breakdowns. Saves a KPI report the
dashboard reads. The runtime engine stays pure formula (no price lookups).
"""
import json
import numpy as np
from collections import defaultdict
from scipy.optimize import differential_evolution
from pathlib import Path
from . import cost_engine as CE
from .db import session_scope
from .models import OrderWork
from sqlalchemy import select

OUT = Path(__file__).resolve().parent.parent / "output"


def run():
    backup = json.loads((OUT / "orderquotes_backup.json").read_text())
    with session_scope() as s:
        works = {w.id: (w.size_label, w.paper_label, w.colour_side, w.package)
                 for w in s.scalars(select(OrderWork)).all()}
    rows, keys = [], []
    for r in backup:
        w = works.get(r["order_work_id"])
        if not w or r["before_discount"] is None:
            continue
        size, paper, colour, pkg = w
        if pkg != "Normal":
            continue
        a = CE.area_m2(size)
        if a == 0 or r["before_discount"] < 1:
            continue
        rows.append((a, CE.gsm_of(paper), CE.plates_of(colour), r["quantity"],
                     CE.cat_of(paper), float(r["before_discount"]), paper, size))
        keys.append((size, paper, colour, pkg))
    A = np.array([x[:6] for x in rows], float)
    a, g, pl, qty, cat, cash = (A[:, i] for i in range(6))
    cat = cat.astype(int); qty = qty.astype(float)
    papers = [x[6] for x in rows]; sizes = [x[7] for x in rows]

    rng = np.random.default_rng(7)
    uniq = list({k for k in keys}); rng.shuffle(uniq)
    hold = set(uniq[: max(1, len(uniq) // 4)])      # 25% configs held out
    tr = np.array([i for i, k in enumerate(keys) if k not in hold])
    te = np.array([i for i, k in enumerate(keys) if k in hold])
    print(f"sample: {len(rows)} price points across {len(uniq)} configs "
          f"(train {len(tr)} / test {len(te)})")

    def loss(p):
        pred = CE._predict(p, a[tr], g[tr], pl[tr], qty[tr], cat[tr])
        return float(np.median(np.abs(pred - cash[tr]) / cash[tr]))

    bounds = [(3, 120), (0, 200), (1.0, 3.0), (0.4, 1.0), (0, 50),
              (1, 18), (1, 18), (1, 18), (1, 18)]
    res = differential_evolution(loss, bounds, maxiter=200, popsize=25, tol=1e-6,
                                 seed=7, workers=1, polish=True)
    p = res.x
    CE.PARAMS_FILE.write_text(json.dumps({"params": list(p), "cats": CE.CATS}, indent=1))

    pred = CE._predict(p, a[te], g[te], pl[te], qty[te], cat[te])
    ape = np.abs(pred - cash[te]) / cash[te] * 100
    under = (pred < cash[te]).mean() * 100
    def pct(t): return round(float((ape <= t).mean() * 100), 1)
    report = {"test": "held-out configs (25%)", "sample_points": len(rows),
              "test_points": int(len(te)), "configs": len(uniq),
              "mape": round(float(ape.mean()), 2), "median": round(float(np.median(ape)), 2),
              "within_3pct": pct(3), "within_5pct": pct(5), "within_10pct": pct(10),
              "under_predict_pct": round(float(under), 1)}
    print("HELD-OUT ACCURACY:", json.dumps(report))

    # breakdown by paper category and size (where is it good/bad?)
    bycat = defaultdict(list); bysize = defaultdict(list)
    for i, e in zip(te, ape):
        bycat[CE.CATS[cat[i]]].append(e); bysize[sizes[i]].append(e)
    report["by_paper"] = {k: round(float(np.median(v)), 1) for k, v in bycat.items()}
    report["by_size"] = {k: round(float(np.median(v)), 1) for k, v in sorted(bysize.items())}
    print("median error by paper:", report["by_paper"])
    print("median error by size :", report["by_size"])
    (OUT / "spot_test_report.json").write_text(json.dumps(report, indent=1))
    print("saved -> output/spot_test_report.json")


if __name__ == "__main__":
    run()
