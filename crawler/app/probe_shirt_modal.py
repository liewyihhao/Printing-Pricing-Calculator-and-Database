"""Explore the +ADD MODEL modal on a v4 readymade shirt ordering page, add one row,
dump per-row fields, and drive a quantity to capture a CheckPrice price.
Usage: python -m app.probe_shirt_modal dtf-shirt
"""
import asyncio, sys, json
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


async def run(slug):
    hold = {}
    async with async_playwright() as pw:
        b = await B.launch(pw)
        page = await b.new_page()

        async def on_resp(resp):
            if "CheckPrice" in resp.url:
                try:
                    hold["resp"] = await resp.json(); hold["req"] = resp.request.post_data_json
                    print("  >>CheckPrice qty",
                          (hold["req"]["spec"][0].get("TotalQuantity") if hold["req"] else "?"),
                          "Price", hold["resp"].get("Price"))
                except Exception as e:
                    print("  resperr", str(e)[:80])
        page.on("response", lambda r: asyncio.create_task(on_resp(r)))

        print("login:", await login_v4(page))
        await page.goto(V4 + slug, wait_until="networkidle", timeout=40000)
        await page.wait_for_timeout(1500)

        # open modal
        await page.click("#shirt_add_model")
        await page.wait_for_timeout(1500)
        modal = await page.evaluate(r"""()=>{
          const out={catRadios:{},cards:[],selects:[],footer:[]};
          document.querySelectorAll("input[type=radio]").forEach(r=>{if(!r.offsetParent)return;
            if(/popup|category/i.test(r.name))(out.catRadios[r.name]=out.catRadios[r.name]||[]).push(r.value);});
          document.querySelectorAll(".shirt-model-card").forEach(c=>{out.cards.push(c.innerText.trim().slice(0,40));});
          document.querySelectorAll(".shirt-popup select,.shirt-popup-footer,[class*=popup] select").forEach(s=>{
            if(s.tagName==='SELECT')out.selects.push({id:s.id||s.name,opts:[...s.options].map(o=>o.text.trim()).slice(0,10)});});
          document.querySelectorAll("[class*=popup-footer],.shirt-popup-footer").forEach(f=>out.footer.push(f.innerText.trim().slice(0,40)));
          return out;}""")
        print("MODAL:", json.dumps(modal, indent=1)[:1500])

        # try to add a model: Adult + first card + confirm
        try:
            await page.check("input[name='shirt_popup_category'][value='Adult']")
        except Exception as e:
            print("cat err", str(e)[:60])
        await page.wait_for_timeout(400)
        cards = page.locator(".shirt-model-card")
        if await cards.count():
            await cards.nth(0).click()
        await page.wait_for_timeout(400)
        try:
            await page.click(".shirt-popup-footer")
        except Exception as e:
            print("footer click err", str(e)[:60])
        await page.wait_for_timeout(1500)

        # dump per-row fields
        row = await page.evaluate(r"""()=>{
          const out={selects:[],inputs:[],radios:{}};
          document.querySelectorAll('select').forEach(s=>{if(!s.offsetParent)return;
            out.selects.push({id:s.id||s.name,opts:[...s.options].map(o=>o.text.trim()).slice(0,10)});});
          document.querySelectorAll("input").forEach(i=>{if(!i.offsetParent)return;
            if(i.type==='radio'){(out.radios[i.name]=out.radios[i.name]||[]).push(i.value);}
            else out.inputs.push({id:i.id||i.name||i.className,type:i.type});});
          return out;}""")
        print("AFTER ADD ROW selects:", json.dumps(row["selects"])[:900])
        print("AFTER ADD ROW radios:", json.dumps(row["radios"])[:400])
        print("AFTER ADD ROW inputs:", json.dumps([i for i in row["inputs"] if 'qty' in str(i).lower() or 'size' in str(i).lower()])[:400])

        # drive quantity
        inp = page.locator(".shirt-qty-input").first
        if await inp.count():
            await inp.click(); await inp.press("Control+A"); await inp.press("Delete")
            await inp.type("50", delay=60); await inp.press("Tab")
            await page.wait_for_timeout(4000)
        else:
            print("NO .shirt-qty-input found")
        await b.close()

asyncio.run(run(sys.argv[1] if len(sys.argv) > 1 else "dtf-shirt"))
