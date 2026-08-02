"""Probe: how do the section headers (General / Optional Finishing / Add On / Delivery) appear in
the v4 SPA DOM, and what controls sit under each? Gentle load, then dump header-like elements +
form controls in DOM order.

  python -m app.v4_probe_sections <v4-slug>
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from app import browser as B
from app.readymade_enum import login_v4

OUT = Path(__file__).resolve().parent.parent / "output"
V4 = "https://v4.excard.com.my/ordering/"

JS = r"""() => {
  const known = /^(general|optional finishing|add[- ]?on|delivery|finishing|artwork|summary)$/i;
  // header candidates: short-text elements whose bg is teal-ish OR whose text is a known section
  const headers = [];
  for (const el of document.querySelectorAll('div,h1,h2,h3,h4,h5,span,p')) {
    const t = (el.childElementCount===0 ? el.textContent : '').trim();
    if (!t || t.length>28) continue;
    const bg = getComputedStyle(el).backgroundColor || '';
    const m = bg.match(/rgba?\(([^)]+)\)/);
    let teal=false;
    if (m){ const [r,g,b]=m[1].split(',').map(Number); teal = (b>90 && g>90 && r<90 && (g+b)>200); }
    if (known.test(t) || teal) headers.push({text:t, teal, bg, cls:el.className, tag:el.tagName});
  }
  // controls in DOM order with label
  const controls = [];
  for (const el of document.querySelectorAll('select,input[type=radio],input[type=checkbox]')) {
    let g = el.closest('.form-group,.row,.mb-3,.field,.option-block') || el.parentElement;
    let lab=''; if(g){const l=g.querySelector('label,.control-label,.field-label,b,h5,h6'); if(l) lab=l.textContent.trim();}
    controls.push({tag:el.tagName, type:el.type||'', name:el.name||el.id||'', label:lab.slice(0,40)});
  }
  return {headers, nControls:controls.length, controls: controls.slice(0,40)};
}"""


async def run(slug):
    async with async_playwright() as pw:
        b = await B.launch(pw)
        page = await b.new_page(viewport={"width": 1500, "height": 2000})
        await login_v4(page)
        await page.goto(V4 + slug, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(7000)
        info = await page.evaluate(JS)
        (OUT / f"v4_sections_{slug}.json").write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(info, indent=1, ensure_ascii=False)[:2500], file=sys.stderr)
        await b.close()


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1] if len(sys.argv) > 1 else "lo-loose-sheet"))
