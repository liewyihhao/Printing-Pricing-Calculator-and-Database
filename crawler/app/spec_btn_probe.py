"""Find the orange 'Product Spec' button on /product/<slug>, click it, and report the
resulting URL + whether the calculator form (selects/radios) appears."""
import asyncio, sys
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts

SLUG = sys.argv[1] if len(sys.argv) > 1 else "money-packet"


async def run():
    a = accounts.get(1)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 2600})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        await page.goto(f"https://www.excard.com.my/product/{SLUG}", wait_until="networkidle")
        await asyncio.sleep(5)
        # find elements whose text is exactly 'Product Spec' (singular) — report tag/href/onclick
        cands = await page.evaluate(r"""()=>{
          const out=[];
          document.querySelectorAll('a,button,div,li,span').forEach(e=>{
            const t=(e.innerText||'').trim();
            if(/^Product Spec$/i.test(t)) out.push({tag:e.tagName, href:e.getAttribute('href')||'',
              onclick:(e.getAttribute('onclick')||'').slice(0,120), cls:e.className.toString().slice(0,40)});});
          return out;}""")
        print("ProductSpec(singular) candidates:", cands)
        # click the first one
        loc = page.locator("text=/^Product Spec$/").first
        if await loc.count():
            try:
                await loc.click(timeout=5000)
            except Exception as e:
                print("click err", str(e)[:60])
            await asyncio.sleep(5)
        n = await page.evaluate("()=>({url:location.href, selects:document.querySelectorAll('select').length, radios:document.querySelectorAll('input[type=radio]').length})")
        print("AFTER CLICK:", n)
        # list select names if any appeared
        names = await page.evaluate("()=>[...document.querySelectorAll('select')].map(s=>(s.name||s.id||'').split('$').pop()).filter(x=>x)")
        print("SELECT NAMES:", names)
        await b.close()

asyncio.run(run())
