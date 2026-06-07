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

from fastapi import FastAPI, Query
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
PRODUCTS_UI = [{"id": 21, "name": "Loose Sheet — Litho (Offset)"},
               {"id": 50, "name": "Loose Sheet — Digital"}]


@app.get("/api/printoka/products")
def printoka_products():
    return PRODUCTS_UI


# accuracy (median %) for products that have a calibrated formula
FORMULATED = {21: 8.29, 50: 1.3}


@app.get("/api/printoka/product-status")
def product_status():
    with session_scope() as s:
        prods = s.scalars(select(Product).order_by(Product.excard_id)).all()
        counts = dict(s.execute(select(OrderWork.product_id, func.count())
                                .group_by(OrderWork.product_id)).all())
        return [{"id": p.excard_id, "name": p.name, "category": p.category,
                 "combos_initiated": counts.get(p.excard_id, 0),
                 "accuracy": FORMULATED.get(p.excard_id),
                 "formulated": p.excard_id in FORMULATED} for p in prods]


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
                   package: str = Query("Normal"), product: int = Query(21)):
    """Pure-formula price (per-product engine) + physics weight. No stored prices."""
    from . import cost_engine, digital_engine, formulation
    try:
        if product == 50:
            cash = digital_engine.cash_price(size, paper, colour, qty)
            tiers = digital_engine.tiers(cash); wt = digital_engine.weight_kg(size, paper, qty)
        else:
            cash = cost_engine.cash_price(size, paper, colour, qty)
            tiers = formulation.tiers(cash); wt = formulation.weight_kg(size, paper, qty)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return {"config": {"size": size, "paper": paper, "colour": colour,
                       "package": package, "qty": qty, "product": product},
            "printoka_cash": round(cash, 2), "method": "formula",
            "tiers": tiers, "weight_kg": wt, "excard_cash": None, "delta_pct": None}


@app.get("/api/printoka/kpi")
def printoka_kpi(product: int = Query(21)):
    """Per-product spot-test accuracy report (Excard = reference; no stored prices)."""
    name = "spot_test_report_50.json" if product == 50 else "spot_test_report.json"
    rep = UI_DIR.parent / "output" / name
    if rep.exists():
        return _json.loads(rep.read_text())
    return {"status": "not_calibrated",
            "note": "No spot-test report yet for this product."}


@app.get("/")
def dashboard():
    return FileResponse(UI_DIR / "dashboard.html")


@app.get("/calculator")
def calculator():
    return FileResponse(UI_DIR / "calculator.html")
