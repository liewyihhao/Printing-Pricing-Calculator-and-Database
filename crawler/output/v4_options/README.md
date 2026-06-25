# v4 option universes — full Excard option parity capture

Goal: every option Excard exposes per product (priced or not, incl. image options) must
appear in our calculator. These `<slug>_options.json` files are the authoritative capture.

## How they're captured (reliable pipeline)

For **metrics-based** ordering pages (most v4 products), the rendered page exposes a global
`window.metrics` — the COMPLETE array of valid configurations (one row per valid combo, every
option dimension as a column). The capture script (run via the Chrome extension on
`https://v4.excard.com.my/ordering/<slug>`):

1. polls until `window.metrics` is populated,
2. computes distinct values per dimension (the option lists), drops noise cols (Weight, Print Method),
3. builds a per-primary dependency map (which sub-option values are valid per primary selection),
4. synthesizes image-option URLs from the on-page S3 diagram pattern
   (`…/diagram/<slug>/<MODEL>.jpg`),
5. downloads the result as `<slug>_options.json` (v4 auto-downloads enabled) → copied here.

## Per-product template types

- **metrics** (window.metrics present): folder, envelope, … — capture works directly.
- **order-form / v3 template** (NO window.metrics): e.g. `business-card` (title "… - Order Form").
  These use a different option store and need separate per-template extraction. TODO.
- **www-only** (not migrated to v4): Loose Sheet / Flyer / Brochure — not reachable (extension is
  scoped to v4; www is blocked).

## Captured so far

- `folder_options.json` — 11 models (img), 4 Model Categories, Paper, Print Colour, Lamination,
  Colour Protective Layer, **CD Seal**, **Fastener**. NOTE: CD Seal + Fastener are the hidden
  dimensions behind the earlier Folder "CD Jacket" price ambiguity.
- `envelope_options.json` — 17 models (img), Size, Print Colour, **Envelope Type** (Peel & Seal /
  security line / window patching variants we did not previously model).

## Next

Capture remaining metrics products, then reconcile each into `build_standalone.py` field
definitions (add missing fields/values + image fields). For options that change price, price them
exactly via the live `Product/CheckPrice` API (payload `JSON.stringify(jData)`) or a price-list CSV.
