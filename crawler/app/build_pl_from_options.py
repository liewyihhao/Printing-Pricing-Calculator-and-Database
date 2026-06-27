"""KPI2: build an exact price-lookup params from a captured v4_options file's embedded
WMPrice curves. Keys by the user-selectable option axes (drops non-option/internal axes
like DeliveryFee, Compulsory, IsAlQuran); residual collisions from any hidden axis are
averaged (transparent, like the Folder CD-Jacket case). Returns (params, price_axes, ncollide)."""
import json
from collections import defaultdict
from pathlib import Path
from app.build_standalone import _is_skip_col, _norm
OUT = Path(__file__).resolve().parent.parent / "output"
_INTERNAL = {"isalquran"}


def build(slug, tag, exclude_names=()):
    d = json.loads((OUT / "v4_options" / f"{slug}_options.json").read_text(encoding="utf-8"))
    pm = d["priceMeta"]; cv = d["curves"]; axes = pm["axisCols"]
    exc = {_norm(x) for x in exclude_names}
    def drop(a):
        return _is_skip_col(a) or _norm(a) in _INTERNAL or _norm(a) in exc
    keep = [i for i, a in enumerate(axes) if not drop(a)]
    price_axes = [axes[i] for i in keep]
    agg = defaultdict(list)
    for k, curve in cv.items():
        av = k.split("|"); nk = "|".join(av[i] for i in keep)
        for q, p in curve.items():
            agg[(nk, q)].append(float(p))
    curves = defaultdict(dict); ncol = 0
    for (nk, q), ps in agg.items():
        if max(ps) - min(ps) > 0.01:
            ncol += 1
        curves[nk][q] = round(sum(ps) / len(ps), 2)
    params = {"axis_cols": price_axes, "qty_col": pm["qtyCol"], "price_col": pm["priceCol"],
              "curves": curves, "note": f"{slug}: exact lookup from captured WM price curves."}
    (OUT / f"{tag}_params.json").write_text(json.dumps(params))
    return params, price_axes, ncol


if __name__ == "__main__":
    import sys
    excl = sys.argv[3].split(",") if len(sys.argv) > 3 else ()
    p, ax, c = build(sys.argv[1], sys.argv[2], excl)
    print(f"{sys.argv[2]}: axes={ax} curves={len(p['curves'])} ambiguous_configs={c}")
