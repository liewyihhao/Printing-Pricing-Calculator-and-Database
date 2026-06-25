"""List frames + iframe srcs on a /product/<slug> page to find the embedded spec form."""
import asyncio, sys
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts

SLUG = sys.argv[1] if len(sys.argv) > 1 else "money-packet"


async def run():
    a = accounts.get(1)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 2200})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        await page.goto(f"https://www.excard.com.my/product/{SLUG}", wait_until="networkidle")
        await asyncio.sleep(5)
        print("FRAMES:")
        for f in page.frames:
            print("  ", repr(f.name), f.url)
        srcs = await page.evaluate("()=>[...document.querySelectorAll('iframe')].map(f=>f.src||f.getAttribute('data-src')||'')")
        print("IFRAME SRCS:", srcs)
        await b.close()

asyncio.run(run())
