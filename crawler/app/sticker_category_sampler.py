"""Sample the Label Sticker alternative cut categories (beyond Rectangle/Custom Die-Cut):
  Round         -> txtDiameter (model as W=H=d with a round premium)
  Standard Shape-> txtHeight/txtWidth (H×W, premium vs Rectangle)
  No Cut        -> qty only (full-sheet; size-independent), per material
  Kiss Cut      -> ddlCutToSheet (sheet) + qty, per material

Saves output/sticker_categories.json:
  {"round": [{d, qty, cash}], "standard_shape": [{h,w,qty,cash}],
   "no_cut": [{paper, qty, cash}], "kiss_cut": [{sheet, qty, cash}]}

  python -m app.sticker_category_sampler [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .logging_setup import log
from .sticker_capture import DIGITAL, _wait, _radio_startswith, _sel, _read_price

OUT = Path(__file__).resolve().parent.parent / "output"
QTYS = [50, 100, 300, 500, 1000, 2000, 5000]


async def _setup(page, cat, paper="Mirror Kote"):
    await page.goto(DIGITAL, wait_until="domcontentloaded"); await _wait(page)
    await _radio_startswith(page, "rdType", "Sticker")
    await _radio_startswith(page, "rdCategory", cat); await asyncio.sleep(0.8)
    await _sel(page, "ddlpaper", paper)
    await _radio_startswith(page, "rbprintcolour", "4C,1")


async def _fill(page, name, val):
    el = page.locator(f"input[name$='{name}']").first
    if await el.count():
        await el.fill(str(val)); await el.dispatch_event("change"); await el.dispatch_event("blur")
        await _wait(page); return True
    return False


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "sticker_categories.json"
    data = json.loads(out.read_text()) if out.exists() else {"round": [], "standard_shape": [], "no_cut": [], "kiss_cut": []}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        # ROUND (diameter)
        for d in [30, 40, 50, 60, 80]:
            await _setup(page, "Round"); await _fill(page, "txtDiameter", d)
            prev = None
            for q in QTYS:
                await _sel(page, "ddlQty", str(q)); c = (await _read_price(page)).get("before_discount")
                if c and c != prev:
                    data["round"].append({"d": d, "qty": q, "cash": c}); prev = c
            out.write_text(json.dumps(data)); log.info("cat.round", d=d)

        # STANDARD SHAPE (H×W)
        for (h, w) in [(50, 50), (50, 90), (100, 100), (150, 150)]:
            await _setup(page, "Standard Shape"); await _fill(page, "txtHeight", h); await _fill(page, "txtWidth", w)
            prev = None
            for q in QTYS:
                await _sel(page, "ddlQty", str(q)); c = (await _read_price(page)).get("before_discount")
                if c and c != prev:
                    data["standard_shape"].append({"h": h, "w": w, "qty": q, "cash": c}); prev = c
            out.write_text(json.dumps(data)); log.info("cat.std", size=f"{h}x{w}")

        # NO CUT (qty only, per material)
        for paper in ["Mirror Kote", "White PP (Polypropylene)", "Synthetic Paper"]:
            await _setup(page, "No Cut", paper)
            prev = None
            for q in QTYS:
                await _sel(page, "ddlQty", str(q)); c = (await _read_price(page)).get("before_discount")
                if c and c != prev:
                    data["no_cut"].append({"paper": paper, "qty": q, "cash": c}); prev = c
            out.write_text(json.dumps(data)); log.info("cat.nocut", paper=paper[:12])

        # KISS CUT (ddlCutToSheet + qty)
        await _setup(page, "Kiss Cut (1up/sheet)")
        sheets = [o for o in await page.locator("select[name$='ddlCutToSheet']").first.evaluate(
            "el=>[...el.options].map(o=>o.text.trim())") if o and not o.startswith("- ")] \
            if await page.locator("select[name$='ddlCutToSheet']").count() else []
        log.info("cat.kiss_sheets", sheets=sheets)
        for sh in (sheets or [None]):
            await _setup(page, "Kiss Cut (1up/sheet)")
            if sh:
                await _sel(page, "ddlCutToSheet", sh)
            prev = None
            for q in QTYS:
                await _sel(page, "ddlQty", str(q)); c = (await _read_price(page)).get("before_discount")
                if c and c != prev:
                    data["kiss_cut"].append({"sheet": sh, "qty": q, "cash": c}); prev = c
            out.write_text(json.dumps(data)); log.info("cat.kiss", sheet=sh)
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: round={len(data['round'])} std={len(data['standard_shape'])} "
          f"no_cut={len(data['no_cut'])} kiss_cut={len(data['kiss_cut'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
