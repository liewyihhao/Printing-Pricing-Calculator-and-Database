"""Capture each box's DEFAULT ProcessJson + BoxPms (the chain the DIY page sends to
GetPriceFactor2 on load). Needed to (a) price each box's real default config and (b) vary
material/colour/finishing within the correct structural chain.

Saves output/packaging_defaults.json {box: {"BoxPms":..., "ProcessJson":[...]}}

  python -m app.packaging_defaults [account]
"""
from __future__ import annotations
import asyncio, json, sys, urllib.parse
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .logging_setup import log

OUT = Path(__file__).resolve().parent.parent / "output"
DIY = "https://packaging.excard.com.my/uc/diy/{}"


async def run(account_id=1):
    a = accounts.get(account_id)
    cat = json.loads((OUT / "packaging_catalogue.json").read_text())
    codes = [b["BoxID"] for b in cat if b.get("On")]
    out_f = OUT / "packaging_defaults.json"
    data = json.loads(out_f.read_text()) if out_f.exists() else {}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1280, "height": 900})
        page = await ctx.new_page()
        try: await login(page, username=a.username, password=a.password)
        except Exception: pass

        for code in codes:
            if code in data:
                continue
            captured = {}
            def on_req(r, code=code, captured=captured):
                if "GetPriceFactor2" in r.url and r.method == "POST" and not captured:
                    try:
                        body = urllib.parse.parse_qs(r.post_data or "")
                        bd = json.loads(body.get("boxDiys", ["[]"])[0])
                        if bd:
                            captured["BoxPms"] = bd[0].get("BoxPms")
                            captured["ProcessJson"] = json.loads(bd[0].get("ProcessJson", "[]"))
                    except Exception:
                        pass
            page.on("request", on_req)
            try:
                await page.goto(DIY.format(code), wait_until="domcontentloaded")
                try: await page.wait_for_load_state("networkidle", timeout=15000)
                except Exception: pass
                await asyncio.sleep(4)
            except Exception as e:  # noqa: BLE001
                log.info("pkg.def_err", box=code, err=str(e)[:50])
            page.remove_listener("request", on_req)
            if captured:
                data[code] = captured; out_f.write_text(json.dumps(data))
                log.info("pkg.default", box=code, procs=[p.get("ID") for p in captured.get("ProcessJson", [])])
            else:
                log.info("pkg.default_miss", box=code)
        try: await b.close()
        except Exception: pass
    print(f"captured defaults for {len(data)}/{len(codes)} boxes -> {out_f.name}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
