"""Voucher CheckPrice sampler — enumerate all Printoka option combos via v4 API.

Saves output/voucher_cp_samples.json:
  {key: {qty: price}, ...}
  where key = "packform|size|paper|colour|sets=N|num=X|perf=Y"

Usage:
  python -m app.voucher_cp_sampler          # sample all
  python -m app.voucher_cp_sampler --build  # also build params + validate
"""
from __future__ import annotations
import argparse, base64, json, math, ssl, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
SAMPLES_FILE = OUT / "voucher_cp_samples.json"
PARAMS_FILE = OUT / "voucher_plx_params.json"

CHECKPRICE_URL = "https://devv2.excard.com.my/Product/CheckPrice"
_B64 = base64.b64encode(b"ExcardAPI:EXCARDPNCAPI").decode()
_API_KEY = "RjvaNM0xSDxcKyneFhFFxek42Nrnd4FuE9rScoHQ"
_CTX = ssl._create_unverified_context()

TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065

# Printoka field options (from FIELD_SCHEMAS["voucher"])
PACKFORMS = ["Pad", "Book", "Loose"]
SIZES = [
    "90mm x 140mm", "105mm x 145mm", "145mm x 145mm", "125mm x 175mm",
    "90mm x 190mm", "107mm x 190mm", "60mm x 210mm", "145mm x 210mm",
    "55mm x 213mm", "95mm x 225mm", "120mm x 230mm", "105mm x 300mm",
]
PAPERS = [
    "Art Paper 100gsm", "Art Paper 130gsm", "Art Paper 150gsm",
    "Matte Art Paper 150gsm",
    "Colour Paper Buff 75gsm", "Colour Paper Blue 75gsm", "Colour Paper Green 75gsm",
    "Colour Paper Pink 75gsm", "Colour Paper Purple 75gsm", "Colour Paper Yellow 75gsm",
    "Simili 80gsm", "Simili 100gsm",
    "Art Card 230gsm (2 sides coated)", "Art Card 260gsm (2 sides coated)",
]
COLOURS = ["4C (Front)", "4C (Both)"]
SETS_PAD_BOOK = ["10", "25", "50"]
NUMBERINGS = ["No", "Yes"]
PERFS = ["0", "1", "2"]

# Orderable quantities per form (from v4 metrics array, excludes "Other")
QTYS_PAD_BOOK = [
    "10", "20", "30", "40", "50", "60", "70", "80", "90", "100",
    "150", "200", "250", "300", "350", "400", "500", "600", "700", "800", "900", "1000",
]
QTYS_LOOSE = [
    "250", "500", "1000", "1500", "2000", "2500",
    "5000", "10000", "15000", "20000", "25000", "50000",
]

_SESSION_COOKIE: str = ""  # set by _get_session_cookie()


