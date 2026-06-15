"""Sample the Label Sticker 'Multiple Dieline' cut category (www Digital order page).

Multiple Dieline is a multi-design SHEET product: the customer nests several die-cut
designs (different size/shape each) on a press sheet and buys whole sheets. The price
drivers (all required, else the page shows a flat placeholder):
  * ddlCutToSheet -> "Delivery Sheet Size": A3+ (317x425) / A4 (210x297) / A5 (148x210)
  * txtTtlArtwork -> "Artwork die line(s) in a sheet" (designs nested per sheet)
  * ddlSheetQty   -> number of SHEETS (10 .. 1,000,000)
  * ddlpaper / rbprintcolour / ddlfinishing as usual

Saves output/sticker_multidieline.json:
  {"sheets":  [{sheet_size, dielines, paper, colour, sheet_qty, cash}],
   "dieline_sens": [{sheet_size, dielines, sheet_qty, cash}],   # txtTtlArtwork sensitivity
   "mat_sens":  [{paper, colour, sheet_size, sheet_qty, cash}]} # material/colour premium

  python -m app.multidieline_sampler [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .logging_setup import log
from .sticker_capture import DIGITAL, _wait, _radio_startswith, _sel, _read_price

OUT = Path(__file__).resolve().parent.parent / "output"
MD_CAT = "Multiple Dieline"
SHEET_SIZES = ["317mm x 425mm (A3+)", "210mm x 297mm (A4)", "148mm x 210mm (A5)"]
SS_KEY = {"317mm x 425mm (A3+)": "A3+", "210mm x 297mm (A4)": "A4", "148mm x 210mm (A5)": "A5"}
SHEET_QTYS = [10, 20, 30, 50, 100, 200, 500, 1000, 2000, 5000, 10000]


async def _fill(page, name, val):
    el = page.locator(f"input[name$='{name}']").first
    if await el.count():
        await el.fill(str(val)); await el.dispatch_event("change"); await el.dispatch_event("blur")
        await _wait(page); return True
    return False


async def _setup(page, paper="Mirror Kote", colour_prefix="4C,1"):
    await page.goto(DIGITAL, wait_until="domcontentloaded"); await _wait(page)
    await _radio_startswith(page, "rdType", "Sticker"); await asyncio.sleep(0.6)
    await _radio_startswith(page, "rdCategory", MD_CAT); await asyncio.sleep(1.2); await _wait(page)
    await _sel(page, "ddlpaper", paper)
    await _radio_startswith(page, "rbprintcolour", colour_prefix)


async def _config(page, sheet_size, dielines):
    await _sel(page, "ddlCutToSheet", sheet_size); await _wait(page)
    await _fill(page, "txtTtlArtwork", dielines)


async def _sel_qty(page, q):
    """Robustly select a ddlSheetQty option after AutoPostBack re-renders."""
    sel = "select[name$='ddlSheetQty']"
    for _ in range(20):  # poll until the option exists (postback may repopulate)
        try:
            has = await page.locator(sel).first.evaluate(
                "(el,l)=>[...el.options].some(o=>o.text.trim()===l)", str(q))
        except Exception:
            has = False
        if has:
            break
        await asyncio.sleep(0.5)
    else:
        return False
    try:
        await page.select_option(sel, label=str(q), timeout=8000); await _wait(page); return True
    except Exception:
        return False


async def _sweep_sheetqty(page, qtys):
    """Set ddlSheetQty across qtys; return {qty: cash} (skips stale repeats)."""
    res = {}; prev = None
    for q in qtys:
        if not await _sel_qty(page, q):
            continue
        await asyncio.sleep(1.2)
        c = (await _read_price(page)).get("before_discount")
        if c and c != prev:
            res[q] = c; prev = c
        elif c == prev:  # stale guard
            await _sel_qty(page, 10); await _sel_qty(page, q)
            await asyncio.sleep(1.2); c = (await _read_price(page)).get("before_discount")
            if c:
                res[q] = c; prev = c
    return res


async def densify(account_id=1):
    """Resample A4 + A5 base curves at a dense ladder and MERGE into the file."""
    a = accounts.get(account_id)
    out = OUT / "sticker_multidieline.json"
    data = json.loads(out.read_text())
    ladder = [10, 20, 30, 40, 50, 70, 100, 150, 200, 300, 500, 700, 1000, 2000]
    targets = ["210mm x 297mm (A4)", "148mm x 210mm (A5)"]
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for ss in targets:
            await _setup(page); await _config(page, ss, 10)
            res = await _sweep_sheetqty(page, ladder)
            have = {r["sheet_qty"] for r in data["sheets"] if r["sheet_size"] == SS_KEY[ss]}
            for q, c in res.items():
                if q not in have:
                    data["sheets"].append({"sheet_size": SS_KEY[ss], "dielines": 10,
                                           "paper": "Mirror Kote", "colour": "4C", "sheet_qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("md.densify", ss=SS_KEY[ss], n=len(res))
        try: await b.close()
        except Exception: pass
    print(f"densified: total base={len(data['sheets'])}")


async def fill(account_id=1):
    """Robust gap fill: FRESH page navigation + reconfigure for EACH (sheet_size, qty),
    so no postback-chain staleness. Slow but bulletproof. Merges into the file."""
    a = accounts.get(account_id)
    out = OUT / "sticker_multidieline.json"
    data = json.loads(out.read_text())
    want = {"A4": [30, 50, 70, 150, 300, 500, 700],
            "A5": [10, 30, 50, 70, 100, 150, 300, 500, 700, 1000]}
    label = {"A4": "210mm x 297mm (A4)", "A5": "148mm x 210mm (A5)"}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for ss_key, qtys in want.items():
            have = {r["sheet_qty"] for r in data["sheets"] if r["sheet_size"] == ss_key}
            for q in qtys:
                if q in have:
                    continue
                await _setup(page); await _config(page, label[ss_key], 10)
                if not await _sel_qty(page, q):
                    log.info("md.fill_miss", ss=ss_key, q=q); continue
                await asyncio.sleep(1.5)
                c = (await _read_price(page)).get("before_discount")
                if c:
                    data["sheets"].append({"sheet_size": ss_key, "dielines": 10,
                                           "paper": "Mirror Kote", "colour": "4C", "sheet_qty": q, "cash": c})
                    out.write_text(json.dumps(data, indent=0))
                    log.info("md.fill", ss=ss_key, q=q, cash=c)
                else:
                    log.info("md.fill_none", ss=ss_key, q=q)
        try: await b.close()
        except Exception: pass
    print(f"filled: base={len([r for r in data['sheets'] if r['paper']=='Mirror Kote' and r['colour']=='4C'])}")


# exact per-sheet-size sheet-qty ladders (from the live ddlSheetQty option dump)
FULL_LADDER = {
    "A3+": [1, 2, 3, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400, 500],
    "A4":  [2, 4, 6, 10, 20, 40, 60, 80, 100, 120, 140, 160, 180, 200, 400, 600, 800, 1000],
    "A5":  [4, 8, 12, 20, 40, 80, 120, 160, 200, 240, 280, 320, 360, 400, 800, 1200, 1600, 2000],
}


async def full(account_id=1):
    """Capture the COMPLETE ddlSheetQty ladder for every sheet size (Mirror Kote 4C),
    fresh-nav per point for robustness. Overwrites the base 'sheets' set so the curve is
    exact at every orderable sheet quantity. Preserves dieline_sens / mat_sens."""
    a = accounts.get(account_id)
    out = OUT / "sticker_multidieline.json"
    data = json.loads(out.read_text()) if out.exists() else {"sheets": [], "dieline_sens": [], "mat_sens": []}
    label = {"A3+": SHEET_SIZES[0], "A4": SHEET_SIZES[1], "A5": SHEET_SIZES[2]}
    fresh = []
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for ss_key, qtys in FULL_LADDER.items():
            for q in qtys:
                await _setup(page); await _config(page, label[ss_key], 10)
                if not await _sel_qty(page, q):
                    log.info("md.full_miss", ss=ss_key, q=q); continue
                await asyncio.sleep(1.3)
                c = (await _read_price(page)).get("before_discount")
                if c:
                    fresh.append({"sheet_size": ss_key, "dielines": 10, "paper": "Mirror Kote",
                                  "colour": "4C", "sheet_qty": q, "cash": c})
                    log.info("md.full", ss=ss_key, q=q, cash=c)
                # persist progress (replace base sheets with fresh-so-far + keep other papers)
                others = [r for r in data["sheets"] if not (r["paper"] == "Mirror Kote" and r["colour"] == "4C")]
                data["sheets"] = others + fresh
                out.write_text(json.dumps(data, indent=0))
        try: await b.close()
        except Exception: pass
    print(f"full capture: {len(fresh)} Mirror Kote 4C points across {len(FULL_LADDER)} sheet sizes")


async def dumpopts(account_id=1):
    """Print the actual ddlSheetQty option list for each sheet size (completeness check)."""
    a = accounts.get(account_id)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for ss in SHEET_SIZES:
            await _setup(page); await _config(page, ss, 10)
            await asyncio.sleep(1.0)
            opts = await page.locator("select[name$='ddlSheetQty']").first.evaluate(
                "el=>[...el.options].map(o=>o.text.trim()).filter(t=>t && !t.startsWith('-'))")
            print(f"{SS_KEY[ss]:4} ddlSheetQty options ({len(opts)}): {opts}")
        try: await b.close()
        except Exception: pass


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "sticker_multidieline.json"
    data = {"sheets": [], "dieline_sens": [], "mat_sens": []}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        # 1) BASE: each sheet size, dielines=10, Mirror Kote 4C, full sheet-qty sweep
        for ss in SHEET_SIZES:
            await _setup(page); await _config(page, ss, 10)
            res = await _sweep_sheetqty(page, SHEET_QTYS)
            for q, c in res.items():
                data["sheets"].append({"sheet_size": SS_KEY[ss], "dielines": 10,
                                       "paper": "Mirror Kote", "colour": "4C", "sheet_qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("md.base", ss=SS_KEY[ss], n=len(res))

        # 2) DIELINE SENSITIVITY: A3+, vary dielines, at a few sheet qtys
        for dl in [1, 5, 20, 40]:
            await _setup(page); await _config(page, SHEET_SIZES[0], dl)
            res = await _sweep_sheetqty(page, [50, 100, 500])
            for q, c in res.items():
                data["dieline_sens"].append({"sheet_size": "A3+", "dielines": dl, "sheet_qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("md.dieline", dl=dl, n=len(res))

        # 3) MATERIAL/COLOUR PREMIUM: A3+, dielines=10, q in [100,500]
        for paper, cpfx, cname in [("White PP (Polypropylene)", "4C,1", "4C"),
                                   ("Synthetic Paper", "4C,1", "4C"),
                                   ("Mirror Kote", "1C,1", "1C")]:
            await _setup(page, paper, cpfx); await _config(page, SHEET_SIZES[0], 10)
            res = await _sweep_sheetqty(page, [100, 500])
            for q, c in res.items():
                data["mat_sens"].append({"paper": paper, "colour": cname, "sheet_size": "A3+", "sheet_qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("md.mat", paper=paper[:10], colour=cname, n=len(res))

        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: base={len(data['sheets'])} dieline_sens={len(data['dieline_sens'])} "
          f"mat_sens={len(data['mat_sens'])}")
    for r in data["sheets"]:
        print(f"  {r['sheet_size']:4} dl{r['dielines']} x{r['sheet_qty']:>6} sheets -> RM{r['cash']}")


if __name__ == "__main__":
    acct = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    if len(sys.argv) > 2 and sys.argv[2] == "densify":
        asyncio.run(densify(acct))
    elif len(sys.argv) > 2 and sys.argv[2] == "fill":
        asyncio.run(fill(acct))
    elif len(sys.argv) > 2 and sys.argv[2] == "dumpopts":
        asyncio.run(dumpopts(acct))
    elif len(sys.argv) > 2 and sys.argv[2] == "full":
        asyncio.run(full(acct))
    else:
        asyncio.run(run(acct))
