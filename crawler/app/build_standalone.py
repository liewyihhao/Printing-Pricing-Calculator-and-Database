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
    return {1: 0.0,    # bizcard Standard: EXACT v4 CheckPrice pricelist (2160 curves)
            21: 1.7, 50: 1.3, 19: 0.5, 37: 1.6, 60: 6.3, 61: 10.5, 24: 2.5,
            110: 0.0,
            111: 4.0,   # computer form: factor model, LOO ~4%
            114: 0.0,   # kad kahwin: EXACT v4 CheckPrice pricelist (154 curves)
            131: 0.0,   # pillow: LOO 0.03% (effectively exact, no markup)
            135: 1.0,   # magnet: per-shape curve LOO median ~1%
            }


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
    # Post-print finishing add-ons. Priced by Excard's finishing line independent of the
    # print method, so litho (21) and digital (50) loose sheets share the same dataset.
    LOOSE_FINISHING_FIELDS = [
        {"key": "hot_stamping", "label": "Hot stamping", "addon": True, "depends": [],
         "options": ["Not Required", "1C (Front)", "1C (Back)", "2C (Front)", "2C (Back)"]},
        {"key": "fold", "label": "Folding", "addon": True, "depends": [],
         "options": ["None", "1Fa", "2Fa", "2Fb", "2Fc", "3Fa", "3Fb", "4Fa", "4Fb"]},
        {"key": "punch", "label": "Hole punching", "addon": True, "depends": [], "options": ["No", "3mm", "6mm"]},
        # Lamination / Round Corner / Perforation — from Excard's Loose Sheet (www /spec/Litho/Loose_Sheet)
        # spec page (option labels documented there; the form's progressive UI did not expose them to capture).
        {"key": "lamination", "label": "Lamination / Finishing", "addon": True, "depends": [],
         "options": ["Not Required", "Gloss Lamination (Front)", "Gloss Lamination (Both)",
                     "Matte Lamination (Front)", "Matte Lamination (Both)",
                     "UV Varnish (Front)", "UV Varnish (Both)",
                     "Gloss Water Based Varnish (Front)", "Gloss Water Based Varnish (Both)"]},
        {"key": "round_corner", "label": "Round corner", "addon": True, "depends": [],
         "options": ["Not Required", "Required"]},
        {"key": "perforation", "label": "Perforation line(s)", "addon": True, "depends": [],
         "options": ["Not Required", "1 Perforation Line", "2 Perforation Lines"]},
    ]
    LOOSE_LITHO_FIELDS = LOOSE_FIELDS + LOOSE_FINISHING_FIELDS
    LOOSE_DIGITAL_FIELDS = LOOSE_FIELDS + LOOSE_FINISHING_FIELDS
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
        {"key": "design_source", "label": "Design", "addon": True, "depends": [],
         "options": ["Custom Made Money Packet", "Ready Designed with Editor"],
         "note": "Upload your own design, or start from a ready-made design in the editor — the print price is the same."},
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
        {"id": 1, "name": "Business Card", "engine": "pricelist",
         "note": "Standard Card. Exact per size+paper+colour+lamination+package(ganging) curves "
                 "from the v4 order engine (/Product/CheckPrice), 2160 combos. Thin/Fat Fold, "
                 "Custom Die-Cut & Plastic Card variants quoted separately."},
        {"id": 104, "name": "Notepad — Litho", "engine": "notepad", "optsrc": "none",
         "accuracy": acc.get(104), "fields": NOTEPAD_FIELDS},
        {"id": 106, "name": "Envelope — Litho", "engine": "envelope", "optsrc": "none",
         "accuracy": 0.0, "fields": ENVELOPE_FIELDS},
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
                "10ft x 3ft", "8ft x 4ft", "10ft x 4ft", "18ft x 3ft", "20ft x 4ft",
                "2ft x 3ft", "2ft x 4ft", "2ft x 6ft", "3ft x 4ft", "3ft x 8ft",
                "3ft x 10ft", "4ft x 8ft", "4ft x 10ft", "3ft x 18ft", "4ft x 20ft"]},
            {"key": "material", "label": "Material (no price change)", "addon": True, "depends": [], "options": [
                "Tarpaulin 300gsm", "Tarpaulin 380gsm"]},
            {"key": "top_eyelet", "label": "Top Eyelet", "addon": True, "depends": [], "options": ["2", "3", "4", "5"]},
            {"key": "bot_eyelet", "label": "Bottom Eyelet", "addon": True, "depends": [], "options": ["2", "3", "4", "5"]}]},
        {"id": 124, "name": "Bunting — Litho", "engine": "simpleqty", "paramKey": "bunting",
         "optsrc": "none", "accuracy": acc.get(124), "fields": [
            {"key": "size", "label": "Size", "addon": True, "depends": [], "options": [
                "2ft x 5ft", "2ft x 6ft", "2.5ft x 6ft"]},
            {"key": "paper", "label": "Material", "addon": True, "depends": [], "options": [
                "Tarpaulin 300gsm", "Synthetic Paper 180micron"]},
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
            {"key": "model", "label": "Model (W x D x H)", "addon": True, "depends": [], "options": [
                "PBG 001 (180x80x230mm)", "PBG 002 (220x80x230mm)", "PBG 003 (250x95x350mm)",
                "PBG 004 (200x95x290mm)", "PBG 005 (320x95x230mm)",
                "PBG 006 (370x120x295mm)", "PBG 007 (320x120x420mm)"]},
            {"key": "paper", "label": "Paper", "addon": True, "depends": [], "options": [
                "Gloss Art Paper 157gsm", "Gloss Art Card 190gsm"]},
            {"key": "lamination", "label": "Lamination", "addon": True, "depends": [],
             "options": ["Gloss Lamination", "Matte Lamination", "Matte Lamination + Spot UV"]},
            {"key": "rope_colour", "label": "Rope Colour (price-neutral)", "addon": True, "depends": [],
             "options": ["Black", "Blue", "Red", "White", "Gold", "Green", "Silver"]}]},
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
             "options": ["Rectangle/Square", "Round", "Custom Die-Cut (with round corner)", "Multiple Dieline"]},
            {"key": "size", "label": "Size (Rectangle / Custom Die-Cut)", "addon": True, "depends": [],
             "options": ["50mm × 35mm", "70mm × 45mm", "90mm × 54mm", "90mm × 90mm",
                         "100mm × 70mm", "120mm × 80mm", "148mm × 105mm"]},
            {"key": "finishing", "label": "Finishing (price-neutral)", "addon": True, "depends": [],
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
             "options": ["Metalised Pet Film", "Transparent Pet Film"]},
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
             {"key": "ink_colour", "label": "Ink Colour (no price change)", "addon": True, "depends": [],
              "options": ["Red", "Black", "Blue", "Violet", "Green", "Brown", "Pink", "Orange", "Yellow", "Sky Blue"]},
         ]},
        {"id": 142, "name": "Mask Keeper — Litho", "engine": "contact", "optsrc": "none",
         "accuracy": None, "fields": [],
         "note": "No automated pricing available. Contact us directly for a quote."},
        {"id": 143, "name": "Sublimation Shirt", "engine": "pricelist",
         "note": "Adult, size M, no VDP. Exact curves from the readymade order engine "
                 "(/Product/CheckPrice). VDP quoted separately."},
        {"id": 144, "name": "Cooler Bag — Litho", "engine": "pricelist"},
        {"id": 145, "name": "DTF Tote Bag With Zip — Litho", "engine": "pricelist"},
        {"id": 146, "name": "Heat Transfer Tote Bag — Litho", "engine": "pricelist"},
        {"id": 147, "name": "Laminated Non-Woven Bag — Litho", "engine": "pricelist"},
        {"id": 148, "name": "RPET Non-Woven Bag — Litho", "engine": "pricelist"},
        {"id": 149, "name": "Toast Bag — Litho", "engine": "pricelist"},
        {"id": 150, "name": "3-Side Seal Packaging — Litho", "engine": "pricelist"},
        {"id": 151, "name": "Kraft Standing Pouch — Litho", "engine": "pricelist"},
        {"id": 152, "name": "Standing Pouch with Spout — Litho", "engine": "pricelist"},
        {"id": 153, "name": "Vacuum Bag Packaging — Litho", "engine": "pricelist"},
        {"id": 154, "name": "Foamboard — Digital", "engine": "pricelist"},
        {"id": 155, "name": "Foamboard with Magnet — Digital", "engine": "pricelist"},
        {"id": 156, "name": "Foldable POP Display — Digital", "engine": "pricelist"},
        {"id": 157, "name": "POP Display — Digital", "engine": "pricelist"},
        {"id": 158, "name": "Wind Flag — Digital", "engine": "pricelist"},
        {"id": 159, "name": "Economy Roll-Up Stand — Digital", "engine": "pricelist"},
        {"id": 160, "name": "Bunting — Gear X Stand", "engine": "pricelist"},
        {"id": 161, "name": "Bunting — Round Base Stand", "engine": "pricelist"},
        {"id": 162, "name": "Bunting — Tripod Stand", "engine": "pricelist"},
        {"id": 163, "name": "Exclusive Leather Cover Wire-O Notebook — Litho", "engine": "pricelist"},
        {"id": 164, "name": "Hard Cover Perfect Bind Notebook — Litho", "engine": "pricelist"},
        {"id": 165, "name": "Creative Cut Card — Digital", "engine": "pricelist"},
        {"id": 166, "name": "Greeting Card — Litho", "engine": "pricelist"},
        {"id": 167, "name": "Premium Money Packet — Litho", "engine": "pricelist"},
        {"id": 168, "name": "Hot Stamping Money Packet — Litho", "engine": "pricelist"},
        {"id": 169, "name": "Envelope Money Packet — Litho", "engine": "pricelist"},
        {"id": 170, "name": "ID Card — Digital", "engine": "contact", "optsrc": "none",
         "accuracy": None, "fields": [
            {"key": "orientation", "label": "Orientation", "addon": True, "depends": [], "options": ["Portrait", "Landscape"]},
            {"key": "colour", "label": "Print colour", "addon": True, "depends": [], "options": ["4C (Front)", "4C (Both)"]},
            {"key": "quantity_hint", "label": "Available quantities (pcs)", "addon": True, "depends": [],
             "options": ["20", "40", "60", "80", "100", "120", "140", "160", "180", "200"]}],
         "note": "No automated pricing available (legacy order-form pricing widget). Contact us directly for a quote."},
        {"id": 171, "name": "X-ccessories — Litho", "engine": "contact", "optsrc": "none",
         "accuracy": None, "fields": [],
         "note": "Bulk accessory order builder (mix-and-match small quantities, West/East Malaysia shipping). Contact us directly for a quote."},
        {"id": 172, "name": "DTF Shirt — Digital", "engine": "pricelist",
         "note": "Adult, size M. Exact per category+model+fabric curves from the readymade order "
                 "engine (/Product/CheckPrice). Printing/VDP quoted separately."},
        {"id": 173, "name": "Silkscreen Shirt — Digital", "engine": "pricelist",
         "note": "Adult, size M. Exact per category+model+fabric curves from the readymade order "
                 "engine (/Product/CheckPrice). Printing/VDP quoted separately."},
        {"id": 174, "name": "Lanyard — Litho", "engine": "pricelist"},
        {"id": 175, "name": "Premium Desk Calendar — Litho", "engine": "pricelist"},
        {"id": 176, "name": "UV DTF Sticker — Digital", "engine": "pricelist"},
        {"id": 177, "name": "Food Tray — Litho", "engine": "pricelist"},
        {"id": 178, "name": "Kraft Paper Bag — Litho", "engine": "pricelist"},
        {"id": 179, "name": "Kotak Cenderahati — Litho", "engine": "pricelist"},
        {"id": 180, "name": "Corporate Shirt — Digital", "engine": "pricelist",
         "note": "Polysoft 150gsm, adult, size M, sublimation, no VDP. Exact per model+sleeve "
                 "curves from the readymade order engine (/Product/CheckPrice). VDP quoted separately."},
        {"id": 181, "name": "Jacket — Digital", "engine": "pricelist",
         "note": "Adult, size M, sublimation, no VDP. Exact per-model curves from the readymade "
                 "order engine (/Product/CheckPrice). VDP quoted separately."},
        {"id": 182, "name": "Muslimah Sublimation — Digital", "engine": "pricelist",
         "note": "Adult, size M, no VDP. Exact per category+fabric curves from the readymade "
                 "order engine (/Product/CheckPrice). VDP quoted separately."},
        {"id": 183, "name": "Sweatshirt & Hoodies — Digital", "engine": "pricelist",
         "note": "Adult, size M, no VDP. Exact per-model curves from the readymade order engine "
                 "(/Product/CheckPrice). VDP quoted separately."},
        {"id": 185, "name": "Cap — DTF", "engine": "pricelist",
         "note": "Acrylic Twill, adult, single front DTF print. Exact per-model curves from the "
                 "readymade order engine (/Product/CheckPrice)."},
        {"id": 184, "name": "Roll Form Sticker — Litho", "engine": "contact", "optsrc": "none",
         "accuracy": None, "fields": [
            {"key": "shape", "label": "Shape", "addon": True, "depends": [], "options": [
                "Rectangle/Square", "Round", "Custom Shape"]},
            {"key": "paper", "label": "Material", "addon": True, "depends": [], "options": [
                "Mirror Kote", "Transparent OPP", "White PP", "Printing Paper", "Synthetic Paper", "Hologram"]},
            {"key": "core", "label": "Paper Core", "addon": True, "depends": [], "options": ["25mm", "40mm", "76mm"]},
            {"key": "quantity_hint", "label": "Available quantities (pcs)", "addon": True, "depends": [],
             "options": ["1000", "5000", "10000", "20000", "50000", "100000"]}],
         "note": "No automated pricing available (legacy roll-form order widget). Contact us directly for a quote."},
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
        {"id": 115, "name": "Kad Terima Kasih — Digital", "engine": "pricelist",
         "note": "Exact per size+paper+colour+lamination+hole-punch curves from the v4 order "
                 "engine (/Product/CheckPrice)."},
        {"id": 114, "name": "Kad Kahwin — Digital", "engine": "pricelist",
         "note": "Standard Kad Kahwin. Exact per size+paper+colour curves from the v4 order "
                 "engine (/Product/CheckPrice). Lamination/envelope price-neutral; hot stamping "
                 "& custom die-cut quoted separately."},
        {"id": 113, "name": "PVC Card — Digital", "engine": "pricelist", "paramKey": "pvccard",
         "axisFields": ["colour", "hole_punch", "vdp"], "optsrc": "none",
         "accuracy": 0.0, "fields": [
            {"key": "orientation", "label": "Orientation (no online price change)", "addon": True, "depends": [], "options": ["Portrait", "Landscape"]},
            {"key": "colour", "label": "Print colour", "addon": True, "depends": [], "options": ["4C (Front)", "4C (Both)"]},
            {"key": "hole_punch", "label": "Hole punching", "addon": True, "depends": [],
             "options": ["Not Required", "Hole Punching (6mm)"]},
            {"key": "vdp", "label": "Variable Data Printing", "addon": True, "depends": [],
             "options": ["Not Required", "Variable Data Printing (Front)",
                         "Variable Data Printing (Back)", "Variable Data Printing (Both)"]}]},
        {"id": 112, "name": "Wire-O Notebook — Litho", "engine": "pricelist",
         "note": "Hard Cover. Exact per lamination+hot-stamping+content+paper curves from the "
                 "v4 ordering metrics (Price WM). Exclusive Leather Cover is a separate product."},
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
         "optsrc": "loose21", "accuracy": acc.get(21), "fields": LOOSE_LITHO_FIELDS},
        {"id": 50, "name": "Loose Sheet — Digital", "engine": "digital",
         "optsrc": "digital50", "accuracy": acc.get(50), "fields": LOOSE_DIGITAL_FIELDS},
        {"id": 19, "name": "Booklet — Litho (Offset)", "engine": "booklet",
         "optsrc": "booklet19", "accuracy": acc.get(19), "fields": BOOKLET_FIELDS},
        {"id": 37, "name": "Booklet — Digital", "engine": "booklet",
         "optsrc": "booklet37", "accuracy": acc.get(37), "fields": BOOKLET_FIELDS},
        # Aliases of Loose Sheet Litho (same Excard order form) — reuse litho engine+options.
        {"id": 101, "name": "Brochure (= Loose Sheet Litho)", "engine": "litho",
         "optsrc": "loose21", "accuracy": acc.get(21), "fields": LOOSE_LITHO_FIELDS},
        {"id": 102, "name": "Flyer (= Loose Sheet Litho)", "engine": "litho",
         "optsrc": "loose21", "accuracy": acc.get(21), "fields": LOOSE_LITHO_FIELDS},
        {"id": 103, "name": "Customprint (= Loose Sheet Litho)", "engine": "litho",
         "optsrc": "loose21", "accuracy": acc.get(21), "fields": LOOSE_LITHO_FIELDS},
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
            "envelope": _load("envelope_plx_params.json", {"curves": {}, "model_meta": {}, "env_gsm": 100}),
            "folder": _load("folder_pl_params.json", {"axis_cols": [], "curves": {}}),
            "lshape": _load("lshape_params.json", {"curves": {}, "size_mm": [310, 442]}),
            "bookmark": _load("bookmark_params.json", {"curves": {}, "fin_delta": {}, "size_mm": [50, 150]}),
            "voucher": _load("voucher_plx_params.json", {"curves": {}, "weight_factor": 1.2065}),
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
            "banner": _load("banner_plx_params.json", {"sizes": {}, "eyelet_delta_per_extra": 5.0, "material_gsm": 400, "ft_to_m": 0.3048}),
            "bunting": _load("bunting_params.json", {"curves": {}, "sizes": [], "papers": [], "paper_gsm": {}}),
            "rollup": _load("rollup_params.json", {"curves": {}, "lams": [], "stand_w_m": 0.85, "stand_h_m": 2.0, "material_gsm": 400}),
            "wobbler": _load("wobbler_params.json", {"curves": {}, "orients": [], "papers": [], "lams": [], "finishings": [], "paper_gsm": {}, "wobbler_w_m": 0.095, "wobbler_h_m": 0.21, "finish_deltas": {}}),
            "paperbag": _load("paperbag_plx_params.json", {"engine": "paperbag_checkprice", "models": [], "model_size": {}, "papers": [], "laminations": [], "curves": {}}),
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


