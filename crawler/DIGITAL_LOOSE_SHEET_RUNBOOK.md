# Digital Loose Sheet (product 50) — crawl runbook

Discovery-first (two-phase) method. Run **only after** the offset/Litho Loose Sheet
work is done and **no other crawl holds the Excard account** (single-session rule).

## Status of preparation
- [x] Confirmed `/spec/Digital/Loose_Sheet` exists and uses the **same order-page
      framework** as Litho (identical 426 KB shell, shared control selectors).
- [x] Product registry `app/products.py` → id **50** = Digital Loose Sheet URL.
- [x] Crawler parameterized by product/URL (backward-compatible; Litho unaffected).
- [x] Phase-1 cascade discovery `app/order_discovery.py` (enumerates ONLY valid combos).
- [x] CLI: `order-discover --product` and `order-crawl --product`.
- [ ] **Live validation pending** — must run one discovery + a few captures against the
      live Digital page (couldn't test earlier: ganging held the account).

## Steps (when ready)
1. **Phase 1 — discover valid combos** (~10–15 min, browser):
   ```
   .venv\Scripts\python.exe -m app order-discover --product 50
   ```
   Enqueues only the size/paper/colour/package combos Excard actually offers.

2. **Sanity-check** the discovery before the long pricing run:
   ```
   .venv\Scripts\python.exe -m app order-status
   ```
   (Confirm a sensible number of valid combos for product 50; spot-check sizes/papers
   match what the Digital order page shows.)

3. **Phase 2 — price the valid combos** (supervised, resumable):
   ```
   .venv\Scripts\python.exe -m app order-crawl --product 50 --normal-only   # base first
   .venv\Scripts\python.exe -m app order-crawl --product 50                  # then the rest
   ```
   Prices stream into the same DB; the calculator picks them up automatically.

## Notes / validation watch-outs
- Digital printing usually offers **smaller quantities** and possibly different
  paper/colour sets than offset — discovery handles that automatically (reads live).
- If the Digital page's control names differ from Litho (they shouldn't — same shell),
  the selectors in `app/order_capture.py` are the single place to adjust.
- Finishing/add-ons (Task #12) for Digital are captured the same way as for Litho,
  after base pricing.
- Going forward, **always pass `--product <id>`** to `order-crawl` so products don't
  mix in the queue.
