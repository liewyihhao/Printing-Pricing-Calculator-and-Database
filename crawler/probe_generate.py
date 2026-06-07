"""Generate the price list, WAIT for the slow full-page postback to complete,
then dump the resulting price rows."""
import os, asyncio
from playwright.async_api import async_playwright
from excard import log, polite_pause, launch_browser, login, OUT

PRICE_URL = os.getenv("EXCARD_PRICE_URL", "https://www.excard.com.my/price-list/Litho/21").strip()
M = "ctl00$mainContent$order_spec_controller1$order_spec_standard_matrix1$"


async def main():
    async with async_playwright() as pw:
        b = await launch_browser(pw)
        page = await (await b.new_context(viewport={"width": 1440, "height": 1200})).new_page()
        if not await login(page):
            raise SystemExit("login failed")
        await page.goto(PRICE_URL, wait_until="domcontentloaded"); await polite_pause()
        await page.select_option(f"select[name='{M}ddlSize']", label="A4 (210mm x 297mm)")
        await page.wait_for_load_state("networkidle"); await polite_pause()
        await page.select_option(f"select[name='{M}ddlPaper']",
                                 label="Gloss Art Card 250gsm (2 sides coated) - Best Seller")
        await page.wait_for_load_state("networkidle"); await polite_pause()
        lam = page.locator("select").filter(
            has=page.locator("option:text-is('Matte Lamination (Front)')")).first
        await lam.select_option(label="Matte Lamination (Front)")
        await page.wait_for_load_state("networkidle"); await polite_pause()

        log("Generating (waiting for full postback, up to 40s)…")
        try:
            async with page.expect_navigation(wait_until="load", timeout=40000):
                await page.evaluate("() => __doPostBack('ctl00$mainContent$btnPriceList','')")
            log(f"Navigation complete -> {page.url}")
        except Exception as e:
            log(f"No full navigation ({type(e).__name__}); may be AJAX. Waiting for RM content…")
        # Either way, wait for real (non-zero) RM amounts.
        try:
            await page.wait_for_function(
                "() => /RM\\s*[1-9]/.test(document.body.innerText)", timeout=20000)
            log("Non-zero RM content present.")
        except Exception:
            log("Still no non-zero RM content.")

        await page.screenshot(path=str(OUT / "probe_generate.png"), full_page=True)
        (OUT / "probe_generate.html").write_text(await page.content(), encoding="utf-8")
        rm_lines = await page.evaluate(
            """() => [...document.body.innerText.split('\\n')]
                     .map(s=>s.trim()).filter(s=>/RM/.test(s)).slice(0,20)""")
        log("RM lines on page:")
        for l in rm_lines:
            log(f"   {l}")
        await b.close()

asyncio.run(main())