# our product id -> captured Excard ordering slug (output/v4_options/<slug>_options.json)
_EXCARD_ID2SLUG = {
    107: "folder", 106: "envelope", 104: "notepad", 114: "kad-kahwin",
    115: "kad-terima-kasih", 113: "pvc-card", 124: "bunting", 123: "banner",
    129: "mug", 109: "bookmark", 110: "voucher-pad", 126: "wobbler",
    133: "hand-fan", 132: "button-badge", 127: "paper-bag",
    136: "hard-cover-menu", 128: "canvas-tote-bag",
    108: "l-shape-plastic-folder", 118: "wall-calendar", 119: "arch-file",
    120: "hard-stand-desk-calendar", 121: "soft-stand-desk-calendar",
    122: "wire-o-wall-calendar", 125: "roll-up-stand",
    112: "hard-cover-wire-o-notebook", 137: "standing-pouch",
    116: "car-sticker", 117: "car-sticker", 138: "money-packet",
    139: "non-woven-bag", 140: "tent-card", 134: "Hanger",
    105: "letterhead", 130: "papan-kopi", 135: "magnet", 131: "pillow",
    144: "cooler-bag", 145: "dtf-totebag-with-zip", 146: "heat-transfer-tote-bag",
    147: "laminated-non-woven-bag", 148: "rpet-non-woven-bag", 149: "toast-bag",
    150: "3-side-seal-packaging", 151: "kraft-standing-pouch",
    152: "standing-pouch-spout", 153: "vacuum-bag-packaging",
    154: "foamboard", 155: "foamboard-with-magnet", 156: "foldable-pop-display",
    157: "pop-display", 158: "wind-flag", 159: "economy-roll-up-stand",
    160: "bunting-gear-x-stand", 161: "bunting-round-base-stand", 162: "bunting-tripod-stand",
    163: "exclusive-leather-cover-wire-o-notebook", 164: "hard-cover-perfect-bind-notebook",
    165: "creative-cut-card", 166: "greeting-card",
    167: "premium-money-packet", 168: "hot-stamping-money-packet", 169: "envelope-money-packet",
    174: "lanyard", 175: "premium-desk-calendar", 176: "uv-dtf-sticker", 177: "food-tray",
    178: "kraft-paper-bag", 179: "kotak-cenderahati",
}
# Excard metric columns that are not user-selectable options
_EXCARD_SKIP = ("price", "weight", "print method", "process day", "fee",
                "delivery", "shipment", "compulsory")


