"""Sample Wire-O Notebook (Litho) prices.

Fixed size/paper/pages per cover type. Drivers: Cover type (Hard / VDP Hard / Soft /
Exclusive Leather) x Additional content sheets (Not Required / 4 / 8 / 12) x Qty +
compulsory Cover Lamination (Matte Front / +Spot UV / Gloss Front) + Hot Stamping (block).

Sections: core (per-cover qty curve @ Matte Front, add None), lamination (Hard Cover x 4
laminations), addcontent (Hard Cover x 4/8/12 sheets).

  python -m app.wireo_sampler [account]
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
URL = "https://www.excard.com.my/spec/Litho/Wire-O_Notebook"
COVERS = ["Hard Cover", "VDP Hard Cover", "Soft Cover", "Exclusive Leather Cover"]
LAMS = ["Matte Lamination (Front)", "Matte Lamination (Front) + Spot UV (Front Cover)",
        "Matte Lamination (Front) + Spot UV (Front and Back Cover)", "Gloss Lamination (Front)"]
ADDC = ["4 sheets", "8 sheets", "12 sheets"]
QTYS = [10, 30, 50, 100, 200, 300, 500, 1000, 3000, 10000]
REF_LAM = "Matte Lamination (Front)"


async def _radio(page, name, value):
    loc = page.locator(f"input[name$='{name}']"); n = await loc.count()
    for i in range(n):
        if (await loc.nth(i).get_attribute("value")) == value:
            try:
                await loc.nth(i).check()
            except Exception:
                await page.evaluate("(el)=>el.click()", await loc.nth(i).element_handle())
            await _wait(page); await asyncio.sleep(1.0); return True
    return False


async def _config(page, cover, lam=REF_LAM, addc=None):
    await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.8)
    await _radio(page, "rblOrderDesc", cover)
    # Soft / Exclusive Leather covers don't offer the Matte-Front reference lamination;
    # fall back to whatever lamination the cover does offer (first real option).
    if not await _sel(page, "ddlCoverLamination", lam):
        avail = await _opts(page, "ddlCoverLamination")
        if not avail or not await _sel(page, "ddlCoverLamination", avail[0]):
            return False
        log.info("wo.lam_fallback", cover=cover, lam=avail[0])
    if addc:
        await _sel(page, "ddlAddContent", addc)
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
    out = OUT / "wireo_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"core": [], "lamination": [], "addcontent": []}
    core_done = {r["cover"] for r in data["core"]
                 if sum(1 for x in data["core"] if x["cover"] == r["cover"]) >= 6}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1500})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        for cover in COVERS:
            if cover in core_done:
                continue
            if not await _config(page, cover):
                log.info("wo.cfg_fail", cover=cover); continue
            res = await _sweep(page, QTYS)
            for q, c in res.items():
                data["core"].append({"cover": cover, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("wo.core", cover=cover, n=len(res))

        if not data["lamination"]:
            for lam in LAMS:
                if not await _config(page, "Hard Cover", lam=lam):
                    continue
                for q in (50, 500):
                    c = await _read(page, q)
                    if c:
                        data["lamination"].append({"lam": lam, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("wo.lam", lam=lam[:24])

        if not data["addcontent"]:
            for ac in [None] + ADDC:
                if not await _config(page, "Hard Cover", addc=ac):
                    continue
                for q in (50, 500):
                    c = await _read(page, q)
                    if c:
                        data["addcontent"].append({"addc": ac or "None", "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("wo.addcontent")

        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: core={len(data['core'])} lamination={len(data['lamination'])} addcontent={len(data['addcontent'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
