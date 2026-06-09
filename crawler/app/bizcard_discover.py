"""Discover business-card options + the form-label -> API-value mapping.

Drives the v4 form (Playwright) just enough to (a) read each cardType's valid
option lists and (b) learn how the SPA maps a form label to the value it sends to
the CheckPrice API (e.g. "54mm × 89mm" -> "54mm x 89mm",
"Gloss Water Based Varnish (Both)(Free)" -> "Gloss Waterbase Varnish (Both)").
Output -> output/bizcard_options.json. Sampling then calls the API directly.

    python -m app.bizcard_discover
"""
from __future__ import annotations
import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch
from . import accounts
from .bizcard_probe import v4_login, URL

OUT = Path(__file__).resolve().parent.parent / "output"
CARDTYPES = {"standard": "Standard Card", "thin_fold": "Thin Fold",
             "fat_fold": "Fat Fold", "custom_die_cut": "Custom Die-Cut",
             "plastic_card": "Plastic Card"}


class Driver:
    def __init__(self, page):
        self.page = page
        self.latest = {}      # latest CheckPrice spec[0]
        self.latest_resp = {}
        page.on("response", self._on_resp)

    async def _on_resp(self, resp):
        if "CheckPrice" in resp.url:
            try:
                body = resp.request.post_data
                self.latest = json.loads(body)["spec"][0]
                self.latest_resp = await resp.json()
            except Exception:
                pass

    async def opts(self, name):
        sel = f"select[name='{name}'], select#{name}"
        if not await self.page.locator(sel).count():
            return []
        return await self.page.locator(sel).first.evaluate(
            "el=>[...el.options].map(o=>o.text.trim()).filter(t=>t && !t.startsWith('--'))")

    async def set_sel(self, name, label):
        sel = f"select[name='{name}'], select#{name}"
        loc = self.page.locator(sel).first
        if not await loc.count():
            return False
        try:
            await loc.select_option(label=label)
        except Exception:
            # partial match (e.g. quantity "300" -> "300 — Best Seller")
            try:
                full = await loc.evaluate(
                    "(el,l)=>{const o=[...el.options].find(o=>o.text.replace(/[, ]/g,'').includes(l.replace(/[, ]/g,'')));return o?o.text:null;}", label)
                if not full:
                    return False
                await loc.select_option(label=full)
            except Exception:
                return False
        await self._fire()
        return True

    async def set_radio(self, name, value):
        loc = self.page.locator(f"input[name='{name}'][value='{value}']").first
        if not await loc.count():
            return False
        await loc.check()
        await self._fire()
        return True

    async def _fire(self):
        try:
            await self.page.evaluate("""()=>{ if(window.jQuery){
                ['cardLamination','paperType','printColour','quantity','cardSize'].forEach(n=>
                  jQuery("select[name='"+n+"'],#"+n).trigger('change'));
            }}""")
        except Exception:
            pass
        await asyncio.sleep(1.3)

    def price(self):
        try:
            p = float(str(self.latest_resp.get("Price", "0")).replace(",", ""))
            return p if p > 0 else None
        except Exception:
            return None


async def discover():
    a = accounts.get(1)
    result = {"product": "Business Card", "cardTypes": {}, "value_maps": {
        "size": {}, "paper": {}, "lamination": {}, "hotStamping": {}, "embossing": {}},
        "finishing": {}}
    async with async_playwright() as pw:
        b = await launch(pw)
        ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page()
        d = Driver(page)
        await v4_login(page, a)
        await page.goto(URL, wait_until="domcontentloaded")
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        await asyncio.sleep(2)

        for ct_val, ct_label in CARDTYPES.items():
            if not await d.set_radio("cardType", ct_val):
                continue
            await asyncio.sleep(1)
            sizes = await d.opts("cardSize")
            papers = await d.opts("paperType")
            colours = await d.opts("printColour")
            lams = await d.opts("cardLamination")
            qtys = await d.opts("quantity")
            packages = await d.opts("package")
            entry = {"label": ct_label, "sizes": sizes, "papers": papers,
                     "colours": colours, "laminations": lams,
                     "qty": [q.split(" —")[0].replace(",", "") for q in qtys],
                     "packages": packages}
            result["cardTypes"][ct_val] = entry

            # Establish a valid baseline to make the API fire, then learn maps.
            if sizes and papers:
                await d.set_sel("cardSize", sizes[0])
                await d.set_sel("paperType", papers[0])
                if colours:
                    await d.set_sel("printColour", colours[0])
                # pick a lamination that yields a price
                for lam in lams:
                    await d.set_sel("cardLamination", lam)
                    await d.set_sel("quantity", "300")
                    if d.price():
                        break
                entry["OrderDesc"] = d.latest.get("OrderDesc")
                # size map
                for s in sizes:
                    if "Other" in s or "Custom" in s:
                        continue
                    await d.set_sel("cardSize", s)
                    if d.latest.get("Size"):
                        result["value_maps"]["size"][s] = d.latest["Size"]
                await d.set_sel("cardSize", sizes[0])
                # paper map (+ validity)
                for p in papers:
                    await d.set_sel("paperType", p)
                    await d.set_sel("quantity", "300")
                    if d.latest.get("Paper"):
                        result["value_maps"]["paper"][p] = d.latest["Paper"]
                await d.set_sel("paperType", papers[0])
                # lamination map
                for lam in lams:
                    await d.set_sel("cardLamination", lam)
                    if d.latest.get("Lamination") is not None:
                        result["value_maps"]["lamination"][lam] = d.latest["Lamination"]
            OUT.joinpath("bizcard_options.json").write_text(json.dumps(result, indent=1))
            print(f"  {ct_val}: sizes={len(sizes)} papers={len(papers)} lams={len(lams)} "
                  f"qty={len(qtys)} OrderDesc={entry.get('OrderDesc')!r}")

        # Finishing maps (under standard + Gloss Art Card 250).
        await d.set_radio("cardType", "standard")
        std = result["cardTypes"].get("standard", {})
        if std.get("sizes"):
            await d.set_sel("cardSize", std["sizes"][0])
            await d.set_sel("paperType", next((p for p in std["papers"] if "Gloss Art Card 250" in p), std["papers"][0]))
            await d.set_sel("quantity", "1,000")
            for hs in await d.opts("hotStampingEnable"):
                await d.set_sel("hotStampingEnable", hs)
                result["value_maps"]["hotStamping"][hs] = d.latest.get("HotStamping")
            await d.set_sel("hotStampingEnable", (await d.opts("hotStampingEnable"))[0])
            for em in await d.opts("embossing"):
                await d.set_sel("embossing", em)
                result["value_maps"]["embossing"][em] = d.latest.get("Embossing")
            result["finishing"]["roundCorner"] = ["no", "required"]
            result["finishing"]["holePunch"] = ["no", "3mm", "5mm"]
            result["finishing"]["spotUV_options"] = await d.opts("silkscreenSpotUV")
        OUT.joinpath("bizcard_options.json").write_text(json.dumps(result, indent=1))
        await b.close()
    print("wrote output/bizcard_options.json")


if __name__ == "__main__":
    asyncio.run(discover())
