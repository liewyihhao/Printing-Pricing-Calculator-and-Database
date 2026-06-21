"""Sample Kad Terima Kasih (Digital) prices — decomposed factor model.

Thank-you gift tag. Drivers: Size(3) x Paper(6; Vellum OOS) x Colour(4C Front/Both) x Qty
+ Hole Punching (3mm). Reference: 52x52 / Gloss Art Card 260gsm / 4C (Front).
Sections: core, size, paper, colour, holepunch.  python -m app.kadterima_sampler [account]
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
URL = "https://www.excard.com.my/spec/Digital/kad_Terima_Kasih"
SIZES = ["52mm x 52mm", "40mm x 86mm", "40mm x 70mm"]
PAPERS = ["Gloss Art Card 230gsm (2 sides coated)", "Gloss Art Card 260gsm (2 sides coated)",
          "Gloss Art Card 310gsm (2 sides coated)", "Gloss Art Card 360gsm (2 sides coated)",
          "Super White 240gsm", "Metal Ice 250gsm"]
REF = dict(size="52mm x 52mm", paper="Gloss Art Card 260gsm (2 sides coated)", colour="4C (Front)")
QTYS = [50, 100, 200, 300, 500]


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


async def _config(page, hp=False, **ov):
    c = {**REF, **ov}
    await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.8)
    if not await _sel(page, "ddlSize", c["size"]):
        return False
    if not await _sel(page, "ddlPaper", c["paper"]):
        return False
    if not await _sel(page, "rblPrintColourSide", c["colour"]):
        return False
    if hp:
        await _radio(page, "rblPunchHole", "Hole Punching (3mm),1")
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
    out = OUT / "kadterima_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {
        "core": [], "size": [], "paper": [], "colour": [], "holepunch": []}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1500})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        if not data["core"]:
            await _config(page); res = await _sweep(page, QTYS)
            data["core"] = [{"qty": q, "cash": c} for q, c in res.items()]
            out.write_text(json.dumps(data, indent=0)); log.info("kt.core", n=len(res))

        if not data["size"]:
            for s in SIZES:
                if not await _config(page, size=s):
                    continue
                for q in (100, 500):
                    c = await _read(page, q)
                    if c:
                        data["size"].append({"size": s, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("kt.size", size=s)

        if not data["paper"]:
            for p in PAPERS:
                if not await _config(page, paper=p):
                    continue
                for q in (100, 500):
                    c = await _read(page, q)
                    if c:
                        data["paper"].append({"paper": p, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("kt.paper", paper=p[:18])

        if not data["colour"]:
            for col in ("4C (Front)", "4C (Both)"):
                if not await _config(page, colour=col):
                    continue
                for q in (100, 500):
                    c = await _read(page, q)
                    if c:
                        data["colour"].append({"colour": col, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("kt.colour")

        if not data["holepunch"]:
            for kind, hp in (("base", False), ("holepunch", True)):
                if not await _config(page, hp=hp):
                    continue
                for q in (100, 500):
                    c = await _read(page, q)
                    if c:
                        data["holepunch"].append({"kind": kind, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("kt.holepunch")

        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: " + " ".join(f"{k}={len(v)}" for k, v in data.items()))


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
