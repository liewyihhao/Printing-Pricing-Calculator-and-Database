"""Dump ALL visible selects + options in the 3-Layer Bill-Book state to find what gates
ddlSets. Try selecting comboQty first too.

  python -m app.billbook_dump3l [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login, polite_pause
from . import accounts
from .billbook_discover import _radio, _sel, _wait, URL

OUT = Path(__file__).resolve().parent.parent / "output"


async def _dump_all(page, tag):
    sels = await page.evaluate("""() => [...document.querySelectorAll('select')]
        .filter(s=>s.offsetParent).map(s=>({name:s.name.split('$').pop(),
        n:s.options.length, options:[...s.options].map(o=>o.text.trim()).filter(Boolean).slice(0,12)}))""")
    print(f"=== {tag} ===")
    for s in sels:
        print(f"  {s['name']} ({s['n']}): {s['options']}")
    return sels


async def run(account_id=1):
    a = accounts.get(account_id)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.0)
        await _radio(page, "rblPackForm", "Book"); await _radio(page, "rblPaper", "NCR")
        await _sel(page, "ddlSize", "A4 (210mm x 297mm)")
        await _sel(page, "ddlPaperMaterial", "NCR - 3 Layers"); await asyncio.sleep(0.6)
        await _dump_all(page, "3L after material (before tints)")
        ok1 = await _sel(page, "ddlLayer1", "NCR White 50gsm")
        ok2 = await _sel(page, "ddlLayer2", "NCR Green 50gsm")
        ok3 = await _sel(page, "ddlLayer3", "NCR Blue 50gsm")
        print(f"layer selects ok: {ok1},{ok2},{ok3}")
        await asyncio.sleep(0.8)
        await _dump_all(page, "3L after all 3 tints set")
        await _sel(page, "ddlPrintColorSide", "1C (Front)"); await asyncio.sleep(0.8)
        await _dump_all(page, "3L after tints + colour")
        try: await b.close()
        except Exception: pass


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
