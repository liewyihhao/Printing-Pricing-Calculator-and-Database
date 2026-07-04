"""Test: add a model row, THEN cycle #shirt_fabric on the row, reading price at qty50 each.
Verifies fabric-after-add recomputes reliably (avoids modal rebuild race).
Usage: python -m app.probe_fabric_after dtf-shirt "Polo (Short Sleeve)"
"""
import asyncio, sys
from playwright.async_api import async_playwright
from app import browser as B
from app import config
V4 = "https://v4.excard.com.my/ordering/"


async def login_v4(page):
    await page.goto("https://v4.excard.com.my/home-visitor/", wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(1500)
    await page.fill("#TemplatedContent1_txtusername", config.USERNAME)
    await page.fill("#TemplatedContent1_txtpassword", config.PASSWORD)
    try:
        async with page.expect_navigation(wait_until="domcontentloaded", timeout=20000):
            await page.click("#TemplatedContent1_excardLogin")
    except Exception:
        await page.click("#TemplatedContent1_excardLogin")
    await page.wait_for_timeout(2000)
    return "visitor" not in page.url.lower()


async def add_row(page, category, card_text):
    await page.click("#shirt_add_model")
    await page.wait_for_selector(".shirt-model-card", timeout=15000)
    await page.wait_for_timeout(500)
    try: await page.check(f"input[name='shirt_popup_category'][value='{category}']")
    except Exception: pass
    await page.wait_for_timeout(400)
    cards = page.locator(".shirt-model-card"); n = await cards.count()
    for i in range(n):
        t = (await cards.nth(i).inner_text()).strip()
        if card_text.lower() in t.lower():
            await cards.nth(i).click(); break
    await page.wait_for_timeout(400)
    await page.click(".shirt-popup-footer")
    await page.wait_for_selector(".shirt-qty-input", timeout=15000)
    await page.wait_for_timeout(500)


async def price(page, hold, qty=50):
    hold["price"] = None; hold["qty"] = None; hold["reqfab"] = None
    inp = page.locator(".shirt-qty-input").first
    await inp.click(); await inp.press("Control+A"); await inp.press("Delete")
    await inp.type(str(qty), delay=60); await inp.press("Tab")
    for _ in range(40):
        await page.wait_for_timeout(300)
        if hold["price"] is not None and hold["qty"] == str(qty):
            return hold["price"], hold.get("reqfab")
    return None, None


async def run(slug, model):
    hold = {}
    async with async_playwright() as pw:
        b = await B.launch(pw); page = await b.new_page()

        async def on_resp(resp):
            if "CheckPrice" in resp.url:
                try:
                    body = await resp.json(); req = resp.request.post_data_json
                    hold["price"] = float(str(body.get("Price")).replace(",", ""))
                    sp = req["spec"][0] if req else {}
                    hold["qty"] = str(sp.get("TotalQuantity"))
                    hold["reqfab"] = sp.get("Fabric") or sp.get("FabricType") or sp.get("Material")
                except Exception: pass
        page.on("response", lambda r: asyncio.create_task(on_resp(r)))
        print("login:", await login_v4(page))
        fabrics = ["Microfiber Mini Eyelet 150gsm", "CVC Honeycomb 180gsm", "Siro Cotton 190gsm"]
        print(f"Model={model} — fabric-first (fresh page each), generous wait:")
        for fab in fabrics:
            await page.goto(V4 + slug, wait_until="networkidle", timeout=40000)
            await page.wait_for_selector("#shirt_add_model", timeout=20000)
            await page.wait_for_timeout(800)
            try:
                await page.select_option("#shirt_fabric", label=fab)
            except Exception as e:
                print(f"  select err {fab}: {str(e)[:60]}"); continue
            # wait for the fabric-triggered rebuild to settle
            try: await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception: pass
            await page.wait_for_timeout(1500)
            try:
                await add_row(page, "Adult", model)
            except Exception as e:
                print(f"  {fab}: add_row failed {type(e).__name__}"); continue
            p, rf = await price(page, hold)
            print(f"  {fab}: price={p}  reqFabric={rf}")
        await b.close()

asyncio.run(run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "Round Neck (Short Sleeve)"))