def _is_skip_col(dim):
    import re
    low = dim.lower()
    if low.startswith("quantity") or re.match(r"^column\s*\d+$", low):
        return True
    return any(s in low for s in _EXCARD_SKIP)


def _norm(s):
    import re
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _img_for(opt, imgmap):
    """Match a calculator option label to an Excard diagram URL (exact, then by code prefix)."""
    if opt in imgmap:
        return imgmap[opt]
    code = opt.split(" — ")[0].split(" (")[0].strip()
    return imgmap.get(code)


_STEM = (("lamination", "lamin"), ("laminate", "lamin"), ("sides", "side"),
         ("colours", "color"), ("colour", "color"), ("required", "req"))


def _val_tokens(v):
    """Alnum tokens (len>=2) of a value, lightly stemmed so cosmetic label variants
    ('Laminate (Front)' vs 'Lamination') still match."""
    import re
    s = str(v).lower()
    for a, b in _STEM:
        s = s.replace(a, b)
    return {t for t in re.findall(r"[a-z0-9]+", s) if len(t) >= 2}


def _val_match(a, b):
    """Two option values are 'the same value' if their token sets overlap strongly."""
    ta, tb = _val_tokens(a), _val_tokens(b)
    if not ta or not tb:
        return False
    inter = len(ta & tb)
    if inter == 0:
        return False
    # subset (one fully contained) OR Jaccard >= 0.5
    return inter == min(len(ta), len(tb)) or inter / len(ta | tb) >= 0.5


