"""Auto-expose the supplier's SINGLE-OPTION order-form controls as display-only fields.

Background: the option-parity standard requires our UI to mirror every control on the
supplier's order form, including price-neutral ones. A control with exactly ONE option is
trivially price-neutral (there is nothing to choose), so it can be surfaced mechanically with
no pricing risk — it documents what's included (e.g. "Wire O Hole Punching",
"Individual Blank Box Packing", "720 dpi solvent", "Die-cutting + creasing").

Multi-option controls are deliberately NOT handled here — those can move price and are added
per-product after verification.

  attach(data) -> (n_products_touched, n_fields_added)
"""
from __future__ import annotations
import json, re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
AUDIT = OUT / "option_audit"

# controls that aren't product options (delivery, nav, quantity, internals)
_SKIP = re.compile(r"country|courier|quantity|qty|review|favourite|rush|track|customsize|"
                   r"^txt|^chk|numberfr|numberto|vdp|k100|m100|eyelet|seal|fastener|alquran|"
                   r"^ddlProduct$", re.I)
# a single option that is really a product name / picker artefact
_NOT_AN_OPTION = re.compile(r"^\s*(-|—|please select|select)", re.I)
# values that carry no information for the customer
_MEANINGLESS = re.compile(r"^\s*(n/?a|none|nil|null|-{1,3})\s*$", re.I)
# a bare dimension ("350mm", '29inch') — the control's generic label (e.g. "Finishing") would
# misdescribe it, so present it as a measurement instead
_BARE_DIM = re.compile(r"^\s*\d+(\.\d+)?\s*(mm|cm|m|inch|in|\")\s*$", re.I)

_LABELS = {
    "compulsory": "Included", "printmethod": "Print Method", "printcolour": "Print Colour",
    "finishing": "Finishing", "paper": "Paper / Binding", "size": "Size", "colour": "Colour",
    "model": "Model", "packing": "Packing", "mixdesign": "Mix Design", "orderdesc": "Order Type",
    "orientation": "Orientation", "binding": "Binding", "lamination": "Lamination",
    "category": "Category", "type": "Type", "package": "Package", "mould": "Mould",
    "punchhole": "Punch Hole", "headerpaper": "Header Paper", "contentpaper": "Content Paper",
}


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _base_slug(name):
    from app.build_specs_page import clean_name
    b = re.split(r"[—(]", clean_name(name))[0]
    return re.sub(r"[^a-z0-9]+", "-", b.strip().lower()).strip("-")


def _label_for(ctrl_name: str) -> str:
    key = _norm(re.sub(r"^(rbl|ddl|combo)", "", ctrl_name))
    if key in _LABELS:
        return _LABELS[key]
    # humanise: rblHeaderPrintColour -> "Header Print Colour"
    raw = re.sub(r"^(rbl|ddl|combo)", "", ctrl_name)
    return re.sub(r"(?<!^)(?=[A-Z])", " ", raw).strip().title() or "Detail"


def attach(data):
    from app.product_quantity import _ALIAS
    touched = added = 0
    for p in data["products"]:
        slug = _base_slug(p["name"])
        slug = _ALIAS.get(slug, slug)
        f = AUDIT / f"{slug}.json"
        if not f.is_file():
            continue
        try:
            aud = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        fields = p.setdefault("fields", [])
        ours = {_norm(x.get("key", "")) for x in fields} | {_norm(x.get("label", "")) for x in fields}
        ourvals = {_norm(v) for x in fields for v in (x.get("options") or []) if _norm(v)}
        ours.discard("")
        new = []
        for c in aud.get("controls", []):
            nm = c.get("name", "")
            if not nm or _SKIP.search(nm):
                continue
            opts = [o for o in (c.get("options") or []) if not _NOT_AN_OPTION.match(str(o))]
            if len(opts) != 1:                      # single-option controls only
                continue
            val = str(opts[0]).strip()
            if not val or _MEANINGLESS.match(val) or _norm(val) in ourvals:
                continue
            ctrl = _norm(re.sub(r"^(rbl|ddl|combo)", "", nm))
            if not ctrl or any(ctrl in o or o in ctrl for o in ours):
                continue
            key = f"inc_{ctrl}"
            if any(_norm(x.get("key", "")) == _norm(key) for x in fields):
                continue
            label = _label_for(nm)
            if _BARE_DIM.match(val) and _norm(label) not in ("size", "sizelength"):
                label = "Size / Length"      # a measurement, not whatever the control is named
            new.append({"key": key, "label": label, "options": [val],
                        "note": "Included as standard on this product.",
                        "addon": True, "depends": []})
            ours.add(ctrl); ourvals.add(_norm(val))
        if new:
            fields.extend(new)
            touched += 1
            added += len(new)
    return touched, added
