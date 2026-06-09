"""Booklet order-page price capture (products 19 Litho & 37 Digital).

The booklet cascade is richer than Loose Sheet, so we can't reuse the flat
configure()/sweep_quantities(). This module sets the full booklet cascade:

    orientation -> size -> ordertype -> binding -> page
                -> coverPaper -> coverColour
                -> contentPaper -> contentColour
                -> outerInner

then sweeps the quantity dropdown reading "PRICE BEFORE DISCOUNT" (the cash tier),
using the SAME recompute trick proven for Loose Sheet (select qty, then toggle the
delivery radio off-and-on to force the UpdatePanel postback).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from playwright.async_api import Page

from .browser import polite_pause, ensure_session
from .logging_setup import log
from .order_capture import (_parse_breakdown, _check_delivery, _read_weight,
                            QTY_SEL, DELIVERY_RADIO, _TOGGLE_HELPER)
from .order_capture import _select  # polling <select> setter
from .booklet_discovery import (ORIENT, SIZE, ORDERTYPE, BINDING, PAGE,
                                COVER_PAPER, COVER_COLOUR, CONTENT_PAPER,
                                CONTENT_COLOUR, OUTER_INNER, _check_radio, _opts)

REFERENCE_DELIVERY = 98


@dataclass
class BookletSpec:
    product_id: int
    spec_url: str
    orientation: str
    size: str
    ordertype: str          # "Soft Cover" | "Hard Cover"
    binding: str            # "Saddle Stitch" | "Perfect Binding"
    page: str               # e.g. "16"
    cover_paper: str
    cover_colour: str       # e.g. "4C"
    content_paper: str
    content_colour: str     # e.g. "4C (Both)" | "1C (Both)"
    outer_inner: str = "4C: 4 Colour Outer Only"
    delivery_code: int = REFERENCE_DELIVERY


async def configure_booklet(page: Page, spec: BookletSpec) -> bool:
    """Set the full booklet cascade. Returns False if any step's option is not
    offered (an invalid combination) — the caller skips it cleanly."""
    await page.goto(spec.spec_url, wait_until="domcontentloaded")
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    await ensure_session(page)
    if await page.locator(SIZE).count() == 0:
        raise RuntimeError("booklet form not loaded (session/throttle) — will retry")
    def fail(step):
        log.warning("booklet.configure_step_failed", step=step, size=spec.size,
                    ordertype=spec.ordertype, binding=spec.binding, page=spec.page,
                    cover=spec.cover_paper, content=spec.content_paper)
        return False
    if not await _check_radio(page, ORIENT, spec.orientation):
        return fail("orientation")
    if not await _select(page, SIZE, spec.size):
        return fail("size")
    if not await _check_radio(page, ORDERTYPE, spec.ordertype):
        return fail("ordertype")
    if not await _check_radio(page, BINDING, spec.binding):
        return fail("binding")
    if not await _select(page, PAGE, spec.page):
        return fail("page")
    if not await _select(page, COVER_PAPER, spec.cover_paper):
        return fail("cover_paper")
    await _select(page, COVER_COLOUR, spec.cover_colour)
    if not await _select(page, CONTENT_PAPER, spec.content_paper):
        return fail("content_paper")
    await _select(page, CONTENT_COLOUR, spec.content_colour)
    await _check_radio(page, OUTER_INNER, spec.outer_inner)
    return True


async def available_quantities(page: Page) -> list[int]:
    if await page.locator(QTY_SEL).count() == 0:
        return []
    texts = await page.locator(QTY_SEL).evaluate(
        "el => [...el.options].map(o => o.text.trim()).filter(t => /^\\d/.test(t))")
    out = []
    for t in texts:
        import re
        digits = re.sub(r"[^\d]", "", t)
        if digits:
            out.append(int(digits))
    return sorted(set(out))


async def sweep_quantities(page: Page, spec: BookletSpec,
                           quantities: list[int]) -> list[dict]:
    """For each qty: select it, toggle delivery (helper->target) to force the
    recompute, read the cash breakdown + weight."""
    rows: list[dict] = []
    helper = _TOGGLE_HELPER.get(spec.delivery_code, 99)
    prev_cash = None
    for q in quantities:
        opt_label = await page.locator(QTY_SEL).evaluate(
            "(el, q) => { const o=[...el.options].find(o=>o.text.replace(/[^0-9]/g,'')===String(q));"
            " return o ? o.text : null; }", q)
        if not opt_label:
            continue
        # Read with a stale-guard: a strictly larger qty must yield a DIFFERENT
        # (higher) cash. If the price didn't recompute (identical to the previous
        # qty), re-toggle delivery and re-read; after retries, skip the point
        # rather than record a stale value (the bug that polluted earlier samples).
        cash = nett = None
        for attempt in range(3):
            await page.select_option(QTY_SEL, label=opt_label)
            await asyncio.sleep(0.3)
            await _check_delivery(page, helper)
            await _check_delivery(page, spec.delivery_code)
            await asyncio.sleep(0.2)
            bd = _parse_breakdown(await page.evaluate("() => document.body.innerText"))
            cash, nett = bd["before_discount"], bd["nett"]
            if cash is None and nett is None:
                break
            if prev_cash is None or cash != prev_cash:
                break  # recomputed (or first reading) — accept
            # identical to previous qty's cash -> likely stale, retry harder
            await asyncio.sleep(0.5)
        if cash is None and nett is None:
            continue
        if prev_cash is not None and cash == prev_cash:
            log.warning("booklet.stale_price_skipped", qty=q, cash=cash,
                        size=spec.size, page=spec.page, binding=spec.binding)
            continue  # never record a duplicate (different qty, same price = stale)
        rows.append({"qty": q, "cash": cash, "nett": nett,
                     "weight": await _read_weight(page)})
        prev_cash = cash
    return rows


async def capture_booklet(page: Page, spec: BookletSpec) -> list[dict]:
    if not await configure_booklet(page, spec):
        log.warning("booklet.configure_failed", size=spec.size, binding=spec.binding,
                    page=spec.page, cover=spec.cover_paper, content=spec.content_paper)
        return []
    qtys = await available_quantities(page)
    if not qtys:
        return []
    rows = await sweep_quantities(page, spec, qtys)
    log.info("booklet.captured", size=spec.size, binding=spec.binding, page=spec.page,
             cover=spec.cover_paper, content=spec.content_paper, n=len(rows))
    return rows
