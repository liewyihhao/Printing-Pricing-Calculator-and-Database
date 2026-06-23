"""Sample Standing Pouch (Litho) prices. Drivers: ddlPaper(2) x comboQty(100..5000),
with a compulsory rblLaminationSide that resets on qty change (re-applied per qty).
Saves output/pouch_samples.json: {"core":[{variant,qty,cash}], "lam":[...]}  (variant=paper).

  python -m app.pouch_sampler [account]
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
URL = "https://www.excard.com.my/spec/Litho/Standing_Pouch"
PAPERS = ["Metalised Pet Film", "Transparent Pet Film"]
QTYS = [100, 200, 300, 500, 1000, 2000, 3000, 5000]


async def _sweep(page, qtys, lam_value, prev=None):
    res = {}
    for q in qtys:
        if not await _sel(page, "comboQty", str(q)):
            continue
        if lam_value:
            await asyncio.sleep(0.35); await _sel(page, "rblLaminationSide", lam_value)
        c = None
        for _ in range(12):
            await asyncio.sleep(0.6)
            c = (await _safe_read(page)).get("before_discount")
            if c is not None and c != 0 and (prev is None or c != prev):
                break
        if c:
            res[q] = c; prev = c
    return res


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "pouch_samples.json"
    data = {"core": [], "lam": []}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1500})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for paper in PAPERS:
            await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.5)
            if not await _sel(page, "ddlPaper", paper):
                log.warning("pouch.paper_fail", paper=paper); continue
            await asyncio.sleep(0.5)
            lo = await _opts(page, "rblLaminationSide")
            res = await _sweep(page, QTYS, lo[0] if lo else None)
            for q, c in res.items():
                data["core"].append({"variant": paper, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("pouch", paper=paper, n=len(res))
        # lamination neutrality on Metalised at qty 500
        await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.5)
        await _sel(page, "ddlPaper", PAPERS[0]); await asyncio.sleep(0.5)
        for lam in (await _opts(page, "rblLaminationSide")):
            r = await _sweep(page, [500], lam)
            for q, c in r.items():
                data["lam"].append({"lam": lam, "qty": q, "cash": c})
        out.write_text(json.dumps(data, indent=0)); log.info("pouch.lam", n=len(data["lam"]))
        try: await b.close()
        except Exception: pass
    print(f"done pouch: core={len(data['core'])} lam={len(data['lam'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
