"""Enumerate order-page configs (by priority) and crawl them resumably.

Priority (lower number = crawled first):
  1  Normal package + 4C (Front/Both)   <- most useful, ~hours
  2  Normal package + 1C
  3  ganging packages (2in1/3in1/4in1…)
Each config sweeps all its quantities. Product price is delivery-independent, so
we crawl one delivery per config by default (configurable).
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

from playwright.async_api import async_playwright
from sqlalchemy import select, func

from . import config
from .db import session_scope
from .browser import launch, login, polite_pause
from .order_capture import (capture_config, OrderConfigSpec, configure,
                            available_quantities, SIZE_SEL, PAPER_SEL,
                            COLOUR_SEL, PACKAGE_SEL)
from .logging_setup import log
from .models import OrderWork, OrderQuote, OptionValue, OptionGroup, utcnow

PRODUCT_ID = 21
# Each config does ~80 page operations (27 quantities × ~3 postbacks). The whole
# browser PROCESS (not just the context) wedges after enough ops, so we relaunch
# the entire browser every few configs and on any error.
RECYCLE_EVERY = 9       # relaunch browser every N configs (under the ~hang threshold)
MAX_CONSEC_ERRORS = 4   # after this many in a row, back off (possible throttle)

# Colour sides and packages, with priorities.
COLOURS_P1 = ["4C (Front)", "4C (Both)"]
COLOURS_P2 = ["1C (Front)", "1C (Both)"]
# The Cash/base price + weight are delivery-INDEPENDENT, so we crawl each config
# once against a single reference delivery and compute shipping from weight via
# the /shipping endpoint for any destination. (No ×4 delivery duplication.)
REFERENCE_DELIVERY = 98  # East Malaysia, used only to trigger the recompute
DELIVERIES = [REFERENCE_DELIVERY]


async def _discover_axes(page) -> dict:
    """Read the real option lists from the order page (sizes, papers, colours,
    packages)."""
    await configure(page, OrderConfigSpec(PRODUCT_ID, "", "", "", "Normal", 98)) \
        if False else None
    from .order_capture import SPEC_URL
    await page.goto(SPEC_URL, wait_until="domcontentloaded")
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    await polite_pause()

    async def opts(sel):
        if await page.locator(sel).count() == 0:
            return []
        return await page.locator(sel).evaluate(
            "el => [...el.options].map(o=>o.text.trim())"
            ".filter(t => t && !t.startsWith('- Please') && !t.startsWith('- Not'))")
    return {
        "sizes": await opts(SIZE_SEL),
        "papers": await opts(PAPER_SEL),
        "colours": await opts(COLOUR_SEL),
        "packages": await opts(PACKAGE_SEL),
    }


def enqueue_orders(axes: dict, deliveries=None, only_normal_4c=False) -> int:
    """Populate order_work with configs, by priority. Idempotent."""
    deliveries = deliveries or DELIVERIES
    sizes, papers = axes["sizes"], axes["papers"]
    all_colours = axes["colours"] or (COLOURS_P1 + COLOURS_P2)
    packages = axes["packages"] or ["Normal"]
    created = 0
    with session_scope() as s:
        existing = {(w.size_label, w.paper_label, w.colour_side, w.package,
                     w.delivery_code)
                    for w in s.scalars(select(OrderWork)).all()}

        def add(size, paper, colour, package, delivery, priority):
            nonlocal created
            key = (size, paper, colour, package, delivery)
            if key in existing:
                return
            s.add(OrderWork(product_id=PRODUCT_ID, size_label=size,
                            paper_label=paper, colour_side=colour, package=package,
                            delivery_code=delivery, priority=priority))
            existing.add(key)
            created += 1

        for size in sizes:
            for paper in papers:
                for d in deliveries:
                    for c in COLOURS_P1:
                        if c in all_colours:
                            add(size, paper, c, "Normal", d, 1)
                    if only_normal_4c:
                        continue
                    for c in COLOURS_P2:
                        if c in all_colours:
                            add(size, paper, c, "Normal", d, 2)
                    for pkg in packages:
                        if pkg == "Normal":
                            continue
                        for c in all_colours:
                            add(size, paper, c, pkg, d, 3)
        s.commit()
    return created


def reset_in_progress(packages: list[str] | None = None) -> int:
    """Return any 'in_progress' rows to 'pending' so a restart re-crawls them
    (a crash leaves the claimed row stuck mid-flight)."""
    with session_scope() as s:
        q = select(OrderWork).where(OrderWork.status == "in_progress")
        if packages:
            q = q.where(OrderWork.package.in_(packages))
        n = 0
        for w in s.scalars(q).all():
            w.status = "pending"
            w.attempts = 0
            n += 1
        return n


def _claim(normal_only: bool = False, packages: list[str] | None = None,
           product_id: int | None = None):
    with session_scope() as s:
        q = select(OrderWork).where(OrderWork.status == "pending")
        if product_id is not None:
            # Target a single product (e.g. 50 = Digital Loose Sheet).
            q = q.where(OrderWork.product_id == product_id)
        if normal_only:
            # Phase 1: standard (Normal) base prices only. When these run out the
            # claim returns None and the crawl exits cleanly — ganging is a later
            # phase run without this flag.
            q = q.where(OrderWork.package == "Normal")
        elif packages:
            # Restrict to a specific set of packages (e.g. 2in1..5in1). Claims
            # outside the set are left pending; crawl exits when the set is done.
            q = q.where(OrderWork.package.in_(packages))
        w = s.scalars(q.order_by(OrderWork.priority, OrderWork.id).limit(1)
                      .with_for_update(skip_locked=True)).first()
        if w is None:
            return None
        w.status = "in_progress"
        w.attempts += 1
        # Resolve the product's order-page URL (default None -> Litho Loose Sheet,
        # preserving original behaviour for product 21 and any unregistered id).
        spec_url = None
        try:
            from .products import get as _get_product
            spec_url = _get_product(w.product_id).spec_url
        except Exception:
            spec_url = None
        return {"id": w.id, "attempts": w.attempts,
                "spec": OrderConfigSpec(w.product_id, w.size_label, w.paper_label,
                                        w.colour_side, w.package, w.delivery_code,
                                        spec_url=spec_url)}


def _store(work_id: int, rows):
    with session_scope() as s:
        for r in rows:
            existing = s.scalars(select(OrderQuote).where(
                OrderQuote.order_work_id == work_id,
                OrderQuote.quantity == r.quantity)).first()
            vals = dict(
                before_discount=_d(r.before_discount), discount_amount=_d(r.discount_amount),
                after_discount=_d(r.after_discount), handling_fee=_d(r.handling_fee),
                delivery_fee=_d(r.delivery_fee), nett=_d(r.nett),
                weight_kg=_d(r.weight_kg), tiers=r.tiers or None)
            if existing:
                for k, v in vals.items():
                    setattr(existing, k, v)
                existing.captured_at = utcnow()
            else:
                s.add(OrderQuote(order_work_id=work_id, quantity=r.quantity, **vals))


def _d(v):
    return Decimal(str(v)) if v is not None else None


def _finish(work_id, status, error=None):
    with session_scope() as s:
        w = s.get(OrderWork, work_id)
        if not w:
            return
        if status == "error":
            w.status = "failed" if w.attempts >= config.MAX_ATTEMPTS else "pending"
            w.last_error = (error or "")[:1000]
        else:
            w.status = status
            w.last_error = error


async def _new_page(browser, save_state: bool = True, account=None):
    from .order_capture import SPEC_URL, SIZE_SEL
    import os
    if account is None:
        from . import accounts
        account = accounts.get(1)
    state_path = account.state_file
    state = state_path if os.path.exists(state_path) else None
    ctx = await browser.new_context(viewport={"width": 1440, "height": 1200},
                                    accept_downloads=True, storage_state=state)
    page = await ctx.new_page()
    # VERIFY the restored session can actually render the order form. A stale
    # storage_state can leave a cookie that neither redirects to /login NOR
    # authorizes the order page (empty form). is_logged_out() misses that case,
    # so check positively for the size dropdown and do a FULL fresh login if it's
    # absent. This guarantees every page we hand back is truly authenticated.
    await page.goto(SPEC_URL, wait_until="domcontentloaded")
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    if await page.locator(SIZE_SEL).count() == 0:
        log.warning("order.session_unusable_reloging_in", account=account.id)
        await login(page, username=account.username, password=account.password)
    if save_state:
        try:
            await ctx.storage_state(path=state_path)
        except Exception:
            pass
    return page


async def _relaunch(pw, browser, account=None):
    """Close the (possibly wedged) browser and launch a fresh one + page.

    Retries with backoff so a transient network drop (ERR_INTERNET_DISCONNECTED)
    or a slow Excard waits it out instead of crashing the whole crawl. Survives
    outages up to ~40 minutes; longer than that, it raises and the user resumes.
    """
    try:
        await browser.close()
    except Exception:
        pass
    last_err = None
    for attempt in range(20):
        try:
            new_browser = await launch(pw)
            page = await _new_page(new_browser, account=account)
            if attempt:
                log.info("order.relaunch_recovered", after_attempts=attempt)
            return new_browser, page
        except Exception as e:  # noqa: BLE001
            last_err = e
            delay = min(120, 15 * (attempt + 1))
            log.warning("order.relaunch_retry", attempt=attempt,
                        error=repr(e)[:120], retry_in_s=delay)
            await asyncio.sleep(delay)
    raise RuntimeError(f"relaunch failed after retries: {last_err!r}")


async def crawl_orders(limit: int | None = None, workers: int = 1,
                       normal_only: bool = False,
                       packages: list[str] | None = None,
                       product_id: int | None = None,
                       account_id: int = 1):
    """Single-worker resumable crawl, on ONE Excard account.

    Per-account this is single-session by necessity: Excard's ASP.NET order form
    keeps the in-progress config in SERVER-side session state, so two tabs on ONE
    login corrupt each other. True parallelism = run this twice with DIFFERENT
    account_id values (each has its own login + storage_state = independent
    session). Account 1 uses the original session file (running crawls unaffected).

    Robustness: relaunch the WHOLE browser on any error and recycle periodically.
    """
    if workers and workers > 1:
        log.warning("order.parallel_unsupported",
                    note="Per account it's single-session; use a 2nd account_id for parallelism")
    from . import accounts
    account = accounts.get(account_id)
    counter = {"done": 0, "empty": 0, "error": 0}
    async with async_playwright() as pw:
        browser = await launch(pw)
        page = await _new_page(browser, account=account)
        log.info("order.crawl_start", account=account_id, product=product_id)
        processed = 0
        consec_err = 0
        try:
            while True:
                if limit and counter["done"] >= limit:
                    break
                if processed and processed % RECYCLE_EVERY == 0:
                    log.info("order.recycle_browser", processed=processed)
                    browser, page = await _relaunch(pw, browser, account=account)
                claim = _claim(normal_only=normal_only, packages=packages,
                               product_id=product_id)
                if claim is None:
                    break
                processed += 1
                try:
                    rows = await capture_config(page, claim["spec"])
                    if rows:
                        _store(claim["id"], rows)
                        _finish(claim["id"], "done")
                        counter["done"] += 1
                    else:
                        _finish(claim["id"], "skipped", "no quantities/prices")
                        counter["empty"] += 1
                    consec_err = 0
                except Exception as e:  # noqa: BLE001
                    log.error("order.error", error=repr(e)[:160])
                    _finish(claim["id"], "error", repr(e))
                    counter["error"] += 1
                    consec_err += 1
                    # Page/browser may have crashed — relaunch the whole browser.
                    browser, page = await _relaunch(pw, browser, account=account)
                    if consec_err >= MAX_CONSEC_ERRORS:
                        log.warning("order.backoff", consec_err=consec_err,
                                    note="many errors in a row — pausing 90s")
                        await asyncio.sleep(90)
                        consec_err = 0
                    else:
                        await polite_pause()
                if counter["done"] % 5 == 0 and counter["done"]:
                    log.info("order.progress", **counter)
        finally:
            try:
                await browser.close()
            except Exception:
                pass
    log.info("order.crawl_finished", **counter)
    return counter


async def discover_and_enqueue(only_normal_4c=False):
    async with async_playwright() as pw:
        browser = await launch(pw)
        page = await _new_page(browser)
        try:
            axes = await _discover_axes(page)
            log.info("order.axes", sizes=len(axes["sizes"]), papers=len(axes["papers"]),
                     colours=axes["colours"], packages=axes["packages"])
        finally:
            await browser.close()
    n = enqueue_orders(axes, only_normal_4c=only_normal_4c)
    log.info("order.enqueued", new=n)
    return n


def order_status():
    with session_scope() as s:
        wq = dict(s.execute(select(OrderWork.status, func.count())
                            .group_by(OrderWork.status)).all())
        quotes = s.scalar(select(func.count()).select_from(OrderQuote))
        print("Order work by status:", wq)
        print("Order quotes:", quotes)
