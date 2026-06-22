"""Sample Mug (Litho) prices. Fixed spec (standard ceramic mug). Drivers: comboQty (20-300).
Saves output/mug_samples.json: {"core": [{qty, cash}]}.
  python -m app.mug_sampler [account]
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
URL = "https://www.excard.com.my/spec/Litho/Mug"
QTYS = [20, 40, 60, 80, 100, 200, 300]


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "mug_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"core": []}
    done = {r["qty"] for r in data["core"]}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.5)
        for q in QTYS:
            if q in done:
                continue
            if not await _sel(page, "comboQty", str(q)):
                log.warning("mug.qty_fail", qty=q); continue
            await asyncio.sleep(1.0)
            r = await _safe_read(page)
            c = r.get("before_discount")
            if not c:
                log.warning("mug.no_price", qty=q); continue
            data["core"].append({"qty": q, "cash": c})
            done.add(q)
            out.write_text(json.dumps(data, indent=0))
            log.info("mug", qty=q, cash=c)
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: {len(data['core'])} pts")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
