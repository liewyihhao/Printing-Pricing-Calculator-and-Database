"""Capture Label Sticker prices from www order pages (Digital + Letterpress).
Custom size via txtHeight/txtWidth. Price read uses the proven delivery-toggle.

Test:  python -m app.sticker_capture
"""
from __future__ import annotations
import asyncio, re
from playwright.async_api import Page
from .browser import polite_pause, ensure_session
from .order_capture import _parse_breakdown, _check_delivery, _TOGGLE_HELPER

DIGITAL = "https://www.excard.com.my/spec/Digital/Label_Sticker"
LETTER = "https://www.excard.com.my/spec/Letterpress/Label_Sticker_with_Hot_Stamping"
PFX_D = "order_spec_do_sticker1"
PFX_L = "order_spec_letterpress_sticker1"


async def _wait(page):
    try: await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception: pass
    await polite_pause()


async def _sel(page, name, label):
    sel = f"select[name$='{name}']"
    if not await page.locator(sel).count():
        return False
    for _ in range(8):
        if await page.locator(sel).first.evaluate(
                "(el,l)=>[...el.options].some(o=>o.text.trim()===l)", label):
            break
        await asyncio.sleep(0.4)
    await page.select_option(sel, label=label); await _wait(page); return True


async def _radio_startswith(page, name, prefix):
    loc = page.locator(f"input[name$='{name}']")
    n = await loc.count()
    for i in range(n):
        v = await loc.nth(i).get_attribute("value")
        if v and v.startswith(prefix):
            await loc.nth(i).check(); await _wait(page); return True
    return False


async def _fill_size(page, h, w):
    for nm, val in (("txtHeight", h), ("txtWidth", w)):
        el = page.locator(f"input[name$='{nm}']").first
        await el.fill(str(val))
        await el.dispatch_event("change"); await el.dispatch_event("blur")
    await _wait(page)


async def _read_price(page, delivery=98):
    helper = _TOGGLE_HELPER.get(delivery, 99)
    await _check_delivery(page, helper); await _check_delivery(page, delivery)
    txt = await page.evaluate("() => document.body.innerText")
    return _parse_breakdown(txt)


async def configure_digital(page, paper, colour, category_prefix, h, w, qty, package="Normal"):
    await ensure_session(page)
    await _radio_startswith(page, "rdType", "Sticker")
    await _radio_startswith(page, "rdCategory", category_prefix)
    await _sel(page, "ddlpaper", paper)
    await _radio_startswith(page, "rbprintcolour", colour)   # "4C,1" / "1C,1"
    await _fill_size(page, h, w)
    await _sel(page, "ddlpaper$noop", "x") if False else None
    # qty
    await _sel(page, "ddlQty", str(qty))
    return True


if __name__ == "__main__":
    import asyncio
    from playwright.async_api import async_playwright
    from .browser import launch, login
    from . import accounts

    async def test():
        a = accounts.get(1)
        async with async_playwright() as pw:
            b = await launch(pw); ctx = await b.new_context(viewport={"width":1440,"height":1300})
            page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
            await page.goto(DIGITAL, wait_until="domcontentloaded"); await _wait(page)
            # min/max size hint text near inputs
            hint = await page.evaluate(r"""() => { const b=document.body.innerText;
                const m=b.match(/(min|minimum|max|maximum)[^\n]{0,80}mm[^\n]{0,40}/gi); return m?m.slice(0,8):[]; }""")
            print("SIZE HINTS:", hint)
            for (h,w,q) in [(50,50,100),(50,50,500),(100,100,100),(100,100,500),(30,30,100)]:
                await page.goto(DIGITAL, wait_until="domcontentloaded"); await _wait(page)
                await configure_digital(page, "Mirror Kote", "4C,1", "Rectangle/Square", h, w, q)
                bd = await _read_price(page)
                print(f"  {h}x{w}mm 4C MirrorKote q{q} Normal -> before_disc={bd.get('before_discount')} nett={bd.get('nett')}")
            await b.close()
    asyncio.run(test())
