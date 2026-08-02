"""Derive each field's EXACT Excard section from the live v4 form capture (output/v4_form/<id>.json)
and write output/field_sections.json = {product_id: {field_key: section}}. build_standalone prefers
these captured sections over the keyword heuristic, so the calculator's General / Optional Finishing
/ Add On grouping matches the supplier form per product.

  python -m app.section_map
"""
from __future__ import annotations
import json
from pathlib import Path
from app.parity_common import norm
from app.v4_reconcile import _sec_of_rows

OUT = Path(__file__).resolve().parent.parent / "output"
FDIR = OUT / "v4_form"


def _match(control, fields):
    """Confident field<->control match for SECTION assignment. Deliberately strict: cascade products
    (Booklet, Loose Sheet) have many near-identical fields (cover vs content paper/colour), so a weak
    option-overlap match mis-assigns sections. Require a NAME match (label/key) or a strong option
    overlap; otherwise return None and let the field keep the section heuristic."""
    clabel = norm(control.get("label", "")); cname = norm(control.get("name", ""))
    copts = {norm(o) for o in (control.get("options") or []) if norm(o)}
    best, best_score = None, 0.0
    for f in fields:
        fk, fl = norm(f.get("key", "")), norm(f.get("label", ""))
        # name match on the human LABEL (most reliable) or an exact key match
        nm = bool(clabel) and bool(fl) and (clabel == fl or clabel in fl or fl in clabel)
        nm = nm or (bool(cname) and cname == fk)
        fopts = {norm(o) for o in (f.get("options") or []) if norm(o)}
        jac = len(copts & fopts) / len(copts | fopts) if (copts and fopts) else 0.0
        score = (2.0 if nm else 0.0) + jac
        if score > best_score:
            best_score, best = score, f
    return best if best_score >= 2.0 or best_score >= 0.7 else None


def build():
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))["products"]
    by_id = {p["id"]: p for p in data}
    out = {}
    if not FDIR.is_dir():
        return out
    for f in sorted(FDIR.glob("*.json")):
        cap = json.loads(f.read_text(encoding="utf-8"))
        p = by_id.get(cap.get("id"))
        if not p or not cap.get("rows") or cap.get("sectionCount", 0) == 0:
            continue
        fields = p.get("fields", [])
        secmap, order = {}, []
        for sec, c in _sec_of_rows(cap["rows"]):        # sec = supplier section label
            if sec not in order:
                order.append(sec)
            m = _match(c, fields)
            if m is not None:
                secmap.setdefault(m["key"], sec)         # first (topmost) section wins
        if secmap:
            out[str(p["id"])] = {"fields": secmap, "order": order}
    (OUT / "field_sections.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    total = sum(len(v["fields"]) for v in out.values())
    print(f"section_map: {total} fields across {len(out)} products -> output/field_sections.json")
    return out


if __name__ == "__main__":
    build()
