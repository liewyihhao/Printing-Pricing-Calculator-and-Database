# Printoka Pricing Calculator — Project Handoff

_For continuing in a new Claude Code chat. Read this first._
_Raw link: https://raw.githubusercontent.com/liewyihhao/Printing-Pricing-Calculator-and-Database/main/crawler/HANDOFF.md_

## ⭐ LATEST STATE (most recent first)
- **52/52 BUILT. PARITY PERFECT: 0 REAL GAPS (2026-06-29 scheduled run).**
  Last deferred gap (Wire-O Exclusive Leather Cover) is now CLOSED:
  - Added "Exclusive Leather Cover" to wireo `cover` options in FIELD_SCHEMAS (api.py),
    build_standalone.py, and the standalone template. Quote endpoint returns a clear
    "price quoted separately — contact us" message for this premium specialty cover
    (no headless pricing data available; handled gracefully as a "quoted separately" item).
  - Standalone JS throws the same message before computing. Note updated to remove
    "Soft/Leather covers pending." text.
  - `parity_checker wireo` now shows **0 gaps**. `parity_checker --print` total: **0 real
    gaps across all 44 checked families**. This is the first fully-clean parity run.
  - Standalone rebuilt. Commit pushed.
- **52/52 BUILT. PARITY STABLE: 1 REAL GAP (DEFERRED). PUBLIC API IMPROVED (2026-06-29).**
  Scheduled-task run. No new parity gaps found (parity_checker --print confirmed 1 deferred:
  Wire-O Exclusive Leather Cover). Two commits pushed:
  1. **public_api.py bizcard validity cascade** — `_detail()` now emits a `validity` block
     for business card: `{"primary":"cardType","fields":["size","paper","colour"],"rules":{…}}`
     mapping each cardType label to its valid sizes/papers/colours. Also injects dynamic
     options into bizcard fields that previously had `options:null`. External websites using
     the public API now get the full cascade without a separate options endpoint call.
  2. **Web frontend** — committed the pending Printoka.com Next.js pages: home (hero +
     popular products + how-it-works + testimonials + FAQ + CTA), products listing +
     per-product configurator, cart/checkout/auth/account stubs, templates, order tracking,
     SEO files (robots.ts, sitemap.ts, JSON-LD structured data), Footer component, and
     pricing-api.ts fix for `array vs {products:[]}` response shape. 31 files, 2660 insertions.
  Both commits pushed to feat/business-card-standalone-calculator.
