# CONTINUE: Printoka — full option parity, sub-configs, and customer pages

_Paste the PROMPT block (bottom) into a new session. Branch
`feat/business-card-standalone-calculator`, work in `crawler/`, venv `.venv\Scripts\python.exe`.
Prefix every shell command with `cd /c/Users/User/OneDrive/Desktop/Printoka.com/crawler &&`._

## Where things stand (2026-07-13)
The calculator is **93 products, 83 exact-priced**. Beyond exact pricing, the project standard is
now **full option parity** — our UI must expose EVERY option the source order form (excard) offers,
including price-neutral ones, and price every relationship correctly. That pass is essentially done:
the value-level diff (`app/parity_values.py`) converges to **0 genuine gaps** (remaining flags are
format false-positives), and `app/menu_scan.py` confirms our 93 cover all **78** live menu products.
All work is committed + pushed (latest `f283e89`).

## THE METHOD (proven; reuse it)
Every excard order page prices via `POST https://devv2.excard.com.my/Product/CheckPrice`
(static Basic-auth + Api-Key + logged-in session cookie). **Gotchas:** capture ONE real request to
learn exact `type` + spec value formats; **CheckPrice is NOT concurrency-safe → workers≤2** and use
Theil-Sen repair (see memory `checkprice-concurrency-corruption`). Helpers: `app/checkprice_enum.py`,
`app/cp_repair.py`, per-product samplers (`billbook_cp_sampler`, `kadkahwin_sampler`, …).

## Tooling built this session
- `app/option_audit.py` — enumerate every control on a v4 `/ordering/<slug>` page (DOM order,
  sections, options). `app/www_audit.py` — same for products whose v4 page 500s (uses www `/spec`).
  Corpus in `output/option_audit/<slug>.json`.
- `app/parity_values.py` — value-level diff: per product, which excard option VALUES are missing
  from our fields. `app/menu_scan.py` — scrape the live mega-menu + diff vs our products.
- `app/build_specs_page.py` → `ui/specs.html` — SEO customer page listing every product's spec.
- `app/build_packaging_standalone.py` → `ui/packaging_standalone.html` — 67-style 3D box configurator.

## Engine mechanisms in `app/build_standalone.py` (+ `ui/_standalone_template.html`)
All keyed by product id; rebuilt into the field list by `_wire_pricelist_products`:
- `_NEUTRAL_FIELDS` — extra UI fields (present, not price axes). Supports `type:"number"` + `showWhen`.
- `_CONTACT_WHEN` / `contactWhen` — expose an option but return "price on request" (combinatorial /
  different sub-product; e.g. Bill-Book Normal paper, Business Card Thin Fold).
- `_ADDON_DELTAS` / `addonDeltas` — exact additive finishing cost sampled independently, scaled by
  qty (and package). Used for Business Card hole-punch + embossing; curve files
  `output/bizcard_holepunch_delta.json`, `output/bizcard_embossing_delta.json`.
- `_EXTRA_AXIS_OPTIONS` — inject excard option VALUES we lack price data for into an axis field +
  auto contactWhen (e.g. Loose-Sheet 1C colours, gang sizes, Magnet Multiple Dieline, custom sizes).
- `showWhen` (template) — a field appears only when a parent field has certain values (hot-stamping
  foil colour + area shown only when hot stamping selected).
- `_CONFIGURATORS` / `configuratorUrl` — product opens a separate tool instead of a form
  (Kotak Cenderahati → `packaging_standalone.html`).
Always `python -m app.build_standalone` after edits, then `python -m app.build_specs_page`.
**Verify:** load `output/calculator_engine.cjs` in node, sample curve keys cent-exact, `accuracy===0`,
and `grep -io excard output/calculator_data.json ui/calculator_standalone.html output/calculator_engine.cjs`
returns nothing.

## Hot-stamping / embossing findings
- **Hot stamping** (all products tested): block/foil is **quoted separately → price-neutral online
  (0%)**. Expose the sub-dropdowns for parity: side (1C/2C F/B), **foil colour** (Business Card Gold/
  Silver; Kad Kahwin 6 colours), **area W×H** (mm number inputs). Done for Business Card + Kad Kahwin
  ONLY — still to do: folder, money packets, greeting card, and any other product whose CheckPrice
  spec has `HotStamping*`/`Embossing*` fields.
