"""Capture XHR/fetch the /product/<slug> React calculator makes — to find a pricing API."""
import asyncio, sys, json
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts

SLUG = sys.argv[1] if len(sys.argv) > 1 else "money-packet"


async def run():
    a = accounts.get(1)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1800})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        reqs = []
        page.on("request", lambda r: reqs.append((r.method, r.url, r.post_data))
                if any(k in r.url.lower() for k in ("api", "price", "quot", "calc", "spec", "product", "order"))
                and r.resource_type in ("xhr", "fetch") else None)
        await page.goto(f"https://www.excard.com.my/product/{SLUG}", wait_until="networkidle")
        await asyncio.sleep(4)
        for _ in range(4):
            await page.mouse.wheel(0, 900); await asyncio.sleep(1.2)
        # try clicking option-ish elements to trigger a recompute
        for sel in ["button", "[role=button]", ".option", "[class*=option]"]:
            try:
                els = page.locator(sel)
                n = min(await els.count(), 3)
                for i in range(n):
                    try: await els.nth(i).click(timeout=1500)
                    except Exception: pass
                    await asyncio.sleep(0.8)
            except Exception:
                pass
        print(f"=== {SLUG}: {len(reqs)} candidate requests ===")
        seen = set()
        for m, u, body in reqs:
            short = u.split("?")[0]
            if short in seen:
                continue
            seen.add(short)
            print(f"{m} {u[:130]}")
            if body:
                print(f"   BODY {str(body)[:200]}")
        await b.close()

asyncio.run(run())
