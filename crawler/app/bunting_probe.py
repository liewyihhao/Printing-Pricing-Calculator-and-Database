"""Probe Bunting form to understand price display. Tests:
1. Price appears directly after qty selection (no delivery toggle needed)
2. What text is on page after each step
  python -m app.bunting_probe [account]
"""
from __future__ import annotations
import asyncio, re, sys
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .billbook_sampler import _wait, _overlay_gone

URL = "https://www.excard.com.my/spec/Litho/Bunting"


async def _direct_price(page):
    """Read price WITHOUT delivery toggle — just reads innerText after overlay gone."""
    await _overlay_gone(page)
    await asyncio.sleep(0.5)
    txt = await page.evaluate("() => document.body.innerText")
    # Try all known patterns
    price_text = [l.strip() for l in txt.split('\n') if l.strip() and
                  any(k in l.upper() for k in ['RM', 'PRICE', 'DISCOUNT', 'NETT', 'TOTAL', 'AMOUNT'])]
    return price_text


async def run(account_id=1):
    a = accounts.get(account_id)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(2.0)
        print("\n=== BUNTING PROBE ===")

        # Dump initial selects
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

        # Step 1: Select size
        size = "2ft x 5ft"
        await page.select_option("select[name$='ddlSize']", label=size)
        await _wait(page); await asyncio.sleep(2.0)
        print(f"\nAfter size={size}:")
        papers = await page.evaluate("""() => {
            const s = document.querySelector('select[name$="ddlPaper"]');
            return s ? Array.from(s.options).map(o=>o.text.trim()).filter(t=>t&&!t.startsWith('-')) : [];
        }""")
        print(f"  ddlPaper options: {papers}")
        pt = await _direct_price(page)
        print(f"  Price text: {pt[:5]}")

        # Step 2: Select paper
        paper = papers[0] if papers else "Tarpaulin 300gsm"
        await page.select_option("select[name$='ddlPaper']", label=paper)
        await _wait(page); await asyncio.sleep(2.0)
        print(f"\nAfter paper={paper}:")
        qtys = await page.evaluate("""() => {
            const s = document.querySelector('select[name$="comboQty"]');
            return s ? Array.from(s.options).map(o=>o.text.trim()).filter(t=>t&&!t.startsWith('-')).slice(0,15) : [];
        }""")
        print(f"  comboQty options: {qtys}")
        pt = await _direct_price(page)
        print(f"  Price text: {pt[:5]}")

        # Step 3: Select first available qty
        if qtys:
            q = qtys[0]
            await page.select_option("select[name$='comboQty']", label=q)
            await _wait(page); await asyncio.sleep(3.0)
            print(f"\nAfter qty={q} (3s wait, no delivery toggle):")
            pt = await _direct_price(page)
            print(f"  Price text (RAW): {pt[:10]}")

            # Step 4: Now try delivery toggle
            print("\nNow clicking delivery 99 then 98:")
            await page.locator("input[name$='rblOrderCountryCode'][value='99']").first.check()
            await asyncio.sleep(2.0)
            pt1 = await _direct_price(page)
            print(f"  Price after del=99: {pt1[:5]}")

            await page.locator("input[name$='rblOrderCountryCode'][value='98']").first.check()
            await asyncio.sleep(2.0)
            pt2 = await _direct_price(page)
            print(f"  Price after del=98: {pt2[:5]}")

            # Step 5: Try 3rd qty to see if price appears differently
            if len(qtys) > 2:
                q2 = qtys[2]
                await page.select_option("select[name$='comboQty']", label=q2)
                await _wait(page); await asyncio.sleep(3.0)
                print(f"\nAfter qty={q2} (no delivery toggle, just direct read):")
                pt3 = await _direct_price(page)
                print(f"  Price text: {pt3[:10]}")

        try: await b.close()
        except Exception: pass


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
