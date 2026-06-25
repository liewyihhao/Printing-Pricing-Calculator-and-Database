"""Fetch v4 price-list pages after login, export DataTable rows to CSV.

  python -m app.v4_pricelist_fetch mask-keeper
  python -m app.v4_pricelist_fetch non-woven-bag
  python -m app.v4_pricelist_fetch sachet-board

For each slug, outputs output/v4_pricelists/<slug>.csv.
The DataTable is server-side with a category selector — we iterate all categories.
"""
import asyncio, sys, csv, json
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch
from . import config

OUT = Path(__file__).resolve().parent.parent / "output" / "v4_pricelists"
OUT.mkdir(parents=True, exist_ok=True)
SLUGS = sys.argv[1:] if len(sys.argv) > 1 else ["mask-keeper"]


async def v4_login(page):
    await page.goto("https://v4.excard.com.my/", wait_until="networkidle")
    await asyncio.sleep(3)
    for sel in ["text=/^LOGIN$/", "text=/^Login$/", "a:has-text('LOGIN')", "button:has-text('LOGIN')"]:
        loc = page.locator(sel).first
        if await loc.count():
            try: await loc.click(timeout=4000); break
            except Exception: pass
    await asyncio.sleep(2)
    try:
        await page.fill("input[name$='txtusername']", config.USERNAME, timeout=6000)
        await page.fill("input[name$='txtpassword']", config.PASSWORD, timeout=6000)
        try:
            async with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
                await page.press("input[name$='txtpassword']", "Enter")
        except Exception:
            pass
        try: await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception: pass
    except Exception as e:
        print("login fill err", str(e)[:80])
    has_login = await page.evaluate(r"()=>/\bLOGIN\b/.test(document.body.innerText)")
    print("after login url:", page.url, "| still shows LOGIN:", has_login)
    return not has_login


async def read_table(page):
    """Read the current DataTable rows + headers."""
    # Wait for table to load (spinner gone or rows > 0)
    for _ in range(20):
        n = await page.evaluate("()=>{const t=document.querySelector('table tbody');return t?t.querySelectorAll('tr').length:0;}")
        if n > 0: break
        await asyncio.sleep(1)
    data = await page.evaluate(r"""()=>{
      const tables=[...document.querySelectorAll('table')];
      let best=null, bestRows=0;
      for(const t of tables){const r=t.querySelectorAll('tbody tr:not(.odd):not([style*="display:none"])').length;
        if(r>bestRows){bestRows=r;best=t;}}
      if(!best) return {headers:[], rows:[], count:0};
      const headers=[...best.querySelectorAll('thead th')].map(th=>th.innerText.trim());
      const rows=[...best.querySelectorAll('tbody tr')].map(tr=>[...tr.querySelectorAll('td')].map(td=>td.innerText.trim()));
      return {headers, rows, title:document.title, count:bestRows};}""")
    return data


async def set_page_length(page, length=10000):
    """Set DataTable to show all rows at once."""
    try:
        sel = await page.query_selector("select[name$='_length']")
        if sel:
            await sel.select_option(value=str(length))
            await asyncio.sleep(3)
    except Exception:
        pass


async def get_categories(page):
    """Get category radio buttons or select options if present."""
    cats = await page.evaluate(r"""()=>{
      // Look for category radios or a category select
      const radios=[...document.querySelectorAll("input[type=radio]")]
        .filter(r=>r.offsetParent&&/categor/i.test(r.name||r.id||r.closest('label')?.innerText||''));
      if(radios.length) return {type:'radio', vals:radios.map(r=>r.value)};
      const sel=[...document.querySelectorAll('select')]
        .find(s=>s.name&&/categor/i.test(s.name));
      if(sel) return {type:'select', name:sel.name||sel.id, opts:[...sel.options].map(o=>o.value)};
      return {type:'none', vals:['']};
    }""")
    return cats


async def scrape_slug(page, slug):
    url = f"https://v4.excard.com.my/price-list/{slug}"
    print(f"\n=== Fetching: {url} ===")
    await page.goto(url, wait_until="networkidle")
    await asyncio.sleep(5)
    print(f"Page title: {await page.title()}, URL: {page.url}")

    # Check if redirected to login
    if "/home-visitor" in page.url or "/login" in page.url:
        print("  REDIRECTED TO LOGIN — skipping")
        return None

    await set_page_length(page)

    cats = await get_categories(page)
    print(f"  Categories found: {cats}")

    all_rows = []
    headers = []

    if cats["type"] == "none" or (cats["type"] == "radio" and not cats["vals"]):
        data = await read_table(page)
        headers = data["headers"]
        all_rows = data["rows"]
        print(f"  Got {len(all_rows)} rows")
    elif cats["type"] == "radio":
        for val in cats["vals"]:
            try:
                await page.check(f"input[type=radio][value='{val}']")
                await asyncio.sleep(3)
                await set_page_length(page)
                data = await read_table(page)
                if not headers:
                    headers = data["headers"]
                all_rows.extend(data["rows"])
                print(f"  Category {val}: {len(data['rows'])} rows")
            except Exception as e:
                print(f"  Category {val} error: {e}")
    elif cats["type"] == "select":
        for opt in cats["opts"]:
            if not opt or opt in ("", "0"):
                continue
            try:
                await page.select_option(f"select[name='{cats['name']}']", value=opt)
                await asyncio.sleep(3)
                await set_page_length(page)
                data = await read_table(page)
                if not headers:
                    headers = data["headers"]
                all_rows.extend(data["rows"])
                print(f"  Category {opt}: {len(data['rows'])} rows")
            except Exception as e:
                print(f"  Category {opt} error: {e}")

    if not headers or not all_rows:
        # Try a screenshot to debug
        await page.screenshot(path=str(OUT.parent.parent / "output" / f"v4_pl_{slug}.png"))
        print(f"  No data found — screenshot saved as v4_pl_{slug}.png")
        return None

    out_path = OUT / f"{slug}.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(all_rows)
    print(f"  Saved {len(all_rows)} rows to {out_path}")
    return out_path


async def run():
    async with async_playwright() as pw:
        b = await launch(pw)
        ctx = await b.new_context(viewport={"width": 1500, "height": 1400})
        page = await ctx.new_page()
        logged_in = await v4_login(page)
        if not logged_in:
            print("WARNING: login may have failed — attempting anyway")
        for slug in SLUGS:
            result = await scrape_slug(page, slug)
            if result:
                print(f"SUCCESS: {result}")
            else:
                print(f"FAILED: {slug}")
        await b.close()


asyncio.run(run())
