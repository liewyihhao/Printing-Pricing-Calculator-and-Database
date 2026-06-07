"""Capture one combination's price matrix from the live site.

A "combination" is one Generate input: (product, size, paper, lamination, delivery).
The Generate is a slow (~35s) full-page postback; we wait for it, then parse.
"""
from __future__ import annotations

from dataclasses import dataclass

from playwright.async_api import Page

from . import config
from .browser import polite_pause, ensure_session
from .logging_setup import log
from .parser import parse_price_html, ParseResult

M = config.MATRIX_PREFIX


@dataclass
class CombinationSpec:
    product_id: int
    delivery_code: int
    size_raw: str | None = None
    size_label: str | None = None
    paper_raw: str | None = None
    paper_label: str | None = None
    lamination_raw: str | None = None
    lamination_label: str | None = None


@dataclass
class CaptureResult:
    status: str            # "ok" | "skipped" | "error"
    html: str = ""
    parsed: ParseResult | None = None
    error: str | None = None


async def _product_url(product_id: int) -> str:
    # The ddlProduct postback handles switching, but loading a known product URL
    # is the most reliable entry. Litho path works for paper products; the page
    # then exposes ddlProduct to switch if needed.
    return f"{config.BASE_URL}/price-list/Litho/{product_id}"


async def _current_label(page: Page, selector: str) -> str | None:
    """The text of the currently-selected option (stable across postbacks,
    unlike the comma-packed option *value* which embeds size-dependent data)."""
    try:
        return await page.locator(selector).first.evaluate(
            "el => el.options[el.selectedIndex] && el.options[el.selectedIndex].text.trim()")
    except Exception:
        return None


async def _set_select(page: Page, selector: str, label: str) -> bool:
    """Select by visible label only if it differs from current (avoids a
    redundant postback). Returns True if a change/postback happened."""
    if await page.locator(selector).count() == 0:
        return False
    if await _current_label(page, selector) == label:
        return False
    await page.select_option(selector, label=label)
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    await polite_pause()
    return True


async def _set_lamination(page: Page, label: str) -> bool:
    """Lamination is a <select> (name ...rblLaminationSide). Select by label."""
    sel = f"select[name='{M}rblLaminationSide']"
    if await page.locator(sel).count() == 0:
        # Fallback: whichever select currently offers this label.
        loc = page.locator("select").filter(
            has=page.locator(f"option:text-is('{label}')")).first
        if await loc.count() == 0:
            return False
        await loc.select_option(label=label)
    else:
        await _set_select(page, sel, label)
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    await polite_pause()
    return True


async def _set_delivery(page: Page, code: int) -> None:
    loc = page.locator(f"input[name$='rblOrderCountryCode'][value='{code}']").first
    if await loc.count():
        try:
            await loc.check()
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        await polite_pause()


async def configure(page: Page, spec: CombinationSpec) -> None:
    """Bring the form to the desired product + options.

    We reload the product page fresh for every combination. After a Generate the
    page is mid-navigation/in a results state, and reusing it races with the
    settling navigation ('execution context was destroyed'). A clean reload per
    combo costs a few seconds but is reliable.
    """
    target = await _product_url(spec.product_id)
    await page.goto(target, wait_until="domcontentloaded")
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    await ensure_session(page)
    # Ensure the form is actually present before touching it.
    try:
        await page.wait_for_selector(f"select[name='{M}ddlSize']", timeout=15000)
    except Exception:
        pass
    await polite_pause()

    # Select by stable LABEL (option values embed size-dependent data).
    if spec.size_label:
        await _set_select(page, f"select[name='{M}ddlSize']", spec.size_label)
    if spec.paper_label:
        await _set_select(page, f"select[name='{M}ddlPaper']", spec.paper_label)
    if spec.lamination_label:
        await _set_lamination(page, spec.lamination_label)
    await _set_delivery(page, spec.delivery_code)


async def generate_and_parse(page: Page) -> CaptureResult:
    """Trigger the slow Generate postback, wait, parse the resulting matrix."""
    # Client-side validation must pass or the postback won't fire. Every enqueued
    # combination is one the form actually offers, so a failure here means a
    # field wasn't set right -> treat as a retryable error, never a silent skip.
    async def _validate():
        return await page.evaluate(
            "() => typeof Page_ClientValidate==='function'"
            " ? Page_ClientValidate('order_spec') : true")
    try:
        valid = await _validate()
    except Exception:
        # Page still settling from a prior navigation; wait and retry once.
        try:
            await page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        valid = await _validate()
    if not valid:
        return CaptureResult(status="error", html=await page.content(),
                             error="client_validation_failed")

    try:
        async with page.expect_navigation(wait_until="load",
                                           timeout=config.GENERATE_TIMEOUT_MS):
            await page.evaluate(
                f"() => __doPostBack('{config.GENERATE_POSTBACK_TARGET}','')")
    except Exception:
        # Might have been an AJAX partial update instead of full nav.
        pass

    # The Generate postback is slow; wait generously for a non-zero RM amount.
    try:
        await page.wait_for_function(
            "() => /RM\\s*[1-9]/.test(document.body.innerText)", timeout=30000)
    except Exception:
        html = await page.content()
        # No price appeared -> retryable error (likely too-slow postback), not a skip.
        return CaptureResult(status="error", html=html,
                             parsed=parse_price_html(html), error="no_nonzero_price")

    html = await page.content()
    parsed = parse_price_html(html)
    if not parsed.ok:
        return CaptureResult(status="error", html=html, parsed=parsed,
                             error="parser_found_no_prices")
    return CaptureResult(status="ok", html=html, parsed=parsed)


async def capture_combination(page: Page, spec: CombinationSpec) -> CaptureResult:
    try:
        await configure(page, spec)
        result = await generate_and_parse(page)
        log.info("capture.done", product=spec.product_id, delivery=spec.delivery_code,
                 size=spec.size_label, paper=spec.paper_label,
                 lamination=spec.lamination_label, status=result.status,
                 prices=(len(result.parsed.prices) if result.parsed else 0))
        return result
    except Exception as e:  # noqa: BLE001
        log.error("capture.error", product=spec.product_id, error=repr(e))
        return CaptureResult(status="error", error=repr(e))
