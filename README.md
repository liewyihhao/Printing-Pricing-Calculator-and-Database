# Printoka Pricing Calculator & Database

Printoka's own **offline, self-contained** print-pricing calculator and catalogue. It
mirrors Excard's product configuration exactly (same options, same valid combinations)
and prices independently in our own system — Excard is the reference/data source only,
never a runtime dependency. Customer UI never links to Excard.

## 👉 START HERE (for a new Claude Code chat)
**Read the full handoff:** [`crawler/HANDOFF.md`](crawler/HANDOFF.md)
Raw: https://raw.githubusercontent.com/liewyihhao/Printing-Pricing-Calculator-and-Database/main/crawler/HANDOFF.md

It contains: current state, architecture, every key file, the 3 accounts, DB state,
domain learnings (offset vs digital economics), how to run, and the pending tasks.

## Repository structure

The root looks small because ~1,230 tracked files live inside a few deep folders:

```
Printoka.com/
├── crawler/                     # the engine (Python) — where ~90% of the work is
│   ├── app/                     # 230 modules: crawlers, CheckPrice samplers, price
│   │                           #   engines, build_standalone.py, packaging_engine.py,
│   │                           #   public_api.py, validity/parity tooling
│   ├── ui/                      # 108 files — the customer-facing output:
│   │   ├── calculator_standalone.html   # self-contained pricing calculator (93 products)
│   │   ├── packaging_standalone.html    # 67-style folding-carton box builder
│   │   ├── products/  (94)              # per-product SEO/spec pages
│   │   ├── specs.html, index.html       # catalogue + landing
│   │   └── _standalone_template.html    # the calculator's engine+UI template
│   ├── output/                  # 700 files — BUILT data & captures (tracked selectively):
│   │   ├── calculator_data.json          # full catalogue: products, fields, validity, prices
│   │   ├── calculator_engine.cjs         # Node-requireable pricing engine (API uses it)
│   │   ├── packaging_params.json         # baked box-pricing params
│   │   ├── validity/, v4_form/, field_sections.json   # live-form captures (build inputs)
│   │   └── spec_content/, spec_facts/, fold_diagrams/ # authored + crawled product depth
│   ├── HANDOFF.md               # full state/architecture handoff (START HERE)
│   └── tests/, booklet_docs/
├── web/                         # 57 files — Next.js storefront (cart/checkout/track)
├── dashboard/                   # ops dashboard
├── .claude/  .agents/           # Claude Code config + bundled skills
└── README.md, PROJECT_SUMMARY.md, brand assets (logo, guideline, product images)
```

**Not in Git (by design, via `.gitignore`):** `.venv/` (reinstall), `__pycache__/`,
`.env` (secrets), and large *regeneratable* caches under `output/` (raw crawl dumps,
`packaging_samples.json`). A fresh clone still builds — the essential derived artifacts
above are all tracked. To rebuild data: re-run the samplers, then `python -m app.build_standalone`.

## Quick status
- ✅ **93 products** in the standalone calculator — full option parity with Excard
  (presence, values, order), exact prices (CheckPrice-sampled), option images embedded.
- ✅ **Conditional validity** replicated per product — exact valid-combination rules
  (which options/fields are valid given other selections), driven by live-form captures
  and price-curve analysis. Standing audits: `parity_full_audit` 0/0/0, `v4_reconcile` 0/0.
- ✅ **Packaging box builder** — 67 folding-carton styles, API-validated option set;
  offline pricing is an ~estimate (packmage's imposition pricing can't be exact offline).
- ✅ Physics-based weight; self-contained order flow (POSTs to our own `public_api.py`).

## Run
```
cd crawler
.venv\Scripts\python.exe -m uvicorn app.api:app --port 8000        # dev API + tooling
# or serve the built calculator directly:
.venv\Scripts\python.exe -m http.server 8030 --directory ui       # → /calculator_standalone.html
```
Rebuild the calculator after data/logic changes: `python -m app.build_standalone`
(then `build_specs_page`, `build_product_pages`). Secrets live in `crawler/.env`
(git-ignored) — recreate from `crawler/.env.example`.
