"""Sample Arch File (Digital) prices. Fixed spec — Steel Binding (4 ring & Metal Clip)
+ Wire-O + Oval curve + 2 L-shape corner + Lamination (Front), all compulsory/included.
Only driver: QUANTITY (ddlQty 20..500). Saves output/archfile_samples.json: {"core":[{qty,cash}]}.

  python -m app.archfile_sampler [account]
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
URL = "https://www.excard.com.my/spec/Digital/Arch_File"
QTYS = [20, 40, 60, 80, 100, 200, 300, 400, 500]


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "archfile_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"core": []}
    done = {r["qty"] for r in data["core"]}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.0)
        prev = None
        for q in QTYS:
            if q in done:
                continue
            if not await _sel(page, "ddlQty", str(q)):
                continue
            await asyncio.sleep(1.0)
            c = (await _safe_read(page)).get("before_discount")
            if c and c != prev:
                data["core"].append({"qty": q, "cash": c}); prev = c
            elif c == prev:
                await _sel(page, "ddlQty", str(QTYS[0])); await _sel(page, "ddlQty", str(q))
                await asyncio.sleep(1.0); c = (await _safe_read(page)).get("before_discount")
                if c and c != prev:
                    data["core"].append({"qty": q, "cash": c}); prev = c
            out.write_text(json.dumps(data, indent=0)); log.info("af.q", q=q, cash=c)
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: core={len(data['core'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
