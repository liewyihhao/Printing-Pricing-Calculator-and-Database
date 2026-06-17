"""Sample Bill-Book (Litho) prices. NCR carbonless book/pad.

Price drivers: PackForm(Book/Pad), Paper(NCR), Size, PaperMaterial(2-6 plies/layers),
PrintColorSide, Sets-per-book(50/100), Qty(books), + numbering / hole-punch deltas.
Binding orientation assumed price-neutral (fixed to Portrait - Left side binding).

Saves output/billbook_samples.json:
  {"core":[{size,layers,colour,sets,qty,cash}],         # A4 curves over the grid
   "size_scan":[{size,layers,colour,sets,qty,cash}],     # size factor at one config
   "finishing":[{kind,layers,colour,sets,qty,cash}],     # numbering / punch on-vs-off
   "packform":[{packform,...,cash}]}                     # Pad vs Book

  python -m app.billbook_sampler [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login, polite_pause
from . import accounts
from .logging_setup import log
from .sticker_capture import _read_price

OUT = Path(__file__).resolve().parent.parent / "output"
URL = "https://www.excard.com.my/spec/Litho/Bill-Book"
BIND = "Portrait - Left side binding"
LAYERS = ["NCR - 2 Layers", "NCR - 3 Layers", "NCR - 4 Layers", "NCR - 5 Layers", "NCR - 6 Layer"]
COLOURS = ["1C (Front)", "4C (Front)", "1C (Both)", "2C (Front)"]
QTYS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200, 300, 500, 1000]
SIZES = ["A4 (210mm x 297mm)", "B5 (176mm x 250mm)", "145mm x 210mm", "90mm x 140mm", "105mm x 145mm"]


async def _wait(page):
    try: await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception: pass
    await polite_pause()


async def _overlay_gone(page):
    """Wait for the ASP.NET 'Loading In Progress...' UpdateProgress overlay to clear."""
    for _ in range(40):
        try:
            busy = await page.evaluate(
                "() => { const e=document.getElementById('UpdateProgress1'); "
                "return e ? (e.getAttribute('aria-hidden')==='false' && e.offsetParent!==null) : false; }")
        except Exception:
            busy = False
        if not busy:
            return
        await asyncio.sleep(0.4)


async def _safe_read(page):
    """Read price after the loading overlay clears; retry once on transient failures."""
    for _ in range(2):
        await _overlay_gone(page)
        try:
            return await _read_price(page)
        except Exception:
            await asyncio.sleep(1.0)
    try:
        return await _read_price(page)
    except Exception:
        return {}


async def _radio(page, name, value):
    loc = page.locator(f"input[name$='{name}']"); n = await loc.count()
    for i in range(n):
        if (await loc.nth(i).get_attribute("value")) == value:
            await loc.nth(i).check(); await _wait(page); return True
    return False


async def _sel(page, name, label):
    sel = f"select[name$='{name}']"
    if not await page.locator(sel).count():
        return False
    for _ in range(12):
        if await page.locator(sel).first.evaluate("(el,l)=>[...el.options].some(o=>o.text.trim()===l)", label):
            break
        await asyncio.sleep(0.4)
    try:
        await page.select_option(sel, label=label, timeout=6000); await _wait(page); return True
    except Exception:
        return False


async def _opts(page, name):
    sel = f"select[name$='{name}']"
    if not await page.locator(sel).count():
        return []
    return await page.locator(sel).first.evaluate(
        "el=>[...el.options].map(o=>o.text.trim()).filter(t=>t && !t.startsWith('-') && t!=='Other')")


# standard NCR ply tint sequence (price is independent of which tint; selection required)
LAYER_TINTS = ["NCR White 50gsm", "NCR Green 50gsm", "NCR Blue 50gsm",
               "NCR Yellow 50gsm", "NCR Pink 50gsm", "NCR White 50gsm"]


def _n_layers(material):
    import re
    m = re.search(r"(\d+)", material or "")
    return int(m.group(1)) if m else 2


async def _config(page, packform, size, layers, colour):
    """Set the cascade up to (but not including) sets/qty. For 3+ layers the per-ply
    paper-tint dropdowns (ddlLayer1..N) must be set before ddlSets appears. Returns True."""
    await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.6)
    await _radio(page, "rblPackForm", packform)
    await _radio(page, "rblPaper", "NCR")
    if not await _sel(page, "ddlSize", size): return False
    if not await _sel(page, "ddlPaperMaterial", layers): return False
    for i in range(_n_layers(layers)):
        await _sel(page, f"ddlLayer{i+1}", LAYER_TINTS[i])
    if not await _sel(page, "ddlPrintColorSide", colour): return False
    await _sel(page, "ddlBindingLocation", BIND)
    return True


async def _sweep_qty(page, sets_label):
    if sets_label is not None:
        if not await _sel(page, "ddlSets", sets_label):
            return {}
    res = {}; prev = None
    for q in QTYS:
        if not await _sel(page, "comboQty", str(q)):
            continue
        await asyncio.sleep(0.8)
        c = (await _safe_read(page)).get("before_discount")
        if c and c != prev:
            res[q] = c; prev = c
        elif c == prev:
            await _sel(page, "comboQty", str(QTYS[0])); await _sel(page, "comboQty", str(q))
            await asyncio.sleep(0.8); c = (await _safe_read(page)).get("before_discount")
            if c: res[q] = c; prev = c
    return res


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "billbook_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"core": [], "size_scan": [], "finishing": [], "packform": []}
    # dedup any earlier duplicates, then build the done-set with a consistent size key
    seen = set(); uniq = []
    for r in data["core"]:
        k = (r["size"], r["layers"], r["colour"], r["sets"], r["qty"])
        if k not in seen:
            seen.add(k); uniq.append(r)
    data["core"] = uniq
    done = {(r["layers"], r["colour"], r["sets"], r["qty"]) for r in data["core"]}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        # 1) CORE curves at A4 over layers x colour x (sets if offered, else direct qty).
        #    2-ply books group into 50/100-set books (ddlSets); 3+ ply forms have NO
        #    ddlSets — comboQty is the set count directly (sets stored as "-").
        for layers in LAYERS:
            for colour in COLOURS:
                if not await _config(page, "Book", "A4 (210mm x 297mm)", layers, colour):
                    log.info("bb.cfg_fail", layers=layers, colour=colour); continue
                sets_opts = await _opts(page, "ddlSets")
                set_list = sets_opts if sets_opts else ["-"]
                for st in set_list:
                    if all((layers, colour, st, q) in done for q in QTYS):
                        continue
                    await _config(page, "Book", "A4 (210mm x 297mm)", layers, colour)
                    res = await _sweep_qty(page, st if sets_opts else None)
                    for q, c in res.items():
                        data["core"].append({"size": "A4", "layers": layers, "colour": colour,
                                              "sets": st, "qty": q, "cash": c})
                    out.write_text(json.dumps(data, indent=0))
                    log.info("bb.core", layers=layers[-8:], colour=colour, sets=st, n=len(res))

        # 2) SIZE scan at (2L, 1C(Front), sets100) over qty [50,200]
        for size in (SIZES if not data["size_scan"] else []):
            await _config(page, "Book", size, "NCR - 2 Layers", "1C (Front)")
            res = await _sweep_qty_small(page, "100", [50, 200])
            for q, c in res.items():
                data["size_scan"].append({"size": size, "layers": "NCR - 2 Layers", "colour": "1C (Front)",
                                           "sets": "100", "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("bb.size", size=size[:14], n=len(res))

        # 3) FINISHING deltas at (A4, 2L, 1C(Front), sets100, q100)
        if not data["finishing"]:
            await _config(page, "Book", "A4 (210mm x 297mm)", "NCR - 2 Layers", "1C (Front)")
            await _sel(page, "ddlSets", "100"); await _sel(page, "comboQty", "100"); await asyncio.sleep(0.8)
            base = (await _safe_read(page)).get("before_discount")
            data["finishing"].append({"kind": "base", "qty": 100, "cash": base})
            await _radio(page, "rdbNumbering", "yes")
            el = page.locator("input[name$='txtNumberingFrom']").first
            if await el.count():
                try: await el.fill("1"); await el.dispatch_event("change")
                except Exception: pass
            # txtHtmlNumberTo is readonly (auto-computed) — do not fill
            await _wait(page); await asyncio.sleep(0.8)
            data["finishing"].append({"kind": "numbering", "qty": 100, "cash": (await _safe_read(page)).get("before_discount")})
            await _radio(page, "rdbNumbering", "no"); await _wait(page)
            await _radio(page, "rblPunchHole", "Hole Punching (6mm)"); await _wait(page); await asyncio.sleep(0.8)
            data["finishing"].append({"kind": "punch", "qty": 100, "cash": (await _safe_read(page)).get("before_discount")})
            out.write_text(json.dumps(data, indent=0)); log.info("bb.finishing", base=base)

        # 4) PAD vs BOOK at (A4, 2L, 1C(Front), sets100, q100)
        if not data["packform"]:
            for pf in ["Book", "Pad"]:
                await _config(page, pf, "A4 (210mm x 297mm)", "NCR - 2 Layers", "1C (Front)")
                await _sel(page, "ddlSets", "100"); await _sel(page, "comboQty", "100"); await asyncio.sleep(0.8)
                data["packform"].append({"packform": pf, "qty": 100, "cash": (await _safe_read(page)).get("before_discount")})
            out.write_text(json.dumps(data, indent=0)); log.info("bb.packform")

        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: core={len(data['core'])} size_scan={len(data['size_scan'])} "
          f"finishing={len(data['finishing'])} packform={len(data['packform'])}")


async def _sweep_qty_small(page, sets_label, qtys):
    if not await _sel(page, "ddlSets", sets_label):
        return {}
    res = {}; prev = None
    for q in qtys:
        if not await _sel(page, "comboQty", str(q)):
            continue
        await asyncio.sleep(0.8)
        c = (await _safe_read(page)).get("before_discount")
        if c and c != prev:
            res[q] = c; prev = c
    return res


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