def _attach_excard_parity(data):
    """KPI 1 — option parity (VALUE-COMPLETE). For every product captured from Excard's
    ordering page, ensure every Excard option dimension AND every one of its values (priced
    or not) is selectable in the calculator, with Excard's exact values + option images.
    Each Excard dimension is matched to the best existing field by value-overlap; any Excard
    values that field is missing are appended (Excard's exact strings). Dimensions with no
    matching field are added as a new addon field. Pricing keys are never removed."""
    by_id = {p["id"]: p for p in data["products"]}
    added = {}
    for pid, slug in _EXCARD_ID2SLUG.items():
        prod = by_id.get(pid)
        f = OUT / "v4_options" / f"{slug}_options.json"
        if not prod or not f.exists():
            continue
        ex = json.loads(f.read_text(encoding="utf-8"))
        imgfield = ex.get("imageField")
        imgmap = ex.get("imageOptions") or {}
        n_vals = n_dims = 0
        dim_field = {}          # Excard dim -> our field dict (for validity wiring)
        for dim in ex["optionCols"]:
            if _is_skip_col(dim):
                continue
            vals = ex["distinct"].get(dim, [])
            if len(vals) < 1:
                continue
            is_img = (dim == imgfield) and bool(imgmap)
            # best existing field: the one matching the most Excard values for this dim
            best, best_hits = None, 0
            for fld in prod["fields"]:
                opts = fld.get("options") or (list(fld["images"].keys()) if fld.get("images") else [])
                if not opts:
                    continue
                hits = sum(1 for v in vals if any(_val_match(v, o) for o in opts))
                if hits > best_hits:
                    best, best_hits = fld, hits
            if best is not None and best_hits >= max(1, 0.5 * len(vals)):
                # same dimension -> union in any Excard values this field is missing
                opts = best.setdefault("options", list(best.get("images", {}).keys()))
                miss = [v for v in vals if not any(_val_match(v, o) for o in opts)]
                opts.extend(miss)
                n_vals += len(miss)
                if is_img:
                    images = best.get("images", {})
                    for o in opts:
                        if o not in images:
                            u = _img_for(o, imgmap)
                            if u:
                                images[o] = u
                    if images:
                        best["images"] = images
                dim_field[dim] = best
            else:
                newf = {"key": "ex_" + _norm(dim), "label": dim,
                        "addon": True, "depends": [], "options": list(vals)}
                if is_img:
                    newf["images"] = {v: imgmap[v] for v in vals if v in imgmap}
                prod["fields"].append(newf)
                dim_field[dim] = newf
                n_dims += 1
                n_vals += len(vals)
        _build_validity(prod, ex, dim_field)
        if n_vals or n_dims:
            added[slug] = f"{n_dims} dims +{n_vals} vals"
    if added:
        print("  [excard parity] ", added)


def _build_validity(prod, ex, dim_field):
    """Bake Excard's valid-combination constraints so dependent dropdowns narrow like the
    real order page. Uses the captured deps map (primary dim value -> valid values per dim).
    Emits prod['validity'] = {primary: <fieldKey>, fields: [constrained fieldKeys],
    rules: {<our primary option>: {<fieldKey>: [valid our options]}}}. Values are stored as
    THIS calculator's option strings so the JS only needs exact set membership."""
    deps = ex.get("deps") or {}
    primary = ex.get("primary")
    if not deps or not primary or primary not in dim_field:
        return
    pfield = dim_field[primary]
    if pfield.get("type") == "number":
        return
    popts = pfield.get("options") or list((pfield.get("images") or {}).keys())
    # which non-primary dims are actually constrained (valid set varies / < full)?
    constrained = {}
    for dim, fld in dim_field.items():
        if dim == primary:
            continue
        full = ex["distinct"].get(dim, [])
        if len(full) <= 1:
            continue
        sets = [frozenset(deps[pv].get(dim, [])) for pv in deps]
        if len(set(sets)) > 1 or any(len(s) < len(full) for s in sets):
            constrained[dim] = fld
    if not constrained:
        return
    rules = {}
    for pv, sub in deps.items():
        our_pv = next((o for o in popts if _val_match(o, pv)), None)
        if our_pv is None:
            continue
        slot = rules.setdefault(our_pv, {})
        for dim, fld in constrained.items():
            valid_ex = sub.get(dim, [])
            fopts = fld.get("options") or []
            valid_our = [o for o in fopts if any(_val_match(o, ev) for ev in valid_ex)]
            prev = slot.get(fld["key"], [])
            slot[fld["key"]] = prev + [o for o in valid_our if o not in prev]
    prod["validity"] = {"primary": pfield["key"],
                        "fields": [f["key"] for f in constrained.values()],
                        "rules": rules}


