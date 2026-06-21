"""Sample Kad Kahwin (Digital) prices — decomposed factor model.

Drivers: OrderType(Standard / Custom Die-cut) x Size(7) x Paper(10; Vellum OOS) x
Colour(4C Front/Both) x Qty + Folding Code + Hot Stamping (block, quoted separately).
Reference: Standard / A5 / Gloss Art Card 260gsm / 4C (Front).

Sections: core, size, paper, colour, ordertype.  python -m app.kadkahwin_sampler [account]
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
URL = "https://www.excard.com.my/spec/Digital/Kad_Kahwin"
SIZES = ["DL (99mm x 210mm)", "2DL (198mm x 210mm)", "A7 (74mm x 105mm)", "A6 (105mm x 148mm)",
         "A5 (148mm x 210mm)", "A4 (210mm x 297mm)", "Square (140mm x 280mm)"]
PAPERS = ["Gloss Art Card 230gsm (2 sides coated)", "Gloss Art Card 260gsm (2 sides coated)",
          "Gloss Art Card 310gsm (2 sides coated)", "Gloss Art Card 360gsm (2 sides coated)",
          "Super White 240gsm", "Linen 240gsm", "Suwen 240gsm", "Simili 140gsm",
          "Metal Ice 250gsm", "Matte Art Paper 150gsm"]
REF = dict(ordertype="1,Standard Kad Kahwin", size="A5 (148mm x 210mm)",
           paper="Gloss Art Card 260gsm (2 sides coated)", colour="4C (Front)")
QTYS = [10, 50, 100, 200, 300, 500, 750]


async def _radio(page, name, value):
    loc = page.locator(f"input[name$='{name}']"); n = await loc.count()
    for i in range(n):
        if (await loc.nth(i).get_attribute("value")) == value:
            try:
                await loc.nth(i).check()
            except Exception:
                await page.evaluate("(el)=>el.click()", await loc.nth(i).element_handle())
            await _wait(page); await asyncio.sleep(0.8); return True
    return False


async def _config(page, **ov):
    c = {**REF, **ov}
    await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.8)
    await _radio(page, "rblOrderType", c["ordertype"])
    if not await _sel(page, "ddlSize", c["size"]):
        return False
    if not await _sel(page, "ddlPaper", c["paper"]):
        return False
    if not await _sel(page, "rblPrintColourSide", c["colour"]):
        return False
    await asyncio.sleep(0.5)
    return True


async def _read(page, q):
    if not await _sel(page, "comboQty", str(q)):
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
    out = OUT / "kadkahwin_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {
        "core": [], "size": [], "paper": [], "colour": [], "ordertype": []}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1600})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        if not data["core"]:
            await _config(page); res = await _sweep(page, QTYS)
            data["core"] = [{"qty": q, "cash": c} for q, c in res.items()]
            out.write_text(json.dumps(data, indent=0)); log.info("kk.core", n=len(res))

        if not data["size"]:
            for s in SIZES:
                if not await _config(page, size=s):
                    continue
                for q in (100, 500):
                    c = await _read(page, q)
                    if c:
                        data["size"].append({"size": s, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("kk.size", size=s[:12])

        if not data["paper"]:
            for p in PAPERS:
                if not await _config(page, paper=p):
                    continue
                for q in (100, 500):
                    c = await _read(page, q)
                    if c:
                        data["paper"].append({"paper": p, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("kk.paper", paper=p[:18])

        if not data["colour"]:
            for col in ("4C (Front)", "4C (Both)"):
                if not await _config(page, colour=col):
                    continue
                for q in (100, 500):
                    c = await _read(page, q)
                    if c:
                        data["colour"].append({"colour": col, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("kk.colour")

        if not data["ordertype"]:
            for ot in ("1,Standard Kad Kahwin", "2,Custom Die-cut Kad Kahwin"):
                if not await _config(page, ordertype=ot):
                    continue
                for q in (100, 500):
                    c = await _read(page, q)
                    if c:
                        data["ordertype"].append({"ordertype": ot, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("kk.ordertype")

        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: " + " ".join(f"{k}={len(v)}" for k, v in data.items()))


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