def _get_session_cookie() -> str:
    """Login to v4 via Playwright and extract session cookies for devv2 API."""
    global _SESSION_COOKIE
    if _SESSION_COOKIE:
        return _SESSION_COOKIE
    import asyncio
    from playwright.async_api import async_playwright
    from app import browser as B
    from app.readymade_enum import login_v4

    async def _fetch_cookie():
        async with async_playwright() as pw:
            b = await B.launch(pw)
            page = await b.new_page()
            await login_v4(page)
            await page.goto("https://v4.excard.com.my/price-list/voucher-pad",
                            wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(1000)
            cookies = await page.context.cookies()
            await b.close()
            return "; ".join(
                f"{c['name']}={c['value']}"
                for c in cookies
                if "excard" in c.get("domain", "").lower()
            )

    _SESSION_COOKIE = asyncio.run(_fetch_cookie())
    return _SESSION_COOKIE


def _make_key(packform: str, size: str, paper: str, colour: str,
              sets: str, numbering: str, perf: str) -> str:
    return f"{packform}|{size}|{paper}|{colour}|sets={sets}|num={numbering}|perf={perf}"


def _fetch(key: str, qty: str, packform: str, size: str, paper: str,
           colour: str, sets: str, numbering: str, perf: str,
           retries: int = 3) -> float | None:
    spec = {
        "Product": "Voucher",
        "Size": size,
        "PackingMethod": packform,
        "Paper": paper,
        "PrintColour": colour,
        "Lamination": "",
        "Quantity": qty,
        "Sets": sets,
        "IsNumbering": "Yes" if numbering == "Yes" else "No",
        "FirstPanelNumbering": "false",
        "PerforationLine": perf,
        "Country": "99",
        "Courier": "Default",
        "CountryZone": "",
    }
    body = json.dumps({"type": "Voucher", "spec": [spec]}).encode()
    hdrs = {
        "Authorization": "Basic " + _B64,
        "Api-Key": _API_KEY,
        "Content-Type": "application/json; charset=utf-8",
        "Cookie": _SESSION_COOKIE,
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(CHECKPRICE_URL, data=body, headers=hdrs, method="POST")
            with urllib.request.urlopen(req, timeout=25, context=_CTX) as r:
                raw = r.read()
            if not raw:
                continue
            d = json.loads(raw.decode())
            p = float(str(d.get("Price", "0")).replace(",", ""))
            return p if p > 0 else None
        except Exception:
            if attempt < retries - 1:
                time.sleep(1.0 * (attempt + 1))
    return None


def _build_tasks() -> list[tuple]:
    """Return list of (key, qty, packform, size, paper, colour, sets, numbering, perf)."""
    tasks = []
    for packform in PACKFORMS:
        sets_list = SETS_PAD_BOOK if packform in ("Pad", "Book") else [""]
        qtys = QTYS_PAD_BOOK if packform in ("Pad", "Book") else QTYS_LOOSE
        for size in SIZES:
            for paper in PAPERS:
                for colour in COLOURS:
                    for sets in sets_list:
                        for numbering in NUMBERINGS:
                            for perf in PERFS:
                                key = _make_key(packform, size, paper, colour, sets, numbering, perf)
                                for qty in qtys:
                                    tasks.append((key, qty, packform, size, paper, colour, sets, numbering, perf))
    return tasks


def run(max_workers: int = 2) -> dict:  # CheckPrice not concurrency-safe: workers<=2
    # Ensure session cookie is available
    cookie = _get_session_cookie()
    if not cookie:
        print("ERROR: Could not get session cookie — aborting", file=sys.stderr)
        sys.exit(1)
    print(f"Session cookie obtained ({len(cookie)} chars)", flush=True)

    # Load existing samples
    existing: dict[str, dict[str, float]] = {}
    if SAMPLES_FILE.exists():
        existing = json.loads(SAMPLES_FILE.read_text(encoding="utf-8"))

    # Build task list (skip already-done)
    all_tasks = _build_tasks()
    tasks = [
        t for t in all_tasks
        if existing.get(t[0], {}).get(t[1]) is None
    ]

    total_needed = len(tasks)
    total_all = len(all_tasks)
    print(f"Voucher CP sampler: {total_needed}/{total_all} calls to fetch", flush=True)

    if not tasks:
        print("All done — samples complete.")
        return existing

    done = 0
    failed = 0

    def _work(t):
        key, qty, packform, size, paper, colour, sets, numbering, perf = t
        price = _fetch(key, qty, packform, size, paper, colour, sets, numbering, perf)
        return key, qty, price

    # Periodic save every 5000 calls
    save_interval = 5000

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_work, t): t for t in tasks}
        for fut in as_completed(futures):
            key, qty, price = fut.result()
            if price is not None:
                existing.setdefault(key, {})[qty] = price
            else:
                failed += 1
            done += 1

            if done % save_interval == 0 or done == total_needed:
                SAMPLES_FILE.write_text(json.dumps(existing, indent=0), encoding="utf-8")
                pct = done * 100 // total_needed
                print(f"  {done}/{total_needed} ({pct}%) done, {failed} failed", flush=True)

    SAMPLES_FILE.write_text(json.dumps(existing, indent=0), encoding="utf-8")
    print(f"Sampling done: {done} calls, {failed} failed -> {SAMPLES_FILE.name}", flush=True)
    return existing


def build_params(samples: dict | None = None) -> dict:
    """Convert samples to curves structure for the engine."""
    if samples is None:
        if not SAMPLES_FILE.exists():
            raise FileNotFoundError(f"{SAMPLES_FILE} not found — run sampler first")
        samples = json.loads(SAMPLES_FILE.read_text(encoding="utf-8"))

    curves: dict[str, dict[str, float]] = {}
    for key, qty_prices in samples.items():
        if qty_prices:
            curves[key] = {str(qty): float(price) for qty, price in qty_prices.items()}

    params = {
        "curves": curves,
        "sizes": SIZES,
        "papers": PAPERS,
        "colours": COLOURS,
        "sets": SETS_PAD_BOOK,
        "numberings": NUMBERINGS,
        "perfs": PERFS,
        "weight_factor": WEIGHT_FACTOR,
    }
    PARAMS_FILE.write_text(json.dumps(params, indent=0), encoding="utf-8")
    print(f"Built {len(curves)} curves -> {PARAMS_FILE.name}", flush=True)
    return params


def _validate(params: dict) -> None:
    """Spot-check a few known combos."""
    from app import voucher_engine_plx as eng
    checks = [
        dict(packform="Pad", size="90mm x 140mm", paper="Art Paper 100gsm",
             colour="4C (Front)", sets="10", qty=100, perforation="0", numbering="No"),
        dict(packform="Book", size="145mm x 210mm", paper="Art Paper 100gsm",
             colour="4C (Front)", sets="50", qty=100, perforation="0", numbering="No"),
        dict(packform="Loose", size="90mm x 140mm", paper="Art Paper 100gsm",
             colour="4C (Front)", sets="", qty=1000, perforation="0", numbering="No"),
    ]
    print("Validation spot-checks:")
    for c in checks:
        price = eng.cash_price(**c)
        print(f"  {c['packform']:5s} {c['size']:15s} qty={c['qty']:5d} -> RM {price:.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="Build params after sampling")
    parser.add_argument("--build-only", action="store_true", help="Only build params from existing samples (no sampling/login)")
    parser.add_argument("--workers", type=int, default=30)
    args = parser.parse_args()

    if args.build_only:
        params = build_params()
        _validate(params)
    else:
        samples = run(max_workers=args.workers)
        if args.build:
            params = build_params(samples)
            _validate(params)
