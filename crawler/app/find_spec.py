"""Find the real /spec order-form URL(s) linked from given /product/<slug> pages."""
import asyncio, sys
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .billbook_sampler import _wait

SLUGS = sys.argv[1:] or ["money-packet", "non-woven-bag", "mask-keeper"]


async def run():
    a = accounts.get(1)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(); page = await ctx.new_page()
        await login(page, username=a.username, password=a.password)
        for slug in SLUGS:
            try:
                await page.goto(f"https://www.excard.com.my/product/{slug}", wait_until="domcontentloaded")
                await _wait(page); await asyncio.sleep(1.5)
                links = await page.evaluate(
                    "()=>[...document.querySelectorAll('a')].map(a=>a.getAttribute('href')||'')"
                    ".filter(h=>h.includes('/spec/')).filter((v,i,a)=>a.indexOf(v)===i)")
                # also any onclick/data nav and the current url after a redirect
                print(f"{slug} -> {links[:8]}")
            except Exception as e:  # noqa: BLE001
                print(f"{slug} ERR {str(e)[:90]}")
        await b.close()

asyncio.run(run())
