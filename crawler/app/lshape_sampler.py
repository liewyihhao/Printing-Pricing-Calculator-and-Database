"""Sample L-Shape Plastic Folder (Digital) prices.

Fixed model LSF 001, size 310x442mm, print colour 4C (fixed). Drivers: PAPER
(Synthetic Paper 180micron / Frosted Plastic 200 micron) x QUANTITY.
Saves output/lshape_samples.json: {"core":[{paper,qty,cash}]}.

  python -m app.lshape_sampler [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .logging_setup import log
from .billbook_sampler import _sel, _safe_read, _wait, _opts

OUT = Path(__file__).resolve().parent.parent / "output"
URL = "https://www.excard.com.my/spec/Digital/L_Shape_Plastic_Folder"
PAPERS = ["Synthetic Paper 180micron", "Frosted Plastic 200 micron (0.2mm)"]
QTYS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 2000, 3000, 4000]


async def _config(page, paper):
    await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.8)
    if not await _sel(page, "ddlPaper", paper):
        return False
    await asyncio.sleep(1.0)
    cols = await _opts(page, "rblPrintColourSide")  # set colour if a choice exists (4C fixed)
    if cols:
        await _sel(page, "rblPrintColourSide", cols[0])
        await asyncio.sleep(0.6)
    return True


async def _sweep(page):
    res = {}; prev = None
    for q in QTYS:
        if not await _sel(page, "comboQty", str(q)):
            continue
        await asyncio.sleep(1.0)
        c = (await _safe_read(page)).get("before_discount")
        if c and c != prev:
            res[q] = c; prev = c
        elif c == prev:
            await _sel(page, "comboQty", str(QTYS[0])); await _sel(page, "comboQty", str(q))
            await asyncio.sleep(1.0); c = (await _safe_read(page)).get("before_discount")
            if c:
                res[q] = c; prev = c
    return res


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "lshape_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"core": []}
    done = {r["paper"] for r in data["core"] if sum(1 for x in data["core"] if x["paper"] == r["paper"]) >= 6}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for paper in PAPERS:
            if paper in done:
                continue
            if not await _config(page, paper):
                log.info("lsf.cfg_fail", paper=paper[:20]); continue
            res = await _sweep(page)
            for q, c in res.items():
                data["core"].append({"paper": paper, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("lsf.core", paper=paper[:20], n=len(res))
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: core={len(data['core'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
