"""Parity audit — dump EVERY control + options on a live Excard order page (after
configuring the cascade so finishing sections are revealed), incl. detailed sub-options
(emboss size, hot-stamp size/colours) and 'Compulsory Finishing' text.

  python -m app.parity_formdump booklet37 [account]
  python -m app.parity_formdump booklet19 | loose50 | loose21 | sticker60 | sticker61
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts

OUT = Path(__file__).resolve().parent.parent / "output"


async def _dump_all(page):
    selects = await page.evaluate(r"""() => [...document.querySelectorAll('select')].map(s=>({
        name:s.name.split('$').pop(), visible:!!s.offsetParent,
        options:[...s.options].map(o=>o.text.trim()).filter(Boolean)})).filter(s=>s.visible)""")
    radios = await page.evaluate(r"""() => { const g={}; for(const r of document.querySelectorAll('input[type=radio]')){
        if(!r.offsetParent) continue; const n=r.name.split('$').pop(); (g[n]=g[n]||[]).push(r.value);} return g; }""")
    checks = await page.evaluate(r"""() => [...document.querySelectorAll('input[type=checkbox]')].filter(c=>c.offsetParent)
        .map(c=>c.name.split('$').pop())""")
    texts = await page.evaluate(r"""() => [...document.querySelectorAll('input[type=text]')].filter(t=>t.offsetParent)
        .map(t=>t.name.split('$').pop())""")
    sections = await page.evaluate(r"""() => { const b=document.body.innerText;
        const m=b.match(/(compulsory finishing|finishing|lamination|emboss|hot stamp|spot uv|creasing|saddle stitch|folding|perforat|round corner|hole punch|varnish)[^\n]{0,80}/gi);
        return m? [...new Set(m)].slice(0,40):[]; }""")
    return {"selects": selects, "radios": radios, "checkboxes": checks, "text_inputs": texts, "sections": sections}


async def booklet(page, method):
    from .booklet_capture import configure_booklet, BookletSpec
    url = f"https://www.excard.com.my/spec/{method}/Booklet"
    spec = BookletSpec(product_id=(37 if method == "Digital" else 19), spec_url=url,
                       orientation="Portrait", size="A4 (210mm x 297mm)",
                       ordertype="Soft Cover", binding="Saddle Stitch", page="16",
                       cover_paper="Gloss Art Card 250gsm (2 sides coated)", cover_colour="4C",
                       content_paper="Simili 80gsm", content_colour="4C (Both)")
    ok = await configure_booklet(page, spec)
    await asyncio.sleep(1.0)
    return ok


async def simple(page, url, setup_js=None):
    await page.goto(url, wait_until="domcontentloaded")
    try: await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception: pass
    await asyncio.sleep(2.0)


PRODUCTS = {
    "booklet37": ("Digital booklet", lambda p: booklet(p, "Digital")),
    "booklet19": ("Litho booklet", lambda p: booklet(p, "Litho")),
    "loose50": ("Digital loose", lambda p: simple(p, "https://www.excard.com.my/spec/Digital/Loose_Sheet")),
    "loose21": ("Litho loose", lambda p: simple(p, "https://www.excard.com.my/spec/Litho/Loose_Sheet")),
    "sticker60": ("Digital sticker", lambda p: simple(p, "https://www.excard.com.my/spec/Digital/Label_Sticker")),
    "sticker61": ("Letterpress sticker", lambda p: simple(p, "https://www.excard.com.my/spec/Letterpress/Label_Sticker_with_Hot_Stamping")),
}


async def run(key, account_id=1):
    a = accounts.get(account_id)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1500})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        name, fn = PRODUCTS[key]
        try:
            await fn(page)
        except Exception as e:  # noqa: BLE001 — partial config still reveals finishing
            print("config warn:", str(e)[:80])
        await asyncio.sleep(1.0)
        dump = await _dump_all(page)
        OUT.joinpath(f"parity_{key}.json").write_text(json.dumps(dump, indent=1))
        print(f"=== {key} ({name}) ===")
        print("SECTIONS:", dump["sections"])
        print("SELECTS:")
        for s in dump["selects"]:
            print(f"  {s['name']}: {s['options'][:14]}")
        print("RADIOS:", {k: v for k, v in dump["radios"].items()})
        print("TEXT INPUTS:", dump["text_inputs"])
        try: await b.close()
        except Exception: pass


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else "booklet37"
    acct = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    asyncio.run(run(key, acct))
