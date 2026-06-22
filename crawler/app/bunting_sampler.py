"""Sample Bunting (Litho) prices. Drivers: ddlSize (3) x ddlPaper (2) x comboQty (1-300).

Saves output/bunting_samples.json: {"data": [{size, paper, qty, cash}]}.
  python -m app.bunting_sampler [account]
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
URL = "https://www.excard.com.my/spec/Litho/Bunting"

SIZES = ["2ft x 5ft", "2ft x 6ft", "2.5ft x 6ft"]
PAPERS = ["Tarpaulin 300gsm", "Synthetic Paper 180micron"]
QTYS = [1, 2, 3, 5, 10, 20, 30, 50, 100, 200, 300]


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "bunting_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"data": []}
    done = {(r["size"], r["paper"], r["qty"]) for r in data["data"]}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for size in SIZES:
            for paper in PAPERS:
                await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.0)
                if not await _sel(page, "ddlSize", size):
                    log.warning("bunting.size_fail", size=size); continue
                await asyncio.sleep(0.5)
                if not await _sel(page, "ddlPaper", paper):
                    log.warning("bunting.paper_fail", paper=paper); continue
                await asyncio.sleep(0.5)
                for q in QTYS:
                    if (size, paper, q) in done:
                        continue
                    if not await _sel(page, "comboQty", str(q)):
                        log.warning("bunting.qty_fail", size=size, paper=paper, qty=q); continue
                    await asyncio.sleep(1.0)
                    r = await _safe_read(page)
                    c = r.get("before_discount")
                    if not c:
                        log.warning("bunting.no_price", size=size, paper=paper, qty=q); continue
                    data["data"].append({"size": size, "paper": paper, "qty": q, "cash": c})
                    done.add((size, paper, q))
                    out.write_text(json.dumps(data, indent=0))
                    log.info("bunting", size=size, paper=paper, qty=q, cash=c)
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: {len(data['data'])} pts")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
