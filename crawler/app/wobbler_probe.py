"""Probe Wobbler form to see what price text appears without delivery toggle.
Also discovers actual field names and cascade behavior.
  python -m app.wobbler_probe [account]
"""
from __future__ import annotations
import asyncio, sys
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .billbook_sampler import _wait, _overlay_gone

URL = "https://www.excard.com.my/spec/Digital/Wobbler"


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
        print("\n=== WOBBLER PROBE ===")

        fields = await page.evaluate("""() => {
            const out = {sel: {}, radio: {}};
            document.querySelectorAll('select').forEach(s => {
                if (!s.name.match(/country|state|courier|other/i))
                    out.sel[s.name] = Array.from(s.options).map(o=>o.text.trim()).filter(t=>t&&!t.startsWith('-')).slice(0,6);
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

        # Step through cascade
        # Orient
        orient_sel = fields['sel'].get(next((k for k in fields['sel'] if 'mould' in k.lower() or 'orient' in k.lower()), ''), [])
        orient_key = next((k for k in fields['sel'] if 'mould' in k.lower() or 'orient' in k.lower()), None)
        print(f"\nOrient field: {orient_key} → {fields['sel'].get(orient_key, [][:3])}")
        if orient_key:
            opts = fields['sel'][orient_key]
            await page.select_option(f"select[name$='{orient_key.split('_')[-1] if '_' in orient_key else orient_key}']", label=opts[0])
            await _wait(page); await asyncio.sleep(2.0)

        # Paper
        paper_opts = await page.evaluate("""() => {
            const s = document.querySelector('select[name$="ddlPaper"]');
            return s ? Array.from(s.options).map(o=>o.text.trim()).filter(t=>t&&!t.startsWith('-')) : [];
        }""")
        print(f"\nddlPaper options: {paper_opts}")
        if paper_opts:
            await page.select_option("select[name$='ddlPaper']", label=paper_opts[0])
            await _wait(page); await asyncio.sleep(2.0)
            await _direct_price(page, f"after paper={paper_opts[0]}")

        # Lam
        lam_opts = await page.evaluate("""() => {
            const s = document.querySelector('select[name$="rblLaminationSide"]') ||
                      document.querySelector('select[name*="lam" i]');
            return s ? Array.from(s.options).map(o=>o.text.trim()).filter(t=>t&&!t.startsWith('-')) : [];
        }""")
        print(f"\nLam options: {lam_opts}")
        if lam_opts:
            sel = await page.evaluate("""() => {
                const s = document.querySelector('select[name$="rblLaminationSide"]') ||
                          document.querySelector('select[name*="lam" i]');
                return s ? s.name : null;
            }""")
            await page.select_option(f"select[name$='{sel.split('_')[-1]}']", label=lam_opts[0])
            await _wait(page); await asyncio.sleep(2.0)
            await _direct_price(page, f"after lam={lam_opts[0]}")

        # Qty
        qty_opts = await page.evaluate("""() => {
            const s = document.querySelector('select[name$="comboQty"]');
            return s ? Array.from(s.options).map(o=>o.text.trim()).filter(t=>t&&!t.startsWith('-')).slice(0,8) : [];
        }""")
        print(f"\ncomboQty options: {qty_opts}")
        if qty_opts:
            await page.select_option("select[name$='comboQty']", label=qty_opts[0])
            await _wait(page); await asyncio.sleep(3.0)
            await _direct_price(page, f"after qty={qty_opts[0]} (NO delivery toggle)")

            # Now try delivery toggle
            print("\n-- Delivery toggle test --")
            await page.locator("input[name$='rblOrderCountryCode'][value='99']").first.check()
            await asyncio.sleep(2.0)
            await _direct_price(page, "after del=99")
            await page.locator("input[name$='rblOrderCountryCode'][value='98']").first.check()
            await asyncio.sleep(2.0)
            await _direct_price(page, "after del=98")

        try: await b.close()
        except Exception: pass


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
