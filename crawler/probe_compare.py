"""Apples-to-apples: compare the order/spec page vs our crawled price-list DB for
a Simili paper (which our crawl captured WITHOUT lamination), to isolate whether
the earlier gap was purely lamination."""
import asyncio, re
from playwright.async_api import async_playwright
from app.browser import launch, login, polite_pause
from app.db import session_scope
from app.models import Combination, Pricing
from sqlalchemy import select

SPEC_URL = "https://www.excard.com.my/spec/Litho/Loose_Sheet"
M = "ctl00$mainContent$order_spec_controller1$order_spec_standard_matrix1$"
SIZE="A4 (210mm x 297mm)"; PAPER="Simili 80gsm - Best Seller"; QTY="1000"; DEL=98


def db_value():
    with session_scope() as s:
        combo = s.scalars(select(Combination).where(
            Combination.product_id==21, Combination.size_label==SIZE,
            Combination.paper_label==PAPER, Combination.delivery_code==DEL,
            Combination.lamination_label.is_(None))).first()
        if not combo: return "no combo in DB"
        rows = s.execute(select(Pricing.color_mode,Pricing.tier,Pricing.price).where(
            Pricing.combination_id==combo.id, Pricing.quantity==int(QTY))).all()
        return {f"{m}/{t}":float(p) for m,t,p in rows}


async def sel(page,name,label):
    s=f"select[name='{name}']"
    if await page.locator(s).count()==0: return
    await page.select_option(s,label=label)
    try: await page.wait_for_load_state("networkidle",timeout=15000)
    except Exception: pass
    await polite_pause()


async def main():
    print("DB (crawled price-list) A4/Simili80/None/East/qty1000:")
    print("  ", db_value())
    async with async_playwright() as pw:
        b=await launch(pw); ctx=await b.new_context(viewport={'width':1440,'height':1300}); page=await ctx.new_page()
        if not await login(page): raise SystemExit("login failed")
        await page.goto(SPEC_URL,wait_until="domcontentloaded"); await polite_pause()
        await sel(page,M+"ddlSize",SIZE)
        await sel(page,M+"ddlPaper",PAPER)
        await sel(page,M+"rblPrintColourSide","4C (Front)")
        await sel(page,M+"dynamic_qty1$comboQty",QTY)
        loc=page.locator(f"input[name='{M}order_price1$rblOrderCountryCode'][value='{DEL}']").first
        if await loc.count():
            await loc.check()
            try: await page.wait_for_load_state("networkidle",timeout=12000)
            except Exception: pass
            await polite_pause()
        txt=await page.evaluate("() => document.body.innerText")
        print("\nSPEC (order page) A4/Simili80/4C(Front)/East/qty1000:")
        for ln in txt.split("\n"):
            s=ln.strip()
            if re.search(r"(BEFORE DISCOUNT|AFTER DISCOUNT|DISCOUNT AMOUNT|HANDLING|DELIVERY FEES|Nett)",s,re.I):
                print("  ",s[:70])
        await b.close()

asyncio.run(main())
