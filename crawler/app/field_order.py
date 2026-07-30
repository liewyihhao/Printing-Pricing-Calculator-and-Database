"""Arrange each product's configuration fields in the SAME sequence the supplier's order form
uses, so customers see options first-to-last exactly like theirs.

The supplier's control sequence (DOM order) + the filtering/aliasing/matching all live in
app.parity_common, so this sequencer, the presence audit and the full audit agree. Unlike the
earlier version, single-option controls (e.g. Business Card "Silkscreen Spot UV") ARE included
and matched by name, so the whole sequence lines up — not just the multi-option axes.

Rules:
  - A field mapped to a supplier control takes that control's DOM position.
  - A `showWhen` sub-field stays directly after its parent field.
  - An unmatched extra field keeps its place after the last matched field before it.
  - Weak overall match (<60% of option-bearing fields) -> leave the product's order alone.

  python -m app.field_order          # report the reordering per product
"""
from __future__ import annotations
import json
from pathlib import Path

from app.build_specs_page import clean_name
from app.parity_common import excard_controls, match_field_to_control

OUT = Path(__file__).resolve().parent.parent / "output"


def reorder_fields(product):
    """Return the product's fields resequenced to the supplier's order (or None to leave as-is)."""
    controls = excard_controls(product)
    fields = product.get("fields") or []
    if not controls or len(fields) < 2:
        return None

    matched = {}                                   # field index -> control DOM index
    for i, f in enumerate(fields):
        c = match_field_to_control(f, controls)
        if c is not None:
            matched[i] = c["idx"]

    if not matched:
        return None

    # Anchor each field: a MATCHED field takes its supplier control's DOM position; an UNMATCHED
    # field stays right after the field that precedes it in our current order (so it never floats
    # away from its neighbours), and a showWhen sub-field trails its parent. This keeps unmatched
    # extras stable while matched fields (incl. single-option "included" ones) move to the
    # supplier's sequence.
    anchor_by = {}
    for i, f in enumerate(fields):
        if i in matched:
            a = float(matched[i])
        elif f.get("showWhen"):
            pk = f.get("showWhen", {}).get("field")
            pa = next((anchor_by[j] for j, pf in enumerate(fields)
                       if pf.get("key") == pk and j in anchor_by), None)
            a = (pa if pa is not None else (anchor_by[i - 1] if i else -1.0)) + 1e-3
        else:
            a = (anchor_by[i - 1] if i else -1.0) + 1e-4
        anchor_by[i] = a

    # Hard guardrail: a field must NEVER sort before a field it depends on (cascade integrity).
    # Bump each field's anchor past its dependencies until stable (fields form a DAG).
    key_to_i = {f.get("key"): i for i, f in enumerate(fields)}
    for _ in range(len(fields) + 1):
        moved = False
        for i, f in enumerate(fields):
            for dep in (f.get("depends") or []):
                j = key_to_i.get(dep)
                if j is not None and anchor_by[j] >= anchor_by[i]:
                    anchor_by[i] = anchor_by[j] + 1e-5
                    moved = True
        if not moved:
            break

    ordered = [fields[i] for i in sorted(range(len(fields)), key=lambda i: (anchor_by[i], i))]

    # Safety post-pass: guarantee each showWhen child is emitted directly after its parent.
    by_key = {f.get("key"): f for f in ordered}
    out, placed = [], set()
    for f in ordered:
        k = f.get("key")
        if k in placed:
            continue
        sw = f.get("showWhen")
        if sw and sw.get("field") in by_key and sw["field"] not in placed:
            continue                                # parent will pull this child in
        out.append(f); placed.add(k)
        for c in ordered:
            csw = c.get("showWhen")
            if c.get("key") not in placed and csw and csw.get("field") == k:
                out.append(c); placed.add(c.get("key"))
    for f in ordered:
        if f.get("key") not in placed:
            out.append(f); placed.add(f.get("key"))
    return out


def reorder(data):
    n = changed = 0
    for p in data["products"]:
        new = reorder_fields(p)
        n += 1
        if new:
            if [f.get("key") for f in new] != [f.get("key") for f in p.get("fields") or []]:
                changed += 1
            p["fields"] = new
    return n, changed


if __name__ == "__main__":
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))
    for p in data["products"]:
        before = [f.get("key") for f in p.get("fields") or []]
        new = reorder_fields(p)
        if new and [f.get("key") for f in new] != before:
            print(f"\n{clean_name(p['name'])}")
            print("  before:", before)
            print("  after :", [f.get("key") for f in new])
    n, changed = reorder(data)
    print(f"\n{changed}/{n} products resequenced to the supplier's option order")