# KPI2: products rebuilt to EXACT price lookups from captured WMPrice curves.
# id -> (captured slug, params tag). Fields/axes are generated from the captured data.
_PRICELIST_FROM_OPTIONS = {
    124: ("bunting", "bunting_pl"), 109: ("bookmark", "bookmark_pl"),
    132: ("button-badge", "buttonbadge_pl"), 133: ("hand-fan", "handfan_pl"),
    129: ("mug", "mug_pl"), 125: ("roll-up-stand", "rollup_pl"),
    121: ("soft-stand-desk-calendar", "softdesk_pl"),
    122: ("wire-o-wall-calendar", "wireowall_pl"),
    144: ("cooler-bag", "cooler_bag_pl"), 145: ("dtf-totebag-with-zip", "dtf_totebag_zip_pl"),
    146: ("heat-transfer-tote-bag", "heat_transfer_tote_pl"),
    147: ("laminated-non-woven-bag", "laminated_nonwoven_pl"),
    148: ("rpet-non-woven-bag", "rpet_nonwoven_pl"), 149: ("toast-bag", "toast_bag_pl"),
    150: ("3-side-seal-packaging", "sideseal_pl"), 151: ("kraft-standing-pouch", "kraft_pouch_pl"),
    152: ("standing-pouch-spout", "spout_pouch_pl"), 153: ("vacuum-bag-packaging", "vacuum_bag_pl"),
    154: ("foamboard", "foamboard_pl"), 155: ("foamboard-with-magnet", "foamboard_magnet_pl"),
    156: ("foldable-pop-display", "foldable_pop_pl"), 157: ("pop-display", "pop_display_pl"),
    158: ("wind-flag", "wind_flag_pl"), 159: ("economy-roll-up-stand", "econ_rollup_pl"),
    160: ("bunting-gear-x-stand", "bunting_gear_pl"), 161: ("bunting-round-base-stand", "bunting_round_pl"),
    162: ("bunting-tripod-stand", "bunting_tripod_pl"),
    163: ("exclusive-leather-cover-wire-o-notebook", "leather_wireo_pl"),
    164: ("hard-cover-perfect-bind-notebook", "hcperfectbind_pl"),
    165: ("creative-cut-card", "creative_cut_card_pl"), 166: ("greeting-card", "greeting_card_pl"),
    167: ("premium-money-packet", "premium_mp_pl"), 168: ("hot-stamping-money-packet", "hotstamp_mp_pl"),
    169: ("envelope-money-packet", "envelope_mp_pl"),
    174: ("lanyard", "lanyard_pl"), 175: ("premium-desk-calendar", "premium_deskcal_pl"),
    176: ("uv-dtf-sticker", "uvdtf_pl"), 177: ("food-tray", "food_tray_pl"),
    178: ("kraft-paper-bag", "kraft_paperbag_pl"), 179: ("kotak-cenderahati", "kotak_pl"),
    # REFERENCE→EXACT upgrades (compact products; giant/order-form ones stay on ref markup)
    126: ("wobbler", "wobbler_plx"), 136: ("hard-cover-menu", "hardmenu_plx"),
    137: ("standing-pouch", "pouch_plx"), 134: ("Hanger", "hanger_plx"),
    108: ("l-shape-plastic-folder", "lshape_plx"), 119: ("arch-file", "archfile_plx"),
    128: ("canvas-tote-bag", "canvastote_plx"), 120: ("hard-stand-desk-calendar", "harddesk_plx"),
    118: ("wall-calendar", "wallcal_plx"),
    185: ("cap", "cap_plx"),  # readymade garment — exact per-model curves via /Product/CheckPrice
    180: ("corporate-shirt", "corpshirt_plx"), 181: ("jacket", "jacket_plx"),
    182: ("muslimah", "muslimah_plx"), 183: ("sweatshirt-hoodies", "sweatshirt_plx"),
    143: ("shirt", "subshirt_plx"),
    172: ("dtf-shirt", "dtfshirt_plx"), 173: ("silkscreen-shirt", "silkshirt_plx"),
    115: ("kad-terima-kasih", "kadterima_plx"), 114: ("kad-kahwin", "kadkahwin_plx"),
    112: ("hard-cover-wire-o-notebook", "wireonb_plx"), 1: ("business-card", "bizcard_plx"),
    24: ("bill-book", "billbook_plx"),  # NCR bill book — exact via workers<=2 CheckPrice sample
    135: ("magnet", "magnet_plx"),  # Digital magnet — exact CheckPrice (Custom Die-Cut=Rect; Round size-neutral)
    # REFERENCE→EXACT batch 2 (price-list DataTable captures)
    104: ("notepad", "notepad_plx"), 123: ("banner", "banner_plx"),
    127: ("paper-bag", "paperbag_plx"),
    116: ("car-sticker", "staticcling_plx"), 117: ("car-sticker", "carsticker_plx"),
    # Loose Sheet Litho + aliases — exact from the 159k-row crawl CSV
    21: ("loose-sheet-litho", "loosesheet_plx"), 101: ("loose-sheet-litho", "loosesheet_plx"),
    102: ("loose-sheet-litho", "loosesheet_plx"), 103: ("loose-sheet-litho", "loosesheet_plx"),
}


# Price-NEUTRAL options present on Excard's order form that must appear in our UI for option
# parity (verified via CheckPrice to NOT change price). Keyed by product id; appended to the
# generated pricelist fields but excluded from axisFields (so they never affect the price).
_NEUTRAL_FIELDS = {
    24: [  # Bill-Book: numbering & perforation are free (verified 0.0% delta)
        {"key": "papermaterials", "label": "Paper Materials",
         "options": ["NCR (Carbonize Paper)", "Normal Paper"],
         "note": "NCR (carbonless) is priced exactly. Normal (plain) paper is quoted on request."},
        {"key": "paper_tint", "label": "Paper (per layer)",
         "options": ["NCR White 50gsm", "NCR Green 50gsm", "NCR Blue 50gsm",
                     "NCR Yellow 50gsm", "NCR Pink 50gsm"],
         "note": "Each layer's tint is selectable free of charge (price-neutral); standard sequence is White, Green, Blue, Yellow, Pink."},
        {"key": "numbering", "label": "Numbering", "options": ["No Numbering", "Yes — Add Numbering"],
         "note": "Numbering is free. 4–7 digit sequential numbering in red; enter the start number on the order."},
        {"key": "last_layer_perforation", "label": "Last Layer Perforation",
         "options": ["No", "Yes"], "note": "Compulsory perforation for one layer in Book type; price-neutral."},
        {"key": "back_print_layer", "label": "Back printing",
         "options": ["First Layer Only", "All Layers"],
         "note": "Which layers carry the back print — price-neutral (verified via CheckPrice)."},
    ],
}

