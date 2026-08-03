"""Add Business Card "Soft Touch Lamination (Both)" to the exact price curves.

Soft Touch is a real premium (~+6–10% over Gloss). The Soft/Gloss price RATIO is package-
independent (verified: Normal 1.0788 == 2-in-1 1.0786), so we only sample the ratio on the
Normal-package grid (~1440 CheckPrice calls at workers<=2, per the concurrency memory) and derive
exact Soft-Touch curves for every package as gloss_curve * ratio[size,paper,colour,qty]. A random
sample of non-Normal packages is validated directly before writing.

  python -m app.bizcard_softtouch          # sample + derive + validate + write
"""
from __future__ import annotations
import json, random, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from app import bizcard_cp_sampler as B
from app import checkprice_enum as C
from app import voucher_cp_sampler as V

OUT = Path(__file__).resolve().parent.parent / "output"
OPTS = OUT / "business-card_options.json"        # actually under v4_options/
OPTS = OUT / "v4_options" / "business-card_options.json"
GLOSS = "Gloss Lamination (Both)"
SOFT = "Soft Touch Lamination (Both)"
# The stored curve-key size/paper are ALREADY the CheckPrice spec format ("54mm x 89mm" with x,
# paper suffix stripped), so pass them through unchanged. Package needs the form label back.
_PKG = {"Normal": "Normal (1 Design)", "2in1": "2 In 1 (2 Designs)", "3in1": "3 In 1 (3 Designs)",
        "4in1": "4 In 1 (4 Designs)", "5in1": "5 In 1 (5 Designs)", "6in1": "6 In 1 (6 Designs)",
        "7in1": "7 In 1 (7 Designs)", "8in1": "8 In 1 (8 Designs)", "9in1": "9 In 1 (9 Designs)",
        "10in1": "10 In 1 (10 Designs)"}


def _spec(size, paper, colour, pkg_form, lam, qty):
    return {"Product": "Business Card", "OrderDesc": "Standard", "Size": size, "Orientation": "Landscape",
            "Paper": paper, "Package": B._pkg(pkg_form), "PrintColour": colour, "Quantity": qty, "Lamination": lam,
            "HotStamping": "", "HotStampingColour": "", "HotStampingBlock": "", "RoundCorner": "", "HolePunch": "",
            "Embossing": "", "Folding": "", "FoldCode": "", "Country": "99", "Courier": "DEFAULT", "CountryZone": "West Malaysia"}


def run(max_workers=2):
    data = json.loads(OPTS.read_text(encoding="utf-8"))
    curves = data["curves"]
    gloss_keys = [k for k in curves if f"|{GLOSS}|" in k]
    # normal-package gloss curves carry the ratio grid
    normal_gloss = {k: v for k, v in curves.items() if k.endswith("|Normal") and f"|{GLOSS}|" in k}
    cookie = V._get_session_cookie()

    # 1) sample Soft Touch at Normal package for every (size,paper,colour,qty) -> ratio
    tasks = []
    for k, curve in normal_gloss.items():
        size_a, paper_a, colour, _lam, _pkg = k.split("|")
        size = size_a; paper = paper_a
        for q in curve:
            tasks.append((k, q, _spec(size, paper, colour, "Normal (1 Design)", SOFT, q)))
    print(f"soft-touch: sampling {len(tasks)} Normal-grid ratios", file=sys.stderr)
    ratio = {}                                          # (normal_gloss_key, qty) -> soft/gloss
    done = fail = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(C._fetch, "Business Card", s, cookie): (k, q) for k, q, s in tasks}
        for fu in as_completed(futs):
            k, q = futs[fu]; p = fu.result(); done += 1
            g = normal_gloss[k].get(q)
            if p and g:
                ratio[(k, q)] = p / g
            else:
                fail += 1
            if done % 300 == 0:
                print(f"  {done}/{len(tasks)} ({fail} none)", file=sys.stderr)
    print(f"soft-touch: {len(ratio)} ratios ({fail} none)", file=sys.stderr)

    # 2) derive Soft Touch curves for ALL packages: gloss_curve * ratio[size,paper,colour,qty]
    added = 0
    for gk, gcurve in list(curves.items()):
        if f"|{GLOSS}|" not in gk:
            continue
        size_a, paper_a, colour, _lam, pkg = gk.split("|")
        nkey = f"{size_a}|{paper_a}|{colour}|{GLOSS}|Normal"
        soft_curve = {}
        for q, gp in gcurve.items():
            r = ratio.get((nkey, q))
            if r:
                soft_curve[q] = round(gp * r, 2)
        if soft_curve:
            curves[f"{size_a}|{paper_a}|{colour}|{SOFT}|{pkg}"] = soft_curve
            added += 1
    print(f"soft-touch: derived {added} curves", file=sys.stderr)

    # 3) validate: sample a few non-Normal Soft Touch directly, compare to derived
    sample = [k for k in curves if f"|{SOFT}|" in k and not k.endswith("|Normal")]
    random.seed(1); random.shuffle(sample)
    errs = []
    for k in sample[:15]:
        size_a, paper_a, colour, _lam, pkg = k.split("|")
        curve = curves[k]; q = list(curve)[len(curve) // 2]
        actual = C._fetch("Business Card", _spec(size_a, paper_a, colour, _PKG[pkg], SOFT, q), cookie)
        if actual:
            errs.append(abs(actual - curve[q]) / actual)
            print(f"  validate {pkg:6} q{q:>5} derived={curve[q]} actual={actual} "
                  f"err={abs(actual-curve[q])/actual*100:.2f}%", file=sys.stderr)
    maxerr = max(errs) if errs else 1
    print(f"soft-touch: max validation error {maxerr*100:.2f}%", file=sys.stderr)
    if maxerr > 0.02:
        print("VALIDATION FAILED (>2%) — NOT writing; package-independence broke, full sample needed.", file=sys.stderr)
        return
    data["curves"] = curves
    data["priceMeta"]["nCurves"] = len(curves)
    if SOFT not in data["distinct"]["Lamination"]:
        data["distinct"]["Lamination"].append(SOFT)
    OPTS.write_text(json.dumps(data))
    print(f"soft-touch: WROTE {len(curves)} curves to business-card_options.json (validated)", file=sys.stderr)


if __name__ == "__main__":
    run()
