"""Booklet (products 19 Litho & 37 Digital) cascade discovery.

The Booklet order form is structurally richer than Loose Sheet. Its cascade:

    rblOrientation (Portrait/Landscape)
      -> ddlSize (A4/A5/B5/A6/B5+)
        -> rdbOrderType (Soft Cover / Hard Cover)
          -> rdbidning (Saddle Stitch / Perfect Binding)
            -> ddlPage (8..80, multiples of 4)            [pages incl. cover]
            -> ddlCoverPaper  -> ddlCoverPrintColour       [async populate]
            -> ddlContentPaper -> ddlContentPrintColour     [async populate]
            -> rbOuterInner, comboQty, + extras

The cover/content paper option SETS depend on (orientation,size,ordertype,binding),
and print-colour sets depend on the chosen paper. We don't enumerate the full
cross-product as flat rows (it's huge and doesn't fit the Loose-Sheet schema);
instead we capture a NESTED option structure into output/booklet_options_<id>.json
that the UI selector + the pricing engine read.

Run:
    python -m app.booklet_discovery probe   [--product 19] [--account 1]
    python -m app.booklet_discovery walk    [--product 19] [--account 1]
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright, Page

from . import products, accounts, config
from .browser import launch, ensure_session, polite_pause
from .order_runner import _new_page, _relaunch
from .order_capture import _select  # reuse the polling <select> setter
from .logging_setup import log

# 'ends-with' name selectors (ASP.NET prefixes the container id).
ORIENT = "input[name$='rblOrientation']"
SIZE = "select[name$='ddlSize']"
ORDERTYPE = "input[name$='rdbOrderType']"
BINDING = "input[name$='rdbidning']"
PAGE = "select[name$='ddlPage']"
COVER_PAPER = "select[name$='ddlCoverPaper']"
COVER_COLOUR = "select[name$='ddlCoverPrintColour']"
CONTENT_PAPER = "select[name$='ddlContentPaper']"
CONTENT_COLOUR = "select[name$='ddlContentPrintColour']"
OUTER_INNER = "input[name$='rbOuterInner']"
QTY = "select[name$='comboQty']"

OUTPUT_DIR = config.OUTPUT_DIR


async def _opts(page: Page, sel: str) -> list[str]:
    """Real option labels for a <select> (drops placeholders)."""
    if await page.locator(sel).count() == 0:
        return []
    return await page.locator(sel).first.evaluate(
        "el => [...el.options].map(o => o.text.trim())"
        ".filter(t => t && !t.startsWith('- Please') && !t.startsWith('- Not')"
        " && !t.startsWith('- Select'))")


async def _radio_labels(page: Page, sel: str) -> list[str]:
    """Visible labels for a radio group (by following-text or value)."""
    n = await page.locator(sel).count()
    out = []
    for i in range(n):
        r = page.locator(sel).nth(i)
        # Prefer an associated <label>, else the radio's value attr.
        lab = await r.evaluate(
            "el => { const id=el.id; if(id){const l=document.querySelector(`label[for='${id}']`);"
            " if(l) return l.innerText.trim();} return (el.value||'').trim(); }")
        out.append(lab)
    return out


async def _check_radio(page: Page, sel: str, label: str) -> bool:
    """Check the radio in group `sel` whose label/value matches `label`."""
    n = await page.locator(sel).count()
    for i in range(n):
        r = page.locator(sel).nth(i)
        lab = await r.evaluate(
            "el => { const id=el.id; if(id){const l=document.querySelector(`label[for='${id}']`);"
            " if(l) return l.innerText.trim();} return (el.value||'').trim(); }")
        if lab == label or label in lab:
            await r.check()
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            await polite_pause()
            return True
    return False


async def _load(page: Page, target) -> None:
    await page.goto(target.spec_url, wait_until="domcontentloaded")
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    await ensure_session(page)


async def _dump_names(page: Page) -> dict:
    """Report the actual full `name` attributes present, to confirm selectors."""
    return await page.evaluate(
        "() => { const r={}; for (const el of document.querySelectorAll('select,input'))"
        " { if(!el.name) continue; const key=el.tagName+':'+el.type;"
        " (r[el.name]=r[el.name]||{tag:el.tagName,type:el.type,count:0}).count++; } return r; }")


async def probe(product_id: int, account_id: int = 1):
    """Live reconnaissance: load the booklet page, set one representative path,
    and print what each control exposes + when paper dropdowns populate."""
    target = products.get(product_id)
    account = accounts.get(account_id)
    async with async_playwright() as pw:
        browser = await launch(pw)
        page = await _new_page(browser, account=account)
        try:
            await _load(page, target)
            print(f"\n=== PROBE product {product_id} ({target.method}) {target.spec_url} ===")
            names = await _dump_names(page)
            booklet_ctrls = {k: v for k, v in names.items()
                             if any(t in k for t in
                                    ("Orientation", "ddlSize", "OrderType", "rdbidning",
                                     "ddlPage", "CoverPaper", "CoverPrintColour",
                                     "ContentPaper", "ContentPrintColour", "OuterInner",
                                     "comboQty"))}
            print("\n-- control names present --")
            for k, v in sorted(booklet_ctrls.items()):
                print(f"   {k}  ({v['tag']}/{v['type']} x{v['count']})")

            print("\n-- top-level options --")
            print("orientation:", await _radio_labels(page, ORIENT))
            print("sizes:", await _opts(page, SIZE))
            print("ordertype:", await _radio_labels(page, ORDERTYPE))
            print("binding:", await _radio_labels(page, BINDING))

            # Walk one representative path and watch paper dropdowns populate.
            print("\n-- setting Portrait / A5 / Soft Cover / Saddle Stitch --")
            await _check_radio(page, ORIENT, "Portrait")
            await _select(page, SIZE, "A5 (148mm x 210mm)")
            await _check_radio(page, ORDERTYPE, "Soft Cover")
            await _check_radio(page, BINDING, "Saddle Stitch")
            pages = await _opts(page, PAGE)
            print("pages:", pages)
            print("cover papers (before page):", await _opts(page, COVER_PAPER))
            # Paper dropdowns likely populate only after a page count is chosen.
            await _select(page, PAGE, "16")
            print("\n-- after selecting page=16 --")
            cps = await _opts(page, COVER_PAPER)
            print("cover papers:", cps)
            if cps:
                await _select(page, COVER_PAPER, cps[0])
                print(f"cover colours (paper={cps[0]!r}):", await _opts(page, COVER_COLOUR))
            cnt = await _opts(page, CONTENT_PAPER)
            print("content papers:", cnt)
            if cnt:
                await _select(page, CONTENT_PAPER, cnt[0])
                print(f"content colours (paper={cnt[0]!r}):", await _opts(page, CONTENT_COLOUR))
            print("outer/inner:", await _radio_labels(page, OUTER_INNER))
            print("qty:", await _opts(page, QTY))
        finally:
            try:
                await browser.close()
            except Exception:
                pass


async def _walk_combo(page: Page, target, orient: str, size: str,
                      ordertype: str, binding: str) -> dict | None:
    """Capture the option structure for one (orient,size,ordertype,binding).

    Cascade dependency learned from the live form:
        page -> coverPaper -> {coverColour, contentPaper -> contentColour}
    Content papers populate ONLY after a cover paper is chosen, and the set
    obeys "cover must be same/thicker than content". So we nest content under
    each cover paper. Colours are uniform, so we read them inline (no extra
    passes). Returns None if the combo is invalid (no pages/papers offered)."""
    await _load(page, target)
    if not await _check_radio(page, ORIENT, orient):
        return None
    if not await _select(page, SIZE, size):
        return None
    if not await _check_radio(page, ORDERTYPE, ordertype):
        return None
    if not await _check_radio(page, BINDING, binding):
        return None
    pages = await _opts(page, PAGE)
    if not pages:
        return None
    # Papers populate after a page is chosen; use the first (smallest) page where
    # the widest paper range is available.
    if not await _select(page, PAGE, pages[0]):
        return None
    cover_papers = await _opts(page, COVER_PAPER)
    if not cover_papers:
        return None  # truly invalid combo (e.g. Landscape on an unsupported size)

    covers: dict[str, dict] = {}
    content_colours: list[str] = []
    for cp in cover_papers:
        if not await _select(page, COVER_PAPER, cp):
            continue
        cover_colours = await _opts(page, COVER_COLOUR)
        content_papers = await _opts(page, CONTENT_PAPER)  # depends on this cover
        covers[cp] = {"colours": cover_colours, "content_papers": content_papers}
        # Read content colours once (uniform across content papers).
        if not content_colours and content_papers:
            if await _select(page, CONTENT_PAPER, content_papers[0]):
                content_colours = await _opts(page, CONTENT_COLOUR)
    outer_inner = await _radio_labels(page, OUTER_INNER)
    qty = await _opts(page, QTY)
    return {"pages": pages, "covers": covers, "content_colours": content_colours,
            "outer_inner": outer_inner, "qty": [q for q in qty if q != "Other"]}


async def walk(product_id: int, account_id: int = 1):
    """Full cascade walk -> output/booklet_options_<id>.json.

    Walks orientation x size x ordertype x binding, capturing each valid combo's
    pages / cover & content papers (+colours) / page->paper validity / qty."""
    target = products.get(product_id)
    account = accounts.get(account_id)
    out_path = OUTPUT_DIR / f"booklet_options_{product_id}.json"
    result: dict = {"product_id": product_id, "method": target.method,
                    "spec_url": target.spec_url, "combos": {}}
    # Resume support: reload any partial run so a relaunch doesn't lose progress.
    if out_path.exists():
        try:
            result = json.loads(out_path.read_text())
            result.setdefault("combos", {})
        except Exception:
            pass

    async with async_playwright() as pw:
        browser = await launch(pw)
        page = await _new_page(browser, account=account)
        try:
            await _load(page, target)
            orientations = await _radio_labels(page, ORIENT)
            sizes = await _opts(page, SIZE)
            ordertypes = await _radio_labels(page, ORDERTYPE)
            bindings = await _radio_labels(page, BINDING)
            log.info("booklet.walk_axes", product=product_id, orient=orientations,
                     sizes=sizes, ordertype=ordertypes, binding=bindings)
            done = 0
            for orient in orientations:
                for size in sizes:
                    for ot in ordertypes:
                        for binding in bindings:
                            key = f"{orient}|{size}|{ot}|{binding}"
                            if key in result["combos"]:
                                continue
                            try:
                                combo = await _walk_combo(page, target, orient,
                                                          size, ot, binding)
                            except Exception as e:  # relaunch on crash, then retry once
                                log.warning("booklet.combo_error", key=key,
                                            error=repr(e)[:120])
                                browser, page = await _relaunch(pw, browser, account)
                                try:
                                    combo = await _walk_combo(page, target, orient,
                                                              size, ot, binding)
                                except Exception as e2:
                                    log.error("booklet.combo_failed", key=key,
                                              error=repr(e2)[:120])
                                    combo = None
                            if combo:
                                result["combos"][key] = combo
                                done += 1
                                log.info("booklet.combo_done", key=key,
                                         pages=len(combo["pages"]),
                                         covers=len(combo["covers"]))
                            else:
                                # Mark invalid so resume doesn't retry it.
                                result["combos"][key] = None
                            out_path.write_text(json.dumps(result, indent=1))
                            # Recycle the browser periodically (ASP.NET state buildup).
                            if done and done % 6 == 0:
                                browser, page = await _relaunch(pw, browser, account)
        finally:
            try:
                await browser.close()
            except Exception:
                pass
    valid = sum(1 for v in result["combos"].values() if v)
    log.info("booklet.walk_done", product=product_id, valid=valid,
             total=len(result["combos"]), file=str(out_path))
    print(f"\nWrote {out_path}  ({valid} valid combos / {len(result['combos'])} probed)")


def _argval(flag, default):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "probe"
    pid = int(_argval("--product", "19"))
    acct = int(_argval("--account", "1"))
    if cmd == "probe":
        asyncio.run(probe(pid, acct))
    elif cmd == "walk":
        asyncio.run(walk(pid, acct))
    else:
        print("commands: probe | walk")
