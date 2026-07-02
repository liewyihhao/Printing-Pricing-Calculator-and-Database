# CONTINUE: Build the calculator for the FULL Excard catalog (all products, none missed)

_Paste the "PROMPT TO START A NEW SESSION" block (bottom) to resume. Branch
`feat/business-card-standalone-calculator`, work in `crawler/`, venv `.venv\Scripts\python.exe`.
Shell gotcha: prefix every command with `cd /c/Users/User/OneDrive/Desktop/Printoka.com/crawler &&`._

## Goal
The calculator currently has **51 products** built to standard. Excard's full menu has ~35 MORE
products we don't have yet. Capture and build **every missing product** to the SAME standard, then
verify nothing is missed against the menu.

## The standard each product must meet (already true for the 51)
1. **Options 100%:** every Excard option dimension AND value present, incl. option images.
2. **Valid-combination enforcement:** cascading `validity` rules (impossible combos disabled).
3. **Pricing:** EXACT (0%) where the capture embeds a WMPrice curve; otherwise REFERENCE
   (~+7.5% markup, "safe/never under-price"). Contact-only products → request-a-quote.
4. **Branding:** zero user-visible "Excard" / "v4 price-list" anywhere; images embedded as data-URIs.

## The pipeline is already generic — capture is the only new input
Per product the flow is fully automated once a snapshot exists:
1. Capture `output/v4_options/<slug>_options.json` (options + WMPrice curves + images).
2. Add the product id → slug to the right maps in `app/build_standalone.py`:
   - `_EXCARD_ID2SLUG` (parity + validity), and
   - `_PRICELIST_FROM_OPTIONS` (exact pricing) IF the snapshot has embedded `priceMeta`/curves.
   - Add the product to the `products` list in `build_data()` (id, name, engine placeholder).
   For a NEW product with embedded prices, `_wire_pricelist_products` auto-generates its option
   fields + axisFields + params from the capture — you mainly need the product stub + the map entry.
3. `python -m app.build_standalone` → rebuilds `ui/calculator_standalone.html` +
   `output/calculator_data.json` + `output/calculator_engine.cjs` (the API artifacts).
4. Verify: exact products cent-exact vs the captured curves (see `app/build_pl_from_options.py`
   which walks all curves), validity cascades, options present, no "excard" in output.
5. Commit per product/batch. Rebuild also refreshes the public API automatically.

Key files: `app/build_standalone.py` (`_wire_pricelist_products`, `_attach_excard_parity`,
`_apply_ref_markup`, `_build_validity`, `_embed_images`, `_emit_api_artifacts`),
`app/build_pl_from_options.py`, `app/pricelist_engine.py`, `ui/_standalone_template.html`.

## How to CAPTURE (needs the browser — pick one)
- **Extension (best, autonomous):** reconnect Claude-for-Chrome (`list_connected_browsers` →
  `select_browser`), then for each `/ordering/<slug>` wait for `window.metrics` and run the
  extractor from `ui/capture.html` (the `const CODE=...` block) via `javascript_tool`; save the
  download into `output/v4_options/`. This is exactly how the 36 baseline snapshots were made.
- **Manual bookmarklet:** the user runs the `/capture` page bookmarklet on each product; files
  land in Downloads → copy into `output/v4_options/`.
- www-only / spec-PDF products (like magnet/pillow were): options via WebFetch on the product
  spec PDF; fixed-spec products may have no selectable options.

## Missing products to build (from Excard's full menu; slugs are in ui/capture.html SLUGS[])
Ecobag: cooler-bag, dtf-totebag-with-zip, heat-transfer-tote-bag, laminated-non-woven-bag,
rpet-non-woven-bag, toast-bag. Flexible Packaging: 3-side-seal-packaging, kraft-standing-pouch,
standing-pouch-spout, vacuum-bag-packaging. Display/large-format: foamboard, foamboard-with-magnet,
foldable-pop-display, pop-display, wind-flag, economy-roll-up-stand, bunting-gear-x-stand,
bunting-round-base-stand, bunting-tripod-stand. Notebooks: exclusive-leather-cover-wire-o-notebook,
hard-cover-perfect-bind-notebook. Loose Sheet: creative-cut-card, greeting-card. Money Packet:
premium-money-packet, hot-stamping-money-packet, envelope-money-packet. Misc: lanyard,
premium-desk-calendar, uv-dtf-sticker, food-tray, kraft-paper-bag, kotak-cenderahati, id-card,
x-ccessories. Shirts (slugs unknown → open from menu, bookmarklet auto-names): DTF Shirt,
Silkscreen Shirt, Corporate Shirt, Jacket, Muslimah Sublimation, Sweatshirt & Hoodies.

## Final check
After building, cross-reference the calculator's product list against Excard's menu and this file's
list to confirm NONE is missed. Then push. End commit messages with
`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## PROMPT TO START A NEW SESSION (paste this)

```
Continue the Printoka project (repo github.com/liewyihhao/Printing-Pricing-Calculator-and-Database,
branch feat/business-card-standalone-calculator, work in crawler/, venv .venv\Scripts\python.exe;
prefix every shell command with: cd /c/Users/User/OneDrive/Desktop/Printoka.com/crawler &&).

STEP 0: Read crawler/CONTINUE_FULL_CATALOG.md in full (it has the pipeline, the standard, the
capture method, and the exact list of missing products).

TASK: Build a functional calculator for EVERY product in Excard's full menu, to the same standard
as the existing 51 (options 100% incl. images, cascading valid-combination enforcement, exact
pricing where a WMPrice curve is captured else ~+7.5% reference markup, zero user-visible "Excard").
~35 products are missing — the full list + slugs are in CONTINUE_FULL_CATALOG.md and
ui/capture.html SLUGS[].

The build pipeline is already generic: a captured output/v4_options/<slug>_options.json plus a
product stub + map entries in app/build_standalone.py (_EXCARD_ID2SLUG, _PRICELIST_FROM_OPTIONS)
auto-produces a fully-priced, validity-enforced, image-embedded product on
`python -m app.build_standalone`. The only new input is CAPTURE.

I will reconnect the Claude Chrome extension so you can capture autonomously. Once I say
"connected": for each missing product, open v4.excard.com.my/ordering/<slug>, wait for
window.metrics, run the extractor from ui/capture.html, save the snapshot into
output/v4_options/, wire it, rebuild, verify (exact-to-cent vs the captured curves; validity;
options; no 'excard' in output), and commit in batches. If the extension can't reach a product
(www-only / spec-PDF), get its options via WebFetch on the spec PDF and flag pricing as needed.
At the end, cross-check the calculator's product list against Excard's menu to confirm none is
missed, then push. End commit messages with Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>.
```
