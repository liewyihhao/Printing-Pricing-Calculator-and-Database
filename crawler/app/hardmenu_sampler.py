"""Sample Hard Cover Menu (Digital) prices. Drivers: rblOrderDesc (Cover+Content /
Cover only / Content only) x ddlAddContent (12/16 content sheets, where applicable) x
ddlQty, with a compulsory ddlLamination that (with add-content) resets on qty change.

variant = "<orderdesc>|<addcontent>"  (addcontent '-' when not applicable).
Saves output/hardmenu_samples.json: {"core":[{variant,qty,cash}], "lam":[...]}.

  python -m app.hardmenu_sampler [account]
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
URL = "https://www.excard.com.my/spec/Digital/Hard_Cover_Menu"
ORDERS = ["Cover + Content", "Cover only", "Content only"]
QTYS = [10, 30, 50, 70, 100, 150, 200, 250]


async def _sweep(page, qtys, reapply, prev=None):
    res = {}
    for q in qtys:
        if not await _sel(page, "ddlQty", str(q)):
            continue
        for name, val in reapply:
            if val:
                await asyncio.sleep(0.35); await _sel(page, name, val)
        c = None
        for _ in range(12):
            await asyncio.sleep(0.6)
            c = (await _safe_read(page)).get("before_discount")
            if c is not None and c != 0 and (prev is None or c != prev):
                break
        if c:
            res[q] = c; prev = c
    return res


async def _setup(page, order):
    await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.2)
    if not await _radio(page, "rblOrderDesc", order):
        return None, None
    await asyncio.sleep(0.6)
    addc = await _opts(page, "ddlAddContent")
    lam = await _opts(page, "ddlLamination")
    return addc, (lam[0] if lam else None)


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "hardmenu_samples.json"
    data = {"core": [], "lam": []}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1600})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for order in ORDERS:
            addc, lam0 = await _setup(page, order)
            if addc is None:
                log.warning("hardmenu.order_fail", order=order); continue
            ac_list = addc if addc else [None]
            for ac in ac_list:
                if ac is not None:  # re-setup so add-content selection is clean
                    addc2, lam0 = await _setup(page, order)
                reapply = [("ddlAddContent", ac), ("ddlLamination", lam0)]
                res = await _sweep(page, QTYS, reapply)
                vkey = f"{order}|{ac or '-'}"
                for q, c in res.items():
                    data["core"].append({"variant": vkey, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("hardmenu", variant=vkey, n=len(res))
        # lamination neutrality on Cover+Content / first add-content
        addc, _ = await _setup(page, ORDERS[0])
        for lam in (await _opts(page, "ddlLamination")):
            r = await _sweep(page, [100], [("ddlAddContent", (addc or [None])[0]), ("ddlLamination", lam)])
            for q, c in r.items():
                data["lam"].append({"lam": lam, "qty": q, "cash": c})
        out.write_text(json.dumps(data, indent=0)); log.info("hardmenu.lam", n=len(data["lam"]))
        try: await b.close()
        except Exception: pass
    print(f"done hardmenu: core={len(data['core'])} lam={len(data['lam'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
