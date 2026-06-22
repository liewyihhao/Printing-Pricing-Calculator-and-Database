"""Sample the cover-lamination options the parity checker flagged on Folder & Bookmark,
at each product's reference config, to determine if they are priced (delta) or price-neutral.

Saves output/fb_lam.json: {folder:[{lam,qty,cash}], bookmark:[{lam,qty,cash}]}
  python -m app.fb_lam_sampler [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .logging_setup import log
from .billbook_sampler import _sel, _safe_read, _wait

OUT = Path(__file__).resolve().parent.parent / "output"
QTYS = [500, 1000]
FOLDER_URL = "https://www.excard.com.my/spec/Litho/Folder"
BOOKMARK_URL = "https://www.excard.com.my/spec/Digital/Bookmark"


async def _radio(page, name, value):
    loc = page.locator(f"input[name$='{name}']"); n = await loc.count()
    for i in range(n):
        if (await loc.nth(i).get_attribute("value")) == value:
            try:
                await loc.nth(i).check()
            except Exception:
                await page.evaluate("(el)=>el.click()", await loc.nth(i).element_handle())
            await _wait(page); await asyncio.sleep(1.0); return True
    return False


async def _opts(page, name):
    sel = f"select[name$='{name}']"
    if not await page.locator(sel).count():
        return []
    return await page.locator(sel).first.evaluate(
        "el=>[...el.options].map(o=>o.text.trim()).filter(t=>t && !/^-|please select/i.test(t))")


async def _read(page, q):
    if not await _sel(page, "comboQty", str(q)):
        return None
    await asyncio.sleep(1.0)
    return (await _safe_read(page)).get("before_discount")


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "fb_lam.json"
    data = json.loads(out.read_text()) if out.exists() else {"folder": [], "bookmark": []}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1600})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        # FOLDER: PF group, first mould, ref paper, sweep lamination options
        if not data["folder"]:
            async def fcfg(lam):
                await page.goto(FOLDER_URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.8)
                await _radio(page, "rblMouldGroup", "PF")
                await page.evaluate(r"""()=>{const r=document.querySelector("input[name$='rblMould']");if(r)r.click();}""")
                await _wait(page); await asyncio.sleep(1.2)
                await _sel(page, "ddlPaper", "Gloss Art Card 250gsm (1 side coated)")
                return await _sel(page, "rblLaminationSide", lam)
            await page.goto(FOLDER_URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.8)
            await _radio(page, "rblMouldGroup", "PF")
            await page.evaluate(r"""()=>{const r=document.querySelector("input[name$='rblMould']");if(r)r.click();}""")
            await _wait(page); await asyncio.sleep(1.2)
            lams = await _opts(page, "rblLaminationSide")
            for lam in lams:
                if not await fcfg(lam):
                    continue
                for q in QTYS:
                    c = await _read(page, q)
                    if c:
                        data["folder"].append({"lam": lam, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("fd.lam", lam=lam[:24])

        # BOOKMARK: ref paper + 4C Front, sweep lamination options
        if not data["bookmark"]:
            async def bcfg(lam):
                await page.goto(BOOKMARK_URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.8)
                await _sel(page, "ddlPaper", "Gloss Art Card 250gsm (2 sides coated)")
                await _sel(page, "rblPrintColourSide", "4C (Front)")
                return await _sel(page, "rblLaminationSide", lam)
            await page.goto(BOOKMARK_URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.8)
            await _sel(page, "ddlPaper", "Gloss Art Card 250gsm (2 sides coated)")
            await _sel(page, "rblPrintColourSide", "4C (Front)")
            lams = await _opts(page, "rblLaminationSide")
            for lam in lams:
                if not await bcfg(lam):
                    continue
                for q in QTYS:
                    c = await _read(page, q)
                    if c:
                        data["bookmark"].append({"lam": lam, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("bm.lam", lam=lam[:24])

        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: folder={len(data['folder'])} bookmark={len(data['bookmark'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
