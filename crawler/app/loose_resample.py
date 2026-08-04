"""Loose Sheet — Litho (21): verify our stored curves against current CheckPrice, and add newly-
offered papers (e.g. "Gloss Art Paper 80gsm - Best Seller (NEW)") by sampling them the same way.

Loose Sheet uses devv2 /Product/CheckPrice (type="Loose Sheet", PrintMethod="Litho"). Our curves
store log(cash) keyed size|paper|colour; the cascade (valid size→paper→colour→packages) is derived
from the sampled combos. Prices are per Excard's own engine, so specs+combos+price all match.

  python -m app.loose_resample verify              # compare stored vs live CheckPrice
  python -m app.loose_resample add "<paper label>" # sample a new paper across the grid
"""
from __future__ import annotations
import json, re, sys, random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from app import checkprice_enum as C
from app import voucher_cp_sampler as V

OUT = Path(__file__).resolve().parent.parent / "output"
SPOT = OUT / "spot_samples_21.json"


def _size_api(size_label):
    """'A3 (297mm x 420mm)' -> '297mm x 420mm'; 'Others' has no dims (custom, skip)."""
    m = re.search(r"\(([^)]+)\)", size_label)
    return m.group(1).replace("×", "x").strip() if m else None


def _paper_api(paper_label):
    """Strip our marketing suffixes to Excard's CheckPrice paper value."""
    return re.sub(r"\s*-\s*Best Seller.*$|\s*\(NEW\)\s*$", "", paper_label).strip()


def _spec(size_api, paper_api, colour, qty, pkg="Normal"):
    return {"Product": "Loose Sheet", "PrintMethod": "Litho", "Size": size_api, "Paper": paper_api,
            "CoatSide": "0", "Quantity": str(qty), "PrintColour": colour, "SpotColourFront": "",
            "SpotColourBack": "", "Lamination": "", "Package": pkg, "creasingLine": "0", "FoldCode": "",
            "HolePunch": "", "RoundCorner": "", "HotStamping": "", "HotStampingSize1": "",
            "HotStampingColour1": "", "HotStampingSize2": "", "HotStampingColour2": "", "EnvelopCode": "",
            "PerforationLine": "0", "PerforationSize": "", "IsCreasing": "False", "IsFolding": "False",
            "IsHandFold": "False", "Country": "99", "Courier": "Default"}


def _axes():
    """Sizes, colours, qtys present in our current samples (the grid Excard prices on)."""
    rows = json.loads(SPOT.read_text(encoding="utf-8"))
    sizes = [s for s in dict.fromkeys(r["size"] for r in rows) if _size_api(s)]
    colours = list(dict.fromkeys(r["colour"] for r in rows))
    qtys = sorted({int(r["qty"]) for r in rows})
    return rows, sizes, colours, qtys


def verify(n=14):
    import math
    curves = json.loads((OUT / "loose_curve_21.json").read_text(encoding="utf-8"))
    cookie = V._get_session_cookie()
    keys = [k for k in curves if _size_api(k.split("|")[0])]
    random.seed(3); random.shuffle(keys)
    errs = []
    for k in keys[:n]:
        size, paper, colour = k.split("|")
        q = random.choice(list(curves[k]))
        live = C._fetch("Loose Sheet", _spec(_size_api(size), _paper_api(paper), colour, q), cookie)
        stored = math.exp(curves[k][q])
        if live:
            e = abs(live - stored) / live
            errs.append(e)
            print(f"  {paper[:22]:22} {size[:14]:14} {colour:9} q{q:>6} stored={stored:.2f} live={live:.2f} err={e*100:.1f}%",
                  file=sys.stderr)
    print(f"verify: max {max(errs)*100:.1f}% / median {sorted(errs)[len(errs)//2]*100:.1f}% over {len(errs)}",
          file=sys.stderr)


def add(paper_label, max_workers=2):
    rows, sizes, colours, qtys = _axes()
    have = {(r["size"], r["colour"], int(r["qty"])) for r in rows if r["paper"] == paper_label}
    cookie = V._get_session_cookie()
    tasks = []
    for size in sizes:
        for colour in colours:
            for q in qtys:
                if (size, colour, q) not in have:
                    tasks.append((size, colour, q, _spec(_size_api(size), _paper_api(paper_label), colour, q)))
    print(f"add '{paper_label}': {len(tasks)} CheckPrice calls", file=sys.stderr)
    added = fail = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(C._fetch, "Loose Sheet", s, cookie): (sz, cl, q) for sz, cl, q, s in tasks}
        for fu in as_completed(futs):
            sz, cl, q = futs[fu]; p = fu.result()
            if p:
                rows.append({"size": sz, "paper": paper_label, "colour": cl, "package": "Normal",
                             "qty": q, "cash": p, "weight": 0.0})
                added += 1
            else:
                fail += 1
    SPOT.write_text(json.dumps(rows))
    valid_combos = {(r["size"], r["colour"]) for r in rows if r["paper"] == paper_label}
    print(f"add: +{added} price points ({fail} invalid combos) across {len(valid_combos)} size×colour; "
          f"wrote spot_samples_21.json", file=sys.stderr)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    if cmd == "verify":
        verify()
    elif cmd == "add":
        add(sys.argv[2])
