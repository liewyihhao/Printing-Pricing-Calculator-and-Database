"""One-off: dump the real structure of Excard's login form so we can wire up
exact selectors (ASP.NET WebForms needs precise field IDs + hidden tokens)."""
import os, sys, io, asyncio
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = Path(__file__).parent
load_dotenv(HERE / ".env")
LOGIN_URL = os.getenv("EXCARD_LOGIN_URL", "https://www.excard.com.my/login")
OUT = HERE / "output"; OUT.mkdir(exist_ok=True)


async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(headless=True, channel="msedge")
        page = await b.new_page()
        await page.goto(LOGIN_URL, wait_until="networkidle")
        print("FINAL URL:", page.url)
        print("TITLE:", await page.title())
        (OUT / "login_page.html").write_text(await page.content(), encoding="utf-8")
        fields = await page.evaluate(
            """() => [...document.querySelectorAll('input, button, select')].map(e => ({
                tag: e.tagName, type: e.type||null, name: e.name||null, id: e.id||null,
                placeholder: e.placeholder||null, value: (e.type==='password'?'***':(e.value||'').slice(0,30)),
                text: (e.innerText||'').trim().slice(0,30)
            }))"""
        )
        print(f"\n{len(fields)} form elements:")
        for f in fields:
            print(" ", {k: v for k, v in f.items() if v})
        await b.close()

asyncio.run(main())
