"""Screenshot /product/<slug> in headless to see what renders + dump iframes/forms again."""
import asyncio, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts

SLUG = sys.argv[1] if len(sys.argv) > 1 else "money-packet"
OUT = Path(__file__).resolve().parent.parent / "output"


async def run():
    a = accounts.get(1)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 2600})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        await page.goto(f"https://www.excard.com.my/product/{SLUG}", wait_until="networkidle")
        await asyncio.sleep(6)
        # count selects/iframes now
        n = await page.evaluate("()=>({selects:document.querySelectorAll('select').length, iframes:document.querySelectorAll('iframe').length, radios:document.querySelectorAll('input[type=radio]').length, bodyLen:document.body.innerText.length})")
        print("COUNTS:", n)
        # is there a 'Product Spec' tab? list tab-ish buttons
        tabs = await page.evaluate(r"""()=>[...document.querySelectorAll('a,button,li,div')].filter(e=>e.offsetParent&&/product spec|artwork spec|price list/i.test(e.innerText||'')&&(e.innerText||'').length<25).map(e=>e.innerText.trim()).filter((v,i,a)=>a.indexOf(v)===i)""")
        print("TABS:", tabs)
        p = OUT / f"shot_{SLUG}.png"
        await page.screenshot(path=str(p), full_page=False)
        print("SHOT:", p)
        await b.close()

asyncio.run(run())