- **Embossing** (Business Card): **priced** (~+RM52.50/run min, scales qty×package) → addonDelta.
  Its area W×H is the neutral spec detail. Re-check embossing pricing for OTHER products before
  assuming neutral.

## Open items / next
1. **Extend hot-stamping/embossing sub-configs** (foil colour + area, and embossing pricing) to the
   remaining products that have them (folder, money packets, greeting card, …). Same pattern as
   Business Card / Kad Kahwin. Rebuild + regenerate specs page.
2. **1C Loose Sheet Litho exact price** (currently "on request"). No CheckPrice API (v4 500s); must
   crawl the www `/spec/Litho/Loose_Sheet` form. Key facts learned: colour/package/envelope are
   `<select>`s named `rblPrintColourSide` / `rblPackage` / `rblEnvelope`; controls are progressively
   disclosed (colour/lamination appear after size+paper); `_read_price` (from `sticker_capture`)
   reads the rendered price and 4C reads matched our data to the cent. Unresolved: 1C selections
   returned `0.0` in the last probe (investigate — may need a settle/postback wait or the price only
   updates after a valid full config incl. lamination). Aliases 101/102/103 share the fix.
3. Minor: `www_audit` URL guesses missed desk-calendar-hard/soft, mask-keeper (contact anyway),
   sublimation (audit via v4 slug `shirt`). Fix URLs if you want their corpus complete.

## Standards
- Serve the UI: `python -m http.server 8030 --directory ui` (or launch.json `printoka-calc-static`).
  `ui/index.html` is the Stripe-styled workspace landing; `calculator_standalone.html` is 21 MB and
  strains the browser's screenshot capture — reload with `?v=N` to bust cache; verify pricing in node.
- Commit per product/feature; end messages with
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Push when done.
- **Proceed autonomously** — don't ask permission for routine samplers/probes/rebuilds/commits/pushes
  (memory `proceed-without-permission-prompts`). Only surface genuine decision forks.
- Read memories first: `completion-requires-full-option-parity`, `checkprice-concurrency-corruption`,
  `excard-readymade-pricing-api`, `proceed-without-permission-prompts`.

---

## PROMPT (paste this into the new session)

```
Continue the Printoka project (repo github.com/liewyihhao/Printing-Pricing-Calculator-and-Database,
branch feat/business-card-standalone-calculator, work in crawler/, venv .venv\Scripts\python.exe;
prefix every shell command with: cd /c/Users/User/OneDrive/Desktop/Printoka.com/crawler &&).

STEP 0: Read crawler/CONTINUE_PARITY.md IN FULL and the memories
'completion-requires-full-option-parity', 'checkprice-concurrency-corruption',
'excard-readymade-pricing-api', 'proceed-without-permission-prompts'.

CONTEXT: The calculator is 93 products, 83 exact-priced. Full OPTION PARITY vs excard is essentially
done (parity_values.py = 0 genuine gaps; menu_scan.py = all 78 menu products covered). Engine
mechanisms exist for neutral fields, price-on-request (contactWhen), additive finishing deltas
(addonDeltas), extra axis options, conditional visibility (showWhen), and configurator links.
CheckPrice is NOT concurrency-safe: sample at workers<=2 and repair with Theil-Sen.

DO NEXT (proceed autonomously; commit per product; push when done):
1. Extend hot-stamping/embossing SUB-CONFIGS (foil colour + area W×H via showWhen, price-neutral;
   embossing may be a priced addonDelta) to remaining products that have them — folder, money
   packets, greeting card, etc. Pattern = how Business Card (1) and Kad Kahwin (114) were done in
   app/build_standalone.py (_NEUTRAL_FIELDS + _ADDON_DELTAS). Verify each via the API, rebuild
   (python -m app.build_standalone), regenerate the specs page (python -m app.build_specs_page),
   confirm 0 'excard' leakage.
2. Then attempt exact 1C Loose Sheet Litho pricing via a www /spec/Litho/Loose_Sheet crawl (see
   CONTINUE_PARITY.md item 2 for what's known); if it stays impractical, leave it on-request.

Verify with node output/calculator_engine.cjs (cent-exact, accuracy===0) and no 'excard' leakage.
End commit messages with Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>.
```
