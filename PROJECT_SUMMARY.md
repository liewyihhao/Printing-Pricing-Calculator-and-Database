# Printoka Pricing Intelligence — Project Summary

_A self-contained briefing for the Claude.ai project "Online Printing In Malaysia, Singapore, and Brunei". Upload this file to the project's knowledge base so the web assistant has full context._

## Goal
Build a system that crawls **all of Excard's (excard.com.my) product prices** — exactly as Excard charges — store them, and later use that data to power **Printoka's** own pricing/costing calculator and reverse-engineer production economics. Printoka is a reseller on Excard (Gold tier). Accuracy must match Excard exactly (Cash base) or within RM 0.10 (derived tiers).

## Where the code lives
`C:\Users\User\OneDrive\Desktop\Printoka.com\` (OneDrive-backed). The working system is the Python package `crawler/app/` (PostgreSQL + Playwright + FastAPI). Run things with `crawler\.venv\Scripts\python.exe -m app <command>`.

## What's built (working)
- **Crawler** (`crawler/app/`): logs into Excard with the reseller account, drives the order page, captures real prices. PostgreSQL storage via SQLAlchemy. Resumable, self-healing (browser relaunch on hang, network-drop retry, gentle pacing to avoid rate-limit blocks).
- **API** (`app/api.py`, FastAPI): serves the data — `/api/order/options` (cascading, only valid combos), `/api/order/quote` (price ladder), product/crawl status. Serves the UI.
- **UI** (`crawler/ui/dashboard.html`): Stripe-styled dashboard (designed with the refero MCP) — Overview, Products, Pricing tables, Calculator, Crawl status. Calculator uses **dependent dropdowns** so only valid Excard combinations can be selected (no empty combos), mirroring Excard's order page.
- **Catalog** (`crawler/PRODUCTS_CHECKLIST.md`): all 78 products classified into 11 families with a done/not-done checklist.

## Key Excard mechanics we reverse-engineered
- **Two price pages differ:** `/price-list/...` is ~2× higher and NOT order-accurate. The **order page `/spec/Litho/<Product>`** is the real one — we crawl that.
- **Login:** main form `#mainContent_txtUsernameMid/...PasswordMid` + `#mainContent_btnLogin`; a "BECOME OUR MEMBER" modal can block it (hide `#excard-form`).
- **Price recompute quirk:** changing quantity alone does NOT update the price (a buggy `checkother()` postback). The price only recomputes on the **delivery (order_price) postback**, and re-checking the same delivery radio is a no-op. Reliable recipe per quantity: select quantity → **toggle delivery** (helper code → target) → read. (A single toggle is unreliable — reads stale values.)
- **Tiers:** Excard charges Cash (base) and discounts: **Silver −4%, Gold −8%, Platinum −14%** off Cash. We crawl the exact Cash base (`PRICE BEFORE DISCOUNT`) and derive the tiers (verified within ±0.02, under the RM 0.10 tolerance). Account is Gold.
- **Weight** is captured per quantity (for shipping estimates; Excard has a `/shipping?country=X&weight=Y` endpoint). Base price is delivery-independent, so we crawl one reference delivery and derive shipping from weight.

## Order-page dimensions (per product, "standard print" family)
Size × Paper × Print Colour (4C/1C, Front/Both) × Package (Normal, 2in1…10in1 ganging) × Quantity. Plus **optional finishing / add-ons** that add price deltas: **Folding, Punch Hole, Round Corner, Hot Stamping, Lamination (art-card papers), Envelope**. These are separable deltas to be captured and added on top of the base price.

## Status (as of this summary)
- **Loose Sheet (product 21)** — base crawl in progress (multi-day; thousands of order-accurate quotes captured). Finishing/add-on deltas: identified, not yet captured. This is the proven template.
- **Other 77 products** — not started. 24 are "Offset Print" (same engine), ~54 are custom (apparel/mugs/large-format/etc., need per-family handlers).
- Crawl one product at a time; tick `PRODUCTS_CHECKLIST.md` as each completes.

## Run commands
```
.venv\Scripts\python.exe -m app init-db
.venv\Scripts\python.exe -m app order-enqueue        # enumerate configs
.venv\Scripts\python.exe -m app order-crawl          # resumable crawl
.venv\Scripts\python.exe -m app order-status         # progress
.venv\Scripts\python.exe -m uvicorn app.api:app --port 8000   # UI at http://localhost:8000
```

## Next steps
1. Capture finishing/add-on deltas for Loose Sheet (Folding, Punch Hole, Round Corner, Hot Stamping, Lamination, Envelope) → exact match incl. extras.
2. Generalize the crawler to the other 23 Offset Print products.
3. Build custom handlers for non-standard families (apparel, large format, etc.).
4. Reverse-engineering / prediction engine on the complete dataset.
5. Wire shipping (weight → cost) for Malaysia/Singapore/Brunei/Thailand + any country.
