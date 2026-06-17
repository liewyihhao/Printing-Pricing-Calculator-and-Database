"""Probe the Bill-Book (Litho) order page: dump every control + options + any hidden
radios, plus the size/qty hint text. First step of the add-a-product workflow.

  python -m app.billbook_probe [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .browser import polite_pause

OUT = Path(__file__).resolve().parent.parent / "output"
URL = "https://www.excard.com.my/spec/Litho/Bill-Book"


async def _wait(page):
    try: await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception: pass
    await polite_pause()


async def run(account_id=1):
    a = accounts.get(account_id)
    res = {}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        await page.goto(URL, wait_until="domcontentloaded"); await _wait(page)
        await asyncio.sleep(1.5)

        # ALL selects (incl hidden), with name + options + visibility
        selects = await page.evaluate("""() => [...document.querySelectorAll('select')].map(s=>({
            name:s.name.split('$').pop(), visible:!!s.offsetParent,
            options:[...s.options].map(o=>o.text.trim()).filter(Boolean)}))""")
        # ALL radios grouped
        radios = await page.evaluate("""() => { const g={}; for(const r of document.querySelectorAll('input[type=radio]')){
            const n=r.name.split('$').pop(); (g[n]=g[n]||[]).push({value:r.value, vis:!!r.offsetParent});} return g; }""")
        # text/number inputs
        texts = await page.evaluate("""() => [...document.querySelectorAll('input[type=text],input:not([type])')]
            .map(t=>({name:t.name.split('$').pop(), vis:!!t.offsetParent}))""")
        # any min/max mm/page hints
        hints = await page.evaluate(r"""() => { const b=document.body.innerText;
            const m=b.match(/(min|max|minimum|maximum|ply|set|page|numbering|perforat|bind)[^\n]{0,70}/gi); return m?m.slice(0,25):[]; }""")
        res = {"selects": selects, "radios": radios, "texts": texts, "hints": hints}
        OUT.joinpath("billbook_probe.json").write_text(json.dumps(res, indent=1))

        print("=== RADIOS ==="); [print(f"  {k}: {[x['value'] for x in v]}") for k, v in radios.items()]
        print("=== TEXT/NUM INPUTS ===", [t["name"] for t in texts if t["name"]])
        print("=== SELECTS (visible) ===")
        for s in selects:
            if s["visible"]:
                print(f"  {s['name']}: {s['options'][:20]}")
        print("=== HINTS ==="); [print("  ", h) for h in res["hints"]]
        try: await b.close()
        except Exception: pass


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
