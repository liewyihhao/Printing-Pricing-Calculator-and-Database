"""Probe: how does the do-loose-sheet / lo-loose-sheet SPA fetch a price? Capture network POSTs
while configuring a spec (incl. the new 'Gloss Art Paper 80gsm' paper) so we can sample it.

  python -m app.loose_price_probe do-loose-sheet
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from app import browser as B
from app.readymade_enum import login_v4

OUT = Path(__file__).resolve().parent.parent / "output"
V4 = "https://v4.excard.com.my/ordering/"


async def run(slug):
    calls = []
    async with async_playwright() as pw:
        b = await B.launch(pw)
        page = await b.new_page(viewport={"width": 1400, "height": 1400})
        await login_v4(page)

        async def on_resp(resp):
            u = resp.url
            if resp.request.method == "POST" and ("devv2.excard" in u.lower() or "checkprice" in u.lower()):
                try:
                    body = resp.request.post_data
                    txt = await resp.text()
                    calls.append({"url": u, "req": (body or "")[:600], "resp": txt[:300]})
                except Exception:
                    pass
        page.on("response", on_resp)

        await page.goto(V4 + slug, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(6000)
        # set selects; prefer an 80gsm Gloss Art paper if present
        picked = await page.evaluate(r"""() => {
          const out=[];
          for (const sel of document.querySelectorAll('select')) {
            const nm=(sel.name||sel.id||'').toLowerCase();
            const opts=[...sel.options].map(o=>o.text.trim());
            let i=-1;
            if (/size/.test(nm)) i=opts.findIndex(t=>/\bA3\b/.test(t));       // small size where 80gsm is valid
            else if (/paper/.test(nm)) i=opts.findIndex(t=>/gloss art paper 80gsm/i.test(t));
            if (i<0) i=opts.findIndex(t=>t && !/select|please|^-+$/i.test(t) && t!=='-');
            if (i>0){ sel.selectedIndex=i; sel.dispatchEvent(new Event('input',{bubbles:true})); sel.dispatchEvent(new Event('change',{bubbles:true})); out.push((sel.name||sel.id||'')+'='+opts[i]); }
          }
          return out;
        }""")
        print("picked:", picked[:10], file=sys.stderr)
        await page.wait_for_timeout(6000)
        (OUT / f"loose_price_probe_{slug}.json").write_text(
            json.dumps({"picked": picked, "calls": calls}, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"captured {len(calls)} price POSTs", file=sys.stderr)
        for c in calls[:4]:
            print("  URL:", c["url"], file=sys.stderr)
            print("  REQ:", c["req"][:300], file=sys.stderr)
            print("  RESP:", c["resp"][:150], file=sys.stderr)
        await b.close()


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1] if len(sys.argv) > 1 else "do-loose-sheet"))
