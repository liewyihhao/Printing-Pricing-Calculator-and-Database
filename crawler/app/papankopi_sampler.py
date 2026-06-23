"""Sample Papan Kopi / Sachet Board (Litho) prices. Drivers: ddlSize (3) x comboQty.
Hole Punching compulsory (included).

Saves output/papankopi_samples.json: {"data": [{size, qty, cash}]}.
  python -m app.papankopi_sampler [account]
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
URL = "https://www.excard.com.my/spec/Litho/Papan_Kopi"
SIZES = ["537mm x 334mm", "622mm x 346mm", "547mm x 346mm"]
QTYS_TRY = [100, 200, 300, 500, 1000, 2000, 3000, 5000]  # will use whatever the form offers


async def _get_qty_opts(page) -> list[str]:
    return await page.evaluate(
        "()=>{var s=document.querySelector('select[name$=\"comboQty\"]');if(!s)return[];"
        "return Array.from(s.options).map(o=>o.value).filter(v=>v&&v!='- Please Select -');}")


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "papankopi_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"data": []}
    done = {(r["size"], r["qty"]) for r in data["data"]}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for size in SIZES:
            await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.0)
            if not await _sel(page, "ddlSize", size):
                log.warning("papankopi.size_fail", size=size); continue
            await asyncio.sleep(1.5)
            qtys = await _get_qty_opts(page)
            if not qtys:
                qtys = [str(q) for q in QTYS_TRY]
            prev = None
            for q_str in qtys:
                q = int(q_str)
                if (size, q) in done:
                    prev = next((r["cash"] for r in data["data"] if r["size"] == size and r["qty"] == q), prev)
                    continue
                if not await _sel(page, "comboQty", q_str):
                    log.warning("papankopi.qty_fail", size=size, qty=q); continue
                # poll until price changes off the previous qty (guards pre-AJAX stale read)
                c = None
                for _ in range(12):
                    await asyncio.sleep(0.7)
                    c = (await _safe_read(page)).get("before_discount")
                    if c is not None and (prev is None or c != prev):
                        break
                if not c:
                    log.warning("papankopi.no_price", size=size, qty=q); continue
                data["data"].append({"size": size, "qty": q, "cash": c})
                done.add((size, q)); prev = c
                out.write_text(json.dumps(data, indent=0))
                log.info("papankopi", size=size, qty=q, cash=c)
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: {len(data['data'])} pts")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
