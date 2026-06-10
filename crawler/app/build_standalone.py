"""Build a STANDALONE, no-server calculator: ui/calculator_standalone.html.

Bakes every product's calibrated params + option cascades into one HTML file with
the pricing formulas ported to JavaScript. Double-click the file to run — no
uvicorn, no network. Re-run this after recalibrating any engine to refresh the file:

    python -m app.build_standalone
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
UI = ROOT / "ui"


def _load(p, default=None):
    f = OUT / p
    return json.loads(f.read_text()) if f.exists() else default


def loose_cascade():
    """size -> paper -> colour -> [packages] for product 21 (status='done')."""
    from .db import session_scope
    from .models import OrderWork
    from sqlalchemy import select
    casc: dict = {}
    with session_scope() as s:
        for w in s.scalars(select(OrderWork).where(
                OrderWork.product_id == 21, OrderWork.status == "done")).all():
            casc.setdefault(w.size_label, {}).setdefault(w.paper_label, {}) \
                .setdefault(w.colour_side, set()).add(w.package or "Normal")
    return {s: {p: {c: sorted(pk) for c, pk in cs.items()} for p, cs in ps.items()}
            for s, ps in casc.items()}


def accuracy():
    # MEASURED median % vs Excard (output/audit_report.json). Curve products are
    # exact at Excard's order quantities; this is the custom-quantity interp error.
    return {1: 2.1, 21: 1.7, 50: 1.3, 19: 0.5, 37: 1.6}


def build_data():
    acc = accuracy()
    digital = json.loads((ROOT / "digital_options.json").read_text())
    from .bizcard_sampler import CARDTYPES, PAPERS, PLASTIC_PAPER
    BC_LABEL = {"standard": "Standard Card", "thin_fold": "Thin Fold",
                "fat_fold": "Fat Fold", "custom_die_cut": "Custom Die-Cut",
                "plastic_card": "Plastic Card"}
    bizcard_ct = {}
    for key, (od, sizes, colours, custom) in CARDTYPES.items():
        bizcard_ct[BC_LABEL[key]] = {
            "internal": key, "sizes": sizes, "colours": colours,
            "papers": [PLASTIC_PAPER] if key == "plastic_card" else PAPERS}

    LOOSE_FIELDS = [
        {"key": "size", "label": "Size", "depends": []},
        {"key": "paper", "label": "Paper", "depends": ["size"]},
        {"key": "colour", "label": "Print colour", "depends": ["size", "paper"]},
        {"key": "package", "label": "Package (ganging)", "depends": ["size", "paper", "colour"]},
    ]
    BOOKLET_FIELDS = [
        {"key": "orientation", "label": "Orientation", "depends": []},
        {"key": "size", "label": "Size", "depends": ["orientation"]},
        {"key": "ordertype", "label": "Cover type", "depends": ["orientation", "size"]},
        {"key": "binding", "label": "Binding", "depends": ["orientation", "size", "ordertype"]},
        {"key": "page", "label": "Pages (incl. cover)", "depends": ["orientation", "size", "ordertype", "binding"]},
        {"key": "cover", "label": "Cover paper", "depends": ["orientation", "size", "ordertype", "binding"]},
        {"key": "content", "label": "Content paper", "depends": ["orientation", "size", "ordertype", "binding", "cover"]},
        {"key": "colour", "label": "Content print colour", "depends": ["orientation", "size", "ordertype", "binding"]},
    ]
    BIZCARD_FIELDS = [
        {"key": "cardType", "label": "Card type", "depends": []},
        {"key": "size", "label": "Size", "depends": ["cardType"]},
        {"key": "paper", "label": "Paper", "depends": ["cardType"]},
        {"key": "colour", "label": "Print colour", "depends": ["cardType"]},
        {"key": "surface", "label": "Surface finishing", "addon": True, "depends": [],
         "options": ["None", "Gloss Lamination (Both)", "Matte Lamination (Both)",
                     "Soft Touch Lamination (Both)", "Spot UV (Front)", "Spot UV (Both)"]},
        {"key": "round_corner", "label": "Round corner (R6mm)", "addon": True, "depends": [], "options": ["No", "Yes"]},
        {"key": "hole_punch", "label": "Hole punching", "addon": True, "depends": [], "options": ["No", "3mm", "5mm"]},
        {"key": "hot_stamping", "label": "Hot stamping (block quoted separately)", "addon": True, "depends": [],
         "options": ["No Hot Stamping", "1C (Front)", "1C (Back)", "2C (Front)", "2C (Back)"]},
        {"key": "embossing", "label": "Embossing (block quoted separately)", "addon": True, "depends": [],
         "options": ["Not Required", "Embossing Front", "Embossing Back"]},
    ]
    products = [
        {"id": 1, "name": "Business Card", "engine": "bizcard", "optsrc": "bizcard",
         "accuracy": acc.get(1), "fields": BIZCARD_FIELDS},
        {"id": 21, "name": "Loose Sheet — Litho (Offset)", "engine": "litho",
         "optsrc": "loose21", "accuracy": acc.get(21), "fields": LOOSE_FIELDS},
        {"id": 50, "name": "Loose Sheet — Digital", "engine": "digital",
         "optsrc": "digital50", "accuracy": acc.get(50), "fields": LOOSE_FIELDS},
        {"id": 19, "name": "Booklet — Litho (Offset)", "engine": "booklet",
         "optsrc": "booklet19", "accuracy": acc.get(19), "fields": BOOKLET_FIELDS},
        {"id": 37, "name": "Booklet — Digital", "engine": "booklet",
         "optsrc": "booklet37", "accuracy": acc.get(37), "fields": BOOKLET_FIELDS},
    ]
    return {
        "products": products,
        "params": {
            "litho": _load("printoka_params.json")["params"],
            "digital": _load("printoka_params_digital.json"),
            "booklet19": _load("booklet_params_19.json")["params"],
            "booklet37": _load("booklet_params_37.json")["params"],
            "bizcard": _load("bizcard_params.json"),
        },
        "curves": {
            "booklet19": _load("booklet_curve_19.json", {}),
            "booklet37": _load("booklet_curve_37.json", {}),
            "loose21": _load("loose_curve_21.json", {}),
        },
        "finishing": _load("bizcard_finishing.json", {"surface": {}, "round_corner": {}, "hole_punch": {}}),
        "options": {
            "loose21": loose_cascade(),
            "digital50": {"sizes": digital["sizes"], "papers_by_size": digital["papers_by_size"]},
            "booklet19": _load("booklet_options_19.json")["combos"],
            "booklet37": _load("booklet_options_37.json")["combos"],
            "bizcard": bizcard_ct,
        },
        "engineByProduct": {1: "bizcard", 21: "litho", 50: "digital", 19: "booklet19", 37: "booklet37"},
    }


def main():
    data = build_data()
    tmpl = (UI / "_standalone_template.html").read_text(encoding="utf-8")
    html = tmpl.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False))
    (UI / "calculator_standalone.html").write_text(html, encoding="utf-8")
    sizes = {k: len(json.dumps(v)) for k, v in data["options"].items()}
    print("wrote ui/calculator_standalone.html")
    print("products:", [p["name"] for p in data["products"]])
    print("option sizes (chars):", sizes)


if __name__ == "__main__":
    main()
