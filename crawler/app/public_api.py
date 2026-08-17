"""Printoka Pricing API — lets external websites use the calculator as a pricing database.

Single source of truth: it serves the SAME catalog and computes quotes with the SAME engine
the standalone calculator uses (output/calculator_data.json + output/calculator_engine.cjs,
both emitted by `python -m app.build_standalone`). Run:

    uvicorn app.public_api:app --host 0.0.0.0 --port 8020

Endpoints (JSON, CORS-enabled):
    GET  /api/v1/health
    GET  /api/v1/products                 -> catalog (id, name, category, pricing_type)
    GET  /api/v1/products/{id}            -> option schema + valid-combination rules + images
    POST /api/v1/quote                    -> {product_id, options:{...}, quantity} -> price
Interactive docs at /docs.
"""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "output" / "calculator_data.json").read_text(encoding="utf-8"))
NODE_CLI = str(ROOT / "app" / "calc_quote.cjs")
CHANGE_REPORT = ROOT / "output" / "change_report.json"
WHATSNEW_HTML = ROOT / "ui" / "whatsnew.html"
PRODUCTS = {p["id"]: p for p in DATA["products"]}

# ── Dynamic option resolvers for products that use specialised engines ─────────
_BC_LABELS = {"Standard Card": "standard", "Thin Fold": "thin_fold",
              "Fat Fold": "fat_fold", "Custom Die-Cut": "custom_die_cut",
              "Plastic Card": "plastic_card"}
_BC_LABELS_INV = {v: k for k, v in _BC_LABELS.items()}


def _bizcard_options_for_field(field_key: str, selected: dict) -> list[str] | None:
    """Return allowed options for a bizcard field given already-selected values."""
    from .bizcard_sampler import CARDTYPES, PAPERS, PLASTIC_PAPER  # noqa: PLC0415
    if field_key == "cardType":
        return list(_BC_LABELS.keys())
    card_label = selected.get("cardType")
    if not card_label:
        return None
    ct_key = _BC_LABELS.get(card_label, card_label)
    ct = CARDTYPES.get(ct_key)
    if not ct:
        return None
    _od, sizes, colours, _custom = ct
    if field_key == "size":
        return sizes
    if field_key == "paper":
        return [PLASTIC_PAPER] if ct_key == "plastic_card" else PAPERS
    if field_key == "colour":
        return colours
    return None


def _resolve_bizcard_fields(fields: list, selected: dict | None = None) -> list:
    """Inject dynamic options into bizcard fields that have depends-based options."""
    selected = selected or {}
    result = []
    for f in fields:
        if f["options"] is None and f.get("key") in ("cardType", "size", "paper", "colour"):
            opts = _bizcard_options_for_field(f["key"], selected)
            result.append({**f, "options": opts})
        else:
            result.append(f)
    return result

# One source of truth for categories: Excard's own catalogue taxonomy (see build_specs_page).
from app.build_specs_page import cat_of as _cat_of, CATEGORIES as _CATEGORIES  # noqa: E402
_CAT_LABEL = {k: l for k, l, _ in _CATEGORIES}


def _category_of(p) -> str:
    return _CAT_LABEL.get(_cat_of(p.get("name", ""), p.get("id")), "Misc")




def _pricing_type(p) -> str:
    if p.get("engine") == "contact":
        return "contact"
    return "exact" if p.get("accuracy") == 0 else "reference"


def _summary(p):
    return {"id": p["id"], "name": p["name"], "category": _category_of(p),
            "pricing_type": _pricing_type(p)}


