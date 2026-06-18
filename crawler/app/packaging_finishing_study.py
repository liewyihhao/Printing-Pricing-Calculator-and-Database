"""Study how packaging finishing STACKS: are multiple finishing deltas additive?
Prices base + single finishings + combinations on a few boxes via the live API and
checks whether delta(A+B) ~= delta(A)+delta(B).

  python -m app.packaging_finishing_study [account]
"""
from __future__ import annotations
import copy, json, sys
from pathlib import Path
from .packaging_api import bootstrap_session

OUT = Path(__file__).resolve().parent.parent / "output"
BOXES = ["A001X", "C001A", "D040A"]
DIMS = {"A001X": (120, 100, 80), "C001A": (120, 100, 80), "D040A": (120, 100, 50)}
QTY = 1000
SURFACE = {"P021", "P022", "P023", "P024", "P036", "P035"}
NAMES = {"P021": "GlossLam", "P022": "MatteLam", "P036": "UVVarnish",
         "P033": "SpotUV", "P031": "HotStamp", "P032": "Emboss", "P034": "Textured"}


def chain_with(base, coating=None, addons=()):
    c = copy.deepcopy(base)
    if coating is not None:
        c = [p for p in c if p.get("ID") not in SURFACE]
        if coating != "none":
            c.append({"ID": coating})
    for a in addons:
        if not any(p.get("ID") == a for p in c):
            c.append({"ID": a})
    return c


def run(account_id=1):
    defaults = json.loads((OUT / "packaging_defaults.json").read_text())
    pk = bootstrap_session(account_id)
    for box in BOXES:
        base = defaults[box]["ProcessJson"]; L, W, D = DIMS[box]
        def price(coating=None, addons=()):
            ch = chain_with(base, coating, addons)
            return pk.price(box, L, W, D, [QTY], process=ch)[0]["total"]
        b = price()  # default (gloss lam)
        print(f"\n=== {box} {L}x{W}x{D} q{QTY} | base(GlossLam)={b:.2f} ===")
        dSpot = price(addons=["P033"]) - b
        dHot = price(addons=["P031"]) - b
        dEmb = price(addons=["P032"]) - b
        dMatte = price(coating="P022") - b
        print(f"  +SpotUV={dSpot:.2f}  +HotStamp={dHot:.2f}  +Emboss={dEmb:.2f}  MatteLam(swap)={dMatte:.2f}")
        # combos vs summed prediction
        for label, coating, addons, pred in [
            ("SpotUV+HotStamp", None, ["P033", "P031"], dSpot + dHot),
            ("SpotUV+HotStamp+Emboss", None, ["P033", "P031", "P032"], dSpot + dHot + dEmb),
            ("MatteLam+SpotUV", "P022", ["P033"], dMatte + dSpot),
        ]:
            actual = price(coating=coating, addons=addons) - b
            err = abs(actual - pred) / abs(actual) * 100 if actual else 0
            print(f"  {label}: actual Δ={actual:.2f} vs summed Δ={pred:.2f}  ({err:.1f}%)")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
