"""Find out how the order page computes price: is there a lightweight price
endpoint we can call per-combo (fast), or only full postbacks (slow)?"""
import asyncio, time
from playwright.async_api import async_playwright
from app.browser import launch, login, polite_pause

SPEC_URL = "https://www.excard.com.my/spec/Litho/Loose_Sheet"
M = "ctl00$mainContent$order_spec_controller1$order_spec_standard_matrix1$"
calls = []


async def sel(page, name, label):
    s=f"select[name='{name}']"
    if await page.locator(s).count()==0: return
    await page.select_option(s,label=label)
    try: await page.wait_for_load_state("networkidle",timeout=15000)
    except Exception: pass
    await polite_pause()


async def main():
    async with async_playwright() as pw:
        b=await launch(pw); ctx=await b.new_context(viewport={'width':1440,'height':1200}); page=await ctx.new_page()

        async def on_req(req):
            if "excard.com.my" in req.url and req.method=="POST":
                calls.append((req.url.split("?")[0], req.method, (req.post_data or "")[:60]))
        page.on("request", on_req)

        if not await login(page): raise SystemExit("login failed")
        await page.goto(SPEC_URL,wait_until="domcontentloaded"); await polite_pause()
        await sel(page,M+"ddlSize","A4 (210mm x 297mm)")
        await sel(page,M+"ddlPaper","Simili 80gsm - Best Seller")
        await sel(page,M+"rblPrintColourSide","4C (Front)")

        # Time a quantity change.
        calls.clear()
        t=time.time()
        await page.select_option(f"select[name='{M}dynamic_qty1$comboQty']", label="1000")
        try: await page.wait_for_load_state("networkidle",timeout=15000)
        except Exception: pass
        dt=time.time()-t
        print(f"\nQuantity change took {dt:.1f}s; POST requests fired:")
        for u,m,d in calls:
            print(f"  {m} {u}")
        # Is it a full-page postback (__doPostBack to the page) or a scriptservice?
        await b.close()

asyncio.run(main())
