"""Order-page capture for excard.com.my/spec/Litho/Loose_Sheet.

The order page is the ACCURATE pricing source (the /price-list page is ~2x off).
Its quirk: changing the quantity dropdown does NOT recompute the price (its
checkother() posts back with the wrong target). The price only recomputes on the
delivery (order_price) postback, and re-checking the same delivery radio is a
no-op. So the working recipe per quantity is:
    select comboQty=q  ->  toggle delivery (other country -> target)  ->  read.
"""
from __future__ import annotations

import re
import asyncio
from dataclasses import dataclass, field

from playwright.async_api import Page

from . import config
from .browser import polite_pause, ensure_session
from .logging_setup import log

SPEC_URL = "https://www.excard.com.my/spec/Litho/Loose_Sheet"
M = config.MATRIX_PREFIX  # Litho matrix prefix (kept for reference)
# 'ends-with' selectors so the SAME capture works across products whose control
# prefixes differ (Litho vs Digital use different order_spec controller names).
SIZE_SEL = "select[name$='ddlSize']"
PAPER_SEL = "select[name$='ddlPaper']"
COLOUR_SEL = "select[name$='rblPrintColourSide']"
PACKAGE_SEL = "select[name$='rblPackage']"
QTY_SEL = "select[name$='comboQty']"
DELIVERY_RADIO = "input[name$='rblOrderCountryCode']"

# A delivery code different from the target, used only to force a recompute toggle.
_TOGGLE_HELPER = {99: 98, 98: 99, 96: 99, 100: 99}


@dataclass
class OrderConfigSpec:
    product_id: int
    size_label: str
    paper_label: str
    colour_side: str
    package: str
    delivery_code: int
    # Optional per-product order-page URL. Defaults (None) to the Litho Loose
    # Sheet page so all existing callers behave exactly as before; other products
    # (e.g. Digital Loose Sheet) pass their own /spec/<Method>/<slug> URL.
    spec_url: str | None = None


@dataclass
class QuoteRow:
    quantity: int
    before_discount: float | None = None
    discount_amount: float | None = None
    after_discount: float | None = None
    handling_fee: float | None = None
    delivery_fee: float | None = None
    nett: float | None = None
    weight_kg: float | None = None
    tiers: dict = field(default_factory=dict)


def _money(text: str, label: str) -> float | None:
    m = re.search(label + r"\s*RM\s*([\d,]+\.\d{2})", text, re.I)
    return float(m.group(1).replace(",", "")) if m else None


def _parse_breakdown(text: str) -> dict:
    return {
        "before_discount": _money(text, "PRICE BEFORE DISCOUNT"),
        "discount_amount": _money(text, "DISCOUNT AMOUNT"),
        "after_discount": _money(text, "PRICE AFTER DISCOUNT"),
        "handling_fee": _money(text, "HANDLING FEE"),
        "delivery_fee": _money(text, "DELIVERY FEES"),
        "nett": _money(text, "Nett Price"),
    }


async def _select(page: Page, selector: str, label: str):
    if await page.locator(selector).count() == 0:
        return False
    # Option lists repopulate ASYNCHRONOUSLY after a prior selection's postback.
    # POLL for the target option before deciding it's absent — otherwise we
    # falsely skip VALID combinations whose option just hasn't loaded yet.
    has = False
    for _ in range(10):  # up to ~4s
        has = await page.locator(selector).first.evaluate(
            "(el, label) => [...el.options].some(o => o.text.trim() === label)", label)
        if has:
            break
        await asyncio.sleep(0.4)
    if not has:
        return False  # option genuinely not offered -> truly invalid combo
    await page.select_option(selector, label=label)
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    await polite_pause()
    return True


async def _check_delivery(page: Page, code: int):
    loc = page.locator(f"{DELIVERY_RADIO}[value='{code}']").first
    if await loc.count():
        await loc.check()
        try:
            await page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass
        await asyncio.sleep(0.5)


