"""Sample Magnet (Digital) prices. Drivers: rdCategory (shape) x ddlQty, with a compulsory
ddlfinishing (lamination) that resets on qty change (re-applied per qty). 'External' shape
is a supply option (skipped). Saves output/magnet_samples.json:
  {"core":[{variant,qty,cash}], "fin":[{fin,qty,cash}]}  (variant = shape)

  python -m app.magnet_sampler [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .logging_setup import log
from .billbook_sampler import _sel, _safe_read, _wait, _radio, _opts

OUT = Path(__file__).resolve().parent.parent / "output"
URL = "https://www.excard.com.my/spec/Digital/Magnet"
SHAPES = [("Rectangle/Square,1", "Rectangle/Square"), ("Round,1", "Round"),
          ("Custom Die-Cut (with round corner),3", "Custom Die-Cut")]
QTYS = [10, 30, 50, 70, 100, 150, 200, 250]


async def _sweep(page, qtys, fin_value, prev=None):
    res = {}
    for q in qtys:
        if not await _sel(page, "ddlQty", str(q)):
            continue
        if fin_value:
            await asyncio.sleep(0.35); await _sel(page, "ddlfinishing", fin_value)
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
    out = OUT / "magnet_samples.json"
    data = {"core": [], "fin": []}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1500})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for val, label in SHAPES:
            await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.2)
            await _radio(page, "rdType", "Magnet"); await asyncio.sleep(0.4)
            if not await _radio(page, "rdCategory", val):
                log.warning("magnet.shape_fail", shape=val); continue
            await asyncio.sleep(0.6)
            fopts = await _opts(page, "ddlfinishing")
            fin0 = fopts[0] if fopts else None
            res = await _sweep(page, QTYS, fin0)
            for q, c in res.items():
                data["core"].append({"variant": label, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("magnet", shape=label, n=len(res))
        # finishing neutrality test on Rectangle at qty 100
        await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.2)
        await _radio(page, "rdType", "Magnet"); await asyncio.sleep(0.3)
        await _radio(page, "rdCategory", SHAPES[0][0]); await asyncio.sleep(0.5)
        for fin in (await _opts(page, "ddlfinishing")):
            r = await _sweep(page, [100], fin)
            for q, c in r.items():
                data["fin"].append({"fin": fin, "qty": q, "cash": c})
        out.write_text(json.dumps(data, indent=0)); log.info("magnet.fin", n=len(data["fin"]))
        try: await b.close()
        except Exception: pass
    print(f"done magnet: core={len(data['core'])} fin={len(data['fin'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