_NEUTRAL_FIELDS[1] = [  # Business Card: verified price-neutral / quoted-separately controls
    {"key": "category", "label": "Category", "neutral": False,
     "options": ["Standard", "Thin Fold", "Fat Fold", "Custom Die Cut", "Plastic Card"],
     "note": "Standard is priced exactly. Thin/Fat Fold, Custom Die Cut and Plastic Card are "
             "separate products — quoted on request."},
    {"key": "orientation", "label": "Orientation", "options": ["Landscape", "Portrait"],
     "note": "Orientation is price-neutral for business cards."},
    {"key": "hot_stamping", "label": "Hot Stamping", "options":
     ["No Hot Stamping", "1C (Front)", "1C (Back)", "2C (Front)", "2C (Back)"],
     "note": "Hot-stamping block is quoted separately; the printing price shown excludes it."},
    # Hot-stamping sub-spec (price-neutral; shown only when hot stamping is selected):
    {"key": "hot_stamping_colour", "label": "Hot Stamping — Foil Colour",
     "options": ["Gold", "Silver"], "showWhen": {"field": "hot_stamping", "notValues": ["No Hot Stamping"]},
     "note": "Foil colour (Gold min. order 3k, Silver min. order 1k)."},
    {"key": "hot_stamping_w", "label": "Hot Stamping — Area width (mm)", "type": "number",
     "min": 5, "max": 300, "placeholder": "e.g. 40", "showWhen": {"field": "hot_stamping", "notValues": ["No Hot Stamping"]}},
    {"key": "hot_stamping_h", "label": "Hot Stamping — Area height (mm)", "type": "number",
     "min": 5, "max": 300, "placeholder": "e.g. 30", "showWhen": {"field": "hot_stamping", "notValues": ["No Hot Stamping"]},
     "note": "Stamping area; the block/foil is quoted separately."},
    # Embossing IS priced (qty×package-scaled, ~+RM52.50/run min) — driven via addonDeltas:
    {"key": "embossing", "label": "Embossing", "neutral": False,
     "options": ["Not Required", "Embossing Front", "Embossing Back"],
     "note": "Embossing adds a per-run cost (Front and Back priced the same)."},
    {"key": "embossing_w", "label": "Embossing — Area width (mm)", "type": "number",
     "min": 5, "max": 300, "placeholder": "e.g. 40", "showWhen": {"field": "embossing", "notValues": ["Not Required"]}},
    {"key": "embossing_h", "label": "Embossing — Area height (mm)", "type": "number",
     "min": 5, "max": 300, "placeholder": "e.g. 30", "showWhen": {"field": "embossing", "notValues": ["Not Required"]},
     "note": "Embossing area."},
    {"key": "round_corner", "label": "Round Corner", "options": ["No", "Required"],
     "note": "Round corner is price-neutral."},
    {"key": "silkscreen_spot_uv", "label": "Silkscreen Spot UV", "options": ["No Required", "Required"],
     "note": "Spot UV block is quoted separately."},
    # Hole punching DOES add cost (qty×package-scaled) — driven via addonDeltas, not an axis:
    {"key": "holepunching", "label": "Hole Punching", "neutral": False,
     "options": ["No Hole Punching", "3mm", "5mm"],
     "note": "Adds a per-piece punching cost (3mm and 5mm priced the same)."},
]

_LOOSE_PKG = ["Normal", "2in1", "3in1", "4in1", "5in1", "6in1", "7in1", "8in1", "9in1", "10in1"]
_LOOSE_ENV = ["- Not Required -", "108mm x 159mm - Pink A6", "110mm x 220mm - White DL",
              "133mm x 102mm - Cream A7", "162mm x 114mm - White A6", "162mm x 229mm - Pink A5",
              "162mm x 229mm - White A5", "215mm x 114mm - Pink DL"]
# Loose Sheet Litho (21) + brochure/flyer/customprint aliases came from a www price-list crawl
# (size×paper×lamination×colour) with no CheckPrice API. Package ganging and Envelope are on
# the Excard form but weren't in the crawl and can't be API-verified → expose + price on request.
for _lsid in (21, 101, 102, 103):
    _NEUTRAL_FIELDS[_lsid] = [
        {"key": "package", "label": "Package (ganging)", "neutral": False, "options": list(_LOOSE_PKG),
         "note": "Normal is priced exactly; ganged (N-in-1) runs are quoted on request."},
        {"key": "envelope", "label": "Envelope", "neutral": False, "options": list(_LOOSE_ENV),
         "note": "Envelopes are quoted separately/on request."},
    ]

_NEUTRAL_FIELDS[123] = [  # Banner: expose Standard/Custom size type (custom → on request)
    {"key": "size_type", "label": "Size Type", "neutral": False,
     "options": ["Standard Size", "Custom Size"],
     "note": "Standard sizes are priced exactly; custom-size banners are quoted on request."},
]

_NEUTRAL_FIELDS[60] = [  # Label Sticker Digital: sample proof is a workflow/quoted-separately option
    {"key": "sample_proof", "label": "Sample Proof (2 pcs)", "options": ["No", "Yes"],
     "note": "Optional pre-production sample proof; quoted separately."},
]

_NEUTRAL_FIELDS[127] = [  # Paper Bag: rope colour is price-neutral (verified)
    {"key": "rope_colour", "label": "Rope Colour",
     "options": ["Black", "Blue", "Gold", "Green", "Red", "Silver", "White"],
     "note": "Rope/handle colour is selectable free of charge (price-neutral)."},
]

_NEUTRAL_FIELDS[129] = [  # Mug: single-option controls on the supplier's form (price-neutral)
    {"key": "mug_colour", "label": "Mug Colour", "options": ["White"],
     "note": "Standard white ceramic mug."},
    {"key": "print_colour", "label": "Print Colour", "options": ["4C (Full Colour)"],
     "note": "Full-colour sublimation print."},
    {"key": "packing", "label": "Packing (included)", "options": ["Individual Blank Box Packing"],
     "note": "Every mug is individually packed in a blank box."},
]

_MONEY_DESIGN_SRC = {"key": "design_source", "label": "Design",
    "options": ["Custom Made Money Packet", "Ready Designed with Editor"],
    "note": "Upload your own design, or start from a ready-made design in the editor — the print price is the same."}
for _mp in (167, 168, 169):  # Premium / Hot Stamping / Envelope money packets: design-source toggle
    _NEUTRAL_FIELDS[_mp] = [dict(_MONEY_DESIGN_SRC)]

