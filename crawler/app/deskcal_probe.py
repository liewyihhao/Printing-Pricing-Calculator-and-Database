"""One-off probe: Desk Calendar (Hard/Soft Stand) — identify rdCategory labels and how
price moves over category x qty. Prints findings; writes nothing permanent.

  python -m app.deskcal_probe ["Hard"|"Soft"]
"""
from __future__ import annotations
import asyncio, sys
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .billbook_sampler import _sel, _safe_read, _wait, _radio

STAND = sys.argv[1] if len(sys.argv) > 1 else "Hard"
URL = f"https://www.excard.com.my/spec/Litho/Desk_Calendar_({STAND}_Stand)"
QTYS = [10, 50, 100, 500, 1000]


async def _radio_labels(page, name):
    """Return [(value, label)] for radio group name$=name (label = nearest text)."""
    return await page.evaluate(
        """(name)=>{const out=[];document.querySelectorAll(`input[name$='${name}']`).forEach(el=>{
            let lab='';const id=el.id;
            if(id){const l=document.querySelector(`label[for='${id}']`);if(l)lab=l.innerText.trim();}
            if(!lab&&el.parentElement)lab=el.parentElement.innerText.trim();
            out.push([el.value,lab]);});return out;}""", name)


async def run(account_id=1):
    a = accounts.get(account_id)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1500})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(1.5)
        labels = await _radio_labels(page, "rdCategory")
        print(f"=== Desk Calendar ({STAND} Stand) rdCategory ===")
        for v, l in labels:
            print(f"  value={v!r} label={l!r}")
        for v, l in labels:
            if not await _radio(page, "rdCategory", v):
                print(f"  [cfg_fail] {v}"); continue
            await asyncio.sleep(0.6)
            row = []
            for q in QTYS:
                if await _sel(page, "comboQty", str(q)):
                    await asyncio.sleep(0.8)
                    row.append((q, (await _safe_read(page)).get("before_discount")))
            print(f"  cat {v} ({l[:30]}): {row}")
        try: await b.close()
        except Exception: pass


if __name__ == "__main__":
    asyncio.run(run())
