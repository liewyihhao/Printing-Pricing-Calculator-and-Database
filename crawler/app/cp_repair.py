"""Re-validate + repair CheckPrice-sampled option files that were collected at high
concurrency (workers>=4) and are therefore partly underpriced (~0.787x) — see memory
checkprice-concurrency-corruption. For each registered product we rebuild the exact API
spec from the stored curve KEY (keys already hold API-format axis values), detect points
sitting below a robust per-curve Theil-Sen trend, and re-fetch ONLY those SEQUENTIALLY
(workers=1 = no session overlap = clean), taking the higher (true) value. Then rewrites the
options file so the next build is exact.

  python -m app.cp_repair business-card [--validate-only] [--samples 120]
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path
from app import checkprice_enum as C
from app.voucher_cp_sampler import _get_session_cookie

OUT = Path(__file__).resolve().parent.parent / "output"


# ---- per-product API spec builders (key parts are already API-format) ----
def _bizcard_spec(parts, qty):
    size, paper, colour, lam, pkg = parts
    return {"Product": "Business Card", "OrderDesc": "Standard", "Size": size, "Orientation": "Landscape",
            "Paper": paper, "Package": pkg, "PrintColour": colour, "Quantity": str(qty), "Lamination": lam,
            "HotStamping": "", "HotStampingColour": "", "HotStampingBlock": "", "RoundCorner": "", "HolePunch": "",
            "Embossing": "", "Folding": "", "FoldCode": "", "Country": "99", "Courier": "DEFAULT",
            "CountryZone": "West Malaysia"}


def _kadkahwin_spec(parts, qty):
    from app import kadkahwin_sampler as KK
    size, paper, colour = parts
    return {"Product": "Kad Kahwin", "Size": KK._size(size), "Paper": KK._paper(paper), "OrderDesc": "Standard",
            "PrintColour": colour, "Quantity": str(qty), "Lamination": "", "FoldCode": "", "HotStamping": "",
            "HotStampingSize1": "N/A", "HotStampingSize2": "N/A", "Envelope": "", "Country": "99",
            "Courier": "DEFAULT", "CountryZone": "West Malaysia"}


REG = {
    "business-card": {"type": "Business Card", "spec": _bizcard_spec},
    "kad-kahwin": {"type": "Kad Kahwin", "spec": _kadkahwin_spec},
}


def _theilsen_suspects(curve: dict, thresh: float = 0.90):
    pts = sorted((int(q), p) for q, p in curve.items() if p)
    if len(pts) < 4:
        return []
    xs = [math.log(q) for q, _ in pts]; ys = [math.log(p) for _, p in pts]
    slopes = sorted((ys[j] - ys[i]) / (xs[j] - xs[i])
                    for i in range(len(xs)) for j in range(i + 1, len(xs)) if xs[j] != xs[i])
    slope = slopes[len(slopes) // 2]
    inters = sorted(ys[i] - slope * xs[i] for i in range(len(xs)))
    inter = inters[len(inters) // 2]
    return [str(q) for (q, p), x in zip(pts, xs) if p / math.exp(inter + slope * x) < thresh]


def validate(slug, n=120):
    import random
    reg = REG[slug]
    d = json.loads((OUT / "v4_options" / f"{slug}_options.json").read_text(encoding="utf-8"))
    curves = {k: v for k, v in d["curves"].items() if v}
    cookie = _get_session_cookie()
    keys = random.sample(list(curves), min(n, len(curves)))
    bad = 0
    for k in keys:
        parts = k.split("|")
        qtys = sorted(curves[k], key=int); q = qtys[len(qtys) // 2]
        stored = curves[k][q]
        got = C._fetch(reg["type"], reg["spec"](parts, q), cookie)
        if got and got > stored * 1.005:      # live higher => stored was corrupted (underpriced)
            bad += 1
            if bad <= 12:
                print(f"  CORRUPT {k} q={q}: stored={stored} live={got} ({got/stored:.4f}x)", file=sys.stderr)
    print(f"{slug} validate: {bad}/{len(keys)} stored points underpriced", file=sys.stderr)
    return bad


def repair(slug, passes=6):
    reg = REG[slug]
    f = OUT / "v4_options" / f"{slug}_options.json"
    d = json.loads(f.read_text(encoding="utf-8"))
    curves = d["curves"]
    cookie = _get_session_cookie()
    total = 0
    for it in range(passes):
        suspects = [(k, q) for k, cur in curves.items() if cur for q in _theilsen_suspects(cur)]
        if not suspects:
            print(f"pass {it}: clean", file=sys.stderr); break
        print(f"pass {it}: {len(suspects)} suspects, re-fetching sequentially...", file=sys.stderr)
        fixed = 0
        for k, q in suspects:
            got = C._fetch(reg["type"], reg["spec"](k.split("|"), q), cookie)
            if got and got > curves[k][q]:
                curves[k][q] = got; fixed += 1
        total += fixed
        # keep priceMeta rows fresh
        d["rows"] = sum(len(c) for c in curves.values() if c)
        f.write_text(json.dumps(d))
        print(f"  fixed {fixed}/{len(suspects)}", file=sys.stderr)
        if fixed == 0:
            break
    print(f"{slug} repair done: {total} points fixed", file=sys.stderr)


if __name__ == "__main__":
    slug = sys.argv[1]
    if "--validate-only" in sys.argv:
        validate(slug)
    else:
        validate(slug)
        repair(slug)
        validate(slug)
