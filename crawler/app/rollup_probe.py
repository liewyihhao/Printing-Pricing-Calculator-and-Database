"""Probe Roll-Up Stand form to discover correct field names and values.
  python -m app.rollup_probe [account]
"""
from __future__ import annotations
import asyncio, sys
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .logging_setup import log
from .billbook_sampler import _wait

URL = "https://www.excard.com.my/spec/Litho/Roll_Up_Stand"


async def _dump_all_fields(page, label=""):
    result = await page.evaluate("""() => {
        const out = {selects: {}, radios: {}, text: {}};
        document.querySelectorAll('select').forEach(s => {
            const nm = s.name || s.id || '?';
            if (!nm.match(/country|state|courier|other/i))
                out.selects[nm] = Array.from(s.options).map(o => o.text.trim()).filter(t => t && !t.startsWith('-'));
        });
        document.querySelectorAll('input[type=radio]').forEach(r => {
            const nm = r.name || '?';
            if (!nm.match(/country|state|courier|other/i)) {
                if (!out.radios[nm]) out.radios[nm] = [];
                out.radios[nm].push(r.value);
            }
        });
        return out;
    }""")
    print(f"\n=== {label} ===")
    for k, v in result['selects'].items():
        print(f"  SELECT {k}: {v[:8]}")
    for k, v in result['radios'].items():
        print(f"  RADIO  {k}: {v}")


async def run(account_id=1):
    a = accounts.get(account_id)
    async with async_playwright() as pw:
        b = await launch(pw)
        ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page()
        await login(page, username=a.username, password=a.password)
        await page.goto(URL, wait_until="domcontentloaded")
        await _wait(page); await asyncio.sleep(2.0)
        await _dump_all_fields(page, "Initial page load (Roll-Up Stand)")
        # Try selecting the first lam option
        lam_opts = await page.evaluate("""() => {
            const s = document.querySelector('select[name$="rblLaminationSide"]') ||
                      document.querySelector('select[name$="ddlLamination"]') ||
                      document.querySelector('select[name*="lam" i]');
            if (!s) return ['NO_LAM_SELECT'];
            return Array.from(s.options).map(o => o.text.trim()).filter(t => t && !t.startsWith('-'));
        }""")
        print(f"\nLamination options found: {lam_opts}")
        # Also check full page text for any price indicators
        txt = await page.evaluate("()=>document.body.innerText")
        price_lines = [l.strip() for l in txt.split('\n') if l.strip() and any(k in l.upper() for k in ['RM','PRICE','LAM','STAND','ROLL'])]
        print(f"Price-related text: {price_lines[:15]}")
        try: await b.close()
        except Exception: pass


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
