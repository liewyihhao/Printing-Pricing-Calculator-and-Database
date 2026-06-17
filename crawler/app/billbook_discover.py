"""Discover the Bill-Book cascade: drive the main controls step-by-step and dump the
dependent dropdowns (ddlSets, ddlBindingLocation, ddlBackPrintLayer) as they populate.

  python -m app.billbook_discover [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login, polite_pause
from . import accounts

OUT = Path(__file__).resolve().parent.parent / "output"
URL = "https://www.excard.com.my/spec/Litho/Bill-Book"


async def _wait(page):
    try: await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception: pass
    await polite_pause()


async def _radio(page, name, value):
    loc = page.locator(f"input[name$='{name}']")
    n = await loc.count()
    for i in range(n):
        if (await loc.nth(i).get_attribute("value")) == value:
            await loc.nth(i).check(); await _wait(page); return True
    return False


async def _sel(page, name, label):
    sel = f"select[name$='{name}']"
    if not await page.locator(sel).count():
        return False
    for _ in range(10):
        if await page.locator(sel).first.evaluate("(el,l)=>[...el.options].some(o=>o.text.trim()===l)", label):
            break
        await asyncio.sleep(0.4)
    try:
        await page.select_option(sel, label=label, timeout=6000); await _wait(page); return True
    except Exception:
        return False


async def _opts(page, name):
    sel = f"select[name$='{name}']"
    if not await page.locator(sel).count():
        return None
    return await page.locator(sel).first.evaluate(
        "el=>[...el.options].map(o=>o.text.trim()).filter(t=>t && !t.startsWith('-'))")


async def _dump(page, tag):
    snap = {n: await _opts(page, n) for n in
            ["ddlBindingLocation", "ddlBackPrintLayer", "ddlSets", "comboQty", "ddlPrintColorSide"]}
    print(f"--- {tag} ---")
    for k, v in snap.items():
        if v is not None:
            print(f"   {k}: {v}")
    return snap


async def run(account_id=1):
    a = accounts.get(account_id)
    result = {}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        for layers in ["NCR - 2 Layers", "NCR - 3 Layers", "NCR - 4 Layers"]:
            await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.0)
            await _radio(page, "rblPackForm", "Book")
            await _radio(page, "rblPaper", "NCR")
            await _sel(page, "ddlSize", "A4 (210mm x 297mm)")
            await _sel(page, "ddlPaperMaterial", layers)
            await _sel(page, "ddlPrintColorSide", "1C (Front)")
            await asyncio.sleep(0.8)
            snap = await _dump(page, f"Book/NCR/A4/{layers}/1C(Front)")
            result[layers] = snap

        # Pad form + Normal paper variation
        await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.0)
        await _radio(page, "rblPackForm", "Pad")
        await _radio(page, "rblPaper", "NCR")
        await _sel(page, "ddlSize", "A4 (210mm x 297mm)")
        await _sel(page, "ddlPaperMaterial", "NCR - 2 Layers")
        await _sel(page, "ddlPrintColorSide", "1C (Front)")
        await asyncio.sleep(0.8)
        result["pad_2L"] = await _dump(page, "Pad/NCR/A4/2L/1C(Front)")

        # higher-layer sets cascade: dump ddlBackPrintLayer, try selecting it, re-check ddlSets
        for layers in ["NCR - 3 Layers", "NCR - 4 Layers", "NCR - 5 Layers", "NCR - 6 Layer"]:
            await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.0)
            await _radio(page, "rblPackForm", "Book"); await _radio(page, "rblPaper", "NCR")
            await _sel(page, "ddlSize", "A4 (210mm x 297mm)")
            await _sel(page, "ddlPaperMaterial", layers)
            await _sel(page, "ddlPrintColorSide", "1C (Front)")
            await asyncio.sleep(0.6)
            bpl = await _opts(page, "ddlBackPrintLayer")
            sets_before = await _opts(page, "ddlSets")
            print(f"[{layers}] backPrintLayer={bpl} setsBEFORE={sets_before}")
            if bpl:
                await _sel(page, "ddlBackPrintLayer", bpl[0]); await asyncio.sleep(0.6)
            sets_after = await _opts(page, "ddlSets")
            print(f"[{layers}] setsAFTER(backlayer={bpl[0] if bpl else None})={sets_after}")
            result[f"{layers}_backlayer"] = {"backPrintLayer": bpl, "sets_before": sets_before, "sets_after": sets_after}

        OUT.joinpath("billbook_cascade.json").write_text(json.dumps(result, indent=1))
        try: await b.close()
        except Exception: pass


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
