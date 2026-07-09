"""Drive the Bill-Book ordering page with Paper Materials = Normal to enumerate the Normal
(non-carbonless) paper option tree: which layer counts and per-layer papers appear, and how
they differ from NCR. Read-only page enumeration (no CheckPrice)."""
import asyncio, json, sys
from playwright.async_api import async_playwright
from app import browser as B
from app.readymade_enum import login_v4

V4 = "https://v4.excard.com.my/ordering/bill-book"


async def run():
    async with async_playwright() as pw:
        b = await B.launch(pw); page = await b.new_page()
        await login_v4(page)
        await page.goto(V4, wait_until="networkidle", timeout=45000)
        await page.wait_for_timeout(3500)

        async def opts(name):
            return await page.evaluate(
                """(nm)=>{const s=[...document.querySelectorAll('select')].find(x=>(x.name||x.id||'').split('$').pop()===nm||x.id===nm);
                return s?[...s.options].map(o=>o.text.trim()).filter(Boolean):null;}""", name)

        out = {}
        for mat in ["ncr", "normal"]:
            # click the Paper Materials radio
            await page.evaluate("""(v)=>{const r=[...document.querySelectorAll('input[type=radio]')]
                .find(x=>x.name&&x.name.toLowerCase().includes('papermaterial')&&x.value===v);
                if(r){r.click();r.dispatchEvent(new Event('change',{bubbles:true}));}}""", mat)
            await page.wait_for_timeout(1500)
            layers = await opts("layers") or await opts("Paper Material + Layers *")
            out[mat] = {"layers_select": layers}
            # for the first real layer option, pick it and read paperLayer1 options
            if layers:
                real = next((o for o in layers if "Select" not in o and o.strip("- ")), None)
                if real:
                    await page.evaluate("""(txt)=>{const s=[...document.querySelectorAll('select')]
                        .find(x=>(x.name||x.id||'').toLowerCase().includes('layer')&&[...x.options].some(o=>o.text.trim()===txt));
                        if(s){s.value=[...s.options].find(o=>o.text.trim()===txt).value;s.dispatchEvent(new Event('change',{bubbles:true}));}}""", real)
                    await page.wait_for_timeout(1200)
                    out[mat]["paperLayer1"] = await opts("paperLayer1")
        (Path := __import__("pathlib").Path)("output/billbook_normal_probe.json").write_text(json.dumps(out, indent=1))
        print(json.dumps(out, indent=1))
        await b.close()

asyncio.run(run())
