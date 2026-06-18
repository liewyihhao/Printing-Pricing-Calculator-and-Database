"""Sample packaging option price deltas (material / print colour / finishing) via the API,
to calibrate an option layer on top of the base engine. Modifies each box's REAL default
chain: P001 for material/colour; swap/add the surface-finishing process for finishing.

Saves output/packaging_option_samples.json
  {variant_key: [{box,L,W,D,qty,total}]}  with variant_key like "base","mat:M0007","col:1","fin:P022","fin:none","fin:+P033"

  python -m app.packaging_options_sampler [account]
"""
from __future__ import annotations
import copy, json, sys
from pathlib import Path
from .packaging_api import bootstrap_session
from .logging_setup import log

OUT = Path(__file__).resolve().parent.parent / "output"
BOXES = ["A001X", "C001A", "D040A", "E005X", "J023A", "M016"]   # one per archetype
DIMS = {"A001X": (120, 100, 80), "C001A": (120, 100, 80), "D040A": (120, 100, 50),
        "E005X": (120, 100, 80), "J023A": (120, 100, 60), "M016": (120, 100, 60)}
QTYS = [100, 500, 1000, 5000]
SURFACE = {"P021", "P022", "P023", "P024", "P036"}   # mutually-exclusive front coatings
MATERIALS = ["M0001", "M0003", "M0006", "M0007", "M0011", "M0013", "M0015", "M0103", "M0106", "M0021"]
SWAP_FIN = ["none", "P022", "P023", "P024", "P036"]   # replace the default P021
ADD_FIN = ["P033", "P031", "P032"]                    # add on top (spot UV / hot stamp / emboss)


def _chain_set_surface(chain, fin):
    c = copy.deepcopy(chain)
    c = [p for p in c if p.get("ID") not in SURFACE] if fin == "none" else \
        [({"ID": fin} if p.get("ID") in SURFACE else p) for p in c]
    return c


def _chain_add(chain, pid):
    c = copy.deepcopy(chain)
    if not any(p.get("ID") == pid for p in c):
        c.append({"ID": pid})
    return c


def run(account_id=1):
    defaults = json.loads((OUT / "packaging_defaults.json").read_text())
    pk = bootstrap_session(account_id)
    if not pk.token:
        raise SystemExit("bootstrap failed")
    out = {}
    def rec(key, box, L, W, D, chain=None, color=4, material="M0024"):
        try:
            for r in pk.price(box, L, W, D, QTYS, color=color, material=material, process=chain):
                out.setdefault(key, []).append({"box": box, "L": L, "W": W, "D": D, "qty": r["qty"], "total": r["total"]})
        except Exception as e:  # noqa: BLE001
            log.info("opt.err", key=key, box=box, err=str(e)[:50])

    for box in BOXES:
        ch = defaults[box]["ProcessJson"]; L, W, D = DIMS[box]
        rec("base", box, L, W, D, ch)
        for m in MATERIALS:
            rec(f"mat:{m}", box, L, W, D, ch, material=m)
        for c in (1, 2):
            rec(f"col:{c}", box, L, W, D, ch, color=c)
        for f in SWAP_FIN:
            rec(f"fin:{f}", box, L, W, D, _chain_set_surface(ch, f))
        for f in ADD_FIN:
            rec(f"fin:+{f}", box, L, W, D, _chain_add(ch, f))
        (OUT / "packaging_option_samples.json").write_text(json.dumps(out))
        log.info("opt.box", box=box, variants=len([k for k in out]))
    print(f"wrote packaging_option_samples.json: {len(out)} variant keys")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
