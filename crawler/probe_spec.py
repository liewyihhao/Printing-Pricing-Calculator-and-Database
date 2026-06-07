"""Explore the real order/spec page to validate our crawled prices against it."""
import asyncio
from playwright.async_api import async_playwright
from app.browser import launch, login, polite_pause
from app.config import OUTPUT_DIR

SPEC_URL = "https://www.excard.com.my/spec/Litho/Loose_Sheet"


async def main():
    async with async_playwright() as pw:
        b = await launch(pw)
        ctx = await b.new_context(viewport={'width':1440,'height':1200})
        page = await ctx.new_page()
        if not await login(page):
            raise SystemExit("login failed")
        await page.goto(SPEC_URL, wait_until="domcontentloaded")
        await polite_pause()
        print("URL:", page.url)
        print("TITLE:", await page.title())
        # Dump selects + their options, and any inputs / price-looking text.
        data = await page.evaluate(
            """() => {
                const sels=[...document.querySelectorAll('select')].map(s=>({
                    name:s.name||s.id, n:s.options.length,
                    sample:[...s.options].slice(0,4).map(o=>o.text.trim())}));
                const inputs=[...document.querySelectorAll('input')]
                  .filter(i=>/qty|quantity|price/i.test((i.name||'')+(i.id||'')))
                  .map(i=>({type:i.type,name:i.name||i.id,value:i.value}));
                const rmLines=[...document.body.innerText.split('\\n')]
                  .map(s=>s.trim()).filter(s=>/RM\\s*\\d/.test(s)).slice(0,15);
                return {selects:sels, inputs, rmLines};
            }""")
        print("\nSELECTS:")
        for s in data["selects"]:
            print(f"  {s['name']}: {s['n']} opts e.g. {s['sample']}")
        print("\nQTY/PRICE INPUTS:", data["inputs"])
        print("\nRM LINES ON PAGE:", data["rmLines"])
        (OUTPUT_DIR/"spec_page.html").write_text(await page.content(), encoding="utf-8")
        await page.screenshot(path=str(OUTPUT_DIR/"spec_page.png"), full_page=True)
        print("\nSaved spec_page.png / spec_page.html")
        await b.close()

asyncio.run(main())
