"""Probe v4 ordering pages: login (correct selectors), visit each slug, dump control shape
and capture any CheckPrice XHR. Usage: python -m app.probe_v4_shape id-card dtf-shirt silkscreen-shirt
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
    ok = "visitor" not in page.url.lower()
    print("v4 login:", ok, page.url, file=sys.stderr)
    return ok


async def run(slugs):
    hold = {}
    async with async_playwright() as pw:
        b = await B.launch(pw)
        page = await b.new_page()

        async def on_resp(resp):
            if "CheckPrice" in resp.url:
                try:
                    hold["resp"] = await resp.json()
                    hold["req"] = resp.request.post_data_json
                except Exception as e:
                    hold["err"] = str(e)
        page.on("response", lambda r: asyncio.create_task(on_resp(r)))

        print("login:", await login_v4(page))
        for slug in slugs:
            print("\n##### ", slug)
            try:
                await page.goto(V4 + slug, wait_until="networkidle", timeout=40000)
            except Exception as e:
                print("  goto err", str(e)[:120]); continue
            await page.wait_for_timeout(2500)
            print("  url:", page.url, "title:", await page.title())
            info = await page.evaluate(r"""()=>{
              const out={selects:[],radios:{},buttons:[],qtyInputs:[]};
              document.querySelectorAll('select').forEach(s=>{if(!s.offsetParent)return;
                out.selects.push({id:s.id||s.name,opts:[...s.options].map(o=>o.text.trim()).filter(t=>t).slice(0,12)});});
              document.querySelectorAll("input[type=radio]").forEach(r=>{if(!r.offsetParent)return;
                (out.radios[r.name]=out.radios[r.name]||[]).push(r.value);});
              document.querySelectorAll("button,a.btn,input[type=button]").forEach(x=>{if(!x.offsetParent)return;
                const t=(x.innerText||x.value||'').trim(); if(t&&t.length<40)out.buttons.push({id:x.id,t});});
              document.querySelectorAll("input").forEach(i=>{if(!i.offsetParent)return;
                if(/qty|quantity/i.test(i.id+i.name+i.className))out.qtyInputs.push(i.id||i.name||i.className);});
              return out;}""")
            print("  SELECTS:", json.dumps(info["selects"])[:800])
            print("  RADIOS:", json.dumps(info["radios"])[:500])
            print("  QTYINPUTS:", info["qtyInputs"])
            print("  BUTTONS:", [x["t"] for x in info["buttons"]][:25])
        await b.close()

asyncio.run(run(sys.argv[1:] or ["id-card"]))
