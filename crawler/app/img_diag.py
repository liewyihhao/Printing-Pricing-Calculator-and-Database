"""One-off diagnostic: for given product ids, print every option-image candidate URL/stem on the
supplier order page alongside our field options, so we can see WHY an image didn't map.

  python -m app.img_diag 149 163 169 175 177 114
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path

from playwright.async_api import async_playwright
from app import browser as B
from app.readymade_enum import login_v4
from app.build_specs_page import clean_name
from app.product_quantity import _base_slug, _ALIAS
from app.option_image_crawl import _collect, _variants, _map_to_fields

OUT = Path(__file__).resolve().parent.parent / "output"


async def run(targets):
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))["products"]
    tl = {str(t) for t in targets}
    data = [p for p in data if str(p["id"]) in tl]
    async with async_playwright() as pw:
        b = await B.launch(pw)
        page = await b.new_page()
        await login_v4(page)
        for p in data:
            own = _base_slug(p["name"])
            imgs = await _collect(page, own)
            src = own
            if not imgs:
                alias = _ALIAS.get(own, own)
                if alias != own:
                    imgs = await _collect(page, alias)
                    src = alias
            mapped = _map_to_fields(p, imgs)
            n = sum(len(v) for v in mapped.values())
            print(f"\n===== [{p['id']}] {clean_name(p['name'])}  (page slug: {src}) =====")
            print(f"  images found: {len(imgs)}  mapped: {n}")
            print("  -- raw image candidates (stem <- url) --")
            for url, stem in imgs:
                print(f"     {stem:40}  {url}")
            print("  -- our fields / options + their match variants --")
            for f in p.get("fields", []):
                opts = f.get("options") or []
                if not opts:
                    continue
                print(f"     field '{f['key']}' ({f.get('label','')}):")
                for o in opts:
                    print(f"        {o!r}  variants={sorted(_variants(o))}")
            print(f"  -- mapped result: {json.dumps(mapped, ensure_ascii=False)}")
        await b.close()


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1:] or ["149", "163", "169", "175", "177", "114"]))
