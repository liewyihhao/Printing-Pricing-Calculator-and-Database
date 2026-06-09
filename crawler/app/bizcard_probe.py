"""Recon for v4.excard.com.my business-card ordering (a NEW platform vs the
ASP.NET www.excard.com.my). Goal: learn auth, DOM controls, and — crucially —
whether the SPA fetches prices from a JSON API we can call directly.

    python -m app.bizcard_probe
"""
from __future__ import annotations
import asyncio, json
from playwright.async_api import async_playwright
from .browser import launch
from . import accounts

URL = "https://v4.excard.com.my/ordering/business-card"
LOGIN_URL = "https://v4.excard.com.my/"


async def v4_login(page, a):
    await page.goto(LOGIN_URL, wait_until="domcontentloaded")
    await asyncio.sleep(2)
    # Fill both desktop + mobile username/password variants (whichever is active).
    for u in ("#TemplatedContent1_txtusername", "#TemplatedContent1_mtxtusername"):
        try: await page.fill(u, a.username, timeout=2000)
        except Exception: pass
    for p in ("#TemplatedContent1_txtpassword", "#TemplatedContent1_mtxtpassword"):
        try: await page.fill(p, a.password, timeout=2000)
        except Exception: pass
    await asyncio.sleep(0.5)
    # Click the LOGIN button (by visible text), fall back to Enter.
    clicked = False
    for sel in ("button:has-text('LOGIN')", "a:has-text('LOGIN')",
                "input[type=submit][value*='LOGIN' i]", "#TemplatedContent1_btnlogin"):
        try:
            loc = page.locator(sel).first
            if await loc.count():
                await loc.click(timeout=4000); clicked = True; break
        except Exception:
            continue
    if not clicked:
        try: await page.press("#TemplatedContent1_txtpassword", "Enter")
        except Exception: pass
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    await asyncio.sleep(2)
    print("after login URL:", page.url, "| logged_in:", "home-visitor" not in page.url)


async def probe():
    a = accounts.get(1)
    reqs = []
    async with async_playwright() as pw:
        browser = await launch(pw)
        ctx = await browser.new_context(viewport={"width": 1440, "height": 1200})
        page = await ctx.new_page()

        def on_req(r):
            if r.resource_type in ("xhr", "fetch") or "price" in r.url.lower() \
               or "ordering" in r.url.lower():
                reqs.append((r.method, r.url))
        page.on("request", on_req)

        await v4_login(page, a)
        reqs.clear()  # only care about traffic on the ordering page
        await page.goto(URL, wait_until="domcontentloaded")
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        await asyncio.sleep(3)
        print("FINAL URL:", page.url)
        print("TITLE:", await page.title())
        # All <select> controls with their option lists.
        sels = await page.evaluate(
            "() => [...document.querySelectorAll('select')].map(s=>({"
            "name:s.name||s.id, opts:[...s.options].map(o=>o.text.trim()).filter(Boolean)}))")
        print("\n--- SELECT controls + options ---")
        for s in sels:
            print(f"  [{s['name']}] -> {s['opts']}")
        # Radio groups by name.
        radios = await page.evaluate(
            "() => { const g={}; for(const r of document.querySelectorAll('input[type=radio]'))"
            "{ const k=r.name||'(noname)'; (g[k]=g[k]||[]).push(r.value||r.id);} return g; }")
        print("\n--- RADIO groups ---")
        for k, v in radios.items():
            print(f"  [{k}] -> {v}")
        # Checkboxes
        cbs = await page.evaluate(
            "() => [...document.querySelectorAll('input[type=checkbox]')].map(c=>c.name||c.id).filter(Boolean)")
        print("\n--- checkboxes ---", cbs)
        # Price-looking text on page
        price_txt = await page.evaluate(
            "() => { const els=[...document.querySelectorAll('*')].filter(e=>/RM\\s*[\\d,]+\\.\\d/.test(e.childNodes.length<3?e.innerText||'':'')); "
            "return els.slice(0,8).map(e=>({id:e.id,cls:e.className,t:(e.innerText||'').slice(0,40)})); }")
        print("\n--- price-looking elements ---")
        for p in price_txt:
            print("  ", p)
        print("\n--- XHR/fetch endpoints (ordering page) ---")
        for m, u in reqs:
            if "google" not in u and "linguise" not in u:
                print(f"  {m} {u[:160]}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(probe())
