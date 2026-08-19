import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright
from app import browser as B
from app.readymade_enum import login_v4

OUT=Path(__file__).resolve().parent.parent/"output"/"loose_form_map.json"
_OPTS=r"""(rx)=>{const R=new RegExp(rx,'i');const vis=e=>e&&e.offsetParent!==null;
 for(const s of document.querySelectorAll('select')){if(!vis(s))continue;const g=s.closest('.form-group,.row,.mb-3,.field')||s.parentElement;const le=g&&g.querySelector('label,.control-label,b,h5,h6');const lab=le?le.textContent.trim():(s.name||'');
 if(R.test(lab)||R.test(s.name||''))return[...s.options].map(o=>o.text.trim()).filter(t=>t&&!/^--|select/i.test(t));}return null;}"""
_SET=r"""(a)=>{const[rx,val]=a;const R=new RegExp(rx,'i');for(const s of document.querySelectorAll('select')){if(s.offsetParent===null)continue;const g=s.closest('.form-group,.row,.mb-3,.field')||s.parentElement;const le=g&&g.querySelector('label,.control-label,b,h5,h6');const lab=le?le.textContent.trim():(s.name||'');
 if(R.test(lab)||R.test(s.name||'')){const i=[...s.options].findIndex(o=>o.text.trim()===val);if(i>=0){s.selectedIndex=i;s.dispatchEvent(new Event('input',{bubbles:true}));s.dispatchEvent(new Event('change',{bubbles:true}));return true;}}}return false;}"""
async def cur(page,rx):
    return await page.evaluate(r"""(rx)=>{const R=new RegExp(rx,'i');for(const s of document.querySelectorAll('select')){if(s.offsetParent===null)continue;const g=s.closest('.form-group,.row,.mb-3,.field')||s.parentElement;const le=g&&g.querySelector('label,.control-label,b,h5,h6');const lab=le?le.textContent.trim():(s.name||'');if(R.test(lab)||R.test(s.name||'')){const o=s.options[s.selectedIndex];return o?o.text.trim():'';}}return null;}""",rx)
async def setv(page,rx,val):
    for _ in range(3):
        await page.evaluate(_SET,[rx,val]); await page.wait_for_timeout(1200)
        if (await cur(page,rx))==val: return True
    return False
async def main(slug):
    async with async_playwright() as pw:
        b=await B.launch(pw); page=await b.new_page(viewport={"width":1400,"height":2400})
        await login_v4(page)
        await page.goto("https://v4.excard.com.my/ordering/"+slug,wait_until="domcontentloaded",timeout=60000)
        await page.wait_for_timeout(6000)
        sizes=await page.evaluate(_OPTS,"^Size")
        m={}
        for sz in sizes:
            if not await setv(page,"^Size",sz): 
                print("  ! size set fail",sz); continue
            await page.wait_for_timeout(600)
            papers=await page.evaluate(_OPTS,"^Paper \*|paper type|paper$")
            m[sz]={"papers":papers,"by_paper":{}}
            for pp in (papers or []):
                if not await setv(page,"^Paper \*|paper type|paper$",pp): continue
                await page.wait_for_timeout(500)
                col=await page.evaluate(_OPTS,"print colour|^colour")
                lam=await page.evaluate(_OPTS,"lamination")
                m[sz]["by_paper"][pp]={"colour":col,"lamination":lam}
            print(f"{sz:26} papers={len(papers or [])}")
        OUT.write_text(json.dumps(m,indent=1,ensure_ascii=False),encoding="utf-8")
        print("wrote",OUT)
        await b.close()
import sys
asyncio.run(main(sys.argv[1] if len(sys.argv)>1 else "lo-loose-sheet"))
