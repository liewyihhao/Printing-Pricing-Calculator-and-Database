"""Recon for Label Sticker (www.excard.com.my) — two production methods:
  Digital:     /spec/Digital/Label_Sticker
  Letterpress: /spec/Letterpress/Label_Sticker_with_Hot_Stamping
Plus the artwork/options page /label-sticker?view=artwork.
Custom size (no standard sizes): customer types W×H mm within min/max, 1mm steps.

    python -m app.sticker_probe
"""
from __future__ import annotations
import asyncio
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts

PAGES = {
    "Digital": "https://www.excard.com.my/spec/Digital/Label_Sticker",
    "Letterpress": "https://www.excard.com.my/spec/Letterpress/Label_Sticker_with_Hot_Stamping",
}
ARTWORK = "https://www.excard.com.my/label-sticker?view=artwork"


async def dump(page, label):
    print(f"\n========== {label}: {page.url} ==========")
    print("TITLE:", await page.title())
    sels = await page.evaluate(
        "() => [...document.querySelectorAll('select')].map(s=>({"
        "name:(s.name||s.id), n:s.options.length,"
        "opts:[...s.options].map(o=>o.text.trim()).filter(t=>t).slice(0,40)}))")
    print("\n-- SELECT controls --")
    for s in sels:
        if s["opts"]:
            print(f"  [{s['name']}] ({s['n']}) -> {s['opts']}")
    radios = await page.evaluate(
        "() => { const g={}; for(const r of document.querySelectorAll('input[type=radio]'))"
        "{ const k=r.name||'(noname)'; (g[k]=g[k]||[]).push(r.value||r.id);} return g; }")
    print("\n-- RADIO groups --")
    for k, v in radios.items():
        print(f"  [{k}] -> {v[:30]}")
    texts = await page.evaluate(
        "() => [...document.querySelectorAll('input[type=text],input[type=number],input:not([type])')]"
        ".map(i=>({name:(i.name||i.id),ph:i.placeholder||'',val:i.value||''})).filter(i=>i.name)")
    print("\n-- TEXT/NUMBER inputs (size?) --")
    for t in texts[:40]:
        print(f"  [{t['name']}] ph={t['ph']!r} val={t['val']!r}")
    cbs = await page.evaluate(
        "() => [...document.querySelectorAll('input[type=checkbox]')].map(c=>c.name||c.id).filter(Boolean)")
    print("\n-- checkboxes --", cbs[:30])


async def main():
    a = accounts.get(1)
    async with async_playwright() as pw:
        b = await launch(pw)
        ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page()
        await login(page, username=a.username, password=a.password)
        for label, url in PAGES.items():
            await page.goto(url, wait_until="domcontentloaded")
            try: await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception: pass
            await asyncio.sleep(1.5)
            await dump(page, label)
        # artwork page: dump visible text (options/material descriptions)
        await page.goto(ARTWORK, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        txt = await page.evaluate("() => document.body.innerText")
        print("\n========== ARTWORK PAGE TEXT (first 3500) ==========")
        print(txt[:3500])
        await b.close()


if __name__ == "__main__":
    asyncio.run(main())
