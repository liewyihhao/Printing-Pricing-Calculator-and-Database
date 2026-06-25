"""Inspect a /product/<slug> page: find Order/Quote buttons (href + onclick) and any
visible price text, and follow the order button to report the resulting URL."""
import asyncio, sys, re
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .billbook_sampler import _wait

SLUG = sys.argv[1] if len(sys.argv) > 1 else "money-packet"


async def run():
    a = accounts.get(1)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1600})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        await page.goto(f"https://www.excard.com.my/product/{SLUG}", wait_until="domcontentloaded")
        await _wait(page); await asyncio.sleep(2)
        # buttons / links mentioning order/quote/spec/price
        btns = await page.evaluate("""()=>{
          const out=[];
          document.querySelectorAll('a,button,input[type=button],div[onclick]').forEach(e=>{
            const t=(e.innerText||e.value||'').trim().slice(0,30);
            const oc=e.getAttribute('onclick')||''; const hf=e.getAttribute('href')||'';
            if(/order|quot|price|spec|buy|cart/i.test(t+oc+hf) && (t||oc||hf))
              out.push({t, href:hf.slice(0,80), onclick:oc.slice(0,90)});});
          return out.slice(0,12);}""")
        print(f"SLUG {SLUG}")
        for x in btns:
            print("  BTN", x)
        # any RM price visible in body
        body = await page.evaluate("()=>document.body.innerText")
        rm = re.findall(r"RM\s?[\d,]+(?:\.\d+)?", body)
        print("  RM-text:", rm[:15])
        # try clicking an order-ish button and report url
        try:
            loc = page.locator("a:has-text('Order'), button:has-text('Order'), a:has-text('Get'), a:has-text('Quot')").first
            if await loc.count():
                await loc.click(timeout=5000); await _wait(page); await asyncio.sleep(2)
                print("  AFTER CLICK URL:", page.url)
        except Exception as e:  # noqa: BLE001
            print("  click err", str(e)[:60])
        await b.close()

asyncio.run(run())
