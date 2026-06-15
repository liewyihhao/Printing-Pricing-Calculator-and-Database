"""Verify two candidate parity gaps on the www Digital sticker form:
  1. rblPackage (Nin1) — does it scale the price, and is it a pure xN multiplier?
  2. rdType — what are the options (Sticker vs CD)?

  python -m app.sticker_parity_probe [account]
"""
from __future__ import annotations
import asyncio, sys
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .sticker_capture import DIGITAL, _wait, _radio_startswith, _sel, _fill_size, _read_price


async def run(account_id=1):
    a = accounts.get(account_id)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        await page.goto(DIGITAL, wait_until="domcontentloaded"); await _wait(page)

        # rdType options
        rtypes = await page.locator("input[name$='rdType']").evaluate_all("els=>els.map(e=>e.value)")
        print("rdType options:", rtypes)

        # configure a standard Rectangle sticker
        await _radio_startswith(page, "rdType", "Sticker")
        await _radio_startswith(page, "rdCategory", "Rectangle/Square")
        await _sel(page, "ddlpaper", "Mirror Kote")
        await _radio_startswith(page, "rbprintcolour", "4C,1")
        await _fill_size(page, 50, 50)
        await _sel(page, "ddlQty", "500")

        # rblPackage options
        pkg_opts = await page.locator("select[name$='rblPackage'], input[name$='rblPackage']").first.evaluate(
            "el => el.tagName==='SELECT' ? [...el.options].map(o=>o.text.trim()) : el.value")
        print("rblPackage:", pkg_opts)

        base = (await _read_price(page)).get("before_discount")
        print(f"package=Normal q500 50x50 -> RM{base}")
        for pk in ["2in1", "4in1"]:
            try:
                await _sel(page, "rblPackage", pk); await _wait(page); await asyncio.sleep(1.0)
            except Exception:
                # rblPackage might be radios
                await _radio_startswith(page, "rblPackage", pk); await _wait(page); await asyncio.sleep(1.0)
            c = (await _read_price(page)).get("before_discount")
            ratio = round(c / base, 3) if (c and base) else None
            print(f"package={pk} -> RM{c}  ratio vs Normal={ratio}")
        try: await b.close()
        except Exception: pass


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
