"""Sample Static Cling Window Sticker (Digital) prices — decomposed factor model.

This form also serves Car Sticker (same pricing). Drivers: Size(10) x Qty x Print
direction (Face Out / Face In / Both Side View) + VDP. Reference: 100x100 / Face Out /
no VDP. Sections: core, size, direction, vdp.

  python -m app.staticcling_sampler [account]
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
URL = "https://www.excard.com.my/spec/Digital/Static_Cling_Window_Sticker"
SIZES = ["54mm x 89mm", "75mm x 75mm", "100mm x 100mm", "110mm x 90mm", "115mm x 120mm",
         "130mm x 170mm", "165mm x 90mm", "220mm x 90mm", "104mm x 420mm", "310mm x 445mm"]
DIRECTIONS = ["Face Out View", "Face In View", "Both Side View"]
REF = dict(size="100mm x 100mm", direction="Face Out View", vdp="Not Required")
QTYS = [10, 50, 100, 200, 500, 1000, 2000, 4000]


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


async def _config(page, **ov):
    c = {**REF, **ov}
    await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.8)
    if not await _sel(page, "ddlSize", c["size"]):
        return False
    await _radio(page, "rblPrintdirection", c["direction"])
    await _sel(page, "ddlVDP", c["vdp"])
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
    out = OUT / "staticcling_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"core": [], "size": [], "direction": [], "vdp": []}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1500})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        if not data["core"]:
            await _config(page); res = await _sweep(page, QTYS)
            data["core"] = [{"qty": q, "cash": c} for q, c in res.items()]
            out.write_text(json.dumps(data, indent=0)); log.info("sc.core", n=len(res))

        if not data["size"]:
            for s in SIZES:
                if not await _config(page, size=s):
                    continue
                for q in (100, 1000):
                    c = await _read(page, q)
                    if c:
                        data["size"].append({"size": s, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("sc.size", size=s)

        if not data["direction"]:
            for d in DIRECTIONS:
                if not await _config(page, direction=d):
                    continue
                for q in (100, 1000):
                    c = await _read(page, q)
                    if c:
                        data["direction"].append({"direction": d, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("sc.direction")

        if not data["vdp"]:
            for v in ("Not Required", "Variable Data Printing (VDP)"):
                if not await _config(page, vdp=v):
                    continue
                for q in (100, 1000):
                    c = await _read(page, q)
                    if c:
                        data["vdp"].append({"vdp": v, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("sc.vdp")

        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: " + " ".join(f"{k}={len(v)}" for k, v in data.items()))


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
