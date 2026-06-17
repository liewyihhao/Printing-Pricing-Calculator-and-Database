"""Find the live antiforgery token post-login + confirm an in-page price fetch works.
  python -m app.packaging_token_probe [account]
"""
from __future__ import annotations
import asyncio, sys, json
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts

DIY = "https://packaging.excard.com.my/uc/diy/A001X"


async def run(account_id=1):
    a = accounts.get(account_id)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1200})
        page = await ctx.new_page()
        try: await login(page, username=a.username, password=a.password)
        except Exception as e: print("login warn:", e)
        await page.goto(DIY, wait_until="domcontentloaded")
        try: await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception: pass
        await asyncio.sleep(6)

        tok = await page.evaluate(r"""() => {
          const out={};
          const inp=document.querySelector('input[name=__RequestVerificationToken]');
          out.hidden = inp ? inp.value : null;
          try { out.cmcache = (window.Cm && Cm.Cache && Cm.Cache.get) ? Cm.Cache.get('__RequestVerificationToken') : null; } catch(e){ out.cmcache='err'; }
          out.globalReqToken = window.reqToken || null;
          return out;
        }""")
        print("token sources:", json.dumps(tok))

        # try an in-page price fetch (the site attaches the token via its own ajax wrapper;
        # here we POST directly with the token we found)
        token = tok.get("hidden") or tok.get("cmcache") or tok.get("globalReqToken") or ""
        res = await page.evaluate(r"""async (token) => {
          const boxDiys = JSON.stringify([{BoxID:"A001X",IsJP:0,diyIdx:1,
            BoxPms:"CHOOSE=3,L=120,W=100,D=200,CAL=0.3",Qtys:[300],
            ProcessJson:JSON.stringify([{ID:"P001",Pms:[4,0,0,0,0],Materials:[{MID:"M0024",SerialNo:1,Pms:[]}]},{ID:"P021"},{ID:"P051"},{ID:"P066"}])}]);
          const body = new URLSearchParams({boxDiys, __RequestVerificationToken: token, __IP:"", __IP_Isp:""});
          const r = await fetch("/uc/GetPriceFactor2", {method:"POST", headers:{"Content-Type":"application/x-www-form-urlencoded","X-Requested-With":"XMLHttpRequest"}, body});
          const t = await r.text();
          return {status:r.status, body:t.slice(0,400)};
        }""", token)
        print("in-page price fetch:", json.dumps(res))
        try: await b.close()
        except Exception: pass


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
