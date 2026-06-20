"""Sample Voucher (Litho) prices — decomposed factor model.

Drivers: PackForm(Pad/Book/Loose) x Size(12) x ContentPaper(14) x ContentColour(4C
Front/Both) x Sets-per-book(10/25/50) x Qty(books/pads) + Perforation lines(0/1/2) +
Numbering. Sampled as a reference qty curve + independent one-factor-at-a-time sweeps.

Reference: Book / 145x210 / Art Paper 100gsm / 4C(Front) / sets 50.
Saves output/voucher_samples.json with sections: core, paper, colour, sets, size,
packform, perforation, numbering.

  python -m app.voucher_sampler [account]
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
URL = "https://www.excard.com.my/spec/Litho/voucher"
PAPERS = ["Art Paper 100gsm", "Art Paper 130gsm", "Art Paper 150gsm", "Matte Art Paper 150gsm",
          "Colour Paper Buff 75gsm", "Colour Paper Blue 75gsm", "Colour Paper Green 75gsm",
          "Colour Paper Pink 75gsm", "Colour Paper Purple 75gsm", "Colour Paper Yellow 75gsm",
          "Simili 80gsm", "Simili 100gsm", "Art Card 230gsm (2 sides coated)",
          "Art Card 260gsm (2 sides coated)"]
SIZES = ["90mm x 140mm", "105mm x 145mm", "145mm x 145mm", "125mm x 175mm", "90mm x 190mm",
         "107mm x 190mm", "60mm x 210mm", "145mm x 210mm", "55mm x 213mm", "95mm x 225mm",
         "120mm x 230mm", "105mm x 300mm"]
REF = dict(packform="Book", size="145mm x 210mm", paper="Art Paper 100gsm",
           colour="4C (Front)", sets="50")
QTYS = [10, 30, 50, 100, 200, 300, 500, 800]


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
    await _radio(page, "rblPackForm", c["packform"])
    if not await _sel(page, "ddlSize", c["size"]):
        return False
    if not await _sel(page, "ddlContentPaper", c["paper"]):
        return False
    if not await _sel(page, "ddlContentColor", c["colour"]):
        return False
    await _sel(page, "ddlSets", c["sets"])
    if "perforation" in ov:
        await _sel(page, "ddlPerforation", ov["perforation"])
    if ov.get("numbering"):
        await _radio(page, "rblNumbering", "True")
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
    out = OUT / "voucher_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {
        "core": [], "paper": [], "colour": [], "sets": [], "size": [], "packform": [],
        "perforation": [], "numbering": []}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1600})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        if not data["core"]:
            await _config(page); res = await _sweep(page, QTYS)
            data["core"] = [{"qty": q, "cash": c} for q, c in res.items()]
            out.write_text(json.dumps(data, indent=0)); log.info("vc.core", n=len(res))

        if not data["paper"]:
            for p in PAPERS:
                if not await _config(page, paper=p):
                    continue
                for q in (50, 300):
                    c = await _read(page, q)
                    if c:
                        data["paper"].append({"paper": p, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("vc.paper", paper=p[:18])

        if not data["colour"]:
            for col in ("4C (Front)", "4C (Both)"):
                if not await _config(page, colour=col):
                    continue
                for q in (50, 300):
                    c = await _read(page, q)
                    if c:
                        data["colour"].append({"colour": col, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("vc.colour")

        if not data["sets"]:
            for st in ("10", "25", "50"):
                if not await _config(page, sets=st):
                    continue
                for q in (50, 300):
                    c = await _read(page, q)
                    if c:
                        data["sets"].append({"sets": st, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("vc.sets")

        if not data["size"]:
            for s in SIZES:
                if not await _config(page, size=s):
                    continue
                c = await _read(page, 100)
                if c:
                    data["size"].append({"size": s, "qty": 100, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("vc.size", size=s)

        if not data["packform"]:
            for pf in ("Pad", "Book", "Loose"):
                if not await _config(page, packform=pf):
                    continue
                for q in (50, 300):
                    c = await _read(page, q)
                    if c:
                        data["packform"].append({"packform": pf, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("vc.packform")

        if not data["perforation"]:
            for pf in ("0", "1", "2"):
                if not await _config(page, perforation=pf):
                    continue
                for q in (50, 300):
                    c = await _read(page, q)
                    if c:
                        data["perforation"].append({"perforation": pf, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("vc.perf")

        if not data["numbering"]:
            for nb in (False, True):
                if not await _config(page, numbering=nb):
                    continue
                for q in (50, 300):
                    c = await _read(page, q)
                    if c:
                        data["numbering"].append({"numbering": nb, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("vc.numbering")

        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: " + " ".join(f"{k}={len(v)}" for k, v in data.items()))


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
