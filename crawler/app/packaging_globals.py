"""Dump the packaging DIY JS globals (catalogue + option model + limits + materials)
to output/packaging_globals/*.json. These define the whole packaging product space.

  python -m app.packaging_globals [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login

OUTD = Path(__file__).resolve().parent.parent / "output" / "packaging_globals"
DIY = "https://packaging.excard.com.my/uc/diy/A001X"
GLOBALS = ["boxTree", "restBoxes", "BOXLIB", "bootPms4DIY", "boxPmsLimit", "Mid4DiyAndOrder", "__boxPmsLimit",
           "PM", "_apnPms", "BoxLib", "BoxDiy2", "BoxDiyDBStore", "BoxDiyComponents", "BOX2"]


async def run(account_id=1):
    from . import accounts
    a = accounts.get(account_id)
    OUTD.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page()
        try: await login(page, username=a.username, password=a.password)
        except Exception: pass
        await page.goto(DIY, wait_until="domcontentloaded")
        try: await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception: pass
        await asyncio.sleep(6)
        for g in GLOBALS:
            try:
                val = await page.evaluate(f"() => {{ try {{ return JSON.stringify(window['{g}']); }} catch(e) {{ return null; }} }}")
            except Exception:
                val = None
            if val:
                (OUTD / f"{g}.json").write_text(val)
                print(f"  {g}: {len(val)} chars")
            else:
                print(f"  {g}: (empty/undefined)")
        try: await b.close()
        except Exception: pass
    print(f"wrote {OUTD}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
