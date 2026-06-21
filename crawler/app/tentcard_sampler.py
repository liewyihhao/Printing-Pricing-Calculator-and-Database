"""Sample Tent Card (Litho) prices.

Fixed Size 294x86mm, Paper Art Card 310gsm, 4C(Front), Die-Cutting + Creasing compulsory.
Drivers: QUANTITY + LAMINATION (Matte Both / Matte Both + Spot UV (Front)).
Saves output/tentcard_samples.json: {"core":[{lam,qty,cash}]}.

  python -m app.tentcard_sampler [account]
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
URL = "https://www.excard.com.my/spec/Litho/Tent_Card"
LAMS = ["Matte Lamination (Both)", "Matte Lamination (Both) + Spot UV (Front)"]
QTYS = [300, 500, 1000, 2000, 3000, 4000, 5000, 10000, 20000]


async def _config(page, lam):
    await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.8)
    if not await _sel(page, "rblLaminationSide", lam):
        return False
    await asyncio.sleep(0.8)
    return True


async def _sweep(page):
    res = {}; prev = None
    for q in QTYS:
        if not await _sel(page, "comboQty", str(q)):
            continue
        await asyncio.sleep(1.1)
        c = (await _safe_read(page)).get("before_discount")
        if c and c != prev:
            res[q] = c; prev = c
        elif not c or c == prev:
            await _sel(page, "comboQty", str(QTYS[0])); await _sel(page, "comboQty", str(q))
            await asyncio.sleep(1.1); c = (await _safe_read(page)).get("before_discount")
            if c and c != prev:
                res[q] = c; prev = c
    return res


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "tentcard_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"core": []}
    done = {r["lam"] for r in data["core"] if sum(1 for x in data["core"] if x["lam"] == r["lam"]) >= 5}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for lam in LAMS:
            if lam in done:
                continue
            if not await _config(page, lam):
                log.info("tc.cfg_fail", lam=lam[:24]); continue
            res = await _sweep(page)
            for q, c in res.items():
                data["core"].append({"lam": lam, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("tc.core", lam=lam[:24], n=len(res))
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: core={len(data['core'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
