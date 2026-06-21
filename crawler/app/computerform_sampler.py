"""Sample Computer Form (Litho, NCR) prices — decomposed factor model.

Fixed size 9.5" x 11". Drivers: Package(Multi Layer / Single Layer / Pay Slip) x
Layers(2-5, Multi only) x Ups(1/2/3) x PrintColour(1C/2C/4C) x Qty(2000..20000) +
Copy Change + Numbering. Per-ply tint dropdowns are price-neutral (set, not priced).

Reference (Multi): 2 layers / ups 1 / 1C. Sections: core, layer, ups, colour,
single (Single Layer curve), payslip (Pay Slip curve), copychange, numbering.

  python -m app.computerform_sampler [account]
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
URL = "https://www.excard.com.my/spec/Litho/Computer_Form"
TINTS = ["NCR White 55gsm", "NCR Yellow 55gsm", "NCR Green 55gsm", "NCR Pink 55gsm", "NCR Blue 55gsm"]
QTYS = [2000, 3000, 5000, 10000, 20000]


async def _radio(page, name, value):
    loc = page.locator(f"input[name$='{name}']"); n = await loc.count()
    for i in range(n):
        if (await loc.nth(i).get_attribute("value")) == value:
            try:
                await loc.nth(i).check()
            except Exception:
                await page.evaluate("(el)=>el.click()", await loc.nth(i).element_handle())
            await _wait(page); await asyncio.sleep(0.9); return True
    return False


async def _set_layers(page, n):
    if not await _sel(page, "ddlLayer", str(n)):
        return False
    for i in range(n):
        await _sel(page, f"ddlLayer{i+1}", TINTS[i % len(TINTS)])
    await asyncio.sleep(0.4)
    return True


async def _config(page, package, layers=2, ups="1", colour="1C", copychange=False, numbering=False):
    await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.8)
    await _radio(page, "rblPackage", package)
    if package == "Multi Layer Computer Form":
        if not await _set_layers(page, layers):
            return False
    await _radio(page, "ddlUps", ups)
    await _radio(page, "ddlPrintColor", colour)
    if copychange:
        await _radio(page, "rblCopyChange", "True")
    if numbering:
        await _radio(page, "rblNumbering", "True")
    await asyncio.sleep(0.4)
    return True


async def _read(page, q):
    if not await _sel(page, "ddlQty", str(q)):
        return None
    await asyncio.sleep(1.0)
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
    out = OUT / "computerform_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {
        "core": [], "layer": [], "ups": [], "colour": [], "single": [], "payslip": [],
        "copychange": [], "numbering": []}
    MULTI = "Multi Layer Computer Form"
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1600})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        if not data["core"]:
            await _config(page, MULTI); res = await _sweep(page, QTYS)
            data["core"] = [{"qty": q, "cash": c} for q, c in res.items()]
            out.write_text(json.dumps(data, indent=0)); log.info("cf.core", n=len(res))

        if not data["layer"]:
            for L in (2, 3, 4, 5):
                if not await _config(page, MULTI, layers=L):
                    continue
                for q in (2000, 10000):
                    c = await _read(page, q)
                    if c:
                        data["layer"].append({"layers": L, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("cf.layer", L=L)

        if not data["ups"]:
            for u in ("1", "2", "3"):
                if not await _config(page, MULTI, ups=u):
                    continue
                for q in (2000, 10000):
                    c = await _read(page, q)
                    if c:
                        data["ups"].append({"ups": u, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("cf.ups")

        if not data["colour"]:
            for col in ("1C", "2C", "4C"):
                if not await _config(page, MULTI, colour=col):
                    continue
                for q in (2000, 10000):
                    c = await _read(page, q)
                    if c:
                        data["colour"].append({"colour": col, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("cf.colour")

        if not data["single"]:
            if await _config(page, "Single Layer Computer Form"):
                res = await _sweep(page, QTYS)
                data["single"] = [{"qty": q, "cash": c} for q, c in res.items()]
                out.write_text(json.dumps(data, indent=0)); log.info("cf.single", n=len(res))

        if not data["payslip"]:
            if await _config(page, "Pay Slip"):
                res = await _sweep(page, QTYS)
                data["payslip"] = [{"qty": q, "cash": c} for q, c in res.items()]
                out.write_text(json.dumps(data, indent=0)); log.info("cf.payslip", n=len(res))

        if not data["copychange"]:
            for kind, cc in (("base", False), ("copychange", True)):
                if not await _config(page, MULTI, copychange=cc):
                    continue
                for q in (2000, 10000):
                    c = await _read(page, q)
                    if c:
                        data["copychange"].append({"kind": kind, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("cf.copychange")

        if not data["numbering"]:
            for kind, nb in (("base", False), ("numbering", True)):
                if not await _config(page, MULTI, numbering=nb):
                    continue
                for q in (2000, 10000):
                    c = await _read(page, q)
                    if c:
                        data["numbering"].append({"kind": kind, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("cf.numbering")

        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: " + " ".join(f"{k}={len(v)}" for k, v in data.items()))


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
