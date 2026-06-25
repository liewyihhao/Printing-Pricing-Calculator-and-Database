"""Dump any price/qty table text from a /product/<slug> page."""
import asyncio, sys
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts

SLUG = sys.argv[1] if len(sys.argv) > 1 else "money-packet"


async def run():
    a = accounts.get(1)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 2000})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        await page.goto(f"https://www.excard.com.my/product/{SLUG}", wait_until="networkidle")
        await asyncio.sleep(4)
        for _ in range(5):
            await page.mouse.wheel(0, 900); await asyncio.sleep(1)
        # every table that mentions RM or Qty
        tables = await page.evaluate("""()=>{
          const out=[];
          document.querySelectorAll('table').forEach(t=>{
            const txt=t.innerText.trim();
            if(/RM|qty|quantity|price|pcs|unit/i.test(txt)) out.push(txt.slice(0,800));});
          return out;}""")
        print(f"=== {SLUG}: {len(tables)} price-ish tables ===")
        for i, t in enumerate(tables):
            print(f"--- table {i} ---")
            print(t)
        await b.close()

asyncio.run(run())
