"""Packaging Box P0 recon. Two parts:
 1. Catalogue: scrape www.excard.com.my/packaging-box-style for all box codes + names.
 2. DIY configurator: open packaging.excard.com.my/uc/diy/<CODE> for a few sample codes;
    capture network XHR/fetch (the pricing API), visible controls, the 3D lib, and whether
    login is required.

Writes output/packaging_recon.json.

  python -m app.packaging_recon [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login, polite_pause
from . import accounts

OUT = Path(__file__).resolve().parent.parent / "output"
LIST_URL = "https://www.excard.com.my/packaging-box-style"
DIY = "https://packaging.excard.com.my/uc/diy/{}"
SAMPLE_CODES = ["A001X", "A002X", "C001A", "D040A", "E005X"]  # RTE, STE, lock-bottom, tray, hinged


async def _wait(page, t=4.0):
    try: await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception: pass
    await asyncio.sleep(t)


async def recon_catalogue(page):
    await page.goto(LIST_URL, wait_until="domcontentloaded"); await _wait(page, 2)
    # links to /uc/diy/<code> or data-code attributes
    items = await page.evaluate(r"""() => {
        const out=[];
        for (const a of document.querySelectorAll('a[href*="/diy/"], a[href*="packaging.excard"]')) {
            const m=a.href.match(/diy\/([A-Za-z0-9]+)/);
            out.push({code: m?m[1]:null, text:(a.innerText||'').trim().slice(0,40), href:a.href});
        }
        return out;
    }""")
    return items


async def recon_diy(page, code):
    reqs = []
    def on_req(r):
        if r.resource_type in ("xhr", "fetch"):
            reqs.append({"method": r.method, "url": r.url})
    page.on("request", on_req)
    info = {"code": code, "requires_login": False}
    try:
        await page.goto(DIY.format(code), wait_until="domcontentloaded"); await _wait(page, 6)
        info["final_url"] = page.url
        info["requires_login"] = "login" in page.url.lower() or "signin" in page.url.lower()
        info["title"] = await page.title()
        # controls
        info["selects"] = await page.evaluate("""() => [...document.querySelectorAll('select')].filter(s=>s.offsetParent)
            .map(s=>({name:s.name||s.id, options:[...s.options].map(o=>o.text.trim()).slice(0,12)}))""")
        info["number_inputs"] = await page.evaluate("""() => [...document.querySelectorAll('input[type=number],input[type=text]')].filter(i=>i.offsetParent)
            .map(i=>({name:i.name||i.id, placeholder:i.placeholder, value:i.value}))""")
        info["has_canvas"] = await page.evaluate("() => !!document.querySelector('canvas')")
        info["3d_libs"] = await page.evaluate("""() => ({three: typeof window.THREE!=='undefined',
            babylon: typeof window.BABYLON!=='undefined',
            scripts:[...document.querySelectorAll('script[src]')].map(s=>s.src).filter(u=>/three|babylon|box|3d|webgl|diy|packaging/i.test(u)).slice(0,20)})""")
        # price text on page
        info["price_text"] = await page.evaluate(r"""() => { const b=document.body.innerText;
            const m=b.match(/(RM|price|total|quantity|qty|dimension|width|height|length|material)[^\n]{0,50}/gi); return m?m.slice(0,20):[]; }""")
    except Exception as e:  # noqa: BLE001
        info["error"] = str(e)
    page.remove_listener("request", on_req)
    info["xhr"] = reqs[:60]
    return info


async def run(account_id=1):
    a = accounts.get(account_id)
    result = {}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page()
        try:
            await login(page, username=a.username, password=a.password)
        except Exception:
            pass
        result["catalogue"] = await recon_catalogue(page)
        print(f"catalogue links found: {len(result['catalogue'])}")
        result["diy"] = []
        for code in SAMPLE_CODES:
            info = await recon_diy(page, code)
            result["diy"].append(info)
            print(f"\n=== {code} === login={info.get('requires_login')} canvas={info.get('has_canvas')} "
                  f"3d={info.get('3d_libs',{}).get('three') or info.get('3d_libs',{}).get('babylon')}")
            print("  selects:", [s["name"] for s in info.get("selects", [])])
            print("  numbers:", [n["name"] for n in info.get("number_inputs", [])])
            api = [r for r in info.get("xhr", []) if any(k in r["url"].lower() for k in ("price", "calc", "quote", "api", "box", "diy"))]
            print("  candidate API XHR:", api[:8])
        OUT.joinpath("packaging_recon.json").write_text(json.dumps(result, indent=1))
        try: await b.close()
        except Exception: pass
    print("\nwrote output/packaging_recon.json")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