_NEUTRAL_FIELDS[178] = [  # Kraft Paper Bag: lamination + rope colour on the order form but not in
                         # the WM price metrics (which vary by model/size/material/print colour).
    {"key": "lamination", "label": "Lamination", "neutral": False,
     "options": ["Gloss Lamination", "Matte Lamination", "Matte Lamination + Spot UV"],
     "note": "Gloss/Matte lamination is included; adding Spot UV is quoted separately."},
    {"key": "rope_colour", "label": "Rope Colour",
     "options": ["Black", "Blue", "Gold", "Green", "Red", "Silver"],
     "note": "Rope/handle colour is selectable free of charge (price-neutral)."},
]

_NEUTRAL_FIELDS[114] = [  # Kad Kahwin: category drives contact; hot-stamping/envelope quoted separately
    {"key": "category", "label": "Category", "neutral": False,
     "options": ["Standard Kad Kahwin", "Custom Die Cut Kad Kahwin"],
     "note": "Standard is priced exactly; Custom Die Cut is a separate product — quoted on request."},
    {"key": "hot_stamping", "label": "Hot Stamping", "options":
     ["Not Required", "1C (Front)", "1C (Back)", "2C (Front)", "2C (Back)"],
     "note": "Hot-stamping block is quoted separately."},
    {"key": "hot_stamping_colour", "label": "Hot Stamping — Foil Colour",
     "options": ["Black", "Blue", "Gold", "Green", "Red", "Silver"],
     "showWhen": {"field": "hot_stamping", "notValues": ["Not Required"]},
     "note": "Foil colour."},
    {"key": "hot_stamping_w", "label": "Hot Stamping — Panel width (mm)", "type": "number",
     "min": 5, "max": 300, "placeholder": "e.g. 90", "showWhen": {"field": "hot_stamping", "notValues": ["Not Required"]}},
    {"key": "hot_stamping_h", "label": "Hot Stamping — Panel height (mm)", "type": "number",
     "min": 5, "max": 300, "placeholder": "e.g. 30", "showWhen": {"field": "hot_stamping", "notValues": ["Not Required"]},
     "note": "Stamping area; the block/foil is quoted separately."},
    {"key": "envelope", "label": "Envelope", "options":
     ["Not Required", "White (DL)", "White (A5)", "White (A6)", "Pink (DL)", "Pink (A5)", "Pink (A6)"],
     "note": "Envelopes are quoted separately from the card printing price."},
]

# Configs exposed in the UI for option parity but outside the exact sampled axes
# (combinatorial sub-options / different sub-products) → priced "on request".
_CONTACT_WHEN = {
    178: [{"field": "lamination", "values": ["Matte Lamination + Spot UV"],
           "note": "Spot UV on the kraft bag is quoted separately — please contact us for a quote."}],
    24: [{"field": "papermaterials", "values": ["Normal Paper"],
          "note": "Normal (non-carbonless) paper — each layer's paper is chosen independently, "
                  "so this is quoted on request. Please contact us for a quote."}],
    1: [{"field": "category", "values": ["Thin Fold", "Fat Fold", "Custom Die Cut", "Plastic Card"],
         "note": "Folded / die-cut / plastic business cards are separate products — quoted on request."}],
    114: [{"field": "category", "values": ["Custom Die Cut Kad Kahwin"],
           "note": "Custom Die Cut Kad Kahwin is a separate product — quoted on request."}],
    123: [{"field": "size_type", "values": ["Custom Size"],
           "note": "Custom-size banners are quoted on request."}],
    **{_lsid: [{"field": "package", "values": _LOOSE_PKG[1:],
               "note": "Ganged (N-in-1) loose-sheet runs are quoted on request."},
              {"field": "envelope", "values": _LOOSE_ENV[1:],
               "note": "Loose-sheet with envelopes is quoted on request."}]
       for _lsid in (21, 101, 102, 103)},
}

# Exact additive finishing deltas (sampled independently of the price axes, scaled by qty
# and — where noted — by package ganging). Attached to the pricelist engine.
_ADDON_DELTAS = {
    1: [{"key": "holepunch", "field": "holepunching", "whenValues": ["3mm", "5mm"],
         "scaleByPackage": True, "curveFile": "bizcard_holepunch_delta.json"},
        {"key": "embossing", "field": "embossing", "whenValues": ["Embossing Front", "Embossing Back"],
         "scaleByPackage": True, "curveFile": "bizcard_embossing_delta.json"}],
}


# Extra option VALUES that exist on Excard's control but aren't in our sampled axis data
# (e.g. 1C loose-sheet colours the CSV crawl skipped, gang sizes, custom size, Multiple
# Dieline). Injected into the matching axis field so every Excard combo is selectable; each
# gets a contactWhen rule (we can't price it exactly) → "price on request".
_EXTRA_AXIS_OPTIONS = {
    1:   {"size": ["Other (Custom Size)"]},
    24:  {"size": ["Other (Custom Size)"]},
    135: {"shape": ["Multiple Dieline"]},
    116: {"size": ["Others"]},
    117: {"size": ["Other"]},
    **{lsid: {"colour": ["1C (Front)", "1C (Both)"],
              "size": ["4xA4 (297mm x 840mm)", "4xA5 (210mm x 594mm)", "Other (Custom Size)"]}
       for lsid in (21, 101, 102, 103)},
}


def _apply_extra_axis_options(prod, pid):
    """Append Excard option values we don't have price data for to their axis field, and add
    contactWhen rules so selecting them shows 'price on request'."""
    extra = _EXTRA_AXIS_OPTIONS.get(pid)
    if not extra:
        return
    cw = prod.get("contactWhen", []) or []
    for fkey, vals in extra.items():
        for fld in prod["fields"]:
            if fld["key"] == fkey:
                for v in vals:
                    if v not in fld["options"]:
                        fld["options"].append(v)
                cw.append({"field": fkey, "values": list(vals),
                           "note": "This option is quoted on request — please contact us for a price."})
                break
    prod["contactWhen"] = cw


