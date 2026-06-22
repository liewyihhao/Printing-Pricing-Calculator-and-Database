# Continue prompt — Printoka calculator build (paste into a new Claude Code chat)

Run from the repo root `C:\Users\User\OneDrive\Desktop\Printoka.com`. Paste everything below.

---

You are continuing the **Printoka pricing-calculator** build. Repo:
github.com/liewyihhao/Printing-Pricing-Calculator-and-Database, branch
`feat/business-card-standalone-calculator`. Work in `crawler/`; venv `crawler/.venv`
(`.venv\Scripts\python.exe`).

**CRITICAL shell gotcha:** background tasks AND the foreground shell sometimes start at the
project ROOT, not `crawler/`. Always prefix commands with
`cd /c/Users/User/OneDrive/Desktop/Printoka.com/crawler &&`. Run the Excard crawl ONE browser
at a time (two headless browsers starve this laptop). Background samplers are resumable — if a
section stalls (flaky ASP.NET postbacks), re-run to resume.

## STEP 0 — read state
1. `crawler/HANDOFF.md` — top "LATEST STATE" lists every built product + the exact pattern.
2. `cd crawler && .venv\Scripts\python.exe -m app.catalogue_scan --print` — coverage (26/52
   products live; ids up to 118).
3. `crawler/output/parity_report.json` (or `/api/printoka/parity`) — current option-parity gaps.
4. `crawler/output/spec_link_map.json` — every catalogue product → its `/spec` order form.

## What's DONE (do NOT rebuild — see PRODUCTS_UI / catalogue_scan BUILT)
Business Card(1) · Loose Sheet Litho/Digital(21/50) · Booklet Litho/Digital(19/37) · Label
Sticker Digital/Letterpress(60/61) · Bill-Book(24) · Packaging Boxes(67) · Brochure/Flyer/
Customprint aliases(101/102/103) · Notepad(104) · Letterhead(105) · Envelope(106) · Folder(107)
· L-Shape Folder(108) · Bookmark(109) · Voucher(110) · Computer Form(111) · Wire-O Notebook(112)
· PVC Card(113) · Kad Kahwin(114) · Kad Terima Kasih(115) · Static Cling(116) · Car Sticker(117)
· Wall Calendar(118). Feature: Excard option-image thumbnails (`output/option_images.json`).

## TASK A — close the remaining option-parity gaps FIRST
Run `.venv\Scripts\python.exe -m app.parity_checker` (deep-configures every live Excard form,
captures ALL options, diffs vs FIELD_SCHEMAS → `output/parity_report.json`, served at
`/api/printoka/parity`). Current real gaps (~7): **PVC Card VDP** (Variable Data Printing
sub-system: ddlVDP/VDPType/font/bold/alignment — sample whether VDP adds cost, then add the
option fields), **Wire-O Soft Cover + Exclusive Leather Cover** (they don't offer the Matte-Front
reference lamination headless — sample with their own ref lamination), **Folder cover lamination
pricing** (currently "quoted separately" — sample the Spot UV/varnish deltas). Ignore
naming-only false positives (No/Yes toggles vs "Round Corner"/"Hole Punching", "Others"
custom-size, per-ply tint dropdowns). For each gap: if the option changes price, sample its
delta (a few qtys) and add to the engine; if price-neutral (verify by sampling 2 qtys — many
Excard finishing options are), add it as a selectable field with a "no online price change"
note. Re-run the checker until each product is clean.

## TASK B — build the remaining ~26 products
Priority: Calendars (Desk Calendar Hard/Soft Stand = `/spec/Litho/Desk_Calendar_(Hard_Stand)`
and `(Soft_Stand)`; Wire-O Wall Calendar = `/spec/Litho/Wire-O_Wall_Calendar`) · Paper Bag,
Non-Woven Bag, Canvas Tote Bag, Standing Pouch, Sachet Board/Papan Kopi · Money Packet ·
Banner, Bunting, Roll-Up Stand, Wobbler · Mug, Magnet, Button Badge, Sublimation Shirt, Hand
Fan, Hanger, Hard Cover Menu, Mask Keeper, Pillow, Pre-Inked Stamp/Stamp Chop, Arch File ·
**Tent Card (DEFERRED** — its price stays RM0 with only lamination+qty set; needs a size-
template interaction; retry or skip with a note).

## PER-PRODUCT WORKFLOW (mirror the existing products exactly)
1. Dump live form: `.venv\Scripts\python.exe -m app.formdump_url "<spec url>" 1 <tag>`.
2. Probe the FULL cascade incl. finishing — set EVERY control so all dependent options reveal
   (the parity_checker enforces this). Note fixed vs priced drivers.
3. `app/<p>_sampler.py` — decomposed model: a reference qty curve + qty-interpolated factors
   per option axis (sample each axis at 2 qtys; exact at sampled points), finishing as additive
   deltas. Run in background, resumable.
4. `app/<p>_engine.py` — log-log qty interpolation for the core curve; `cash_price`, `tiers`
   (Cash/Silver-4/Gold-8/Platinum-14), `weight_kg`. Audit honestly: core leave-one-out + per-
   axis reconstruction; report median %. Never claim an accuracy you didn't measure.
5. Wire `app/api.py`: PRODUCTS_UI, FORMULATED, `_family()`, FIELD_SCHEMAS, `/options`+`/quote`
   endpoints (next free id 119+). Mirror fields in `app/build_standalone.py` (+ params load +
   engineByProduct) and port the engine to JS in `ui/_standalone_template.html`; run
   `python -m app.build_standalone`; verify JS==Python to the cent via `node`.
6. If Excard shows option IMAGES, add them to `output/option_images.json` (UTF-8!) keyed by
   family/field/label — they render as thumbnails automatically.
7. Add the slug to `BUILT` in `app/catalogue_scan.py`; update `HANDOFF.md`.
8. Verify live: restart the preview server (or `uvicorn app.api:app --port 8010`) and confirm
   the product quotes; then commit (force-add only SMALL `output/*.json` params/curves, NEVER
   the large `*_samples_*.json`) and `git push`. End commit messages with:
   `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

## Notes
- A recurring local scheduled task `printoka-build-all-products` (every 5h, while the app is
  open) already runs this same workflow. You can work in parallel; just don't double-build.
- Engine pattern reference: `app/kadkahwin_engine.py` (factor model), `app/notepad_engine.py`
  (qty-only curve), `app/envelope_engine.py` (per-mould curve + additive option delta).
- Work autonomously, one product/gap at a time, committing + pushing each. Report per-product
  progress and a final summary.
