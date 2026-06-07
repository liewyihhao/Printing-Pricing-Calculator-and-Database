"""Nested guided-walk enumeration → work queue.

Excard's option lists are dependent: the available Papers depend on the chosen
Size, and the available Laminations depend on the chosen Paper. The option
*values* also embed size-dependent data, so we select and identify everything by
stable LABEL. We walk the form live (size -> papers -> laminations) and emit one
Combination + WorkItem per valid (size, paper, lamination, delivery), deduped by
combo_hash. Idempotent and checkpointed per size.
"""
from __future__ import annotations

from playwright.async_api import Page
from sqlalchemy.orm import Session

from . import config
from .browser import polite_pause
from .logging_setup import log
from .discovery import (discover_product, read_options, SIZE_SEL, PAPER_SEL,
                        _upsert_group)
from .models import OptionGroup, OptionValue, Combination, WorkItem, combo_hash

M = config.MATRIX_PREFIX
LAMINATION_SEL = f"select[name='{M}rblLaminationSide']"


def _is_placeholder(text: str) -> bool:
    t = text.strip()
    return (t == "" or t.startswith("- Please Select")
            or t.startswith("- Not Required") or "required" in t.lower())


async def _select(page: Page, selector: str, label: str):
    await page.select_option(selector, label=label)
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    await polite_pause()


def _upsert_value(session: Session, group: OptionGroup, raw: str, label: str, ordinal: int):
    exists = (session.query(OptionValue)
              .filter_by(group_id=group.id, raw_value=raw).first())
    if not exists:
        session.add(OptionValue(group_id=group.id, raw_value=raw,
                                label=label, ordinal=ordinal))


def _make_combo(session: Session, product_id: int, delivery_code: int,
                size: dict, paper: dict, lam: dict | None) -> bool:
    """Upsert a Combination + pending WorkItem keyed by label-based hash."""
    h = combo_hash(product_id, size["label"], paper["label"],
                   lam["label"] if lam else "", delivery_code)
    if session.query(Combination).filter_by(combo_hash=h).first():
        return False
    c = Combination(
        product_id=product_id, combo_hash=h, delivery_code=delivery_code,
        size_raw=size["value"], size_label=size["label"],
        paper_raw=paper["value"], paper_label=paper["label"],
        lamination_raw=(lam["value"] if lam else None),
        lamination_label=(lam["label"] if lam else None),
    )
    session.add(c)
    session.flush()
    session.add(WorkItem(combination_id=c.id, status="pending"))
    return True


async def enqueue_product(session: Session, page: Page, product_id: int,
                          name: str | None = None) -> int:
    """Live nested walk: size -> papers(size) -> laminations(paper) -> combos."""
    product = await discover_product(session, page, product_id, name)
    if product.status == "unsupported":
        return 0

    g_size = _upsert_group(session, product_id, "Size", f"{M}ddlSize", 0)
    g_paper = _upsert_group(session, product_id, "Paper", f"{M}ddlPaper", 1)
    g_lam = _upsert_group(session, product_id, "Lamination", LAMINATION_SEL, 2)
    session.flush()

    sizes = [o for o in await read_options(page, SIZE_SEL) if not _is_placeholder(o["text"])]
    if not sizes:
        log.warning("enqueue.no_sizes", product=product_id)
        return 0

    created = 0
    for si, size in enumerate(sizes):
        size = {"value": size["value"], "label": size["text"]}
        await _select(page, SIZE_SEL, size["label"])
        _upsert_value(session, g_size, size["value"], size["label"], si)

        papers = [o for o in await read_options(page, PAPER_SEL)
                  if not _is_placeholder(o["text"])]
        for pi, p in enumerate(papers):
            paper = {"value": p["value"], "label": p["text"]}
            await _select(page, PAPER_SEL, paper["label"])
            _upsert_value(session, g_paper, paper["value"], paper["label"], pi)

            lam_opts = [o for o in await read_options(page, LAMINATION_SEL)
                        if not _is_placeholder(o["text"])]
            lam_list = ([{"value": o["value"], "label": o["text"]} for o in lam_opts]
                        or [None])
            for li, lam in enumerate(lam_list):
                if lam:
                    _upsert_value(session, g_lam, lam["value"], lam["label"], li)
                for delivery_code in config.DELIVERIES:
                    if _make_combo(session, product_id, delivery_code, size, paper, lam):
                        created += 1
        session.commit()  # checkpoint after each size
        log.info("enqueue.size_done", product=product_id, size=size["label"],
                 papers=len(papers), created_so_far=created)

    log.info("enqueue.done", product=product_id, sizes=len(sizes), created=created)
    return created
