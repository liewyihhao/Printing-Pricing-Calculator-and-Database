"""Sample Paper Bag (Litho) prices. Fixed size. Drivers: ddlPaper (2) x comboQty (50-500).
Rope colour (5 options) is likely price-neutral — we sample the base price only.
Folding + Gluing + Hole Punching compulsory (included).

Saves output/paperbag_samples.json: {"data": [{paper, qty, cash}]}.
  python -m app.paperbag_sampler [account]
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
URL = "https://www.excard.com.my/spec/Litho/Paper_Bag"

PAPERS = ["Gloss Art Paper 157gsm", "Gloss Art Card 190gsm (1 side coated)"]
QTYS = [50, 100, 200, 300, 500]


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "paperbag_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"data": []}
    done = {(r["paper"], r["qty"]) for r in data["data"]}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for paper in PAPERS:
            await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.0)
            if not await _sel(page, "ddlPaper", paper):
                log.warning("paperbag.paper_fail", paper=paper); continue
            await asyncio.sleep(0.5)
            for q in QTYS:
                if (paper, q) in done:
                    continue
                if not await _sel(page, "comboQty", str(q)):
                    log.warning("paperbag.qty_fail", paper=paper, qty=q); continue
                await asyncio.sleep(1.0)
                r = await _safe_read(page)
                c = r.get("before_discount")
                if not c:
                    log.warning("paperbag.no_price", paper=paper, qty=q); continue
                data["data"].append({"paper": paper, "qty": q, "cash": c})
                done.add((paper, q))
                out.write_text(json.dumps(data, indent=0))
                log.info("paperbag", paper=paper, qty=q, cash=c)
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: {len(data['data'])} pts")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
