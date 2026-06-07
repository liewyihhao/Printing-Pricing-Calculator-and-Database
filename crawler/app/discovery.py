"""Discover a product's option structure and persist it.

Reads the live <select> controls (Size, Paper) and records product metadata.
The dependent Lamination field is walked during enumeration (it depends on the
chosen Paper). Products that expose no standard pricing matrix are flagged
status='unsupported' rather than crashing the crawl.
"""
from __future__ import annotations

from playwright.async_api import Page
from sqlalchemy.orm import Session

from . import config
from .browser import polite_pause, ensure_session
from .logging_setup import log
from .models import Product, OptionGroup, OptionValue, utcnow

M = config.MATRIX_PREFIX
SIZE_SEL = f"select[name='{M}ddlSize']"
PAPER_SEL = f"select[name='{M}ddlPaper']"


async def read_options(page: Page, selector: str) -> list[dict]:
    """Return [{value, text}] for a <select>, or [] if it's absent."""
    if await page.locator(selector).count() == 0:
        return []
    return await page.locator(selector).first.evaluate(
        "el => [...el.options].map(o => ({value:o.value, text:o.text.trim()}))")


async def read_products(page: Page) -> list[dict]:
    """Read the ddlProduct list: [{id, name}]."""
    sel = f"select[name='{config.PRODUCT_SELECT}']"
    opts = await read_options(page, sel)
    out, seen = [], set()
    for o in opts:
        v = (o["value"] or "").strip()
        if not v.isdigit():
            continue
        key = (v, o["text"])
        if key in seen:
            continue
        seen.add(key)
        out.append({"id": int(v), "name": o["text"]})
    return out


async def goto_product(page: Page, product_id: int) -> bool:
    """Load a product's matrix. Try the direct URL, then ddlProduct fallback.
    Returns True if the standard Size matrix is present."""
    await page.goto(f"{config.BASE_URL}/price-list/Litho/{product_id}",
                    wait_until="domcontentloaded")
    await polite_pause()
    await ensure_session(page)
    if await page.locator(SIZE_SEL).count() > 0:
        return True

    # Fallback: switch product via the ddlProduct dropdown on the base page.
    await page.goto(config.PRICE_URL, wait_until="domcontentloaded")
    await polite_pause()
    sel = f"select[name='{config.PRODUCT_SELECT}']"
    if await page.locator(sel).count():
        try:
            await page.select_option(sel, value=str(product_id))
            await page.wait_for_load_state("networkidle", timeout=15000)
            await polite_pause()
        except Exception:
            pass
    return await page.locator(SIZE_SEL).count() > 0


def _upsert_group(session: Session, product_id: int, name: str,
                  field_name: str, ordinal: int) -> OptionGroup:
    grp = (session.query(OptionGroup)
           .filter_by(product_id=product_id, field_name=field_name).one_or_none())
    if grp is None:
        grp = OptionGroup(product_id=product_id, name=name,
                          field_name=field_name, ordinal=ordinal)
        session.add(grp)
        session.flush()
    return grp


def upsert_values(session: Session, group: OptionGroup, options: list[dict]) -> None:
    existing = {v.raw_value for v in group.values}
    for i, o in enumerate(options):
        raw = o["value"]
        if raw in existing:
            continue
        # Skip placeholder "- Please Select -" (empty value).
        if raw == "" or o["text"].strip().startswith("- Please Select"):
            continue
        session.add(OptionValue(group_id=group.id, raw_value=raw,
                                label=o["text"], ordinal=i))


async def discover_product(session: Session, page: Page, product_id: int,
                           name: str | None = None) -> Product:
    """Persist a product's Size/Paper option metadata. Flags unsupported."""
    product = session.get(Product, product_id)
    if product is None:
        product = Product(excard_id=product_id, name=name or f"product_{product_id}",
                          category="Litho")
        session.add(product)
        session.flush()
    elif name:
        product.name = name

    has_matrix = await goto_product(page, product_id)
    if not has_matrix:
        product.status = "unsupported"
        product.note = "No standard Size matrix on price-list page."
        log.warning("discover.unsupported", product=product_id, name=product.name)
        session.flush()
        return product

    sizes = await read_options(page, SIZE_SEL)
    papers = await read_options(page, PAPER_SEL)
    g_size = _upsert_group(session, product_id, "Size", f"{M}ddlSize", 0)
    g_paper = _upsert_group(session, product_id, "Paper", f"{M}ddlPaper", 1)
    session.flush()
    upsert_values(session, g_size, sizes)
    upsert_values(session, g_paper, papers)
    product.status = "active"
    product.last_crawled = utcnow()
    session.flush()
    log.info("discover.ok", product=product_id, name=product.name,
             sizes=len(sizes), papers=len(papers))
    return product
