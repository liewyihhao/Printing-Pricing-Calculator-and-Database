"""Click the 'Product Spec' tab on /product/<slug>, then dump the spec form controls + price."""
import asyncio, sys
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts

SLUG = sys.argv[1] if len(sys.argv) > 1 else "money-packet"


async def run():
    a = accounts.get(1)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 2400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        await page.goto(f"https://www.excard.com.my/product/{SLUG}", wait_until="networkidle")
        await asyncio.sleep(4)
        # click the Product Spec tab (by text)
        for txt in ("Product Spec", "Product Spec ", "PRODUCT SPEC"):
            loc = page.locator(f"text={txt}").first
            if await loc.count():
                try:
                    await loc.click(timeout=4000); break
                except Exception:
                    pass
        await asyncio.sleep(4)
        ctrls = await page.evaluate(r"""()=>{
          const out={selects:[],radios:{},price:null};
          document.querySelectorAll('select').forEach(s=>{const n=(s.name||s.id||'').split('$').pop();
            if(n&&n!=='review-filter'&&!n.includes('Country'))
              out.selects.push({n,opts:[...s.options].map(o=>o.text.trim()).filter(t=>t).slice(0,10)});});
          document.querySelectorAll("input[type=radio]").forEach(r=>{if(r.offsetParent){const n=(r.name||'').split('$').pop();
            if(!n.includes('Country')&&!n.includes('Courier'))(out.radios[n]=out.radios[n]||[]).push(r.value);}});
          const m=document.body.innerText.match(/TOTAL AMOUNT[^R]*RM\s?[\d,]+\.?\d*/i);
          out.price=m?m[0].replace(/\s+/g,' '):null;
          return out;}""")
        print("SELECTS:")
        for s in ctrls["selects"]:
            print("  ", s["n"], s["opts"])
        print("RADIOS:", ctrls["radios"])
        print("PRICE:", ctrls["price"])
        await b.close()

asyncio.run(run())
