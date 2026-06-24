"""Sample Bunting (Litho) prices. Drivers: ddlSize(3) x ddlPaper(2) x ddlColourProtective
(fitting: Wood / PVC Pipe / Wood+Wire) x comboQty(1..300). The compulsory ddlColourProtective
is the last required field and resets on qty change, so it is re-applied per qty.

variant = "<size>|<paper>|<protective>".
Saves output/bunting_samples.json: {"core":[{variant,qty,cash}]}.

  python -m app.bunting_sampler [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .logging_setup import log
from .billbook_sampler import _sel, _safe_read, _wait, _opts

OUT = Path(__file__).resolve().parent.parent / "output"
URL = "https://www.excard.com.my/spec/Litho/Bunting"
SIZES = ["2ft x 5ft", "2ft x 6ft", "2.5ft x 6ft"]
PAPERS = ["Tarpaulin 300gsm", "Synthetic Paper 180micron"]
PROT = ["Come With Wood Only", "Come With PVC Pipe", "Come With Wood and Pre-Installed Wire (#18)"]
PROT_SHORT = {"Come With Wood Only": "Wood", "Come With PVC Pipe": "PVC Pipe",
              "Come With Wood and Pre-Installed Wire (#18)": "Wood+Wire"}
QTYS = [1, 2, 5, 10, 20, 50, 100, 200, 300]


async def _sweep(page, qtys, prot, prev=None):
    res = {}
    for q in qtys:
        if not await _sel(page, "comboQty", str(q)):
            continue
        await asyncio.sleep(0.35); await _sel(page, "ddlColourProtective", prot)
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
    out = OUT / "bunting_samples.json"
    data = {"core": []}
    done = {r["variant"] for r in data["core"]}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1500})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for size in SIZES:
            for paper in PAPERS:
                for prot in PROT:
                    vkey = f"{size}|{paper}|{PROT_SHORT[prot]}"
                    if vkey in done:
                        continue
                    await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.5)
                    if not await _sel(page, "ddlSize", size):
                        log.warning("bunting.size_fail", size=size); continue
                    await asyncio.sleep(0.6)
                    if not await _sel(page, "ddlPaper", paper):
                        log.warning("bunting.paper_fail", paper=paper); continue
                    await asyncio.sleep(0.6)
                    res = await _sweep(page, QTYS, prot)
                    for q, c in res.items():
                        data["core"].append({"variant": vkey, "qty": q, "cash": c})
                    out.write_text(json.dumps(data, indent=0)); log.info("bunting", variant=vkey, n=len(res))
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"done bunting: {len(data['core'])} pts")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
