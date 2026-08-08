"""One-off repair: re-insert the two uncommitted price-curve additions that were only ever present
in the working-tree v4_options files (never committed) and were lost on a `git checkout --` revert:

  - Business Card  "Soft Touch Lamination (Both)"        (bizcard_softtouch.py, CheckPrice-sampled)
  - Loose Sheet    "Gloss Art Paper 80gsm - Best Seller (NEW)"  (loose_add_paper.py, CheckPrice)

Both are fully recoverable, exactly, from the COMMITTED calculator_data.json — its embedded
params (data['params']['bizcard_plx'] / ['loosesheet_plx']) already carry the built curves, and for
both products axisCols has NO dropped internal axes, so the params curve key == the v4_options
curve key verbatim. We splice those curves + distinct value + deps entries back into the source
v4_options files (appending the new option last, matching the committed field order) so a fresh
build reproduces the committed catalogue. Verified afterwards by diffing rebuilt params vs committed.
"""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
V4 = OUT / "v4_options"


def _committed_params():
    raw = subprocess.run(
        ["git", "show", "HEAD:crawler/output/calculator_data.json"],
        capture_output=True, text=True, encoding="utf-8", cwd=OUT.parent.parent,
    ).stdout
    return json.loads(raw)["params"]


def _splice(slug, param_tag, dim, new_value):
    """Add every committed curve whose `dim` axis == new_value into the v4_options source file,
    plus the distinct + deps entries. Appends new_value last in distinct[dim]."""
    f = V4 / f"{slug}_options.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    axis_cols = d["priceMeta"]["axisCols"]
    dim_idx = axis_cols.index(dim)
    params = _committed_params()[param_tag]
    # sanity: no dropped axes ⇒ key formats identical
    assert params["axis_cols"] == axis_cols, (params["axis_cols"], axis_cols)

    added = 0
    primary = d.get("primary")
    prim_idx = axis_cols.index(primary) if primary in axis_cols else None
    for key, curve in params["curves"].items():
        parts = key.split("|")
        if parts[dim_idx] != new_value:
            continue
        if key not in d["curves"]:
            d["curves"][key] = curve
            added += 1
        # deps: make new_value valid under its primary value
        if prim_idx is not None and d.get("deps"):
            pv = parts[prim_idx]
            slot = d["deps"].setdefault(pv, {}).setdefault(dim, [])
            if new_value not in slot:
                slot.append(new_value)
    # distinct: append last (matches committed field option order)
    dl = d["distinct"].setdefault(dim, [])
    if new_value not in dl:
        dl.append(new_value)
    d["priceMeta"]["nCurves"] = len(d["curves"])
    f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    print(f"{slug}: +{added} curves for {dim}={new_value!r}; nCurves={len(d['curves'])}")


def main():
    _splice("business-card", "bizcard_plx", "Lamination", "Soft Touch Lamination (Both)")
    _splice("loose-sheet-litho", "loosesheet_plx", "paper", "Gloss Art Paper 80gsm - Best Seller (NEW)")


if __name__ == "__main__":
    main()