def _detail(p):
    fields = []
    for f in p.get("fields", []):
        opts = f.get("options") or (list(f["images"].keys()) if f.get("images") else None)
        fields.append({
            "key": f["key"], "label": f["label"], "type": f.get("type", "select"),
            "required": not f.get("optional", False) and f.get("type") != "number",
            "options": opts, "images": f.get("images") or None,
            "min": f.get("min"), "max": f.get("max"),
            # conditional visibility + presentation the configurator needs to mirror the calculator
            "showWhen": f.get("showWhen"), "swatch": f.get("swatch", False),
            "optional": f.get("optional", False), "section": f.get("section"),
            "default": f.get("default"), "note": f.get("note"),
        })

    validity = p.get("validity")

    # For bizcard engine: inject dynamic options + build validity cascade rules
    if p.get("optsrc") == "bizcard" or p.get("engine") == "bizcard":
        fields = _resolve_bizcard_fields(fields)
        # Build validity rules: selecting cardType restricts size/paper/colour
        from .bizcard_sampler import CARDTYPES, PAPERS, PLASTIC_PAPER  # noqa: PLC0415
        rules: dict = {}
        for label, key in _BC_LABELS.items():
            ct = CARDTYPES.get(key)
            if ct:
                _od, sizes, colours, _custom = ct
                rules[label] = {
                    "size": sizes,
                    "paper": [PLASTIC_PAPER] if key == "plastic_card" else PAPERS,
                    "colour": colours,
                }
        validity = {"primary": "cardType", "fields": ["size", "paper", "colour"], "rules": rules}

    return {"id": p["id"], "name": p["name"], "category": _category_of(p),
            "pricing_type": _pricing_type(p), "markup": p.get("markup", 1.0),
            "fields": fields, "validity": validity,
            "quantity": _quantity_of(p),
            # Excard's questionnaire sections, in Excard's order (General / Optional Finishing / …),
            # so the configurator can group controls exactly like the supplier's order form.
            "sectionOrder": p.get("sectionOrder") or [],
            # The section that holds Quantity on Excard (or null — most products keep Quantity in the
            # summary, NOT General). Configurator inlines Quantity only where Excard groups it.
            "quantitySection": p.get("quantitySection"),
            "tiers": ["Cash", "Silver", "Gold", "Platinum"]}


def _quantity_of(p):
    """Per-product order quantity rules, mirrored from the supplier's order form:
    moq = minimum order quantity, options = the standard order quantities,
    custom = whether an arbitrary quantity is accepted, mode = 'free' | 'fixed'
    ('fixed' means the order quantity must be one of `options`)."""
    q = p.get("quantity") or {}
    if not q:
        return {"moq": 1, "maxq": None, "options": [], "custom": True, "mode": "free",
                "note": "any positive integer; price interpolates between breakpoints"}
    return {"moq": q.get("moq", 1), "maxq": q.get("maxq"), "options": q.get("options", []),
            "custom": q.get("custom", True), "mode": q.get("mode", "free"),
            "note": ("any quantity from the MOQ; price interpolates between breakpoints"
                     if q.get("custom") else
                     "order quantity must be one of `options` (minimum = moq)")}


app = FastAPI(title="Printoka Pricing API", version="1.0",
              description="Product catalog, customization options, valid-combination rules, "
                          "and live pricing — shared by the Printoka calculator.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                   allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "products": len(PRODUCTS)}


@app.get("/api/v1/products")
def list_products(category: str | None = None, pricing_type: str | None = None):
    items = [_summary(p) for p in DATA["products"]]
    if category:
        items = [i for i in items if i["category"].lower() == category.lower()]
    if pricing_type:
        items = [i for i in items if i["pricing_type"] == pricing_type]
    return {"count": len(items), "products": items}


@app.get("/api/v1/products/{product_id}")
def get_product(product_id: int):
    p = PRODUCTS.get(product_id)
    if not p:
        raise HTTPException(404, "unknown product_id")
    return _detail(p)


class QuoteRequest(BaseModel):
    product_id: int
    options: dict = {}
    quantity: int


@app.post("/api/v1/quote")
def quote(req: QuoteRequest):
    if req.product_id not in PRODUCTS:
        raise HTTPException(404, "unknown product_id")
    # Enforce the supplier's order-quantity rules (MOQ / fixed quantities)
    q = _quantity_of(PRODUCTS[req.product_id])
    if req.quantity < q["moq"]:
        raise HTTPException(400, {"error": "quantity below minimum order quantity",
                                  "moq": q["moq"], "options": q["options"][:20]})
    if q["mode"] == "fixed" and q["options"] and req.quantity not in q["options"]:
        raise HTTPException(400, {"error": "quantity must be one of the standard order quantities",
                                  "moq": q["moq"], "options": q["options"]})
    payload = json.dumps({"product_id": req.product_id, "options": req.options,
                          "quantity": req.quantity})
    try:
        r = subprocess.run(["node", NODE_CLI], input=payload, capture_output=True,
                           text=True, timeout=20)
    except FileNotFoundError:
        raise HTTPException(500, "Node.js is required to run the pricing engine")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"pricing engine error: {e}")
    if r.returncode != 0 or not r.stdout:
        raise HTTPException(500, (r.stderr or "pricing engine failed").strip())
    res = json.loads(r.stdout)
    status = res.pop("_status", 200)
    if status != 200:
        raise HTTPException(status, res.get("error", "could not price this combination"))
    return res


