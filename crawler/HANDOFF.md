# Printoka Pricing Calculator — Project Handoff

_For continuing in a new Claude Code chat. Read this first._
_Raw link: https://raw.githubusercontent.com/liewyihhao/Printing-Pricing-Calculator-and-Database/main/crawler/HANDOFF.md_

## ⭐ LATEST STATE (most recent first)
- **EXCARD ORDERING-PAGE PARITY (single ongoing task #18 — NOT complete).** Goal: every
  product's calculator UI mirrors its Excard order page. Progress:
  - ✅ **Digital Loose Sheet** finishing: hot stamping, folding (8 types, size-dep),
    hole punch — sampled (`loose_finishing_50.json`, `app/loose_finishing.py`) + wired
    (product 50 = `loose_digital` schema family). Hidden radios set via JS click.
  - ✅ **Booklet** (19/37) add-ons: cover hot stamping (block charge, 0 online — note),
    outer/inner (included in cover colour, 0 — curve already matches), **+RM30 extra
    books** (real). `booklet_finishing_sampler.py`.
  - ✅ **Loose Sheet Litho** custom W×H size; **Business Card** finishing+custom size+package.
  - ◑ **Label Sticker** Digital: Rectangle/Square + Custom Die-Cut + 13 materials incl
    Warranty (re-sampled, genuine ~5.5×). Calibration = imposition + blended loss +
    selective material re-centering; TRAIN ~6%, held-out ~11%. Warranty/synthetic
    premium materials remain APPROXIMATE (imposition model can't fully capture them).
  - ✅ Sticker **all cut categories DONE** — Rectangle/Square, Custom Die-Cut,
    **Standard Shape** (H×W, ~1.2× premium), **Round** (diameter d→d×d), **No Cut**
    (qty-only full-sheet, exact curve), **Kiss Cut** (~flat curve). `sticker_categories.py`
    + `sticker_categories.json`; digital sticker schema offers all 6 + optional diameter.
  - ✅ **Letterpress Round** shape (diameter) + **Business Card orientation** field added.
  - ✅ **Sticker Multiple Dieline DONE** — a sheet-based multi-design product. Probed the
    live www form (`app/multidieline_sampler.py`): the ONLY price drivers are
    **ddlCutToSheet** = "Delivery Sheet Size" (A3+ 317×425 / A4 210×297 / A5 148×210 mm),
    **ddlSheetQty** = number of press SHEETS (10…1,000,000), material, and colour. The
    **die-line count** (txtTtlArtwork, "designs per sheet") has **ZERO price effect**
    (verified dl=1/5/20/40 → identical price) — it's a production-only input. There is NO
    per-design size input. Model in `sticker_categories.py` (`multidieline_price`): a
    log-interp **sheet-count curve per sheet size** (Mirror Kote 4C base, from
    `output/sticker_multidieline.json`) × a **material multiplier** (sampled for White PP
    ≈1.43×, Synthetic ≈1.72×; other materials via a linear map of the imposition engine's
    per-material factor, calibrated on those points) × a **1C colour multiplier** (≈0.85).
    Wired into the digital sticker schema (category "Multiple Dieline" + a `sheet_size`
    addon field + an informational `dielines` field), `sticker/quote` (qty = sheet count,
    weight = sheet area × 150gsm × sheets), and the standalone (precomputed
    base/colourMult/matMult baked in; JS `multidielinePrice` == Python to the cent, verified
    via node localQuote: A3+ q100 = RM202.05/2.438kg, A4 Synthetic q1000 = RM1050.88).
    **Accuracy: EXACT at every orderable sheet quantity.** The ddlSheetQty ladder differs
    per sheet size (A4 ≈ 2× A3+, A5 ≈ 4×, since smaller sheets need more sheets for the same
    piece count). `dumpopts` mode captured the real per-size option lists, then `full` mode
    captured **all 18 orderable quantities × 3 sheet sizes = 54 points** (Mirror Kote 4C);
    the curve log-interpolates so it's exact at each dropdown value. Material/colour layer
    median 1.2% (held-out). Sampler modes: `multidieline_sampler.py {run|densify|fill|
    dumpopts|full}` (resumable). Earlier coarse-grid LOO numbers are obsolete.
  - ✅ **Warranty Sticker accuracy FIXED.** Per-material audit vs stored samples revealed
    the handoff's "premium materials ~20–40% off" was really ONLY Warranty Sticker (median
    35.6%); Synthetic/White PP/etc. are already ~5%. Warranty's cost scales far more steeply
    with sticker AREA than nesting predicts (ratio ~2.6× at 20mm → ~12.7× at 100mm), so a
    single material multiplier can't fit it. Replaced with a **2D area×qty curve**
    (`output/sticker_warranty.json`, 11 sizes from real samples) → `warranty_price()` in
    `sticker_categories.py`, routed for Warranty on the per-piece cut categories
    (Rectangle/Custom/Standard/Round). **Exact (0%) at sampled sizes; ~18.6% median for a
    fully held-out size via area interp** (arbitrary in-between sizes interpolate between
    neighbours, so better in practice). Ported to the standalone (`warrantyPrice` JS +
    embedded data; JS==Python to the cent).
  - ⛔ **REMAINING (documented limitations, not missing controls):**
    1. Mirror Kote base imposition median ~12.5% (vs ~5% for most materials) — the
       smooth-formula tail on awkward custom sizes (imposition-band misalignment), as long
       documented. Warranty is now the curve exception above.

## ✅ PARITY ACHIEVED for all standard ordering flows (7 products)
Every product's calculator now mirrors its Excard order page for standard orders:
size/custom-size, paper/material, colour, package, quantity, delivery, AND finishing:
Business Card (lamination/Spot UV/round corner/hole punch/hot stamping/emboss),
Digital Loose Sheet (hot stamp/fold/punch), Booklet (outer-inner/cover hot stamp/extra
books), Label Sticker (all 6 cut categories + 13 materials). Server calc + standalone
both verified JS==Python.
- **EXCARD-PARITY PASS (custom size + package).** Audited each product's live Excard
  ordering form vs our UI and closed the input gaps:
  - **Custom size**: Loose Sheet (21/50) + Business Card (1) now have optional
    **Custom width/height (mm)** fields that override the standard size — priced via the
    engine's area formula (litho/digital) or nearest-area fallback (bizcard). Schema
    supports `type:"number"` + `optional:true` fields; generic UI renders numeric inputs.
    e.g. litho 120×80 q1000 = RM174.86 (server == standalone). Label Sticker already had W×H.
  - **Package (Nin1)**: now a ×N multiplier applied to Loose Sheet + Business Card quotes
    (was previously ignored) — matches Excard's per-design ganging.
  - Fixed an async race in the server calculator (`S.seq` guard) so rapid input can't
    render a stale price.
  - **STILL MISSING vs Excard (need a finishing price-sampling pass on www):**
    Digital Loose Sheet finishing (hot stamping / fold formula / punch hole) and Booklet
    cover finishing (lamination / Spot UV / hot stamping). Litho Loose Sheet has NO
    finishing controls on Excard (confirmed). Business Card finishing is done.
- **LABEL STICKER (products 60 Digital / 61 Letterpress-Hot-Stamping) = BUILT & LIVE.**
  Custom-size product (no standard sizes): customer types W×H mm (1mm steps). On the
  OLD www site — `/spec/Digital/Label_Sticker` + `/spec/Letterpress/Label_Sticker_with_Hot_Stamping`.
  - **Options:** Digital — rdType(Sticker/CD), rdCategory(Rectangle/Round/Custom Die-Cut/
    Kiss Cut/No Cut/…), 13 materials (Mirror Kote…Warranty Sticker), 4C/1C, txtHeight/
    txtWidth, qty 10–8000, Nin1. Letterpress — Standard/Round shape, Gold/Silver hot
    stamping, qty 500–1,000,000.
  - **Price↔size = IMPOSITION BANDS** (stepped, symmetric in W×H, non-monotonic:
    50×48=RM59.90 but 50×60=RM47.90) — how many nest per press sheet. So the engine is
    an **imposition formula** (`app/sticker_engine.py`): `sheets=ceil(qty/ups(W,H))`,
    `cash=margin*(setup+rate*mat[m]*colour*sheets^gamma)`, picking the best of TWO
    calibrated press sheets. Capture+sampler: `app/sticker_capture.py`,
    `app/sticker_sampler.py` (resumable, stale-guarded). Samples
    `output/sticker_samples_{digital,letterpress}.json`; params `sticker_params_*.json`.
  - **Accuracy (held-out sizes/configs):** Digital median ~6%, ~68% within 10% (TRAIN
    4.4%); a tail (~30% of awkward custom sizes) reaches ~36% from imposition-band
    misalignment — a smooth formula can't perfectly track Excard's nesting. Letterpress
    median ~10.5% (sparser: 13 sizes, Standard Shape only — Round didn't capture).
  - **API/UI:** `/api/printoka/sticker/options|quote`; schema family `sticker_digital`/
    `sticker_letterpress` with **number fields** (height/width, type:"number") — the
    generic UI renderer (both server + standalone) now supports numeric inputs.
  - **REMAINING:** denser size sampling would tighten the band tails to ≤10%; Letterpress
    Round shape + Warranty-Sticker material need re-sampling; other cut categories
    (Kiss Cut/No Cut) not yet sampled. Delivery applies (per-kg).
- **FINISHING + DELIVERY for Business Card = DONE (exact via v4 API).**
  - Finishing deltas are per-unit, scale with qty, independent of size/paper. Modelled
    as delta-vs-qty curves in `app/bizcard_finishing.py` (`output/bizcard_finishing.json`),
    added to the quote (`finishing_cost`). Verified exact: e.g. q1000 Gloss250 4C(Both)
    + Gloss Lamination + Round Corner = RM113.20 (47.35 base + 50.85 lam + 15 RC).
  - Priceable via API (exact): **Surface finishing** = Gloss/Matte/Soft-Touch lamination
    + Spot UV (Front/Both) [Spot UV is encoded in the API `Lamination` field as
    "Matte Lamination (Both) + Spot UV (...)"], **Round Corner** (+per-unit, code RC0601),
    **Hole Punch** (3mm/5mm, +per-unit).
  - **Hot Stamping & Embossing**: the CheckPrice API only adds process-DAYS, not cost
    (block/mould charge isn't exposed). UI offers them but labels them "block quoted
    separately"; finishing_cost excludes them + returns a `note`.
  - UI: finishing fields are schema **add-on fields** (`addon:true`, inline `options`,
    `depends:[]`) — the generic renderer fills them inline + defaults, independent of the
    cascade. Both server calculator and standalone updated (JS finishing == Python).
  - Rebuild after re-sampling: `python -m app.bizcard_finishing` then `app.build_standalone`.
  - **REMAINING:** finishing for Loose Sheet (21/50) + Booklets (19/37) is NOT done —
    those products live on the old www site (no API), so finishing must be sampled via
    the browser crawler (slow). Base + delivery are done for them.
- **ACCURACY (measured, honest — `app/audit.py`, ≥60% vs Excard ground truth):**
  All products use **per-config Excard price CURVES** (exact at Excard's order
  quantities) with the smooth formula as fallback for unsampled combos:
  - Booklet-Litho (19): median 0.5%, **100% within 10%** (held-out qty)
  - Booklet-Digital (37): median 1.6%, **100% within 10%**
  - Loose-Sheet-Digital (50): median 1.0%, **93% within 10%**
  - Loose-Sheet-Litho (21): RE-SAMPLED (`spot_samples_21.json`, 147 cfg / 3,424 pts),
    curve `loose_curve_21.json`, median 1.7%, **88% within 10%** (`cost_engine.build_curves()`)
  - Business Card (1): dense re-sample (26,100 pts, qty every 50/100/250), median ~0%
    at order quantities. NOTE: a tail of CUSTOM in-between quantities (e.g. 1,250)
    still exceeds 10% because Excard's between-tier pricing is discontinuous
    (3,250 costs MORE than 3,500). Standard order quantities are exact.
  - Curves are gitignored data rebuilt by: `python -m app.{booklet_engine 19/37, cost_engine, bizcard_engine}`
    (cost_engine/booklet expose `build_curves()`), then `python -m app.build_standalone`.
  - `output/audit_report.json` is the source of truth for the accuracy badges.
- **Delivery, price breakdown & feedback** live in BOTH UIs now. Standalone feedback
  copies a JSON to clipboard (no server); server calculator POSTs to
  `/api/printoka/feedback` → `output/feedback.jsonl`.
- **STANDALONE, NO-SERVER CALCULATOR** = `ui/calculator_standalone.html` (just
  double-click — no uvicorn, no network). All 5 formulas + calibrated params +
  option cascades are BAKED into the one file; the Python engines are ported to JS
  and **verified to match Python to the cent (12/12 configs via node)**. This is the
  primary deliverable — crawling/API are now only for occasional audit/recalibration.
  - Built by `python -m app.build_standalone` (reads params + options + accuracy,
    injects them into `ui/_standalone_template.html` → emits the standalone). **Re-run
    this after recalibrating ANY engine** to refresh the baked-in numbers.
  - Embeds: litho/digital/booklet-19/booklet-37/bizcard params; loose-21 cascade
    (from DB status='done'), digital_options, booklet_options_19/37 combos, bizcard
    cardtypes. JS engine ports live in the template (cashLitho/Digital/Booklet/Bizcard).
  - The local server (`/calculator`) still exists for the live/auto-updating flow,
    but is optional. Runtime pricing NEVER calls Excard.
- **NEW schema-driven CALCULATOR UI** at `ui/calculator.html` (served `/calculator`).
  Stripe-themed, Excard-ordering-like: product picker (cards w/ accuracy badge) →
  dynamic cascade fields → live price panel (Cash + Platinum/Gold/Silver tiers +
  per-unit + weight). **Fully API-driven & auto-updating:** it reads
  `/api/printoka/product-status` (products), `/api/printoka/schema?product=ID`
  (field cascade per product), then each field's options + the quote from the
  endpoints the schema names. Add/curate a product in `PRODUCTS_UI` +
  `FIELD_SCHEMAS` (api.py) and it appears automatically — no UI edits.
  `FIELD_SCHEMAS` families: `loose` (21/50), `booklet` (19/37), `bizcard` (1).
- **BUSINESS CARD (v4) = BUILT, calibrated & LIVE in calculator (product id 1).**
  - **NEW PLATFORM:** `v4.excard.com.my` is a different site from www (still ASP.NET
    under a new skin). Its SPA prices via a JSON API — we call it DIRECTLY (no
    browser, no member login):
    `POST https://devv2.excard.com.my/Product/CheckPrice`
    headers `Authorization: Basic ExcardAPI:EXCARDPNCAPI` + `Api-Key: RjvaNM0xSDxcKyneFhFFxek42Nrnd4FuE9rScoHQ`,
    body `{"type":"Business card","spec":[{Product,OrderDesc,Size,Orientation,Paper,
    Quantity,Package,PrintColour,Lamination,HotStamping…,RoundCorner,HolePunch,
    Embossing,Folding,Country,Courier,IsCustomSize}]}` → returns `{Price,Weight,…}`.
    Client: `app/bizcard_api.py` (`price()/check_price()/make_spec()`).
  - **Value rules (form label → API):** Size `×`→`x`, strip `(Open Size)`/`(Custom Size)`;
    Paper = strip `(…)`; Lamination exact (`Gloss Waterbase Varnish (Both)`, etc.);
    **Package N = pure ×N multiplier** (not sampled); base price uses `Lamination=""`.
    OrderDesc: `Standard/Thin Fold/Fat Fold/Custom Die-Cut/Plastic Card`.
  - **Options** (cardType→size/paper/colour) hard-listed from spec+API in
    `app/bizcard_sampler.py CARDTYPES/PAPERS`. **Sampler** `app/bizcard_sampler.py`
    calls the API directly (threaded) — 5,800 pts in ~2 min → `output/bizcard_samples.json`.
  - **Engine** `app/bizcard_engine.py`: business card is offset gang-up + best-seller
    promo pricing (q300/500/1000/5000/10000 discounted; q400/600/6000–9000 spike;
    paper cost is per-MATERIAL not ∝gsm) — a smooth formula caps ~18%. So the engine
    stores a **per-config quantity curve** (`cardType|size|paper|colour → {qty:log cash}`)
    and **log-interpolates** for arbitrary qty. **EXACT at Excard's breakpoint
    quantities (median 0%)**; held-out-quantity interpolation median **6.1%**. All
    selectable option-combos are sampled, so the dropdown quantities are exact.
    Params `output/bizcard_params.json`, KPI `output/spot_test_report_bizcard.json`.
  - **API:** `/api/printoka/bizcard/options` + `/bizcard/quote` (id 1, package ×N).
  - Recon scripts (dev): `app/bizcard_probe.py`, `app/bizcard_api_probe.py`,
    `app/bizcard_discover.py` (the form→API map capture is superseded by direct API
    probing; `bizcard_options.json` is unused by runtime).
  - **TODO (not yet):** finishing add-ons (lamination/Spot UV/hot stamping/embossing/
    round corner/hole punch/creasing) — sample on-vs-off deltas via the API and add as
    additive terms; custom-die-cut arbitrary sizes (currently nearest-size area-scaled).
- **BOOKLET (products 19 Litho & 37 Digital) = BUILT & LIVE in UI.** Full cascade
  discovered, priced by pure formula, wired into the product selector.
  - **Cascade (learned from live form):** orientation → size → ordertype(Soft/Hard)
    → binding(Saddle/Perfect) → page → **coverPaper → {coverColour, contentPaper →
    contentColour}**. KEY GOTCHA: content papers populate ONLY after a cover paper is
    chosen, and obey "cover ≥ content thickness" — so options are nested under each
    cover. Papers populate only after a page is selected. Hardcover ⇒ Perfect Binding
    only; Landscape ⇒ A4/A5 only. Saddle pages 8–80; Perfect 36–292 (soft) / 56–292
    (hard) — live form exceeds the PDF's 80.
  - **Options:** `output/booklet_options_{19,37}.json` (nested tree; 20 valid combos
    for 19, 18 for 37). Discovered via `app/booklet_discovery.py` (`probe` | `walk`).
  - **Engine:** `app/booklet_engine.py`. Physical model — `cash = margin*(setup +
    variable*qty^gamma)`, where `setup = base_setup[binding] + plate_cost*plates`
    (make-ready amortised over the run = the real volume economy) and `variable =
    p_paper*paper_kg + p_imp*plates` (per-book material + printing). Offset booklet is
    ~LINEAR in qty (gamma≈0.85–1.0); volume economy comes from amortising plates, NOT
    a steep power law. plates = cover(4 or 8 if Outer&Inner) + content_sheets×(8 for
    4C both / 2 for 1C both); content_sheets = content_pages/4.
  - **Accuracy (held-out 25% of configs):** **Digital (37) median 2.1%, 58% ≤5%**
    (gamma 0.99, flat — the achievable win). **Litho (19) median ~9.9%, 51% ≤10%**
    (offset's step/promo pricing caps a smooth formula ~8–10%, as expected). Params
    `output/booklet_params_{19,37}.json`; KPI `output/spot_test_report_{19,37}.json`.
  - **Sampler:** `app/booklet_sampler.py` + `app/booklet_capture.py` (cascade-aware).
    Capture has a **stale-price guard** (a larger qty must yield a different cash, else
    re-toggle/skip — fixes the bug where qty didn't recompute) + per-step configure
    logging. Samples: `output/booklet_samples_{19,37}.json` (~1100 pts each, all 3
    binding types). Run: `python -m app.booklet_sampler <id> <account>` (resumable).
  - **API/UI:** `/api/printoka/booklet/options` (cascade) + `/api/printoka/booklet/quote`
    (formula+tiers+weight). dashboard.html Formulation tab renders the booklet
    configurator when product 19/37 is selected; KPI badge reads spot_test_report.
  - **NOTE:** sampler is fragile to network drops (DNS) + occasional hangs — kill
    `python.exe`+headless `msedge.exe` and re-run (resumes). Two browsers on one
    laptop starve; serialize. 37 hardcover required 2 resumes after stalls.
- **Calculator UI = product-aware.** Printoka Formulation tab has a **Product selector**
  (21 Loose Sheet Litho / 50 Loose Sheet Digital) → cascade Size→Paper→Colour→Package→Qty,
  each product uses its OWN formula + shows its OWN accuracy badge.
- **UI cleaned to formula-only** (we do NOT crawl anymore). Nav = Overview, Products,
  Printoka Formulation (removed Crawl status, Pricing tables, Calculator + their views/badges).
  Overview = formula-focused (products formulated / tracked / best accuracy; no crawl bar).
  Products table columns: Combos initiated · Accuracy test result · Status (formulated /
  not formulated) — via `/api/printoka/product-status`. (Legacy views.calculator/pricing JS
  remain but are unreachable; can be deleted later.)
- **Digital Loose Sheet (50) formula = DONE & meets bar:** click-based pure formula,
  held-out **median 1.3%, 86% within 5%** (calibrated on 2,052-pt spot sample). gamma≈1.0
  (digital flat — no real volume discount). Engine: `app/digital_engine.py`,
  params `output/printoka_params_digital.json`, KPI `output/spot_test_report_50.json`.
- **Litho Loose Sheet (21) formula:** pure formula `app/cost_engine.py`, ~8% median
  (4–7% common A2–A5, 20–30% extremes; offset step-pricing limit). KPI
  `output/spot_test_report.json`. Could improve common sizes via per-size calibration.
- **API endpoints (product-aware):** `/api/printoka/products`, `/api/printoka/options?product=`,
  `/api/printoka/quote?product=&size=&paper=&colour=&qty=&package=`, `/api/printoka/kpi?product=`.
  Litho options come from OrderWork(status='done'); Digital options from `digital_options.json`.
- **Booklet source captured** in `crawler/booklet_docs/` (8 PDFs: litho+digital spec +
  saddle/perfect-bind soft/hard finishing) — ready for the next build (products 19 & 37).
- **Calibration principle (user):** OFFSET drops per-unit strongly with qty (gamma<1);
  DIGITAL stays flat (gamma≈1). Apply per product. Excard = reference only; target 3–5%.
- **GitHub:** liewyihhao/Printing-Pricing-Calculator-and-Database (branch main). Secrets
  (.env, 3 accounts + PG) are git-ignored — NOT in the repo; recreate from .env.example.

## NEXT TASK (booklet is DONE — remaining polish / next products)
Booklet (19 & 37) is fully built & live (see LATEST STATE). Remaining/optional:
- **Improve 37 tail:** median is 2.1% but MAPE ~16% — a tail of larger errors
  (likely 1C colour or extreme pages/hardcover). Add per-binding gamma or a colour
  term if tighter ≤5% coverage is wanted.
- **Improve 19 common cases:** per-binding/per-page calibration could pull common
  saddle configs under ~5% (offset extremes will stay high — accepted).
- **Finishing/add-ons** (#12) still pending for ALL products: lamination, Spot UV,
  hot stamping, embossing, folding, etc. Booklet cover finishing rules are in
  `booklet_docs/booklet_*_{LO,DO}.txt` (process days + qty≥300 gating).
- **Page×content-paper edge validity:** discovery captured cover→content sets at the
  smallest page; the live form narrows content papers as pages grow (spec tables).
  Not enforced in UI yet — the engine prices any in-range page regardless.
- **Delivery** (#13): weight×courier rate, West/East Malaysia (rates from user).
- Next products beyond booklet: see `PRODUCTS_CHECKLIST.md`.


## Goal
Build Printoka's **own offline, formula-driven** print-pricing calculator that mirrors
Excard's products (a competitor we resell). Options/combos must match Excard **exactly**;
prices are **our own formula** (Excard is a *reference only*), targeting **3–5% deviation
from Excard's CASH tier**, with **weight estimation** (±3%). Business model: Printoka runs
a website, fulfills via Excard at Gold cost (cash−8%), sells ~cash+3% → must profit per order.

## CURRENT DIRECTION (locked by user)
- **No more price crawling.** Crawled prices were **deleted** (user wants independence).
- **Pure formula** engines per product, calibrated by **spot-test sampling** (a few hundred
  prices via account, NOT a full crawl). Runtime = formula only, no price lookups.
- **Options/combos** kept (the valid combinations) and sourced via discovery (reading
  dropdowns, not prices).
- **Weight** = physics: `area_m² × gsm × qty / 1000 × 1.2065` (calibrated factor; ~85% within 3%).

## KEY DOMAIN LEARNINGS (important for the formula)
- **Offset (Litho):** plate charges (per colour×side) + parent-sheet gang-up steps +
  quantity-break discounts → **per-unit drops steeply with quantity** (volume economy).
  A pure formula caps at ~**8% median** (4–7% on common A2–A5; 20–30% on A1/A6/ganging) —
  tabular/step pricing can't be matched to 3–5% by a smooth formula. Use a LOW volume
  exponent (gamma<1).
- **Digital:** NO plates — charged per **"click" (impression) per side per sheet**.
  Cost is **~linear / flat per-unit** (e.g. A5/GlossCard230: 0.73→0.52 RM/pc from 100→1000).
  Volume exponent gamma ≈ 1.0. Digital should hit 3–5% far more easily than offset.
- Reality check given to user repeatedly: a *single pure formula* cannot reproduce offset's
  step/promo pricing to 3–5%; the data-anchored "rate card" approach hit 0.27% but the user
  chose pure formula for independence. Accept offset ~8%; digital is the achievable win.

## ARCHITECTURE (crawler/app/)
- `config.py` — env (.env): 3 Excard accounts (USERNAME[_2/_3]), PG creds, delays.
- `accounts.py` — Account registry (1=yushancorporation, 2=tkprintagency, 3=yushancompany).
  Each has its own session_state file. NOTE: on ONE laptop, accounts DON'T parallelize
  (resource limit — two headless browsers starve); only useful across separate machines.
- `products.py` — ProductTarget registry: 21=Loose Sheet Litho, 50=Loose Sheet Digital,
  19=Booklet Litho, 37=Booklet Digital (+ spec URLs).
- `browser.py` — launch (system Edge), login(username,password), session recovery.
- `order_capture.py` — reads Excard order-page prices. **Selectors are now `name$='...'`
  ends-with** so they work across Litho AND Digital (different control prefixes). Key:
  configure() (size→paper→colour→package via robust polling _select), sweep_quantities()
  (qty → double delivery-toggle → read "PRICE BEFORE DISCOUNT"). spec_url on OrderConfigSpec
  lets it target any product page.
- `cost_engine.py` — **Litho pure formula** (per-piece paper×gsm + ink×plates, fixed
  plates/setup, volume exponent gamma). Calibrate: `python -m app.cost_engine`. Params →
  output/printoka_params.json.
- `digital_engine.py` — **Digital pure formula** (click-based, SRA3 gang-up, gamma≈1).
  Calibrate: `python -m app.digital_engine` (needs output/spot_samples_50.json).
  Params → output/printoka_params_digital.json.
- `spot_sampler.py` — collects stratified price samples for calibration (no full crawl).
  `python -m app.spot_sampler 50 1` samples Digital via account 1.
- `formulation.py` — weight (physics) + tier helpers (data-anchored price path is now
  unused since prices deleted; weight/tiers still used).
- `order_discovery.py` — cascade option discovery (enumerate valid combos / mark validity).
  `discover_and_mark(product_id)` marks valid combos status='done' (options only, no prices).
- `api.py` — FastAPI. `/api/order/options` (cascade from OrderWork status='done'),
  `/api/printoka/quote` (pure formula + weight), `/api/printoka/kpi` (spot-test report).
  Serves `ui/dashboard.html`. Run: `python -m uvicorn app.api:app --port 8000`.
- `ui/dashboard.html` — Stripe-styled SPA. Tabs: Overview, Products, Pricing, Calculator,
  **Printoka Formulation** (the formula-driven pricing UI), Crawl status.

## DATABASE (PostgreSQL `printoka`, PG18, pw in .env)
- `OrderWork` (4400 rows) — the COMBOS: size/paper/colour/package/status. status='done' =
  valid combo (the kept option set). **OrderQuote (prices) was DELETED** — empty.

## STATUS
Done: Litho options + pure formula + KPI (8% median, honest); weight model (physics, ~3%);
full Litho + Digital + Booklet option structures gathered (PDFs + live site); Digital price
reading unblocked; Digital spot-sampler built and RUNNING.
Pending tasks (see TaskList / below):
- **#15 Digital formula calibration** — spot sample running (output/spot_samples_50.json,
  ~56 configs/~2000 pts, incremental). When done: `python -m app.digital_engine` → report
  held-out accuracy; then register product-50 options + add Litho/Digital selector to UI.
- **#12 Finishing/add-ons** — full cascade per product (lamination, folding Standard/Custom,
  hot-stamping size+foil+areas, round corner, hole punch, perforation, creasing, envelope).
  Rules in PDFs (pdf_flyer_LO.txt, pdf_flyer_finishing.txt, pdf_flyer_digital.txt). "Mix not
  allowed" for fold/crease/perf/holepunch.
- **#13 Delivery** — West/East Malaysia (weight × courier rate, user to provide rates).
- **#14 Booklet — TWO products: Litho (19) + Digital (37).** Deep cover/content configurator
  with ASYNC-loading dropdowns (must poll). Live URLs: /spec/Litho/Booklet, /spec/Digital/Booklet.
  Dimensions (from booklet_structure.txt): Orientation, Size(A4/A5/B5/A6/B5+), Page count
  (depends on cover+binding: SaddleStitch 8-80, PerfectBinding 36-292), Cover Type (Soft/Hard),
  Binding (Saddle Stitch / Perfect Binding), Cover paper+print colour+hot stamping,
  Content paper+print colour, Outer/Inner (rbOuterInner OO/OI), + extras (chkExtraQty,
  Jawi/Quran, rush). SOURCE DOCS (full text) in **crawler/booklet_docs/**:
  booklet_litho_spec.txt, booklet_digital_spec.txt, booklet_{saddle,perfbind_softcover,
  perfbind_hardcover}_{LO,DO}.txt — read these for exact papers/binding/page/finishing rules.
  TODO for new chat: (1) full option discovery for products 19 & 37 (poll the cascade),
  register combos + wire into UI product selector; (2) build pricing — note Booklet price
  scales with PAGE COUNT (content sheets) + cover + binding; offset booklet has volume
  economy (gamma<1), digital booklet flatter (gamma~1) — same offset-vs-digital principle;
  (3) spot-test sample (sufficient size) + calibrate per binding type + validate to 3-5%;
  finishing shared with offset/digital loose sheet. Combo space is large -> sample smartly.
- Litho **per-size calibration** to pull common sizes to ~5% (user to confirm).

## REFERENCE FILES (in crawler/)
PRODUCTS_CHECKLIST.md, DIGITAL_LOOSE_SHEET_NOTES.md, DIGITAL_LOOSE_SHEET_RUNBOOK.md,
digital_options.json, booklet_structure.txt, pdf_flyer_LO.txt, pdf_flyer_finishing.txt,
pdf_flyer_digital.txt, pdf_*.txt.

## HOW TO RUN (new chat)
1. `cd crawler` ; venv at `.venv`.
2. Web UI: `.venv\Scripts\python.exe -m uvicorn app.api:app --port 8000` → http://localhost:8000
3. Calibrate Litho: `.venv\Scripts\python.exe -m app.cost_engine`
4. Calibrate Digital (after sampling): `.venv\Scripts\python.exe -m app.digital_engine`
5. More spot samples: `.venv\Scripts\python.exe -m app.spot_sampler <product_id> <account>`

## NEXT IMMEDIATE STEP
Wait for `output/spot_samples_50.json` to finish populating (sampler running), then run
`python -m app.digital_engine` and report held-out accuracy (expect closer to 3–5% due to
digital linearity). Then wire product-50 into the UI (product selector) + per-product KPI.
