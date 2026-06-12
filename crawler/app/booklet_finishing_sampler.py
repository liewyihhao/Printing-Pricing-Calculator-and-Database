"""Sample Booklet (19 Litho / 37 Digital) finishing add-ons from the www order page.
The only priced cover add-ons online are HOT STAMPING (ddlCoverHSColourNum) and the
OUTER/INNER colour option (rbOuterInner). Lamination is compulsory/included in the
cover paper; Spot UV / embossing are not separately orderable online.

Robust to HIDDEN selects/radios (set via JS). Saves output/booklet_finishing_<id>.json:
  {"hot_stamping": {opt: {qty: delta}}, "outer_inner": {qty: delta}}

  python -m app.booklet_finishing_sampler 19 [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts, products
from .logging_setup import log
from .booklet_discovery import (ORIENT, SIZE, ORDERTYPE, BINDING, PAGE, COVER_PAPER,
                                COVER_COLOUR, CONTENT_PAPER, CONTENT_COLOUR, OUTER_INNER)
from .booklet_capture import sweep_quantities, BookletSpec
from . import booklet_capture

OUT = Path(__file__).resolve().parent.parent / "output"
QTYS = [100, 300, 500, 1000, 2000, 5000]


async def js_select(page, name, label):
    sel = f"select[name$='{name}']"
    if not await page.locator(sel).count():
        return False
    ok = await page.locator(sel).first.evaluate(
        "(el,l)=>{const o=[...el.options].find(o=>o.text.trim()===l);if(!o)return false;"
        "el.value=o.value;el.dispatchEvent(new Event('change'));return true;}", label)
    if ok:
        try: await page.wait_for_load_state("networkidle", timeout=12000)
        except Exception: pass
        await asyncio.sleep(0.6)
    return ok


async def js_radio(page, name, contains):
    loc = page.locator(f"input[name$='{name}']"); n = await loc.count()
    for i in range(n):
        lab = await loc.nth(i).evaluate(
            "el=>{const id=el.id;const l=id?document.querySelector(`label[for='${id}']`):null;return (l?l.innerText:el.value||'').trim();}")
        if contains in lab:
            await loc.nth(i).evaluate("el=>el.click()")
            try: await page.wait_for_load_state("networkidle", timeout=12000)
            except Exception: pass
            await asyncio.sleep(0.6); return True
    return False


async def configure(page, url, orient, size, ot, binding, page_n, cover, content):
    await page.goto(url, wait_until="domcontentloaded")
    try: await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception: pass
    await asyncio.sleep(1)
    await js_radio(page, "rblOrientation", orient)
    await js_select(page, "ddlSize", size)
    await js_radio(page, "rdbOrderType", ot)
    await js_radio(page, "rdbidning", binding)
    await js_select(page, "ddlPage", page_n)
    await js_select(page, "ddlCoverPaper", cover)
    await js_select(page, "ddlCoverPrintColour", "4C")
    await js_select(page, "ddlContentPaper", content)
    await js_select(page, "ddlContentPrintColour", "4C (Both)")


async def run(pid=19, account_id=1):
    a = accounts.get(account_id); url = products.get(pid).spec_url
    out = OUT / f"booklet_finishing_{pid}.json"
    data = json.loads(out.read_text()) if out.exists() else {"hot_stamping": {}, "outer_inner": {}}
    spec = BookletSpec(pid, url, "Portrait", "A5 (148mm x 210mm)", "Soft Cover",
                       "Saddle Stitch", "16", "Gloss Art Card 230gsm (2 side coated)",
                       "4C", "Gloss Art Paper 128gsm", "4C (Both)", "4C: 4 Colour Outer Only")
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        async def base():
            await configure(page, url, "Portrait", "A5 (148mm x 210mm)", "Soft Cover",
                            "Saddle Stitch", "16", "Gloss Art Card 230gsm (2 side coated)",
                            "Gloss Art Paper 128gsm")

        await base()
        hs_opts = [o for o in await page.locator("select[name$='ddlCoverHSColourNum']").first.evaluate(
            "el=>[...el.options].map(o=>o.text.trim())") if o and not o.startswith("- ")] \
            if await page.locator("select[name$='ddlCoverHSColourNum']").count() else []
        log.info("booklet_fin.hs_opts", pid=pid, opts=hs_opts)
        for q in QTYS:
            await base()
            base_rows = await sweep_quantities(page, spec, [q]); base_p = base_rows[0]["cash"] if base_rows else None
            if not base_p:
                continue
            for opt in hs_opts:
                await js_select(page, "ddlCoverHSColourNum", opt)
                r = await sweep_quantities(page, spec, [q])
                if r and r[0]["cash"]:
                    data["hot_stamping"].setdefault(opt, {})[str(q)] = round(r[0]["cash"] - base_p, 2)
                await js_select(page, "ddlCoverHSColourNum", "- Not Required -")
            # outer & inner
            await base()
            if await js_radio(page, "rbOuterInner", "Outer & 4 Colour Inner"):
                r = await sweep_quantities(page, spec, [q])
                if r and r[0]["cash"]:
                    data["outer_inner"][str(q)] = round(r[0]["cash"] - base_p, 2)
            out.write_text(json.dumps(data, indent=1))
            log.info("booklet_fin.q", pid=pid, q=q, base=base_p)
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=1))
    print(f"wrote {out.name}: hot_stamping={list(data['hot_stamping'])} outer_inner_qtys={list(data['outer_inner'])}")


if __name__ == "__main__":
    pid = int(sys.argv[1]) if len(sys.argv) > 1 else 19
    acct = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    asyncio.run(run(pid, acct))
