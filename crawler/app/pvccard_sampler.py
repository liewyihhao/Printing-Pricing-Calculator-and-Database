"""Sample PVC Card (Digital) prices.

Fixed card size/material (PVC); orientation (Portrait/Landscape) is price-neutral (verified).
Drivers: PRINT COLOUR (4C Front / 4C Both) x QUANTITY + Round Cornering / Hole Punching deltas.
Saves output/pvccard_samples.json: {"core":[{colour,qty,cash}], "finishing":[{kind,qty,cash}]}

  python -m app.pvccard_sampler [account]
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
URL = "https://www.excard.com.my/spec/Digital/PVC_Card"
COLOURS = ["4C (Front)", "4C (Both)"]
QTYS = [20, 60, 100, 200, 500, 1000, 2000, 3500]


async def _radio(page, name, value):
    loc = page.locator(f"input[name$='{name}']"); n = await loc.count()
    for i in range(n):
        if (await loc.nth(i).get_attribute("value")) == value:
            try:
                await loc.nth(i).check()
            except Exception:
                await page.evaluate("(el)=>el.click()", await loc.nth(i).element_handle())
            await _wait(page); await asyncio.sleep(0.7); return True
    return False


async def _config(page, colour, rc=False, hp=False, vdp=False):
    await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.8)
    await _sel(page, "ddlSizeOrientation", "Portrait")
    if not await _sel(page, "rblPrintColourSide", colour):
        return False
    if rc:
        for v in ("Round Cornering,1", "Round Cornering (R6),1", "Round Cornering"):
            if await _radio(page, "rblRoundCorner", v):
                break
    if hp:
        await _radio(page, "rblPunchHole", "Hole Punching,1")
    if vdp:
        for v in ("Variable Data Printing (Front)", "Variable Data Printing (Front),1"):
            if await _sel(page, "ddlVDP", v):
                break
        await _wait(page); await asyncio.sleep(0.4)
    await asyncio.sleep(0.4)
    return True


async def _read(page, q):
    if not await _sel(page, "comboQty", str(q)):
        return None
    await asyncio.sleep(0.9)
    return (await _safe_read(page)).get("before_discount")


async def _sweep(page, qtys):
    res = {}; prev = None
    for q in qtys:
        c = await _read(page, q)
        if c and c != prev:
            res[q] = c; prev = c
    return res


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "pvccard_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"core": [], "finishing": []}
    done = {r["colour"] for r in data["core"] if sum(1 for x in data["core"] if x["colour"] == r["colour"]) >= 5}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1500})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for colour in COLOURS:
            if colour in done:
                continue
            if not await _config(page, colour):
                log.info("pvc.cfg_fail", colour=colour); continue
            res = await _sweep(page, QTYS)
            for q, c in res.items():
                data["core"].append({"colour": colour, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("pvc.core", colour=colour, n=len(res))

        if not data["finishing"]:
            for kind, rc, hp in [("base", False, False), ("round_corner", True, False), ("hole_punch", False, True)]:
                if not await _config(page, "4C (Front)", rc=rc, hp=hp):
                    continue
                for q in (100, 1000):
                    c = await _read(page, q)
                    if c:
                        data["finishing"].append({"kind": kind, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("pvc.finishing")

        if not any(r["kind"] == "vdp" for r in data["finishing"]):
            # VDP delta vs the existing "base" rows (same 4C Front, no finishing config).
            if await _config(page, "4C (Front)", vdp=True):
                for q in (100, 1000):
                    c = await _read(page, q)
                    if c:
                        data["finishing"].append({"kind": "vdp", "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("pvc.vdp")
            else:
                log.info("pvc.vdp_cfg_fail")
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: core={len(data['core'])} finishing={len(data['finishing'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
