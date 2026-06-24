"""Generic diagnostic: open a /spec form, select the first real option of every
select + first radio of every group (twice, to settle ASP.NET postbacks and
re-apply fields that reset), then report the price and any still-empty required
controls. Tells us what each 'no price headless' product actually needs.

  python -m app.autoconfig_probe <path1> [path2 ...]
"""
from __future__ import annotations
import asyncio, sys
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .billbook_sampler import _safe_read, _wait

BASE = "https://www.excard.com.my"
SKIP = ("country", "courier", "comboqty", "ddlqty", "track", "review-filter", "product", "printmethod")


async def _controls(page):
    return await page.evaluate("""()=>{
      const out={selects:[],radios:{}};
      document.querySelectorAll('select').forEach(s=>{
        const n=(s.name||'').split('$').pop();
        const opts=[...s.options].map(o=>o.text.trim()).filter(t=>t&&!t.startsWith('-')&&t!=='Other');
        out.selects.push({n,val:s.value,opts});});
      document.querySelectorAll("input[type=radio]").forEach(r=>{
        const n=(r.name||'').split('$').pop();
        if(!r.offsetParent)return;
        (out.radios[n]=out.radios[n]||[]).push(r.value);});
      return out;}""")


async def _sel_by_text(page, name, text):
    try:
        await page.select_option(f"select[name$='{name}']", label=text, timeout=4000)
        return True
    except Exception:
        return False


async def _click_radio(page, name, value):
    try:
        loc = page.locator(f"input[name$='{name}'][value='{value}']")
        if await loc.count():
            await loc.first.check(timeout=4000); return True
    except Exception:
        pass
    return False


async def configure(page):
    """Two passes: select first real option of each meaningful select/radio."""
    for _ in range(2):
        c = await _controls(page)
        for r, vals in c["radios"].items():
            if any(k in r.lower() for k in SKIP) or not vals:
                continue
            await _click_radio(page, r, vals[0]); await asyncio.sleep(0.5)
        c = await _controls(page)
        for s in c["selects"]:
            if any(k in s["n"].lower() for k in SKIP) or not s["opts"]:
                continue
            await _sel_by_text(page, s["n"], s["opts"][0]); await asyncio.sleep(0.5)
        # set a qty if present
        await _sel_by_text(page, "comboQty", None) if False else None
        for qn in ("comboQty", "ddlQty"):
            try:
                opts = await page.locator(f"select[name$='{qn}']").first.evaluate(
                    "el=>[...el.options].map(o=>o.value).filter(v=>v&&!v.startsWith('-'))")
                if opts:
                    await page.select_option(f"select[name$='{qn}']", value=opts[len(opts)//2]); await asyncio.sleep(0.6)
            except Exception:
                pass
        await asyncio.sleep(0.8)


async def run(paths):
    a = accounts.get(1)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1600})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for path in paths:
            try:
                await page.goto(BASE + path, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(2.0)
                await configure(page)
                price = (await _safe_read(page)).get("before_discount")
                empty = await page.evaluate(
                    "()=>Array.from(document.querySelectorAll('select')).filter(s=>s.name&&!s.value&&[...s.options].length>1).map(s=>s.name.split('$').pop())")
                empty = [e for e in empty if not any(k in e.lower() for k in SKIP)]
                radios_empty = await page.evaluate(
                    "()=>{const seen={};document.querySelectorAll('input[type=radio]').forEach(r=>{if(!r.offsetParent)return;const n=r.name.split('$').pop();seen[n]=seen[n]||false;if(r.checked)seen[n]=true;});return Object.keys(seen).filter(k=>!seen[k]);}")
                radios_empty = [e for e in radios_empty if not any(k in e.lower() for k in SKIP)]
                print(f"=== {path}  PRICE={price}  empty_selects={empty}  unchecked_radios={radios_empty}")
            except Exception as e:  # noqa: BLE001
                print(f"=== {path}  ERROR {str(e)[:90]}")
        try: await b.close()
        except Exception: pass


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1:]))