@app.get("/api/v1/changes")
def changes():
    """Latest market-change report (from app.excard_watch ... --json output/change_report.json)."""
    if CHANGE_REPORT.exists():
        return json.loads(CHANGE_REPORT.read_text(encoding="utf-8"))
    return {"error": "no change report yet", "new_products": [], "removed_products": [], "changed": {}}


@app.get("/whatsnew")
def whatsnew():
    """Market Watch dashboard (renders /api/v1/changes)."""
    return FileResponse(WHATSNEW_HTML)


@app.get("/capture")
def capture():
    """Market Scan helper: capture bookmarklet + the full product checklist."""
    return FileResponse(ROOT / "ui" / "capture.html")


# ── Order intake ───────────────────────────────────────────────────────────────
# The standalone calculator's Excard-style order flow POSTs a configured order here.
# No payment: an order is a *request* Printoka fulfils manually. Stored as one JSON
# file per order under output/orders/ plus an append-only output/orders.jsonl log.
import datetime as _dt
import secrets as _secrets
import threading as _threading

ORDERS_DIR = ROOT / "output" / "orders"
ORDERS_LOG = ROOT / "output" / "orders.jsonl"
_ORDER_LOCK = _threading.Lock()


class OrderLine(BaseModel):
    product_id: int
    product_name: str = ""
    options: dict = {}
    quantity: int
    unit_price: float | None = None
    cash: float | None = None
    weight_kg: float | None = None


class OrderRequest(BaseModel):
    items: list[OrderLine]
    contact: dict = {}          # name, email, phone, company
    delivery: dict = {}         # destination code/label, address lines, method
    artwork: dict = {}          # filename, note, design_service
    totals: dict = {}           # subtotal, delivery_fee, grand_total (as computed client-side)
    remarks: str = ""


def _new_ref() -> str:
    return f"ORD-{_dt.datetime.now():%y%m%d}-{_secrets.token_hex(3).upper()}"


@app.post("/api/v1/orders")
def create_order(req: OrderRequest):
    if not req.items:
        raise HTTPException(400, "order has no items")
    for ln in req.items:
        if ln.product_id not in PRODUCTS:
            raise HTTPException(404, f"unknown product_id {ln.product_id}")
        if ln.quantity <= 0:
            raise HTTPException(400, "quantity must be positive")
    ref = _new_ref()
    record = {"order_ref": ref, "status": "received",
              "received_at": _dt.datetime.now().isoformat(timespec="seconds"),
              **req.model_dump()}
    with _ORDER_LOCK:
        ORDERS_DIR.mkdir(parents=True, exist_ok=True)
        (ORDERS_DIR / f"{ref}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1),
                                                encoding="utf-8")
        with ORDERS_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"ok": True, "order_ref": ref, "status": record["status"],
            "received_at": record["received_at"]}


@app.get("/api/v1/orders/{order_ref}")
def get_order(order_ref: str):
    """Order tracking — look up a previously placed order request by reference."""
    f = ORDERS_DIR / f"{order_ref}.json"
    if not f.exists():
        raise HTTPException(404, "unknown order reference")
    return json.loads(f.read_text(encoding="utf-8"))
