"""Packaging recon v2: capture the GetPriceFactor2 pricing call (request body + response)
and the DIY configurator's option model, for a couple of box codes.

  python -m app.packaging_recon2 [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts

OUT = Path(__file__).resolve().parent.parent / "output"
DIY = "https://packaging.excard.com.my/uc/diy/{}"
CODES = ["A001X", "D040A"]


async def _wait(page, t=6.0):
    try: await page.wait_for_load_state("networkidle", timeout=20000)
    except Exception: pass
    await asyncio.sleep(t)


async def recon(page, code):
    captured = []

    async def on_resp(resp):
        u = resp.url
        if "GetPriceFactor" in u or "/uc/" in u and resp.request.method == "POST":
            rec = {"url": u, "status": resp.status, "method": resp.request.method}
            try: rec["req_body"] = resp.request.post_data
            except Exception: rec["req_body"] = None
            try:
                rec["resp"] = (await resp.text())[:4000]
            except Exception:
                rec["resp"] = None
            captured.append(rec)
    page.on("response", on_resp)
    info = {"code": code}
    try:
        await page.goto(DIY.format(code), wait_until="domcontentloaded"); await _wait(page)
        info["final_url"] = page.url
        # full option panel: any element with text that looks like an option group
        info["panel_text"] = await page.evaluate(r"""() => {
            const root = document.querySelector('.diy, #diy, [class*=option], [class*=config], aside, .sidebar') || document.body;
            return (root.innerText||'').slice(0, 3000);
        }""")
        # global JS data model candidates
        info["globals"] = await page.evaluate(r"""() => {
            const out={}; for (const k of Object.keys(window)) {
              try { const v=window[k];
                if (v && typeof v==='object' && !(v instanceof Node) &&
                    /box|diy|price|option|material|product|spec|config|model/i.test(k)) {
                  out[k]=JSON.stringify(v).slice(0,800); } } catch(e){} }
            return out;
        }""")
    except Exception as e:  # noqa: BLE001
        info["error"] = str(e)
    await asyncio.sleep(1)
    page.remove_listener("response", on_resp)
    info["captured_posts"] = captured
    return info


async def run(account_id=1):
    a = accounts.get(account_id)
    result = {}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page()
        try: await login(page, username=a.username, password=a.password)
        except Exception: pass
        for code in CODES:
            info = await recon(page, code)
            result[code] = info
            print(f"\n=== {code} === posts captured: {len(info.get('captured_posts',[]))}")
            for p in info.get("captured_posts", []):
                print(f"  [{p['status']}] {p['method']} {p['url']}")
                if p.get("req_body"): print("    REQ:", p["req_body"][:500])
                if p.get("resp"): print("    RESP:", p["resp"][:800])
            print("  globals:", list(info.get("globals", {}).keys()))
        OUT.joinpath("packaging_recon2.json").write_text(json.dumps(result, indent=1))
        try: await b.close()
        except Exception: pass
    print("\nwrote output/packaging_recon2.json")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
