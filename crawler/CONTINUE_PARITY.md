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
1. **Hot-stamping/embossing sub-configs — DONE / non-task (verified 2026-07-13).** Every product
   that GENUINELY has hot stamping / embossing / deboss on Excard already exposes it; the
   "folder / money packets / greeting card still to do" claim above was a FALSE POSITIVE from
   `option_audit` (it dumps the shared v4 template, so `ddlHS`/`ddlDeBoss*`/`ddlCoverHotStamping*`
   appear hidden on ~42/53 products). Ground truth (captured CheckPrice spec keys / metrics cols,
   see `app/_hs_probe.py`):
   - Money Packet: only the **Hot Stamping** variant (168) has it, already a priced `finishing`
     axis (Gold Both / Front-Back; cent-exact vs `hotstamp_mp_pl_params`). Standard (138) /
     Premium (167) / Envelope (169) have NO hot stamping.
   - Wire-O Notebook (112) `hotstamping` axis; Perfect Bind Notebook (164) `hotstampingcolour`
     axis; Leather Wire-O (163) `deboss`+`deboss H/W` axes; Booklet (19/37) `cover_embossing`+
     `hot_stamping` fields. All already exposed.
   - Folder (107), Greeting Card (166), Kad Terima Kasih (115), Creative Cut Card (165) etc. have
     NO hot stamping. See memory `hotstamp-emboss-parity-complete`.
2. **1C Loose Sheet Litho exact price — BLOCKED, stays on-request (investigated 2026-07-13).**
   Exact 1C prices DO exist in `output/spot_samples_21.json` (190 pts 1C Front, 243 pts 1C Both,
   all non-zero — the old "returned 0.0" issue is gone). BUT `spot_samples_21.json` is on a
   DIFFERENT price scale from the shipped `loosesheet_plx_params.json` (the current 393 4C curves):
   overlapping 4C points match at low qty but diverge up to ~1.16× at high qty, with some ratios
   as low as 0.16 — i.e. the two captures are incompatible (different epoch/field/ganging), so 1C
   from `spot_samples` CANNOT be grafted onto the 4C params without mispricing. Worse, the source
   that built the current `loosesheet_plx_params.json` is not reproducible in-repo (no builder
   script, no source CSV in `output/`). Getting consistent exact 1C requires a FRESH full
   `order_capture` re-crawl of the whole size×paper×lamination grid for BOTH 1C and 4C (thousands
   of configs, hours, session-recycling) — a large, risky, separate effort (would re-touch
   shipped-exact 4C). Left on-request per the "impractical → on-request" fallback.
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
