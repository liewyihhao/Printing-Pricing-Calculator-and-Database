"""Resumable crawl runner.

Claims pending work via Postgres FOR UPDATE SKIP LOCKED (safe for optional
concurrency), captures each combination, persists pricing (+ history on change)
and the raw HTML, and checkpoints per item. Recovers from session loss; retries
with backoff and quarantines after MAX_ATTEMPTS.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

from playwright.async_api import async_playwright
from sqlalchemy import select

from . import config
from .db import session_scope
from .browser import launch, login, polite_pause
from .capture import capture_combination, CombinationSpec
from .logging_setup import log
from .models import (WorkItem, Combination, Pricing, PriceHistory, RawPayload,
                     CrawlSession, utcnow)


def _claim(product_id: int | None):
    """Atomically claim one pending work item; return a detached spec dict."""
    with session_scope() as s:
        q = (select(WorkItem).join(Combination)
             .where(WorkItem.status == "pending"))
        if product_id is not None:
            q = q.where(Combination.product_id == product_id)
        q = q.order_by(Combination.product_id, Combination.id).limit(1) \
             .with_for_update(skip_locked=True, of=WorkItem)
        item = s.scalars(q).first()
        if item is None:
            return None
        item.status = "in_progress"
        item.attempts += 1
        c = item.combination
        return {
            "work_id": item.id, "combination_id": c.id, "attempts": item.attempts,
            "spec": CombinationSpec(
                product_id=c.product_id, delivery_code=c.delivery_code,
                size_raw=c.size_raw, size_label=c.size_label,
                paper_raw=c.paper_raw, paper_label=c.paper_label,
                lamination_raw=c.lamination_raw, lamination_label=c.lamination_label),
        }


def _persist(combination_id: int, parsed, html: str):
    """Upsert pricing rows (history on change) + store raw payload."""
    with session_scope() as s:
        for pp in parsed.prices:
            existing = s.scalars(select(Pricing).where(
                Pricing.combination_id == combination_id,
                Pricing.color_mode == pp.color_mode,
                Pricing.quantity == pp.quantity,
                Pricing.tier == pp.tier)).first()
            new_price = Decimal(str(pp.price))
            if existing is None:
                s.add(Pricing(combination_id=combination_id, color_mode=pp.color_mode,
                              quantity=pp.quantity, tier=pp.tier, price=new_price,
                              suffix=pp.suffix))
            elif existing.price != new_price:
                s.add(PriceHistory(combination_id=combination_id, color_mode=pp.color_mode,
                                   quantity=pp.quantity, tier=pp.tier,
                                   old_price=existing.price, new_price=new_price))
                existing.price = new_price
                existing.suffix = pp.suffix
                existing.captured_at = utcnow()
        s.add(RawPayload(combination_id=combination_id, html=html))


def _save_debug(combination_id: int, reason: str, html: str):
    """Persist a failing page so we can see why no price was produced."""
    debug_dir = config.OUTPUT_DIR / "debug"
    debug_dir.mkdir(exist_ok=True)
    safe = "".join(ch if ch.isalnum() else "_" for ch in reason)[:40]
    path = debug_dir / f"combo_{combination_id}_{safe}.html"
    try:
        path.write_text(html, encoding="utf-8")
        log.warning("capture.saved_debug", combination=combination_id,
                    reason=reason, path=str(path))
    except Exception:
        pass


def _finish(work_id: int, status: str, error: str | None = None):
    with session_scope() as s:
        item = s.get(WorkItem, work_id)
        if item is None:
            return
        if status == "error":
            # Retry until attempts exhausted, then quarantine.
            item.status = "failed" if item.attempts >= config.MAX_ATTEMPTS else "pending"
            item.last_error = (error or "")[:1000]
        else:
            item.status = status            # done | skipped
            item.last_error = error


RECYCLE_EVERY = 120  # rebuild the browser context periodically to avoid leaks/hangs
STATE_FILE = config.OUTPUT_DIR / "session_state.json"


async def _new_page(browser):
    """Create a context that REUSES the saved login session (cookies) when
    available, so we log in once and avoid repeated logins that trigger Excard's
    rate-limit. Only logs in if no saved session or the session has expired."""
    from .browser import ensure_session
    state = str(STATE_FILE) if STATE_FILE.exists() else None
    ctx = await browser.new_context(
        viewport={"width": 1440, "height": 1200}, accept_downloads=True,
        storage_state=state)
    page = await ctx.new_page()
    if state:
        # Validate the reused session; re-login only if it has expired.
        await page.goto(config.PRICE_URL, wait_until="domcontentloaded")
        await ensure_session(page)
    else:
        await login(page)
    # Persist the (fresh or refreshed) session for the next context.
    try:
        await ctx.storage_state(path=str(STATE_FILE))
    except Exception:
        pass
    return page


async def _worker(worker_id: int, browser, product_id: int | None,
                  limit: int | None, counter: dict):
    page = await _new_page(browser)
    processed = 0
    while True:
        if limit is not None and counter["done"] >= limit:
            break
        # Recycle the browser context every N combos: a single long-lived page
        # accumulates memory/state and eventually hangs (goto timeouts).
        if processed and processed % RECYCLE_EVERY == 0:
            log.info("worker.recycle_browser", worker=worker_id, processed=processed)
            try:
                await page.context.close()
            except Exception:
                pass
            page = await _new_page(browser)
        claim = _claim(product_id)
        if claim is None:
            break
        processed += 1
        result = await capture_combination(page, claim["spec"])
        if result.status == "ok":
            _persist(claim["combination_id"], result.parsed, result.html)
            _finish(claim["work_id"], "done")
            counter["done"] += 1
        else:
            # Every enqueued combo should price; an error means something to fix.
            # Save the page so we can diagnose why no price appeared.
            if result.html:
                _save_debug(claim["combination_id"], result.error or "error", result.html)
            _finish(claim["work_id"], "error", result.error)
            counter["error"] += 1
            await polite_pause()  # backoff a touch on errors
        if counter["done"] % 10 == 0 and counter["done"]:
            log.info("worker.progress", **counter)
    await page.context.close()


async def crawl(product_id: int | None = None, limit: int | None = None,
                workers: int | None = None):
    workers = workers or config.WORKERS
    counter = {"done": 0, "skipped": 0, "error": 0}
    with session_scope() as s:
        sess = CrawlSession(status="running")
        s.add(sess)
        s.flush()
        session_id = sess.id
    log.info("crawl.start", product=product_id, limit=limit, workers=workers,
             session=session_id)
    async with async_playwright() as pw:
        browser = await launch(pw)
        try:
            await asyncio.gather(*[
                _worker(i, browser, product_id,
                        (limit if workers == 1 else None), counter)
                for i in range(workers)])
        finally:
            await browser.close()
    with session_scope() as s:
        sess = s.get(CrawlSession, session_id)
        sess.status = "finished"
        sess.finished_at = utcnow()
        sess.stats = counter
    log.info("crawl.finished", **counter)
    return counter
