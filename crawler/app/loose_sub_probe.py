"""Capture the SUB-controls Excard reveals when a loose-sheet finishing option is chosen:
Hot Stamping -> H/S Size + H/S Colour; Perforation -> Perforation Side + panel widths; Hole
Punching -> position. Drives lo-loose-sheet, sets each finishing field to a non-default value, and
dumps the newly-visible controls + options.

  python -m app.loose_sub_probe
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from app import browser as B
from app.readymade_enum import login_v4

OUT = Path(__file__).resolve().parent.parent / "output"
V4 = "https://v4.excard.com.my/ordering/lo-loose-sheet"

_SETBYLABEL = """(args) => {
  const [labelRx, valRx] = args;
  for (const sel of document.querySelectorAll('select')) {
    const g = sel.closest('.form-group,.row,.mb-3,.field')||sel.parentElement;
    const lab = g&&g.querySelector('label,b')?g.querySelector('label,b').textContent:'';
    if (new RegExp(labelRx,'i').test(lab)) {
      const i=[...sel.options].findIndex(o=>new RegExp(valRx,'i').test(o.text));
      if(i>=0){ sel.selectedIndex=i; sel.dispatchEvent(new Event('input',{bubbles:true})); sel.dispatchEvent(new Event('change',{bubbles:true})); return lab.trim()+' = '+sel.options[i].text; }
    }
  }
  return null;
}"""

_DUMP = """() => {
  const vis = el => el && el.offsetParent!==null && el.getBoundingClientRect().height>1;
  const rows=[];
  for (const el of document.querySelectorAll('select, input[type=text], input[type=number], input[type=radio], button')) {
    if(!vis(el)) continue;
    const g=el.closest('.form-group,.row,.mb-3,.field')||el.parentElement;
    const lab=g&&g.querySelector('label,b,.control-label')?g.querySelector('label,b,.control-label').textContent.trim():(el.name||el.placeholder||'');
    if(!lab || /qty|quantity|country|courier|favourite|size \*|paper \*|colour \*|package/i.test(lab)) continue;
    let opts=[]; if(el.tagName==='SELECT') opts=[...el.options].map(o=>o.text.trim()).filter(t=>t&&!/^-/.test(t)).slice(0,12);
    rows.push({tag:el.tagName, type:el.type||'', label:lab.slice(0,36), opts});
  }
  // dedup by label
  const seen=new Set(), out=[];
  for(const r of rows){ if(seen.has(r.label))continue; seen.add(r.label); out.push(r); }
  return out;
}"""


async def run():
    async with async_playwright() as pw:
        b = await B.launch(pw)
        page = await b.new_page(viewport={"width": 1400, "height": 2200})
        await login_v4(page)
        await page.goto(V4, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(6000)
        await page.evaluate(_SETBYLABEL, ["size", "A3"])
        await page.evaluate(_SETBYLABEL, ["paper", "Simili.*100"])
        await page.wait_for_timeout(1500)
        for tag, (lab, val) in {
            "HOT_STAMPING": ("hot stamping", "1C.*Front"),
            "PERFORATION": ("perforation", "3 Line"),
            "HOLE_PUNCH": ("hole punch", "3mm|6mm|yes"),
        }.items():
            r = await page.evaluate(_SETBYLABEL, [lab, val])
            await page.wait_for_timeout(2000)
            dump = await page.evaluate(_DUMP)
            print(f"\n== {tag} ({r}) ==", file=sys.stderr)
            for d in dump:
                print(f"   [{d['tag']}/{d['type']}] {d['label']:30} opts={d['opts'][:8]}", file=sys.stderr)
            (OUT / f"loose_sub_{tag}.json").write_text(json.dumps(dump, indent=1, ensure_ascii=False), encoding="utf-8")
            # reset it back so the next probe is isolated
            await page.evaluate(_SETBYLABEL, [lab, "Not Required|Not Require"])
            await page.wait_for_timeout(800)
        await b.close()


if __name__ == "__main__":
    asyncio.run(run())