async def configure(page: Page, spec: OrderConfigSpec) -> bool:
    """Load the order page and set size/paper/colour/package. Reloads fresh each
    config to avoid stale-state races."""
    await page.goto(spec.spec_url or SPEC_URL, wait_until="domcontentloaded")
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    await ensure_session(page)
    if await page.locator(SIZE_SEL).count() == 0:
        # The order form didn't render. This is NOT an invalid combo — it means
        # the session/page failed to load (stale cookie, throttle). RAISE so the
        # runner relaunches + re-logins and RETRIES, instead of mis-marking the
        # config "skipped" and silently losing a valid combination.
        raise RuntimeError("order form not loaded (session/throttle) — will retry")
    if not await _select(page, SIZE_SEL, spec.size_label):
        return False
    if not await _select(page, PAPER_SEL, spec.paper_label):
        return False  # this paper isn't offered for this size — skip cleanly
    if not await _select(page, COLOUR_SEL, spec.colour_side):
        return False
    await _select(page, PACKAGE_SEL, spec.package)
    return True


async def available_quantities(page: Page) -> list[int]:
    if await page.locator(QTY_SEL).count() == 0:
        return []
    texts = await page.locator(QTY_SEL).evaluate(
        "el => [...el.options].map(o => o.text.trim()).filter(t => /^\\d/.test(t))")
    out = []
    for t in texts:
        digits = re.sub(r"[^\d]", "", t)
        if digits:
            out.append(int(digits))
    return sorted(set(out))


async def sweep_quantities(page: Page, spec: OrderConfigSpec,
                           quantities: list[int]) -> list[QuoteRow]:
    """For each quantity, force a recompute (qty -> toggle delivery helper then
    target) and read the order-accurate breakdown. The double toggle is required
    for RELIABILITY: a single toggle sometimes reads the price before the
    UpdatePanel postback settles, yielding a stale value. Accuracy > speed."""
    rows: list[QuoteRow] = []
    helper = _TOGGLE_HELPER.get(spec.delivery_code, 99)
    for q in quantities:
        # comboQty options carry packed values; select by visible label digits.
        opt_label = await page.locator(QTY_SEL).evaluate(
            "(el, q) => { const o=[...el.options].find(o=>o.text.replace(/[^0-9]/g,'')===String(q));"
            " return o ? o.text : null; }", q)
        if not opt_label:
            continue
        await page.select_option(QTY_SEL, label=opt_label)
        await asyncio.sleep(0.2)
        await _check_delivery(page, helper)
        await _check_delivery(page, spec.delivery_code)
        text = await page.evaluate("() => document.body.innerText")
        bd = _parse_breakdown(text)
        if bd["before_discount"] is None and bd["nett"] is None:
            continue  # nothing computed for this qty
        bd["weight_kg"] = await _read_weight(page)
        rows.append(QuoteRow(quantity=q, tiers={}, **bd))
    return rows


async def _read_weight(page: Page) -> float | None:
    """The order page exposes weight in #..._lblWeight ('Weight : X')."""
    try:
        txt = await page.locator("[id$='_lblWeight']").first.inner_text()
    except Exception:
        return None
    m = re.search(r"([\d,]+\.?\d*)", txt.split(":")[-1])
    return float(m.group(1).replace(",", "")) if m else None


async def capture_config(page: Page, spec: OrderConfigSpec) -> list[QuoteRow]:
    if not await configure(page, spec):
        log.warning("order.configure_failed", size=spec.size_label,
                    paper=spec.paper_label, colour=spec.colour_side,
                    package=spec.package)
        return []
    qtys = await available_quantities(page)
    if not qtys:
        return []
    rows = await sweep_quantities(page, spec, qtys)
    log.info("order.captured", size=spec.size_label, paper=spec.paper_label,
             colour=spec.colour_side, package=spec.package,
             delivery=spec.delivery_code, quantities=len(rows))
    return rows
