"""Probe Desk Calendar forms to understand options and pricing."""
import asyncio
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts

URLS = {
    "HardStand": "https://www.excard.com.my/spec/Litho/Desk_Calendar_(Hard_Stand)",
    "SoftStand": "https://www.excard.com.my/spec/Litho/Desk_Calendar_(Soft_Stand)",
}

async def get_radios(page):
    return await page.evaluate(
        "() => { var rows = [];"
        " var radios = document.querySelectorAll('input[type=radio]');"
        " for (var i=0; i<radios.length; i++) {"
        "   var r = radios[i];"
        "   var name = (r.name||'').split('$').pop();"
        "   if (/country|courier/i.test(name)) continue;"
        "   var p = r.closest('label') || r.parentElement;"
        "   var lbl = p ? p.innerText.trim() : r.value;"
        "   rows.push({name: name, value: r.value, label: lbl});"
        " }"
        " return rows; }"
    )

async def get_prices(page):
    return await page.evaluate(
        "() => { var els = document.querySelectorAll('[id],[class]');"
        " var out = [];"
        " for (var i=0; i<els.length; i++) {"
        "   var e = els[i];"
        "   if (!e.offsetParent) continue;"
        "   if (!/price|Price|cash|Cash/.test(e.id + e.className)) continue;"
        "   var t = e.innerText.trim().slice(0,80);"
        "   if (!t || t==='RM' || t.length<2) continue;"
        "   out.push({id: (e.id||'').split('$').pop(), t: t});"
        " }"
        " return out.slice(0,8); }"
    )

async def probe():
    a = accounts.get(1)
    async with async_playwright() as pw:
        b = await launch(pw)
        ctx = await b.new_context(viewport={"width": 1440, "height": 1600})
        page = await ctx.new_page()
        await login(page, username=a.username, password=a.password)

        for tag, url in URLS.items():
            print(f"\n=== {tag} ===")
            await page.goto(url, wait_until="domcontentloaded")
            try:
                await page.wait_for_load_state("networkidle", timeout=12000)
            except Exception:
                pass
            await asyncio.sleep(2)

            rows = await get_radios(page)
            for r in rows:
                print(f"  radio [{r['name']}] val={r['value']!r} lbl={r['label']!r}")

            for qty in ["100", "200", "500", "1000"]:
                await page.goto(url, wait_until="domcontentloaded")
                try:
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                await asyncio.sleep(1.5)
                try:
                    await page.select_option("select[name$='comboQty']", qty)
                    await asyncio.sleep(1.5)
                except Exception as ex:
                    print(f"  qty={qty}: select failed: {ex}")
                    continue
                prices = await get_prices(page)
                print(f"  qty={qty}: {prices}")

        await b.close()

if __name__ == "__main__":
    asyncio.run(probe())
