"""Sample Folder (Litho) prices.

Drivers: MOULD GROUP (PF/DF/KF/CF) -> MOULD (11 image-radio moulds; code e.g. FPF 001) x
PAPER (5 Gloss Art Card weights) x QUANTITY. No print-colour choice (fixed). Compulsory:
Die-cutting + creasing (included). Decomposition:
  * core:  each mould x ref paper (250gsm 1 side) over the qty ladder -> per-mould base curve
  * paper: REF mould x all 5 papers at {500,1000} -> paper delta/factor vs ref
  * check: a 2nd mould x all 5 papers at {500,1000} -> validate paper-model independence

Saves output/folder_samples.json: {"core":[{group,mould,size,paper,qty,cash}], "paper":[...], "check":[...]}

  python -m app.folder_sampler [account]
"""
from __future__ import annotations
import asyncio, json, sys, re
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .logging_setup import log
from .billbook_sampler import _sel, _safe_read, _wait, _opts

OUT = Path(__file__).resolve().parent.parent / "output"
URL = "https://www.excard.com.my/spec/Litho/Folder"
GROUPS = ["PF", "DF", "KF", "CF"]
PAPERS = ["Gloss Art Card 250gsm (1 side coated)", "Gloss Art Card 300gsm (1 side coated)",
          "Gloss Art Card 250gsm (2 side coated)", "Gloss Art Card 310gsm (2 side coated)",
          "Gloss Art Card 360gsm (2 side coated)"]
REF_PAPER = PAPERS[0]
QTYS = [250, 300, 350, 400, 450, 500, 1000]
REF_MOULD = ("PF", "FPF 001")
CHK_MOULD = ("DF", "FDF 001")


async def _radio(page, name, val):
    loc = page.locator(f"input[name$='{name}']"); n = await loc.count()
    for i in range(n):
        if (await loc.nth(i).get_attribute("value")) == val:
            try:
                await loc.nth(i).check()
            except Exception:
                await page.evaluate("(el)=>el.click()", await loc.nth(i).element_handle())
            await _wait(page); await asyncio.sleep(1.4); return True
    return False


async def _moulds(page):
    """rblMould radio values for the current group -> [(value, code)]."""
    vals = await page.evaluate(
        r"""()=>[...document.querySelectorAll("input[name$='rblMould']")].map(r=>r.value)""")
    out = []
    for v in vals:
        parts = v.split(",")
        code = parts[1] if len(parts) > 1 else v
        out.append((v, code))
    return out


async def _pick_mould(page, value):
    await page.evaluate(
        r"""(val)=>{const r=[...document.querySelectorAll("input[name$='rblMould']")].find(x=>x.value===val);if(r)r.click();}""",
        value)
    await _wait(page); await asyncio.sleep(1.4)


async def _size(page):
    txt = await page.evaluate("()=>document.body.innerText")
    m = re.search(r"Size\s*\t?\s*(\d+\s*mm\s*x\s*\d+\s*mm)", txt)
    return m.group(1).replace(" ", "") if m else ""


async def _sweep(page, qtys):
    res = {}; prev = None
    for q in qtys:
        if not await _sel(page, "comboQty", str(q)):
            continue
        await asyncio.sleep(1.0)
        c = (await _safe_read(page)).get("before_discount")
        if c and c != prev:
            res[q] = c; prev = c
        elif c == prev:
            await _sel(page, "comboQty", str(qtys[0])); await _sel(page, "comboQty", str(q))
            await asyncio.sleep(1.0); c = (await _safe_read(page)).get("before_discount")
            if c:
                res[q] = c; prev = c
    return res


async def _config(page, group, mould_value, paper):
    await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.8)
    if not await _radio(page, "rblMouldGroup", group):
        return None
    await _pick_mould(page, mould_value)
    if not await _sel(page, "ddlPaper", paper):
        return None
    await asyncio.sleep(0.6)
    return await _size(page)


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "folder_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"core": [], "paper": [], "check": []}
    core_done = {r["mould"] for r in data["core"]
                 if sum(1 for x in data["core"] if x["mould"] == r["mould"]) >= 5}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1600})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        # 1) CORE: each mould (all groups) x ref paper over qty
        for group in GROUPS:
            await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.6)
            await _radio(page, "rblMouldGroup", group)
            moulds = await _moulds(page)
            for mv, code in moulds:
                if code in core_done:
                    continue
                size = await _config(page, group, mv, REF_PAPER)
                if size is None:
                    log.info("fd.cfg_fail", group=group, mould=code); continue
                res = await _sweep(page, QTYS)
                for q, c in res.items():
                    data["core"].append({"group": group, "mould": code, "size": size,
                                         "paper": REF_PAPER, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("fd.core", mould=code, size=size, n=len(res))

        # 2) PAPER table on REF mould
        if not data["paper"]:
            await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.6)
            await _radio(page, "rblMouldGroup", REF_MOULD[0])
            mref = next((v for v, c in await _moulds(page) if c == REF_MOULD[1]), None)
            for paper in PAPERS:
                if await _config(page, REF_MOULD[0], mref, paper) is None:
                    continue
                res = await _sweep(page, [500, 1000])
                for q, c in res.items():
                    data["paper"].append({"mould": REF_MOULD[1], "paper": paper, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("fd.paper", paper=paper[:24], n=len(res))

        # 3) CHECK paper-model independence on a 2nd mould
        if not data["check"]:
            await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.6)
            await _radio(page, "rblMouldGroup", CHK_MOULD[0])
            mchk = next((v for v, c in await _moulds(page) if c == CHK_MOULD[1]), None)
            for paper in PAPERS:
                if await _config(page, CHK_MOULD[0], mchk, paper) is None:
                    continue
                res = await _sweep(page, [500, 1000])
                for q, c in res.items():
                    data["check"].append({"mould": CHK_MOULD[1], "paper": paper, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("fd.check", paper=paper[:24], n=len(res))

        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: core={len(data['core'])} paper={len(data['paper'])} check={len(data['check'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
