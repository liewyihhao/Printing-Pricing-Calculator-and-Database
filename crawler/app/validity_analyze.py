"""Analyse output/validity/<id>.json (from app.validity_capture) into per-product conditional
rule PROPOSALS: which controls are conditionally VISIBLE (showWhen candidate) and which controls'
OPTIONS depend on a driver (validity candidate). Prints a triage of products that have conditionals.

  python -m app.validity_analyze            # summary of all
  python -m app.validity_analyze 21 --verbose
"""
from __future__ import annotations
import json, sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
VDIR = OUT / "validity"


def analyze(cap):
    vis, opt = [], []
    for dname, dv in (cap.get("variations") or {}).items():
        vals = dv.get("values", {})
        if len(vals) < 2:
            continue
        labels = {r["label"] for rows in vals.values() for r in rows}
        for ctrl in sorted(labels):
            shown = [v for v, rows in vals.items() if any(r["label"] == ctrl for r in rows)]
            hidden = [v for v in vals if v not in shown]
            if shown and hidden:                      # conditionally visible
                vis.append({"control": ctrl, "driver": dname, "driverLabel": dv.get("label", dname),
                            "shownWhen": shown})
            # option dependency: distinct option sets across values where shown
            osets = {}
            for v in shown:
                row = next((r for r in vals[v] if r["label"] == ctrl), None)
                if row is not None:
                    osets[v] = tuple(row.get("opts", []))
            if len(set(osets.values())) > 1 and len(osets) >= 2:
                opt.append({"control": ctrl, "driver": dname, "driverLabel": dv.get("label", dname),
                            "optionsByValue": {v: list(o) for v, o in osets.items()}})
    return {"visibility": vis, "options": opt}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    verbose = "--verbose" in sys.argv
    files = ([VDIR / f"{a}.json" for a in args] if args
             else sorted(VDIR.glob("*.json"), key=lambda p: int(p.stem)))
    withcond = 0
    print("=== VALIDITY CONDITIONAL TRIAGE ===")
    for f in files:
        if not f.is_file():
            continue
        cap = json.loads(f.read_text(encoding="utf-8"))
        if not cap.get("variations"):
            continue
        r = analyze(cap)
        if not (r["visibility"] or r["options"]):
            continue
        withcond += 1
        vlabels = sorted({v["control"] for v in r["visibility"]})
        olabels = sorted({o["control"] for o in r["options"]})
        print(f"\n[{cap['id']}] {cap['name'][:34]:34} drivers={cap.get('drivers')}")
        if vlabels:
            print(f"   conditional VISIBILITY: {vlabels}")
        if olabels:
            print(f"   conditional OPTIONS:    {olabels}")
        if verbose:
            for v in r["visibility"]:
                print(f"     [{v['driverLabel']}] {v['control']} shown for: {v['shownWhen'][:6]}")
            for o in r["options"]:
                vals = list(o["optionsByValue"])
                print(f"     [{o['driverLabel']}] {o['control']} opts vary across {vals[:4]}")
    print(f"\n{withcond} products with conditional validity (of {len(files)} captured).")


if __name__ == "__main__":
    main()
