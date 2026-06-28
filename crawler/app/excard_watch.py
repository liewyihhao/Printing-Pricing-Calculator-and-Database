"""Change watcher: detect what changed on the source site between two captured snapshots.

A snapshot is a directory of <slug>_options.json files (the same format produced by the
capture extractor). Compares a BASELINE dir (e.g. output/v4_options) against a FRESH dir
and reports, per product:
  - NEW / REMOVED products
  - NEW / REMOVED option dimensions (e.g. a whole new 'Finishing' axis)
  - NEW / REMOVED option values  (new finishing, new sizes, new colours; removed options)
  - PRICE INCREASES / DECREASES  (per config + quantity, with %)
  - NEW / REMOVED option images

Usage:
    python -m app.excard_watch <baseline_dir> <fresh_dir> [--json report.json]
"""
from __future__ import annotations
import json
import sys
from pathlib import Path


def _load_dir(d: Path) -> dict:
    out = {}
    for f in sorted(d.glob("*_options.json")):
        slug = f.name[:-len("_options.json")]
        try:
            out[slug] = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return out


def _price_index(snap: dict) -> dict:
    """(config_key, qty) -> price, from embedded WMPrice curves (if present)."""
    cv = snap.get("curves") or {}
    idx = {}
    for key, curve in cv.items():
        for q, p in curve.items():
            try:
                idx[(key, str(q))] = float(p)
            except (TypeError, ValueError):
                pass
    return idx


def diff_product(base: dict, fresh: dict) -> dict:
    rep = {}
    bdims = {c: set(base.get("distinct", {}).get(c, [])) for c in base.get("optionCols", [])}
    fdims = {c: set(fresh.get("distinct", {}).get(c, [])) for c in fresh.get("optionCols", [])}
    new_dims = [c for c in fdims if c not in bdims]
    rem_dims = [c for c in bdims if c not in fdims]
    if new_dims:
        rep["new_dimensions"] = {c: sorted(fdims[c]) for c in new_dims}
    if rem_dims:
        rep["removed_dimensions"] = {c: sorted(bdims[c]) for c in rem_dims}
    new_vals, rem_vals = {}, {}
    for c in bdims.keys() & fdims.keys():
        added = sorted(fdims[c] - bdims[c])
        gone = sorted(bdims[c] - fdims[c])
        if added:
            new_vals[c] = added
        if gone:
            rem_vals[c] = gone
    if new_vals:
        rep["new_values"] = new_vals
    if rem_vals:
        rep["removed_values"] = rem_vals
    # images
    bimg = set((base.get("imageOptions") or {}).keys())
    fimg = set((fresh.get("imageOptions") or {}).keys())
    if fimg - bimg:
        rep["new_images"] = sorted(fimg - bimg)
    if bimg - fimg:
        rep["removed_images"] = sorted(bimg - fimg)
    # prices
    bp, fp = _price_index(base), _price_index(fresh)
    ups, downs = [], []
    for k in bp.keys() & fp.keys():
        old, new = bp[k], fp[k]
        if old > 0 and abs(new - old) / old > 0.005:
            row = {"config": k[0], "qty": k[1], "old": round(old, 2), "new": round(new, 2),
                   "pct": round(100 * (new - old) / old, 2)}
            (ups if new > old else downs).append(row)
    if ups:
        rep["price_increases"] = sorted(ups, key=lambda r: -r["pct"])
    if downs:
        rep["price_decreases"] = sorted(downs, key=lambda r: r["pct"])
    return rep


def diff_snapshots(baseline_dir: str, fresh_dir: str) -> dict:
    base = _load_dir(Path(baseline_dir))
    fresh = _load_dir(Path(fresh_dir))
    report = {"baseline": baseline_dir, "fresh": fresh_dir,
              "new_products": sorted(set(fresh) - set(base)),
              "removed_products": sorted(set(base) - set(fresh)),
              "changed": {}}
    for slug in sorted(set(base) & set(fresh)):
        d = diff_product(base[slug], fresh[slug])
        if d:
            report["changed"][slug] = d
    return report


def render(report: dict) -> str:
    L = ["# Source change report", f"_baseline `{report['baseline']}`  vs  fresh `{report['fresh']}`_", ""]
    if report["new_products"]:
        L.append(f"## 🆕 New products ({len(report['new_products'])})")
        L += [f"- {s}" for s in report["new_products"]] + [""]
    if report["removed_products"]:
        L.append(f"## ❌ Removed products ({len(report['removed_products'])})")
        L += [f"- {s}" for s in report["removed_products"]] + [""]
    if not report["changed"]:
        L.append("_No option or price changes on existing products._")
    for slug, d in report["changed"].items():
        L.append(f"## {slug}")
        for dim, vals in (d.get("new_dimensions") or {}).items():
            L.append(f"- ➕ NEW option category **{dim}**: {', '.join(vals[:8])}")
        for dim, vals in (d.get("removed_dimensions") or {}).items():
            L.append(f"- ➖ REMOVED option category **{dim}**")
        for dim, vals in (d.get("new_values") or {}).items():
            L.append(f"- ➕ new **{dim}**: {', '.join(vals)}")
        for dim, vals in (d.get("removed_values") or {}).items():
            L.append(f"- ➖ removed **{dim}**: {', '.join(vals)}")
        for r in (d.get("price_increases") or [])[:10]:
            L.append(f"- 🔺 price +{r['pct']}%  ({r['config']} @ {r['qty']}): {r['old']} → {r['new']}")
        for r in (d.get("price_decreases") or [])[:5]:
            L.append(f"- 🔻 price {r['pct']}%  ({r['config']} @ {r['qty']}): {r['old']} → {r['new']}")
        ni = len(d.get("price_increases") or [])
        if ni > 10:
            L.append(f"  …and {ni-10} more price increases")
        L.append("")
    return "\n".join(L)


def diff_catalogue(base_path: str, fresh_path: str) -> dict:
    """Catalogue/promotion diff from two menu snapshots (lists of product objects with fields
    like 'product', 'promo_msg', 'isnew', 'ishot', 'ispromo'). Detects new/removed products and
    promotion changes (a product gaining, changing, or ending a promo message)."""
    def load(p):
        objs = json.loads(Path(p).read_text(encoding="utf-8"))
        return {o.get("product") or o.get("url"): o for o in objs if (o.get("product") or o.get("url"))}
    b, f = load(base_path), load(fresh_path)
    rep = {"new_products": sorted(set(f) - set(b)), "removed_products": sorted(set(b) - set(f)),
           "new_promotions": [], "changed_promotions": [], "ended_promotions": []}
    for name in b.keys() & f.keys():
        bp = (b[name].get("promo_msg") or "").strip()
        fp = (f[name].get("promo_msg") or "").strip()
        if fp and not bp:
            rep["new_promotions"].append({"product": name, "promo": fp})
        elif bp and not fp:
            rep["ended_promotions"].append({"product": name, "was": bp})
        elif fp and bp and fp != bp:
            rep["changed_promotions"].append({"product": name, "old": bp, "new": fp})
    return rep


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    rep = diff_snapshots(sys.argv[1], sys.argv[2])
    if "--json" in sys.argv:
        out = sys.argv[sys.argv.index("--json") + 1]
        Path(out).write_text(json.dumps(rep, indent=2), encoding="utf-8")
        print("wrote", out)
    print(render(rep))
