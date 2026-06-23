"""Sample three simple Apparel & Gifts products in one login:
  - Hand Fan (Digital): ddlPaper(2) x comboQty(50..800). No lamination.
  - Hanger (Digital):   ddlPaper(2) x comboQty(50..800) + rblLaminationSide (Matte/Gloss Both).
  - Button Badge (Digital): comboQty(10..250) + rblLaminationSide (Gloss/Soft Touch).

Each writes output/<tag>_samples.json: {"core":[{variant,qty,cash}], "lam":[{lam,qty,cash}]}.
The 'variant' axis is paper for fan/hanger, "-" for badge. Lamination captured at one qty
per option to test price-neutrality.

  python -m app.gifts_sampler [account]
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
BASE = "https://www.excard.com.my"


async def _qopts(page, name):
    return await page.evaluate(
        "(n)=>{var s=document.querySelector(`select[name$='${n}']`);if(!s)return[];"
        "return Array.from(s.options).map(o=>o.value).filter(v=>v&&!v.startsWith('-'));}", name)


async def _sweep_qty(page, qty_sel, qtys, prev=None, lam_field=None, lam_value=None, reapply=None):
    """Return {qty:cash}, polling until price changes off prev (stale-read guard).
    On these forms changing qty resets compulsory selects (lamination, print colour),
    so re-apply them AFTER each qty in order (price calc only fires once the last
    required field is set). `reapply` is a list of (select_name, value)."""
    fields = list(reapply or [])
    if lam_field and lam_value:
        fields.append((lam_field, lam_value))
    res = {}
    for q in qtys:
        if not await _sel(page, qty_sel, str(q)):
            continue
        for name, val in fields:
            if val:
                await asyncio.sleep(0.35)
                await _sel(page, name, val)
        c = None
        for _ in range(12):
            await asyncio.sleep(0.6)
            c = (await _safe_read(page)).get("before_discount")
            if c is not None and c != 0 and (prev is None or c != prev):
                break
        if c:
            res[q] = c; prev = c
    return res


async def sample_fan(page):
    out = OUT / "handfan_samples.json"
    data = {"core": [], "lam": []}
    papers = ["Gloss Art Card 310gsm", "Gloss Art Card 360gsm"]
    qtys = [50, 100, 200, 300, 400, 500, 600, 800]
    for paper in papers:
        await page.goto(BASE + "/spec/Digital/Hand_Fan", wait_until="domcontentloaded")
        await _wait(page); await asyncio.sleep(1.0)
        if not await _sel(page, "ddlPaper", paper):
            log.warning("fan.paper_fail", paper=paper); continue
        await asyncio.sleep(0.5)
        lam_opts = await _opts(page, "rblLaminationSide")  # compulsory; reset on each qty change
        lam0 = lam_opts[0] if lam_opts else None
        res = await _sweep_qty(page, "comboQty", qtys, lam_field="rblLaminationSide", lam_value=lam0)
        for q, c in res.items():
            data["core"].append({"variant": paper, "qty": q, "cash": c})
        out.write_text(json.dumps(data, indent=0)); log.info("fan", paper=paper, n=len(res))
    out.write_text(json.dumps(data, indent=0))


async def sample_hanger(page):
    out = OUT / "hanger_samples.json"
    data = {"core": [], "lam": []}
    papers = ["Gloss Art Card 310gsm (2 sides coated)", "Gloss Art Card 360gsm (2 sides coated)"]
    colours = ["4C (Front)", "4C (Both)"]
    lams = ["Matte Lamination (Both)", "Gloss Lamination (Both)"]
    qtys = [50, 100, 200, 300, 400, 500, 600, 800]
    # paper x colour qty curves; per qty re-apply colour + lamination (both reset on qty change)
    for paper in papers:
        for colour in colours:
            await page.goto(BASE + "/spec/Digital/Hanger", wait_until="domcontentloaded")
            await _wait(page); await asyncio.sleep(1.0)
            if not await _sel(page, "ddlPaper", paper):
                log.warning("hanger.paper_fail", paper=paper); continue
            await asyncio.sleep(0.4)
            lo = await _opts(page, "rblLaminationSide")
            lam0 = (lams[0] if lams[0] in (lo or []) else (lo[0] if lo else None))
            res = await _sweep_qty(page, "comboQty", qtys,
                                   reapply=[("rblPrintColourSide", colour)],
                                   lam_field="rblLaminationSide", lam_value=lam0)
            for q, c in res.items():
                data["core"].append({"variant": f"{paper}|{colour}", "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("hanger", paper=paper, colour=colour, n=len(res))
    # lamination neutrality test at one config/qty
    for lam in lams:
        await page.goto(BASE + "/spec/Digital/Hanger", wait_until="domcontentloaded")
        await _wait(page); await asyncio.sleep(1.0)
        await _sel(page, "ddlPaper", papers[0]); await asyncio.sleep(0.4)
        r = await _sweep_qty(page, "comboQty", [200],
                             reapply=[("rblPrintColourSide", colours[0])],
                             lam_field="rblLaminationSide", lam_value=lam)
        for q, c in r.items():
            data["lam"].append({"lam": lam, "qty": q, "cash": c})
    out.write_text(json.dumps(data, indent=0)); log.info("hanger.lam", n=len(data["lam"]))


async def sample_badge(page):
    out = OUT / "buttonbadge_samples.json"
    data = {"core": [], "lam": []}
    lams = ["Gloss", "Soft Touch"]
    qtys = [10, 30, 50, 70, 100, 150, 200, 250]
    await page.goto(BASE + "/spec/Digital/button_badge", wait_until="domcontentloaded")
    await _wait(page); await asyncio.sleep(1.0)
    await _sel(page, "rblLaminationSide", lams[0]); await asyncio.sleep(0.5)
    res = await _sweep_qty(page, "comboQty", qtys)
    for q, c in res.items():
        data["core"].append({"variant": "-", "qty": q, "cash": c})
    out.write_text(json.dumps(data, indent=0)); log.info("badge.core", n=len(res))
    # lamination neutrality test
    for lam in lams:
        await page.goto(BASE + "/spec/Digital/button_badge", wait_until="domcontentloaded")
        await _wait(page); await asyncio.sleep(1.0)
        if await _sel(page, "rblLaminationSide", lam):
            await asyncio.sleep(0.4)
            r = await _sweep_qty(page, "comboQty", [100])
            for q, c in r.items():
                data["lam"].append({"lam": lam, "qty": q, "cash": c})
    out.write_text(json.dumps(data, indent=0)); log.info("badge.lam", n=len(data["lam"]))


SECTIONS = {"fan": None, "hanger": None, "badge": None}  # filled below


async def run(account_id=1, only=None):
    a = accounts.get(account_id)
    fns = {"fan": sample_fan, "hanger": sample_hanger, "badge": sample_badge}
    todo = [fns[k] for k in (only or fns.keys()) if k in fns]
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1500})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for fn in todo:
            try:
                await fn(page)
            except Exception as e:  # noqa: BLE001
                log.warning("gifts.section_fail", fn=fn.__name__, err=str(e)[:80])
        try: await b.close()
        except Exception: pass
    print("done:", ",".join(only or ["fan", "hanger", "badge"]))


if __name__ == "__main__":
    # usage: python -m app.gifts_sampler [account] [section ...]
    args = sys.argv[1:]
    acct = int(args[0]) if args and args[0].isdigit() else 1
    secs = [s for s in args if not s.isdigit()] or None
    asyncio.run(run(acct, only=secs))
