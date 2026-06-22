"""Sample Wire-O Wall Calendar (Litho) prices.
Fixed spec; only driver: QUANTITY. Saves output/wireow_samples.json: {"core":[{qty,cash}]}.

  python -m app.wireow_sampler [account]
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
URL = "https://www.excard.com.my/spec/Litho/Wire-O_Wall_Calendar"
QTYS = [100, 200, 300, 500, 1000, 1500, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "wireow_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"core": []}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.5)
        prev = None
        for q in QTYS:
            if any(r["qty"] == q for r in data["core"]):
                continue
            if not await _sel(page, "comboQty", str(q)):
                log.warning("wireow.qty_fail", qty=q); continue
            await asyncio.sleep(1.0)
            c = (await _safe_read(page)).get("before_discount")
            if c and c != prev:
                data["core"].append({"qty": q, "cash": c}); prev = c
            elif c == prev:
                await _sel(page, "comboQty", str(QTYS[0])); await _sel(page, "comboQty", str(q))
                await asyncio.sleep(1.0); c = (await _safe_read(page)).get("before_discount")
                if c and c != prev:
                    data["core"].append({"qty": q, "cash": c}); prev = c
            out.write_text(json.dumps(data, indent=0))
            log.info("wireow.q", qty=q, cash=c)
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: core={len(data['core'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
