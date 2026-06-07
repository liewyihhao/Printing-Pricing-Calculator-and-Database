"""Command-line interface: init-db, discover, enqueue, crawl, status, export."""
from __future__ import annotations

import argparse
import asyncio
import csv
import os
import time
from datetime import datetime, timedelta

from playwright.async_api import async_playwright
from sqlalchemy import select, func

from . import config
from .db import init_db, session_scope
from .browser import launch, login
from .discovery import read_products
from .enumerate_combos import enqueue_product
from .runner import crawl
from .logging_setup import log
from .models import Product, WorkItem, Pricing, Combination


# ---------- discover / enqueue ----------
async def _resolve_products(page, which: str) -> list[dict]:
    """which is 'all' or a product id."""
    await page.goto(config.PRICE_URL, wait_until="domcontentloaded")
    products = await read_products(page)
    if which == "all":
        return products
    pid = int(which)
    named = next((p for p in products if p["id"] == pid), None)
    return [named or {"id": pid, "name": f"product_{pid}"}]


async def _discover_or_enqueue(which: str, do_enqueue: bool):
    async with async_playwright() as pw:
        browser = await launch(pw)
        page = await (await browser.new_context(
            viewport={"width": 1440, "height": 1100})).new_page()
        try:
            if not await login(page):
                raise SystemExit("Login failed.")
            products = await _resolve_products(page, which)
            log.info("cli.products_resolved", count=len(products))
            total = 0
            for p in products:
                with session_scope() as s:
                    if do_enqueue:
                        total += await enqueue_product(s, page, p["id"], p["name"])
                    else:
                        from .discovery import discover_product
                        await discover_product(s, page, p["id"], p["name"])
            if do_enqueue:
                log.info("cli.enqueue_total", new_combos=total)
        finally:
            await browser.close()


# ---------- status ----------
def _snapshot() -> dict:
    with session_scope() as s:
        wq = dict(s.execute(
            select(WorkItem.status, func.count()).group_by(WorkItem.status)).all())
        prods = dict(s.execute(
            select(Product.status, func.count()).group_by(Product.status)).all())
        prices = s.scalar(select(func.count()).select_from(Pricing))
        combos = s.scalar(select(func.count()).select_from(Combination))
    return {"wq": wq, "prods": prods, "prices": prices, "combos": combos}


def _print_status(snap: dict, rate_per_min: float | None = None):
    wq = snap["wq"]
    total = sum(wq.values())
    done = wq.get("done", 0)
    pending = wq.get("pending", 0)
    in_prog = wq.get("in_progress", 0)
    failed = wq.get("failed", 0)
    pct = (done / total * 100) if total else 0.0

    print(f"Products: " + ", ".join(f"{k}={v}" for k, v in snap["prods"].items()))
    print(f"Combinations: {snap['combos']:,}   Price points: {snap['prices']:,}")
    print("Work queue:")
    for st in ("done", "pending", "in_progress", "failed"):
        print(f"  {st:12} {wq.get(st, 0):,}")
    bar_len = 30
    filled = int(bar_len * pct / 100)
    print(f"\n  [{'#' * filled}{'-' * (bar_len - filled)}] {pct:5.1f}%  "
          f"({done:,}/{total:,})")
    if rate_per_min:
        remaining = pending + in_prog
        eta_min = remaining / rate_per_min if rate_per_min > 0 else 0
        eta = datetime.now() + timedelta(minutes=eta_min)
        print(f"  rate: {rate_per_min:.1f} combos/min   "
              f"ETA: ~{eta_min/60:.1f} h  (~{eta:%a %H:%M})")
    if failed:
        print(f"\n  NOTE: {failed} failed — every combo should price; "
              f"run 'requeue --failed' after a fix, see output/debug/ for HTML.")
    if total and done + failed >= total and pending + in_prog == 0:
        print("\n  >>> CRAWL COMPLETE. <<<")


