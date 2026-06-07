"""Configure the order/spec page for a known combo and read its price, to
compare against our crawled price-list data."""
import asyncio
from playwright.async_api import async_playwright
from app.browser import launch, login, polite_pause
from app.config import OUTPUT_DIR

SPEC_URL = "https://www.excard.com.my/spec/Litho/Loose_Sheet"
M = "ctl00$mainContent$order_spec_controller1$order_spec_standard_matrix1$"


async def sel(page, name, label):
    s = f"select[name='{name}']"
    if await page.locator(s).count() == 0:
        print(f"  (no select {name})"); return False
    await page.select_option(s, label=label)
    try: await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception: pass
    await polite_pause()
    return True


async def main():
    async with async_playwright() as pw:
        b = await launch(pw)
        ctx = await b.new_context(viewport={'width':1440,'height':1300})
        page = await ctx.new_page()
        if not await login(page): raise SystemExit("login failed")
        await page.goto(SPEC_URL, wait_until="domcontentloaded"); await polite_pause()

        await sel(page, M+"ddlSize", "A4 (210mm x 297mm)")
        await sel(page, M+"ddlPaper", "Gloss Art Card 250gsm (2 sides coated) - Best Seller")

        # Does a lamination field appear after paper?
        lam = page.locator("select").filter(has=page.locator("option:text-is('Matte Lamination (Front)')"))
        if await lam.count():
            print("LAMINATION field present -> selecting Matte Lamination (Front)")
            await lam.first.select_option(label="Matte Lamination (Front)")
            try: await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception: pass
            await polite_pause()
        else:
            print("NO lamination field on spec page for this paper.")

        await sel(page, M+"rblPrintColourSide", "4C (Front)")
        # Quantity
        await sel(page, M+"dynamic_qty1$comboQty", "1000")
        # Delivery: East Malaysia (98)
        loc = page.locator(f"input[name='{M}order_price1$rblOrderCountryCode'][value='98']").first
        if await loc.count():
            await loc.check()
            try: await page.wait_for_load_state("networkidle", timeout=12000)
            except Exception: pass
            await polite_pause()

        # Read the price block
        txt = await page.evaluate("() => document.body.innerText")
        import re
        print("\n--- PRICE BLOCK (spec page) ---")
        for ln in txt.split("\n"):
            s = ln.strip()
            if re.search(r"(PRICE|DISCOUNT|HANDLING|DELIVERY|TOTAL|AMOUNT).*RM|RM\s*\d", s, re.I):
                print("  ", s[:80])
        (OUTPUT_DIR/"spec_price.png").write_text  # noop guard
        await page.screenshot(path=str(OUTPUT_DIR/"spec_price.png"), full_page=True)
        print("\nSaved spec_price.png")
        await b.close()

asyncio.run(main())
