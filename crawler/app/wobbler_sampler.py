"""Sample Wobbler (Digital) prices. Drivers: rblMouldGroup(2) x ddlPaper(2) x rblLaminationSide(2) x comboQty.
Round Corner and Digital Die-Cut are add-on finishing (priced separately by delta).

Saves output/wobbler_samples.json: {"core": [{orient, paper, lam, qty, cash}], "finish": [{orient, paper, lam, qty, rc, cash}]}.
  python -m app.wobbler_sampler [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .logging_setup import log
from .billbook_sampler import _sel, _safe_read, _wait, _radio

OUT = Path(__file__).resolve().parent.parent / "output"
URL = "https://www.excard.com.my/spec/Digital/Wobbler"

ORIENTS = ["Portrait", "Landscape"]
PAPERS = ["Gloss Art Card 250gsm", "Gloss Art Card 310gsm"]
LAMS = ["Matte Lamination (Front)", "Gloss Lamination (Front)"]
QTYS = [50, 100, 200, 300, 500, 1000, 2000, 3000, 5000]
RC_OPTS = ["-", "Round Cornering (R6),4,1", "Digital Die-cutting,0,0"]


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "wobbler_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"core": [], "finish": []}
    done_core = {(r["orient"], r["paper"], r["lam"], r["qty"]) for r in data["core"]}

    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        # Core: orient x paper x lam x qty (no finishing)
        for orient in ORIENTS:
            for paper in PAPERS:
                for lam in LAMS:
                    await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.0)
                    if not await _radio(page, "rblMouldGroup", orient):
                        log.warning("wobbler.orient_fail", orient=orient); continue
                    await asyncio.sleep(0.3)
                    if not await _sel(page, "ddlPaper", paper):
                        log.warning("wobbler.paper_fail", paper=paper); continue
                    await asyncio.sleep(0.3)
                    if not await _sel(page, "rblLaminationSide", lam):
                        log.warning("wobbler.lam_fail", lam=lam); continue
                    await asyncio.sleep(0.5)
                    for q in QTYS:
                        if (orient, paper, lam, q) in done_core:
                            continue
                        if not await _sel(page, "comboQty", str(q)):
                            log.warning("wobbler.qty_fail", qty=q); continue
                        await asyncio.sleep(1.0)
                        r = await _safe_read(page)
                        c = r.get("before_discount")
                        if not c:
                            log.warning("wobbler.no_price", orient=orient, paper=paper, lam=lam, qty=q); continue
                        data["core"].append({"orient": orient, "paper": paper, "lam": lam, "qty": q, "cash": c})
                        done_core.add((orient, paper, lam, q))
                        out.write_text(json.dumps(data, indent=0))
                        log.info("wobbler.core", orient=orient, paper=paper, lam=lam, qty=q, cash=c)

        # Finishing delta: use Portrait/250gsm/Matte as reference, vary RC
        ref = ("Portrait", "Gloss Art Card 250gsm", "Matte Lamination (Front)")
        done_fin = {(r["rc"], r["qty"]) for r in data["finish"]}
        for rc in RC_OPTS[1:]:  # skip "-" (no finishing = core)
            await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.0)
            if not await _radio(page, "rblMouldGroup", ref[0]): continue
            await asyncio.sleep(0.3)
            if not await _sel(page, "ddlPaper", ref[1]): continue
            await asyncio.sleep(0.3)
            if not await _sel(page, "rblLaminationSide", ref[2]): continue
            await asyncio.sleep(0.3)
            if not await _radio(page, "rblRoundCorner", rc):
                log.warning("wobbler.rc_fail", rc=rc); continue
            await asyncio.sleep(0.5)
            for q in [100, 500, 1000]:
                if (rc, q) in done_fin:
                    continue
                if not await _sel(page, "comboQty", str(q)): continue
                await asyncio.sleep(1.0)
                r = await _safe_read(page)
                c = r.get("before_discount")
                if c:
                    data["finish"].append({"orient": ref[0], "paper": ref[1], "lam": ref[2], "rc": rc, "qty": q, "cash": c})
                    done_fin.add((rc, q))
                    out.write_text(json.dumps(data, indent=0))
                    log.info("wobbler.finish", rc=rc[:20], qty=q, cash=c)

        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: core={len(data['core'])} finish={len(data['finish'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
