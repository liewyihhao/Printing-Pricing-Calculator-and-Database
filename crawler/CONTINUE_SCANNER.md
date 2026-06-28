# CONTINUE: Automated Excard Market Scanner

_Paste the "PROMPT TO START A NEW SESSION" block (bottom of this file) to resume. Branch
`feat/business-card-standalone-calculator`, work in `crawler/`, venv `.venv\Scripts\python.exe`.
Shell gotcha: prefix every command with `cd /c/Users/User/OneDrive/Desktop/Printoka.com/crawler &&`._

## What this feature is
A monitor that detects what changed on the source print site (excard) between scans:
new products, new promotions, new finishing / sizes / colours, **removed** customization
options, and **price increases**. The goal is to run it **automatically** on a schedule and
surface the result on the Market Watch dashboard + API.

## What already exists (DONE, committed, pushed)
- `app/excard_watch.py` — the **diff engine** (pure Python, no browser). Compares two snapshot
  dirs of `<slug>_options.json` and reports new/removed products, new/removed option dimensions,
  new/removed values, **price increases/decreases (%)**, image changes. `diff_catalogue()` diffs
  a menu snapshot for promotions. CLI:
  `python -m app.excard_watch <baseline_dir> <fresh_dir> --json output/change_report.json`
- `app/public_api.py` — serves `GET /api/v1/changes` (the report) and `GET /whatsnew`
  (dashboard) and `GET /capture` (manual capture helper).
- `ui/whatsnew.html` — Market Watch dashboard (renders the change report).
- `ui/capture.html` — **manual** capture: a "Capture this product" bookmarklet (same extractor
  that built the baseline) + the full product URL checklist.
- **Baseline snapshots:** `output/v4_options/*.json` — the frozen reference (options + embedded
  WMPrice curves) for ~38 products. This is what "fresh" gets diffed against.

## What's NOT done — the "AUTO" part (THIS is the task)
The capture is currently **manual** (bookmarklet per page). To make it automatic we need a
**headless capture** that renders each ordering page, extracts the snapshot, and runs the diff
on a schedule — no human clicking.

### Plan (recommended)
1. **Headless capturer** `app/excard_scan.py` using **Playwright** (`pip install playwright;
   playwright install chromium`):
   - Log in to `https://v4.excard.com.my` (account 142059498 — credentials from env vars
     `EXCARD_USER` / `EXCARD_PASS`, never hard-code). Reuse cookies between runs.
   - For each product slug (the list is in `_EXCARD_ID2SLUG` in `app/build_standalone.py` +
     the order-form ones), `page.goto('/ordering/<slug>')`, wait for `window.metrics` to be a
     non-empty array (poll up to ~12s), then `page.evaluate(...)` the SAME extractor used in
     `ui/capture.html` (metrics path → distinct values + image map + WMPrice curves; DOM-select
     fallback for the order-form template products). Write `output/v4_options_fresh/<slug>_options.json`.
   - For the menu/promos: extract the embedded menu JSON (product objects with `promo_msg`/
     `isnew`/`ispromo`) from any rendered page → `output/menu_fresh.json`.
   - www-only products (loose-sheet, magnet, pillow): the Playwright context is scoped to v4;
     handle www separately or skip (note it in the report).
2. **Run + diff + report** in one command (`app/excard_scan.py` `main()`):
   - capture → `excard_watch.diff_snapshots(output/v4_options, output/v4_options_fresh)`
     and `diff_catalogue(output/menu_baseline.json, output/menu_fresh.json)`
   - merge → write `output/change_report.json` (the `/api/v1/changes` + `/whatsnew` source).
   - optional notify: if any change, send email / webhook (env `WATCH_WEBHOOK`).
   - **Do not** auto-overwrite the baseline; print a one-liner to promote it
     (`robocopy/cp output/v4_options_fresh output/v4_options`) after a human glance, OR add a
     `--promote` flag.
3. **Schedule it:** a Windows Task Scheduler entry (or `app/scheduler` cron) that runs
   `python -m app.excard_scan` daily/weekly. (There is existing scheduled-task infra under
   `.claude/` and a `mcp__scheduled-tasks` tool, but a plain Task Scheduler job is simplest.)
4. **Re-pricing hook (nice-to-have):** when the report shows a price increase or new option for
   a product that is currently `exact`, flag it for re-conversion via
   `app/build_pl_from_options.py` (the captured fresh curves can rebuild its `*_pl_params.json`).

### Gotchas / notes
- The extractor logic to reuse verbatim is the metrics+DOM one in `ui/capture.html`
  (`const CODE=...`) — it's validated and matches the baseline format exactly.
- The v4 ordering pages are SPAs; metrics load via JS after navigation → must wait for
  `window.metrics`, not for network idle (idle never fires; that wedged the old Chrome tool).
- Price columns vary by product: `WMPrice` / `WM Price` / `Total Price`. Curves are keyed by the
  option axes; `build_pl_from_options.build()` already auto-drops price-neutral axes (DeliveryFee/
  Compulsory/IsAlQuran) and averages residual collisions.
- Keep `output/v4_options/` as the committed baseline; write fresh captures to a separate dir.
- After any pricing change, run `python -m app.build_standalone` to refresh the calculator +
  `output/calculator_data.json` + `output/calculator_engine.cjs` that the API serves.

---

## PROMPT TO START A NEW SESSION (paste this)

```
Continue the Printoka project (repo github.com/liewyihhao/Printing-Pricing-Calculator-and-Database,
branch feat/business-card-standalone-calculator, work in crawler/, venv .venv\Scripts\python.exe;
prefix every shell command with: cd /c/Users/User/OneDrive/Desktop/Printoka.com/crawler &&).

STEP 0: Read crawler/CONTINUE_SCANNER.md in full.

TASK: Build the AUTOMATED Excard market scanner. The diff engine (app/excard_watch.py), the
Market Watch dashboard (/whatsnew + /api/v1/changes), and the manual capture bookmarklet
(/capture, ui/capture.html) already exist and are committed. The baseline snapshots are in
output/v4_options/. What's missing is the *automatic* capture so it runs without me clicking.

Build app/excard_scan.py: a headless Playwright capturer that logs into v4.excard.com.my
(credentials from env EXCARD_USER/EXCARD_PASS), visits each product ordering page, waits for
window.metrics, runs the SAME extractor used in ui/capture.html, and writes fresh snapshots to
output/v4_options_fresh/. Then run app.excard_watch to diff fresh vs the output/v4_options
baseline + diff the menu for promotions, write output/change_report.json (so /whatsnew and
/api/v1/changes show it), and optionally notify on changes. Add a way to promote fresh->baseline
(a --promote flag, never automatic). Then give me a Windows Task Scheduler command to run it on a
schedule. Don't hard-code credentials. Commit each working piece. End commit messages with
Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>.
```
