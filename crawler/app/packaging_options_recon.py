"""Recon the packaging DIY option model: materials, print colours, and finishing/process
options (IDs + names) — captured from the page's option menus + any loader XHR + globals.

  python -m app.packaging_options_recon [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts

OUT = Path(__file__).resolve().parent.parent / "output"
DIY = "https://packaging.excard.com.my/uc/diy/A001X"


async def run(account_id=1):
    a = accounts.get(account_id)
    cap = []
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page()

        async def on_resp(r):
            u = r.url.lower()
            if any(k in u for k in ("process", "material", "getprocess", "getmaterial", "craft", "paper", "boxpms", "getbox")) and "/uc/" in u:
                try: body = (await r.text())[:3000]
                except Exception: body = None
                cap.append({"url": r.url, "status": r.status, "body": body})
        page.on("response", on_resp)

        try: await login(page, username=a.username, password=a.password)
        except Exception: pass
        await page.goto(DIY, wait_until="domcontentloaded")
        try: await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception: pass
        await asyncio.sleep(6)

        # dump more globals that may hold the process/material catalog
        globs = {}
        for g in ["PROCESSLIB", "MATERIALLIB", "Processes", "Materials", "craftTree",
                  "processTree", "materialTree", "Mid4DiyAndOrder", "boxProcess", "__processes",
                  "PROCESS", "MATERIAL", "DIYDATA", "diyData", "__diy", "PM"]:
            try:
                v = await page.evaluate(f"() => {{ try {{ return JSON.stringify(window['{g}']); }} catch(e){{ return null; }} }}")
                if v and v not in ("null", "{}", "[]", "\"\""):
                    globs[g] = v[:4000]
            except Exception:
                pass
        # also scan all window keys for process/material-ish objects
        keys = await page.evaluate(r"""() => Object.keys(window).filter(k=>/process|material|craft|paper|pm|diy|box/i.test(k))""")
        # option menu DOM text (the right-side config panel)
        panel = await page.evaluate(r"""() => {
            const els=[...document.querySelectorAll('[class*=process],[class*=material],[class*=option],[class*=craft],[class*=menu],.diy-right,.config')];
            return els.slice(0,8).map(e=>(e.innerText||'').slice(0,400));
        }""")
        out = {"xhr": cap, "globals": globs, "window_keys": keys, "panel_text": panel}
        OUT.joinpath("packaging_options_recon.json").write_text(json.dumps(out, indent=1))
        print("XHR captured:", [(c["url"].split("/uc/")[-1], c["status"]) for c in cap])
        print("globals found:", list(globs.keys()))
        print("candidate window keys:", keys[:30])
        try: await b.close()
        except Exception: pass


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
