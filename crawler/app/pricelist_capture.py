"""Capture an Excard v4 price-list DataTable into output/v4_options/<slug>_options.json
(the standard capture shape) so the build pipeline turns it into an EXACT product.

Uses Playwright (no 45s eval cap like the browser extension) so it handles the big tables
(banner ~91k rows). Reads #MPPriceList's DataTable, drops noise columns, and builds curves
keyed by the user-selectable option axes -> {qty: WM price}.

CLI:  python -m app.pricelist_capture banner car-sticker notepad paper-bag
"""
from __future__ import annotations
import asyncio
import json
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright
from app import browser as B
from app.readymade_enum import login_v4

OUT = Path(__file__).resolve().parent.parent / "output"
NOISE = re.compile(r"price|date|process\s*day|weight|print\s*method|fee|delivery|shipment|"
                   r"^product$|compulsory|^em\b", re.I)


async def capture(page, slug):
    await page.goto(f"https://v4.excard.com.my/price-list/{slug}", wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2500)
    for _ in range(30):
        n = await page.evaluate("() => (typeof jQuery!=='undefined' && jQuery('#MPPriceList').length && jQuery('#MPPriceList').DataTable().rows().count()) || 0")
        if n:
            break
        await page.wait_for_timeout(400)
    data = await page.evaluate("""() => {
        const $=jQuery; const dt=$('#MPPriceList').DataTable();
        return dt.rows().data().toArray().map(r=>({...r}));
    }""")
    if not data:
        print(f"  {slug}: NO price-list data", file=sys.stderr)
        return None
    allc = list(data[0].keys())
    cols = [c for c in allc if not NOISE.search(c)]
    distinct = {}
    for c in cols:
        seen = []
        for r in data:
            v = r.get(c)
            if v is not None and v not in seen:
                seen.append(v)
        distinct[c] = seen
    opt = [c for c in cols if len(distinct[c]) > 1]
    # price + qty columns
    pc = next((c for c in allc if re.search(r"wm", c, re.I) and re.search(r"price", c, re.I)), None) \
        or next((c for c in allc if re.search(r"price", c, re.I) and not re.match(r"\s*em", c, re.I)), None)
    qc = next((c for c in allc if re.match(r"\s*quantity|\s*qty", c, re.I)), None)
    curves = {}
    axes = [c for c in opt if c != qc]
    for r in data:
        try:
            pv = float(str(r[pc]).replace(",", ""))
        except (ValueError, TypeError):
            continue
        if pv <= 0:
            continue
        q = re.sub(r"[^\d]", "", str(r[qc]))
        if not q:
            continue
        key = "|".join(str(r[c]) for c in axes)
        curves.setdefault(key, {})[q] = pv
    primary = opt[0] if opt else None
    deps = {}
    if primary:
        for pv in distinct[primary]:
            rows = [r for r in data if r.get(primary) == pv]
            sub = {}
            for c in opt:
                if c == primary:
                    continue
                vs = []
                for r in rows:
                    v = r.get(c)
                    if v is not None and v not in vs:
                        vs.append(v)
                sub[c] = vs
            deps[pv] = sub
    out = {
        "slug": slug, "source": "pricelist-datatable-pw", "rows": len(data),
        "optionCols": opt, "primary": primary, "deps": deps,
        "imageField": None, "distinct": {c: distinct[c] for c in opt}, "imageOptions": {},
        "priceMeta": {"priceCol": pc, "qtyCol": qc, "axisCols": axes, "nCurves": len(curves)},
        "curves": curves,
    }
    (OUT / "v4_options" / f"{slug}_options.json").write_text(json.dumps(out), encoding="utf-8")
    print(f"  {slug}: {len(curves)} curves, axes={axes}, pc={pc}", file=sys.stderr)
    return out


async def main(slugs):
    async with async_playwright() as pw:
        b = await B.launch(pw)
        page = await b.new_page()
        print("v4 login:", await login_v4(page), file=sys.stderr)
        for s in slugs:
            try:
                await capture(page, s)
            except Exception as e:
                print(f"  {s}: ERROR {type(e).__name__} {e}", file=sys.stderr)
        await b.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