def cmd_status(watch: bool = False, interval: int = 15):
    if not watch:
        _print_status(_snapshot())
        return
    prev_done, prev_t = None, None
    try:
        while True:
            snap = _snapshot()
            done = snap["wq"].get("done", 0)
            rate = None
            now = time.time()
            if prev_done is not None and now > prev_t:
                rate = (done - prev_done) / ((now - prev_t) / 60.0)
            prev_done, prev_t = done, now
            os.system("cls" if os.name == "nt" else "clear")
            print(f"Printoka crawl monitor  ({datetime.now():%Y-%m-%d %H:%M:%S})  "
                  f"refresh {interval}s, Ctrl+C to stop\n")
            _print_status(snap, rate)
            total = sum(snap["wq"].values())
            if total and snap["wq"].get("pending", 0) + snap["wq"].get("in_progress", 0) == 0:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped monitoring (crawl keeps running in its own window).")


# ---------- requeue ----------
def cmd_requeue(product: int | None = None, stale_minutes: int | None = None):
    from .models import WorkItem
    from sqlalchemy import update, or_, and_
    from datetime import datetime, timezone, timedelta
    with session_scope() as s:
        conds = [WorkItem.status == "failed"]
        if stale_minutes is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)
            # Reclaim items stuck 'in_progress' longer than the cutoff (a real
            # combo never takes this long), without touching the live one.
            conds.append(and_(WorkItem.status == "in_progress",
                              WorkItem.updated_at < cutoff))
        q = update(WorkItem).where(or_(*conds))
        if product is not None:
            q = q.where(WorkItem.combination_id.in_(
                select(Combination.id).where(Combination.product_id == product)))
        q = q.values(status="pending", attempts=0, last_error=None)
        n = s.execute(q).rowcount
    print(f"Requeued {n} item(s) to pending.")


