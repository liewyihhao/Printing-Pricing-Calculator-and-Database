"""Enumerate the full control list for products whose v4 /ordering page 500s, using their
legacy www /spec form. Reuses option_audit._JS. Writes output/option_audit/<slug>.json
(overwriting the v4 error stub) so the parity gap audit can include them.

  python -m app.www_audit
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from app import browser as B
from app.option_audit import _JS, OUT

# slug -> list of candidate www /spec URLs (first that renders product controls wins)
BASE = "https://www.excard.com.my/spec/"
CAND = {
    "booklet": [BASE+"Litho/Booklet", BASE+"Digital/Booklet"],
    "loose-sheet": [BASE+"Litho/Loose_Sheet", BASE+"Digital/Loose_Sheet"],
    "magnet": [BASE+"Digital/Magnet"],
    "voucher": [BASE+"Litho/Voucher"],
    "wire-o-notebook": [BASE+"Litho/Wire-O_Notebook", BASE+"Digital/Wire-O_Notebook"],
    "l-shape-folder": [BASE+"Digital/L-Shape_Plastic_Folder", BASE+"Digital/L_Shape_Plastic_Folder"],
    "static-cling-window-sticker": [BASE+"Digital/Static_Cling_Window_Sticker"],
    "desk-calendar-hard-stand": [BASE+"Litho/Desk_Calendar", BASE+"Litho/Hard_Stand_Desk_Calendar"],
    "desk-calendar-soft-stand": [BASE+"Litho/Soft_Stand_Desk_Calendar", BASE+"Litho/Desk_Calendar"],
    "papan-kopi": [BASE+"Litho/Papan_Kopi", BASE+"Litho/Sachet_Board"],
    "pillow": [BASE+"Litho/Pillow"],
    "stamp-chop": [BASE+"Digital/Stamp_Chop", BASE+"Litho/Stamp_Chop"],
    "mask-keeper": [BASE+"Litho/Mask_Keeper"],
    "sublimation-shirt": [BASE+"Digital/Sublimation_Shirt"],
    "label-sticker-with-hot-stamping": [BASE+"Letterpress/Label_Sticker_With_Hot_Stamping",
                                        BASE+"Digital/Label_Sticker_With_Hot_Stamping"],
    "wire-o-wall-calendar": [BASE+"Litho/Wire-O_Wall_Calendar"],
}


async def enum_www(page, url):
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except Exception as e:
        return None, "goto:" + str(e)[:60]
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    await page.wait_for_timeout(1500)
    body = await page.evaluate("() => document.body ? document.body.innerText.slice(0,80) : ''")
    if "Sorry" in body or "not found" in body.lower() or "error" in body.lower()[:40]:
        return None, "notfound"
    ctrls = await page.evaluate(_JS)
    # keep only if there are real product controls (selects/radios beyond nav)
    real = [c for c in ctrls if c.get("options") and c["options"][:2] != ["Track Order", "Product"]]
    if len(real) < 2:
        return None, "no-controls"
    return ctrls, url


async def run(slugs):
    async with async_playwright() as pw:
        b = await B.launch(pw)
        ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page()
        await B.login(page)
        for slug in slugs:
            got = None
            for url in CAND.get(slug, []):
                ctrls, info = await enum_www(page, url)
                if ctrls:
                    got = (ctrls, url); break
            if got:
                info = {"slug": slug, "url": got[1], "error": None, "controls": got[0], "source": "www"}
                nreal = len([c for c in got[0] if c.get('options') and c['options'][:2] != ['Track Order', 'Product']])
                print(f"[{slug}] OK {got[1]} controls={nreal}", file=sys.stderr)
            else:
                info = {"slug": slug, "error": "www enumerate failed (tried candidates)", "controls": []}
                print(f"[{slug}] FAIL", file=sys.stderr)
            (OUT / f"{slug}.json").write_text(json.dumps(info, indent=1))
        await b.close()


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1:] or list(CAND.keys())))
