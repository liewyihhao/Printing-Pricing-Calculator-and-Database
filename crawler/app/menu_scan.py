"""Scrape Excard's authoritative product mega-menu (every product link + label) and diff it
against our calculator's products, so we can see coverage gaps. Read-only.

  python -m app.menu_scan
"""
from __future__ import annotations
import asyncio, json, re, sys
from pathlib import Path
from playwright.async_api import async_playwright
from app import browser as B

OUT = Path(__file__).resolve().parent.parent / "output"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


async def run():
    async with async_playwright() as pw:
        b = await B.launch(pw)
        ctx = await b.new_context(viewport={"width": 1500, "height": 1200})
        page = await ctx.new_page()
        await B.login(page)
        await page.goto("https://www.excard.com.my/home-member", wait_until="networkidle", timeout=45000)
        await page.wait_for_timeout(2000)
        # Every product link in the mega-menu: anchors under /product/ or /spec/
        items = await page.evaluate(r"""() => {
          const seen={}, out=[];
          document.querySelectorAll("a[href]").forEach(a=>{
            const href=a.getAttribute('href')||'';
            if(/\/(product|spec)\//i.test(href)){
              const label=(a.innerText||a.textContent||'').replace(/\s+/g,' ').trim();
              if(label && label.length<50 && !seen[label]){seen[label]=1;out.push({label, href});}
            }});
          return out;}""")
        await b.close()
    (OUT / "excard_menu.json").write_text(json.dumps(items, indent=1))
    return items


def diff(items):
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))
    ours = data["products"]
    # normalized token sets of our product names (strip the "— Method" suffix + alias notes)
    def base(n): return _norm(re.split(r"[—(]", n)[0])
    ourbases = {base(p["name"]) for p in ours}
    ournames = "\n".join(_norm(p["name"]) for p in ours)
    missing = []
    for it in items:
        lab = it["label"]
        nb = _norm(re.split(r"[—(]", lab)[0])
        # match if our product base-name contains or equals the menu label token, or vice-versa
        hit = any(nb and (nb in ob or ob in nb) for ob in ourbases) or (_norm(lab) in ournames)
        if not hit:
            missing.append(lab)
    return missing


if __name__ == "__main__":
    items = asyncio.run(run())
    print(f"Excard menu: {len(items)} product links", file=sys.stderr)
    miss = diff(items)
    print("\n=== Excard menu products NOT obviously in our calculator ===")
    for m in sorted(set(miss)):
        print("  ", m)
    print(f"\n({len(set(miss))} to review of {len(items)} menu items)")
