"""Diagnose Hand Fan / Hanger price rendering."""
import asyncio, sys
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .billbook_sampler import _sel, _safe_read, _wait

URL = sys.argv[1] if len(sys.argv) > 1 else "https://www.excard.com.my/spec/Digital/Hand_Fan"
PAPER = sys.argv[2] if len(sys.argv) > 2 else "Gloss Art Card 310gsm"


async def run():
    a = accounts.get(1)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1500})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        await page.goto(URL, wait_until="domcontentloaded"); await _wait(page)
        await asyncio.sleep(1.5)
        ok_p = await _sel(page, "ddlPaper", PAPER)
        print("paper select ok:", ok_p)
        # list all selects + their current values
        sels = await page.evaluate(
            "()=>Array.from(document.querySelectorAll('select')).map(s=>({name:s.name,val:s.value,opts:s.options.length}))")
        print("selects:", [s for s in sels if 'Country' not in s['name']])
        from .billbook_sampler import _opts
        ok_q = await _sel(page, "comboQty", "100")
        print("qty select ok:", ok_q); await asyncio.sleep(1.0)
        lo = await _opts(page, "rblLaminationSide")
        print("lam opts:", lo)
        if lo:
            print("lam select ok:", await _sel(page, "rblLaminationSide", lo[0]))
        await asyncio.sleep(2.5)
        r = await _safe_read(page)
        print("price read (lam last):", r)
        # any still-empty required selects?
        empties = await page.evaluate(
            "()=>Array.from(document.querySelectorAll('select')).filter(s=>s.name && !s.value).map(s=>s.name.split('$').pop())")
        print("empty selects:", empties)
        # dump any element that looks like a price
        txt = await page.evaluate(
            "()=>{var out=[];document.querySelectorAll('[id*=Price],[id*=price],[id*=Total],[id*=Amount]').forEach(e=>{if(e.innerText&&e.innerText.trim())out.push([e.id,e.innerText.trim().slice(0,40)]);});return out;}")
        print("price-ish elements:", txt[:15])
        try: await b.close()
        except Exception: pass

asyncio.run(run())
