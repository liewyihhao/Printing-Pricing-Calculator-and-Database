"""Foundation test: configure one order-page config and sweep several quantities,
capturing the full price breakdown for each. Establishes the capture mechanic."""
import asyncio, re, time
from playwright.async_api import async_playwright
from app.browser import launch, login, polite_pause

SPEC_URL = "https://www.excard.com.my/spec/Litho/Loose_Sheet"
M = "ctl00$mainContent$order_spec_controller1$order_spec_standard_matrix1$"
QSEL = f"select[name='{M}dynamic_qty1$comboQty']"


def parse_breakdown(txt):
    g = lambda lbl: (re.search(lbl + r"\s*RM\s*([\d,]+\.\d{2})", txt, re.I) or [None, None])[1]
    return {
        "before_discount": g("PRICE BEFORE DISCOUNT"),
        "discount_amount": g("DISCOUNT AMOUNT"),
        "after_discount": g("PRICE AFTER DISCOUNT"),
        "handling": g("HANDLING FEE"),
        "delivery": g("DELIVERY FEES"),
        "nett": g("Nett Price"),
    }


async def sel(page, name, label):
    s = f"select[name='{name}']"
    if await page.locator(s).count() == 0:
        return
    await page.select_option(s, label=label)
    try: await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception: pass
    await polite_pause()


async def main():
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={'width':1440,'height':1200}); page = await ctx.new_page()
        if not await login(page): raise SystemExit("login failed")
        await page.goto(SPEC_URL, wait_until="domcontentloaded"); await polite_pause()
        await sel(page, M+"ddlSize", "A4 (210mm x 297mm)")
        await sel(page, M+"ddlPaper", "Simili 80gsm - Best Seller")
        await sel(page, M+"rblPrintColourSide", "4C (Front)")
        # delivery East Malaysia
        loc = page.locator(f"input[name='{M}order_price1$rblOrderCountryCode'][value='98']").first
        if await loc.count():
            await loc.check()
            try: await page.wait_for_load_state("networkidle", timeout=12000)
            except Exception: pass
            await polite_pause()

        # available quantities
        qtys = await page.locator(QSEL).evaluate(
            "el => [...el.options].map(o=>o.text.trim()).filter(t=>/^\\d/.test(t))")
        print(f"{len(qtys)} quantities available. Sweeping first 5…")
        for q in qtys[:5]:
            t = time.time()
            await page.select_option(QSEL, label=q)
            try: await page.wait_for_load_state("networkidle", timeout=12000)
            except Exception: pass
            await asyncio.sleep(0.6)
            txt = await page.evaluate("() => document.body.innerText")
            bd = parse_breakdown(txt)
            print(f"  qty {q:>6}: nett={bd['nett']} before={bd['before_discount']} "
                  f"deliv={bd['delivery']}  ({time.time()-t:.1f}s)")
        await b.close()

asyncio.run(main())
