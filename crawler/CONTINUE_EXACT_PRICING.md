# CONTINUE: Make the last 12 Printoka products EXACT via Excard's CheckPrice API

_Paste the "PROMPT" block (bottom) into a new session. Branch
`feat/business-card-standalone-calculator`, work in `crawler/`, venv `.venv\Scripts\python.exe`.
Prefix every shell command with `cd /c/Users/User/OneDrive/Desktop/Printoka.com/crawler &&`._

## Current state (2026-07-05)
Catalog = **93 products**: **81 EXACT** (cent-accurate), **8 REFERENCE** (calibrated formula,
already <5% except Label Stickers), **4 CONTACT** (no auto price yet).
The **+7.5% selling markup is REMOVED** (`_REF_MARKUP = 1.0` in `app/build_standalone.py`) — every
displayed price now matches Excard as closely as its engine allows. **KEEP it at 1.0** for now;
the user will add a markup later, after everything is exact.

## The 12 remaining
**REFERENCE (formula today → make EXACT):**
- `19` Booklet — Litho (Offset) · slug `booklet-offset-softcover`
- `37` Booklet — Digital · slug `booklet-digital-softcover`
- `24` Bill-Book — Litho (NCR) · slug `bill-book`
- `50` Loose Sheet — Digital · slug `loose-sheet` (Digital variant; Litho id 21 already EXACT)
- `111` Computer Form — Litho (NCR) · slug `computer-form`
- `60` Label Sticker — Digital · slug `label-sticker`
- `61` Label Sticker — Letterpress (Hot Stamping) · slug `label-sticker` (Letterpress category)
- `135` Magnet — Digital · slug `magnet` (v4 page = Runtime Error; try www /spec/Digital/Magnet)

**CONTACT (no price today → make EXACT or keep contact):**
- `170` ID Card — Digital · www `spec/Digital/ID_Card` (needs a VDP template chosen to price)
- `184` Roll Form Sticker — Litho · www `spec/Litho/Roll_Form_Sticker`
- `171` X-ccessories — Litho · www `spec/Litho/X-ccessories` (bulk multi-item builder — may stay contact)
- `142` Mask Keeper — Litho · check if it has any v4/www order page

## THE METHOD (already proven — this is the whole game)
Every Excard order page prices through **one API**:
`POST https://devv2.excard.com.my/Product/CheckPrice` with STATIC headers
`Authorization: Basic base64("ExcardAPI:EXCARDPNCAPI")`, `Api-Key: RjvaNM0xSDxcKyneFhFFxek42Nrnd4FuE9rScoHQ`,
plus the logged-in **session Cookie**. Body `{"type":"<Type>","spec":[{...}]}` → `{"Price":"<WM cash>"}`.
Threaded HTTP (no browser per call). Helpers already exist:
- `app/checkprice_enum.py` — GENERALIZED enumerator. For v4 pages with `window.metrics` it (a) uses a
  LOCAL price column if present (`Price (WM)`/`WMPrice`) — no API; else (b) captures the live CheckPrice
  request to learn the schema, aggregates valid combos in-browser (handles 388k-row pages), and prices
  via the direct API. `python -m app.checkprice_enum <slug> [--axes "Col1,Col2"]`.
- `app/voucher_cp_sampler.py`, `app/kadkahwin_sampler.py`, `app/bizcard_cp_sampler.py` — per-product
  samplers for order-form pages that have NO `window.metrics` (read the page `<select>` options, transform
  values, enumerate the cartesian, skip invalid=None). **Copy `bizcard_cp_sampler.py` as the template
  for Booklet/Bill-Book/Loose-Sheet/Computer-Form/Label-Sticker.**
- `app/readymade_enum.login_v4(page)` — the v4 login used everywhere. `checkprice_enum._fetch(type,spec,cookie)`
  and `voucher_cp_sampler._get_session_cookie()` are the API primitives to reuse.

**TWO GOTCHAS that cause "RM 0.00 / None for everything" (this was the whole bug the user flagged):**
1. **`type` casing + spec VALUE format differ from the page labels.** ALWAYS capture ONE real CheckPrice
   request first (drive the page, read `page.on("response")` for `/CheckPrice/`) to see the exact strings,
   then transform. Seen so far: Business Card Size `54mm × 89mm`→`54mm x 89mm`, Package `2 In 1 (2 Designs)`→`2in1`,
   qty strips `— Best Seller`/commas; Kad Kahwin type=`Kad Kahwin`, Size `DL (99mm x 210mm)`→`99mm x 210mm`,
   Paper strips ` (2 sides coated)`; Bill-Book type=`BILL BOOK`, fields Size/BindingType/Orientation/
   PaperMaterials/Layers/PrintColour/Sets/IsNumbering/… (schema already captured — see git log / just re-capture).
