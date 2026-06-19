"""Sample Letterhead (Litho) prices.

Fixed size A4 (210x297mm). Price drivers: cover PAPER (7) x PRINT COLOUR/side (4) x
QUANTITY. Saves output/letterhead_samples.json: {"core":[{paper,colour,qty,cash}]}.

  python -m app.letterhead_sampler [account]
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
URL = "https://www.excard.com.my/spec/Litho/Letterhead"
# The 4 Conqueror 100gsm variants are price-identical (verified) — sample one representative
# (Brilliant White); the engine maps all Conqueror finishes to this curve.
PAPERS = ["Simili 80gsm", "Simili 100gsm", "Conqueror 100gsm Brilliant White Laid"]
COLOURS = ["1C (Front)", "2C (Front)", "4C (Front)", "4C (Both)"]
# representative qty ladder (intersected with the live dropdown per config; curve log-interps)
QTYS = [10, 50, 100, 200, 300, 500, 700, 1000, 1500, 2000, 3000, 5000, 10000]


async def _qty_ready(page):
    """After the colour postback, comboQty repopulates asynchronously and in stages — wait
    until the option count is large AND stable across two checks (full ladder loaded)."""
    last = -1; stable = 0
    for _ in range(40):
        try:
            n = await page.locator("select[name$='comboQty']").first.evaluate("el=>el.options.length")
        except Exception:
            n = 0
        if n == last and n > 5:
            stable += 1
            if stable >= 2:
                return True
        else:
            stable = 0
        last = n
        await asyncio.sleep(0.5)
    return last > 3


async def _avail(page):
    """Read comboQty options, retrying while the postback repopulates the select."""
    for _ in range(10):
        try:
            opts = await _opts(page, "comboQty")
        except Exception:
            opts = []
        nums = [int(q) for q in opts if q.isdigit()]
        if len(nums) >= 3:
            return nums
        await asyncio.sleep(0.8)
    return nums


async def _config(page, paper, colour):
    await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.8)
    if not await _sel(page, "ddlPaper", paper):
        return False
    if not await _sel(page, "rblPrintColourSide", colour):
        return False
    await asyncio.sleep(1.5)
    return True


async def _sweep(page, qtys):
    res = {}; prev = None
    for q in qtys:
        if not await _sel(page, "comboQty", str(q)):
            continue
        await asyncio.sleep(1.2)
        c = (await _safe_read(page)).get("before_discount")
        if c and c != prev:
            res[q] = c; prev = c
        elif c == prev:
            await _sel(page, "comboQty", str(qtys[0])); await _sel(page, "comboQty", str(q))
            await asyncio.sleep(1.2); c = (await _safe_read(page)).get("before_discount")
            if c:
                res[q] = c; prev = c
    return res


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "letterhead_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"core": []}
    # dedup existing
    seen = {};
    for r in data["core"]:
        seen[(r["paper"], r["colour"], r["qty"])] = r
    data["core"] = list(seen.values())
    from collections import Counter
    cnt = Counter((r["paper"], r["colour"]) for r in data["core"])
    done = {k for k, n in cnt.items() if n >= 6}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for paper in PAPERS:
            for colour in COLOURS:
                if (paper, colour) in done:
                    continue
                if not await _config(page, paper, colour):
                    log.info("lh.cfg_fail", paper=paper[:18], colour=colour); continue
                avail = await _avail(page)
                qtys = [q for q in QTYS if q in avail] or avail
                res = await _sweep(page, qtys)
                for q, c in res.items():
                    seen[(paper, colour, q)] = {"paper": paper, "colour": colour, "qty": q, "cash": c}
                data["core"] = list(seen.values())
                out.write_text(json.dumps(data, indent=0))
                log.info("lh.core", paper=paper[:16], colour=colour, n=len(res))
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: core={len(data['core'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
