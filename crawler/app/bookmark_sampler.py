"""Sample Bookmark (Digital) prices.

Fixed bookmark size. Drivers: PAPER (7; Vellum is Out of Stock) x PRINT COLOUR
(4C Front / 4C Both) x QUANTITY, + finishing deltas: Round Cornering (R6), Hole
Punching (6mm). Saves output/bookmark_samples.json:
  {"core":[{paper,colour,qty,cash}], "finishing":[{kind,qty,cash}]}

  python -m app.bookmark_sampler [account]
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
URL = "https://www.excard.com.my/spec/Digital/Bookmark"
PAPERS = ["Gloss Art Card 250gsm (2 sides coated)", "Gloss Art Card 310gsm (2 sides coated)",
          "Super White 250gsm", "Linen 240gsm", "Suwen 240gsm", "Synthetic Paper 180micron",
          "Metal Ice 250gsm"]
COLOURS = ["4C (Front)", "4C (Both)"]
QTYS = [100, 300, 500, 1000, 2000, 5000, 10000, 20000]
RC_VAL = "Round Cornering (R6),4,1"
HP_VAL = "Hole Punching (6mm),1"


async def _radio(page, name, value):
    loc = page.locator(f"input[name$='{name}']"); n = await loc.count()
    for i in range(n):
        if (await loc.nth(i).get_attribute("value")) == value:
            try:
                await loc.nth(i).check()
            except Exception:
                await page.evaluate("(el)=>el.click()", await loc.nth(i).element_handle())
            await _wait(page); await asyncio.sleep(0.8); return True
    return False


async def _config(page, paper, colour):
    await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.8)
    if not await _sel(page, "ddlPaper", paper):
        return False
    if not await _sel(page, "rblPrintColourSide", colour):
        return False
    await asyncio.sleep(0.6)
    return True


async def _sweep(page, qtys):
    res = {}; prev = None
    for q in qtys:
        if not await _sel(page, "comboQty", str(q)):
            continue
        await asyncio.sleep(0.9)
        c = (await _safe_read(page)).get("before_discount")
        if c and c != prev:
            res[q] = c; prev = c
        elif c == prev:
            await _sel(page, "comboQty", str(qtys[0])); await _sel(page, "comboQty", str(q))
            await asyncio.sleep(0.9); c = (await _safe_read(page)).get("before_discount")
            if c:
                res[q] = c; prev = c
    return res


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "bookmark_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"core": [], "finishing": []}
    done = {(r["paper"], r["colour"]) for r in data["core"]
            if sum(1 for x in data["core"] if x["paper"] == r["paper"] and x["colour"] == r["colour"]) >= 5}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1500})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for paper in PAPERS:
            for colour in COLOURS:
                if (paper, colour) in done:
                    continue
                if not await _config(page, paper, colour):
                    log.info("bm.cfg_fail", paper=paper[:18], colour=colour); continue
                res = await _sweep(page, QTYS)
                for q, c in res.items():
                    data["core"].append({"paper": paper, "colour": colour, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("bm.core", paper=paper[:16], colour=colour, n=len(res))

        # finishing deltas at (Gloss Art Card 250, 4C Front)
        if not data["finishing"]:
            for kind, val in [("base", None), ("round_corner", RC_VAL), ("hole_punch", HP_VAL)]:
                if not await _config(page, PAPERS[0], "4C (Front)"):
                    continue
                if val:
                    await _radio(page, "rblRoundCorner" if kind == "round_corner" else "rblPunchHole", val)
                res = await _sweep(page, [500, 5000])
                for q, c in res.items():
                    data["finishing"].append({"kind": kind, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("bm.fin", kind=kind, n=len(res))
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: core={len(data['core'])} finishing={len(data['finishing'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
