"""Sample Roll-Up Stand (Litho) prices. Fixed size (standard stand). Drivers: rblLaminationSide x comboQty (1-100).

Saves output/rollup_samples.json: {"data": [{lam, qty, cash}]}.
  python -m app.rollup_sampler [account]
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
URL = "https://www.excard.com.my/spec/Litho/Roll_Up_Stand"

LAMS = ["Matte Lamination", "Gloss Lamination"]
QTYS = [1, 2, 3, 5, 10, 20, 30, 50, 100]


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "rollup_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"data": []}
    done = {(r["lam"], r["qty"]) for r in data["data"]}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for lam in LAMS:
            await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.0)
            if not await _sel(page, "rblLaminationSide", lam):
                log.warning("rollup.lam_fail", lam=lam); continue
            await asyncio.sleep(0.5)
            for q in QTYS:
                if (lam, q) in done:
                    continue
                if not await _sel(page, "comboQty", str(q)):
                    log.warning("rollup.qty_fail", lam=lam, qty=q); continue
                await asyncio.sleep(1.0)
                r = await _safe_read(page)
                c = r.get("before_discount")
                if not c:
                    log.warning("rollup.no_price", lam=lam, qty=q); continue
                data["data"].append({"lam": lam, "qty": q, "cash": c})
                done.add((lam, q))
                out.write_text(json.dumps(data, indent=0))
                log.info("rollup", lam=lam, qty=q, cash=c)
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: {len(data['data'])} pts")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
