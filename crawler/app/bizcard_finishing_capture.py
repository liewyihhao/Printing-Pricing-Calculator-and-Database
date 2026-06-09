"""Capture business-card FINISHING -> exact CheckPrice spec values + price deltas,
by driving the v4 form (which enforces the real constraints). Saves
output/bizcard_finishing_capture.json: [{finishing, control, label, payload, price}].

    python -m app.bizcard_finishing_capture
"""
from __future__ import annotations
import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch
from . import accounts
from .bizcard_probe import v4_login, URL
from .bizcard_api_probe import set_select

OUT = Path(__file__).resolve().parent.parent / "output"


async def main():
    a = accounts.get(1)
    latest = {}
    rows = []
    async with async_playwright() as pw:
        b = await launch(pw)
        ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page()

        async def on_resp(resp):
            if "CheckPrice" in resp.url:
                try:
                    latest["payload"] = json.loads(resp.request.post_data)["spec"][0]
                    latest["resp"] = await resp.json()
                except Exception:
                    pass
        page.on("response", on_resp)
        await v4_login(page, a)
        await page.goto(URL, wait_until="domcontentloaded")
        await asyncio.sleep(2)

        async def opts(name):
            sel = f"select[name='{name}'], select#{name}"
            if not await page.locator(sel).count():
                return []
            return await page.locator(sel).first.evaluate(
                "el=>[...el.options].map(o=>o.text.trim()).filter(t=>t&&!t.startsWith('--'))")

        async def trigger():
            try:
                await page.evaluate("""()=>{ if(window.jQuery)['cardLamination','quantity','silkscreenSpotUV','hotStampingEnable','embossing'].forEach(n=>jQuery("select[name='"+n+"'],#"+n).trigger('change')); }""")
            except Exception:
                pass
            await asyncio.sleep(1.4)

        async def base():
            await page.locator("input[name='cardType'][value='standard']").first.check(); await asyncio.sleep(0.8)
            await set_select(page, "cardSize", "54mm × 89mm")
            await set_select(page, "paperType", "Gloss Art Card 250gsm")
            await set_select(page, "printColour", "4C (Both)")
            await set_select(page, "cardLamination", "Gloss Water Based Varnish")
            await set_select(page, "quantity", "1,000")
            await trigger()

        def rec(fin, ctrl, label):
            rows.append({"finishing": fin, "control": ctrl, "label": label,
                         "payload": dict(latest.get("payload", {})),
                         "price": latest.get("resp", {}).get("Price")})

        await base(); rec("BASE", "—", "base")

        # Lamination
        for lab in await opts("cardLamination"):
            await base(); await set_select(page, "cardLamination", lab); await trigger()
            rec("lamination", "cardLamination", lab)
        # Spot UV (needs Matte Lamination Both)
        await base(); await set_select(page, "cardLamination", "Matte Lamination"); await trigger()
        for lab in await opts("silkscreenSpotUV"):
            await set_select(page, "silkscreenSpotUV", lab); await trigger()
            rec("spot_uv", "silkscreenSpotUV", lab)
        # Hot stamping
        for lab in await opts("hotStampingEnable"):
            await base(); await set_select(page, "hotStampingEnable", lab); await trigger()
            # set a colour if a colour radio is visible
            try:
                loc = page.locator("input[name='hotStampingFrontColour1'][value='gold']").first
                if await loc.count(): await loc.check(); await trigger()
            except Exception: pass
            rec("hot_stamping", "hotStampingEnable", lab)
        # Embossing
        for lab in await opts("embossing"):
            await base(); await set_select(page, "embossing", lab); await trigger()
            rec("embossing", "embossing", lab)
        # Round corner
        await base()
        try:
            await page.locator("input[name='roundCornerEnable'][value='required']").first.check(); await trigger()
            rec("round_corner", "roundCornerEnable", "required")
        except Exception: pass
        # Hole punching
        for val in ("3mm", "5mm"):
            await base()
            try:
                await page.locator(f"input[name='holePunching'][value='{val}']").first.check(); await trigger()
                rec("hole_punch", "holePunching", val)
            except Exception: pass

        await b.close()
    OUT.joinpath("bizcard_finishing_capture.json").write_text(json.dumps(rows, indent=1))
    print(f"captured {len(rows)} finishing rows")
    base_price = next((float(r["price"]) for r in rows if r["finishing"] == "BASE" and r["price"]), None)
    for r in rows:
        p = r["price"]; d = (float(p) - base_price) if (p and base_price) else None
        pay = r["payload"]
        keyf = {k: pay[k] for k in ("Lamination", "HotStamping", "HotStampingColour",
                "Embossing", "RoundCorner", "HolePunch", "SpotUV", "SilkscreenSpotUV")
                if k in pay and pay[k]}
        print(f"  {r['finishing']:13s} {r['label'][:34]:34s} price={p} d={None if d is None else round(d,2)}  {keyf}")


if __name__ == "__main__":
    asyncio.run(main())
