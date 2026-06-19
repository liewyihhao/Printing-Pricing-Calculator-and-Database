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


def _multidieline_data(mats):
    """Precompute Multiple Dieline pricing inputs for the standalone:
    base Mirror-Kote-4C sheet curve per sheet size, 1C colour multiplier, and a
    per-material multiplier (so the JS port needs no fit)."""
    from . import sticker_categories as SC
    base = {}
    for ss in SC.MD_SHEET_SIZES:
        pts = SC._md_base_pts(ss)
        if pts:
            base[ss] = {str(q): c for q, c in sorted(pts)}
    return {"base": base,
            "colourMult": round(SC._md_colour_mult(), 6),
            "matMult": {m: round(SC._md_mat_mult(m), 6) for m in mats}}


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
    return {1: 2.1, 21: 1.7, 50: 1.3, 19: 0.5, 37: 1.6, 60: 6.3, 61: 10.5, 24: 2.5}


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

    ENVELOPE_OPTS = ["Not Required", "108mm x 159mm - Pink A6", "110mm x 220mm - White DL",
                     "133mm x 102mm - Cream A7", "162mm x 114mm - White A6",
                     "162mm x 229mm - Pink A5", "162mm x 229mm - White A5", "215mm x 114mm - Pink DL"]
    LOOSE_FIELDS = [
        {"key": "size", "label": "Size", "depends": []},
        {"key": "paper", "label": "Paper", "depends": ["size"]},
        {"key": "colour", "label": "Print colour", "depends": ["size", "paper"]},
        {"key": "package", "label": "Package (ganging)", "depends": ["size", "paper", "colour"]},
        {"key": "envelope", "label": "Envelope (add-on)", "addon": True, "depends": [], "options": ENVELOPE_OPTS},
        {"key": "custom_w", "label": "Custom width (mm) — optional", "type": "number", "optional": True, "min": 10, "max": 1000, "depends": []},
        {"key": "custom_h", "label": "Custom height (mm) — optional", "type": "number", "optional": True, "min": 10, "max": 1000, "depends": []},
    ]
    LOOSE_DIGITAL_FIELDS = LOOSE_FIELDS + [
        {"key": "hot_stamping", "label": "Hot stamping", "addon": True, "depends": [],
         "options": ["Not Required", "1C (Front)", "1C (Back)", "2C (Front)", "2C (Back)"]},
        {"key": "fold", "label": "Folding", "addon": True, "depends": [],
         "options": ["None", "1Fa", "2Fa", "2Fb", "2Fc", "3Fa", "3Fb", "4Fa", "4Fb"]},
        {"key": "punch", "label": "Hole punching", "addon": True, "depends": [], "options": ["No", "3mm", "6mm"]},
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
        {"key": "outer_inner", "label": "Cover colour sides", "addon": True, "depends": [],
         "options": ["4C: 4 Colour Outer Only", "4C: 4 Colour Outer & 4 Colour Inner"]},
        {"key": "cover_lamination", "label": "Cover lamination / finishing", "addon": True, "depends": [],
         "options": ["Not Required", "Matte Lamination (Front)", "Matte Lamination (Both)",
                     "Matte Lamination (Front) + Spot UV (Front)", "Matte Lamination (Both) + Spot UV (Front)",
                     "Gloss Lamination (Front)", "Gloss Lamination (Both)", "UV Varnish (Front)",
                     "UV Varnish (Both)", "Gloss Waterbase Varnish (Front)", "Gloss Waterbase Varnish (Both)"]},
        {"key": "cover_embossing", "label": "Cover embossing — emboss size (block quoted separately)", "addon": True, "depends": [],
         "options": ["Not Required", "90mm x 30mm", "90mm x 70mm", "95mm x 206mm", "101mm x 144mm", "144mm x 206mm", "194mm x 206mm", "206mm x 294mm"]},
        {"key": "hot_stamping", "label": "Cover hot stamping (block quoted separately)", "addon": True, "depends": [],
         "options": ["Not Required", "1C (Front)", "2C (Front)"]},
        {"key": "jawi", "label": "Jawi content", "addon": True, "depends": [], "options": ["No", "Yes"]},
        {"key": "extra_books", "label": "Add 3 extra books (+RM30)", "addon": True, "depends": [], "options": ["No", "Yes"]},
    ]
    BIZCARD_FIELDS = [
        {"key": "cardType", "label": "Card type", "depends": []},
        {"key": "size", "label": "Size", "depends": ["cardType"]},
        {"key": "orientation", "label": "Orientation", "addon": True, "depends": [], "options": ["Landscape", "Portrait"]},
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
    STICKER_MATS = ["Mirror Kote", "Mirror Kote (Strong Glue)", "Transparent OPP",
                    "White PP (Polypropylene)", "White PE (Polyethylene)", "Synthetic Paper",
                    "Printing Paper", "Brown Craft Paper", "Matte Silver Polyester",
                    "Bright Silver Polyester", "Removable Transparent OPP",
                    "Removable White PP", "Warranty Sticker"]
    STICKER_D_FIELDS = [
        {"key": "type", "label": "Product type", "addon": True, "depends": [], "options": ["Sticker", "CD"]},
        {"key": "category", "label": "Cut type (Sticker only)", "addon": True, "depends": [], "options": ["Rectangle/Square", "Custom Die-Cut", "Standard Shape", "Round", "No Cut", "Kiss Cut", "Multiple Dieline"]},
        {"key": "paper", "label": "Material", "addon": True, "depends": [], "options": STICKER_MATS},
        {"key": "colour", "label": "Print colour", "addon": True, "depends": [], "options": ["4C", "1C"]},
        {"key": "finishing", "label": "Lamination", "addon": True, "depends": [],
         "options": ["Not Required", "Matte Laminate (Front)", "Gloss Laminate (Front)",
                     "Gloss Water Based Varnish", "UV Varnish", "Soft Touch Laminate (Front)"]},
        {"key": "hot_stamping", "label": "Hot stamping (block quoted separately)", "addon": True, "depends": [], "options": ["Not Required", "Gold", "Silver"]},
        {"key": "package", "label": "Package (N-in-1, ×N)", "addon": True, "depends": [], "options": ["Normal", "2in1", "3in1", "4in1", "5in1", "6in1", "7in1", "8in1", "9in1", "10in1"]},
        {"key": "sheet_size", "label": "Sheet size — Multiple Dieline only", "addon": True, "depends": [], "options": ["A3+", "A4", "A5"]},
        {"key": "dielines", "label": "Die lines per sheet — Multiple Dieline (no price effect)", "type": "number", "optional": True, "min": 1, "max": 100, "depends": []},
        {"key": "height", "label": "Height (mm) — Rectangle/Standard/Custom", "type": "number", "min": 10, "max": 300, "default": 50, "depends": []},
        {"key": "width", "label": "Width (mm) — Rectangle/Standard/Custom", "type": "number", "min": 10, "max": 300, "default": 90, "depends": []},
        {"key": "diameter", "label": "Diameter (mm) — Round only", "type": "number", "optional": True, "min": 10, "max": 300, "depends": []},
    ]
    STICKER_L_FIELDS = [
        {"key": "category", "label": "Shape", "addon": True, "depends": [], "options": ["Standard Shape", "Round"]},
        {"key": "colour", "label": "Hot stamping colour", "addon": True, "depends": [], "options": ["Gold", "Silver"]},
        {"key": "height", "label": "Height (mm) — Standard Shape", "type": "number", "min": 10, "max": 300, "default": 50, "depends": []},
        {"key": "width", "label": "Width (mm) — Standard Shape", "type": "number", "min": 10, "max": 300, "default": 90, "depends": []},
        {"key": "diameter", "label": "Diameter (mm) — Round only", "type": "number", "optional": True, "min": 10, "max": 300, "depends": []},
    ]
    BILLBOOK_SIZES = ["145mm x 210mm", "A4 (210mm x 297mm)", "B5 (176mm x 250mm)", "90mm x 140mm",
                  "90mm x 177mm", "95mm x 210mm", "95mm x 225mm", "105mm x 145mm", "105mm x 175mm",
                  "107mm x 190mm", "110mm x 210mm", "120mm x 210mm", "120mm x 230mm", "125mm x 175mm",
                  "135mm x 210mm", "145mm x 148mm", "145mm x 190mm", "148mm x 190mm", "148mm x 291mm",
                  "160mm x 240mm", "165mm x 210mm", "170mm x 190mm", "173mm x 206mm", "180mm x 280mm",
                  "190mm x 210mm", "190mm x 270mm", "190mm x 290mm", "190mm x 297mm", "192mm x 268mm",
                  "194mm x 205mm", "206mm x 240mm", "206mm x 330mm", "210mm x 270mm", "210mm x 291mm",
                  "B4 (250mm x 353mm)", "291mm x 420mm", "F3 (330mm x 420mm)"]
    BILLBOOK_FIELDS = [
        {"key": "packform", "label": "Form", "addon": True, "depends": [], "options": ["Book", "Pad"]},
        {"key": "size", "label": "Size", "addon": True, "depends": [], "options": BILLBOOK_SIZES},
        {"key": "layers", "label": "Plies (NCR layers)", "addon": True, "depends": [],
         "options": ["NCR - 2 Layers", "NCR - 3 Layers", "NCR - 4 Layers", "NCR - 5 Layers", "NCR - 6 Layer"]},
        {"key": "colour", "label": "Print colour / side", "addon": True, "depends": [],
         "options": ["1C (Front)", "2C (Front)", "4C (Front)", "1C (Both)", "2C (Front) / 1C (Back)", "4C (Front) / 1C (Back)"]},
        {"key": "sets", "label": "Sets per book (2-ply only)", "addon": True, "depends": [], "options": ["50", "100"]},
        {"key": "binding", "label": "Binding location", "addon": True, "depends": [],
         "options": ["Portrait - Left side binding", "Portrait - Top side binding",
                     "Landscape - Left side binding", "Landscape - Top side binding"]},
        {"key": "numbering", "label": "Numbering (free)", "addon": True, "depends": [], "options": ["No", "Yes"]},
        {"key": "punch", "label": "Hole punch (6mm)", "addon": True, "depends": [], "options": ["No", "Yes"]},
    ]
    NOTEPAD_FIELDS = [
        {"key": "paper", "label": "Cover paper (weight only; no price change)", "addon": True, "depends": [],
         "options": ["Gloss Art Card 260gsm (2 side coated)", "Gloss Art Card 310gsm (2 side coated)"]},
        {"key": "lamination", "label": "Lamination (Matte Both compulsory; Spot UV quoted separately)", "addon": True, "depends": [],
         "options": ["Matte Lamination (Both)", "Matte Lamination (Both) + Spot UV (Front Cover)"]},
    ]
    products = [
        {"id": 1, "name": "Business Card", "engine": "bizcard", "optsrc": "bizcard",
         "accuracy": acc.get(1), "fields": BIZCARD_FIELDS},
        {"id": 104, "name": "Notepad — Litho", "engine": "notepad", "optsrc": "none",
         "accuracy": acc.get(104), "fields": NOTEPAD_FIELDS},
        {"id": 24, "name": "Bill-Book — Litho (NCR Carbonless)", "engine": "billbook",
         "optsrc": "none", "accuracy": acc.get(24), "fields": BILLBOOK_FIELDS},
        {"id": 60, "name": "Label Sticker — Digital", "engine": "sticker", "optsrc": "none",
         "accuracy": acc.get(60), "fields": STICKER_D_FIELDS, "stickerMethod": "digital"},
        {"id": 61, "name": "Label Sticker — Letterpress (Hot Stamping)", "engine": "sticker", "optsrc": "none",
         "accuracy": acc.get(61), "fields": STICKER_L_FIELDS, "stickerMethod": "letterpress"},
        {"id": 21, "name": "Loose Sheet — Litho (Offset)", "engine": "litho",
         "optsrc": "loose21", "accuracy": acc.get(21), "fields": LOOSE_FIELDS},
        {"id": 50, "name": "Loose Sheet — Digital", "engine": "digital",
         "optsrc": "digital50", "accuracy": acc.get(50), "fields": LOOSE_DIGITAL_FIELDS},
        {"id": 19, "name": "Booklet — Litho (Offset)", "engine": "booklet",
         "optsrc": "booklet19", "accuracy": acc.get(19), "fields": BOOKLET_FIELDS},
        {"id": 37, "name": "Booklet — Digital", "engine": "booklet",
         "optsrc": "booklet37", "accuracy": acc.get(37), "fields": BOOKLET_FIELDS},
        # Aliases of Loose Sheet Litho (same Excard order form) — reuse litho engine+options.
        {"id": 101, "name": "Brochure (= Loose Sheet Litho)", "engine": "litho",
         "optsrc": "loose21", "accuracy": acc.get(21), "fields": LOOSE_FIELDS},
        {"id": 102, "name": "Flyer (= Loose Sheet Litho)", "engine": "litho",
         "optsrc": "loose21", "accuracy": acc.get(21), "fields": LOOSE_FIELDS},
        {"id": 103, "name": "Customprint (= Loose Sheet Litho)", "engine": "litho",
         "optsrc": "loose21", "accuracy": acc.get(21), "fields": LOOSE_FIELDS},
    ]
    return {
        "products": products,
        "params": {
            "litho": _load("printoka_params.json")["params"],
            "digital": _load("printoka_params_digital.json"),
            "booklet19": _load("booklet_params_19.json")["params"],
            "booklet37": _load("booklet_params_37.json")["params"],
            "bizcard": _load("bizcard_params.json"),
            "sticker_digital": _load("sticker_params_digital.json"),
            "sticker_letterpress": _load("sticker_params_letterpress.json"),
            "billbook": _load("billbook_params.json", {"curves": {}, "size_factors": {}, "size_mm": {}}),
            "notepad": _load("notepad_params.json", {"curve": {}, "size_mm": [80, 106], "content_sheets": 40, "content_gsm": 80}),
        },
        "curves": {
            "booklet19": _load("booklet_curve_19.json", {}),
            "booklet37": _load("booklet_curve_37.json", {}),
            "loose21": _load("loose_curve_21.json", {}),
        },
        "finishing": _load("bizcard_finishing.json", {"surface": {}, "round_corner": {}, "hole_punch": {}}),
        "loose_finishing": _load("loose_finishing_50.json", {"hot_stamping": {}, "punch": {}, "fold": {}}),
        "sticker_categories": _load("sticker_categories.json", {"round": [], "standard_shape": [], "no_cut": [], "kiss_cut": []}),
        "stickerStdMult": (lambda: __import__("app.sticker_categories", fromlist=["_std_mult"])._std_mult())(),
        "multidieline": _multidieline_data(STICKER_MATS),
        "warranty": _load("sticker_warranty.json", {"sizes": [], "colour1C": 0.87}),
        "sticker_cd": _load("sticker_cd.json", {"curves": {}}),
        "sticker_finishing": _load("sticker_finishing.json", {}),
        "options": {
            "loose21": loose_cascade(),
            "digital50": {"sizes": digital["sizes"], "papers_by_size": digital["papers_by_size"]},
            "booklet19": _load("booklet_options_19.json")["combos"],
            "booklet37": _load("booklet_options_37.json")["combos"],
            "bizcard": bizcard_ct,
        },
        "engineByProduct": {1: "bizcard", 21: "litho", 50: "digital", 19: "booklet19",
                            37: "booklet37", 60: "sticker_digital", 61: "sticker_letterpress",
                            24: "billbook", 101: "litho", 102: "litho", 103: "litho",
                            104: "notepad"},
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
