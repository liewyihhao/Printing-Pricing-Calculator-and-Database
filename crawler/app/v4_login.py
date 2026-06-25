"""Log into v4.excard.com.my with the crawler account, then open a product's spec
calculator and dump its controls + price."""
import asyncio, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch
from . import config
OUT = Path(__file__).resolve().parent.parent / "output"
SLUG = sys.argv[1] if len(sys.argv) > 1 else "money-packet"


async def v4_login(page):
    await page.goto("https://v4.excard.com.my/", wait_until="networkidle")
    await asyncio.sleep(3)
    # open the LOGIN modal (top-right button)
    for sel in ["text=/^LOGIN$/", "text=/^Login$/", "a:has-text('LOGIN')", "button:has-text('LOGIN')"]:
        loc = page.locator(sel).first
        if await loc.count():
            try: await loc.click(timeout=4000); break
            except Exception: pass
    await asyncio.sleep(2)
    # dump the modal's visible inputs so we know the right selectors
    modal_inputs = await page.evaluate("()=>[...document.querySelectorAll('input')].filter(i=>i.offsetParent).map(i=>({type:i.type,name:i.name||i.id||'',ph:i.placeholder||''}))")
    print("MODAL INPUTS:", modal_inputs)
    await page.screenshot(path=str(OUT / "v4_loginmodal.png"))
    try:
        await page.fill("input[name$='txtusername']", config.USERNAME, timeout=6000)
        await page.fill("input[name$='txtpassword']", config.PASSWORD, timeout=6000)
        try:
            async with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
                await page.press("input[name$='txtpassword']", "Enter")
        except Exception:
            pass
        try: await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception: pass
    except Exception as e:  # noqa: BLE001
        print("login fill err", str(e)[:80])
    # detect logged-in state (LOGIN button gone / account number shown)
    has_login = await page.evaluate(r"()=>/\bLOGIN\b/.test(document.body.innerText)")
    print("after login url:", page.url, "| still shows LOGIN:", has_login)


async def run():
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1300, "height": 2200})
        page = await ctx.new_page()
        await v4_login(page)
        await page.goto(f"https://v4.excard.com.my/product/{SLUG}", wait_until="networkidle")
        await asyncio.sleep(5)
        # click the orange 'Product Spec' button/tab
        for sel in ["text=/^Product Spec$/", "text=Product Spec"]:
            loc = page.locator(sel).first
            if await loc.count():
                try: await loc.click(timeout=4000); break
                except Exception: pass
        await asyncio.sleep(4)
        info = await page.evaluate(r"""()=>{
          const out={url:location.href,selects:[],radios:{}};
          document.querySelectorAll('select').forEach(s=>{const n=(s.name||s.id||'').split('$').pop();
            if(n&&n!=='review-filter'&&!/country/i.test(n))out.selects.push({n,opts:[...s.options].map(o=>o.text.trim()).filter(t=>t).slice(0,8)});});
          document.querySelectorAll("input[type=radio]").forEach(r=>{if(r.offsetParent){const n=(r.name||'').split('$').pop();
            if(!/country|courier/i.test(n))(out.radios[n]=out.radios[n]||[]).push(r.value);}});
          return out;}""")
        print("URL:", info["url"])
        print("SELECTS:")
        for s in info["selects"]:
            print("  ", s["n"], s["opts"])
        print("RADIOS:", info["radios"])
        await page.screenshot(path=str(OUT / f"v4_{SLUG}.png"))
        await b.close()

asyncio.run(run())
