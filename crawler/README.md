# Printoka — Excard price crawler

Resumable crawler that captures Excard's full price lists (all products × valid
option combinations × 4 delivery destinations) into PostgreSQL, for internal
reverse-engineering of pricing.

## How it works

Each Excard "Generate Price List" is a slow (~35s) full-page postback that returns
**every quantity × both color modes (4C, 4C+4C) × all four tiers (Platinum, Gold,
Silver, Cash)** at once. So one crawl unit = one
`(product, size, paper, lamination, delivery)` combination. Combinations are
enumerated into a Postgres `work_queue` and processed by a resumable runner that
checkpoints after every item.

## Setup

1. Python deps (already installed in `.venv`):
   ```
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   .venv\Scripts\python.exe -m playwright install chromium   # we actually use system Edge
   ```
2. Fill `.env` (copy from `.env.example`):
   - `EXCARD_PASSWORD` — your reseller password
   - `PGPASSWORD` — your local PostgreSQL superuser password
3. Browser: uses **system Edge** (`channel=msedge`) to avoid a Chromium SxS issue
   on this machine. Set `HEADLESS=true` for unattended runs.

## Commands

```
python -m app init-db                      # create DB, tables, seed deliveries
python -m app discover --product 21        # read a product's option metadata
python -m app enqueue   --product 21       # guided-walk + fill the work queue
python -m app enqueue   --product all      # all 79 products
python -m app crawl     --product 21 --limit 3   # crawl a few (smoke test)
python -m app crawl     --workers 1        # full resumable crawl (default resume)
python -m app status                       # progress by product / queue / prices
python -m app export    --csv output\pricing_export.csv
```

The crawl is **idempotent and resumable**: re-running `crawl` skips `done` items and
continues `pending` ones. Kill it any time; restart to resume.

## Schema (PostgreSQL)

`products`, `option_groups`, `option_values`, `deliveries`, `combinations`,
`work_queue`, `pricing`, `price_history`, `raw_payloads`, `crawl_sessions`,
`reverse_engineering_analysis` (stub). See `app/models.py`.

- `combinations.combo_hash` = deterministic sha256 of the 5 input fields → dedupe.
- `pricing` unique on `(combination_id, color_mode, quantity, tier)`.
- `price_history` records old→new whenever a re-crawl changes a price.
- `raw_payloads` keeps the generated HTML so prices can be re-parsed without re-crawling.

## Robustness

- Session expiry mid-crawl → auto re-login and retry.
- Failures retried up to `CRAWL_MAX_ATTEMPTS`, then quarantined as `failed` with `last_error`.
- Invalid/zero-price combinations are marked `skipped` (not retried forever).
- Optional concurrency via `--workers N` (Postgres `FOR UPDATE SKIP LOCKED`); keep low to be polite.
- Politeness delays `CRAWL_MIN_DELAY_MS`..`CRAWL_MAX_DELAY_MS` between actions.

## Tests

```
.venv\Scripts\python.exe -m pytest        # DB tests auto-skip if PG unavailable
```

`tests/test_parser.py` (golden-file parse), `test_hash.py`, `test_models.py`
(constraints + price history), `test_recovery.py` (session detection + quarantine).

## Scale note

~35s per combination. Loose Sheet alone ≈ ~3,000 combos ≈ ~30h; the full site is a
multi-day background run. Use `status` to monitor; the queue makes it safe to stop/resume.

## Scope

This is the data-collection layer. The original master-prompt's FastAPI/Celery/Redis
API layer and the reverse-engineering engine are intentionally **not** built yet; the
schema/package are structured so they can be layered on top of this data.
