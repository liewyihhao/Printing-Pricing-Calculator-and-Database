"""Phase 1: cascade-discovery of VALID order combos for a product.

Instead of enqueuing the full size x paper x colour x package cross-product (which
makes Phase 2 waste ~20s confirming every invalid combo), we walk Excard's own
cascading dropdowns once and read validity in bulk: selecting a size reveals all
valid papers at once; a paper reveals all valid colours; a colour reveals valid
packages + quantities. We enqueue ONLY the combos Excard actually offers, so the
pricing phase never tests an invalid combo.

    python -m app order-discover --product 50      # enumerate valid combos
    python -m app order-crawl    --product 50      # price them (Phase 2)

NOTE: browser-based — run when no other crawl holds the Excard account.
"""
from __future__ import annotations

from playwright.async_api import async_playwright, Page
from sqlalchemy import select

from .browser import launch, ensure_session, polite_pause
from .db import session_scope
from .logging_setup import log
from .models import OrderWork
from . import products
from .order_capture import (SIZE_SEL, PAPER_SEL, COLOUR_SEL, PACKAGE_SEL,
                            _select, available_quantities)

REFERENCE_DELIVERY = 98  # price is delivery-independent; one reference is enough


async def _options(page: Page, sel: str) -> list[str]:
    """Visible, real option labels for a <select> (drop placeholders)."""
    if await page.locator(sel).count() == 0:
        return []
    return await page.locator(sel).first.evaluate(
        "el => [...el.options].map(o => o.text.trim())"
        ".filter(t => t && !t.startsWith('- Please') && !t.startsWith('- Not')"
        " && !t.startsWith('- Select'))")


async def _walk(page: Page, target: products.ProductTarget) -> list[dict]:
    """Return every valid (size, paper, colour, package) combo Excard offers.

    Reloads the page fresh per size to bound ASP.NET postback state buildup."""
    combos: list[dict] = []
    await page.goto(target.spec_url, wait_until="domcontentloaded")
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    await ensure_session(page)
    sizes = await _options(page, SIZE_SEL)
    log.info("discover.sizes", product=target.product_id, n=len(sizes), sizes=sizes)

    for size in sizes:
        # Fresh page per size keeps the cascade state clean.
        await page.goto(target.spec_url, wait_until="domcontentloaded")
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        await ensure_session(page)
        if not await _select(page, SIZE_SEL, size):
            continue
        papers = await _options(page, PAPER_SEL)
        for paper in papers:
            if not await _select(page, PAPER_SEL, paper):
                continue
            colours = await _options(page, COLOUR_SEL)
            for colour in colours:
                if not await _select(page, COLOUR_SEL, colour):
                    continue
                packages = await _options(page, PACKAGE_SEL) or ["Normal"]
                qtys = await available_quantities(page)
                for pkg in packages:
                    combos.append({"size": size, "paper": paper, "colour": colour,
                                   "package": pkg, "qty_count": len(qtys)})
            await polite_pause()
        log.info("discover.size_done", size=size, combos_so_far=len(combos))
    return combos


def _enqueue(target: products.ProductTarget, combos: list[dict],
             deliveries=None) -> int:
    """Insert valid combos as pending OrderWork rows (idempotent per product)."""
    deliveries = deliveries or [REFERENCE_DELIVERY]
    created = 0
    with session_scope() as s:
        existing = {(w.size_label, w.paper_label, w.colour_side, w.package,
                     w.delivery_code)
                    for w in s.scalars(select(OrderWork).where(
                        OrderWork.product_id == target.product_id)).all()}
        for c in combos:
            for d in deliveries:
                key = (c["size"], c["paper"], c["colour"], c["package"], d)
                if key in existing:
                    continue
                s.add(OrderWork(product_id=target.product_id,
                                size_label=c["size"], paper_label=c["paper"],
                                colour_side=c["colour"], package=c["package"],
                                delivery_code=d,
                                priority=1 if c["package"] == "Normal" else 3))
                existing.add(key)
                created += 1
        s.commit()
    return created


async def discover_and_mark(product_id: int, account_id: int = 1):
    """Option-only pass: walk the live cascade and MARK every valid combo as
    status='done' (validity, no prices). Completes the combo list exactly like
    Excard without scraping prices."""
    target = products.get(product_id)
    from .order_runner import _new_page
    from . import accounts
    from .db import session_scope
    from .models import OrderWork
    from sqlalchemy import select
    account = accounts.get(account_id)
    log.info("discover_mark.start", product=product_id, url=target.spec_url)
    async with async_playwright() as pw:
        browser = await launch(pw)
        page = await _new_page(browser, account=account)
        try:
            combos = await _walk(page, target)
        finally:
            try:
                await browser.close()
            except Exception:
                pass
    marked = 0
    with session_scope() as s:
        ex = {(w.size_label, w.paper_label, w.colour_side, w.package): w
              for w in s.scalars(select(OrderWork).where(
                  OrderWork.product_id == target.product_id)).all()}
        for c in combos:
            key = (c["size"], c["paper"], c["colour"], c["package"])
            w = ex.get(key)
            if w:
                if w.status != "done":
                    w.status = "done"; marked += 1
            else:
                s.add(OrderWork(product_id=target.product_id, size_label=c["size"],
                                paper_label=c["paper"], colour_side=c["colour"],
                                package=c["package"], delivery_code=REFERENCE_DELIVERY,
                                status="done", priority=1))
                marked += 1
        s.commit()
    log.info("discover_mark.done", valid_combos=len(combos), newly_marked=marked)
    return len(combos), marked


async def discover_product(product_id: int, deliveries=None, account_id: int = 1) -> int:
    """Phase 1 entry point: walk the cascade and enqueue valid combos."""
    target = products.get(product_id)
    log.info("discover.start", product=product_id, name=target.name,
             method=target.method, url=target.spec_url, account=account_id)
    from .order_runner import _new_page  # reuse the verified-login page factory
    from . import accounts
    account = accounts.get(account_id)
    async with async_playwright() as pw:
        browser = await launch(pw)
        page = await _new_page(browser, account=account)
        try:
            combos = await _walk(page, target)
        finally:
            try:
                await browser.close()
            except Exception:
                pass
    n = _enqueue(target, combos, deliveries)
    log.info("discover.enqueued", product=product_id, valid_combos=len(combos),
             new_rows=n)
    return n