- **52/52 BUILT. PARITY CHECKER EXPANDED TO 44 FAMILIES: 1 REAL GAP (2026-06-27 run 2).**
  Added `booklet_digital` (https://www.excard.com.my/spec/Digital/Booklet) to FAMILY_URL
  in parity_checker.py. Digital Booklet uses the same FIELD_SCHEMAS family as Litho Booklet;
  handled via new `FAMILY_ALIAS` dict in parity_checker.py. Result: 0 gaps — Digital booklet
  form is fully covered by existing schema. Parity checker now also merges subset results into
  the existing report (no longer overwrites the full report when running a single family).
  parity_report.json updated: 44 families, 1 real gap (Wire-O Exclusive Leather Cover, deferred).
- **52/52 BUILT. PARITY CHECKER EXPANDED TO 43 FAMILIES: 1 REAL GAP (2026-06-27).**
  Parity checker now covers 43 families (was 37). 2 real gaps found and closed:
  - **Stamp Chop ink colour** — `ddlColour` (Red/Black/Blue/Violet/Green/Brown/Pink/Orange/
    Yellow/Sky Blue) was not in FIELD_SCHEMAS. Ink colour is price-neutral for stamps.
    Added as a selectable "Ink Colour (no price change)" field in api.py, build_standalone.py.
  - **Wire-O Wall Calendar rblPunchHole** — single-option "Not Required" display artifact
    (hole punch is compulsory/included in the fixed spec); suppressed in `FAMILY_IGNORE["wireow"]`.
  New families added to FAMILY_URL: `deskcal_soft`, `wireow`, `mug`, `pillow`, `archfile`,
  `stamp_chop`. mask_keeper and sublimation_shirt skipped (quote-only, no headless form).
  parity_report.json updated. Standalone rebuilt with ink_colour for stamp_chop.
  papan_kopi shows a page.evaluate crash (known headless nav issue) — not a real gap.
- **52/52 BUILT. PARITY CHECKER EXPANDED TO 37 FAMILIES: 1 REAL GAP (2026-06-26 run 2).**
  Parity checker now covers 37 families (was 20). 5 real gaps found and closed:
  - **Bunting Synthetic Paper 180micron** — added to paper options in FIELD_SCHEMAS, api.py,
    build_standalone.py. `bunting_engine.cash_price` now returns 0.0 (not wrong fallback) for
    unsampled materials; `bunting_quote` returns "not yet priced" error for Synthetic Paper.
  - **Magnet shape rename + Multiple Dieline** — "Custom Die-Cut" renamed to "Custom Die-Cut
    (with round corner)" (Excard's exact label). "Multiple Dieline" added as shape option that
    returns "not yet priced". Alias map in `magnet_quote` + standalone JS handles translation.
  - **Paper Bag lamination + rope colour** — `rblLaminationSide` (Gloss/Matte Front) and
    `rblRopeColour` (Black/Blue/Red/White/Gold) added to FIELD_SCHEMAS. Both are no-online-
    price-change per sampler notes; quote endpoint accepts them as pass-through params.
  - **Standing Pouch Transparent Pet Film** — added to paper options; `pouch_quote` returns
    "not yet priced" for unsampled materials.
  - **Wobbler rblRoundCorner** — false positive (Round Corner + Custom Die-Cut already in
    our `finishing` field); fixed KEYWORD_FIELDS `"corner" → ("corner", "finishing")`.
  - **Magnet rdType=Magnet** — false positive (constant form-nav radio); suppressed via
    `FAMILY_IGNORE["magnet"] = ("rdtype",)` in parity_checker.py.
  - **Standalone simpleqty JS**: now throws "not yet priced" instead of silently falling back
    to first curve when selected variant has no sampled data.
  - All 37 checked families now at 0 real gaps. Wire-O Exclusive Leather Cover remains the
    1 known deferred gap (cfg_fails headless). parity_report.json updated.
- **52/52 BUILT. PARITY CHECKER: 1 REAL GAP (2026-06-26 run 1).** Two minor gaps found and closed:
  - **PVC Card orientation** — `ddlSizeOrientation` (Portrait/Landscape) was missing from FIELD_SCHEMAS.
    Orientation is price-neutral (already verified in pvccard_sampler). Added as a selectable field with
    "no online price change" label in api.py, build_standalone.py; standalone rebuilt.
  - **Folder mould group** — `rblMouldGroup` (Presentation/Document/Key/CD Jacket grouping radio) not
    in FIELD_SCHEMAS. Our flat `model` field covers all individual moulds across all groups, so this is
    a parity-checker false positive. Fixed by adding "mould" → ("model",) to KEYWORD_FIELDS in
    parity_checker.py. Also added "orient" → ("orientation",) for future orientation controls.
  - parity_report.json updated: **1 total gap** (Wire-O Exclusive Leather Cover, known headless-deferred).
    All other 20 checked families at 0 gaps.
- **52/52 BUILT. PARITY CHECKER SHOWS 0 REAL GAPS (2026-06-25 session 2).** All 52 Excard catalogue
  products are built and verified. Improvements this session (all committed + pushed):
  - **Loose Sheet Litho finishing consistency** — api.py now applies hot_stamping/fold/punch finishing
    to litho (product 21/101/102/103) matching the standalone. Also added finishing fields to the `loose`
    FIELD_SCHEMAS in api.py. The finishing dataset is shared with digital (loose_finishing_50.json).
  - **Folder CD Jacket accuracy improved** — `pricelist_engine.build_params` now supports
    `average_dupes=True`. Folder params rebuilt with averaging: CD Jacket median error 2.4% → 1.2%
    (Excard's CSV has a hidden option not exported as a column; averaging halves the expected error).
    PF/DF/KF mould groups remain 100% exact.
  - **Chrome extension still wedged** (navigate hangs after 300s). No new CSVs could be downloaded.
    Next session: ask user to reload/re-pair the Chrome extension before attempting CSV exports.
- **WEIGHT FIXES + STALE NOTE CORRECTED (2026-06-25).** folder_quote, letterhead_quote, and
  pvccard_quote were returning `weight_kg: 0.0` — now fixed with proper estimates:
  - **Folder** ~40g/piece (A4 folder open area × 250gsm + lamination)
  - **Letterhead** uses actual A4 gsm from paper name (`0.210×0.297×gsm×qty`)
  - **PVC Card** 5.6g/card (CR80 standard)
  - unit_wt added to folder_pl_params, letterhead_pl_params, pvccard_pl_params so the standalone also
    computes correct weights via the pricelist engine branch.
  - Stale notepad API note fixed: "Spot UV does not change price" → "Spot UV adds a cost delta" (the
    delta was added in the CONTINUE_REBUILD fix but the note was not updated).
  - Chrome extension still wedged — navigate hangs; no new CSVs could be downloaded this session.
- **EXACT REBUILD FROM v4 PRICE-LISTS IN PROGRESS — see `CONTINUE_REBUILD.md`.** An audit found the
  original www-form sampling had **silent option-select failures**, so several priced options were
  wrongly modelled as "no price change" (root cause). We now rebuild affected products EXACTLY from the
  authoritative v4 price-list CSV exports. **New generic `app/pricelist_engine.py`** + a generic
  `"pricelist"` standalone JS branch do exact config-lookup with qty interpolation. **Notepad (104)
  fixed** (Spot UV is priced) and **Folder (107) fully rebuilt exact** (all mould groups + print colour
  + 8 laminations + protective layer; 692 config curves). CSVs live in `output/v4_pricelists/`. Next:
  re-verify every remaining "neutral/quoted-separately" claim across products by downloading more v4
  CSVs (needs working browser). Products rebuilt so far: Notepad (delta), Folder, Letterhead, PVC Card,
  Money Packet Standard, Non-Woven Bag, Papan Kopi, Tent Card, Stamp Chop (flat unit prices).
  Chrome extension paired; user logged into v4 (acct 142059498); downloads enabled for v4.excard.com.my.
- **43/52 BUILT.** Added **Bunting (124)** and **Wobbler (126)** by fixing what blocked them
  (found via new `app/autoconfig_probe.py`, which auto-configures every control and reports
  the price + any still-empty required field):
  - **Bunting**: price was RM0 because `ddlColourProtective` (fitting: Wood / PVC Pipe /
    Wood+Wire — a real price driver) was unset AND resets on qty change. Sampler re-applies it
    per qty; built on simpleqty (size|paper|fitting), Tarpaulin 300gsm, 9 variants, LOO 2.81%.
    Synthetic Paper deferred (renders 1 pt headless).
  - **Wobbler**: compulsory `rblLaminationSide` resets per qty — re-applied per qty; 8
    orient×paper×lam curves via its own engine, LOO ~4.3%.
  - **REMAINING 9 — confirmed not headless-buildable:**
    - *No online price table at all (quote-only products):* **Money Packet, Non-Woven Bag,
      Mask Keeper** — `price_table=false`, no qty/spec controls. Not buildable (no price to read).
    - *Price table exists but won't compute headless:* **Papan Kopi / Sachet Board** —
      size+qty set but price cell stays empty (dynamic-qty / bestseller hidden-field quirk).
    - *Complex configurators / interactions:* **Tent Card** (size template), **Sublimation
      Shirt** (model/sleeve/fabric quote), **Stamp Chop + Pre-Inked Stamp** (shape→model→per-
      line), **Wire-O Exclusive Leather** cover (cfg_fail headless).
    These need a non-headless / scripted-interaction pass (or simply have no online price).
- **41/52 BUILT.** New this session via a reusable generic engine `simpleqty_engine`
  (per-variant log-log qty curve; params in `output/<tag>_params.json` as
  `{curves,variant_field,unit_wt,note}`; one JS branch `engine:"simpleqty"`,`paramKey` in
  the template; `variant_field` may be a string or a list → composite "a|b" key):
  - **Button Badge (132)** qty curve, lamination neutral. **Hand Fan (133)** per-paper.
  - **Hanger (134)** per (paper × colour). **Magnet (135)** per shape (Soft Touch +~RM4).
  - **Hard Cover Menu (136)** per (order × add-content); Cover-only aliased across add-content.
  - **Standing Pouch (137)** Metalised Pet Film only (Transparent deferred — stale headless reads).
  - **KEY SAMPLER INSIGHT:** these Digital forms reset compulsory selects (lamination, and
    for hanger print colour) on every qty change, so price reads RM0 unless those fields are
    re-applied AFTER qty. `gifts_sampler._sweep_qty(..., reapply=[(name,val),...], lam_field=)`
    handles it. Reusable triage: `app/batch_formdump.py` (one login, many /spec dumps).
  - **STILL UNBUILT (11), all genuinely hard headless:** Tent Card, Bunting, Wobbler,
    Papan Kopi, Money Packet, Mask Keeper, Non-Woven Bag (empty cascade), Sublimation Shirt
    (complex model/sleeve/fabric quote), Stamp Chop + Pre-Inked Stamp (shape→model→per-line
    configurator), Wire-O Exclusive Leather cover. Need a non-headless / deeper-interaction pass.
- **TASK B PROGRESS — Arch File + Pillow + Desk Calendar finished; 3 deferred.**
  - **Arch File (id 119) BUILT** — flat RM5.00/unit qty curve (LOO 0%), fixed spec
    (steel binding + wire-O + corners + lamination all compulsory). Full pipeline, JS==Python.
  - **Pillow (id 131) BUILT** — had 19 samples but no params; built params (LOO 0.03%), JS==Python.
  - **Desk Calendar Hard Stand (id 120) FIXED** — prior curve had stale-read plateaus; rewrote
    the sampler read to poll until the price changes off the previous qty. cat3 (Hot Stamping)
    clean; cat1/cat2 (WDCH Portrait/Landscape) keep genuine Excard caps (confirmed real — same
    code samples cat3 cleanly). LOO 1.12%, JS==Python.
  - **Empty-params guard in build_standalone** — `_drop_unsampled()` hides any product whose
    engine params have no sampled curve (avoids RM0 in the shipped UI; auto-reappears once
    `*_params.json` is populated). Currently hides 124/126/130.
  - **DEFERRED (headless-hard, like Tent Card): Bunting (124), Wobbler (126), Papan Kopi (130).**
    Samplers were made robust (dynamic qty opts + change-poll read) but the Excard forms render
    NO price headless (0–1 points; papankopi even times out navigating). Engines/api/scaffold
    exist; they just need a non-headless sample pass. They are hidden from the standalone.
  - Note: live api PRODUCTS still lists 124/126/130 (quote returns a graceful "no price" error).
- **PARITY GAPS CLOSED (7 → 1).** `parity_checker` now reports just **1 real gap**:
  Wire-O **Exclusive Leather Cover** — genuinely deferred (cfg_fails headless: its cover
  lamination dropdown is unreadable, same class as Tent Card). Closed this session:
  - **PVC Card VDP** (id 113): Variable Data Printing (Front) is a priced add-on
    (+RM40@100, +RM130@1000). Sampled the delta → `vdp` finishing delta in `pvccard_engine`
    + `vdp` field in schema/standalone. JS==Python exact.
  - **Wire-O Soft Cover** (id 112): sampler now falls back to the cover's first available
    lamination (Soft Cover → Matte Both) when the Matte-Front reference is absent; captured
    full qty curve, wired into schema/standalone. JS==Python exact.
  - Booklet `rdbidning` was a **checker false positive** (our `binding` is a dynamic cascade
    field; Excard control is misspelled) — suppressed via KEYWORD_FIELDS in `parity_checker`.
  - bookmark / billbook / sticker_digital flags were **transient deep-configure reads** (gone
    on re-run); bookmark RC/HP are Yes/No toggle noise (engine already applies the deltas).
  - billbook "Normal Paper" (non-NCR variant) noted as a deferred sub-system if it recurs.
- **OPTION-PARITY CHECKER (NEW) — `app/parity_checker.py`.** Deep-configures every built
  product's live Excard form (reveals all dependent/finishing controls), captures EVERY
  option, and diffs vs our FIELD_SCHEMAS → `output/parity_report.json` (served at
  `/api/printoka/parity`). Run: `python -m app.parity_checker [family ...]` or `--print`.
  Flags missing fields + missing option values (ignores Out-of-Stock, "Others" custom-size,
  per-ply NCR tint dropdowns, VDP text sub-options, nav). **This caught real misses my
  www-only dumps skipped.** Fixed so far: **Kad Kahwin + Kad Terima Kasih now offer
  Lamination (Matte/Gloss × Front/Both) + Kad Kahwin Envelope (White/Pink)** — VERIFIED
  price-neutral online (added as selectable fields with a "no online price change" note;
  `output/kad_finishing.json`). Both now show 0 gaps. **REMAINING real gaps to close
  (see report): Folder cover lamination, Bookmark lamination, PVC Card VDP sub-system,
  Wire-O Soft/Exclusive-Leather covers (deferred).** The recurring scheduled task
  `printoka-build-all-products` now runs the checker and closes gaps before building new ones.
- **OPTION IMAGES (thumbnails) — matches Excard.** Where Excard shows image-based options,
  the calculator now renders a thumbnail grid instead of a dropdown. Map is
  `output/option_images.json` ({family:{field_key:{option_label:image_url}}}, **must be UTF-8**
  — labels contain em-dashes), hotlinked from Excard (`/images/member/order_env/*`,
  `/order_folder/*`). api.py `_attach_option_images()` injects `images` into the matching
  schema field; both UIs render `renderImageGrid()` (clickable cards) for any field with an
  `images` map; `build_standalone._attach_images()` bakes them in (engine→family map).
  Currently wired: Envelope moulds (17) + Folder moulds (6). Packaging already had images.
  To add more: capture the option image URLs and extend `option_images.json`.
- **BUILDING ALL 52 — batch in progress.** Map of every catalogue product → its `/spec`
  order form saved at `output/spec_link_map.json` (most catalogue "products" are marketing
  pages funnelling into a shared spec form). Reusable form dumper: `app/formdump_url.py`.
  - **Brochure / Flyer / Customprint (ids 101/102/103)** = pure aliases of Loose Sheet Litho
    (their order page IS `/spec/Litho/Loose_Sheet`) — surfaced as products reusing the litho
    engine/options/standalone. Accuracy = loose-litho 1.7%.
  - **Wall Calendar — Litho (id 118) BUILT.** Fixed spec (260×265mm, Boxboard backing +
    Simili 60gsm 12-sheet content, Folding + Side Stitching compulsory). Qty-only curve
    (log-log), LOO median 1.7%. Sampler `app/wallcal_sampler.py`, engine `app/wallcal_engine.py`.
    Wired everywhere; JS==Python. (Desk Calendar Hard/Soft Stand at /spec/Litho/
    Desk_Calendar_(Hard_Stand)/(Soft_Stand) + Wire-O Wall Calendar still pending.)
  - **Static Cling Window Sticker (id 116) + Car Sticker (id 117) BUILT** (one engine, two
    products — same Excard form `/spec/Digital/Static_Cling_Window_Sticker`). Drivers: Size(10)
    × Qty × Print direction (Face Out=Face In; Both Side ≈1.5×) + VDP. Engine
    `app/staticcling_engine.py` = reference qty curve (log-log) × qty-interp size/direction/vdp
    factors. core LOO 5.9%, axes exact. Sampler `app/staticcling_sampler.py`. Wired everywhere; JS==Python.
  - **Kad Terima Kasih — Digital (id 115) BUILT.** Thank-you gift tag. Size(3) × Paper(6;
    Vellum OOS) × Colour(4C Front/Both) × Qty + Hole Punching (3mm). Engine
    `app/kadterima_engine.py` = reference qty curve (log-log) × qty-interp size/paper/colour
    factors + hole-punch delta. core LOO 4%, axes exact. Sampler `app/kadterima_sampler.py`.
    Wired everywhere; JS==Python.
  - **Kad Kahwin — Digital (id 114) BUILT.** Wedding card. OrderType(Standard / Custom
    Die-cut) × Size(7) × Paper(10; Vellum OOS) × Colour(4C Front/Both) × Qty + folding/hot
    stamping (block). Engine `app/kadkahwin_engine.py` = reference qty curve (log-log) ×
    qty-interp size/paper/colour/ordertype factors (exact at q100/q500). core LOO 3.1%, axes
    exact. Sampler `app/kadkahwin_sampler.py`. Wired everywhere; JS==Python.
  - **TENT CARD (Litho/Tent_Card) DEFERRED.** Fixed size/paper/colour; price stays RM0 with
    just lamination+qty set — the form needs an unidentified extra interaction (likely a size-
    template click). Sampler `app/tentcard_sampler.py` written but captures 0; revisit.
  - **PVC Card — Digital (id 113) BUILT.** Fixed CR80 card. Orientation & print colour are
    PRICE-NEUTRAL (verified); round cornering is FREE; hole punching adds a per-run delta.
    Engine `app/pvccard_engine.py` = qty curve (log-log) + hole-punch delta. LOO median 4.1%.
    Sampler `app/pvccard_sampler.py`. Wired everywhere; JS==Python.
  - **Wire-O Notebook — Litho (id 112) BUILT (Hard Cover + VDP Hard Cover).** Fixed size/
    paper/pages per cover. Drivers: cover type × additional content sheets (None/4/8/12) × qty
    + compulsory cover lamination (Matte/Gloss Front = same price; Spot UV adds a delta) + hot
    stamping (block, quoted separately). Engine `app/wireo_engine.py` = per-cover log-log qty
    curve + additive lamination/add-content deltas. Hard Cover full (LOO median 2.3%); VDP Hard
    Cover is genuinely low-qty (≤100). **GAP: Soft Cover + Exclusive Leather Cover don't offer
    the Matte-Front reference lamination (cfg_fail headless) — left pending.** Sampler
    `app/wireo_sampler.py`. Wired everywhere; JS==Python.
  - **Computer Form — Litho (NCR) (id 111) BUILT.** Fixed 9.5"×11". Package(Multi Layer /
    Single Layer / Pay Slip) × Layers(2–5, Multi only) × Ups(1–3) × Colour(1C/2C/4C) × Qty
    + copy-change/numbering. Engine `app/computerform_engine.py` = Multi core qty curve
    (log-log) × qty-interp layer/ups/colour factors (exact at q2000/q10000); Single & Pay-Slip
    have own curves. **Copy change has NO online price effect; per-ply tints price-neutral;
    numbering is quoted separately (its sweep stalled headless — a numbering-range input hangs
    the read; left as a block charge).** core LOO median 3.9%, factor axes exact. Sampler
    `app/computerform_sampler.py`. Wired everywhere; JS==Python.
  - **Voucher — Litho (id 110) BUILT.** Complex (like Bill-Book): PackForm(Pad/Book/Loose) ×
    Size(12) × ContentPaper(14) × ContentColour(4C Front/Both) × Sets(10/25/50) × Qty +
    Perforation(0/1/2) + Numbering. Engine `app/voucher_engine.py` = **decomposed factor
    model**: reference qty curve (log-log) × qty-interpolated factors (paper/colour/sets/
    packform, exact at sampled q50/q300) × size factor (q100) + numbering delta. **Perforation
    has NO online price effect** (verified). Single-option axes reconstruct EXACTLY (0%); core
    LOO median 3.9%; multi-factor combinations approximated (badge 8%). Sampler
    `app/voucher_sampler.py` (one-factor-at-a-time sweeps; resumable per section — note it can
    stall after the long paper phase, just re-run to resume). Wired everywhere; JS==Python.
  - **Bookmark — Digital (id 109) BUILT.** Drivers: paper (7; Vellum OOS skipped) × colour
    (4C Front/Both) × qty, + Round Cornering (R6) / Hole Punching (6mm) additive add-ons.
    Engine `app/bookmark_engine.py` = per-(paper|colour) **log-log** qty curve (price is
    ~power-law in qty — log-log cut held-out LOO from 18.7% to **2.5%**) + finishing deltas.
    NOTE: bookmark/standalone uses a log-log interpolator (`interpLogLog`), distinct from the
    shared log-price/linear-qty `interpLogPts`. Sampler `app/bookmark_sampler.py` (112 core +
    6 finishing). Wired everywhere; JS==Python.
  - **L-Shape Plastic Folder — Digital (id 108) BUILT.** Fixed model LSF 001, 310×442mm, 4C.
    Drivers: material (Synthetic Paper 180micron / Frosted Plastic 200micron) × qty. Engine
    `app/lshape_engine.py` = per-paper qty curve (log-interp; exact at the 14 order qtys; LOO
    median 2.2%). Sampler `app/lshape_sampler.py` (28 pts). Wired everywhere; JS==Python.
  - **Folder — Litho (id 107) BUILT (Presentation Folder group).** Drivers: mould group
    (PF/DF/KF/CF) → mould (image radios) × paper (5 Gloss Art Card weights) × qty; no
    print-colour; Die-cutting + creasing compulsory (included). Engine `app/folder_engine.py`
    = per-mould base qty curve at 250gsm-1side ref + additive paper delta (from FPF 001
    table). **Built for the PF group (6 moulds) — base-curve LOO median 3.5%, p90 6.2%.**
    GAP: DF/KF/CF groups (5 niche moulds: document/karki/CD folders) do NOT offer the
    250gsm-1side ref paper and wouldn't configure reliably headless — left pending (note in
    quote). Sampler `app/folder_sampler.py` (mould via JS-click; core 42 / paper 10 / check 8),
    params `output/folder_params.json`. Wired: PRODUCTS_UI(107), FIELD_SCHEMAS, _family,
    `/api/printoka/folder/{options,quote}`, standalone (JS==Python verified).
  - **Envelope — Litho (id 106) BUILT.** Standalone Envelope product (NOT the loose-sheet
    add-on). Drivers: **mould/model** (17 image-radio moulds; code encodes size + window
    NW/W) × **print colour/side** (12) × qty. Compulsory Die-Cutting + Folding + Gluing
    (included). Engine `app/envelope_engine.py` = per-model base qty curve at 4C(Front)
    (log-interp) + **additive colour plate-cost delta** vs 4C(Front) (the additive model
    transfers across moulds far better than multiplicative — validated on a 2nd mould).
    **Accuracy: base-curve held-out-qty LOO median 2.0% (p90 4.7%); held-out colour on a
    2nd mould median 4.1%, max 9.7%.** GAP: the 3 OE 'Best Seller' moulds need an extra
    paper select (cfg_fail headless) so they're unsampled — mapped to the same-size EV
    mould (paper differs slightly). Sampler `app/envelope_sampler.py` (mould via JS-click;
    core 84 / colour 24 / check 6 pts), params `output/envelope_params.json`. Wired:
    PRODUCTS_UI(106), FIELD_SCHEMAS, _family, `/api/printoka/envelope/{options,quote}`,
    standalone (JS==Python verified incl. OE→EV size fallback).
  - **Letterhead — Litho (id 105) BUILT.** Fixed A4 (210×297mm). Drivers: paper × print
    colour/side × qty. The **4 Conqueror 100gsm finishes are price-identical** (verified →
    collapsed to one curve); Simili 80/100 differ. Engine `app/letterhead_engine.py` =
    per-(paper|colour) qty curve (log-interp). Exact at sampled order quantities
    (500/1000/1500); held-out custom-qty LOO median 8.2%, p90 13.7% (offset step-pricing
    limit). **GAP: the live form is flaky headless (colour-select postback intermittently
    drops comboQty), so low quantities (<500) are only sampled for Simili100 4C; other
    configs extrapolate flat below 500 and above 1500.** Sampler `app/letterhead_sampler.py`
    (resumable, `_avail` retry); samples `output/letterhead_samples.json` (63 pts/16 cfgs),
    params `output/letterhead_params.json`. Wired: PRODUCTS_UI(105), FIELD_SCHEMAS,
    _family, `/api/printoka/letterhead/{options,quote}`, standalone (JS==Python verified).
  - **Notepad — Litho (id 104) BUILT.** Fixed-spec product: Size 80×106mm, Simili 80gsm
    40-sheet content, 4C+4C cover / 1C content, Wire-O punch + Matte Lamination (Both)
    compulsory. **VERIFIED on the live form: price depends ONLY on quantity** — cover paper
    (260/310gsm) and Spot UV (Front Cover) do NOT change the online price (block/included);
    paper only affects weight. Engine `app/notepad_engine.py` = single qty curve (log-interp,
    exact at the 11 order quantities; held-out custom-qty LOO median 5.2%, max 14%). Sampler
    `app/notepad_sampler.py`; samples `output/notepad_samples.json` (33 pts), params
    `output/notepad_params.json`. Wired: PRODUCTS_UI(104), FIELD_SCHEMAS["notepad"], _family,
    `/api/printoka/notepad/{options,quote}`, standalone (notepad JS == Python to the cent).

- **CROSS-PRODUCT PARITY AUDIT vs Excard (options + prices) — see PARITY_AUDIT.md.** Dumped
  every live order page (`app/parity_formdump.py` → `output/parity_*.json`) and compared
  options field-by-field. Gaps found + FIXED (option/UI parity, both UIs + standalone):
  - **Booklet 19/37:** added **Cover Lamination** (11 opts), **Cover Embossing — emboss
    size** (7), **Jawi content**, and a **Compulsory Finishing display** (binding-driven:
    Saddle → "Creasing, Saddle Stitching + Folding"; shown in the quote note). Embossing +
    hot-stamp (size/foil) are block charges → "quoted separately" (no online price delta,
    like bizcard). **Cover-lamination price delta NOT yet sampled** — currently shown as a
    selectable option + note; sample its delta to make it priced (TODO).
  - **Loose 21 + 50:** added **Envelope** add-on (7 sizes) — quoted separately (note).
    Confirmed Litho loose has NO lamination/hot-stamp/fold/punch (only Envelope).
  - **Sticker 60:** added **Hot Stamping** (Gold/Silver) — block charge, quoted separately.
  - Business Card, Letterpress sticker, Packaging already at full option parity.
  - Quote `note` now rendered in both UIs (server `#status` + standalone) so compulsory
    finishing + block charges are visible.
  - **Envelope (21+50) now PRICED** (per-piece estimate ~RM0.043–0.049/pc × qty × package;
    `envelope_cost()` in api.py + `envCost()` in standalone; JS==Python). Sampled
    `finishing_envelope.json` — Digital linear, Litho band-priced (low-qty estimate differs).
  - **Booklet cover lamination still 'quoted separately'** — its delta sample was unusable
    (booklet form cover-colour cascade hidden in headless → stale RM130 read); needs a
    booklet-config fix to sample. Embossing/hot-stamp remain block charges (parity-correct).
- **PACKAGING BOX — new section (P0–P2 done; P3 + full-fidelity folding remain).**
  Served at **`/packaging`** (`ui/packaging.html`). Excard's packmage engine reverse-
  engineered (see PACKAGING_BOX_FINDINGS.md): pricing `POST /uc/GetPriceFactor2` (public
  JSON, exact total/unit price + weight), 3D dieline `POST /uc/LinTest3D` (LineExp cut/
  crease segments), delivery `GetTranFeeByAreaID`. Token bootstrapped via ONE Playwright
  login then threaded `requests` (`app/packaging_api.py bootstrap_session`).
  - **Sampled** all 67 boxes × dims grid × full qty ladder (2656 pts) + a dieline each
    (`app/packaging_sampler.py`; raw `output/packaging_samples.json` 492KB gitignored).
  - **Engine** `app/packaging_engine.py` (our own): per-box regression `total = a0 +
    a1·netarea + b0·qty + b1·(netarea·qty)`, netarea predicted from L/W/D. Sampled 11
    sizes/box (5760 pts). **Held-out (leave-one-dimension-out) median 6.5%, 70% within 10%,
    p90 16.8%** — tail on odd shapes (dividers/cones/sleeves). Params
    `output/packaging_params.json`.
  - **API:** `/api/printoka/packaging/{catalogue,quote,dieline}`. Catalogue (67 boxes, 11
    categories, names/images/limits) `output/packaging_catalogue_ui.json`
    (`app/packaging_catalogue.py`).
  - **3D (P2):** three.js viewer with Folded-3D / Flat-dieline toggle. Flat dieline =
    EXACT from LinTest3D LineExp (all boxes). Folded 3D = parametric tube (walls+bottom+
    tuck flap) for RTE/STE/Lock-Bottom archetypes; size-accurate solid for others.
  - **3D + 2D ACCURACY IMPROVED:** (a) 3D mesh now coloured by selected **material** (kraft/
    white/grey/gold/silver/translucent PVC) + **window-patch** boxes show a translucent window
    panel and **hanging** boxes a hang-hole (`addFeatures`, MAT_COLOR in packaging.html).
    (b) **2D dieline now matches the chosen dimensions** — `/packaging/dieline?box&L&W&D`
    serves the EXACT dieline live from LinTest3D when possible (works in a normally-run
    server; auto-disabled inside the Windows dev preview where Playwright can't spawn in a
    worker thread), otherwise the **nearest of 4 pre-captured sizes/box**
    (`packaging_dielines_multi.json`, `app/packaging_dielines_multi.py`, 268 dielines). The
    standalone bakes the multi set and picks nearest client-side. Verified: small vs large
    L give different dielines (Width 173 vs 544); material/window/hang render, no errors.
  - **STACKABLE FINISHING (matches Excard):** finishing deltas verified **perfectly additive**
    (0.0% vs live API, `app/packaging_finishing_study.py`). UI now = a **surface-coating**
    dropdown (None/Gloss/Matte/Gloss-Varnish/Matte-Varnish/UV, mutually exclusive) + **stackable
    add-on checkboxes** (Spot UV / Hot Stamping / Embossing). Engine `cash_price(... coating=,
    addons=[])` sums the coating-swap delta + each add-on delta; API `coating` + `addons` (CSV);
    standalone JS port == Python to the cent. `optioncat` split into `coatings`/`addons`.
  - **P3a options DONE:** decoded `_apnPms.info4MaterialsProcesses`; per-box real default
    chains captured (`packaging_defaults.json`, fixes P062 underprice); engine option layer
    = material per-piece multipliers (14 mats) + finishing additive deltas (10) + print
    colour = no price effect (verified). Option-layer accuracy vs API median 5.3%. Wired:
    `/packaging/options` + material/colour/finishing on `/packaging/quote` + UI dropdowns.
  - **P3b standalone DONE:** `ui/packaging_standalone.html` (212KB, baked catalogue/options/
    params/67 dielines + JS engine port == Python to the cent). `app/build_packaging_standalone.py`;
    served `/packaging-standalone`.
  - **P3c folding DONE (archetype-level):** `buildCarton` folds tube (RTE/STE/Lock), tray
    (Trays & Top-Base), sleeve (open-ended), hinged-lid; other categories show solid +
    exact flat dieline. All verified rendering with live price, no console errors.
  - **P3c folding COMPLETE for all categories:** `buildCarton` (tube/tray/sleeve/hinged) +
    `buildCone`/`buildTriangle`/`buildGable`/`buildEnvelope`/`buildDivider` (codes L044/L082/
    K016X + Folder&Envelope/Divider). Every box now renders a shaped 3D form + the exact
    flat-dieline toggle. All archetypes verified rendering with live price, no console errors.
  - **PARITY (end-to-end vs live Excard GetPriceFactor2, 60 random held-out configs —
    random dims/qty/material/finishing): median 6.7%, mean 9.3%, p90 20.7%, 70% within 10%**
    (`app/packaging_parity_audit.py`, `output/packaging_parity_audit.json`). Tail on extreme
    dims / odd boxes (dividers, metallic+spot-UV). Packaging is COMPLETE.
- **NEW PRODUCT: Bill-Book — Litho (NCR carbonless), id 24.** Order page
  `www.excard.com.my/spec/Litho/Bill-Book`. Cascade learned: PackForm(Book/Pad) ×
  Paper(NCR) × Size(~37) × PaperMaterial(NCR 2–6 Layers/plies) × per-ply tint dropdowns
  (ddlLayer1..N — required for 3+ ply, price-neutral) × PrintColorSide(1C/2C/4C front,
  both, .../back) × Sets-per-book(ddlSets 50/100 — **2-ply only**; 3+ ply count sets
  directly via comboQty) × comboQty(books) + Numbering(free) + Hole-punch(+~RM0.36/book) +
  Binding orientation (price-neutral). KEY GOTCHAS: ddlSets only exists for 2-ply; 3+ ply
  needs ddlLayer1..N set before pricing; an ASP.NET "Loading In Progress" overlay must
  clear before reading price (sampler `_safe_read` waits it out). Engine
  `app/billbook_engine.py`: per-config **quantity curve keyed (layers|colour|sets)** at A4
  (log-interp over books) × **size factor** (per-size vs A4 from a size scan, area-interp
  for unsampled sizes) × Pad factor (0.988) + punch delta; numbering free. Price is ~linear
  in plies (~+RM404/ply at A4 q100). Sampler `app/billbook_sampler.py` (modes: run; full
  comboQty ladder; resumable, overlay-hardened). Wired: products.py(24), PRODUCTS_UI,
  FIELD_SCHEMAS["billbook"], _family, `/api/printoka/billbook/{options,quote}`, standalone
  (billbookPrice JS == Python verified). **Full comboQty ladder captured for ALL plies
  (2–6) — exact at every orderable quantity; held-out custom-qty LOO median 2.5%.** Samples
  `output/billbook_samples.json` (360 pts, 24 configs), params `output/billbook_params.json`.
- **#18 PARITY MATRIX (side-by-side vs each Excard order page).** Verified each product's
  UI fields against its live Excard order-page controls:
  - **Business Card (1)** — cardType(Std/Thin Fold/Fat Fold/Custom Die-Cut/Plastic), size
    (+custom), orientation, paper, colour, package(×N), qty, surface lam/SpotUV, round
    corner, hole punch, hot stamping, embossing, delivery. ✅ complete.
  - **Loose Sheet Litho (21)** — size(+custom), paper, colour, package(×N), qty, delivery.
    Litho has NO finishing on Excard. ✅ complete.
  - **Loose Sheet Digital (50)** — + hot stamping / fold / punch finishing. ✅ complete.
  - **Booklet Litho/Digital (19/37)** — orientation, size, cover type, binding, page, cover
    paper/colour, content paper/colour, outer-inner, cover hot stamping, extra books, qty,
    delivery. ✅ complete.
  - **Label Sticker Digital (60)** — rdType **Sticker**, all 7 cut categories (incl Multiple
    Dieline), 13 materials, colour, lamination/finishing, size/diameter, sheet_size+dielines,
    **package(×N, verified 2in1=2.0× / 4in1=4.0×)**, qty, delivery, AND the **rdType "CD"**
    type (✅ NEW). ✅ complete.
  - **CD disc label (rdType=CD on product 60)** ✅ — fixed-shape disc, no cut/size; drivers
    are material (Mirror Kote / Printing Paper only), colour (4C/1C), qty, package(×N).
    Sampled all 45 orderable quantities × 4 material/colour curves (`output/sticker_cd.json`)
    → `cd_price()` (exact at every qty); wired as a `type` field in the digital sticker
    schema/quote/standalone (JS==Python). Sampler `app/cd_sticker_sampler.py`.
  - **Label Sticker Letterpress (61)** — shape(Standard/Round), hot-stamp colour, size/
    diameter, qty, delivery. ✅ complete.
  ⇒ **#18 COMPLETE — every product's UI now mirrors its Excard order page in full** (all
  sizes/materials/colours/packages/cut-categories/types + finishing + delivery).
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
