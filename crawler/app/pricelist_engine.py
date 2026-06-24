"""Generic price-list lookup engine.

Builds an EXACT pricing model directly from an Excard v4 price-list CSV export
(output/v4_pricelists/<tag>.csv). The model is a lookup keyed by the product's
option axes -> {qty: WM_price}, with log-log qty interpolation between the listed
order quantities (prices are exact AT the listed quantities).

Params file output/<tag>_pl_params.json:
  {"axis_cols": [...], "qty_col": "...", "price_col": "WM Price",
   "curves": {"<axisval1>|<axisval2>|...": {"<qty>": price}}, "note": "..."}

  cash_price(params, config: dict, qty) -> RM   (config maps axis_col -> value)
"""
from __future__ import annotations
import csv, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
PL = OUT / "v4_pricelists"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}


def _interp_ll(curve: dict, qty) -> float:
    pts = sorted((int(q), c) for q, c in curve.items())
    if not pts:
        return 0.0
    if len(pts) == 1:
        return pts[0][1]
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


def _key(config: dict, axis_cols) -> str:
    return "|".join(str(config.get(c, "")) for c in axis_cols)


def cash_price(params: dict, config: dict, qty) -> float:
    cv = params["curves"]
    key = _key(config, params["axis_cols"])
    curve = cv.get(key)
    if curve is None:                      # fall back to first curve sharing the leading axes
        pref = key.split("|")[0]
        curve = next((c for k, c in cv.items() if k.startswith(pref)), None) or next(iter(cv.values()), {})
    return round(_interp_ll(curve, qty), 2)


def tiers(cash: float) -> dict:
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def build_params(tag: str, axis_cols, qty_col="Quantity", price_col="WM Price",
                 note="", csv_name=None) -> dict:
    """Parse the CSV and emit the lookup params. Drops the DataTables filter junk row
    (the one whose qty cell is a concatenation, not a plain integer)."""
    f = PL / (csv_name or f"{tag}.csv")
    rows = list(csv.DictReader(f.open(encoding="utf-8-sig")))
    curves: dict = {}
    qcol = next((c for c in rows[0] if c.strip().lower().startswith(qty_col.lower())), qty_col)
    pcol = next((c for c in rows[0] if c.strip() == price_col), price_col)
    used_axes = [next((c for c in rows[0] if c.strip() == a), a) for a in axis_cols]
    for r in rows:
        q = (r.get(qcol) or "").strip().replace(",", "")
        if not q.isdigit():
            continue
        try:
            price = float((r.get(pcol) or "").replace(",", ""))
        except ValueError:
            continue
        if price <= 0:
            continue
        key = "|".join((r.get(c) or "").strip() for c in used_axes)
        curves.setdefault(key, {})[q] = price
    p = {"axis_cols": axis_cols, "qty_col": qty_col, "price_col": price_col,
         "curves": curves, "note": note}
    (OUT / f"{tag}_pl_params.json").write_text(json.dumps(p))
    return p


if __name__ == "__main__":
    import sys
    tag = sys.argv[1]
    p = build_params(tag, sys.argv[2].split(",") if len(sys.argv) > 2 else [])
    print(f"{tag}: {len(p['curves'])} config curves")
