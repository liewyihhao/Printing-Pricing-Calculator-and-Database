"""Sample Label Sticker LAMINATION finishing (ddlfinishing) deltas — applies to all
cut categories. Options: Matte/Gloss Laminate (Front), Gloss Water Based Varnish,
UV Varnish, Soft Touch Laminate (Front). Delta = price(with) - base, across qty and
a couple sizes (lamination is per-area). Saves output/sticker_finishing.json:
  {opt: {"WxH": {qty: delta}}}

  python -m app.sticker_finishing_sampler [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .logging_setup import log
from .sticker_capture import DIGITAL, configure_digital, _read_price, _wait, _sel

OUT = Path(__file__).resolve().parent.parent / "output"
QTYS = [50, 100, 300, 500, 1000, 2000, 5000]
SIZES = [(50, 50), (100, 100), (150, 150)]
OPTS = ["Matte Laminate (Front)", "Gloss Laminate (Front)", "Gloss Water Based Varnish",
        "UV Varnish", "Soft Touch Laminate (Front)"]


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "sticker_finishing.json"
    data = json.loads(out.read_text()) if out.exists() else {o: {} for o in OPTS}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for (h, w) in SIZES:
            wxh = f"{h}x{w}"
            for q in QTYS:
                await page.goto(DIGITAL, wait_until="domcontentloaded"); await _wait(page)
                await configure_digital(page, "Mirror Kote", "4C,1", "Rectangle/Square", h, w, q)
                base = (await _read_price(page)).get("before_discount")
                if not base:
                    continue
                for opt in OPTS:
                    if not await _sel(page, "ddlfinishing", opt):
                        continue
                    p = (await _read_price(page)).get("before_discount")
                    if p:
                        data.setdefault(opt, {}).setdefault(wxh, {})[str(q)] = round(p - base, 2)
                    await _sel(page, "ddlfinishing", "Not Required")
                out.write_text(json.dumps(data, indent=1))
                log.info("sticker_fin", size=wxh, q=q, base=base)
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=1))
    print(f"wrote {out.name}: opts={list(data)}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
