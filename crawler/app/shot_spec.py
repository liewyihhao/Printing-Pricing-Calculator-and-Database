import asyncio,sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
URL=sys.argv[1]
OUT=Path(__file__).resolve().parent.parent/"output"
async def run():
    a=accounts.get(1)
    async with async_playwright() as pw:
        b=await launch(pw);ctx=await b.new_context(viewport={"width":1300,"height":1700})
        page=await ctx.new_page();await login(page,username=a.username,password=a.password)
        await page.goto(URL,wait_until="domcontentloaded")
        try:
            await page.wait_for_load_state("networkidle",timeout=15000)
        except Exception: pass
        await asyncio.sleep(3)
        n=await page.evaluate("()=>({url:location.href,selects:document.querySelectorAll('select').length,radios:document.querySelectorAll('input[type=radio]').length})")
        print("INFO:",n)
        await page.screenshot(path=str(OUT/"shot_spec.png"))
        print("done")
        await b.close()
asyncio.run(run())
