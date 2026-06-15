"""Probe the Label Sticker 'CD' type on the www Digital order page: dump every visible
control + its options when rdType=CD is selected.

  python -m app.cd_sticker_probe [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .sticker_capture import DIGITAL, _wait, _radio_startswith

OUT = Path(__file__).resolve().parent.parent / "output"


async def run(account_id=1):
    a = accounts.get(account_id)
    res = {}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        await page.goto(DIGITAL, wait_until="domcontentloaded"); await _wait(page)
        await _radio_startswith(page, "rdType", "CD"); await asyncio.sleep(1.5); await _wait(page)

        selects = await page.evaluate("""() => [...document.querySelectorAll('select')]
            .filter(s=>s.offsetParent).map(s=>({name:s.name.split('$').pop(),
            options:[...s.options].map(o=>o.text.trim()).filter(Boolean)}))""")
        radios = await page.evaluate("""() => { const g={}; for(const r of document.querySelectorAll('input[type=radio]')){
            if(!r.offsetParent) continue; const n=r.name.split('$').pop(); (g[n]=g[n]||[]).push(r.value);} return g; }""")
        texts = await page.evaluate("""() => [...document.querySelectorAll('input[type=text]')]
            .filter(t=>t.offsetParent).map(t=>t.name.split('$').pop())""")
        res = {"selects": selects, "radios": radios, "text_inputs": texts}
        OUT.joinpath("cd_sticker_probe.json").write_text(json.dumps(res, indent=1))
        print("=== radios ==="); [print(f"  {k}: {v}") for k, v in radios.items()]
        print("=== text inputs ===", texts)
        print("=== selects ===")
        for s in selects:
            print(f"  {s['name']}: {s['options'][:18]}")
        try: await b.close()
        except Exception: pass


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
