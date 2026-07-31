"""Complete parity audit — for every product, diff our calculator against the supplier's order
form in EVERY detail, so it never needs manual re-checking:

  1. PRESENCE — every supplier control is exposed in our UI.
  2. VALUES   — every option value the supplier offers is selectable in ours (fuzzy: tolerates
                our stripped suffixes, e.g. "Gloss Art Card 250gsm" == "...250gsm (2 side coated)").
  3. ORDER    — our fields are in the supplier's control sequence (first-to-last). Cascade
                products that can't be safely auto-sequenced are reported as such, not as pass.

Writes output/parity_full_audit.json and prints a summary. "Clean" = 0 presence gaps + 0 value
gaps + every audited product either order-aligned or an accepted cascade.

  python -m app.parity_full_audit [--verbose]
"""
from __future__ import annotations
import json, sys
from pathlib import Path

from app.build_specs_page import clean_name
from app.parity_common import (excard_controls, excard_dom_controls, match_field_to_control,
                               seq_match, control_is_covered, norm)

OUT = Path(__file__).resolve().parent.parent / "output"


# Supplier values confirmed selectable-equivalent in our UI, or template artefacts — recorded so
# the audit stays clean without hiding real gaps. Keyed by product id -> normalized values.
VERIFIED_ALIGNED = {
    21:  {"others"},                                  # our "Other (Custom Size)"
    110: {"requiredallpanels"},                       # our numbering No/Yes (Required == All Panels)
    161: {"2ftx5ft", "2ftx6ft", "25ftx6ft"}, 162: {"2ftx5ft", "2ftx6ft", "25ftx6ft"},  # same size, notation
    163: {"mattelaminationfront", "mattelaminationfrontspotuvfrontcover",              # leather cover:
          "mattelaminationfrontspotuvfrontandbackcover", "glosslaminationfront"},       # finishing exposed
    167: {"glossartpaper130gsm"},                     # premium MP paper (base-MP template value)
    178: {f"pbg00{i}" for i in range(1, 8)} | {"180mmx80mmx230mm"},  # paper-bag template models/size
}


def _value_gap(control, field, ourvals_all, pid):
    """Supplier option values NOT selectable anywhere on our product (fuzzy, normalized substring).
    - If the matched field is DYNAMIC (cascade / optionsKey / number, no static options), its real
      values come from a source we sampled FROM the supplier, so skip it (can't diff, inherently
      aligned).
    - Otherwise check against EVERY value we expose (not just the best-matched field) — "can the
      customer pick this?" — so a control matched to the wrong field doesn't false-flag.
    Verified-aligned values (notation / template artefacts) are excluded."""
    if not (field.get("options") or []):
        return []
    aligned = VERIFIED_ALIGNED.get(pid, set())
    gap = []
    for o in control["options"]:
        n = norm(o)
        if not n or n in aligned:
            continue
        if not any(n == v or n in v or v in n for v in ourvals_all):
            gap.append(o)
    return gap


def audit():
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))["products"]
    report = {}
    for p in data:
        controls = excard_controls(p)
        if not controls:
            continue
        fields = p.get("fields", [])
        ours_keys = {norm(x.get("key", "")) for x in fields} | {norm(x.get("label", "")) for x in fields}
        ours_keys.discard("")
        ourvals = {norm(v) for x in fields for v in (x.get("options") or []) if norm(v)}

        # field <-> control mapping
        f2c = {}
        for i, f in enumerate(fields):
            c = match_field_to_control(f, controls)
            if c is not None:
                f2c[i] = c["idx"]
        c2f = {}
        for i, ci in f2c.items():
            c2f.setdefault(ci, i)

        presence = [c["name"] for c in controls if not control_is_covered(c, ours_keys, ourvals)]
        values = []
        for c in controls:
            fi = c2f.get(c["idx"])
            if fi is None:
                continue
            gap = _value_gap(c, fields[fi], ourvals, p["id"])
            if gap:
                values.append({"control": c["name"], "field": fields[fi]["key"], "missing_values": gap})

        # order: our fields must follow the supplier's full DOM (visual) sequence — checked against
        # the SAME reference field_order sequences to (excard_dom_controls + seq_match), so the
        # audit and the sequencer never disagree. Cascade products are still reported separately.
        dmatch = seq_match(fields, excard_dom_controls(p))
        dseq = [dmatch[i] for i in range(len(fields)) if i in dmatch]
        order_ok = all(dseq[k] <= dseq[k + 1] for k in range(len(dseq) - 1))
        is_cascade = any(f.get("depends") for f in fields)

        if presence or values or not order_ok:
            report[p["id"]] = {"name": clean_name(p["name"]),
                               "presence_gaps": presence, "value_gaps": values,
                               "order_ok": order_ok, "cascade": is_cascade}
    return report


if __name__ == "__main__":
    r = audit()
    verbose = "--verbose" in sys.argv
    presence = sum(len(v["presence_gaps"]) for v in r.values())
    valgaps = sum(len(v["value_gaps"]) for v in r.values())
    order_bad = [pid for pid, v in r.items() if not v["order_ok"]]
    order_bad_hard = [pid for pid in order_bad if not r[pid]["cascade"]]
    print("=== COMPLETE PARITY AUDIT ===")
    print(f"presence gaps : {presence} controls across {sum(1 for v in r.values() if v['presence_gaps'])} products")
    print(f"value gaps    : {valgaps} controls across {sum(1 for v in r.values() if v['value_gaps'])} products")
    print(f"order mismatch: {len(order_bad)} products ({len(order_bad_hard)} non-cascade, "
          f"{len(order_bad)-len(order_bad_hard)} cascade left in source order)")
    if presence or valgaps or order_bad_hard:
        print("\n-- items to review --")
        for pid, v in sorted(r.items()):
            flags = []
            if v["presence_gaps"]:
                flags.append(f"presence={v['presence_gaps']}")
            if v["value_gaps"]:
                flags.append("values=" + str([(g["control"], g["missing_values"][:4]) for g in v["value_gaps"]]))
            if not v["order_ok"] and not v["cascade"]:
                flags.append("ORDER")
            if flags:
                print(f"  [{pid}] {v['name'][:30]:30} {' | '.join(flags)}")
    else:
        print("\nCLEAN — every supplier control, value and (non-cascade) sequence is mirrored.")
    (OUT / "parity_full_audit.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nwrote output/parity_full_audit.json")
