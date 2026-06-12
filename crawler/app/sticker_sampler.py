"""Label Sticker price sampler (Digital + Letterpress, www order pages).

Custom-size product: price depends on (H,W) continuously/steppily, so we sample a
SIZE GRID per config plus the qty ladder. Stale-guard: every read is double-toggled
and a size/qty change must produce a different price than an identical neighbour
read, else re-read.

  python -m app.sticker_sampler digital [account]
  python -m app.sticker_sampler letterpress [account]

Saves output/sticker_samples_digital.json / _letterpress.json:
  {method, category, paper, colour, h, w, qty, cash, weight}
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .logging_setup import log
from .sticker_capture import (DIGITAL, LETTER, configure_digital, _read_price,
                              _wait, _sel, _radio_startswith, _fill_size)
from .order_capture import _read_weight

OUT = Path(__file__).resolve().parent.parent / "output"

# Size grid: spans small->A4-ish, denser at small sizes where steps are tighter.
SIZES = [(20, 20), (30, 30), (40, 40), (50, 50), (50, 70), (60, 60), (70, 100),
         (80, 80), (90, 130), (100, 100), (120, 120), (150, 150), (150, 210),
         (200, 200), (210, 297)]
QTYS_D = [10, 50, 100, 200, 300, 500, 1000, 2000, 3000, 5000, 8000]
QTYS_L = [500, 1000, 2000, 5000, 10000, 50000, 100000]

PAPERS = ["Mirror Kote", "Mirror Kote (Strong Glue)", "Transparent OPP",
          "White PP (Polypropylene)", "White PE (Polyethylene)", "Synthetic Paper",
          "Printing Paper", "Brown Craft Paper", "Matte Silver Polyester",
          "Bright Silver Polyester", "Removable Transparent OPP",
          "Removable White PP", "Warranty Sticker"]
CATEGORIES_D = ["Rectangle/Square", "Round", "Custom Die-Cut", "Kiss Cut", "No Cut"]
CATEGORIES_L = ["Standard Shape", "Round"]


def _digital_configs():
    """Stratified plan: full size grid on the anchor (MirrorKote/Rect/4C);
    reduced grids elsewhere to bound the crawl."""
    cfgs = []
    anchor_sizes, small = SIZES, [(30, 30), (60, 60), (100, 100), (150, 150)]
    for (h, w) in anchor_sizes:
        cfgs.append(("Rectangle/Square", "Mirror Kote", "4C,1", h, w))
    for cat in CATEGORIES_D:
        if cat == "Rectangle/Square":
            continue
        for (h, w) in small:
            cfgs.append((cat, "Mirror Kote", "4C,1", h, w))
    for paper in PAPERS:
        if paper == "Mirror Kote":
            continue
        for (h, w) in [(50, 50), (100, 100)]:
            cfgs.append(("Rectangle/Square", paper, "4C,1", h, w))
    for (h, w) in small:
        cfgs.append(("Rectangle/Square", "Mirror Kote", "1C,1", h, w))
    return cfgs


async def sample_digital(account_id=1, recycle_every=8):
    a = accounts.get(account_id)
    out = OUT / "sticker_samples_digital.json"
    results = json.loads(out.read_text()) if out.exists() else []
    done = {(r["category"], r["paper"], r["colour"], r["h"], r["w"]) for r in results}
    cfgs = [c for c in _digital_configs() if c not in done]
    print(f"digital sticker: {len(cfgs)} configs to sample ({len(done)} done)")
    async with async_playwright() as pw:
        b = await launch(pw)
        ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page()
        await login(page, username=a.username, password=a.password)
        n = 0
        for (cat, paper, colour, h, w) in cfgs:
            if n and n % recycle_every == 0:
                try: await ctx.close()
                except Exception: pass
                ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
                page = await ctx.new_page()
                await login(page, username=a.username, password=a.password)
            try:
                await page.goto(DIGITAL, wait_until="domcontentloaded"); await _wait(page)
                await configure_digital(page, paper, colour, cat, h, w, QTYS_D[0])
                prev = None
                for q in QTYS_D:
                    await _sel(page, "ddlQty", str(q))
                    bd = await _read_price(page)
                    cash = bd.get("before_discount")
                    if cash is None:
                        continue
                    if prev is not None and cash == prev:
                        bd = await _read_price(page)   # stale guard re-read
                        cash = bd.get("before_discount")
                        if cash == prev:
                            log.warning("sticker.stale_skip", q=q, cash=cash)
                            continue
                    results.append({"method": "digital", "category": cat, "paper": paper,
                                    "colour": colour, "h": h, "w": w, "qty": q,
                                    "cash": cash, "weight": await _read_weight(page)})
                    prev = cash
                out.write_text(json.dumps(results))
                log.info("sticker.config_done", cat=cat, paper=paper[:18], size=f"{h}x{w}",
                         total=len(results))
            except Exception as e:  # noqa: BLE001
                log.error("sticker.error", error=repr(e)[:120])
                try: await ctx.close()
                except Exception: pass
                ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
                page = await ctx.new_page()
                await login(page, username=a.username, password=a.password)
            n += 1
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(results))
    print(f"wrote {out.name} ({len(results)} points)")


async def sample_letterpress(account_id=1, recycle_every=8):
    a = accounts.get(account_id)
    out = OUT / "sticker_samples_letterpress.json"
    results = json.loads(out.read_text()) if out.exists() else []
    done = {(r["category"], r.get("hs_colour", ""), r["h"], r["w"]) for r in results}
    cfgs = []
    lp_sizes = [(20, 20), (30, 30), (40, 40), (50, 50), (50, 70), (60, 60), (70, 100),
                (80, 80), (90, 130), (100, 100), (120, 120), (150, 150), (150, 210)]
    for cat in CATEGORIES_L:
        for hs in ["Gold", "Silver"]:
            for (h, w) in lp_sizes:
                if (cat, hs, h, w) not in done:
                    cfgs.append((cat, hs, h, w))
    print(f"letterpress sticker: {len(cfgs)} configs to sample ({len(done)} done)")
    async with async_playwright() as pw:
        b = await launch(pw)
        ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page()
        await login(page, username=a.username, password=a.password)
        n = 0
        for (cat, hs, h, w) in cfgs:
            if n and n % recycle_every == 0:
                try: await ctx.close()
                except Exception: pass
                ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
                page = await ctx.new_page()
                await login(page, username=a.username, password=a.password)
            try:
                await page.goto(LETTER, wait_until="domcontentloaded"); await _wait(page)
                await _radio_startswith(page, "rdCategory", cat)
                await _fill_size(page, h, w)
                await _sel(page, "ddlHotStampingColour1", hs)
                prev = None
                for q in QTYS_L:
                    await _sel(page, "ddlQty", str(q))
                    bd = await _read_price(page)
                    cash = bd.get("before_discount")
                    if cash is None:
                        continue
                    if prev is not None and cash == prev:
                        bd = await _read_price(page)
                        cash = bd.get("before_discount")
                        if cash == prev:
                            continue
                    results.append({"method": "letterpress", "category": cat,
                                    "paper": "Sticker", "colour": "HS " + hs,
                                    "hs_colour": hs, "h": h, "w": w, "qty": q,
                                    "cash": cash, "weight": await _read_weight(page)})
                    prev = cash
                out.write_text(json.dumps(results))
                log.info("sticker.lp_done", cat=cat, hs=hs, size=f"{h}x{w}",
                         total=len(results))
            except Exception as e:  # noqa: BLE001
                log.error("sticker.error", error=repr(e)[:120])
                try: await ctx.close()
                except Exception: pass
                ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
                page = await ctx.new_page()
                await login(page, username=a.username, password=a.password)
            n += 1
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(results))
    print(f"wrote {out.name} ({len(results)} points)")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "digital"
    acct = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    asyncio.run(sample_digital(acct) if which == "digital" else sample_letterpress(acct))
