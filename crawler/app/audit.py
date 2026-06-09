"""HONEST accuracy audit: compare each Printoka engine to Excard ground truth on
>=60% of available samples. No bluffing — reports median, %within 5/10%, and the
worst offenders that exceed 10% so we can fix them.

Ground truth:
  - business_card : LIVE v4 API (fresh random configs + RANDOM quantities -> tests
    real interpolation, not the stored breakpoints)
  - digital(50), booklet(19/37) : stored Excard samples (output/*_samples_*.json)
  - litho(21) : NO stored raw prices (OrderQuote was deleted) -> needs re-sampling;
    reported as 'no ground truth available' rather than a fabricated number.

    python -m app.audit            # audit all (uses stored samples; bizcard via API)
    python -m app.audit --frac 0.6
"""
from __future__ import annotations
import json, random, sys
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent.parent / "output"


def _stats(name, errs, preds, acts):
    e = np.array(errs)
    over = [(round(p, 2), round(a, 2), round(x, 1)) for p, a, x in
            sorted(zip(preds, acts, errs), key=lambda t: -t[2]) if x > 10][:8]
    r = {"product": name, "n": len(e), "median": round(float(np.median(e)), 2),
         "mean_mape": round(float(e.mean()), 2),
         "within_5pct": round(float((e <= 5).mean() * 100), 1),
         "within_10pct": round(float((e <= 10).mean() * 100), 1),
         "max": round(float(e.max()), 1), "worst_over_10pct": over}
    print(f"\n=== {name} (n={r['n']}, {int(FRAC*100)}% sample) ===")
    print(f"  median {r['median']}%  | within 5%: {r['within_5pct']}%  | "
          f"within 10%: {r['within_10pct']}%  | worst {r['max']}%")
    if over:
        print(f"  configs OVER 10% (pred, excard, err%): {over[:5]}")
    return r


def audit_digital(frac):
    from . import digital_engine as E
    data = [d for d in json.loads((OUT / "spot_samples_50.json").read_text()) if d.get("cash")]
    random.shuffle(data); data = data[:max(1, int(len(data) * frac))]
    errs, preds, acts = [], [], []
    for d in data:
        p = E.cash_price(d["size"], d["paper"], d["colour"], d["qty"])
        errs.append(abs(p - d["cash"]) / d["cash"] * 100); preds.append(p); acts.append(d["cash"])
    return _stats("Loose Sheet — Digital (50)", errs, preds, acts)


def audit_booklet(pid, frac):
    """Honest test for the per-config-curve engine = held-out QUANTITIES (interpolation).
    Build curves from train quantities only, then predict the held-out quantities so the
    curve must INTERPOLATE (not memorise). Mirrors how custom quantities are priced."""
    import math
    from . import booklet_engine as E
    data = [d for d in json.loads((OUT / f"booklet_samples_{pid}.json").read_text()) if d.get("cash")]
    TEST_Q = {300, 1000, 4000, 9000} if pid == 19 else {30, 100, 250, 400}
    train = [d for d in data if int(d["qty"]) not in TEST_Q]
    test = [d for d in data if int(d["qty"]) in TEST_Q]
    random.shuffle(test); test = test[:max(1, int(len(test) * frac))]
    # build curves from TRAIN only
    curves = {}
    for d in train:
        k = E._curve_key(d["size"], d["page"], d["ordertype"], d["binding"],
                         d["cover_paper"], d["content_paper"], d["content_colour"])
        curves.setdefault(k, {})[str(int(d["qty"]))] = math.log(d["cash"])
    errs, preds, acts = [], [], []
    for d in test:
        k = E._curve_key(d["size"], d["page"], d["ordertype"], d["binding"],
                         d["cover_paper"], d["content_paper"], d["content_colour"])
        c = curves.get(k)
        if c and len(c) >= 2:
            p = math.exp(E._interp_log(c, d["qty"]))
        else:
            p = E.cash_price(d["size"], d["page"], d["ordertype"], d["binding"], d["cover_paper"],
                             d["content_paper"], d["content_colour"], d["qty"], product_id=pid)
        errs.append(abs(p - d["cash"]) / d["cash"] * 100); preds.append(p); acts.append(d["cash"])
    lab = "Litho (19)" if pid == 19 else "Digital (37)"
    return _stats(f"Booklet — {lab} [curve, held-out qty]", errs, preds, acts)


def audit_bizcard(frac):
    """Fresh LIVE test vs v4 API at RANDOM quantities (real interpolation test)."""
    from . import bizcard_engine as E
    from .bizcard_api import make_spec, price
    from .bizcard_sampler import CARDTYPES, PAPERS, PLASTIC_PAPER
    LBL = {"standard": "Standard", "thin_fold": "Thin Fold", "fat_fold": "Fat Fold",
           "custom_die_cut": "Custom Die-Cut", "plastic_card": "Plastic Card"}
    rng = random.Random(7)
    jobs = []
    for key, (od, sizes, colours, custom) in CARDTYPES.items():
        papers = [PLASTIC_PAPER] if key == "plastic_card" else PAPERS
        for size in sizes:
            for paper in papers:
                for colour in colours:
                    jobs.append((key, od, size, paper, colour, custom))
    rng.shuffle(jobs); jobs = jobs[:max(1, int(len(jobs) * frac))]
    errs, preds, acts = [], [], []
    for (key, od, size, paper, colour, custom) in jobs:
        qty = rng.choice([175, 275, 550, 650, 1250, 1750, 3250, 5250, 7250, 8750])  # truly unsampled
        act = price(make_spec(OrderDesc=od, Size=size, Paper=paper, PrintColour=colour,
                              Lamination="", Quantity=str(qty),
                              IsCustomSize=("true" if custom else "false")))
        if not act:
            continue
        p = E.cash_price(key, size, paper, colour, qty)
        errs.append(abs(p - act) / act * 100); preds.append(p); acts.append(act)
    return _stats("Business Card (1) — LIVE API, interpolation", errs, preds, acts)


FRAC = 0.6


def main():
    global FRAC
    if "--frac" in sys.argv:
        FRAC = float(sys.argv[sys.argv.index("--frac") + 1])
    random.seed(7)
    reports = []
    reports.append(audit_bizcard(FRAC))
    reports.append(audit_digital(FRAC))
    reports.append(audit_booklet(19, FRAC))
    reports.append(audit_booklet(37, FRAC))
    print("\n=== Loose Sheet — Litho (21) ===")
    print("  NO ground truth: OrderQuote prices were deleted; needs re-sampling to audit honestly.")
    reports.append({"product": "Loose Sheet — Litho (21)", "n": 0,
                    "note": "no stored ground truth — re-sample required"})
    (OUT / "audit_report.json").write_text(json.dumps(reports, indent=1))
    print("\nsaved -> output/audit_report.json")
    # Summary of which meet <=10% on the bulk
    print("\n--- PASS (<=10% on >=90% of sample)? ---")
    for r in reports:
        if r.get("n"):
            ok = r["within_10pct"] >= 90
            print(f"  {'PASS' if ok else 'FAIL'} {r['product']}: {r['within_10pct']}% within 10%")


if __name__ == "__main__":
    main()
