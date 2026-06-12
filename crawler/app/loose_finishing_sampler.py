"""Sample Digital Loose Sheet (50) finishing add-on price DELTAS from the www order
page: hot stamping (ddlHotStamping), folding (rblFoldFormula), hole punch
(rblPunchHole). Each delta = price(with finishing) - base, captured across the qty
ladder. Folding can depend on size, so it's sampled at a few sizes.

  python -m app.loose_finishing_sampler [account]

Saves output/loose_finishing_50.json:
  {"hot_stamping":{opt:{qty:delta}}, "punch":{opt:{qty:delta}},
   "fold":{opt:{"WxH":{qty:delta}}}}
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .logging_setup import log
from .order_capture import (configure, OrderConfigSpec, _select, _check_delivery,
                            _parse_breakdown, _TOGGLE_HELPER)

OUT = Path(__file__).resolve().parent.parent / "output"
SPEC = "https://www.excard.com.my/spec/Digital/Loose_Sheet"
QTYS = [50, 100, 200, 500, 1000, 2000, 5000]
SIZES = ["210mm x 297mm (A4)", "148mm x 210mm (A5)", "105mm x 148mm (A6)"]
PAPER, COLOUR = "Gloss Art Paper 128gsm", "4C (Both)"


async def _price(page, deliv=98):
    h = _TOGGLE_HELPER.get(deliv, 99)
    await _check_delivery(page, h); await _check_delivery(page, deliv)
    return _parse_breakdown(await page.evaluate("()=>document.body.innerText")).get("before_discount")


async def _set_qty(page, q):
    if await page.locator("select[name$='comboQty']").count():
        await _select(page, "select[name$='comboQty']", str(q))


async def _radio_prefix(page, name, prefix):
    # These radios are HIDDEN (styled), so .check() fails — click via JS instead.
    loc = page.locator(f"input[name$='{name}']"); n = await loc.count()
    for i in range(n):
        v = await loc.nth(i).get_attribute("value")
        if v and v.startswith(prefix):
            await loc.nth(i).evaluate("el=>el.click()")
            try: await page.wait_for_load_state("networkidle", timeout=12000)
            except Exception: pass
            await asyncio.sleep(0.5); return True
    return False


async def _opts(page, name):
    sel = f"select[name$='{name}']"
    if not await page.locator(sel).count():
        return []
    return [o for o in await page.locator(sel).first.evaluate(
        "el=>[...el.options].map(o=>o.text.trim())") if o and not o.startswith("- ")]


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "loose_finishing_50.json"
    data = json.loads(out.read_text()) if out.exists() else {"hot_stamping": {}, "punch": {}, "fold": {}}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        async def base_at(size, q):
            await configure(page, OrderConfigSpec(50, size, PAPER, COLOUR, "Normal", 98, spec_url=SPEC))
            await _set_qty(page, q); return await _price(page)

        # hot stamping + punch: size-independent -> sample at A4 across qty
        size0 = SIZES[0]
        await configure(page, OrderConfigSpec(50, size0, PAPER, COLOUR, "Normal", 98, spec_url=SPEC))
        hs_opts = await _opts(page, "ddlHotStamping")
        for q in QTYS:
            await configure(page, OrderConfigSpec(50, size0, PAPER, COLOUR, "Normal", 98, spec_url=SPEC))
            await _set_qty(page, q); base = await _price(page)
            if not base: continue
            for hs in hs_opts:
                await _select(page, "select[name$='ddlHotStamping']", hs)
                p = await _price(page)
                if p: data["hot_stamping"].setdefault(hs, {})[str(q)] = round(p - base, 2)
                await _select(page, "select[name$='ddlHotStamping']", "- Not Required -")
            for pf, label in [("Hole Punching (3mm)", "3mm"), ("Hole Punching (6mm)", "6mm")]:
                if await _radio_prefix(page, "rblPunchHole", pf):
                    p = await _price(page)
                    if p: data["punch"].setdefault(label, {})[str(q)] = round(p - base, 2)
                    await _radio_prefix(page, "rblPunchHole", "-")
            out.write_text(json.dumps(data, indent=1))
            log.info("loose_fin.hs_punch", q=q, base=base)

        # folding: size-dependent -> sample each fold code at a few sizes
        for size in SIZES:
            await configure(page, OrderConfigSpec(50, size, PAPER, COLOUR, "Normal", 98, spec_url=SPEC))
            fold_vals = []
            loc = page.locator("input[name$='rblFoldFormula']")
            for i in range(await loc.count()):
                v = await loc.nth(i).get_attribute("value")
                if v and not v.startswith("-"):
                    fold_vals.append(v.split(",")[0])
            wxh = size.split("(")[0].strip().replace("mm x ", "x").replace("mm", "")
            for code in fold_vals:
                for q in [200, 1000, 5000]:
                    await configure(page, OrderConfigSpec(50, size, PAPER, COLOUR, "Normal", 98, spec_url=SPEC))
                    await _set_qty(page, q); base = await _price(page)
                    if not base: continue
                    if await _radio_prefix(page, "rblFoldFormula", code + ","):
                        p = await _price(page)
                        if p: data["fold"].setdefault(code, {}).setdefault(wxh, {})[str(q)] = round(p - base, 2)
            out.write_text(json.dumps(data, indent=1))
            log.info("loose_fin.fold_size", size=size, folds=len(fold_vals))
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=1))
    print(f"wrote {out.name}: hot_stamping={list(data['hot_stamping'])} punch={list(data['punch'])} fold={list(data['fold'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