def _wire_pricelist_products(data):
    """KPI2: convert each configured product to an exact price-list lookup built from its
    captured WMPrice curves. Generates the option fields from the captured Excard values
    (so options stay 100% and pricing is exact), sets engine=pricelist + axisFields, and
    bakes the params. Cascading validity is re-derived afterwards by _attach_excard_parity."""
    from . import build_pl_from_options as B
    by_id = {p["id"]: p for p in data["products"]}
    done = {}
    for pid, (slug, tag) in _PRICELIST_FROM_OPTIONS.items():
        prod = by_id.get(pid)
        f = OUT / "v4_options" / f"{slug}_options.json"
        if not prod or not f.exists():
            continue
        ex = json.loads(f.read_text(encoding="utf-8"))
        if not ex.get("priceMeta"):
            continue
        params, price_axes, ncol = B.build(slug, tag)
        imgfield = ex.get("imageField"); imgmap = ex.get("imageOptions") or {}
        fields = []
        for dim in price_axes:
            vals = ex["distinct"].get(dim, [])
            fld = {"key": _norm(dim), "label": dim, "addon": True, "depends": [], "options": list(vals)}
            if dim == imgfield and imgmap:
                im = {v: imgmap[v] for v in vals if v in imgmap}
                if im:
                    fld["images"] = im
            fields.append(fld)
        # Append extra UI fields so the calculator mirrors Excard's full order form. Fields
        # marked neutral (default) don't affect price; non-neutral extra fields drive addon
        # deltas (below) but are not price axes. None are in axisFields.
        for nf in _NEUTRAL_FIELDS.get(pid, []):
            fld = {"key": nf["key"], "label": nf["label"], "addon": True,
                   "depends": nf.get("depends", []), "neutral": nf.get("neutral", True),
                   "note": nf.get("note", "")}
            if nf.get("type") == "number":
                fld["type"] = "number"
                for k in ("min", "max", "placeholder", "default"):
                    if k in nf:
                        fld[k] = nf[k]
            else:
                fld["options"] = list(nf["options"])
            if "showWhen" in nf:
                fld["showWhen"] = nf["showWhen"]
            fields.append(fld)
        prod["engine"] = "pricelist"
        prod["paramKey"] = tag
        prod["axisFields"] = [_norm(dim) for dim in price_axes]
        prod["fields"] = fields
        if pid in _CONTACT_WHEN:
            prod["contactWhen"] = _CONTACT_WHEN[pid]
        _apply_extra_axis_options(prod, pid)
        if pid in _ADDON_DELTAS:
            ads = []
            for ad in _ADDON_DELTAS[pid]:
                curve = json.loads((OUT / ad["curveFile"]).read_text(encoding="utf-8"))
                ads.append({"field": _norm(ad["field"]), "whenValues": ad["whenValues"],
                            "scaleByPackage": ad.get("scaleByPackage", False), "curve": curve})
            prod["addonDeltas"] = ads
        prod["accuracy"] = 0.0
        data["params"][tag] = params
        done[slug] = f"{len(params['curves'])} curves, {len(price_axes)} axes"
    if done:
        print("  [pricelist KPI2]", done)


def _embed_images(data):
    """Replace option-diagram image URLs with self-contained base64 data URIs
    (output/img_data_uris.json), so the file embeds its images and carries no
    external image hosts. Image entries with no cached data URI are dropped."""
    cache = _load("img_data_uris.json", {})
    for p in data["products"]:
        for f in p.get("fields", []):
            if "images" not in f:
                continue
            newimgs = {k: cache[u] for k, u in f["images"].items() if u in cache}
            if newimgs:
                f["images"] = newimgs
            else:
                del f["images"]


# Reference markup applied to NON-exact products. Per current directive: MATCH Excard's
# prices (no selling margin) so every product's displayed price stays within ~5% of Excard;
# a selling markup will be layered on separately once all products are priced. Set to 1.0
# (no markup) — formula/reference products then display at their calibrated Excard estimate.
_REF_MARKUP = 1.0


def _apply_ref_markup(data):
    for p in data["products"]:
        if p.get("accuracy") == 0 or p.get("engine") == "contact":
            continue  # exact (matches reference) or contact-only (no auto price)
        p["markup"] = _REF_MARKUP


def _emit_api_artifacts(data, tmpl):
    """Emit the two artifacts the public API serves, from the SAME data + engine the
    calculator uses (single source of truth):
      output/calculator_data.json  — full catalog (products, fields, validity, images).
      output/calculator_engine.cjs — Node-requireable pricing engine (the calculator's exact
                                      localQuote, with image-stripped data for speed).
    """
    import copy
    (OUT / "calculator_data.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    edata = copy.deepcopy(data)
    for p in edata["products"]:
        p.pop("art", None)                   # pricing engine never needs the illustration
        for f in p.get("fields", []):
            f.pop("images", None)            # pricing never needs images
    marker = "const DATA = /*__DATA__*/;"
    s = tmpl.index(marker) + len(marker)
    e = tmpl.index("// ---------- UI ----------")
    engine_code = tmpl[s:e]
    bundle = ("const DATA=" + json.dumps(edata, ensure_ascii=False) + ";\n"
              + engine_code
              + "\nmodule.exports={DATA,localQuote,localOptions,tiers};\n")
    (OUT / "calculator_engine.cjs").write_text(bundle, encoding="utf-8")


# Products that open a dedicated configurator (separate standalone tool) instead of the
# simple field form — e.g. Kotak Cenderahati = the full 67-style folding-carton box builder
# (3D preview, custom dimensions, materials/coatings/add-ons) in packaging_standalone.html.
_CONFIGURATORS = {
    179: {"url": "packaging_standalone.html",
          "note": "Choose from 67 folding-carton box styles in the box configurator."},
}


def _attach_configurators(data):
    for p in data["products"]:
        c = _CONFIGURATORS.get(p["id"])
        if c:
            p["configuratorUrl"] = c["url"]
            p["configuratorNote"] = c["note"]


def _attach_art(data):
    """Bake each product's original animated SVG illustration into the catalog so the
    calculator's picker + config header can show it (same art as the product pages)."""
    from app.product_art import svg_for
    for p in data["products"]:
        p["art"] = svg_for(p["name"])


def main():
    data = build_data()
    _drop_unsampled(data)
    _wire_pricelist_products(data)
    _attach_configurators(data)
    _attach_images(data)
    _attach_excard_parity(data)
    # Mirror the supplier's single-option controls (included processes, fixed specs) as
    # display-only fields — trivially price-neutral, required for full option parity.
    from app.auto_parity import attach as _attach_auto_parity
    _t, _a = _attach_auto_parity(data)
    print(f"option parity: +{_a} single-option controls across {_t} products")
    _apply_ref_markup(data)
    _embed_images(data)
    from app.field_order import reorder as _reorder_fields
    _fn, _fc = _reorder_fields(data)
    print(f"field order: {_fc}/{_fn} products resequenced to the supplier's option order")
    _attach_art(data)
    from app.product_quantity import attach as _attach_quantity
    _n, _hit = _attach_quantity(data)
    print(f"quantity: {_hit}/{_n} products with order-form MOQ")
    from app.product_art import ART_KEYFRAMES
    tmpl = (UI / "_standalone_template.html").read_text(encoding="utf-8")
    tmpl = tmpl.replace("/*__ARTCSS__*/", ART_KEYFRAMES)
    html = tmpl.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False))
    (UI / "calculator_standalone.html").write_text(html, encoding="utf-8")
    _emit_api_artifacts(data, tmpl)
    sizes = {k: len(json.dumps(v)) for k, v in data["options"].items()}
    print("wrote ui/calculator_standalone.html")
    print("products:", [p["name"] for p in data["products"]])
    print("option sizes (chars):", sizes)


if __name__ == "__main__":
    main()
