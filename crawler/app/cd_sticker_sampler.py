"""Sample the Label Sticker 'CD' type (www Digital order page).

CD is a fixed-shape disc label: NO cut category, NO size input. Price drivers are just
material (Mirror Kote / Printing Paper), colour (4C/1C), quantity, and package (xN).

Saves output/sticker_cd.json: {"curves": {"<paper>|<colour>": {qty: cash}}}

  python -m app.cd_sticker_sampler [account]
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
PAPERS = ["Mirror Kote", "Printing Paper"]
COLOURS = [("4C", "4C,1"), ("1C", "1C,1")]


async def _setup(page, paper, colour_prefix):
    await page.goto(DIGITAL, wait_until="domcontentloaded"); await _wait(page)
    await _radio_startswith(page, "rdType", "CD"); await asyncio.sleep(1.2); await _wait(page)
    await _sel(page, "ddlpaper", paper)
    await _radio_startswith(page, "rbprintcolour", colour_prefix)


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "sticker_cd.json"
    data = json.loads(out.read_text()) if out.exists() else {"curves": {}}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        # read the full ddlQty option ladder once
        await _setup(page, PAPERS[0], COLOURS[0][1])
        qtys = await page.locator("select[name$='ddlQty']").first.evaluate(
            "el=>[...el.options].map(o=>o.text.trim()).filter(t=>t && !t.startsWith('-'))")
        qtys = [int(q) for q in qtys if q.isdigit()]
        log.info("cd.qtys", n=len(qtys), qtys=qtys)
        for paper in PAPERS:
            for cname, cpfx in COLOURS:
                key = f"{paper}|{cname}"
                if data["curves"].get(key) and len(data["curves"][key]) >= len(qtys) - 1:
                    log.info("cd.skip", key=key); continue
                await _setup(page, paper, cpfx)
                curve = {}; prev = None
                for q in qtys:
                    if not await _sel(page, "ddlQty", str(q)):
                        continue
                    await asyncio.sleep(0.8)
                    c = (await _read_price(page)).get("before_discount")
                    if c and c != prev:
                        curve[str(q)] = c; prev = c
                    elif c == prev:  # stale guard
                        await _sel(page, "ddlQty", str(qtys[0])); await _sel(page, "ddlQty", str(q))
                        await asyncio.sleep(0.8); c = (await _read_price(page)).get("before_discount")
                        if c:
                            curve[str(q)] = c; prev = c
                data["curves"][key] = curve
                out.write_text(json.dumps(data, indent=0))
                log.info("cd.done", key=key, n=len(curve))
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: curves={list(data['curves'].keys())}")
    for k, cv in data["curves"].items():
        print(f"  {k}: {dict(list(cv.items())[:6])} ... ({len(cv)} pts)")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
