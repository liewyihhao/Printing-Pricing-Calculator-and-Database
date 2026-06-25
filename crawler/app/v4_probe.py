"""Probe v4.excard.com.my: screenshot home + locate the login form fields."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch
OUT = Path(__file__).resolve().parent.parent / "output"


async def run():
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1300, "height": 1700})
        page = await ctx.new_page()
        await page.goto("https://v4.excard.com.my/", wait_until="networkidle")
        await asyncio.sleep(4)
        print("HOME URL:", page.url)
        # find login link/button
        loginish = await page.evaluate(r"""()=>[...document.querySelectorAll('a,button')]
          .filter(e=>e.offsetParent&&/log\s?in|sign\s?in|member/i.test(e.innerText||''))
          .map(e=>({t:(e.innerText||'').trim().slice(0,20), href:e.getAttribute('href')||''})).slice(0,8)""")
        print("LOGIN-ISH:", loginish)
        await page.screenshot(path=str(OUT / "v4_home.png"))
        # try the login route directly
        for path in ("/login", "/member-login", "/sign-in", "/member-auth-new"):
            try:
                await page.goto("https://v4.excard.com.my" + path, wait_until="domcontentloaded")
                await asyncio.sleep(2.5)
                inputs = await page.evaluate("()=>[...document.querySelectorAll('input')].filter(i=>i.offsetParent).map(i=>({type:i.type,name:i.name||i.id||'',ph:i.placeholder||''})).slice(0,10)")
                print(f"{path} url={page.url} inputs={inputs}")
            except Exception as e:  # noqa: BLE001
                print(path, "ERR", str(e)[:60])
        await page.screenshot(path=str(OUT / "v4_login.png"))
        await b.close()

asyncio.run(run())