# ---------- export ----------
def cmd_export(path: str):
    with session_scope() as s, open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["product_id", "size", "paper", "lamination", "delivery_code",
                    "color_mode", "quantity", "tier", "price", "suffix"])
        rows = s.execute(
            select(Combination.product_id, Combination.size_label,
                   Combination.paper_label, Combination.lamination_label,
                   Combination.delivery_code, Pricing.color_mode, Pricing.quantity,
                   Pricing.tier, Pricing.price, Pricing.suffix)
            .join(Pricing, Pricing.combination_id == Combination.id))
        n = 0
        for r in rows:
            w.writerow(r)
            n += 1
    print(f"Exported {n} rows -> {path}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m app", description="Printoka Excard crawler")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init-db", help="Create database, tables, seed deliveries")

    d = sub.add_parser("discover", help="Read & store a product's option metadata")
    d.add_argument("--product", default="all", help="product id or 'all'")

    e = sub.add_parser("enqueue", help="Guided-walk a product and fill the work queue")
    e.add_argument("--product", default="all", help="product id or 'all'")

    c = sub.add_parser("crawl", help="Run the resumable crawl")
    c.add_argument("--product", default=None, help="restrict to a product id")
    c.add_argument("--limit", type=int, default=None, help="stop after N combos")
    c.add_argument("--workers", type=int, default=None, help="parallel browsers")
    c.add_argument("--resume", action="store_true", help="(default) continue pending work")

    st = sub.add_parser("status", help="Show crawl progress")
    st.add_argument("--watch", action="store_true", help="auto-refresh with ETA")
    st.add_argument("--interval", type=int, default=15, help="refresh seconds")

    rq = sub.add_parser("requeue", help="Reset failed/stuck items back to pending")
    rq.add_argument("--failed", action="store_true", help="(default) requeue failed items")
    rq.add_argument("--stale", type=int, nargs="?", const=10, default=None,
                    metavar="MIN", help="also reclaim in_progress stuck > MIN minutes (default 10)")
    rq.add_argument("--product", default=None, help="restrict to a product id")

    # --- order-page (accurate) crawler ---
    oe = sub.add_parser("order-enqueue", help="Discover + enqueue order-page configs")
    oe.add_argument("--normal-4c", action="store_true",
                    help="only Normal package + 4C (Phase 1, fastest)")
    oc = sub.add_parser("order-crawl", help="Run the order-page crawl (accurate prices)")
    oc.add_argument("--limit", type=int, default=None)
    oc.add_argument("--workers", type=int, default=1,
                    help="concurrent browser tabs sharing one login (e.g. 2)")
    oc.add_argument("--normal-only", action="store_true",
                    help="Phase 1: crawl only Normal-package base prices, then exit")
    oc.add_argument("--packages", default=None,
                    help="comma-separated packages to crawl, e.g. 2in1,3in1,4in1,5in1")
    oc.add_argument("--product", type=int, default=None,
                    help="restrict to one product id (e.g. 50 = Digital Loose Sheet)")
    oc.add_argument("--account", type=int, default=1,
                    help="Excard account to use (1 default, 2 = parallel second login)")
    od = sub.add_parser("order-discover",
                        help="Phase 1: enumerate VALID combos for a product (discovery-first)")
    od.add_argument("--product", type=int, required=True,
                    help="product id to discover (see app/products.py)")
    od.add_argument("--account", type=int, default=1,
                    help="Excard account to use (1 default, 2 = second login)")
    sub.add_parser("order-status", help="Order-page crawl progress")

    x = sub.add_parser("export", help="Export pricing to CSV")
    x.add_argument("--csv", default=str(config.OUTPUT_DIR / "pricing_export.csv"))

    args = ap.parse_args(argv)
    if args.cmd == "init-db":
        init_db()
        print("Database initialized.")
    elif args.cmd == "discover":
        asyncio.run(_discover_or_enqueue(args.product, do_enqueue=False))
    elif args.cmd == "enqueue":
        asyncio.run(_discover_or_enqueue(args.product, do_enqueue=True))
    elif args.cmd == "crawl":
        pid = int(args.product) if args.product else None
        asyncio.run(crawl(product_id=pid, limit=args.limit, workers=args.workers))
    elif args.cmd == "status":
        cmd_status(watch=args.watch, interval=args.interval)
    elif args.cmd == "requeue":
        cmd_requeue(product=(int(args.product) if args.product else None),
                    stale_minutes=args.stale)
    elif args.cmd == "order-enqueue":
        from .order_runner import discover_and_enqueue
        n = asyncio.run(discover_and_enqueue(only_normal_4c=args.normal_4c))
        print(f"Enqueued {n} order configs.")
    elif args.cmd == "order-crawl":
        import time as _time
        from .order_runner import crawl_orders, reset_in_progress
        pkgs = [p.strip() for p in args.packages.split(",")] if args.packages else None
        # Supervisor: a single browser/driver crash (TargetClosedError, driver
        # death) shouldn't end an unattended multi-hour run. Auto-restart with a
        # fresh Playwright instance, reset the stuck claim, and keep going until
        # the queue is genuinely drained (crawl_orders returns normally) — so it
        # survives the weekend on its own. Ctrl+C still stops it cleanly.
        attempt = 0
        while True:
            try:
                asyncio.run(crawl_orders(limit=args.limit, workers=args.workers,
                                         normal_only=args.normal_only, packages=pkgs,
                                         product_id=args.product, account_id=args.account))
                print("Order crawl complete — queue drained.")
                break
            except KeyboardInterrupt:
                print("Interrupted by user. Resume by rerunning the same command.")
                break
            except Exception as e:  # noqa: BLE001
                attempt += 1
                reset = reset_in_progress(pkgs)
                wait = min(120, 30 * attempt)
                print(f"[supervisor] crawl crashed ({type(e).__name__}: {str(e)[:120]}); "
                      f"reset {reset} stuck row(s); restarting in {wait}s "
                      f"(restart #{attempt}).")
                _time.sleep(wait)
    elif args.cmd == "order-discover":
        from .order_discovery import discover_product
        n = asyncio.run(discover_product(args.product, account_id=args.account))
        print(f"Discovery complete — enqueued {n} valid combos for product {args.product}.")
    elif args.cmd == "order-status":
        from .order_runner import order_status
        order_status()
    elif args.cmd == "export":
        cmd_export(args.csv)


if __name__ == "__main__":
    main()
