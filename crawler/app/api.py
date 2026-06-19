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
               {"id": 105, "name": "Letterhead — Litho"}]
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
              105: 8.2}  # letterhead: exact at sampled order qtys; 8.2 = held-out interp median


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
                     "options": ["Rectangle/Square", "Custom Die-Cut", "Standard Shape", "Round", "No Cut", "Kiss Cut", "Multiple Dieline"]},
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
                    {"key": "numbering", "label": "Numbering (free)", "addon": True, "depends": [], "options": ["No", "Yes"]},
                    {"key": "punch", "label": "Hole punch (6mm)", "addon": True, "depends": [], "options": ["No", "Yes"]},
                ]},
    "letterhead": {"options": "/api/printoka/letterhead/options", "quote": "/api/printoka/letterhead/quote",
                "fields": [
                    {"key": "paper", "label": "Paper", "addon": True, "depends": [],
                     "options": ["Simili 80gsm", "Simili 100gsm", "Conqueror 100gsm Brilliant White Laid",
                                 "Conqueror 100gsm Diamond White Laid", "Conqueror 100gsm White Wove",
                                 "Conqueror 100gsm Cream Laid"]},
                    {"key": "colour", "label": "Print colour / side", "addon": True, "depends": [],
                     "options": ["1C (Front)", "2C (Front)", "4C (Front)", "4C (Both)"]},
                ]},
    "notepad": {"options": "/api/printoka/notepad/options", "quote": "/api/printoka/notepad/quote",
                "fields": [
                    {"key": "paper", "label": "Cover paper (weight only; no price change)", "addon": True, "depends": [],
                     "options": ["Gloss Art Card 260gsm (2 side coated)", "Gloss Art Card 310gsm (2 side coated)"]},
                    {"key": "lamination", "label": "Lamination (Matte Both compulsory; Spot UV quoted separately)", "addon": True, "depends": [],
                     "options": ["Matte Lamination (Both)", "Matte Lamination (Both) + Spot UV (Front Cover)"]},
                ]},
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
        if method == "digital" and category == "Multiple Dieline":
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


# ---------- Letterhead (Litho, id 105) ----------
@app.get("/api/printoka/letterhead/options")
def letterhead_options(product: int = Query(105)):
    return {}  # all letterhead fields are inline addon fields in the schema


@app.get("/api/printoka/letterhead/quote")
def letterhead_quote(product: int = Query(105), paper: str = Query("Simili 80gsm"),
                     colour: str = Query("4C (Front)"), qty: int = Query(...)):
    from . import letterhead_engine as LH
    try:
        cash = LH.cash_price(paper, colour, qty)
        wt = LH.weight_kg(paper, qty)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": "no price"}, status_code=400)
    note = ("Letterhead: fixed A4 (210x297mm). The 4 Conqueror 100gsm finishes are price-"
            "identical. Exact at sampled order quantities (500/1000/1500); other quantities "
            "interpolate. qty = sheets.")
    return {"config": {"product": product, "paper": paper, "colour": colour, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "formula (per-config qty curve)", "note": note,
            "tiers": LH.tiers(cash), "weight_kg": round(wt, 3)}


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
            "(260/310gsm) and Spot UV do not change the online price (block/included). qty = books.")
    return {"config": {"product": product, "paper": paper, "lamination": lamination, "qty": qty},
            "printoka_cash": round(cash, 2), "method": "formula (qty curve)", "note": note,
            "tiers": NP.tiers(cash), "weight_kg": round(wt, 3)}


# ---------- Bill-Book (Litho NCR, id 24) ----------
@app.get("/api/printoka/billbook/options")
def billbook_options(product: int = Query(24)):
    return {}  # all bill-book fields are inline addon fields in the schema


@app.get("/api/printoka/billbook/quote")
def billbook_quote(product: int = Query(24), size: str = Query("A4 (210mm x 297mm)"),
                   layers: str = Query("NCR - 2 Layers"), colour: str = Query("1C (Front)"),
                   sets: str = Query("50"), qty: int = Query(...), packform: str = Query("Book"),
                   binding: str = Query("Portrait - Left side binding"),
                   numbering: str = Query("No"), punch: str = Query("No")):
    from . import billbook_engine as BB
    import re
    n_layers = int(re.search(r"(\d+)", layers).group(1)) if re.search(r"(\d+)", layers) else 2
    sets_eff = sets if n_layers == 2 else "-"   # 3+ ply: sets fixed (no dropdown on Excard)
    try:
        cash = BB.cash_price(size, layers, colour, sets_eff, qty, packform=packform,
                             numbering=(numbering == "Yes"), punch=(punch == "Yes"))
        wt = BB.weight_kg(size, layers, sets_eff, qty, packform=packform)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=400)
    if cash <= 0:
        return JSONResponse({"error": f"no price for {layers}/{colour}"}, status_code=400)
    return {"config": {"product": product, "size": size, "layers": layers, "colour": colour,
                       "sets": sets_eff, "qty": qty, "packform": packform, "binding": binding,
                       "numbering": numbering, "punch": punch},
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
        if product == 50:
            from . import loose_finishing as LF
            base = digital_engine.cash_price(size, paper, colour, qty)
            fin = LF.finishing_cost({"hot_stamping": hot_stamping, "fold": fold, "punch": punch}, qty, size) + env_add
            cash = (base + fin) * mult
            tiers = digital_engine.tiers(cash); wt = digital_engine.weight_kg(size, paper, qty) * mult
        else:
            fin = env_add
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
