"""Generic Excard order-form dumper — dump every visible control + options on any
www.excard.com.my/spec/<Method>/<slug> page (logged in). Reusable across all products.

  python -m app.formdump_url "https://www.excard.com.my/spec/Litho/Brochure" [account] [tag]

Writes output/formdump_<tag-or-slug>.json and prints a summary.
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .parity_formdump import _dump_all

OUT = Path(__file__).resolve().parent.parent / "output"


async def run(url, account_id=1, tag=None):
    a = accounts.get(account_id)
    tag = tag or url.rstrip("/").split("/")[-1].lower()
    async with async_playwright() as pw:
        b = await launch(pw)
        ctx = await b.new_context(viewport={"width": 1440, "height": 1600})
        page = await ctx.new_page()
        await login(page, username=a.username, password=a.password)
        await page.goto(url, wait_until="domcontentloaded")
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        await asyncio.sleep(3.0)
        dump = await _dump_all(page)
        dump["url"] = url
        OUT.joinpath(f"formdump_{tag}.json").write_text(json.dumps(dump, indent=1))
        print(f"=== {tag} ({url}) ===")
        print("SECTIONS:", dump["sections"])
        print("SELECTS:")
        for s in dump["selects"]:
            print(f"  {s['name']}: {s['options'][:20]}")
        print("RADIOS:", dump["radios"])
        print("CHECKBOXES:", dump["checkboxes"])
        print("TEXT INPUTS:", dump["text_inputs"])
        try:
            await b.close()
        except Exception:
            pass


if __name__ == "__main__":
    url = sys.argv[1]
    acct = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    tag = sys.argv[3] if len(sys.argv) > 3 else None
    asyncio.run(run(url, acct, tag))
