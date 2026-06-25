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
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else default


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


# engine name (as used in the products list) -> key in the baked params dict
_PARAMS_KEY = {"deskcal_hard": "deskcal", "deskcal_soft": "deskcal"}
# curve-like keys; a product whose params has one of these and they're ALL empty is unsampled
_CURVE_KEYS = ("curve", "curves", "core", "data", "soft_curve", "hard_curves",
               "base_curves", "cover_curves")


def _params_unsampled(blob):
    """True only if the blob clearly has curve data that is entirely empty."""
    if not isinstance(blob, dict):
        return False
    present = [blob[k] for k in _CURVE_KEYS if k in blob]
    return bool(present) and all(not v for v in present)


def _drop_unsampled(data):
    """Hide products whose engine params have no sampled curve yet (avoid RM0 in the UI).
    They reappear automatically once their *_params.json is populated."""
    params = data["params"]
    kept = []
    for p in data["products"]:
        key = p.get("paramKey") or _PARAMS_KEY.get(p["engine"], p["engine"])
        if key in params and _params_unsampled(params[key]):
            print(f"  [skip unsampled] id={p['id']} {p['name']} (engine={p['engine']})")
            continue
        kept.append(p)
    data["products"] = kept
    return data


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
        {"key": "lamination", "label": "Lamination (Matte Both compulsory; +Spot UV adds a cost)", "addon": True, "depends": [],
         "options": ["Matte Lamination (Both)", "Matte Lamination (Both) + Spot UV (Front Cover)"]},
    ]
    LETTERHEAD_FIELDS = [
        {"key": "paper", "label": "Paper", "addon": True, "depends": [],
         "options": ["Simili 80gsm", "Simili 100gsm", "Conqueror 100gsm Brilliant White Laid",
                     "Conqueror 100gsm Diamond White Laid", "Conqueror 100gsm White Wove",
                     "Conqueror 100gsm Cream Laid"]},
        {"key": "colour", "label": "Print colour / side", "addon": True, "depends": [],
         "options": ["1C (Front)", "2C (Front)", "4C (Front)", "4C (Both)"]},
        {"key": "packing", "label": "Packing", "addon": True, "depends": [],
         "options": ["Loose", "Pad (100 pcs per pad)"]},
    ]
    MONEY_PACKET_FIELDS = [
        {"key": "model", "label": "Model (MP 101=154x79.5mm · MP 103=79.5x154mm · MP 104=85x167mm)", "addon": True, "depends": [],
         "options": ["MP 101", "MP 103", "MP 104"]},
        {"key": "package", "label": "Package (number of designs)", "addon": True, "depends": [],
         "options": ["Normal", "Dual Design", "5 Design", "6 Design"]},
        {"key": "paper", "label": "Paper", "addon": True, "depends": [],
         "options": ["Gloss Art Paper 130gsm", "Linen 140gsm", "Art Paper 157gsm"]},
        {"key": "finishing", "label": "Finishing", "addon": True, "depends": [],
         "options": ["N/A", "Matte Lamination", "Soft Touch Lamination"]},
        {"key": "packing", "label": "Packing method (price-neutral; for info)", "addon": True, "depends": [],
         "options": ["5pcs / Pack", "6pcs / Pack", "8pcs / Pack", "10pcs / Pack"]},
    ]
    TENT_CARD_FIELDS = [
        {"key": "model", "label": "Model (TC 003=294x86mm · TC 004=294x140mm)", "addon": True, "depends": [],
         "options": ["TC 003", "TC 004"]},
        {"key": "lamination", "label": "Lamination", "addon": True, "depends": [],
         "options": ["Matte Lamination (Both)", "Matte Lamination (Both) + Spot UV (Front)"]},
    ]
    NON_WOVEN_BAG_FIELDS = [
        {"key": "model", "label": "Model (determines size · WN-B5=200x230x80mm · WS-A4=280x330x80mm · WS-A3P=350x350x100mm · WS-A3L=420x320x100mm · WH-A4=280x330x80mm)", "addon": True, "depends": [],
         "options": ["WN-B5", "WS-A4", "WS-A3P", "WS-A3L", "WH-A4"]},
        {"key": "print_colour", "label": "Print Colour (WN/WS=1C only · WH=4C only)", "addon": True, "depends": [],
         "options": ["1C (Front)", "1C (Both)", "4C (Front)", "4C (Both)"]},
        {"key": "bag_colour", "label": "Bag Colour (price-neutral; for info)", "addon": True, "depends": [],
         "options": ["Black", "White", "Beige", "Yellow", "Orange", "Dark Orange", "Magenta", "Red",
                     "Maroon", "Green", "Milo Green", "Dark Green", "Turquoise", "Cyan",
                     "Royal Blue", "Navy Blue", "Dark Purple", "Light Brown", "Dark Brown", "Grey"]},
        {"key": "handle_length", "label": "Handle Length (price-neutral; for info)", "addon": True, "depends": [],
         "options": ["300mm", "440mm", "500mm"]},
        {"key": "handle_colour", "label": "Handle Colour (price-neutral; for info)", "addon": True, "depends": [],
         "options": ["Same as bag colour", "Black", "White", "Beige", "Orange", "Dark Orange", "Magenta",
                     "Red", "Maroon", "Green", "Milo Green", "Dark Green", "Turquoise", "Cyan",
                     "Royal Blue", "Navy Blue", "Dark Purple", "Light Brown", "Dark Brown", "Grey"]},
    ]
    ENVELOPE_MODELS = [
        "OE4496NW — 114x248mm (Best Seller)", "OE4496W — 114x248mm (window)",
        "OE9013NW — 229x324mm", "EV4090NW — 102x229mm", "EV4090W — 102x229mm (window)",
        "EV4286NW — 110x220mm", "EV4286W — 110x220mm (window)", "EV4496NW — 114x248mm",
        "EV4496W — 114x248mm (window)", "EV6390NW — 162x229mm", "EV7010NW — 178x254mm",
        "EV9013NW — 229x324mm", "EV1015NW — 254x381mm", "IS4286NW — 110x220mm",
        "IS6390NW — 162x229mm", "OP8642NW — 220x110mm", "OP6344NW — 162x114mm"]
    ENVELOPE_COLOURS = ["1C (Front)", "1C (Both)", "1C (Front)/2C (Back)", "1C (Front)/4C (Back)",
        "2C (Front)", "2C (Front)/1C (Back)", "2C (Both)", "2C (Front)/4C (Back)",
        "4C (Front)", "4C (Front)/1C (Back)", "4C (Front)/2C (Back)", "4C (Both)"]
    ENVELOPE_FIELDS = [
        {"key": "model", "label": "Envelope model (size / window)", "addon": True, "depends": [], "options": ENVELOPE_MODELS},
        {"key": "colour", "label": "Print colour / side", "addon": True, "depends": [], "options": ENVELOPE_COLOURS},
    ]
    products = [
        {"id": 1, "name": "Business Card", "engine": "bizcard", "optsrc": "bizcard",
         "accuracy": acc.get(1), "fields": BIZCARD_FIELDS},
        {"id": 104, "name": "Notepad — Litho", "engine": "notepad", "optsrc": "none",
         "accuracy": acc.get(104), "fields": NOTEPAD_FIELDS},
        {"id": 106, "name": "Envelope — Litho", "engine": "envelope", "optsrc": "none",
         "accuracy": acc.get(106), "fields": ENVELOPE_FIELDS},
        {"id": 107, "name": "Folder — Litho", "engine": "pricelist", "paramKey": "folder",
         "axisFields": ["model", "paper", "colour", "lamination", "protective"], "optsrc": "none",
         "accuracy": 0.0, "fields": [
            {"key": "model", "label": "Folder model", "addon": True, "depends": [], "options": [
                "FPF 001", "FPF 004", "FPF 005", "FPF 014", "FPF 015", "FPF 016",
                "FDF 001", "FDF 002", "FKF 001", "FKF 002", "FCD 004"]},
            {"key": "paper", "label": "Paper", "addon": True, "depends": [], "options": [
                "Gloss Art Card 210gsm (1 side coated)", "Gloss Art Card 250gsm (1 side coated)",
                "Gloss Art Card 260gsm (1 side coated)", "Gloss Art Card 300gsm (1 side coated)",
                "Gloss Art Card 230gsm (2 side coated)", "Gloss Art Card 250gsm (2 side coated)",
                "Gloss Art Card 310gsm (2 side coated)", "Gloss Art Card 360gsm (2 side coated)"]},
            {"key": "colour", "label": "Print colour", "addon": True, "depends": [], "options": ["4C (Front)", "4C (Both)"]},
            {"key": "lamination", "label": "Lamination", "addon": True, "depends": [], "options": [
                "Gloss Lamination (Front)", "Matte Lamination (Front)", "Matte Lamination (Front) + Spot UV (Front)",
                "Gloss Waterbase Varnish (Front)", "Gloss Lamination (Both)", "Matte Lamination (Both)",
                "Matte Lamination (Both) + Spot UV (Front)", "Gloss Waterbase Varnish (Both)"]},
            {"key": "protective", "label": "Colour protective layer (back)", "addon": True, "depends": [],
             "options": ["N/A", "Gloss Waterbase Varnish (Back)"]}]},
        {"id": 108, "name": "L-Shape Plastic Folder — Digital", "engine": "lshape", "optsrc": "none",
         "accuracy": acc.get(108), "fields": [
            {"key": "paper", "label": "Material", "addon": True, "depends": [],
             "options": ["Synthetic Paper 180micron", "Frosted Plastic 200 micron (0.2mm)"]}]},
        {"id": 118, "name": "Wall Calendar — Litho", "engine": "wallcal", "optsrc": "none",
         "accuracy": acc.get(118), "fields": []},
        {"id": 119, "name": "Arch File — Digital", "engine": "archfile", "optsrc": "none",
         "accuracy": acc.get(119), "fields": []},
        {"id": 120, "name": "Desk Calendar — Hard Stand (Litho)", "engine": "deskcal_hard", "optsrc": "none",
         "accuracy": acc.get(120), "fields": [
            {"key": "cat", "label": "Model", "addon": True, "depends": [], "options": [
                "WDCH 001 (Portrait)", "WDCH 002 (Landscape)", "DCHS 001 (Hot Stamping - Portrait)"]}]},
        {"id": 121, "name": "Desk Calendar — Soft Stand (Litho)", "engine": "deskcal_soft", "optsrc": "none",
         "accuracy": acc.get(121), "fields": []},
        {"id": 122, "name": "Wire-O Wall Calendar — Litho", "engine": "wireow", "optsrc": "none",
         "accuracy": acc.get(122), "fields": []},
        {"id": 123, "name": "Banner — Litho", "engine": "banner", "optsrc": "none",
         "accuracy": acc.get(123), "fields": [
            {"key": "size", "label": "Size", "addon": True, "depends": [], "options": [
                "3ft x 2ft", "4ft x 2ft", "6ft x 2ft", "4ft x 3ft", "8ft x 3ft",
                "10ft x 3ft", "18ft x 3ft", "8ft x 4ft", "10ft x 4ft", "20ft x 4ft"]}]},
        {"id": 124, "name": "Bunting — Litho", "engine": "simpleqty", "paramKey": "bunting",
         "optsrc": "none", "accuracy": acc.get(124), "fields": [
            {"key": "size", "label": "Size", "addon": True, "depends": [], "options": [
                "2ft x 5ft", "2ft x 6ft", "2.5ft x 6ft"]},
            {"key": "paper", "label": "Material", "addon": True, "depends": [], "options": ["Tarpaulin 300gsm"]},
            {"key": "protective", "label": "Fitting", "addon": True, "depends": [], "options": [
                "Wood", "PVC Pipe", "Wood+Wire"]}]},
        {"id": 125, "name": "Roll-Up Stand — Litho", "engine": "rollup", "optsrc": "none",
         "accuracy": acc.get(125), "fields": [
            {"key": "lam", "label": "Lamination", "addon": True, "depends": [], "options": [
                "Matte Lamination", "Gloss Lamination"]}]},
        {"id": 126, "name": "Wobbler — Digital", "engine": "wobbler", "optsrc": "none",
         "accuracy": acc.get(126), "fields": [
            {"key": "orient", "label": "Orientation", "addon": True, "depends": [], "options": [
                "Portrait", "Landscape"]},
            {"key": "paper", "label": "Paper", "addon": True, "depends": [], "options": [
                "Gloss Art Card 250gsm", "Gloss Art Card 310gsm"]},
            {"key": "lam", "label": "Lamination", "addon": True, "depends": [], "options": [
                "Matte Lamination (Front)", "Gloss Lamination (Front)"]},
            {"key": "finishing", "label": "Finishing", "addon": True, "depends": [], "options": [
                "-", "Round Cornering (R6),4,1", "Digital Die-cutting,0,0"]}]},
        {"id": 127, "name": "Paper Bag — Litho", "engine": "paperbag", "optsrc": "none",
         "accuracy": acc.get(127), "fields": [
            {"key": "paper", "label": "Paper", "addon": True, "depends": [], "options": [
                "Gloss Art Paper 157gsm", "Gloss Art Card 190gsm (1 side coated)"]}]},
        {"id": 128, "name": "Canvas Tote Bag — Litho", "engine": "canvastote", "optsrc": "none",
         "accuracy": acc.get(128), "fields": [
            {"key": "colour", "label": "Print colour", "addon": True, "depends": [], "options": [
                "1C (Front)", "1C (Both)"]}]},
        {"id": 129, "name": "Mug — Litho", "engine": "mug", "optsrc": "none",
         "accuracy": acc.get(129), "fields": []},
        {"id": 130, "name": "Papan Kopi / Sachet Board — Litho", "engine": "pricelist", "paramKey": "papan_kopi",
         "axisFields": ["model"], "optsrc": "none", "accuracy": 0.0,
         "fields": [
            {"key": "model", "label": "Model (SB 01=537x334mm 20win · SB 02=622x346mm 20win · SB 03=547x346mm 20win · SB 04=547x346mm 15win)", "addon": True, "depends": [],
             "options": ["SB 01", "SB 02", "SB 03", "SB 04"]},
         ]},
        {"id": 131, "name": "Pillow — Litho", "engine": "pillow", "optsrc": "none",
         "accuracy": acc.get(131), "fields": []},
        {"id": 132, "name": "Button Badge — Digital", "engine": "simpleqty", "paramKey": "buttonbadge",
         "optsrc": "none", "accuracy": acc.get(132), "fields": [
            {"key": "lamination", "label": "Lamination (price-neutral)", "addon": True, "depends": [],
             "options": ["Gloss", "Soft Touch"]}]},
        {"id": 133, "name": "Hand Fan — Digital", "engine": "simpleqty", "paramKey": "handfan",
         "optsrc": "none", "accuracy": acc.get(133), "fields": [
            {"key": "paper", "label": "Paper", "addon": True, "depends": [],
             "options": ["Gloss Art Card 310gsm", "Gloss Art Card 360gsm"]},
            {"key": "lamination", "label": "Lamination (priced at Matte Both)", "addon": True, "depends": [],
             "options": ["Matte Lamination (Both)", "Gloss Lamination (Both)"]}]},
        {"id": 134, "name": "Hanger — Digital", "engine": "simpleqty", "paramKey": "hanger",
         "optsrc": "none", "accuracy": acc.get(134), "fields": [
            {"key": "paper", "label": "Paper", "addon": True, "depends": [],
             "options": ["Gloss Art Card 310gsm (2 sides coated)", "Gloss Art Card 360gsm (2 sides coated)"]},
            {"key": "colour", "label": "Print colour / side", "addon": True, "depends": [],
             "options": ["4C (Front)", "4C (Both)"]},
            {"key": "lamination", "label": "Lamination (priced at Matte Both)", "addon": True, "depends": [],
             "options": ["Matte Lamination (Both)", "Gloss Lamination (Both)"]}]},
        {"id": 135, "name": "Magnet — Digital", "engine": "simpleqty", "paramKey": "magnet",
         "optsrc": "none", "accuracy": acc.get(135), "fields": [
            {"key": "shape", "label": "Shape", "addon": True, "depends": [],
             "options": ["Rectangle/Square", "Round", "Custom Die-Cut"]},
            {"key": "finishing", "label": "Finishing (Soft Touch ~+RM4)", "addon": True, "depends": [],
             "options": ["Matte Laminate (Front)", "Gloss Laminate (Front)", "Soft Touch Laminate (Front)"]}]},
        {"id": 136, "name": "Hard Cover Menu — Digital", "engine": "simpleqty", "paramKey": "hardmenu",
         "optsrc": "none", "accuracy": acc.get(136), "fields": [
            {"key": "order", "label": "Order", "addon": True, "depends": [],
             "options": ["Cover + Content", "Cover only", "Content only"]},
            {"key": "addcontent", "label": "Add content sheets (Cover only: -)", "addon": True, "depends": [],
             "options": ["12", "16", "-"]},
            {"key": "lamination", "label": "Lamination (price-neutral)", "addon": True, "depends": [],
             "options": ["Gloss Lamination (Both)", "Matte Lamination (Both)"]}]},
        {"id": 137, "name": "Standing Pouch — Litho", "engine": "simpleqty", "paramKey": "pouch",
         "optsrc": "none", "accuracy": acc.get(137), "fields": [
            {"key": "paper", "label": "Material", "addon": True, "depends": [],
             "options": ["Metalised Pet Film"]},
            {"key": "lamination", "label": "Lamination (price-neutral)", "addon": True, "depends": [],
             "options": ["Matte Lamination", "Gloss Lamination"]}]},
        {"id": 138, "name": "Money Packet — Litho", "engine": "pricelist", "paramKey": "money_packet",
         "axisFields": ["model", "package", "paper", "finishing"], "optsrc": "none",
         "accuracy": 0.0, "fields": MONEY_PACKET_FIELDS},
        {"id": 139, "name": "Non-Woven Bag — Litho", "engine": "pricelist", "paramKey": "non_woven_bag",
         "axisFields": ["model", "print_colour"], "optsrc": "none",
         "accuracy": 0.0, "fields": NON_WOVEN_BAG_FIELDS},
        {"id": 140, "name": "Tent Card — Litho", "engine": "pricelist", "paramKey": "tent_card",
         "axisFields": ["model", "lamination"], "optsrc": "none",
         "accuracy": 0.0, "fields": TENT_CARD_FIELDS},
        {"id": 141, "name": "Stamp Chop", "engine": "stamp", "optsrc": "stamp_chop",
         "accuracy": 0.0, "fields": [
             {"key": "stamp_type", "label": "Stamp Type", "optionsKey": "stamp_types", "depends": []},
             {"key": "category", "label": "Category", "optionsKey": "categories", "depends": ["stamp_type"]},
             {"key": "model_key", "label": "Model", "optionsKey": "model_keys", "depends": ["stamp_type", "category"]},
         ]},
        {"id": 142, "name": "Mask Keeper — Litho", "engine": "contact", "optsrc": "none",
         "accuracy": None, "fields": [],
         "note": "No automated pricing available. Contact Excard directly for a quote."},
        {"id": 143, "name": "Sublimation Shirt", "engine": "contact", "optsrc": "none",
         "accuracy": None, "fields": [],
         "note": "No automated pricing available. Contact Excard directly for a quote."},
        {"id": 116, "name": "Static Cling Window Sticker — Digital", "engine": "staticcling", "optsrc": "none",
         "accuracy": acc.get(116), "fields": [
            {"key": "size", "label": "Size", "addon": True, "depends": [], "options": [
                "54mm x 89mm", "75mm x 75mm", "100mm x 100mm", "110mm x 90mm", "115mm x 120mm",
                "130mm x 170mm", "165mm x 90mm", "220mm x 90mm", "104mm x 420mm", "310mm x 445mm"]},
            {"key": "direction", "label": "Print direction", "addon": True, "depends": [], "options": ["Face Out View", "Face In View", "Both Side View"]},
            {"key": "vdp", "label": "Variable Data Printing", "addon": True, "depends": [], "options": ["Not Required", "Variable Data Printing (VDP)"]}]},
        {"id": 117, "name": "Car Sticker — Digital (= Static Cling form)", "engine": "staticcling", "optsrc": "none",
         "accuracy": acc.get(117), "fields": [
            {"key": "size", "label": "Size", "addon": True, "depends": [], "options": [
                "54mm x 89mm", "75mm x 75mm", "100mm x 100mm", "110mm x 90mm", "115mm x 120mm",
                "130mm x 170mm", "165mm x 90mm", "220mm x 90mm", "104mm x 420mm", "310mm x 445mm"]},
            {"key": "direction", "label": "Print direction", "addon": True, "depends": [], "options": ["Face Out View", "Face In View", "Both Side View"]},
            {"key": "vdp", "label": "Variable Data Printing", "addon": True, "depends": [], "options": ["Not Required", "Variable Data Printing (VDP)"]}]},
        {"id": 115, "name": "Kad Terima Kasih — Digital", "engine": "kadterima", "optsrc": "none",
         "accuracy": acc.get(115), "fields": [
            {"key": "size", "label": "Size", "addon": True, "depends": [], "options": ["52mm x 52mm", "40mm x 86mm", "40mm x 70mm"]},
            {"key": "paper", "label": "Paper", "addon": True, "depends": [], "options": [
                "Gloss Art Card 230gsm (2 sides coated)", "Gloss Art Card 260gsm (2 sides coated)",
                "Gloss Art Card 310gsm (2 sides coated)", "Gloss Art Card 360gsm (2 sides coated)",
                "Super White 240gsm", "Metal Ice 250gsm"]},
            {"key": "colour", "label": "Print colour / side", "addon": True, "depends": [], "options": ["4C (Front)", "4C (Both)"]},
            {"key": "lamination", "label": "Lamination (no online price change)", "addon": True, "depends": [], "options": ["Matte Lamination (Front)", "Matte Lamination (Both)", "Gloss Lamination (Front)", "Gloss Lamination (Both)"]},
            {"key": "hole_punch", "label": "Hole punching (3mm)", "addon": True, "depends": [], "options": ["No", "Yes"]}]},
        {"id": 114, "name": "Kad Kahwin — Digital", "engine": "kadkahwin", "optsrc": "none",
         "accuracy": acc.get(114), "fields": [
            {"key": "ordertype", "label": "Order type", "addon": True, "depends": [], "options": ["Standard Kad Kahwin", "Custom Die-cut Kad Kahwin"]},
            {"key": "size", "label": "Size", "addon": True, "depends": [], "options": [
                "DL (99mm x 210mm)", "2DL (198mm x 210mm)", "A7 (74mm x 105mm)", "A6 (105mm x 148mm)",
                "A5 (148mm x 210mm)", "A4 (210mm x 297mm)", "Square (140mm x 280mm)"]},
            {"key": "paper", "label": "Paper", "addon": True, "depends": [], "options": [
                "Gloss Art Card 230gsm (2 sides coated)", "Gloss Art Card 260gsm (2 sides coated)",
                "Gloss Art Card 310gsm (2 sides coated)", "Gloss Art Card 360gsm (2 sides coated)",
                "Super White 240gsm", "Linen 240gsm", "Suwen 240gsm", "Simili 140gsm",
                "Metal Ice 250gsm", "Matte Art Paper 150gsm"]},
            {"key": "colour", "label": "Print colour / side", "addon": True, "depends": [], "options": ["4C (Front)", "4C (Both)"]},
            {"key": "lamination", "label": "Lamination (no online price change)", "addon": True, "depends": [], "options": ["Matte Lamination (Front)", "Matte Lamination (Both)", "Gloss Lamination (Front)", "Gloss Lamination (Both)"]},
            {"key": "envelope", "label": "Envelope (no online price change)", "addon": True, "depends": [], "options": ["Not Required", "White", "Pink"]},
            {"key": "hot_stamping", "label": "Hot stamping (quoted separately)", "addon": True, "depends": [], "options": ["Not Required", "1C (Front)", "1C (Back)", "2C (Front)", "2C (Back)"]}]},
        {"id": 113, "name": "PVC Card — Digital", "engine": "pricelist", "paramKey": "pvccard",
         "axisFields": ["colour", "hole_punch", "vdp"], "optsrc": "none",
         "accuracy": 0.0, "fields": [
            {"key": "colour", "label": "Print colour", "addon": True, "depends": [], "options": ["4C (Front)", "4C (Both)"]},
            {"key": "hole_punch", "label": "Hole punching", "addon": True, "depends": [],
             "options": ["Not Required", "Hole Punching (6mm)"]},
            {"key": "vdp", "label": "Variable Data Printing", "addon": True, "depends": [],
             "options": ["Not Required", "Variable Data Printing (Front)",
                         "Variable Data Printing (Back)", "Variable Data Printing (Both)"]}]},
        {"id": 112, "name": "Wire-O Notebook — Litho", "engine": "wireo", "optsrc": "none",
         "accuracy": acc.get(112), "fields": [
            {"key": "cover", "label": "Cover type", "addon": True, "depends": [], "options": ["Hard Cover", "VDP Hard Cover", "Soft Cover"]},
            {"key": "lamination", "label": "Cover lamination (compulsory)", "addon": True, "depends": [], "options": [
                "Matte Lamination (Front)", "Gloss Lamination (Front)",
                "Matte Lamination (Front) + Spot UV (Front Cover)", "Matte Lamination (Front) + Spot UV (Front and Back Cover)"]},
            {"key": "addcontent", "label": "Additional content sheets", "addon": True, "depends": [], "options": ["Not Required", "4 sheets", "8 sheets", "12 sheets"]},
            {"key": "hot_stamping", "label": "Cover hot stamping (quoted separately)", "addon": True, "depends": [], "options": ["Not Required", "1C (Front Cover)", "2C (Front Cover)", "1C (Front & Back Cover)", "2C (Front & Back Cover)"]}]},
        {"id": 111, "name": "Computer Form — Litho (NCR)", "engine": "computerform", "optsrc": "none",
         "accuracy": acc.get(111), "fields": [
            {"key": "package", "label": "Package", "addon": True, "depends": [], "options": ["Multi Layer Computer Form", "Single Layer Computer Form", "Pay Slip"]},
            {"key": "layers", "label": "Layers / plies (Multi Layer only)", "addon": True, "depends": [], "options": ["2", "3", "4", "5"]},
            {"key": "ups", "label": "Ups (forms per set)", "addon": True, "depends": [], "options": ["1", "2", "3"]},
            {"key": "colour", "label": "Print colour", "addon": True, "depends": [], "options": ["1C", "2C", "4C"]},
            {"key": "copychange", "label": "Copy change (no online price change)", "addon": True, "depends": [], "options": ["No", "Yes"]},
            {"key": "numbering", "label": "Numbering (quoted separately)", "addon": True, "depends": [], "options": ["No", "Yes"]}]},
        {"id": 110, "name": "Voucher — Litho", "engine": "voucher", "optsrc": "none",
         "accuracy": acc.get(110), "fields": [
            {"key": "packform", "label": "Form", "addon": True, "depends": [], "options": ["Pad", "Book", "Loose"]},
            {"key": "size", "label": "Size", "addon": True, "depends": [], "options": [
                "90mm x 140mm", "105mm x 145mm", "145mm x 145mm", "125mm x 175mm", "90mm x 190mm",
                "107mm x 190mm", "60mm x 210mm", "145mm x 210mm", "55mm x 213mm", "95mm x 225mm",
                "120mm x 230mm", "105mm x 300mm"]},
            {"key": "paper", "label": "Content paper", "addon": True, "depends": [], "options": [
                "Art Paper 100gsm", "Art Paper 130gsm", "Art Paper 150gsm", "Matte Art Paper 150gsm",
                "Colour Paper Buff 75gsm", "Colour Paper Blue 75gsm", "Colour Paper Green 75gsm",
                "Colour Paper Pink 75gsm", "Colour Paper Purple 75gsm", "Colour Paper Yellow 75gsm",
                "Simili 80gsm", "Simili 100gsm", "Art Card 230gsm (2 sides coated)", "Art Card 260gsm (2 sides coated)"]},
            {"key": "colour", "label": "Content colour", "addon": True, "depends": [], "options": ["4C (Front)", "4C (Both)"]},
            {"key": "sets", "label": "Sets per book/pad", "addon": True, "depends": [], "options": ["10", "25", "50"]},
            {"key": "perforation", "label": "Perforation lines (no online price change)", "addon": True, "depends": [], "options": ["0", "1", "2"]},
            {"key": "numbering", "label": "Numbering", "addon": True, "depends": [], "options": ["No", "Yes"]}]},
        {"id": 109, "name": "Bookmark — Digital", "engine": "bookmark", "optsrc": "none",
         "accuracy": acc.get(109), "fields": [
            {"key": "paper", "label": "Paper", "addon": True, "depends": [],
             "options": ["Gloss Art Card 250gsm (2 sides coated)", "Gloss Art Card 310gsm (2 sides coated)",
                         "Super White 250gsm", "Linen 240gsm", "Suwen 240gsm", "Synthetic Paper 180micron",
                         "Metal Ice 250gsm"]},
            {"key": "colour", "label": "Print colour / side", "addon": True, "depends": [], "options": ["4C (Front)", "4C (Both)"]},
            {"key": "lamination", "label": "Lamination (no online price change)", "addon": True, "depends": [], "options": ["Not Required", "Matte Lamination (Both)", "Gloss Lamination (Both)"]},
            {"key": "round_corner", "label": "Round cornering (R6)", "addon": True, "depends": [], "options": ["No", "Yes"]},
            {"key": "hole_punch", "label": "Hole punching (6mm)", "addon": True, "depends": [], "options": ["No", "Yes"]}]},
        {"id": 105, "name": "Letterhead — Litho", "engine": "pricelist", "paramKey": "letterhead",
         "axisFields": ["paper", "colour", "packing"], "optsrc": "none",
         "accuracy": 0.0, "fields": LETTERHEAD_FIELDS},
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
            "letterhead": _load("letterhead_pl_params.json", {"axis_cols": [], "curves": {}}),
            "envelope": _load("envelope_params.json", {"base_curves": {}, "sizes": {}, "colour_delta": {}, "env_gsm": 100}),
            "folder": _load("folder_pl_params.json", {"axis_cols": [], "curves": {}}),
            "lshape": _load("lshape_params.json", {"curves": {}, "size_mm": [310, 442]}),
            "bookmark": _load("bookmark_params.json", {"curves": {}, "fin_delta": {}, "size_mm": [50, 150]}),
            "voucher": _load("voucher_params.json", {"core": {}, "paper_f": {}, "colour_f": {}, "sets_f": {}, "packform_f": {}, "size_f": {}, "perf_d": {}, "numbering_d": {}, "ref": {}}),
            "computerform": _load("computerform_params.json", {"core": {}, "single": {}, "payslip": {}, "layer_f": {}, "ups_f": {}, "colour_f": {}, "copychange_d": [], "numbering_d": [], "size_mm": [241.3, 279.4], "ncr_gsm": 55}),
            "wireo": _load("wireo_params.json", {"cover_curves": {}, "lam_delta": {}, "addc_delta": {}, "cover_wt": {}, "ref_lam": ""}),
            "pvccard": _load("pvccard_pl_params.json", {"axis_cols": [], "curves": {}}),
            "kadkahwin": _load("kadkahwin_params.json", {"core": {}, "size_f": {}, "paper_f": {}, "colour_f": {}, "ordertype_f": {}, "ref": {}}),
            "kadterima": _load("kadterima_params.json", {"core": {}, "size_f": {}, "paper_f": {}, "colour_f": {}, "hp_delta": [], "ref": {}}),
            "staticcling": _load("staticcling_params.json", {"core": {}, "size_f": {}, "direction_f": {}, "vdp_f": {}, "ref": {}, "cling_gsm": 200}),
            "wallcal": _load("wallcal_params.json", {"curve": {}, "size_mm": [260, 265], "content_sheets": 12, "content_gsm": 60, "back_gsm": 300}),
            "archfile": _load("archfile_params.json", {"curve": {}, "unit_wt": 0.42}),
            "deskcal": _load("deskcal_params.json", {"soft_curve": {}, "hard_curves": {}, "hard_unit_kg": 0.35, "soft_unit_kg": 0.25}),
            "wireow": _load("wireow_params.json", {"curve": {}, "unit_kg": 0.30}),
            "banner": _load("banner_params.json", {"curves": {}, "sizes": [], "material_gsm": 400, "ft_to_m": 0.3048}),
            "bunting": _load("bunting_params.json", {"curves": {}, "sizes": [], "papers": [], "paper_gsm": {}}),
            "rollup": _load("rollup_params.json", {"curves": {}, "lams": [], "stand_w_m": 0.85, "stand_h_m": 2.0, "material_gsm": 400}),
            "wobbler": _load("wobbler_params.json", {"curves": {}, "orients": [], "papers": [], "lams": [], "finishings": [], "paper_gsm": {}, "wobbler_w_m": 0.095, "wobbler_h_m": 0.21, "finish_deltas": {}}),
            "paperbag": _load("paperbag_params.json", {"curves": {}, "papers": [], "paper_gsm": {}, "bag_sheet_m2": 0.16}),
            "canvastote": _load("canvastote_params.json", {"curves": {}, "colours": [], "bag_w_m": 0.38, "bag_h_m": 0.42, "canvas_gsm": 250}),
            "mug": _load("mug_params.json", {"curve": {}, "mug_kg": 0.35}),
            "papan_kopi": _load("papan_kopi_pl_params.json", {"axis_cols": [], "curves": {}}),
            "pillow": _load("pillow_params.json", {"curve": {}, "pillow_kg": 0.60}),
            "buttonbadge": _load("buttonbadge_params.json", {"curves": {}, "variant_field": "", "unit_wt": 0.012}),
            "handfan": _load("handfan_params.json", {"curves": {}, "variant_field": "paper", "unit_wt": 0.02}),
            "hanger": _load("hanger_params.json", {"curves": {}, "variant_field": ["paper", "colour"], "unit_wt": 0.03}),
            "magnet": _load("magnet_params.json", {"curves": {}, "variant_field": "shape", "unit_wt": 0.012}),
            "hardmenu": _load("hardmenu_params.json", {"curves": {}, "variant_field": ["order", "addcontent"], "unit_wt": 0.30}),
            "pouch": _load("pouch_params.json", {"curves": {}, "variant_field": "paper", "unit_wt": 0.015}),
            "money_packet": _load("money_packet_pl_params.json", {"axis_cols": [], "curves": {}, "unit_wt": 0.006}),
            "non_woven_bag": _load("non_woven_bag_pl_params.json", {"axis_cols": [], "curves": {}}),
            "tent_card": _load("tent_card_pl_params.json", {"axis_cols": [], "curves": {}}),
            "stamp_chop": _load("stamp_chop_prices.json", {}),
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
                            104: "notepad", 105: "letterhead", 106: "envelope", 107: "folder",
                            108: "lshape", 109: "bookmark", 110: "voucher", 111: "computerform",
                            112: "wireo", 113: "pvccard", 114: "kadkahwin", 115: "kadterima",
                            116: "staticcling", 117: "staticcling", 118: "wallcal", 119: "archfile",
                            120: "deskcal_hard", 121: "deskcal_soft", 122: "wireow",
                            123: "banner", 124: "bunting", 125: "rollup", 126: "wobbler",
                            127: "paperbag", 128: "canvastote", 129: "mug",
                            130: "papan_kopi", 131: "pillow", 132: "buttonbadge", 133: "handfan",
                            134: "hanger", 135: "magnet", 136: "hardmenu", 137: "pouch",
                            138: "money_packet", 139: "non_woven_bag",
                            140: "tent_card", 141: "stamp_chop",
                            142: "contact", 143: "contact"},
    }


def _attach_images(data):
    """Bake Excard option images into image-bearing fields (envelope mould / folder mould)."""
    imgs = _load("option_images.json")
    if not imgs:
        return
    # map engine -> image family
    fam_by_engine = {"envelope": "envelope", "folder": "folder"}
    for prod in data["products"]:
        fam = fam_by_engine.get(prod.get("engine"))
        if not fam or fam not in imgs:
            continue
        for fld in prod["fields"]:
            if fld["key"] in imgs[fam]:
                fld["images"] = imgs[fam][fld["key"]]


def main():
    data = build_data()
    _drop_unsampled(data)
    _attach_images(data)
    tmpl = (UI / "_standalone_template.html").read_text(encoding="utf-8")
    html = tmpl.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False))
    (UI / "calculator_standalone.html").write_text(html, encoding="utf-8")
    sizes = {k: len(json.dumps(v)) for k, v in data["options"].items()}
    print("wrote ui/calculator_standalone.html")
    print("products:", [p["name"] for p in data["products"]])
    print("option sizes (chars):", sizes)


if __name__ == "__main__":
    main()
