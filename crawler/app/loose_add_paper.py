"""Add a newly-offered Loose Sheet — Litho (21) paper to the EXACT pricelist
(output/v4_options/loose-sheet-litho_options.json). id21 is a pricelist product with axes
size|paper|lamination|colour and curve value = total cash, sampled from devv2 /Product/CheckPrice
(type="Loose Sheet", PrintMethod="Litho"). We sample the new paper across each size's valid
lamination×colour set (per the file's deps) and splice the curves + distinct + deps in.

  python -m app.loose_add_paper "Gloss Art Paper 80gsm - Best Seller (NEW)"
"""
from __future__ import annotations
import json, re, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from app import checkprice_enum as C
from app import voucher_cp_sampler as V
from app.loose_resample import _size_api, _paper_api, _spec

OUT = Path(__file__).resolve().parent.parent / "output"
OPTS = OUT / "v4_options" / "loose-sheet-litho_options.json"


def _spec_lam(size_api, paper_api, colour, lam, qty):
    s = _spec(size_api, paper_api, colour, qty)
    s["Lamination"] = "" if lam == "Not Required" else lam     # empty == Not Required (verified)
    return s


def run(paper_label, max_workers=2):
    d = json.loads(OPTS.read_text(encoding="utf-8"))
    curves = d["curves"]
    deps = d["deps"]
    qtys = sorted({int(q) for c in curves.values() for q in c})
    paper_api = _paper_api(paper_label)
    cookie = V._get_session_cookie()

    tasks = []
    for size, dep in deps.items():
        sa = _size_api(size)
        if not sa:
            continue
        for lam in dep.get("lamination", []):
            for colour in dep.get("colour", []):
                for q in qtys:
                    tasks.append((size, lam, colour, q, _spec_lam(sa, paper_api, colour, lam, q)))
    print(f"add '{paper_label}': {len(tasks)} CheckPrice calls", file=sys.stderr)

    got = {}                       # (size,lam,colour) -> {qty: cash}
    done = fail = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(C._fetch, "Loose Sheet", s, cookie): (sz, lam, cl, q)
                for sz, lam, cl, q, s in tasks}
        for fu in as_completed(futs):
            sz, lam, cl, q = futs[fu]; p = fu.result(); done += 1
            if p:
                got.setdefault((sz, lam, cl), {})[str(q)] = p
            else:
                fail += 1
            if done % 500 == 0:
                print(f"  {done}/{len(tasks)} ({fail} none)", file=sys.stderr)

    # splice curves + distinct + deps
    added = 0
    valid_sizes = set()
    for (sz, lam, cl), curve in got.items():
        if len(curve) >= 2:
            curves[f"{sz}|{paper_label}|{lam}|{cl}"] = curve
            added += 1
            valid_sizes.add(sz)
    if paper_label not in d["distinct"]["paper"]:
        d["distinct"]["paper"].append(paper_label)
    for sz in valid_sizes:
        pl = deps[sz].setdefault("paper", [])
        if paper_label not in pl:
            pl.append(paper_label)
    d["priceMeta"]["nCurves"] = len(curves)
    d["rows"] = sum(len(c) for c in curves.values())
    OPTS.write_text(json.dumps(d))
    print(f"add: +{added} curves ({fail} none of {done}) across {len(valid_sizes)} sizes; wrote {OPTS.name}",
          file=sys.stderr)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "Gloss Art Paper 80gsm - Best Seller (NEW)")
