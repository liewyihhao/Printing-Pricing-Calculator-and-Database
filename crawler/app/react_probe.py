"""Inspect the React calculator on /product/<slug>: dump clickable option groups and the
price element, so we can drive it headlessly."""
import asyncio, sys
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts

SLUG = sys.argv[1] if len(sys.argv) > 1 else "money-packet"


async def run():
    a = accounts.get(1)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 2200})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        await page.goto(f"https://www.excard.com.my/product/{SLUG}", wait_until="networkidle")
        await asyncio.sleep(5)
        for _ in range(4):
            await page.mouse.wheel(0, 800); await asyncio.sleep(1)
        # find the element showing the RM price + its container, and clickable option-ish els
        info = await page.evaluate(r"""()=>{
          const out={price_els:[], groups:[], inputs:[]};
          // price elements
          document.querySelectorAll('*').forEach(e=>{
            if(e.children.length===0){
              const t=(e.innerText||'').trim();
              if(/^RM\s?[\d,]+\.?\d*$/.test(t)) out.price_els.push({t, cls:e.className.toString().slice(0,40), id:e.id});
            }});
          // clickable options: buttons, [role=button], li, label, divs with cursor pointer + short text
          const seen=new Set();
          document.querySelectorAll("button,[role=button],label,li,a,div").forEach(e=>{
            if(!e.offsetParent) return;
            const t=(e.innerText||'').trim();
            if(!t || t.length>40 || e.children.length>2) return;
            const cs=getComputedStyle(e);
            if(cs.cursor!=='pointer') return;
            const key=t+'|'+e.tagName;
            if(seen.has(key)) return; seen.add(key);
            out.groups.push({tag:e.tagName, t, cls:e.className.toString().slice(0,30)});
          });
          document.querySelectorAll('input,select,textarea').forEach(e=>{
            if(e.offsetParent) out.inputs.push({tag:e.tagName, type:e.type||'', name:(e.name||e.id||'').slice(0,30), val:(e.value||'').slice(0,20)});
          });
          return out;}""")
        print("PRICE ELS:", info["price_els"][:8])
        print("INPUTS:", info["inputs"][:20])
        print(f"CLICKABLE OPTIONS ({len(info['groups'])}):")
        for g in info["groups"][:60]:
            print("  ", g["tag"], repr(g["t"]), g["cls"])
        await b.close()

asyncio.run(run())
