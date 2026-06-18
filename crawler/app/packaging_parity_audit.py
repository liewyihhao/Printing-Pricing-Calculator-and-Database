"""Final parity audit: compare our packaging engine vs Excard's live GetPriceFactor2 on
RANDOM held-out configs (random dims within limits, random qty/material/finishing).

  python -m app.packaging_parity_audit [account] [n]
"""
from __future__ import annotations
import json, random, statistics, sys
from pathlib import Path
from .packaging_api import bootstrap_session
from . import packaging_engine as PE

OUT = Path(__file__).resolve().parent.parent / "output"
QTYS = [150, 250, 400, 750, 1500, 2500, 4000]
MATS = ["M0024", "M0001", "M0003", "M0013", "M0103"]
FINS = ["P021", "none", "P022", "P033", "P031"]


def run(account_id=1, n=50):
    lim = json.loads((OUT / "packaging_globals" / "boxPmsLimit.json").read_text())
    defaults = json.loads((OUT / "packaging_defaults.json").read_text())
    cat = [b["code"] for b in json.loads((OUT / "packaging_catalogue_ui.json").read_text())]
    PE._CACHE.clear()
    import copy
    SURFACE = {"P021", "P022", "P023", "P024", "P036"}
    pk = bootstrap_session(account_id)
    rng = random.Random(7); errs = []; rows = []
    for _ in range(n):
        box = rng.choice(cat)
        lm = lim.get(box, {})
        L = (lm.get("L") or [50])[0] + rng.choice([0, 30, 70, 120])
        W = (lm.get("W") or [50])[0] + rng.choice([0, 20, 50, 90])
        Darr = lm.get("D") or [50]; Dmax = Darr[2] if len(Darr) > 2 and Darr[2] else Darr[0] * 4
        D = min(Dmax, (Darr[0] or 50) + rng.choice([0, 20, 50, 100]))
        qty = rng.choice(QTYS); mat = rng.choice(MATS); fin = rng.choice(FINS)
        chain = copy.deepcopy(defaults.get(box, {}).get("ProcessJson"))
        if not chain:
            continue
        if fin == "none":
            chain = [p for p in chain if p.get("ID") not in SURFACE]
        elif fin in SURFACE:
            chain = [({"ID": fin} if p.get("ID") in SURFACE else p) for p in chain]
        else:  # add-on
            if not any(p.get("ID") == fin for p in chain):
                chain.append({"ID": fin})
        try:
            api = pk.price(box, L, W, D, [qty], material=mat, process=chain)
            truth = api[0]["total"] if api else None
        except Exception:
            truth = None
        if not truth:
            continue
        pred = PE.cash_price(box, L, W, D, qty, material=mat, finishing=fin)
        e = abs(pred - truth) / truth * 100
        errs.append(e); rows.append((box, f"{L}x{W}x{D}", qty, mat, fin, round(pred, 1), round(truth, 1), round(e, 1)))
    rows.sort(key=lambda r: -r[-1])
    print(f"PARITY vs live API: n={len(errs)} median={statistics.median(errs):.1f}% "
          f"mean={statistics.mean(errs):.1f}% p90={sorted(errs)[int(len(errs)*0.9)]:.1f}% "
          f"within10={sum(1 for e in errs if e<=10)/len(errs)*100:.0f}%")
    print("worst 8:", rows[:8])
    (OUT / "packaging_parity_audit.json").write_text(json.dumps(
        {"n": len(errs), "median": round(statistics.median(errs), 2),
         "within10": round(sum(1 for e in errs if e <= 10) / len(errs) * 100), "rows": rows}, indent=0))


if __name__ == "__main__":
    a = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    run(a, n)
