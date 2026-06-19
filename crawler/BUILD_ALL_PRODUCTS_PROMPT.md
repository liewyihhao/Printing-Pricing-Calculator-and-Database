# Prompt — Build ALL 52 Excard products into the Printoka calculator

_Paste the block below into a fresh Claude Code chat (run from the repo root,
`C:\Users\User\OneDrive\Desktop\Printoka.com`). It tells Claude to read everything already
done, then build the remaining products one at a time, committing to GitHub as it goes._

---

You are continuing the **Printoka pricing-calculator** project (branch
`feat/business-card-standalone-calculator`, repo
github.com/liewyihhao/Printing-Pricing-Calculator-and-Database). Work in `crawler/`; the
venv is `crawler/.venv` (`.venv\Scripts\python.exe`).

## STEP 0 — Read everything already done (do this first, fully)
1. `crawler/HANDOFF.md` — full project state, conventions, every product built so far.
2. `crawler/PARITY_AUDIT.md` — option/price parity vs Excard per product + open gaps.
3. `crawler/NEW_PRODUCT_PROMPT.md` — the reusable add-a-product workflow (follow it).
4. `crawler/PACKAGING_BOX_PLAN.md` + `PACKAGING_BOX_FINDINGS.md` — packaging build.
5. The catalogue coverage: open `crawler/output/catalogue_coverage.json` (or run
   `cd crawler && .venv\Scripts\python.exe -m app.catalogue_scan --print`). It lists all
   **52 Excard products** and which **8** are built. Also read the existing engines/UI to
   learn the pattern: `app/api.py` (FIELD_SCHEMAS, quote endpoints), `app/*_engine.py`,
   `app/*_sampler.py`, `ui/calculator.html`, `ui/_standalone_template.html`,
   `app/build_standalone.py`, `ui/packaging.html`.

## What's DONE (8 product families — do NOT rebuild)
Business Card (1) · Loose Sheet Litho/Digital (21/50) · Booklet Litho/Digital (19/37) ·
Label Sticker Digital/Letterpress (60/61, incl CD + all cut categories) · Bill-Book (24) ·
Packaging Boxes (67 styles, 3D + dieline). #18 parity closed; cross-product option audit
done; catalogue auto-check-up live at `/coverage`.

## GOAL — build the remaining 44 products so all 52 are in the dashboard
Build each following the established pattern. Group/priority (do most-ordered first):
- **Books & Stationery:** Brochure, Flyer(=loose, verify), Notepad, Letterhead, Envelope,
  Folder, L-Shape Folder, Bookmark, Voucher, Computer Form, Wire-O Notebook.
- **Cards:** PVC Card, Tent Card, Kad Kahwin, Kad Terima Kasih.
- **Calendars & Diary:** Desk Calendar (Hard/Soft Stand), Wall Calendar, Wire-O Wall Calendar.
- **Stickers & Labels:** Car Sticker, Static Cling Window Sticker (+ Roll-Form already=60).
- **Packaging & Bags:** Paper Bag, Non-Woven Bag, Canvas Tote Bag, Standing Pouch, Sachet Board.
- **Money Packet.**  **Large Format:** Banner, Bunting, Roll-Up Stand, Wobbler.
- **Apparel & Gifts:** Mug, Magnet, Button Badge, Sublimation Shirt, Hand Fan, Hanger,
  Hard Cover Menu, Mask Keeper, Pillow, Pre-Inked Stamp, Stamp Chop.
- **Misc:** Arch File, Papan Kopi, Customprint.

## HOW to build each product (per NEW_PRODUCT_PROMPT.md)
1. **Find the order page.** Most are `www.excard.com.my/spec/<Method>/<slug>` (browser-driven
   like booklet/loose/sticker); some are v4 `devv2.excard.com.my/Product/CheckPrice` (like
   Business Card — call the JSON API directly); large-format/apparel may differ. Use
   `app/parity_formdump.py` to dump the live form's controls + options first.
2. **Sample prices** (our own formula, Excard = reference only). Build
   `app/<product>_sampler.py`; sweep every option × the qty ladder; finishing as deltas.
   ONE www crawl at a time (two headless browsers starve this machine); run in background,
   resumable; never claim an accuracy number you didn't measure.
3. **Build the engine** `app/<product>_engine.py`: per-config quantity curve (log-interp,
   exact at order qtys) or area-law fit; `cash_price`, `tiers` (Cash→Silver−4→Gold−8→
   Platinum−14), `weight_kg`, delivery per-kg (W.MY 6 / E.MY 10 / SG 6 / TH 6).
4. **Wire into the API + both UIs:** add to `PRODUCTS_UI`, `FIELD_SCHEMAS`, `_family()` +
   `options`/`quote` endpoints in `app/api.py`; mirror the field list in
   `app/build_standalone.py` + JS engine port in `ui/_standalone_template.html`; run
   `python -m app.build_standalone`. The schema-driven UI then renders it automatically.
   Match Excard's options EXACTLY incl. detailed sub-options (sizes, materials, finishing,
   colours) and show compulsory finishing in the quote note.
5. **Audit honestly** (`app/audit.py` or leave-one-out): report median %, % within 10%,
   worst configs; iterate to ≤10% or document why not.
6. **Update `BUILT` in `app/catalogue_scan.py`** so `/coverage` shows the product as built,
   and update `HANDOFF.md` + `PARITY_AUDIT.md`.

## GitHub — keep everything updated
Commit incrementally **per product** (engine + sampler + api + UIs + standalone + docs).
Force-add only SMALL `output/*.json` params/curves (never the large `*_samples_*.json`).
End commit messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
`git push` after each product. Keep the working tree clean.

## Verify
After each product: `cd crawler && .venv\Scripts\python.exe -m uvicorn app.api:app --port 8000`,
open `/` (pick the product) and `/coverage`; confirm options match Excard, price computes,
and JS(standalone)==Python to the cent.

## Known open items to also close
- Booklet **cover-lamination** price delta is unsampled (form cover-colour cascade hidden
  headless → stale read). Fix the booklet config (set cover colour via the OuterInner
  radio / JS), sample the delta, and price it (currently "quoted separately").
- Loose **Envelope** is priced as a per-piece estimate; Litho band-prices at low qty —
  refine if you sample more points.

Work autonomously, one product at a time, committing + pushing as you go. Report progress
per product and a final summary when all 52 are built and pushed.
