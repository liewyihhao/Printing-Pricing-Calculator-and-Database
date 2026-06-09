"""Business-card price sampler — calls the v4 pricing API directly (no browser).

Builds a representative grid over cardType × size × paper × colour and sweeps the
quantity ladder, recording Excard's cash (before-discount) price. Package is a pure
×N multiplier (verified) so it is NOT sampled. Finishing add-ons are sampled
separately (bizcard_sampler.py finishing). Output -> output/bizcard_samples.json.

    python -m app.bizcard_sampler          # core grid
    python -m app.bizcard_sampler finishing  # finishing add-on deltas
"""
from __future__ import annotations
import json, re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from .bizcard_api import make_spec, check_price

OUT = Path(__file__).resolve().parent.parent / "output"
# Dense ladder to capture Excard's non-monotonic sheet/promo "sawtooth" between the
# headline breakpoints: every 50 to 2000, every 100 to 5000, every 250 to 10000.
QTYS = sorted(set(
    list(range(50, 2001, 50)) +
    list(range(2000, 5001, 100)) +
    list(range(5000, 10001, 250))))

PAPERS = ["Gloss Art Card 250gsm", "Gloss Art Card 310gsm", "Gloss Art Card 360gsm",
          "Matte Art Card 250gsm", "Linen 240gsm", "Metal Ice 250gsm",
          "Synthetic Paper 180micron", "Super White 250gsm", "Suwen 240gsm"]

# cardType -> (OrderDesc, [api sizes], [colours], is_custom)
CARDTYPES = {
    "standard": ("Standard",
                 ["54mm x 89mm", "52mm x 86mm", "50mm x 89mm", "54mm x 86mm"],
                 ["4C (Both)", "4C (Front)"], False),
    "thin_fold": ("Thin Fold",
                  ["54mm x 178mm", "52mm x 172mm", "50mm x 172mm", "52mm x 156mm"],
                  ["4C (Both)", "4C (Front)"], False),
    "fat_fold": ("Fat Fold",
                 ["89mm x 108mm", "86mm x 104mm", "86mm x 100mm", "86mm x 88mm"],
                 ["4C (Both)", "4C (Front)"], False),
    "custom_die_cut": ("Custom Die-Cut",
                       ["40mm x 40mm", "60mm x 50mm", "70mm x 89mm", "89mm x 54mm"],
                       ["4C (Both)", "4C (Front)"], True),
    "plastic_card": ("Plastic Card", ["54mm x 89mm"],
                     ["4C", "4C & White"], False),
}
PLASTIC_PAPER = "Frosted Plastic Card 400micron"


def dims(api_size):
    m = re.search(r"(\d+)\s*mm\s*x\s*(\d+)\s*mm", api_size)
    return (int(m.group(1)), int(m.group(2))) if m else (54, 89)


def _one(ct, od, size, paper, colour, is_custom, qty):
    spec = make_spec(OrderDesc=od, Size=size, Paper=paper, PrintColour=colour,
                     Lamination="", Quantity=str(qty), Package="Normal",
                     IsCustomSize=("true" if is_custom else "false"))
    d = check_price(spec)
    if not d:
        return None
    try:
        cash = float(str(d.get("Price", "0")).replace(",", ""))
    except ValueError:
        return None
    if cash <= 0:
        return None
    w, h = dims(size)
    return {"cardType": ct, "size": size, "paper": paper, "colour": colour,
            "qty": qty, "cash": cash, "w": w, "h": h,
            "weight": d.get("Weight"), "is_custom": is_custom}


def core():
    jobs = []
    for ct, (od, sizes, colours, is_custom) in CARDTYPES.items():
        papers = [PLASTIC_PAPER] if ct == "plastic_card" else PAPERS
        for size in sizes:
            for paper in papers:
                for colour in colours:
                    for qty in QTYS:
                        jobs.append((ct, od, size, paper, colour, is_custom, qty))
    print(f"sampling {len(jobs)} business-card price points via API…")
    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for i, r in enumerate(ex.map(lambda a: _one(*a), jobs)):
            if r:
                results.append(r)
            if (i + 1) % 200 == 0:
                print(f"  {i+1}/{len(jobs)} done, {len(results)} valid")
                OUT.joinpath("bizcard_samples.json").write_text(json.dumps(results))
    OUT.joinpath("bizcard_samples.json").write_text(json.dumps(results, indent=0))
    print(f"wrote output/bizcard_samples.json ({len(results)} points)")


if __name__ == "__main__":
    core()
