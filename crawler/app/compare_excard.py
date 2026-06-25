"""Purchaser comparison: OUR calculator price vs EXCARD official v4 price-list price.

The v4 price-list CSVs (output/v4_pricelists/<tag>.csv) are Excard's authoritative
online prices. Our standalone calculator + api both compute via pricelist_engine.cash_price
on the baked params. This walks every row of each CSV (a real spec + qty + Excard WM price),
computes our price for the same spec/qty, and reports the delta. At the listed order
quantities our exact-lookup products must match to the cent.
"""
from __future__ import annotations
import csv, json, statistics
from pathlib import Path
from app import pricelist_engine as PE

ROOT = Path(__file__).resolve().parent.parent
PL = ROOT / "output" / "v4_pricelists"

# tag -> (csv_name, price_col, axis_cols)
PRODUCTS = {
    "letterhead":    ("letterhead.csv", "WM Price", ["Paper", "Print Colour", "Packing"]),
    "pvccard":       ("pvc_card.csv",   "WMPrice",  ["Print Colour", "Hole Punch", "VDP"]),
    "folder":        ("folder.csv",     "WM Price", ["Model", "Paper", "Print Colour", "Lamination", "Colour Protective Layer"]),
    "money_packet":  ("money_packet_standard.csv", "WM Price", ["Model", "Package", "Paper", "Finishing"]),
}


def qcol_of(header):
    return next((c for c in header if c.strip().lower().startswith("quantity")), "Quantity")


def run():
    grand = []
    for tag, (csvname, pcol, axes) in PRODUCTS.items():
        params = json.load(open(ROOT / "output" / f"{tag}_pl_params.json", encoding="utf-8"))
        rows = list(csv.DictReader((PL / csvname).open(encoding="utf-8-sig")))
        header = rows[0].keys()
        qcol = qcol_of(header)
        deltas, worst, n, exact = [], (0, None), 0, 0
        for r in rows:
            q = (r.get(qcol) or "").strip().replace(",", "")
            if not q.isdigit() or len(q) > 7:
                continue
            try:
                excard = float((r.get(pcol) or "").replace(",", ""))
            except ValueError:
                continue
            if excard <= 0:
                continue
            cfg = {a: (r.get(a) or "").strip() for a in axes}
            ours = PE.cash_price(params, cfg, int(q))
            d = ours - excard
            pct = 100 * d / excard
            deltas.append(abs(pct))
            n += 1
            if abs(d) < 0.005:
                exact += 1
            if abs(d) > abs(worst[0]):
                worst = (d, (cfg, int(q), excard, ours))
        med = statistics.median(deltas) if deltas else 0
        mx = max(deltas) if deltas else 0
        print(f"\n=== {tag} ({n} priced rows) ===")
        print(f"  exact-to-cent matches : {exact}/{n}  ({100*exact/n:.1f}%)")
        print(f"  |error| median        : {med:.4f}%   max: {mx:.4f}%")
        if abs(worst[0]) >= 0.005:
            cfg, q, ex, ou = worst[1]
            print(f"  worst row: {cfg} qty={q}  excard={ex}  ours={ou}  d={worst[0]:+.2f}")
        grand.append((tag, n, exact, med, mx))
    print("\n================ SUMMARY ================")
    print(f"{'product':14} {'rows':>6} {'exact%':>8} {'medErr%':>9} {'maxErr%':>9}")
    for tag, n, exact, med, mx in grand:
        print(f"{tag:14} {n:6d} {100*exact/n:7.1f}% {med:8.4f}% {mx:8.4f}%")


if __name__ == "__main__":
    run()
