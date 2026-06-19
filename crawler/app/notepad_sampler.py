"""Sample Notepad (Litho) prices.

Notepad is a FIXED-spec product: Size 80mm x 106mm, content Simili 80gsm (40 Sheets),
print colour 4C+4C (Cover) + 1C (Content), Wire-O hole punching compulsory. The only
price drivers are:
  * cover PAPER  (Gloss Art Card 260gsm / 310gsm)
  * QUANTITY     (books: 250..20000)
  * LAMINATION   (compulsory "Matte Lamination (Both)"; optional + Spot UV (Front Cover))

Saves output/notepad_samples.json:
  {"core":[{paper,qty,cash}],            # per-paper qty curve (Matte Lam Both)
   "spotuv":[{paper,qty,cash}]}          # +Spot UV upgrade delta

  python -m app.notepad_sampler [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login, polite_pause
from . import accounts
from .logging_setup import log
from .sticker_capture import _read_price
from .billbook_sampler import _sel, _safe_read, _wait

OUT = Path(__file__).resolve().parent.parent / "output"
URL = "https://www.excard.com.my/spec/Litho/Notepad"
PAPERS = ["Gloss Art Card 260gsm (2 side coated)", "Gloss Art Card 310gsm (2 side coated)"]
LAM_BASE = "Matte Lamination (Both)"
LAM_UV = "Matte Lamination (Both) + Spot UV (Front Cover)"
QTYS = [250, 300, 500, 1000, 2000, 3000, 4000, 5000, 10000, 15000, 20000]


async def _config(page, paper, lam):
    await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.6)
    if not await _sel(page, "ddlPaper", paper):
        return False
    await _sel(page, "rblLaminationSide", lam)
    return True


async def _sweep(page):
    res = {}; prev = None
    for q in QTYS:
        if not await _sel(page, "comboQty", str(q)):
            continue
        await asyncio.sleep(0.8)
        c = (await _safe_read(page)).get("before_discount")
        if c and c != prev:
            res[q] = c; prev = c
        elif c == prev:  # stale guard
            await _sel(page, "comboQty", str(QTYS[0])); await _sel(page, "comboQty", str(q))
            await asyncio.sleep(0.8); c = (await _safe_read(page)).get("before_discount")
            if c:
                res[q] = c; prev = c
    return res


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "notepad_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"core": [], "spotuv": []}
    done = {(r["paper"], r["qty"]) for r in data["core"]}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        # 1) CORE per-paper qty curve (Matte Lamination Both = compulsory default)
        for paper in PAPERS:
            if all((paper, q) in done for q in QTYS):
                continue
            if not await _config(page, paper, LAM_BASE):
                log.info("np.cfg_fail", paper=paper[:18]); continue
            res = await _sweep(page)
            for q, c in res.items():
                data["core"].append({"paper": paper, "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("np.core", paper=paper[:18], n=len(res))

        # 2) Spot UV upgrade delta at 260gsm over the qty ladder
        if not data["spotuv"]:
            if await _config(page, PAPERS[0], LAM_UV):
                res = await _sweep(page)
                for q, c in res.items():
                    data["spotuv"].append({"paper": PAPERS[0], "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("np.spotuv", n=len(res))

        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: core={len(data['core'])} spotuv={len(data['spotuv'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