2. **Restrict to PRICE-DETERMINING axes** to avoid combinatorial blowup: NCR paper colours, lamination,
   envelope, hot-stamping, numbering are usually price-neutral. Verify neutrality by sampling 2 values ×
   a few configs, then drop the neutral axes from the enumeration key.

## Per-product wiring (identical each time)
1. Sampler writes `output/v4_options/<slug>_options.json` (standard capture shape: `optionCols`, `primary`,
   `deps`, `distinct`, `priceMeta`, `curves`). checkprice_enum & the samplers already do this.
2. In `app/build_standalone.py`: change the product stub to `"engine": "pricelist"` (drop its old custom
   engine/fields) with a short `note`, and add `id: ("<slug>", "<tag>_plx")` to `_PRICELIST_FROM_OPTIONS`.
   `_wire_pricelist_products` auto-generates fields + axisFields + params from the capture.
3. `python -m app.build_standalone` → rebuilds `ui/calculator_standalone.html` + `output/calculator_data.json`
   + `output/calculator_engine.cjs`.
4. **Verify (REQUIRED):** with `node`, load `output/calculator_engine.cjs`, and for several sampled curve
   keys assert `localQuote` == the captured price to the cent; confirm `p.accuracy===0`; and
   `grep -io excard output/calculator_data.json ui/calculator_standalone.html output/calculator_engine.cjs`
   returns nothing (no user-visible "excard").
5. Commit per product/batch, ending messages with
   `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Push at the end.

## Scale note
Business Card was 43,200 calls (~30 min, threaded 30). Bill-Book/Booklet are similar or larger — run
samplers as background jobs (`nohup … &`) and poll. Label Sticker (60/61) uses a custom `sticker_categories`
engine and may need the category picker driven; ID Card needs a VDP template selected before it prices
(the user granted the Chrome extension access to `www.excard.com.my` — it can screenshot but not script www,
so prefer Playwright which reads www fully). If a product genuinely can't be enumerated (e.g. X-ccessories
bulk builder), leaving it CONTACT is acceptable — note why.

## Final
Cross-check the calculator's product list once more, confirm 0 "excard" leakage, rebuild, push. Update
`PRODUCT_STATUS.md` and the memory `excard-readymade-pricing-api` if the method evolves.

---

## PROMPT (paste this into the new session)

```
Continue the Printoka project (repo github.com/liewyihhao/Printing-Pricing-Calculator-and-Database,
branch feat/business-card-standalone-calculator, work in crawler/, venv .venv\Scripts\python.exe;
prefix every shell command with: cd /c/Users/User/OneDrive/Desktop/Printoka.com/crawler &&).

STEP 0: Read crawler/CONTINUE_EXACT_PRICING.md IN FULL and the memory
'excard-readymade-pricing-api' — they contain the cracked method, the exact API, the helper
modules, the value-transform gotchas, and the wiring/verification standard.

GOAL: make the LAST 12 products EXACT (price matches Excard to the cent, or within the product's
formula error where cent-exact is impractical). The calculator is 93 products, 81 already EXACT.
KEEP the reference markup at 1.0 (already removed) so prices match Excard — a markup will be added
later, after everything is exact.

REMAINING: Booklet Offset (19), Booklet Digital (37), Bill-Book (24), Loose Sheet Digital (50),
Computer Form (111), Label Sticker Digital (60), Label Sticker Letterpress (61), Magnet (135),
ID Card (170), Roll Form Sticker (184), X-ccessories (171), Mask Keeper (142).

METHOD (proven): every Excard order page prices via POST devv2.excard.com.my/Product/CheckPrice
with static Basic-auth + Api-Key + the logged-in session cookie. For each product: capture ONE
real CheckPrice request to learn the exact `type` + spec value format (they differ from the page
labels — this was the bug), restrict to price-determining axes, enumerate combos via the direct
API (threaded, background), write output/v4_options/<slug>_options.json, wire it in
app/build_standalone.py (stub engine=pricelist + _PRICELIST_FROM_OPTIONS entry), rebuild
(python -m app.build_standalone), verify cent-exact via output/calculator_engine.cjs + no 'excard'
leakage, and commit per product. Reuse app/checkprice_enum.py (metrics pages) and copy
app/bizcard_cp_sampler.py as the template for the order-form pages (no window.metrics). Run
samplers as background jobs — Business Card was 43k calls/~30min. Leaving a genuinely
non-enumerable product (e.g. X-ccessories bulk builder) as CONTACT is acceptable if noted.
At the end: cross-check the full product list, confirm 0 'excard' leakage, rebuild, update
PRODUCT_STATUS.md, and push. End commit messages with
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>.
```
