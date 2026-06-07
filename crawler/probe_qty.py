"""Configure the Loose Sheet form, then dump every interactive control in the
order-spec area so we see exactly what the Quantity widget is."""
import os, asyncio
from playwright.async_api import async_playwright
from excard import log, polite_pause, launch_browser, login, OUT

PRICE_URL = os.getenv("EXCARD_PRICE_URL", "https://www.excard.com.my/price-list/Litho/21").strip()
M = "ctl00$mainContent$order_spec_controller1$order_spec_standard_matrix1$"


async def main():
    async with async_playwright() as pw:
        b = await launch_browser(pw)
        page = await (await b.new_context(viewport={"width": 1440, "height": 1000})).new_page()
        if not await login(page):
            raise SystemExit("login failed")
        await page.goto(PRICE_URL, wait_until="domcontentloaded"); await polite_pause()
        await page.select_option(f"select[name='{M}ddlSize']", label="A4 (210mm x 297mm)")
        await page.wait_for_load_state("networkidle"); await polite_pause()
        await page.select_option(f"select[name='{M}ddlPaper']",
                                 label="Gloss Art Card 250gsm (2 sides coated) - Best Seller")
        await page.wait_for_load_state("networkidle"); await polite_pause()
        # lamination radio/select
        lam = page.locator("select,input[type=radio]").filter(
            has=page.locator("option:text-is('Matte Lamination (Front)')")).first
        try:
            await page.locator(f"input[name='{M}rblLaminationSide']").first.check()
        except Exception:
            pass

        # Dump everything that looks like a quantity control.
        controls = await page.evaluate(
            """() => {
                const want = el => /qty|quantity/i.test((el.name||'')+(el.id||''));
                const out = [];
                document.querySelectorAll('select, input').forEach(el => {
                    if (!want(el)) return;
                    const box = el.getBoundingClientRect();
                    out.push({
                        tag: el.tagName, type: el.type||null, name: el.name||null, id: el.id||null,
                        value: el.value, visible: box.width>0 && box.height>0,
                        options: el.tagName==='SELECT' ? [...el.options].map(o=>o.text.trim()) : null
                    });
                });
                return out;
            }""")
        log(f"Found {len(controls)} qty-related controls:")
        for c in controls:
            log(f"  {c['tag']} type={c['type']} name={c['name']} id={c['id']} "
                f"visible={c['visible']} value={c['value']!r}")
            if c["options"]:
                log(f"     options: {c['options']}")
        await page.screenshot(path=str(OUT / "probe_qty.png"), full_page=True)
        await b.close()

asyncio.run(main())
