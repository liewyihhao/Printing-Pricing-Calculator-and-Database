"""Deep-inspect an /ordering/<slug> page: wait for the SPA form, scroll, then dump every
select/input/radio (name, visible, options) and any RM price."""
import asyncio, sys, re
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts

SLUG = sys.argv[1] if len(sys.argv) > 1 else "money-packet"


async def run():
    a = accounts.get(1)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1800})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        await page.goto(f"https://www.excard.com.my/product/{SLUG}", wait_until="networkidle")
        await asyncio.sleep(5)
        for _ in range(4):
            await page.mouse.wheel(0, 900); await asyncio.sleep(1.2)
        ctrls = await page.evaluate("""()=>{
          const out=[];
          document.querySelectorAll('select').forEach(s=>out.push({tag:'select',name:(s.name||s.id||'').split('$').pop(),
            vis:!!s.offsetParent, opts:[...s.options].map(o=>o.text.trim()).filter(t=>t).slice(0,12)}));
          document.querySelectorAll("input[type=radio]").forEach(r=>{if(r.offsetParent)out.push({tag:'radio',name:(r.name||'').split('$').pop(),val:r.value});});
          return out;}""")
        seen = set()
        for c in ctrls:
            key = (c.get("tag"), c.get("name"), str(c.get("val", "")))
            if c.get("name") and c.get("name") not in ("", "review-filter") and key not in seen:
                seen.add(key); print(" ", c)
        body = await page.evaluate("()=>document.body.innerText")
        print("RM:", re.findall(r"RM\s?[\d,]+(?:\.\d+)?", body)[:12])
        print("URL:", page.url, "| title:", await page.title())
        await b.close()

asyncio.run(run())
