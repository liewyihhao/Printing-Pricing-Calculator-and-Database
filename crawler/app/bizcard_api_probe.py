"""Capture a real Product/CheckPrice request+response for the v4 business-card
form, to learn the exact pricing-API payload (so we can call it directly).

    python -m app.bizcard_api_probe
"""
from __future__ import annotations
import asyncio, json
from playwright.async_api import async_playwright
from .browser import launch
from . import accounts
from .bizcard_probe import v4_login, URL


async def set_select(page, name, label_contains):
    sel = f"select[name='{name}'], select#{name}"
    try:
        await page.locator(sel).first.select_option(label=label_contains)
        return True
    except Exception:
        # try by value/partial
        try:
            opts = await page.locator(sel).first.evaluate(
                "el=>[...el.options].map(o=>o.text)")
            for o in opts:
                if label_contains.lower() in o.lower():
                    await page.locator(sel).first.select_option(label=o)
                    return True
        except Exception:
            pass
    return False


async def main():
    a = accounts.get(1)
    captured = []
    async with async_playwright() as pw:
        b = await launch(pw)
        ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page()

        async def on_resp(resp):
            if "CheckPrice" in resp.url:
                try:
                    body = resp.request.post_data
                    rj = await resp.json()
                    captured.append({"payload": body, "response": rj})
                except Exception as e:
                    captured.append({"err": repr(e)[:120]})
        page.on("response", on_resp)
        # The price fn logs JSON.stringify(jData) — capture it from the console.
        page.on("console", lambda m: captured.append({"console": m.text})
                if m.text.strip().startswith("{") else None)

        await v4_login(page, a)
        await page.goto(URL, wait_until="domcontentloaded")
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        await asyncio.sleep(2)
        # Configure a simple valid Standard card combo.
        await page.locator("input[name='cardType'][value='standard']").first.check()
        await asyncio.sleep(1)
        await set_select(page, "cardSize", "54mm × 89mm")
        await asyncio.sleep(0.5)
        await page.locator("input[name='orientation'][value='landscape']").first.check()
        await asyncio.sleep(0.5)
        await set_select(page, "paperType", "Gloss Art Card 250gsm")
        await asyncio.sleep(0.5)
        await set_select(page, "printColour", "4C (Both)")
        await asyncio.sleep(0.5)
        await set_select(page, "cardLamination", "Gloss Water Based Varnish")
        await asyncio.sleep(0.5)
        await set_select(page, "quantity", "300")
        await asyncio.sleep(1)
        # Force the change handlers / price calc via jQuery triggers.
        try:
            await page.evaluate("""() => {
                if (window.jQuery) {
                    ['cardLamination','paperType','printColour','quantity'].forEach(n=>{
                        jQuery("select[name='"+n+"'],#"+n).trigger('change');
                    });
                }
            }""")
        except Exception as e:
            print("trigger note:", repr(e)[:80])
        await asyncio.sleep(4)  # let get-price fire
        # Read on-page price too
        price = await page.evaluate(
            "()=>document.getElementById('tdPriceb4Disc1Main')?.innerText||''")
        print("ON-PAGE PRICE BEFORE DISCOUNT:", price)
        import pathlib
        pathlib.Path("output/bizcard_checkprice_capture.json").write_text(
            json.dumps(captured, indent=1, default=str))
        pays = [c for c in captured if "payload" in c]
        print(f"\n=== {len(pays)} CheckPrice payloads (of {len(captured)} events) ===")
        for c in pays[-2:]:
            if "payload" in c:
                print("\nPAYLOAD:")
                try:
                    print(json.dumps(json.loads(c["payload"]), indent=1)[:2500])
                except Exception:
                    print(c["payload"][:2000])
                print("\nRESPONSE (keys):")
                r = c["response"]
                r = r.get("d", r) if isinstance(r, dict) else r
                if isinstance(r, str):
                    try: r = json.loads(r)
                    except Exception: pass
                print(json.dumps(r, indent=1)[:1500] if not isinstance(r, str) else r[:1500])
            else:
                print(c)
        await b.close()


if __name__ == "__main__":
    asyncio.run(main())
