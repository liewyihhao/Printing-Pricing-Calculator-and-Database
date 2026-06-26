"""FastAPI backend serving the crawled Excard pricing for the Printoka calculator.

Endpoints (all derive from real data that actually has prices, so the UI never
offers a combination we can't quote):
  GET  /api/options                  -> cascading option lists
  GET  /api/quote                    -> price ladder for a configured combo
  GET  /                             -> the calculator UI (static)

Run:  .venv/Scripts/python.exe -m uvicorn app.api:app --port 8000
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, distinct, and_

from .db import session_scope
from .models import (Combination, Pricing, Delivery, Product, WorkItem,
                     OrderWork, OrderQuote)

app = FastAPI(title="Printoka Pricing API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

UI_DIR = Path(__file__).resolve().parent.parent / "ui"
PRODUCT_ID = 21  # Loose Sheet (the product we have data for)

# Membership tiers are fixed discounts off the Cash (base) price, so we only
# crawl Cash (= before_discount) and derive the rest.
TIER_DISCOUNTS = {"Cash": 0.00, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}


def derive_tiers(cash_price: float | None) -> dict:
    if cash_price is None:
        return {}
    return {t: round(cash_price * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def package_multiplier(package: str | None) -> int:
    """'Nin1' ganging multiplies the OUTPUT: the selected quantity is per-design,
    and total pieces = quantity * N. 'Normal' (or anything unparseable) is 1.
    e.g. '2in1' -> 2, '10in1' -> 10."""
    if not package:
        return 1
    m = re.match(r"\s*(\d+)\s*in\s*1\s*$", package, re.I)
    return int(m.group(1)) if m else 1


def _priced(q):
    """Restrict a Combination query to rows that actually have pricing."""
    return q.join(Pricing, Pricing.combination_id == Combination.id)


@app.get("/api/options")
def options(size: str | None = None, paper: str | None = None,
            lamination: str | None = None):
    """Cascading options: each level filtered by the prior selections, and only
    values that have real pricing are returned."""
    with session_scope() as s:
        def col_values(col, *conds):
            q = _priced(select(distinct(col)).where(
                Combination.product_id == PRODUCT_ID, *conds))
            return [r[0] for r in s.execute(q).all() if r[0] is not None]

        sizes = sorted(col_values(Combination.size_label))
        papers = lams = []
        conds = []
        if size:
            conds.append(Combination.size_label == size)
            papers = sorted(col_values(Combination.paper_label, *conds))
        if size and paper:
            conds.append(Combination.paper_label == paper)
            lams_raw = col_values(Combination.lamination_label, *conds)
            # Normalize None -> "None" label for the UI.
            lams = sorted([l for l in lams_raw if l]) + \
                   (["None"] if any(l is None for l in s.execute(_priced(select(
                       Combination.lamination_label).where(
                       Combination.product_id == PRODUCT_ID,
                       Combination.size_label == size,
                       Combination.paper_label == paper))).all()
                       if l[0] is None) else [])

        deliveries = {d.code: d.name for d in s.scalars(select(Delivery)).all()}
        return {"sizes": sizes, "papers": papers, "laminations": lams,
                "deliveries": deliveries}


@app.get("/api/quote")
def quote(size: str = Query(...), paper: str = Query(...),
          delivery: int = Query(...), lamination: str | None = None):
    """Return the full price ladder (quantities x tiers x color modes) for one
    configured combination."""
    lam_cond = (Combination.lamination_label.is_(None)
                if (lamination in (None, "", "None"))
                else Combination.lamination_label == lamination)
    with session_scope() as s:
        combo = s.scalars(_priced(select(Combination).where(
            Combination.product_id == PRODUCT_ID,
            Combination.size_label == size,
            Combination.paper_label == paper,
            Combination.delivery_code == delivery,
            lam_cond)).limit(1)).first()
        if not combo:
            return JSONResponse({"error": "No pricing for this combination."},
                                status_code=404)
        rows = s.execute(select(
            Pricing.color_mode, Pricing.quantity, Pricing.tier, Pricing.price,
            Pricing.suffix).where(Pricing.combination_id == combo.id)
            .order_by(Pricing.quantity)).all()

        # Shape: { "4C": { qty: {tier: price, ...} }, "4C+4C": {...} }
        ladder: dict = {}
        for mode, qty, tier, price, suffix in rows:
            ladder.setdefault(mode, {}).setdefault(int(qty), {})[tier] = float(price)
        return {
            "combination": {
                "size": combo.size_label, "paper": combo.paper_label,
                "lamination": combo.lamination_label or "None",
                "delivery_code": combo.delivery_code,
            },
            "color_modes": sorted(ladder.keys()),
            "quantities": sorted({q for m in ladder.values() for q in m}),
            "ladder": ladder,
        }


@app.get("/api/summary")
def summary():
    with session_scope() as s:
        return {
            "product": "Loose Sheet",
            "combinations_priced": s.scalar(select(func.count(distinct(
                Combination.id))).select_from(Combination).join(
                Pricing, Pricing.combination_id == Combination.id)),
            "price_points": s.scalar(select(func.count()).select_from(Pricing)),
        }


@app.get("/api/products")
def products():
    with session_scope() as s:
        out = []
        for p in s.scalars(select(Product).order_by(Product.excard_id)).all():
            combos = s.scalar(select(func.count(distinct(Combination.id)))
                              .select_from(Combination).join(
                                  Pricing, Pricing.combination_id == Combination.id)
                              .where(Combination.product_id == p.excard_id))
            prices = s.scalar(select(func.count()).select_from(Pricing).join(
                Combination, Combination.id == Pricing.combination_id)
                .where(Combination.product_id == p.excard_id))
            pending = s.scalar(select(func.count()).select_from(WorkItem).join(
                Combination, Combination.id == WorkItem.combination_id)
                .where(Combination.product_id == p.excard_id,
                       WorkItem.status == "pending"))
            out.append({"id": p.excard_id, "name": p.name, "category": p.category,
                        "status": p.status, "combos_priced": combos or 0,
                        "price_points": prices or 0, "pending": pending or 0})
        return out


@app.get("/api/crawl-status")
def crawl_status():
    with session_scope() as s:
        wq = dict(s.execute(select(WorkItem.status, func.count())
                            .group_by(WorkItem.status)).all())
        total = sum(wq.values())
        done = wq.get("done", 0)
        return {
            "by_status": wq, "total": total, "done": done,
            "pending": wq.get("pending", 0), "in_progress": wq.get("in_progress", 0),
            "failed": wq.get("failed", 0),
            "pct": round(done / total * 100, 1) if total else 0,
            "combinations": s.scalar(select(func.count()).select_from(Combination)),
            "price_points": s.scalar(select(func.count()).select_from(Pricing)),
        }


@app.get("/api/pricing")
def pricing(limit: int = Query(50, le=500), offset: int = 0,
            size: str | None = None, paper: str | None = None,
            tier: str | None = None, color_mode: str | None = None):
    """Paginated real pricing rows for the Pricing-tables view."""
    conds = [Combination.product_id == PRODUCT_ID]
    if size:
        conds.append(Combination.size_label == size)
    if paper:
        conds.append(Combination.paper_label == paper)
    if tier:
        conds.append(Pricing.tier == tier)
    if color_mode:
        conds.append(Pricing.color_mode == color_mode)
    base = (select(Combination.size_label, Combination.paper_label,
                   Combination.lamination_label, Combination.delivery_code,
                   Pricing.color_mode, Pricing.quantity, Pricing.tier,
                   Pricing.price, Pricing.suffix)
            .join(Pricing, Pricing.combination_id == Combination.id)
            .where(and_(*conds)))
    with session_scope() as s:
        total = s.scalar(select(func.count()).select_from(base.subquery()))
        rows = s.execute(base.order_by(
            Combination.size_label, Combination.paper_label, Pricing.quantity)
            .limit(limit).offset(offset)).all()
        deliveries = {d.code: d.name for d in s.scalars(select(Delivery)).all()}
        return {
            "total": total, "limit": limit, "offset": offset,
            "rows": [{
                "size": r[0], "paper": r[1], "lamination": r[2] or "None",
                "delivery": deliveries.get(r[3], r[3]), "color_mode": r[4],
                "quantity": r[5], "tier": r[6], "price": float(r[7]),
                "suffix": r[8],
            } for r in rows],
        }


# ---------- order-page (accurate) pricing ----------
@app.get("/api/order/options")
def order_options(size: str | None = None, paper: str | None = None,
                  colour: str | None = None, package: str | None = None):
    """Cascading options from order_work rows that actually have quotes."""
    with session_scope() as s:
        def vals(col, *conds):
            # Options now come from the combos themselves (status='done' = a valid
            # combination Excard offers). Prices are no longer stored — pricing is
            # by the Printoka formula.
            q = (select(distinct(col)).select_from(OrderWork)
                 .where(OrderWork.status == "done", *conds))
            return sorted({r[0] for r in s.execute(q).all() if r[0] is not None})
        out = {"sizes": vals(OrderWork.size_label), "papers": [], "colours": [],
               "packages": [], "deliveries": {d.code: d.name
                                              for d in s.scalars(select(Delivery)).all()}}
        conds = []
        if size:
            conds.append(OrderWork.size_label == size)
            out["papers"] = vals(OrderWork.paper_label, *conds)
        if size and paper:
            conds.append(OrderWork.paper_label == paper)
            out["colours"] = vals(OrderWork.colour_side, *conds)
        if size and paper and colour:
            conds.append(OrderWork.colour_side == colour)
            out["packages"] = vals(OrderWork.package, *conds)
        return out


@app.get("/api/order/quote")
def order_quote(size: str = Query(...), paper: str = Query(...),
                colour: str = Query(...), package: str = Query("Normal"),
                delivery: int = Query(98)):
    with session_scope() as s:
        w = s.scalars(select(OrderWork).where(
            OrderWork.size_label == size, OrderWork.paper_label == paper,
            OrderWork.colour_side == colour, OrderWork.package == package,
            OrderWork.delivery_code == delivery)).first()
        if not w:
            return JSONResponse({"error": "Not crawled yet."}, status_code=404)
        rows = s.scalars(select(OrderQuote).where(
            OrderQuote.order_work_id == w.id).order_by(OrderQuote.quantity)).all()
        mult = package_multiplier(package)

        def row(r):
            cash = float(r.before_discount) if r.before_discount else None
            pieces = int(r.quantity) * mult  # total output (Nin1 doubles, etc.)
            tiers = derive_tiers(cash)
            # Per-piece cost on the EFFECTIVE pieces, for fair cross-package compare.
            per_piece = {t: round(v / pieces, 4) for t, v in tiers.items()} if pieces else {}
            return {
                "cash": cash,
                "tiers": tiers,
                "pieces": pieces,
                "per_piece": per_piece,
                "delivery_fee": float(r.delivery_fee) if r.delivery_fee else None,
                "weight_kg": float(r.weight_kg) if r.weight_kg else None,
                "nett": float(r.nett) if r.nett else None,
            }
        return {
            "config": {"size": size, "paper": paper, "colour": colour,
                       "package": package, "delivery_code": delivery,
                       "multiplier": mult},
            "quantities": [r.quantity for r in rows],
            "ladder": {r.quantity: row(r) for r in rows},
        }


@app.get("/api/order/status")
def order_status_api():
    with session_scope() as s:
        wq = dict(s.execute(select(OrderWork.status, func.count())
                            .group_by(OrderWork.status)).all())
        return {"by_status": wq, "total": sum(wq.values()),
                "done": wq.get("done", 0),
                "quotes": s.scalar(select(func.count()).select_from(OrderQuote))}


# ---------- Printoka Formulation (our own engine) ----------
import json as _json
PRODUCTS_UI = [{"id": 1, "name": "Business Card"},
               {"id": 21, "name": "Loose Sheet — Litho (Offset)"},
               {"id": 50, "name": "Loose Sheet — Digital"},
               {"id": 19, "name": "Booklet — Litho (Offset)"},
               {"id": 37, "name": "Booklet — Digital"},
               {"id": 60, "name": "Label Sticker — Digital"},
               {"id": 61, "name": "Label Sticker — Letterpress (Hot Stamping)"},
               {"id": 24, "name": "Bill-Book — Litho (NCR Carbonless)"},
               {"id": 101, "name": "Brochure (= Loose Sheet Litho)"},
               {"id": 102, "name": "Flyer (= Loose Sheet Litho)"},
               {"id": 103, "name": "Customprint (= Loose Sheet Litho)"},
               {"id": 104, "name": "Notepad — Litho"},
               {"id": 105, "name": "Letterhead — Litho"},
               {"id": 106, "name": "Envelope — Litho"},
               {"id": 107, "name": "Folder — Litho (Presentation Folder)"},
               {"id": 108, "name": "L-Shape Plastic Folder — Digital"},
               {"id": 109, "name": "Bookmark — Digital"},
               {"id": 110, "name": "Voucher — Litho"},
               {"id": 111, "name": "Computer Form — Litho (NCR)"},
               {"id": 112, "name": "Wire-O Notebook — Litho"},
               {"id": 113, "name": "PVC Card — Digital"},
               {"id": 114, "name": "Kad Kahwin — Digital"},
               {"id": 115, "name": "Kad Terima Kasih — Digital"},
               {"id": 116, "name": "Static Cling Window Sticker — Digital"},
               {"id": 117, "name": "Car Sticker — Digital (= Static Cling form)"},
               {"id": 118, "name": "Wall Calendar — Litho"},
               {"id": 119, "name": "Arch File — Digital"},
               {"id": 120, "name": "Desk Calendar — Hard Stand (Litho)"},
               {"id": 121, "name": "Desk Calendar — Soft Stand (Litho)"},
               {"id": 122, "name": "Wire-O Wall Calendar — Litho"},
               {"id": 123, "name": "Banner — Litho"},
               {"id": 124, "name": "Bunting — Litho"},
               {"id": 125, "name": "Roll-Up Stand — Litho"},
               {"id": 126, "name": "Wobbler — Digital"},
               {"id": 127, "name": "Paper Bag — Litho"},
               {"id": 128, "name": "Canvas Tote Bag — Litho"},
               {"id": 129, "name": "Mug — Litho"},
               {"id": 130, "name": "Papan Kopi / Sachet Board — Litho"},
               {"id": 131, "name": "Pillow — Litho"},
               {"id": 132, "name": "Button Badge — Digital"},
               {"id": 133, "name": "Hand Fan — Digital"},
               {"id": 134, "name": "Hanger — Digital"},
               {"id": 135, "name": "Magnet — Digital"},
               {"id": 136, "name": "Hard Cover Menu — Digital"},
               {"id": 137, "name": "Standing Pouch — Litho"},
               {"id": 138, "name": "Money Packet — Litho"},
               {"id": 139, "name": "Non-Woven Bag — Litho"},
               {"id": 140, "name": "Tent Card — Litho"},
               {"id": 141, "name": "Stamp Chop"},
               {"id": 142, "name": "Mask Keeper — Litho"},
               {"id": 143, "name": "Sublimation Shirt"}]
SC_SIZES = ["54mm x 89mm", "75mm x 75mm", "100mm x 100mm", "110mm x 90mm", "115mm x 120mm",
            "130mm x 170mm", "165mm x 90mm", "220mm x 90mm", "104mm x 420mm", "310mm x 445mm"]
KAD_LAMS = ["Matte Lamination (Front)", "Matte Lamination (Both)",
            "Gloss Lamination (Front)", "Gloss Lamination (Both)"]
KT_SIZES = ["52mm x 52mm", "40mm x 86mm", "40mm x 70mm"]
KT_PAPERS = ["Gloss Art Card 230gsm (2 sides coated)", "Gloss Art Card 260gsm (2 sides coated)",
             "Gloss Art Card 310gsm (2 sides coated)", "Gloss Art Card 360gsm (2 sides coated)",
             "Super White 240gsm", "Metal Ice 250gsm"]
KK_SIZES = ["DL (99mm x 210mm)", "2DL (198mm x 210mm)", "A7 (74mm x 105mm)", "A6 (105mm x 148mm)",
            "A5 (148mm x 210mm)", "A4 (210mm x 297mm)", "Square (140mm x 280mm)"]
KK_PAPERS = ["Gloss Art Card 230gsm (2 sides coated)", "Gloss Art Card 260gsm (2 sides coated)",
             "Gloss Art Card 310gsm (2 sides coated)", "Gloss Art Card 360gsm (2 sides coated)",
             "Super White 240gsm", "Linen 240gsm", "Suwen 240gsm", "Simili 140gsm",
             "Metal Ice 250gsm", "Matte Art Paper 150gsm"]
WIREO_LAMS = ["Matte Lamination (Front)", "Gloss Lamination (Front)",
              "Matte Lamination (Front) + Spot UV (Front Cover)",
              "Matte Lamination (Front) + Spot UV (Front and Back Cover)"]
VOUCHER_SIZES = ["90mm x 140mm", "105mm x 145mm", "145mm x 145mm", "125mm x 175mm", "90mm x 190mm",
                 "107mm x 190mm", "60mm x 210mm", "145mm x 210mm", "55mm x 213mm", "95mm x 225mm",
                 "120mm x 230mm", "105mm x 300mm"]
VOUCHER_PAPERS = ["Art Paper 100gsm", "Art Paper 130gsm", "Art Paper 150gsm", "Matte Art Paper 150gsm",
                  "Colour Paper Buff 75gsm", "Colour Paper Blue 75gsm", "Colour Paper Green 75gsm",
                  "Colour Paper Pink 75gsm", "Colour Paper Purple 75gsm", "Colour Paper Yellow 75gsm",
                  "Simili 80gsm", "Simili 100gsm", "Art Card 230gsm (2 sides coated)",
                  "Art Card 260gsm (2 sides coated)"]
LSHAPE_PAPERS = ["Synthetic Paper 180micron", "Frosted Plastic 200 micron (0.2mm)"]
BOOKMARK_PAPERS = ["Gloss Art Card 250gsm (2 sides coated)", "Gloss Art Card 310gsm (2 sides coated)",
                   "Super White 250gsm", "Linen 240gsm", "Suwen 240gsm", "Synthetic Paper 180micron",
                   "Metal Ice 250gsm"]
FOLDER_MOULDS = ["FPF 001 — 350x510mm", "FPF 004 — 371x534mm", "FPF 005 — 410x614mm",
                 "FPF 014 — 326x613mm", "FPF 015 — 324x635mm", "FPF 016 — 631x478mm"]
FOLDER_PAPERS = ["Gloss Art Card 250gsm (1 side coated)", "Gloss Art Card 300gsm (1 side coated)",
                 "Gloss Art Card 250gsm (2 side coated)", "Gloss Art Card 310gsm (2 side coated)",
                 "Gloss Art Card 360gsm (2 side coated)"]
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
# Catalogue products whose Excard order page IS the Loose Sheet Litho form (aliases) —
# they reuse the litho engine/options exactly (see output/spec_link_map.json).
LOOSE_LITHO_ALIASES = (101, 102, 103)
BOOKLET_IDS = (19, 37)
ENVELOPE_RATE = {"108mm x 159mm - Pink A6": 0.043, "110mm x 220mm - White DL": 0.049}  # RM/piece (sampled)


def envelope_cost(env: str | None, qty: int) -> float:
    """Per-piece envelope add-on cost (sampled ~RM0.043–0.049/pc; default 0.046)."""
    if not env or env.startswith("Not"):
        return 0.0
    return ENVELOPE_RATE.get(env, 0.046) * int(qty)


ENVELOPE_OPTS = ["Not Required", "108mm x 159mm - Pink A6", "110mm x 220mm - White DL",
                 "133mm x 102mm - Cream A7", "162mm x 114mm - White A6",
                 "162mm x 229mm - Pink A5", "162mm x 229mm - White A5", "215mm x 114mm - Pink DL"]
BK_COVER_LAM = ["Not Required", "Matte Lamination (Front)", "Matte Lamination (Both)",
                "Matte Lamination (Front) + Spot UV (Front)", "Matte Lamination (Both) + Spot UV (Front)",
                "Gloss Lamination (Front)", "Gloss Lamination (Both)", "UV Varnish (Front)",
                "UV Varnish (Both)", "Gloss Waterbase Varnish (Front)", "Gloss Waterbase Varnish (Both)"]
BK_EMBOSS = ["Not Required", "90mm x 30mm", "90mm x 70mm", "95mm x 206mm", "101mm x 144mm",
             "144mm x 206mm", "194mm x 206mm", "206mm x 294mm"]
BILLBOOK_SIZES = ["145mm x 210mm", "A4 (210mm x 297mm)", "B5 (176mm x 250mm)", "90mm x 140mm",
                  "90mm x 177mm", "95mm x 210mm", "95mm x 225mm", "105mm x 145mm", "105mm x 175mm",
                  "107mm x 190mm", "110mm x 210mm", "120mm x 210mm", "120mm x 230mm", "125mm x 175mm",
                  "135mm x 210mm", "145mm x 148mm", "145mm x 190mm", "148mm x 190mm", "148mm x 291mm",
                  "160mm x 240mm", "165mm x 210mm", "170mm x 190mm", "173mm x 206mm", "180mm x 280mm",
                  "190mm x 210mm", "190mm x 270mm", "190mm x 290mm", "190mm x 297mm", "192mm x 268mm",
                  "194mm x 205mm", "206mm x 240mm", "206mm x 330mm", "210mm x 270mm", "210mm x 291mm",
                  "B4 (250mm x 353mm)", "291mm x 420mm", "F3 (330mm x 420mm)"]


@app.get("/api/printoka/products")
def printoka_products():
    return PRODUCTS_UI


# accuracy = MEASURED median % vs Excard (output/audit_report.json). Curve-based
# products are exact at Excard's order quantities; this median is the held-out /
# custom-quantity interpolation error.
FORMULATED = {1: 2.1, 21: 1.7, 50: 1.3, 19: 0.5, 37: 1.6, 60: 7.4, 61: 10.5, 24: 2.5,
              101: 1.7, 102: 1.7, 103: 1.7,  # aliases reuse loose-litho accuracy
              104: 5.2,  # notepad: exact at order qtys; 5.2 = held-out interp median
              105: 0.0,  # letterhead: EXACT v4 price-list lookup (paper x colour x packing Loose/Pad)
              106: 4.1,  # envelope: base LOO ~2%; held-out colour (additive) median 4.1%
              107: 0.0,  # folder: EXACT v4 price-list lookup (all mould groups + colour + lam + protective)
              108: 2.2,  # l-shape folder: per-paper curve LOO median 2.2%
              109: 2.5,  # bookmark: per-(paper|colour) log-log curve LOO median 2.5%
              110: 8.0,  # voucher: factor model — single axes exact, ~4% core interp + interactions
              111: 4.0,  # computer form: factor model — axes exact, core LOO ~4%
              112: 2.3,  # wire-o notebook: per-cover curve LOO median 2.3% (Hard Cover)
              113: 0.0,  # pvc card: EXACT v4 price-list lookup (colour x hole punch x VDP; all priced)
              114: 5.0,  # kad kahwin: factor model — axes exact, core LOO ~3%
              115: 4.0,  # kad terima kasih: factor model — axes exact, core LOO ~4%
              116: 5.9, 117: 5.9,  # static cling / car sticker: factor model, core LOO ~5.9%
              118: 1.7,  # wall calendar: qty curve LOO median 1.7%
              119: 0.0,  # arch file: flat RM5.00/unit — linear qty curve, exact
              120: 1.1,  # desk calendar hard stand: per-cat qty curve LOO median 1.12% (cat=1)
              121: 0.7,  # desk calendar soft stand: qty curve LOO median 0.67%
              122: 0.8,  # wire-o wall calendar: qty curve LOO median 0.82%
              123: 0.9,  # banner: per-size qty curve LOO median 0.9%
              124: 2.8,  # bunting (Tarpaulin): per size×fitting qty curve LOO median 2.81%
              125: 0.68,  # rollup: per-lam qty curve LOO median 0.68%
              126: 4.3,  # wobbler: per orient×paper×lam qty curve LOO median ~4.3%
              127: 17.4,  # paperbag: per-paper qty curve LOO 17% (anomalous q200 dip)
              128: 0.79,  # canvastote: per-colour qty curve LOO median 0.79%
              129: 0.53,  # mug: qty curve LOO median 0.53%
              130: 0.0,  # papan kopi: EXACT v4 price-list lookup (model)
              131: 0.0,  # pillow: qty curve LOO median 0.03% (effectively exact)
              132: 3.3,  # button badge: qty curve LOO median 3.27%; lamination price-neutral
              133: 3.3,  # hand fan: per-paper qty curve LOO median 3.27%
              134: 2.5,  # hanger: per-(paper x colour) qty curve LOO median 2.49%
              135: 1.0,  # magnet: per-shape qty curve LOO median 0.97%
              136: 2.2,  # hard cover menu: per-(order x add-content) qty curve LOO median 2.2%
              137: 9.6,  # standing pouch (Metalised): qty curve LOO median 9.6% (non-smooth curve)
              138: 0.0,  # money packet: EXACT v4 price-list lookup (model x package x paper x finishing)
              139: 0.0,  # non-woven bag: EXACT v4 price-list lookup (model x print colour)
              140: 0.0,  # tent card: EXACT v4 price-list lookup (model x lamination)
              141: 0.0,  # stamp chop: EXACT v4 unit price lookup (type x category x model)
              142: None,  # mask keeper: v4 price-list returns 500, quote only
              143: None}  # sublimation shirt: v4 price-list returns 500, quote only


def _accuracy(product_id: int):
    """Calibrated median % for a product: static map, else its spot-test report
    (booklet engines write spot_test_report_<id>.json)."""
    if product_id in FORMULATED:
        return FORMULATED[product_id]
    name = "spot_test_report_bizcard.json" if product_id == 1 else f"spot_test_report_{product_id}.json"
    rep = UI_DIR.parent / "output" / name
    if rep.exists():
        try:
            return _json.loads(rep.read_text()).get("median")
        except Exception:
            return None
    return None


def _booklet_valid_count(product_id: int) -> int:
    f = UI_DIR.parent / "output" / f"booklet_options_{product_id}.json"
    if not f.exists():
        return 0
    try:
        c = _json.loads(f.read_text()).get("combos", {})
        return sum(1 for v in c.values() if v)
    except Exception:
        return 0


@app.get("/api/printoka/product-status")
def product_status():
    """Drives the calculator's product picker — PRODUCTS_UI is authoritative so
    formula-only products (e.g. v4 Business Card, not in the crawl DB) appear too."""
    with session_scope() as s:
        counts = dict(s.execute(select(OrderWork.product_id, func.count())
                                .group_by(OrderWork.product_id)).all())
    out = []
    for p in PRODUCTS_UI:
        pid = p["id"]
        acc = _accuracy(pid)
        combos = counts.get(pid, 0) or _booklet_valid_count(pid)
        out.append({"id": pid, "name": p["name"], "combos_initiated": combos,
                    "accuracy": acc, "formulated": acc is not None})
    return out


# ---------- Booklet (products 19 & 37): richer cascade ----------
def _booklet_opts(product_id: int) -> dict:
    f = UI_DIR.parent / "output" / f"booklet_options_{product_id}.json"
    return _json.loads(f.read_text()) if f.exists() else {"combos": {}}


@app.get("/api/printoka/booklet/options")
def booklet_options(product: int = Query(...), orientation: str | None = None,
                    size: str | None = None, ordertype: str | None = None,
                    binding: str | None = None, page: str | None = None,
                    cover: str | None = None):
    """Cascade for the booklet form. Each provided level filters the next."""
    combos = _booklet_opts(product).get("combos", {})
    valid = {k: v for k, v in combos.items() if v}
    keys = [k.split("|") for k in valid]  # [orient, size, ordertype, binding]

    def distinct(idx, *fixed):
        seen = []
        for parts, k in zip(keys, valid):
            if all(parts[i] == val for i, val in fixed) and parts[idx] not in seen:
                seen.append(parts[idx])
        return seen

    out = {"orientations": distinct(0), "sizes": [], "ordertypes": [],
           "bindings": [], "pages": [], "covers": [], "contents": [],
           "colours": [], "outer_inner": [], "qty": []}
    if orientation:
        out["sizes"] = distinct(1, (0, orientation))
    if orientation and size:
        out["ordertypes"] = distinct(2, (0, orientation), (1, size))
    if orientation and size and ordertype:
        out["bindings"] = distinct(3, (0, orientation), (1, size), (2, ordertype))
    if orientation and size and ordertype and binding:
        key = f"{orientation}|{size}|{ordertype}|{binding}"
        v = valid.get(key)
        if v:
            out["pages"] = v["pages"]
            out["covers"] = list(v["covers"].keys())
            out["colours"] = v["content_colours"]
            out["outer_inner"] = v["outer_inner"]
            out["qty"] = v["qty"]
            if cover and cover in v["covers"]:
                out["contents"] = v["covers"][cover]["content_papers"]
    return out


@app.get("/api/printoka/booklet/quote")
def booklet_quote(product: int = Query(...), orientation: str = Query(...),
                  size: str = Query(...), ordertype: str = Query(...),
                  binding: str = Query(...), page: str = Query(...),
                  cover: str = Query(...), content: str = Query(...),
                  colour: str = Query("4C (Both)"), qty: int = Query(...),
                  outer_inner: str = Query("4C: 4 Colour Outer Only"),
                  hot_stamping: str = Query("Not Required"),
                  cover_lamination: str = Query("Not Required"),
                  cover_embossing: str = Query("Not Required"),
                  jawi: str = Query("No"),
                  extra_books: str = Query("No")):
    from . import booklet_engine as be
    try:
        cash = be.cash_price(size, page, ordertype, binding, cover, content,
                             colour, qty, outer_inner=outer_inner, product_id=product)
        extra = 30.0 if extra_books in ("Yes", "yes", "true", True) else 0.0
        cash += extra
        wt = be.weight_kg(size, page, ordertype, binding, cover, content, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    # Compulsory finishing (always included, shown like Excard) depends on binding.
    compulsory = "Creasing, Saddle Stitching + Folding" if "Saddle" in binding \
        else ("Perfect Binding" if "Perfect" in binding else binding)
    blocks = []
    if hot_stamping not in ("Not Required", ""): blocks.append("hot stamping")
    if cover_embossing not in ("Not Required", ""): blocks.append("embossing")
    if cover_lamination not in ("Not Required", ""): blocks.append("cover lamination")
    note = f"Compulsory finishing: {compulsory} (included)."
    if blocks:
        note += " " + ", ".join(blocks).capitalize() + " quoted separately by Excard (not in the online price)."
    return {"config": {"product": product, "orientation": orientation, "size": size,
                       "ordertype": ordertype, "binding": binding, "page": page,
                       "cover": cover, "content": content, "colour": colour,
                       "qty": qty, "outer_inner": outer_inner, "hot_stamping": hot_stamping,
                       "cover_lamination": cover_lamination, "cover_embossing": cover_embossing,
                       "jawi": jawi, "compulsory_finishing": compulsory,
                       "extra_books": extra_books},
            "printoka_cash": round(cash, 2), "finishing_cost": round(extra, 2),
            "method": "formula", "note": note,
            "tiers": be.tiers(cash), "weight_kg": wt}


# ---------- Generic schema (drives the schema-aware calculator UI) ----------
# Each product family declares an ordered field cascade. The UI renders fields in
# order, fetches options per field from `options` (passing all selected `depends`),
# reads the field's `optionsKey` from the response, and calls `quote` when complete.
# Adding/curating a product here makes it appear in the calculator automatically.
FIELD_SCHEMAS = {
    "loose": {"options": "/api/printoka/options", "quote": "/api/printoka/quote",
              "fields": [
                  {"key": "size", "label": "Size", "optionsKey": "sizes", "depends": []},
                  {"key": "paper", "label": "Paper", "optionsKey": "papers", "depends": ["size"]},
                  {"key": "colour", "label": "Print colour", "optionsKey": "colours", "depends": ["size", "paper"]},
                  {"key": "package", "label": "Package (ganging)", "optionsKey": "packages", "depends": ["size", "paper", "colour"]},
                  {"key": "envelope", "label": "Envelope (add-on)", "addon": True, "depends": [], "options": ENVELOPE_OPTS},
                  {"key": "custom_w", "label": "Custom width (mm) — optional, overrides Size", "type": "number", "optional": True, "min": 10, "max": 1000, "depends": []},
                  {"key": "custom_h", "label": "Custom height (mm) — optional", "type": "number", "optional": True, "min": 10, "max": 1000, "depends": []},
                  {"key": "hot_stamping", "label": "Hot stamping", "addon": True, "depends": [],
                   "options": ["Not Required", "1C (Front)", "1C (Back)", "2C (Front)", "2C (Back)"]},
                  {"key": "fold", "label": "Folding", "addon": True, "depends": [],
                   "options": ["None", "1Fa", "2Fa", "2Fb", "2Fc", "3Fa", "3Fb", "4Fa", "4Fb"]},
                  {"key": "punch", "label": "Hole punching", "addon": True, "depends": [],
                   "options": ["No", "3mm", "6mm"]},
              ]},
    "loose_digital": {"options": "/api/printoka/options", "quote": "/api/printoka/quote",
              "fields": [
                  {"key": "size", "label": "Size", "optionsKey": "sizes", "depends": []},
                  {"key": "paper", "label": "Paper", "optionsKey": "papers", "depends": ["size"]},
                  {"key": "colour", "label": "Print colour", "optionsKey": "colours", "depends": ["size", "paper"]},
                  {"key": "package", "label": "Package (ganging)", "optionsKey": "packages", "depends": ["size", "paper", "colour"]},
                  {"key": "custom_w", "label": "Custom width (mm) — optional, overrides Size", "type": "number", "optional": True, "min": 10, "max": 1000, "depends": []},
                  {"key": "custom_h", "label": "Custom height (mm) — optional", "type": "number", "optional": True, "min": 10, "max": 1000, "depends": []},
                  {"key": "hot_stamping", "label": "Hot stamping", "addon": True, "depends": [],
                   "options": ["Not Required", "1C (Front)", "1C (Back)", "2C (Front)", "2C (Back)"]},
                  {"key": "fold", "label": "Folding", "addon": True, "depends": [],
                   "options": ["None", "1Fa", "2Fa", "2Fb", "2Fc", "3Fa", "3Fb", "4Fa", "4Fb"]},
                  {"key": "punch", "label": "Hole punching", "addon": True, "depends": [],
                   "options": ["No", "3mm", "6mm"]},
                  {"key": "envelope", "label": "Envelope (add-on)", "addon": True, "depends": [], "options": ENVELOPE_OPTS},
              ]},
    "bizcard": {"options": "/api/printoka/bizcard/options", "quote": "/api/printoka/bizcard/quote",
                "fields": [
                    {"key": "cardType", "label": "Card type", "optionsKey": "cardTypes", "depends": []},
                    {"key": "size", "label": "Size", "optionsKey": "sizes", "depends": ["cardType"]},
                    {"key": "orientation", "label": "Orientation", "addon": True, "depends": [], "options": ["Landscape", "Portrait"]},
                    {"key": "paper", "label": "Paper", "optionsKey": "papers", "depends": ["cardType"]},
                    {"key": "colour", "label": "Print colour", "optionsKey": "colours", "depends": ["cardType"]},
                    {"key": "package", "label": "Package (designs)", "addon": True, "depends": [],
                     "options": ["Normal", "2in1", "3in1", "4in1", "5in1", "6in1", "7in1", "8in1", "9in1", "10in1"]},
                    {"key": "custom_w", "label": "Custom width (mm) — optional", "type": "number", "optional": True, "min": 20, "max": 200, "depends": []},
                    {"key": "custom_h", "label": "Custom height (mm) — optional", "type": "number", "optional": True, "min": 20, "max": 200, "depends": []},
                    {"key": "surface", "label": "Surface finishing", "addon": True, "depends": [],
                     "options": ["None", "Gloss Lamination (Both)", "Matte Lamination (Both)",
                                 "Soft Touch Lamination (Both)", "Spot UV (Front)", "Spot UV (Both)"]},
                    {"key": "round_corner", "label": "Round corner (R6mm)", "addon": True, "depends": [],
                     "options": ["No", "Yes"]},
                    {"key": "hole_punch", "label": "Hole punching", "addon": True, "depends": [],
                     "options": ["No", "3mm", "5mm"]},
                    {"key": "hot_stamping", "label": "Hot stamping (block quoted separately)", "addon": True, "depends": [],
                     "options": ["No Hot Stamping", "1C (Front)", "1C (Back)", "2C (Front)", "2C (Back)"]},
                    {"key": "embossing", "label": "Embossing (block quoted separately)", "addon": True, "depends": [],
                     "options": ["Not Required", "Embossing Front", "Embossing Back"]},
                ]},
    "sticker_digital": {"options": "/api/printoka/sticker/options", "quote": "/api/printoka/sticker/quote",
                "fields": [
                    {"key": "type", "label": "Product type", "addon": True, "depends": [],
                     "options": ["Sticker", "CD"]},
                    {"key": "category", "label": "Cut type (Sticker only)", "addon": True, "depends": [],
                     "options": ["Rectangle/Square", "Custom Die-Cut", "Standard Shape", "Round", "No Cut", "Kiss Cut (1up/sheet)", "Multiple Dieline (Available for different size and different shape)"]},
                    {"key": "paper", "label": "Material", "addon": True, "depends": [],
                     "options": ["Mirror Kote", "Mirror Kote (Strong Glue)", "Transparent OPP",
                                 "White PP (Polypropylene)", "White PE (Polyethylene)", "Synthetic Paper",
                                 "Printing Paper", "Brown Craft Paper", "Matte Silver Polyester",
                                 "Bright Silver Polyester", "Removable Transparent OPP",
                                 "Removable White PP", "Warranty Sticker"]},
                    {"key": "colour", "label": "Print colour", "addon": True, "depends": [], "options": ["4C", "1C"]},
                    {"key": "finishing", "label": "Lamination", "addon": True, "depends": [],
                     "options": ["Not Required", "Matte Laminate (Front)", "Gloss Laminate (Front)",
                                 "Gloss Water Based Varnish", "UV Varnish", "Soft Touch Laminate (Front)"]},
                    {"key": "hot_stamping", "label": "Hot stamping (block quoted separately)", "addon": True, "depends": [],
                     "options": ["Not Required", "Gold", "Silver"]},
                    {"key": "package", "label": "Package (N-in-1, ×N)", "addon": True, "depends": [],
                     "options": ["Normal", "2in1", "3in1", "4in1", "5in1", "6in1", "7in1", "8in1", "9in1", "10in1"]},
                    {"key": "sheet_size", "label": "Sheet size — Multiple Dieline only", "addon": True, "depends": [],
                     "options": ["A3+", "A4", "A5"]},
                    {"key": "dielines", "label": "Die lines per sheet — Multiple Dieline (no price effect)", "type": "number", "optional": True, "min": 1, "max": 100, "depends": []},
                    {"key": "height", "label": "Height (mm) — Rectangle/Standard/Custom", "type": "number", "min": 10, "max": 300, "default": 50, "depends": []},
                    {"key": "width", "label": "Width (mm) — Rectangle/Standard/Custom", "type": "number", "min": 10, "max": 300, "default": 90, "depends": []},
                    {"key": "diameter", "label": "Diameter (mm) — Round only", "type": "number", "optional": True, "min": 10, "max": 300, "depends": []},
                ]},
    "sticker_letterpress": {"options": "/api/printoka/sticker/options", "quote": "/api/printoka/sticker/quote",
                "fields": [
                    {"key": "category", "label": "Shape", "addon": True, "depends": [], "options": ["Standard Shape", "Round"]},
                    {"key": "colour", "label": "Hot stamping colour", "addon": True, "depends": [], "options": ["Gold", "Silver"]},
                    {"key": "height", "label": "Height (mm) — Standard Shape", "type": "number", "min": 10, "max": 300, "default": 50, "depends": []},
                    {"key": "width", "label": "Width (mm) — Standard Shape", "type": "number", "min": 10, "max": 300, "default": 90, "depends": []},
                    {"key": "diameter", "label": "Diameter (mm) — Round only", "type": "number", "optional": True, "min": 10, "max": 300, "depends": []},
                ]},
    "billbook": {"options": "/api/printoka/billbook/options", "quote": "/api/printoka/billbook/quote",
                "fields": [
                    {"key": "paper", "label": "Paper type", "addon": True, "depends": [], "options": ["NCR (Carbonize Paper)", "Normal Paper"]},
                    {"key": "packform", "label": "Form", "addon": True, "depends": [], "options": ["Book", "Pad"]},
                    {"key": "size", "label": "Size", "addon": True, "depends": [], "options": BILLBOOK_SIZES},
                    {"key": "layers", "label": "Plies (NCR layers)", "addon": True, "depends": [],
                     "options": ["NCR - 2 Layers", "NCR - 3 Layers", "NCR - 4 Layers", "NCR - 5 Layers", "NCR - 6 Layer"]},
                    {"key": "colour", "label": "Print colour / side", "addon": True, "depends": [],
                     "options": ["1C (Front)", "2C (Front)", "4C (Front)", "1C (Both)", "2C (Front) / 1C (Back)", "4C (Front) / 1C (Back)"]},
                    {"key": "sets", "label": "Sets per book (2-ply only; else fixed)", "addon": True, "depends": [], "options": ["50", "100"]},
                    {"key": "binding", "label": "Binding location", "addon": True, "depends": [],
                     "options": ["Portrait - Left side binding", "Portrait - Top side binding",
                                 "Landscape - Left side binding", "Landscape - Top side binding"]},
                    {"key": "numbering", "label": "Numbering (free)", "addon": True, "depends": [], "options": ["Not Required", "Required"]},
                    {"key": "punch", "label": "Hole punch (6mm)", "addon": True, "depends": [], "options": ["Not Required", "Required (6mm)"]},
                ]},
    "wallcal": {"options": "/api/printoka/wallcal/options", "quote": "/api/printoka/wallcal/quote",
                "fields": []},
    "archfile": {"options": "/api/printoka/archfile/options", "quote": "/api/printoka/archfile/quote",
                "fields": []},
    "deskcal_hard": {"options": "/api/printoka/deskcal/options", "quote": "/api/printoka/deskcal/quote",
                "fields": [
                    {"key": "cat", "label": "Model", "addon": True, "depends": [], "options": [
                        "WDCH 001 (Portrait)", "WDCH 002 (Landscape)", "DCHS 001 (Hot Stamping - Portrait)"]},
                ]},
    "deskcal_soft": {"options": "/api/printoka/deskcal_soft/options", "quote": "/api/printoka/deskcal_soft/quote",
                "fields": []},
    "wireow": {"options": "/api/printoka/wireow/options", "quote": "/api/printoka/wireow/quote",
                "fields": []},
    "banner": {"options": "/api/printoka/banner/options", "quote": "/api/printoka/banner/quote",
                "fields": [
                    {"key": "size", "label": "Size", "addon": True, "depends": [], "options": [
                        "3ft x 2ft", "4ft x 2ft", "6ft x 2ft", "4ft x 3ft", "8ft x 3ft",
                        "10ft x 3ft", "18ft x 3ft", "8ft x 4ft", "10ft x 4ft", "20ft x 4ft"]},
                ]},
    "bunting": {"options": "/api/printoka/bunting/options", "quote": "/api/printoka/bunting/quote",
                "fields": [
                    {"key": "size", "label": "Size", "addon": True, "depends": [], "options": [
                        "2ft x 5ft", "2ft x 6ft", "2.5ft x 6ft"]},
                    {"key": "paper", "label": "Material", "addon": True, "depends": [], "options": ["Tarpaulin 300gsm", "Synthetic Paper 180micron"]},
                    {"key": "protective", "label": "Fitting", "addon": True, "depends": [], "options": [
                        "Wood", "PVC Pipe", "Wood+Wire"]},
                ]},
    "rollup": {"options": "/api/printoka/rollup/options", "quote": "/api/printoka/rollup/quote",
                "fields": [
                    {"key": "lam", "label": "Lamination", "addon": True, "depends": [], "options": [
                        "Matte Lamination", "Gloss Lamination"]},
                ]},
    "wobbler": {"options": "/api/printoka/wobbler/options", "quote": "/api/printoka/wobbler/quote",
                "fields": [
                    {"key": "orient", "label": "Orientation", "addon": True, "depends": [], "options": [
                        "Portrait", "Landscape"]},
                    {"key": "paper", "label": "Paper", "addon": True, "depends": [], "options": [
                        "Gloss Art Card 250gsm", "Gloss Art Card 310gsm"]},
                    {"key": "lam", "label": "Lamination", "addon": True, "depends": [], "options": [
                        "Matte Lamination (Front)", "Gloss Lamination (Front)"]},
                    {"key": "finishing", "label": "Finishing", "addon": True, "depends": [], "options": [
                        "-", "Round Cornering (R6),4,1", "Digital Die-cutting,0,0"]},
                ]},
    "paperbag": {"options": "/api/printoka/paperbag/options", "quote": "/api/printoka/paperbag/quote",
                "fields": [
                    {"key": "paper", "label": "Paper", "addon": True, "depends": [], "options": [
                        "Gloss Art Paper 157gsm", "Gloss Art Card 190gsm (1 side coated)"]},
                    {"key": "lamination", "label": "Lamination (no online price change)", "addon": True, "depends": [],
                     "options": ["Gloss Lamination (Front)", "Matte Lamination (Front)"]},
                    {"key": "rope_colour", "label": "Rope Colour (no online price change)", "addon": True, "depends": [],
                     "options": ["Black", "Blue", "Red", "White", "Gold"]},
                ]},
    "canvastote": {"options": "/api/printoka/canvastote/options", "quote": "/api/printoka/canvastote/quote",
                "fields": [
                    {"key": "colour", "label": "Print colour", "addon": True, "depends": [], "options": [
                        "1C (Front)", "1C (Both)"]},
                ]},
    "mug": {"options": "/api/printoka/mug/options", "quote": "/api/printoka/mug/quote",
                "fields": []},
    "papan_kopi": {"options": "/api/printoka/papan_kopi/options", "quote": "/api/printoka/papan_kopi/quote",
                "fields": [
                    {"key": "model", "label": "Model (SB 01=537x334mm 20win · SB 02=622x346mm 20win · SB 03=547x346mm 20win · SB 04=547x346mm 15win)", "addon": True, "depends": [], "options": [
                        "SB 01", "SB 02", "SB 03", "SB 04"]},
                ]},
    "pillow": {"options": "/api/printoka/pillow/options", "quote": "/api/printoka/pillow/quote",
                "fields": []},
    "buttonbadge": {"options": "/api/printoka/buttonbadge/options", "quote": "/api/printoka/buttonbadge/quote",
                "fields": [
                    {"key": "lamination", "label": "Lamination (price-neutral)", "addon": True, "depends": [],
                     "options": ["Gloss", "Soft Touch"]}]},
    "handfan": {"options": "/api/printoka/handfan/options", "quote": "/api/printoka/handfan/quote",
                "fields": [
                    {"key": "paper", "label": "Paper", "addon": True, "depends": [],
                     "options": ["Gloss Art Card 310gsm", "Gloss Art Card 360gsm"]},
                    {"key": "lamination", "label": "Lamination (priced at Matte Both)", "addon": True, "depends": [],
                     "options": ["Matte Lamination (Both)", "Gloss Lamination (Both)"]}]},
    "hanger": {"options": "/api/printoka/hanger/options", "quote": "/api/printoka/hanger/quote",
                "fields": [
                    {"key": "paper", "label": "Paper", "addon": True, "depends": [],
                     "options": ["Gloss Art Card 310gsm (2 sides coated)", "Gloss Art Card 360gsm (2 sides coated)"]},
                    {"key": "colour", "label": "Print colour / side", "addon": True, "depends": [],
                     "options": ["4C (Front)", "4C (Both)"]},
                    {"key": "lamination", "label": "Lamination (priced at Matte Both)", "addon": True, "depends": [],
                     "options": ["Matte Lamination (Both)", "Gloss Lamination (Both)"]}]},
    "magnet": {"options": "/api/printoka/magnet/options", "quote": "/api/printoka/magnet/quote",
                "fields": [
                    {"key": "shape", "label": "Shape", "addon": True, "depends": [],
                     "options": ["Rectangle/Square", "Round", "Custom Die-Cut (with round corner)", "Multiple Dieline"]},
                    {"key": "finishing", "label": "Finishing (Soft Touch ~+RM4)", "addon": True, "depends": [],
                     "options": ["Matte Laminate (Front)", "Gloss Laminate (Front)", "Soft Touch Laminate (Front)"]}]},
    "hardmenu": {"options": "/api/printoka/hardmenu/options", "quote": "/api/printoka/hardmenu/quote",
                "fields": [
                    {"key": "order", "label": "Order", "addon": True, "depends": [],
                     "options": ["Cover + Content", "Cover only", "Content only"]},
                    {"key": "addcontent", "label": "Add content sheets (Cover only: -)", "addon": True, "depends": [],
                     "options": ["12", "16", "-"]},
                    {"key": "lamination", "label": "Lamination (price-neutral)", "addon": True, "depends": [],
                     "options": ["Gloss Lamination (Both)", "Matte Lamination (Both)"]}]},
    "pouch": {"options": "/api/printoka/pouch/options", "quote": "/api/printoka/pouch/quote",
                "fields": [
                    {"key": "paper", "label": "Material", "addon": True, "depends": [],
                     "options": ["Metalised Pet Film", "Transparent Pet Film"]},
                    {"key": "lamination", "label": "Lamination (price-neutral)", "addon": True, "depends": [],
                     "options": ["Matte Lamination", "Gloss Lamination"]}]},
    "staticcling": {"options": "/api/printoka/staticcling/options", "quote": "/api/printoka/staticcling/quote",
                "fields": [
                    {"key": "size", "label": "Size", "addon": True, "depends": [], "options": SC_SIZES},
                    {"key": "direction", "label": "Print direction", "addon": True, "depends": [], "options": ["Face Out View", "Face In View", "Both Side View"]},
                    {"key": "vdp", "label": "Variable Data Printing", "addon": True, "depends": [], "options": ["Not Required", "Variable Data Printing (VDP)"]},
                ]},
    "kadterima": {"options": "/api/printoka/kadterima/options", "quote": "/api/printoka/kadterima/quote",
                "fields": [
                    {"key": "size", "label": "Size", "addon": True, "depends": [], "options": KT_SIZES},
                    {"key": "paper", "label": "Paper", "addon": True, "depends": [], "options": KT_PAPERS},
                    {"key": "colour", "label": "Print colour / side", "addon": True, "depends": [], "options": ["4C (Front)", "4C (Both)"]},
                    {"key": "lamination", "label": "Lamination (no online price change)", "addon": True, "depends": [], "options": KAD_LAMS},
                    {"key": "hole_punch", "label": "Hole punching (3mm)", "addon": True, "depends": [], "options": ["No", "Yes"]},
                ]},
    "kadkahwin": {"options": "/api/printoka/kadkahwin/options", "quote": "/api/printoka/kadkahwin/quote",
                "fields": [
                    {"key": "ordertype", "label": "Order type", "addon": True, "depends": [], "options": ["Standard Kad Kahwin", "Custom Die-cut Kad Kahwin"]},
                    {"key": "size", "label": "Size", "addon": True, "depends": [], "options": KK_SIZES},
                    {"key": "paper", "label": "Paper", "addon": True, "depends": [], "options": KK_PAPERS},
                    {"key": "colour", "label": "Print colour / side", "addon": True, "depends": [], "options": ["4C (Front)", "4C (Both)"]},
                    {"key": "lamination", "label": "Lamination (no online price change)", "addon": True, "depends": [], "options": KAD_LAMS},
                    {"key": "envelope", "label": "Envelope (no online price change)", "addon": True, "depends": [], "options": ["Not Required", "White", "Pink"]},
                    {"key": "hot_stamping", "label": "Hot stamping (quoted separately)", "addon": True, "depends": [], "options": ["Not Required", "1C (Front)", "1C (Back)", "2C (Front)", "2C (Back)"]},
                ]},
    "pvccard": {"options": "/api/printoka/pvccard/options", "quote": "/api/printoka/pvccard/quote",
                "fields": [
                    {"key": "orientation", "label": "Orientation (no online price change)", "addon": True, "depends": [], "options": ["Portrait", "Landscape"]},
                    {"key": "colour", "label": "Print colour", "addon": True, "depends": [], "options": ["4C (Front)", "4C (Both)"]},
                    {"key": "hole_punch", "label": "Hole punching", "addon": True, "depends": [], "options": ["Not Required", "Hole Punching (6mm)"]},
                    {"key": "vdp", "label": "Variable Data Printing", "addon": True, "depends": [], "options": ["Not Required", "Variable Data Printing (Front)", "Variable Data Printing (Back)", "Variable Data Printing (Both)"]},
                ]},
    "wireo": {"options": "/api/printoka/wireo/options", "quote": "/api/printoka/wireo/quote",
                "fields": [
                    {"key": "cover", "label": "Cover type", "addon": True, "depends": [], "options": ["Hard Cover", "VDP Hard Cover", "Soft Cover"]},
                    {"key": "lamination", "label": "Cover lamination (compulsory)", "addon": True, "depends": [], "options": WIREO_LAMS},
                    {"key": "addcontent", "label": "Additional content sheets", "addon": True, "depends": [], "options": ["Not Required", "4 sheets", "8 sheets", "12 sheets"]},
                    {"key": "hot_stamping", "label": "Cover hot stamping (quoted separately)", "addon": True, "depends": [], "options": ["Not Required", "1C (Front Cover)", "2C (Front Cover)", "1C (Front & Back Cover)", "2C (Front & Back Cover)"]},
                ]},
    "computerform": {"options": "/api/printoka/computerform/options", "quote": "/api/printoka/computerform/quote",
                "fields": [
                    {"key": "package", "label": "Package", "addon": True, "depends": [],
                     "options": ["Multi Layer Computer Form", "Single Layer Computer Form", "Pay Slip"]},
                    {"key": "layers", "label": "Layers / plies (Multi Layer only)", "addon": True, "depends": [], "options": ["2", "3", "4", "5"]},
                    {"key": "ups", "label": "Ups (forms per set)", "addon": True, "depends": [], "options": ["1", "2", "3"]},
                    {"key": "colour", "label": "Print colour", "addon": True, "depends": [], "options": ["1C", "2C", "4C"]},
                    {"key": "copychange", "label": "Copy change (no online price change)", "addon": True, "depends": [], "options": ["No", "Yes"]},
                    {"key": "numbering", "label": "Numbering (quoted separately)", "addon": True, "depends": [], "options": ["No", "Yes"]},
                ]},
    "voucher": {"options": "/api/printoka/voucher/options", "quote": "/api/printoka/voucher/quote",
                "fields": [
                    {"key": "packform", "label": "Form", "addon": True, "depends": [], "options": ["Pad", "Book", "Loose"]},
                    {"key": "size", "label": "Size", "addon": True, "depends": [], "options": VOUCHER_SIZES},
                    {"key": "paper", "label": "Content paper", "addon": True, "depends": [], "options": VOUCHER_PAPERS},
                    {"key": "colour", "label": "Content colour", "addon": True, "depends": [], "options": ["4C (Front)", "4C (Both)"]},
                    {"key": "sets", "label": "Sets per book/pad", "addon": True, "depends": [], "options": ["10", "25", "50"]},
                    {"key": "perforation", "label": "Perforation lines (no online price change)", "addon": True, "depends": [], "options": ["0", "1", "2"]},
                    {"key": "numbering", "label": "Numbering", "addon": True, "depends": [], "options": ["No", "Yes"]},
                ]},
    "bookmark": {"options": "/api/printoka/bookmark/options", "quote": "/api/printoka/bookmark/quote",
                "fields": [
                    {"key": "paper", "label": "Paper", "addon": True, "depends": [], "options": BOOKMARK_PAPERS},
                    {"key": "colour", "label": "Print colour / side", "addon": True, "depends": [], "options": ["4C (Front)", "4C (Both)"]},
                    {"key": "lamination", "label": "Lamination (no online price change)", "addon": True, "depends": [], "options": ["Not Required", "Matte Lamination (Both)", "Gloss Lamination (Both)"]},
                    {"key": "round_corner", "label": "Round cornering", "addon": True, "depends": [], "options": ["Not Required", "Round Corner"]},
                    {"key": "hole_punch", "label": "Hole punching", "addon": True, "depends": [], "options": ["Not Required", "Hole Punching (6mm)"]},
                ]},
    "lshape": {"options": "/api/printoka/lshape/options", "quote": "/api/printoka/lshape/quote",
                "fields": [
                    {"key": "paper", "label": "Material", "addon": True, "depends": [], "options": LSHAPE_PAPERS},
                ]},
    "folder": {"options": "/api/printoka/folder/options", "quote": "/api/printoka/folder/quote",
                "fields": [
                    {"key": "model", "label": "Folder model", "addon": True, "depends": [], "options": [
                        "FPF 001", "FPF 004", "FPF 005", "FPF 014", "FPF 015", "FPF 016",
                        "FDF 001", "FDF 002", "FKF 001", "FKF 002", "FCD 004"]},
                    {"key": "paper", "label": "Paper (Gloss Art Card)", "addon": True, "depends": [], "options": [
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
                     "options": ["N/A", "Gloss Waterbase Varnish (Back)"]},
                ]},
    "envelope": {"options": "/api/printoka/envelope/options", "quote": "/api/printoka/envelope/quote",
                "fields": [
                    {"key": "model", "label": "Envelope model (size / window)", "addon": True, "depends": [], "options": ENVELOPE_MODELS},
                    {"key": "colour", "label": "Print colour / side", "addon": True, "depends": [], "options": ENVELOPE_COLOURS},
                ]},
    "letterhead": {"options": "/api/printoka/letterhead/options", "quote": "/api/printoka/letterhead/quote",
                "fields": [
                    {"key": "paper", "label": "Paper", "addon": True, "depends": [],
                     "options": ["Simili 80gsm", "Simili 100gsm", "Conqueror 100gsm Brilliant White Laid",
                                 "Conqueror 100gsm Diamond White Laid", "Conqueror 100gsm White Wove",
                                 "Conqueror 100gsm Cream Laid"]},
                    {"key": "colour", "label": "Print colour / side", "addon": True, "depends": [],
                     "options": ["1C (Front)", "2C (Front)", "4C (Front)", "4C (Both)"]},
                    {"key": "packing", "label": "Packing", "addon": True, "depends": [],
                     "options": ["Loose", "Pad (100 pcs per pad)"]},
                ]},
    "notepad": {"options": "/api/printoka/notepad/options", "quote": "/api/printoka/notepad/quote",
                "fields": [
                    {"key": "paper", "label": "Cover paper (weight only; no price change)", "addon": True, "depends": [],
                     "options": ["Gloss Art Card 260gsm (2 side coated)", "Gloss Art Card 310gsm (2 side coated)"]},
                    {"key": "lamination", "label": "Lamination (Matte Both compulsory; +Spot UV adds a cost)", "addon": True, "depends": [],
                     "options": ["Matte Lamination (Both)", "Matte Lamination (Both) + Spot UV (Front Cover)"]},
                ]},
    "money_packet": {"options": "/api/printoka/money_packet/options", "quote": "/api/printoka/money_packet/quote",
                "fields": [
                    {"key": "model", "label": "Model (MP 101=154x79.5mm · MP 103=79.5x154mm · MP 104=85x167mm)", "addon": True, "depends": [], "options": [
                        "MP 101", "MP 103", "MP 104"]},
                    {"key": "package", "label": "Package (number of designs)", "addon": True, "depends": [], "options": [
                        "Normal", "Dual Design", "5 Design", "6 Design"]},
                    {"key": "paper", "label": "Paper", "addon": True, "depends": [], "options": [
                        "Gloss Art Paper 130gsm", "Linen 140gsm", "Art Paper 157gsm"]},
                    {"key": "finishing", "label": "Finishing", "addon": True, "depends": [], "options": [
                        "N/A", "Matte Lamination", "Soft Touch Lamination"]},
                    {"key": "packing", "label": "Packing method (price-neutral; for info)", "addon": True, "depends": [], "options": [
                        "5pcs / Pack", "6pcs / Pack", "8pcs / Pack", "10pcs / Pack"]},
                ]},
    "tent_card": {"options": "/api/printoka/tent_card/options", "quote": "/api/printoka/tent_card/quote",
                "fields": [
                    {"key": "model", "label": "Model (TC 003=294x86mm · TC 004=294x140mm)", "addon": True, "depends": [], "options": [
                        "TC 003", "TC 004"]},
                    {"key": "lamination", "label": "Lamination", "addon": True, "depends": [], "options": [
                        "Matte Lamination (Both)", "Matte Lamination (Both) + Spot UV (Front)"]},
                ]},
    "stamp_chop": {"options": "/api/printoka/stamp_chop/options", "quote": "/api/printoka/stamp_chop/quote",
                "fields": [
                    {"key": "stamp_type", "label": "Stamp Type", "optionsKey": "stamp_types", "depends": []},
                    {"key": "category", "label": "Category", "optionsKey": "categories", "depends": ["stamp_type"]},
                    {"key": "model_key", "label": "Model", "optionsKey": "model_keys", "depends": ["stamp_type", "category"]},
                ]},
    "non_woven_bag": {"options": "/api/printoka/non_woven_bag/options", "quote": "/api/printoka/non_woven_bag/quote",
                "fields": [
                    {"key": "model", "label": "Model (determines size · WN-B5=200x230x80mm · WS-A4=280x330x80mm · WS-A3P=350x350x100mm · WS-A3L=420x320x100mm · WH-A4=280x330x80mm)", "addon": True, "depends": [], "options": [
                        "WN-B5", "WS-A4", "WS-A3P", "WS-A3L", "WH-A4"]},
                    {"key": "print_colour", "label": "Print Colour (WN/WS=1C only · WH=4C only)", "addon": True, "depends": [], "options": [
                        "1C (Front)", "1C (Both)", "4C (Front)", "4C (Both)"]},
                    {"key": "bag_colour", "label": "Bag Colour (price-neutral; for info)", "addon": True, "depends": [], "options": [
                        "Black", "White", "Beige", "Yellow", "Orange", "Dark Orange", "Magenta", "Red",
                        "Maroon", "Green", "Milo Green", "Dark Green", "Turquoise", "Cyan",
                        "Royal Blue", "Navy Blue", "Dark Purple", "Light Brown", "Dark Brown", "Grey"]},
                    {"key": "handle_length", "label": "Handle Length (price-neutral; for info)", "addon": True, "depends": [], "options": [
                        "300mm", "440mm", "500mm"]},
                    {"key": "handle_colour", "label": "Handle Colour (price-neutral; for info)", "addon": True, "depends": [], "options": [
                        "Same as bag colour", "Black", "White", "Beige", "Orange", "Dark Orange", "Magenta",
                        "Red", "Maroon", "Green", "Milo Green", "Dark Green", "Turquoise", "Cyan",
                        "Royal Blue", "Navy Blue", "Dark Purple", "Light Brown", "Dark Brown", "Grey"]},
                ]},
    "mask_keeper": {"options": "/api/printoka/mask_keeper/options", "quote": "/api/printoka/mask_keeper/quote",
                "fields": []},
    "sublimation_shirt": {"options": "/api/printoka/sublimation_shirt/options", "quote": "/api/printoka/sublimation_shirt/quote",
                "fields": []},
    "booklet": {"options": "/api/printoka/booklet/options", "quote": "/api/printoka/booklet/quote",
                "fields": [
                    {"key": "orientation", "label": "Orientation", "optionsKey": "orientations", "depends": []},
                    {"key": "size", "label": "Size", "optionsKey": "sizes", "depends": ["orientation"]},
                    {"key": "ordertype", "label": "Cover type", "optionsKey": "ordertypes", "depends": ["orientation", "size"]},
                    {"key": "binding", "label": "Binding", "optionsKey": "bindings", "depends": ["orientation", "size", "ordertype"]},
                    {"key": "page", "label": "Pages (incl. cover)", "optionsKey": "pages", "depends": ["orientation", "size", "ordertype", "binding"]},
                    {"key": "cover", "label": "Cover paper", "optionsKey": "covers", "depends": ["orientation", "size", "ordertype", "binding"]},
                    {"key": "content", "label": "Content paper", "optionsKey": "contents", "depends": ["orientation", "size", "ordertype", "binding", "cover"]},
                    {"key": "colour", "label": "Content print colour", "optionsKey": "colours", "depends": ["orientation", "size", "ordertype", "binding"]},
                    {"key": "outer_inner", "label": "Cover colour sides", "addon": True, "depends": [],
                     "options": ["4C: 4 Colour Outer Only", "4C: 4 Colour Outer & 4 Colour Inner"]},
                    {"key": "cover_lamination", "label": "Cover lamination / finishing", "addon": True, "depends": [], "options": BK_COVER_LAM},
                    {"key": "cover_embossing", "label": "Cover embossing — emboss size (block quoted separately)", "addon": True, "depends": [], "options": BK_EMBOSS},
                    {"key": "hot_stamping", "label": "Cover hot stamping (block quoted separately)", "addon": True, "depends": [],
                     "options": ["Not Required", "1C (Front)", "2C (Front)"]},
                    {"key": "jawi", "label": "Jawi content", "addon": True, "depends": [], "options": ["No", "Yes"]},
                    {"key": "extra_books", "label": "Add 3 extra books (+RM30)", "addon": True, "depends": [], "options": ["No", "Yes"]},
                ]},
}


# Attach Excard option images (thumbnails) to image-bearing option fields. The map
# (output/option_images.json) is {family: {field_key: {option_label: image_url}}} — hotlinked
# from Excard so the calculator shows the same product images Excard does.
def _attach_option_images():
    f = UI_DIR.parent / "output" / "option_images.json"
    if not f.exists():
        return
    imgs = _json.loads(f.read_text(encoding="utf-8"))
    for fam, fields in imgs.items():
        sch = FIELD_SCHEMAS.get(fam)
        if not sch:
            continue
        for fld in sch["fields"]:
            if fld["key"] in fields:
                fld["images"] = fields[fld["key"]]


_attach_option_images()


def _family(product_id: int) -> str:
    if product_id in (19, 37):
        return "booklet"
    if product_id in (1,):  # business card (added when calibrated)
        return "bizcard"
    if product_id == 60:
        return "sticker_digital"
    if product_id == 61:
        return "sticker_letterpress"
    if product_id == 50:
        return "loose_digital"   # has finishing add-ons (hot stamp / fold / punch)
    if product_id == 24:
        return "billbook"
    if product_id == 104:
        return "notepad"
    if product_id == 105:
        return "letterhead"
    if product_id == 106:
        return "envelope"
    if product_id == 107:
        return "folder"
    if product_id == 108:
        return "lshape"
    if product_id == 109:
        return "bookmark"
    if product_id == 110:
        return "voucher"
    if product_id == 111:
        return "computerform"
    if product_id == 112:
        return "wireo"
    if product_id == 113:
        return "pvccard"
    if product_id == 114:
        return "kadkahwin"
    if product_id == 115:
        return "kadterima"
    if product_id in (116, 117):
        return "staticcling"
    if product_id == 118:
        return "wallcal"
    if product_id == 119:
        return "archfile"
    if product_id == 120:
        return "deskcal_hard"
    if product_id == 121:
        return "deskcal_soft"
    if product_id == 122:
        return "wireow"
    if product_id == 123:
        return "banner"
    if product_id == 124:
        return "bunting"
    if product_id == 125:
        return "rollup"
    if product_id == 126:
        return "wobbler"
    if product_id == 127:
        return "paperbag"
    if product_id == 128:
        return "canvastote"
    if product_id == 129:
        return "mug"
    if product_id == 130:
        return "papan_kopi"
    if product_id == 131:
        return "pillow"
    if product_id == 132:
        return "buttonbadge"
    if product_id == 133:
        return "handfan"
    if product_id == 134:
        return "hanger"
    if product_id == 135:
        return "magnet"
    if product_id == 136:
        return "hardmenu"
    if product_id == 137:
        return "pouch"
    if product_id == 138:
        return "money_packet"
    if product_id == 139:
        return "non_woven_bag"
    if product_id == 140:
        return "tent_card"
    if product_id == 141:
        return "stamp_chop"
    if product_id == 142:
        return "mask_keeper"
    if product_id == 143:
        return "sublimation_shirt"
    return "loose"


@app.get("/api/printoka/schema")
def printoka_schema(product: int = Query(...)):
    fam = _family(product)
    sch = FIELD_SCHEMAS.get(fam)
    if not sch:
        return JSONResponse({"error": f"no schema for product {product}"}, status_code=404)
    name = next((p["name"] for p in PRODUCTS_UI if p["id"] == product), str(product))
    return {"id": product, "name": name, "family": fam,
            "accuracy": _accuracy(product),
            "options_endpoint": sch["options"], "quote_endpoint": sch["quote"],
            "fields": sch["fields"]}


# ---------- Business Card (v4 product, id 1) ----------
_BC_LABELS = {"Standard Card": "standard", "Thin Fold": "thin_fold",
              "Fat Fold": "fat_fold", "Custom Die-Cut": "custom_die_cut",
              "Plastic Card": "plastic_card"}


@app.get("/api/printoka/bizcard/options")
def bizcard_options(product: int = Query(1), cardType: str | None = None):
    from .bizcard_sampler import CARDTYPES, PAPERS, PLASTIC_PAPER
    out = {"cardTypes": list(_BC_LABELS.keys()), "sizes": [], "papers": [], "colours": []}
    if cardType:
        key = _BC_LABELS.get(cardType, cardType)
        ct = CARDTYPES.get(key)
        if ct:
            _od, sizes, colours, _custom = ct
            out["sizes"] = sizes
            out["papers"] = [PLASTIC_PAPER] if key == "plastic_card" else PAPERS
            out["colours"] = colours
    return out


@app.get("/api/printoka/bizcard/quote")
def bizcard_quote(product: int = Query(1), cardType: str = Query(...),
                  size: str = Query(...), paper: str = Query(...),
                  colour: str = Query(...), qty: int = Query(...),
                  package: str = Query("Normal"), surface: str = Query("None"),
                  round_corner: str = Query("No"), hole_punch: str = Query("No"),
                  hot_stamping: str = Query("No Hot Stamping"),
                  embossing: str = Query("Not Required"),
                  custom_h: float = Query(0), custom_w: float = Query(0)):
    from . import bizcard_engine as BE
    from . import bizcard_finishing as BF
    key = _BC_LABELS.get(cardType, cardType)
    mult = package_multiplier(package)
    if custom_h and custom_w:
        size = f"{int(custom_w)}mm x {int(custom_h)}mm"
    try:
        base = BE.cash_price(key, size, paper, colour, qty)
        fin = BF.finishing_cost({"surface": surface, "round_corner": round_corner,
                                 "hole_punch": hole_punch}, qty)
        cash = (base + fin) * mult
        wt = BE.weight_kg(size, paper, qty) * mult
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    note = None
    if hot_stamping not in ("", "No Hot Stamping") or embossing not in ("", "Not Required"):
        note = "Hot stamping / embossing block charge is quoted separately by Excard."
    return {"config": {"product": product, "cardType": cardType, "size": size,
                       "paper": paper, "colour": colour, "qty": qty, "package": package,
                       "surface": surface, "round_corner": round_corner, "hole_punch": hole_punch,
                       "hot_stamping": hot_stamping, "embossing": embossing},
            "printoka_cash": round(cash, 2), "finishing_cost": round(fin * mult, 2),
            "method": "formula", "note": note,
            "tiers": BE.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Label Sticker (products 60 Digital / 61 Letterpress) ----------
@app.get("/api/printoka/sticker/options")
def sticker_options(product: int = Query(60)):
    return {}  # all sticker fields are inline add-on / number fields in the schema


@app.get("/api/printoka/sticker/quote")
def sticker_quote(product: int = Query(60), height: float = Query(0),
                  width: float = Query(0), qty: int = Query(...),
                  category: str = Query("Rectangle/Square"), paper: str = Query("Mirror Kote"),
                  colour: str = Query("4C"), diameter: float = Query(0),
                  finishing: str = Query("Not Required"), sheet_size: str = Query("A3+"),
                  package: str = Query("Normal"), type: str = Query("Sticker"),
                  hot_stamping: str = Query("Not Required")):
    from . import sticker_engine as SE
    # Multiple Dieline is sheet-based: qty = number of press sheets, sized A3+/A4/A5.
    MD_SHEET_MM = {"A3+": (317, 425), "A4": (210, 297), "A5": (148, 210)}
    method = "letterpress" if product == 61 else "digital"
    mult = package_multiplier(package)  # N-in-1 = pure xN gang (verified)
    fin = 0.0
    try:
        if method == "digital" and type == "CD":
            from . import sticker_categories as SC
            cash = SC.cd_price(paper, colour, qty) * mult
            wt = SE.weight_kg(117, 117, qty) * mult  # standard CD label ~117mm disc
            return {"config": {"product": product, "method": method, "type": "CD",
                               "paper": paper, "colour": colour, "qty": qty, "package": package},
                    "note": "CD disc label (fixed shape); Mirror Kote / Printing Paper only.",
                    "printoka_cash": round(cash, 2), "finishing_cost": 0.0,
                    "method": "formula (CD curve)",
                    "tiers": SE.tiers(cash), "weight_kg": round(wt, 3)}
        if method == "digital" and category in ("Multiple Dieline", "Multiple Dieline (Available for different size and different shape)"):
            from . import sticker_categories as SC
            cash = SC.category_price(category, 0, 0, paper, colour, qty, sheet_size=sheet_size) * mult
            sh, sw = MD_SHEET_MM.get(sheet_size, (317, 425))
            wt = SE.weight_kg(sh, sw, qty) * mult  # each sheet weighed as one "piece"
            note = "Multiple Dieline is priced per press sheet (A3+/A4/A5). Die lines per sheet do not affect price; lamination quoted separately."
            return {"config": {"product": product, "method": method, "category": category,
                               "paper": paper, "colour": colour, "sheet_size": sheet_size,
                               "qty": qty, "package": package, "finishing": finishing}, "note": note,
                    "printoka_cash": round(cash, 2), "finishing_cost": 0.0,
                    "method": "formula (sheet curve)",
                    "tiers": SE.tiers(cash), "weight_kg": round(wt, 3)}
        if method == "digital":
            from . import sticker_categories as SC
            from . import sticker_finishing as SF
            cash = SC.category_price(category, float(height), float(width), paper,
                                     colour, qty, diameter=float(diameter))
            fh = float(diameter) if (category == "Round" and diameter) else (float(height) or 50)
            fw = float(diameter) if (category == "Round" and diameter) else (float(width) or 50)
            fin = SF.finishing_cost(finishing, fh, fw, qty)
            cash = (cash + fin) * mult       # N-in-1 = pure xN gang (digital, verified)
            fin = fin * mult
        else:  # letterpress: Round uses diameter as W=H (package not offered)
            if category == "Round" and diameter:
                cash = SE.cash_price(method, float(diameter), float(diameter), paper, colour, qty)
            else:
                cash = SE.cash_price(method, float(height) or 50, float(width) or 50, paper, colour, qty)
        # weight uses the bounding box (diameter for round, else h×w)
        wh = float(diameter) if (category == "Round" and diameter) else float(height)
        ww = float(diameter) if (category == "Round" and diameter) else float(width)
        wt = SE.weight_kg(wh or 50, ww or 50, qty) * (mult if method == "digital" else 1)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    hs_note = ("Hot stamping (%s) block/foil charge is quoted separately by Excard." % hot_stamping) \
        if hot_stamping not in ("Not Required", "") else None
    return {"config": {"product": product, "method": method, "category": category,
                       "paper": paper, "colour": colour, "height": height, "width": width,
                       "diameter": diameter, "qty": qty, "package": package, "finishing": finishing,
                       "hot_stamping": hot_stamping},
            "printoka_cash": round(cash, 2), "finishing_cost": round(fin, 2),
            "method": "formula (imposition)", "note": hs_note,
            "tiers": SE.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Parity checker (Excard options vs our build) ----------
@app.get("/api/printoka/parity")
def parity_report():
    """Latest option-parity report: per built product, which Excard controls/options our
    build is missing. Refresh with `python -m app.parity_checker`."""
    f = UI_DIR.parent / "output" / "parity_report.json"
    if not f.exists():
        return {"status": "not_run", "note": "run python -m app.parity_checker"}
    rep = _json.loads(f.read_text(encoding="utf-8"))
    summary = {fam: {"gaps": len(r.get("gaps", [])), "detail": r.get("gaps", [])}
               for fam, r in rep.items()}
    return {"families": len(rep), "total_gaps": sum(v["gaps"] for v in summary.values()),
            "by_family": summary}


# ---------- Catalogue auto check-up (scan Excard + coverage) ----------
@app.get("/api/printoka/catalogue/coverage")
def catalogue_coverage():
    """Latest Excard catalogue + our coverage (built / new / not-built). Read-only;
    refreshed by the scan endpoint or `python -m app.catalogue_scan`."""
    f = UI_DIR.parent / "output" / "catalogue_coverage.json"
    return _json.loads(f.read_text()) if f.exists() else {"total": 0, "built": 0, "products": []}


@app.get("/api/printoka/catalogue/scan")
def catalogue_scan_now():
    """Run a live catalogue check-up (fetch Excard sitemap, diff vs last, recompute coverage)."""
    try:
        from . import catalogue_scan as CS
        return CS.coverage()
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=502)


# ---------- Packaging Box (packmage, own section) ----------
_PKG_CACHE: dict = {}


def _pkg_load(name):
    if name not in _PKG_CACHE:
        f = UI_DIR.parent / "output" / name
        _PKG_CACHE[name] = _json.loads(f.read_text()) if f.exists() else {}
    return _PKG_CACHE[name]


@app.get("/api/printoka/packaging/catalogue")
def packaging_catalogue():
    return _pkg_load("packaging_catalogue_ui.json") or []


@app.get("/api/printoka/packaging/options")
def packaging_options():
    return _pkg_load("packaging_optioncat.json") or {}


@app.get("/api/printoka/packaging/quote")
def packaging_quote(box: str = Query(...), L: float = Query(...), W: float = Query(...),
                    D: float = Query(...), qty: int = Query(...),
                    material: str = Query("M0024"), colour: int = Query(4),
                    coating: str = Query("P021"), addons: str = Query(""),
                    finishing: str = Query(None)):
    from . import packaging_engine as PE
    addon_list = [a for a in (addons or "").split(",") if a]
    try:
        cash = PE.cash_price(box, float(L), float(W), float(D), int(qty), material=material,
                             colour=colour, coating=coating, addons=addon_list, finishing=finishing)
        wt = PE.weight_kg(box, float(L), float(W), float(D), int(qty))
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": f"no price model for box {box}"}, status_code=404)
    return {"config": {"box": box, "L": L, "W": W, "D": D, "qty": qty, "material": material,
                       "colour": colour, "coating": coating, "addons": addon_list},
            "printoka_cash": round(cash, 2), "method": "formula (area-law + stacked option deltas)",
            "note": "Folding-carton box; coating + add-ons stack; print colour does not affect price.",
            "tiers": PE.tiers(cash), "weight_kg": round(wt, 3)}


_PKG_SESSION: dict = {}


def _pkg_session():
    """Lazily bootstrap (Playwright login) one packaging API session, reused across calls.
    The async Playwright bootstrap runs in a dedicated thread+loop (so it works regardless
    of the request's threadpool context); afterwards the requests-based client is reused."""
    if "pk" not in _PKG_SESSION:
        import asyncio, threading
        from . import packaging_api as PA
        box = {}

        def _worker():
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try:
                token, cookies = loop.run_until_complete(PA._bootstrap_async(1))
                box["pk"] = PA.Packaging(token=token, cookies=cookies)
            except Exception as e:  # noqa: BLE001
                box["err"] = repr(e)
            finally:
                loop.close()
        t = threading.Thread(target=_worker, daemon=True); t.start(); t.join(timeout=40)
        if "pk" not in box:
            raise RuntimeError(f"packaging bootstrap failed: {box.get('err','timeout')}")
        _PKG_SESSION["pk"] = box["pk"]
    return _PKG_SESSION["pk"]


@app.get("/api/printoka/packaging/dieline")
def packaging_dieline(box: str = Query(...), L: float = Query(0), W: float = Query(0), D: float = Query(0)):
    """Dieline geometry (LineExp segments + panel dims). If L/W/D given, fetch the EXACT
    dieline for those dimensions live from Excard's LinTest3D; else the stored reference."""
    if L and W and D and not _PKG_SESSION.get("off"):
        try:
            dl = _pkg_session().dieline(box, float(L), float(W), float(D))
            if dl and dl.get("LineExp"):
                return dl
        except Exception:  # noqa: BLE001
            # live LinTest3D unavailable here (e.g. Playwright can't launch inside the dev
            # server on Windows) — disable further live attempts; use nearest pre-captured.
            _PKG_SESSION["off"] = True; _PKG_SESSION.pop("pk", None)
    # offline fallback: nearest pre-captured size (works in preview + standalone)
    if L and W and D:
        variants = _pkg_load("packaging_dielines_multi.json").get(box)
        if variants:
            tgt = (float(L), float(W), float(D))
            best = min(variants, key=lambda v: sum((a - b) ** 2 for a, b in zip(v["dims"], tgt)))
            return {"BoxJson": best["BoxJson"], "LineExp": best["LineExp"]}
    dl = _pkg_load("packaging_dielines.json").get(box)
    if not dl:
        return JSONResponse({"error": f"no dieline for {box}"}, status_code=404)
    return dl


# ---------- Wall Calendar (Litho, id 118) ----------
@app.get("/api/printoka/wallcal/options")
def wallcal_options(product: int = Query(118)):
    return {}


@app.get("/api/printoka/wallcal/quote")
def wallcal_quote(product: int = Query(118), qty: int = Query(...)):
    from . import wallcal_engine as WC
    try:
        cash = WC.cash_price(qty); wt = WC.weight_kg(qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = ("Wall Calendar: fixed 260x265mm, Boxboard backing + Simili 60gsm 12-sheet content; "
            "Folding + Side Stitching compulsory (included). qty = calendars.")
    return {"config": {"product": product, "qty": qty}, "printoka_cash": round(cash, 2),
            "method": "formula (qty curve)", "note": note,
            "tiers": WC.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Arch File (Digital, id 119) ----------
@app.get("/api/printoka/archfile/options")
def archfile_options(product: int = Query(119)):
    return {}


@app.get("/api/printoka/archfile/quote")
def archfile_quote(product: int = Query(119), qty: int = Query(...)):
    from . import archfile_engine as AF
    try:
        cash = AF.cash_price(qty); wt = AF.weight_kg(qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = ("Arch File: fixed spec — Steel Binding (4 ring & Metal Clip) + Wire-O + Oval curve "
            "+ 2 L-shape corners + Lamination (Front), all compulsory (included). qty = files.")
    return {"config": {"product": product, "qty": qty}, "printoka_cash": round(cash, 2),
            "method": "formula (qty curve)", "note": note,
            "tiers": AF.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Desk Calendar Hard Stand (Litho, id 120) ----------
_DESKCAL_CAT_MAP = {
    "WDCH 001 (Portrait)": "1", "Portrait": "1",
    "WDCH 002 (Landscape)": "2", "Landscape": "2",
    "DCHS 001 (Hot Stamping - Portrait)": "3", "Hot Stamping": "3",
}


@app.get("/api/printoka/deskcal/options")
def deskcal_options(product: int = Query(120)):
    from . import deskcal_engine as DC
    return {"cat": list(DC.HARD_CATS.values())}


@app.get("/api/printoka/deskcal/quote")
def deskcal_quote(product: int = Query(120), cat: str = Query("WDCH 001 (Portrait)"), qty: int = Query(...)):
    from . import deskcal_engine as DC
    cat_val = _DESKCAL_CAT_MAP.get(cat, "1")
    try:
        cash = DC.cash_price("hard", qty, cat_val); wt = DC.weight_kg("hard", qty)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = (f"Desk Calendar Hard Stand: model={cat}, qty={qty}. "
            "Hot Stamping - Portrait model: Hot Stamping compulsory (included).")
    return {"config": {"product": product, "cat": cat, "qty": qty}, "printoka_cash": round(cash, 2),
            "method": "formula (qty curve per model)", "note": note,
            "tiers": DC.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Desk Calendar Soft Stand (Litho, id 121) ----------
@app.get("/api/printoka/deskcal_soft/options")
def deskcal_soft_options(product: int = Query(121)):
    return {}


@app.get("/api/printoka/deskcal_soft/quote")
def deskcal_soft_quote(product: int = Query(121), qty: int = Query(...)):
    from . import deskcal_engine as DC
    try:
        cash = DC.cash_price("soft", qty); wt = DC.weight_kg("soft", qty)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = ("Desk Calendar Soft Stand: Wire-O binding + cardboard cover, fixed spec. "
            "Hole Punching + Wire-O Binding (Black) + Creasing compulsory (included). qty = calendars.")
    return {"config": {"product": product, "qty": qty}, "printoka_cash": round(cash, 2),
            "method": "formula (qty curve)", "note": note,
            "tiers": DC.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Wire-O Wall Calendar (Litho, id 122) ----------
@app.get("/api/printoka/wireow/options")
def wireow_options(product: int = Query(122)):
    return {}


@app.get("/api/printoka/wireow/quote")
def wireow_quote(product: int = Query(122), qty: int = Query(...)):
    from . import wireow_engine as WOW
    try:
        cash = WOW.cash_price(qty); wt = WOW.weight_kg(qty)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = ("Wire-O Wall Calendar: fixed spec, Wire-O binding + hanger. "
            "Hole Punching + Wire-O Binding (White) + Hanger compulsory (included). qty = calendars.")
    return {"config": {"product": product, "qty": qty}, "printoka_cash": round(cash, 2),
            "method": "formula (qty curve)", "note": note,
            "tiers": WOW.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Banner (Litho, id 123) ----------
_BANNER_SIZES = ["3ft x 2ft", "4ft x 2ft", "6ft x 2ft", "4ft x 3ft", "8ft x 3ft",
                 "10ft x 3ft", "18ft x 3ft", "8ft x 4ft", "10ft x 4ft", "20ft x 4ft"]


@app.get("/api/printoka/banner/options")
def banner_options(product: int = Query(123)):
    return {"sizes": _BANNER_SIZES}


@app.get("/api/printoka/banner/quote")
def banner_quote(product: int = Query(123), size: str = Query("3ft x 2ft"), qty: int = Query(...)):
    from . import banner_engine as BN
    try:
        cash = BN.cash_price(size, qty); wt = BN.weight_kg(size, qty)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = "Banner (solvent-print vinyl on tarpaulin). Fixed material 400gsm. qty = pieces."
    return {"config": {"product": product, "size": size, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "formula (per-size qty curve)",
            "note": note, "tiers": BN.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Bunting (Litho, id 124) ----------
@app.get("/api/printoka/bunting/options")
def bunting_options(product: int = Query(124)):
    return {}


@app.get("/api/printoka/bunting/quote")
def bunting_quote(product: int = Query(124), size: str = Query("2ft x 5ft"),
                  paper: str = Query("Tarpaulin 300gsm"), protective: str = Query("Wood"),
                  qty: int = Query(...)):
    from . import simpleqty_engine as SQ
    p = _simpleqty_params("bunting")
    variant = f"{size}|{paper}|{protective}"
    if variant not in p.get("curves", {}):
        return JSONResponse({"error": f"{paper} ({size}, {protective}) is not yet priced — contact us for a quote"}, status_code=400)
    try:
        cash = SQ.cash_price(p, variant, qty); wt = SQ.weight_kg(p, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    return {"config": {"product": product, "size": size, "paper": paper, "protective": protective, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "formula (per size×fitting qty curve)",
            "note": p.get("note", ""), "tiers": SQ.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Roll-Up Stand (Litho, id 125) ----------
@app.get("/api/printoka/rollup/options")
def rollup_options(product: int = Query(125)):
    from . import rollup_engine as RU
    return {"lams": RU.LAMS}


@app.get("/api/printoka/rollup/quote")
def rollup_quote(product: int = Query(125), lam: str = Query("Matte Lamination"), qty: int = Query(...)):
    from . import rollup_engine as RU
    try:
        cash = RU.cash_price(lam, qty); wt = RU.weight_kg(qty)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = f"Roll-Up Stand: 0.85m × 2.00m panel, {lam}. qty = stands."
    return {"config": {"product": product, "lam": lam, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "formula (per-lam qty curve)",
            "note": note, "tiers": RU.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Wobbler (Digital, id 126) ----------
@app.get("/api/printoka/wobbler/options")
def wobbler_options(product: int = Query(126)):
    from . import wobbler_engine as WB
    return {"orients": WB.ORIENTS, "papers": WB.PAPERS, "lams": WB.LAMS, "finishings": WB.FINISHINGS}


@app.get("/api/printoka/wobbler/quote")
def wobbler_quote(product: int = Query(126), orient: str = Query("Portrait"),
                  paper: str = Query("Gloss Art Card 250gsm"),
                  lam: str = Query("Matte Lamination (Front)"),
                  finishing: str = Query("-"), qty: int = Query(...)):
    from . import wobbler_engine as WB
    try:
        cash = WB.cash_price(orient, paper, lam, qty, finishing); wt = WB.weight_kg(paper, qty)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = f"Wobbler: {orient}, {paper}, {lam}. qty = pieces."
    return {"config": {"product": product, "orient": orient, "paper": paper, "lam": lam, "finishing": finishing, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "formula (per-combo qty curve + finishing delta)",
            "note": note, "tiers": WB.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Paper Bag (Litho, id 127) ----------
@app.get("/api/printoka/paperbag/options")
def paperbag_options(product: int = Query(127)):
    from . import paperbag_engine as PB
    return {"papers": PB.PAPERS}


@app.get("/api/printoka/paperbag/quote")
def paperbag_quote(product: int = Query(127), paper: str = Query("Gloss Art Paper 157gsm"),
                   lamination: str = Query("Gloss Lamination (Front)"),
                   rope_colour: str = Query("Black"), qty: int = Query(...)):
    from . import paperbag_engine as PB
    try:
        cash = PB.cash_price(paper, qty); wt = PB.weight_kg(paper, qty)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = f"Paper Bag: {paper}. Folding + Gluing + Hole Punching compulsory. Lamination and rope colour do not change the online price. qty = bags."
    return {"config": {"product": product, "paper": paper, "lamination": lamination, "rope_colour": rope_colour, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "formula (per-paper qty curve)",
            "note": note, "tiers": PB.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Canvas Tote Bag (Litho, id 128) ----------
@app.get("/api/printoka/canvastote/options")
def canvastote_options(product: int = Query(128)):
    from . import canvastote_engine as CT
    return {"colours": CT.COLOURS}


@app.get("/api/printoka/canvastote/quote")
def canvastote_quote(product: int = Query(128), colour: str = Query("1C (Front)"), qty: int = Query(...)):
    from . import canvastote_engine as CT
    try:
        cash = CT.cash_price(colour, qty); wt = CT.weight_kg(qty)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = f"Canvas Tote Bag: {colour}. qty = bags."
    return {"config": {"product": product, "colour": colour, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "formula (per-colour qty curve)",
            "note": note, "tiers": CT.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Mug (Litho, id 129) ----------
@app.get("/api/printoka/mug/options")
def mug_options(product: int = Query(129)):
    return {}


@app.get("/api/printoka/mug/quote")
def mug_quote(product: int = Query(129), qty: int = Query(...)):
    from . import mug_engine as MG
    try:
        cash = MG.cash_price(qty); wt = MG.weight_kg(qty)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = "Mug: standard ceramic sublimation. qty = mugs."
    return {"config": {"product": product, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "formula (qty curve)",
            "note": note, "tiers": MG.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Papan Kopi / Sachet Board (Litho, id 130) — exact v4 price-list lookup ----------
@app.get("/api/printoka/papan_kopi/options")
def papan_kopi_options(product: int = Query(130)):
    return {}


@app.get("/api/printoka/papan_kopi/quote")
def papan_kopi_quote(product: int = Query(130), qty: int = Query(...),
                     model: str = Query("SB 01")):
    from . import pricelist_engine as PE
    p = _pl_params("papan_kopi")
    cfg = {"Model": model}
    try:
        cash = PE.cash_price(p, cfg, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = ("Papan Kopi / Sachet Board (exact v4 price-list lookup). 4 models with fixed specs. "
            "Compulsory: Boxboard Grey Back 400gsm, Gloss Water Based Varnish (Front), 4C Front, Die-Cutting. qty = boards.")
    wt = round(p.get("unit_wt", 0.08) * qty, 3)
    return {"config": {"product": product, "model": model, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "exact (v4 price-list lookup)", "note": note,
            "tiers": PE.tiers(cash), "weight_kg": wt}


# ---------- Pillow (Litho, id 131) ----------
@app.get("/api/printoka/pillow/options")
def pillow_options(product: int = Query(131)):
    return {}


@app.get("/api/printoka/pillow/quote")
def pillow_quote(product: int = Query(131), qty: int = Query(...)):
    from . import pillow_engine as PL
    try:
        cash = PL.cash_price(qty); wt = PL.weight_kg(qty)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = "Pillow: standard 40cm × 40cm sublimation with filling. qty = pillows."
    return {"config": {"product": product, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "formula (qty curve)",
            "note": note, "tiers": PL.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Button Badge (Digital, id 132) — generic simpleqty engine ----------
import functools as _functools


@_functools.lru_cache(maxsize=None)
def _simpleqty_params(tag: str):
    import json as _json
    from pathlib import Path as _Path
    f = _Path(__file__).resolve().parent.parent / "output" / f"{tag}_params.json"
    return _json.loads(f.read_text()) if f.exists() else {"curves": {}, "variant_field": ""}


@_functools.lru_cache(maxsize=None)
def _pl_params(tag: str):
    """Load a generic price-list lookup params file (<tag>_pl_params.json)."""
    import json as _json
    from pathlib import Path as _Path
    f = _Path(__file__).resolve().parent.parent / "output" / f"{tag}_pl_params.json"
    return _json.loads(f.read_text()) if f.exists() else {"axis_cols": [], "curves": {}}


@app.get("/api/printoka/buttonbadge/options")
def buttonbadge_options(product: int = Query(132)):
    return {}


@app.get("/api/printoka/buttonbadge/quote")
def buttonbadge_quote(product: int = Query(132), qty: int = Query(...),
                      lamination: str = Query("Gloss")):
    from . import simpleqty_engine as SQ
    p = _simpleqty_params("buttonbadge")
    try:
        cash = SQ.cash_price(p, "-", qty); wt = SQ.weight_kg(p, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    return {"config": {"product": product, "qty": qty, "lamination": lamination},
            "printoka_cash": round(cash, 2), "method": "formula (qty curve)",
            "note": p.get("note", ""), "tiers": SQ.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Hand Fan (Digital, id 133) — generic simpleqty engine ----------
@app.get("/api/printoka/handfan/options")
def handfan_options(product: int = Query(133)):
    return {}


@app.get("/api/printoka/handfan/quote")
def handfan_quote(product: int = Query(133), qty: int = Query(...),
                  paper: str = Query("Gloss Art Card 310gsm"),
                  lamination: str = Query("Matte Lamination (Both)")):
    from . import simpleqty_engine as SQ
    p = _simpleqty_params("handfan")
    try:
        cash = SQ.cash_price(p, paper, qty); wt = SQ.weight_kg(p, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    return {"config": {"product": product, "qty": qty, "paper": paper, "lamination": lamination},
            "printoka_cash": round(cash, 2), "method": "formula (per-paper qty curve)",
            "note": p.get("note", ""), "tiers": SQ.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Hanger (Digital, id 134) — generic simpleqty engine, paper x colour ----------
@app.get("/api/printoka/hanger/options")
def hanger_options(product: int = Query(134)):
    return {}


@app.get("/api/printoka/hanger/quote")
def hanger_quote(product: int = Query(134), qty: int = Query(...),
                 paper: str = Query("Gloss Art Card 310gsm (2 sides coated)"),
                 colour: str = Query("4C (Front)"),
                 lamination: str = Query("Matte Lamination (Both)")):
    from . import simpleqty_engine as SQ
    p = _simpleqty_params("hanger")
    try:
        cash = SQ.cash_price(p, f"{paper}|{colour}", qty); wt = SQ.weight_kg(p, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    return {"config": {"product": product, "qty": qty, "paper": paper, "colour": colour, "lamination": lamination},
            "printoka_cash": round(cash, 2), "method": "formula (per-paper×colour qty curve)",
            "note": p.get("note", ""), "tiers": SQ.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Magnet (Digital, id 135) — generic simpleqty engine, per shape ----------
@app.get("/api/printoka/magnet/options")
def magnet_options(product: int = Query(135)):
    return {}


@app.get("/api/printoka/magnet/quote")
def magnet_quote(product: int = Query(135), qty: int = Query(...),
                 shape: str = Query("Rectangle/Square"),
                 finishing: str = Query("Matte Laminate (Front)")):
    from . import simpleqty_engine as SQ
    p = _simpleqty_params("magnet")
    # "Custom Die-Cut (with round corner)" is Excard's exact name for what we sampled as "Custom Die-Cut"
    _SHAPE_ALIAS = {"Custom Die-Cut (with round corner)": "Custom Die-Cut"}
    shape_key = _SHAPE_ALIAS.get(shape, shape)
    if shape == "Multiple Dieline":
        return JSONResponse({"error": "Multiple Dieline magnets are not yet priced — contact us for a quote"}, status_code=400)
    try:
        cash = SQ.cash_price(p, shape_key, qty); wt = SQ.weight_kg(p, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    return {"config": {"product": product, "qty": qty, "shape": shape, "finishing": finishing},
            "printoka_cash": round(cash, 2), "method": "formula (per-shape qty curve)",
            "note": p.get("note", ""), "tiers": SQ.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Hard Cover Menu (Digital, id 136) — generic simpleqty engine ----------
@app.get("/api/printoka/hardmenu/options")
def hardmenu_options(product: int = Query(136)):
    return {}


@app.get("/api/printoka/hardmenu/quote")
def hardmenu_quote(product: int = Query(136), qty: int = Query(...),
                   order: str = Query("Cover + Content"), addcontent: str = Query("12"),
                   lamination: str = Query("Gloss Lamination (Both)")):
    from . import simpleqty_engine as SQ
    p = _simpleqty_params("hardmenu")
    ac = "-" if order == "Cover only" else addcontent
    try:
        cash = SQ.cash_price(p, f"{order}|{ac}", qty); wt = SQ.weight_kg(p, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    return {"config": {"product": product, "qty": qty, "order": order, "addcontent": ac, "lamination": lamination},
            "printoka_cash": round(cash, 2), "method": "formula (per-config qty curve)",
            "note": p.get("note", ""), "tiers": SQ.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Standing Pouch (Litho, id 137) — generic simpleqty engine ----------
@app.get("/api/printoka/pouch/options")
def pouch_options(product: int = Query(137)):
    return {}


@app.get("/api/printoka/pouch/quote")
def pouch_quote(product: int = Query(137), qty: int = Query(...),
                paper: str = Query("Metalised Pet Film"),
                lamination: str = Query("Matte Lamination")):
    from . import simpleqty_engine as SQ
    p = _simpleqty_params("pouch")
    if paper not in p.get("curves", {}):
        return JSONResponse({"error": f"{paper} is not yet priced — contact us for a quote"}, status_code=400)
    try:
        cash = SQ.cash_price(p, paper, qty); wt = SQ.weight_kg(p, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    return {"config": {"product": product, "qty": qty, "paper": paper, "lamination": lamination},
            "printoka_cash": round(cash, 2), "method": "formula (qty curve)",
            "note": p.get("note", ""), "tiers": SQ.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Money Packet (Litho, id 138) — exact v4 price-list lookup ----------
@app.get("/api/printoka/money_packet/options")
def money_packet_options(product: int = Query(138)):
    return {}  # all fields are inline addon fields in the schema


@app.get("/api/printoka/money_packet/quote")
def money_packet_quote(product: int = Query(138), qty: int = Query(...),
                       model: str = Query("MP 101"),
                       package: str = Query("Normal"),
                       paper: str = Query("Gloss Art Paper 130gsm"),
                       finishing: str = Query("N/A"),
                       packing: str = Query("10pcs / Pack")):
    from . import pricelist_engine as PE
    p = _pl_params("money_packet")
    cfg = {"Model": model, "Package": package, "Paper": paper, "Finishing": finishing}
    try:
        cash = PE.cash_price(p, cfg, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    wt = round(p.get("unit_wt", 0.006) * qty, 3)
    note = ("Money Packet Standard (exact v4 price-list lookup). 3 models (MP 101/103/104), "
            "4 package types (Normal/Dual/5/6 Design), 3 papers, 2 finishings. "
            "Packing Method (5/6/8/10 pcs per pack) is price-neutral. qty = pcs.")
    return {"config": {"product": product, "model": model, "package": package,
                       "paper": paper, "finishing": finishing, "packing": packing, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "exact (v4 price-list lookup)", "note": note,
            "tiers": PE.tiers(cash), "weight_kg": wt}


# ---------- Non-Woven Bag (Litho, id 139) — exact v4 price-list lookup ----------
@app.get("/api/printoka/non_woven_bag/options")
def non_woven_bag_options(product: int = Query(139)):
    return {}  # all fields are inline addon fields in the schema


@app.get("/api/printoka/non_woven_bag/quote")
def non_woven_bag_quote(product: int = Query(139), qty: int = Query(...),
                        model: str = Query("WN-B5"),
                        print_colour: str = Query("1C (Front)"),
                        bag_colour: str = Query("Black"),
                        handle_length: str = Query("300mm"),
                        handle_colour: str = Query("Same as bag colour")):
    from . import pricelist_engine as PE
    p = _pl_params("non_woven_bag")
    cfg = {"Model": model, "Print Colour": print_colour}
    try:
        cash = PE.cash_price(p, cfg, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price for this model/print colour combination"}, status_code=400)
    note = ("Non-Woven Bag (exact v4 price-list lookup). Model determines size. "
            "Bag Colour, Handle Length, Handle Colour are price-neutral. qty = pcs.")
    wt = round(p.get("unit_wt", 0.035) * qty, 3)
    return {"config": {"product": product, "model": model, "print_colour": print_colour,
                       "bag_colour": bag_colour, "handle_length": handle_length,
                       "handle_colour": handle_colour, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "exact (v4 price-list lookup)", "note": note,
            "tiers": PE.tiers(cash), "weight_kg": wt}


# ---------- Tent Card (Litho, id 140) — exact v4 price-list lookup ----------
@app.get("/api/printoka/tent_card/options")
def tent_card_options(product: int = Query(140)):
    return {}


@app.get("/api/printoka/tent_card/quote")
def tent_card_quote(product: int = Query(140), qty: int = Query(...),
                    model: str = Query("TC 003"),
                    lamination: str = Query("Matte Lamination (Both)")):
    from . import pricelist_engine as PE
    p = _pl_params("tent_card")
    cfg = {"Model": model, "Lamination": lamination}
    try:
        cash = PE.cash_price(p, cfg, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price for this configuration"}, status_code=400)
    note = ("Tent Card (exact v4 price-list lookup). 2 models (TC 003=294x86mm, TC 004=294x140mm). "
            "Paper (Art Card 310gsm), Print Colour (4C Front), and Die-Cutting are compulsory (included). qty = pcs.")
    wt = round(p.get("unit_wt", 0.02) * qty, 3)
    return {"config": {"product": product, "model": model, "lamination": lamination, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "exact (v4 price-list lookup)", "note": note,
            "tiers": PE.tiers(cash), "weight_kg": wt}


# ---------- Stamp Chop (id 141) — exact v4 unit price lookup ----------
@app.get("/api/printoka/stamp_chop/options")
def stamp_chop_options(product: int = Query(141)):
    f = Path(__file__).resolve().parent.parent / "output" / "stamp_chop_prices.json"
    prices = _json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    return {
        "stamp_types": sorted(prices.keys()),
        "categories": {st: sorted(cats.keys()) for st, cats in prices.items()},
        "model_keys": {st: {cat: sorted(models.keys()) for cat, models in cats.items()}
                      for st, cats in prices.items()},
    }


@app.get("/api/printoka/stamp_chop/quote")
def stamp_chop_quote(product: int = Query(141), qty: int = Query(...),
                     stamp_type: str = Query("Pre-Inked Stamp"),
                     category: str = Query("Rectangle"),
                     model_key: str = Query(...)):
    f = Path(__file__).resolve().parent.parent / "output" / "stamp_chop_prices.json"
    if not f.exists():
        return JSONResponse({"error": "stamp_chop_prices.json not found"}, status_code=500)
    prices = _json.loads(f.read_text(encoding="utf-8"))
    unit_price = (prices.get(stamp_type, {}).get(category, {}).get(model_key))
    if unit_price is None:
        return JSONResponse({"error": f"no price for {stamp_type}/{category}/{model_key}"}, status_code=400)
    cash = unit_price * qty
    note = f"Stamp: {stamp_type} / {category} / {model_key}. Unit price × qty."
    from . import pricelist_engine as PE
    return {"config": {"product": product, "stamp_type": stamp_type, "category": category,
                       "model_key": model_key, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "exact (v4 price-list lookup)", "note": note,
            "tiers": PE.tiers(cash), "weight_kg": round(0.05 * qty, 3)}


# ---------- Mask Keeper (id 142) — quote only, v4 price-list returns 500 ----------
@app.get("/api/printoka/mask_keeper/options")
def mask_keeper_options(product: int = Query(142)):
    return {}


@app.get("/api/printoka/mask_keeper/quote")
def mask_keeper_quote(product: int = Query(142), qty: int = Query(...)):
    return JSONResponse({"error": "Mask Keeper pricing is not available online. Please contact Excard directly for a quote.", "quote_only": True}, status_code=400)


# ---------- Sublimation Shirt (id 143) — quote only, v4 price-list returns 500 ----------
@app.get("/api/printoka/sublimation_shirt/options")
def sublimation_shirt_options(product: int = Query(143)):
    return {}


@app.get("/api/printoka/sublimation_shirt/quote")
def sublimation_shirt_quote(product: int = Query(143), qty: int = Query(...)):
    return JSONResponse({"error": "Sublimation Shirt pricing is not available online. Please contact Excard directly for a quote.", "quote_only": True}, status_code=400)


# ---------- Static Cling Window Sticker / Car Sticker (Digital, id 116/117) ----------
@app.get("/api/printoka/staticcling/options")
def staticcling_options(product: int = Query(116)):
    return {}


@app.get("/api/printoka/staticcling/quote")
def staticcling_quote(product: int = Query(116), size: str = Query("100mm x 100mm"),
                      direction: str = Query("Face Out View"), qty: int = Query(...),
                      vdp: str = Query("Not Required")):
    from . import staticcling_engine as SC
    try:
        cash = SC.cash_price(size, direction, qty, vdp=vdp)
        wt = SC.weight_kg(size, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    nm = "Car Sticker" if product == 117 else "Static Cling Window Sticker"
    note = f"{nm} (static-cling vinyl). Face In = Face Out price; Both Side View prints both sides. qty = pieces."
    return {"config": {"product": product, "size": size, "direction": direction, "qty": qty, "vdp": vdp},
            "printoka_cash": round(cash, 2), "method": "formula (reference curve x factors)",
            "note": note, "tiers": SC.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Kad Terima Kasih (Digital, id 115) ----------
@app.get("/api/printoka/kadterima/options")
def kadterima_options(product: int = Query(115)):
    return {}


@app.get("/api/printoka/kadterima/quote")
def kadterima_quote(product: int = Query(115), size: str = Query("52mm x 52mm"),
                    paper: str = Query("Gloss Art Card 260gsm (2 sides coated)"),
                    colour: str = Query("4C (Front)"), qty: int = Query(...),
                    hole_punch: str = Query("No"), lamination: str = Query("Matte Lamination (Front)")):
    from . import kadterima_engine as KT
    hp = hole_punch == "Yes"
    try:
        cash = KT.cash_price(size, paper, colour, qty, hole_punch=hp)
        wt = KT.weight_kg(size, paper, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = "Kad Terima Kasih (thank-you gift tag). Lamination does not change the online price. qty = tags."
    return {"config": {"product": product, "size": size, "paper": paper, "colour": colour,
                       "qty": qty, "hole_punch": hole_punch, "lamination": lamination},
            "printoka_cash": round(cash, 2), "method": "formula (reference curve x factors)",
            "note": note, "tiers": KT.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Kad Kahwin (Digital, id 114) ----------
_KK_OT = {"Standard Kad Kahwin": "1,Standard Kad Kahwin", "Custom Die-cut Kad Kahwin": "2,Custom Die-cut Kad Kahwin"}


@app.get("/api/printoka/kadkahwin/options")
def kadkahwin_options(product: int = Query(114)):
    return {}


@app.get("/api/printoka/kadkahwin/quote")
def kadkahwin_quote(product: int = Query(114), ordertype: str = Query("Standard Kad Kahwin"),
                    size: str = Query("A5 (148mm x 210mm)"),
                    paper: str = Query("Gloss Art Card 260gsm (2 sides coated)"),
                    colour: str = Query("4C (Front)"), qty: int = Query(...),
                    hot_stamping: str = Query("Not Required"),
                    lamination: str = Query("Matte Lamination (Front)"),
                    envelope: str = Query("Not Required")):
    from . import kadkahwin_engine as KK
    ot = _KK_OT.get(ordertype, ordertype)
    try:
        cash = KK.cash_price(ot, size, paper, colour, qty)
        wt = KK.weight_kg(size, paper, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = ("Kad Kahwin (wedding card). Lamination & envelope colour do not change the online "
            "price; folding code & hot stamping are quoted separately. qty = cards.")
    if hot_stamping not in ("Not Required", ""):
        note += f" Hot stamping ({hot_stamping}) quoted separately."
    return {"config": {"product": product, "ordertype": ordertype, "size": size, "paper": paper,
                       "colour": colour, "qty": qty, "hot_stamping": hot_stamping,
                       "lamination": lamination, "envelope": envelope},
            "printoka_cash": round(cash, 2), "method": "formula (reference curve x factors)",
            "note": note, "tiers": KK.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- PVC Card (Digital, id 113) ----------
@app.get("/api/printoka/pvccard/options")
def pvccard_options(product: int = Query(113)):
    return {}


@app.get("/api/printoka/pvccard/quote")
def pvccard_quote(product: int = Query(113), colour: str = Query("4C (Front)"),
                  qty: int = Query(...), hole_punch: str = Query("Not Required"),
                  vdp: str = Query("Not Required")):
    from . import pricelist_engine as PE
    p = _pl_params("pvccard")
    cfg = {"Print Colour": colour, "Hole Punch": hole_punch, "VDP": vdp}
    try:
        cash = PE.cash_price(p, cfg, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = ("PVC Card (CR80, 0.80mm Gloss, Round Cornering compulsory). Exact v4 price-list "
            "lookup. Orientation/size price-neutral. Print colour (4C Front/Both), Hole Punching "
            "and Variable Data Printing are each PRICED. qty = cards.")
    wt = round(0.0056 * qty, 3)  # CR80 PVC card ~5.6g each
    return {"config": {"product": product, "colour": colour, "qty": qty,
                       "hole_punch": hole_punch, "vdp": vdp},
            "printoka_cash": round(cash, 2), "method": "exact (v4 price-list lookup)", "note": note,
            "tiers": PE.tiers(cash), "weight_kg": wt}


# ---------- Wire-O Notebook (Litho, id 112) ----------
@app.get("/api/printoka/wireo/options")
def wireo_options(product: int = Query(112)):
    return {}


@app.get("/api/printoka/wireo/quote")
def wireo_quote(product: int = Query(112), cover: str = Query("Hard Cover"),
                lamination: str = Query("Matte Lamination (Front)"),
                addcontent: str = Query("Not Required"), qty: int = Query(...),
                hot_stamping: str = Query("Not Required")):
    from . import wireo_engine as WO
    try:
        cash = WO.cash_price(cover, lamination, addcontent, qty)
        wt = WO.weight_kg(cover, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = ("Wire-O Notebook: Wire-O hole punch + binding compulsory (included). Gloss=Matte "
            "lamination (same price); Spot UV adds a delta. Hot stamping is quoted separately. "
            "Soft Cover is priced at its standard lamination (Matte Both); Exclusive Leather "
            "Cover is still pending. qty = books.")
    if hot_stamping not in ("Not Required", ""):
        note += f" Hot stamping ({hot_stamping}) quoted separately."
    return {"config": {"product": product, "cover": cover, "lamination": lamination,
                       "addcontent": addcontent, "qty": qty, "hot_stamping": hot_stamping},
            "printoka_cash": round(cash, 2), "method": "formula (per-cover curve + deltas)",
            "note": note, "tiers": WO.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Computer Form (Litho NCR, id 111) ----------
@app.get("/api/printoka/computerform/options")
def computerform_options(product: int = Query(111)):
    return {}


@app.get("/api/printoka/computerform/quote")
def computerform_quote(product: int = Query(111), package: str = Query("Multi Layer Computer Form"),
                       layers: str = Query("2"), ups: str = Query("1"), colour: str = Query("1C"),
                       qty: int = Query(...), copychange: str = Query("No"), numbering: str = Query("No")):
    from . import computerform_engine as CF
    try:
        cash = CF.cash_price(package, int(layers), ups, colour, qty,
                             copychange=(copychange == "Yes"), numbering=(numbering == "Yes"))
        wt = CF.weight_kg(int(layers), ups, qty, package=package)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = ("Computer Form (NCR), fixed 9.5\"x11\". qty = sets/forms. Per-ply tints are "
            "price-neutral; copy change has no online price effect; numbering is quoted "
            "separately. Layers apply to Multi Layer only.")
    return {"config": {"product": product, "package": package, "layers": layers, "ups": ups,
                       "colour": colour, "qty": qty, "copychange": copychange, "numbering": numbering},
            "printoka_cash": round(cash, 2), "method": "formula (reference curve x factors)",
            "note": note, "tiers": CF.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Voucher (Litho, id 110) ----------
@app.get("/api/printoka/voucher/options")
def voucher_options(product: int = Query(110)):
    return {}


@app.get("/api/printoka/voucher/quote")
def voucher_quote(product: int = Query(110), packform: str = Query("Book"),
                  size: str = Query("145mm x 210mm"), paper: str = Query("Art Paper 100gsm"),
                  colour: str = Query("4C (Front)"), sets: str = Query("50"), qty: int = Query(...),
                  perforation: str = Query("0"), numbering: str = Query("No")):
    from . import voucher_engine as VC
    try:
        cash = VC.cash_price(packform, size, paper, colour, sets, qty,
                             perforation=perforation, numbering=(numbering == "Yes"))
        wt = VC.weight_kg(size, paper, sets, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = ("Voucher (Litho). qty = books/pads (x sets per book). Perforation lines have no "
            "online price effect; numbering adds a per-run cost. Decomposed factor model: "
            "single-option axes are exact, combinations are approximated.")
    return {"config": {"product": product, "packform": packform, "size": size, "paper": paper,
                       "colour": colour, "sets": sets, "qty": qty, "perforation": perforation,
                       "numbering": numbering},
            "printoka_cash": round(cash, 2), "method": "formula (reference curve x factors)",
            "note": note, "tiers": VC.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Bookmark (Digital, id 109) ----------
@app.get("/api/printoka/bookmark/options")
def bookmark_options(product: int = Query(109)):
    return {}


@app.get("/api/printoka/bookmark/quote")
def bookmark_quote(product: int = Query(109), paper: str = Query("Gloss Art Card 250gsm (2 sides coated)"),
                   colour: str = Query("4C (Front)"), qty: int = Query(...),
                   round_corner: str = Query("Not Required"), hole_punch: str = Query("Not Required"),
                   lamination: str = Query("Not Required")):
    from . import bookmark_engine as BM
    rc = round_corner not in ("Not Required", "No"); hp = hole_punch not in ("Not Required", "No")
    try:
        cash = BM.cash_price(paper, colour, qty, round_corner=rc, hole_punch=hp)
        fin = BM.finishing_cost(qty, round_corner=rc, hole_punch=hp)
        wt = BM.weight_kg(paper, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    return {"config": {"product": product, "paper": paper, "colour": colour, "qty": qty,
                       "round_corner": round_corner, "hole_punch": hole_punch},
            "printoka_cash": round(cash, 2), "finishing_cost": round(fin, 2),
            "method": "formula (per-config log-log curve)",
            "note": "Bookmark (Digital). Lamination does not change the online price; round cornering / hole punching are optional add-ons. qty = pieces.",
            "tiers": BM.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- L-Shape Plastic Folder (Digital, id 108) ----------
@app.get("/api/printoka/lshape/options")
def lshape_options(product: int = Query(108)):
    return {}


@app.get("/api/printoka/lshape/quote")
def lshape_quote(product: int = Query(108), paper: str = Query("Synthetic Paper 180micron"),
                 qty: int = Query(...)):
    from . import lshape_engine as LS
    try:
        cash = LS.cash_price(paper, qty); wt = LS.weight_kg(paper, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = ("L-Shape Plastic Folder: fixed model LSF 001, 310x442mm, 4C. Compulsory die-cut "
            "+ fold included. qty = pieces.")
    return {"config": {"product": product, "paper": paper, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "formula (per-paper qty curve)", "note": note,
            "tiers": LS.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Folder (Litho Presentation Folder, id 107) ----------
@app.get("/api/printoka/folder/options")
def folder_options(product: int = Query(107)):
    return {}  # inline addon fields


@app.get("/api/printoka/folder/quote")
def folder_quote(product: int = Query(107), model: str = Query("FPF 001"),
                 paper: str = Query("Gloss Art Card 250gsm (1 side coated)"),
                 colour: str = Query("4C (Front)"), qty: int = Query(...),
                 lamination: str = Query("Gloss Lamination (Front)"),
                 protective: str = Query("N/A")):
    from . import pricelist_engine as PE
    p = _pl_params("folder")
    cfg = {"Model": model, "Paper": paper, "Print Colour": colour,
           "Lamination": lamination, "Colour Protective Layer": protective}
    try:
        cash = PE.cash_price(p, cfg, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = ("Folder (exact v4 price-list lookup). Covers all mould groups "
            "(Presentation/Document/Key/CD Jacket), print colour, all laminations incl Spot UV, "
            "and the back colour-protective layer. Die-cutting + creasing compulsory. qty = pieces.")
    wt = round(0.040 * qty, 3)  # ~40g per presentation folder
    return {"config": {"product": product, "model": model, "paper": paper, "colour": colour,
                       "lamination": lamination, "protective": protective, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "exact (v4 price-list lookup)",
            "note": note, "tiers": PE.tiers(cash), "weight_kg": wt}


# ---------- Envelope (Litho, id 106) ----------
@app.get("/api/printoka/envelope/options")
def envelope_options(product: int = Query(106)):
    return {}  # inline addon fields


@app.get("/api/printoka/envelope/quote")
def envelope_quote(product: int = Query(106), model: str = Query("EV4496NW — 114x248mm"),
                   colour: str = Query("4C (Front)"), qty: int = Query(...)):
    from . import envelope_engine as EV
    try:
        cash = EV.cash_price(model, colour, qty)
        wt = EV.weight_kg(model, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = ("Envelope: Die-Cutting, Folding + Gluing compulsory (included). Print colour is "
            "an additive plate cost vs 4C(Front). The 3 OE 'Best Seller' moulds map to the "
            "same-size EV mould (their paper differs slightly). qty = pieces.")
    return {"config": {"product": product, "model": model, "colour": colour, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "formula (per-model curve + colour plate delta)",
            "note": note, "tiers": EV.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Letterhead (Litho, id 105) ----------
@app.get("/api/printoka/letterhead/options")
def letterhead_options(product: int = Query(105)):
    return {}  # all letterhead fields are inline addon fields in the schema


@app.get("/api/printoka/letterhead/quote")
def letterhead_quote(product: int = Query(105), paper: str = Query("Simili 80gsm"),
                     colour: str = Query("4C (Front)"), qty: int = Query(...),
                     packing: str = Query("Loose")):
    from . import pricelist_engine as PE
    p = _pl_params("letterhead")
    cfg = {"Paper": paper, "Print Colour": colour, "Packing": packing}
    try:
        cash = PE.cash_price(p, cfg, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = ("Letterhead (exact v4 price-list lookup). Fixed A4 (210x297mm). Axes: Paper x "
            "Print Colour x Packing (Loose / Pad 100pcs). Exact at listed order quantities; "
            "other quantities interpolate. qty = sheets.")
    gsm = 100 if "100" in paper else 80
    wt = round(0.210 * 0.297 * gsm / 1000 * qty, 3)  # A4 physical weight per sheet
    return {"config": {"product": product, "paper": paper, "colour": colour,
                       "packing": packing, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "exact (v4 price-list lookup)", "note": note,
            "tiers": PE.tiers(cash), "weight_kg": wt}


# ---------- Notepad (Litho, id 104) ----------
@app.get("/api/printoka/notepad/options")
def notepad_options(product: int = Query(104)):
    return {}  # all notepad fields are inline addon fields in the schema


@app.get("/api/printoka/notepad/quote")
def notepad_quote(product: int = Query(104),
                  paper: str = Query("Gloss Art Card 260gsm (2 side coated)"),
                  lamination: str = Query("Matte Lamination (Both)"), qty: int = Query(...)):
    from . import notepad_engine as NP
    try:
        cash = NP.cash_price(paper, qty, lamination)
        wt = NP.weight_kg(paper, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = ("Notepad: fixed 80x106mm, Simili 80gsm 40-sheet content, 4C+4C cover / 1C content, "
            "Wire-O hole punch + Matte Lamination (Both) compulsory (included). Cover paper "
            "(260/310gsm) price-neutral (affects weight only). Spot UV (Front Cover) adds a cost delta. "
            "qty = books.")
    return {"config": {"product": product, "paper": paper, "lamination": lamination, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "formula (qty curve)", "note": note,
            "tiers": NP.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Bill-Book (Litho NCR, id 24) ----------
@app.get("/api/printoka/billbook/options")
def billbook_options(product: int = Query(24)):
    return {}  # all bill-book fields are inline addon fields in the schema


@app.get("/api/printoka/billbook/quote")
def billbook_quote(product: int = Query(24), size: str = Query("A4 (210mm x 297mm)"),
                   paper: str = Query("NCR (Carbonize Paper)"),
                   layers: str = Query("NCR - 2 Layers"), colour: str = Query("1C (Front)"),
                   sets: str = Query("50"), qty: int = Query(...), packform: str = Query("Book"),
                   binding: str = Query("Portrait - Left side binding"),
                   numbering: str = Query("Not Required"), punch: str = Query("Not Required")):
    if paper == "Normal Paper":
        return JSONResponse({"error": "Normal Paper billbook pricing not yet sampled — contact us for quote."}, status_code=400)
    from . import billbook_engine as BB
    import re
    n_layers = int(re.search(r"(\d+)", layers).group(1)) if re.search(r"(\d+)", layers) else 2
    sets_eff = sets if n_layers == 2 else "-"   # 3+ ply: sets fixed (no dropdown on Excard)
    do_num = numbering in ("Yes", "Required")
    do_punch = punch in ("Yes", "Required (6mm)")
    try:
        cash = BB.cash_price(size, layers, colour, sets_eff, qty, packform=packform,
                             numbering=do_num, punch=do_punch)
        wt = BB.weight_kg(size, layers, sets_eff, qty, packform=packform)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": f"no price for {layers}/{colour}"}, status_code=400)
    return {"config": {"product": product, "paper": paper, "size": size, "layers": layers,
                       "colour": colour, "sets": sets_eff, "qty": qty, "packform": packform,
                       "binding": binding, "numbering": numbering, "punch": punch},
            "printoka_cash": round(cash, 2), "method": "formula (per-config curve)",
            "note": "Numbering is free; binding orientation is price-neutral. qty = number of books/pads.",
            "tiers": BB.tiers(cash), "weight_kg": round(wt, 3)}


def _digital_options(size=None, paper=None, colour=None):
    d = _json.loads((UI_DIR.parent / "digital_options.json").read_text())
    out = {"sizes": d["sizes"], "papers": [], "colours": [], "packages": [],
           "deliveries": {}}
    if size:
        out["papers"] = [p for p in d["papers_by_size"].get(size, []) if "Out of Stock" not in p]
    if size and paper:
        out["colours"] = ["4C (Both)", "4C (Front)"]
    if size and paper and colour:
        out["packages"] = ["Normal", "2in1", "3in1", "4in1", "5in1"]
    return out


@app.get("/api/printoka/options")
def printoka_options(product: int = Query(21), size: str | None = None,
                     paper: str | None = None, colour: str | None = None):
    if product == 50:
        return _digital_options(size, paper, colour)
    return order_options(size, paper, colour)   # Litho: from OrderWork combos


@app.get("/api/printoka/quote")
def printoka_quote(size: str = Query(...), paper: str = Query(...),
                   colour: str = Query(...), qty: int = Query(...),
                   package: str = Query("Normal"), product: int = Query(21),
                   custom_h: float = Query(0), custom_w: float = Query(0),
                   hot_stamping: str = Query("Not Required"), fold: str = Query("None"),
                   punch: str = Query("No"), envelope: str = Query("Not Required")):
    """Pure-formula price (per-product engine) + physics weight. No stored prices.
    custom_h/custom_w (mm) override the standard size for a custom dimension — priced
    by the engine's area formula (the curve only covers the standard sizes)."""
    from . import cost_engine, digital_engine, formulation
    custom = bool(custom_h and custom_w)
    if custom:
        size = f"{int(custom_w)}mm x {int(custom_h)}mm"
    mult = package_multiplier(package)
    env_add = envelope_cost(envelope, qty)   # priced per-piece (sampled), scales with package
    fin = 0.0
    try:
        from . import loose_finishing as LF
        fin_add = LF.finishing_cost({"hot_stamping": hot_stamping, "fold": fold, "punch": punch}, qty, size)
        if product == 50:
            base = digital_engine.cash_price(size, paper, colour, qty)
            fin = fin_add + env_add
            cash = (base + fin) * mult
            tiers = digital_engine.tiers(cash); wt = digital_engine.weight_kg(size, paper, qty) * mult
        else:
            fin = fin_add + env_add
            cash = (cost_engine.cash_price(size, paper, colour, qty) + fin) * mult
            tiers = formulation.tiers(cash); wt = formulation.weight_kg(size, paper, qty) * mult
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    note = "Envelope priced as a per-piece estimate (~RM0.04/pc); Excard band-prices at low quantities." \
        if env_add else None
    return {"config": {"size": size, "paper": paper, "colour": colour,
                       "package": package, "qty": qty, "product": product, "custom": custom,
                       "envelope": envelope},
            "printoka_cash": round(cash, 2), "finishing_cost": round(fin * mult, 2),
            "method": "formula" + (" · custom size" if custom else ""), "note": note,
            "tiers": tiers, "weight_kg": round(wt, 2), "excard_cash": None, "delta_pct": None}


@app.get("/api/printoka/kpi")
def printoka_kpi(product: int = Query(21)):
    """Per-product spot-test accuracy report (Excard = reference; no stored prices)."""
    name = "spot_test_report_50.json" if product == 50 else "spot_test_report.json"
    rep = UI_DIR.parent / "output" / name
    if rep.exists():
        return _json.loads(rep.read_text())
    return {"status": "not_calibrated",
            "note": "No spot-test report yet for this product."}


@app.post("/api/printoka/feedback")
async def feedback(request: Request):
    """Capture user pricing feedback → output/feedback.jsonl (one JSON per line),
    so it can be reviewed and fed into recalibration."""
    import datetime
    try:
        body = await request.json()
    except Exception:
        body = {}
    body["ts"] = datetime.datetime.now().isoformat(timespec="seconds")
    fp = UI_DIR.parent / "output" / "feedback.jsonl"
    with fp.open("a", encoding="utf-8") as f:
        f.write(_json.dumps(body, ensure_ascii=False) + "\n")
    return {"ok": True, "saved": str(fp.name)}


@app.get("/api/printoka/feedback")
def feedback_list():
    fp = UI_DIR.parent / "output" / "feedback.jsonl"
    if not fp.exists():
        return {"count": 0, "items": []}
    items = [_json.loads(l) for l in fp.read_text(encoding="utf-8").splitlines() if l.strip()]
    return {"count": len(items), "items": items[-50:]}


@app.get("/")
def calculator():
    # The calculator is the primary page (what the preview opens).
    return FileResponse(UI_DIR / "calculator.html")


@app.get("/calculator")
def calculator_alias():
    return FileResponse(UI_DIR / "calculator.html")


@app.get("/standalone")
def standalone():
    return FileResponse(UI_DIR / "calculator_standalone.html")


@app.get("/dashboard")
def dashboard():
    return FileResponse(UI_DIR / "dashboard.html")


@app.get("/packaging")
def packaging_page():
    return FileResponse(UI_DIR / "packaging.html")


@app.get("/coverage")
def coverage_page():
    return FileResponse(UI_DIR / "coverage.html")


@app.get("/packaging-standalone")
def packaging_standalone():
    return FileResponse(UI_DIR / "packaging_standalone.html")
