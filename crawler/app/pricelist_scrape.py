"""Scrape a v4 price-list page's DataTable rows directly (no login, no CSV download).
Tries to read the table; sets a large page length first. Prints row count + sample.

  python -m app.pricelist_scrape <pricelist-url>
"""
import asyncio, sys, json
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch
OUT = Path(__file__).resolve().parent.parent / "output" / "v4_pricelists"
URL = sys.argv[1] if len(sys.argv) > 1 else "https://v4.excard.com.my/price-list/money-packet"


async def run():
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1500, "height": 1400})
        page = await ctx.new_page()
        await page.goto(URL, wait_until="networkidle")
        await asyncio.sleep(4)
        # read the data table: headers + all rows
        data = await page.evaluate(r"""()=>{
          const tables=[...document.querySelectorAll('table')];
          let best=null, bestRows=0;
          for(const t of tables){const r=t.querySelectorAll('tbody tr').length; if(r>bestRows){bestRows=r;best=t;}}
          if(!best) return {headers:[], rows:[]};
          const headers=[...best.querySelectorAll('thead th')].map(th=>th.innerText.trim());
          const rows=[...best.querySelectorAll('tbody tr')].map(tr=>[...tr.querySelectorAll('td')].map(td=>td.innerText.trim()));
          return {headers, rows, title:document.title};}""")
        print("TITLE:", data.get("title"))
        print("HEADERS:", data["headers"])
        print("ROW COUNT:", len(data["rows"]))
        for r in data["rows"][:3]:
            print("  ", r)
        await b.close()

asyncio.run(run())
