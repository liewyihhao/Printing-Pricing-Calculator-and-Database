"""Sample Banner (Litho) prices. Drivers: ddlSize (10 fixed) x comboQty (1-300).
No paper dropdown on the Banner form (material included in fixed spec).

Saves output/banner_samples.json: {"data": [{size, qty, cash}]}.
  python -m app.banner_sampler [account]
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
URL = "https://www.excard.com.my/spec/Litho/Banner"

SIZES = ["3ft x 2ft", "4ft x 2ft", "6ft x 2ft", "4ft x 3ft", "8ft x 3ft",
         "10ft x 3ft", "18ft x 3ft", "8ft x 4ft", "10ft x 4ft", "20ft x 4ft"]
QTYS = [1, 2, 3, 5, 10, 20, 30, 50, 100, 200, 300]


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "banner_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"data": []}
    done = {(r["size"], r["qty"]) for r in data["data"]}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for size in SIZES:
            await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.0)
            if not await _sel(page, "ddlSize", size):
                log.warning("banner.size_fail", size=size); continue
            await asyncio.sleep(0.5)
            for q in QTYS:
                if (size, q) in done:
                    continue
                if not await _sel(page, "comboQty", str(q)):
                    log.warning("banner.qty_fail", size=size, qty=q); continue
                await asyncio.sleep(1.0)
                r = await _safe_read(page)
                c = r.get("before_discount")
                if not c:
                    log.warning("banner.no_price", size=size, qty=q); continue
                data["data"].append({"size": size, "qty": q, "cash": c})
                done.add((size, q))
                out.write_text(json.dumps(data, indent=0))
                log.info("banner", size=size, qty=q, cash=c)
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: {len(data['data'])} pts")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
