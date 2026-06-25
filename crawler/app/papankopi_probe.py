"""Probe Papan Kopi form to understand why price doesn't show.
  python -m app.papankopi_probe [account]
"""
from __future__ import annotations
import asyncio, sys
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .billbook_sampler import _wait, _overlay_gone

URL = "https://www.excard.com.my/spec/Litho/Papan_Kopi"


async def _direct_price(page, label=""):
    await _overlay_gone(page)
    await asyncio.sleep(0.5)
    txt = await page.evaluate("() => document.body.innerText")
    lines = [l.strip() for l in txt.split('\n') if l.strip() and
             any(k in l.upper() for k in ['RM', 'PRICE', 'DISCOUNT', 'NETT', 'TOTAL', 'AMOUNT'])]
    print(f"  [{label}] price text: {lines[:8]}")


async def run(account_id=1):
    a = accounts.get(account_id)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(2.0)
        print("\n=== PAPAN KOPI PROBE ===")

        # Dump all fields on initial load
        fields = await page.evaluate("""() => {
            const out = {sel: {}, radio: {}};
            document.querySelectorAll('select').forEach(s => {
                if (!s.name.match(/country|state|courier|other/i))
                    out.sel[s.name] = Array.from(s.options).map(o=>o.text.trim()).filter(t=>t&&!t.startsWith('-')).slice(0,8);
            });
            document.querySelectorAll('input[type=radio]').forEach(r => {
                if (r.name && !r.name.match(/country|state|courier|other/i)) {
                    if (!out.radio[r.name]) out.radio[r.name]=[];
                    out.radio[r.name].push(r.value);
                }
            });
            return out;
        }""")
        print("Initial fields:", fields)

        # Select first available size
        size_opts = fields['sel'].get(next((k for k in fields['sel'] if 'size' in k.lower() or 'ddlSize' in k), ''), [])
        size_key = next((k for k in fields['sel'] if 'size' in k.lower()), None)
        print(f"\nSize field: {size_key} → {size_opts[:4]}")

        if not size_key:
            print("ERROR: No size field found!")
        else:
            size = size_opts[0]
            await page.select_option(f"select[name$='{size_key.split('_')[-1]}']", label=size)
            await _wait(page); await asyncio.sleep(2.0)

            # Check what changed after size selection
            fields2 = await page.evaluate("""() => {
                const out = {sel: {}, radio: {}};
                document.querySelectorAll('select').forEach(s => {
                    if (!s.name.match(/country|state|courier|other/i))
                        out.sel[s.name] = Array.from(s.options).map(o=>o.text.trim()).filter(t=>t&&!t.startsWith('-')).slice(0,8);
                });
                document.querySelectorAll('input[type=radio]').forEach(r => {
                    if (r.name && !r.name.match(/country|state|courier|other/i)) {
                        if (!out.radio[r.name]) out.radio[r.name]=[];
                        out.radio[r.name].push(r.value);
                    }
                });
                return out;
            }""")
            print(f"\nAfter size={size}:")
            for k, v in fields2['sel'].items():
                print(f"  sel {k}: {v[:6]}")
            for k, v in fields2['radio'].items():
                print(f"  radio {k}: {v[:4]}")
            await _direct_price(page, f"after size={size}")

            # Try selecting first qty
            qty_opts = fields2['sel'].get(next((k for k in fields2['sel'] if 'qty' in k.lower()), ''), [])
            qty_key = next((k for k in fields2['sel'] if 'qty' in k.lower()), None)
            print(f"\nQty field: {qty_key} → {qty_opts[:6]}")

            if qty_opts and qty_key:
                q = qty_opts[0]
                await page.select_option(f"select[name$='{qty_key.split('_')[-1]}']", label=q)
                await _wait(page); await asyncio.sleep(3.0)
                print(f"\nAfter qty={q} (NO delivery toggle):")
                await _direct_price(page, f"after qty={q}")

                # Try delivery toggle
                print("\n-- Delivery toggle test --")
                await page.locator("input[name$='rblOrderCountryCode'][value='99']").first.check()
                await asyncio.sleep(3.0)
                await _direct_price(page, "after del=99")
                await page.locator("input[name$='rblOrderCountryCode'][value='98']").first.check()
                await asyncio.sleep(3.0)
                await _direct_price(page, "after del=98")

        try: await b.close()
        except Exception: pass


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
