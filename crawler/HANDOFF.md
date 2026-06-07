# Printoka Pricing Calculator — Project Handoff

_For continuing in a new Claude Code chat. Read this first._
_Raw link: https://raw.githubusercontent.com/liewyihhao/Printing-Pricing-Calculator-and-Database/main/crawler/HANDOFF.md_

## ⭐ LATEST STATE (most recent first)
- **Calculator UI = product-aware.** Printoka Formulation tab has a **Product selector**
  (21 Loose Sheet Litho / 50 Loose Sheet Digital) → cascade Size→Paper→Colour→Package→Qty,
  each product uses its OWN formula + shows its OWN accuracy badge.
- **Crawl UI removed** (no Crawl-status tab, no crawl-status calls, no prices badge). App
  opens on the Formulation view. We do NOT crawl anymore.
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

## NEXT TASK (Booklet — products 19 Litho & 37 Digital)
Read `crawler/booklet_docs/*.txt`. Discover all options (poll async dropdowns), put in the
UI product selector, spot-sample sufficiently, calibrate per binding type (Saddle Stitch /
Perfect Binding soft/hard), validate to 3–5%, make live in preview. Booklet price scales with
PAGE COUNT (content sheets) + cover + binding; offset gamma<1, digital gamma≈1.


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
