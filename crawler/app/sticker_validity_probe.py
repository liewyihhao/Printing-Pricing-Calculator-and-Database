"""Capture the Label-Sticker form's shape-driven conditionals: set Category (shape) to each value
and record which size/dieline controls appear (Round -> diameter; Rectangle -> H/W; Custom
Die-Cut -> dieline upload; etc.), plus Cutting Method behaviour.

  python -m app.sticker_validity_probe [slug]      # default label-sticker
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from app import browser as B
from app.readymade_enum import login_v4

OUT = Path(__file__).resolve().parent.parent / "output"
V4 = "https://v4.excard.com.my/ordering/"

_SETBYLABEL = """(args) => {
  const [labRx, valRx] = args;
  for (const sel of document.querySelectorAll('select')) {
    const g=sel.closest('.form-group,.row,.mb-3,.field')||sel.parentElement;
    const lab=g&&g.querySelector('label,b')?g.querySelector('label,b').textContent:'';
    if(new RegExp(labRx,'i').test(lab)){
      const i=[...sel.options].findIndex(o=>new RegExp(valRx,'i').test(o.text));
      if(i>=0){ sel.selectedIndex=i; sel.dispatchEvent(new Event('input',{bubbles:true})); sel.dispatchEvent(new Event('change',{bubbles:true})); return lab.trim()+'='+sel.options[i].text; }
    }
  }
  return null;
}"""

_CATVALUES = """() => {
  for (const sel of document.querySelectorAll('select')) {
    const g=sel.closest('.form-group,.row,.mb-3,.field')||sel.parentElement;
    const lab=g&&g.querySelector('label,b')?g.querySelector('label,b').textContent:'';
    if(/category|shape/i.test(lab)) return [...sel.options].map(o=>o.text.trim()).filter(t=>t&&!/^-/.test(t));
  }
  return [];
}"""

_VISCTRLS = """() => {
  const vis=el=>el&&el.offsetParent!==null&&el.getBoundingClientRect().height>1;
  const out=[]; const seen=new Set();
  for(const el of document.querySelectorAll('select,input[type=text],input[type=number],input[type=file]')){
    if(!vis(el))continue;
    const g=el.closest('.form-group,.row,.mb-3,.field')||el.parentElement;
    const lab=g&&g.querySelector('label,b,.control-label')?g.querySelector('label,b,.control-label').textContent.trim():(el.name||el.placeholder||'');
    if(!lab||/qty|quantity|country|courier|favourite|job name/i.test(lab))continue;
    if(seen.has(lab))continue; seen.add(lab);
    out.push({tag:el.tag||el.tagName, type:el.type||'', label:lab.slice(0,34)});
  }
  return out;
}"""


async def run(slug):
    async with async_playwright() as pw:
        b = await B.launch(pw)
        page = await b.new_page(viewport={"width": 1400, "height": 2200})
        await login_v4(page)
        await page.goto(V4 + slug, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(6000)
        cats = await page.evaluate(_CATVALUES)
        print("Category values:", cats, file=sys.stderr)
        result = {}
        for c in cats:
            r = await page.evaluate(_SETBYLABEL, ["category|shape", "^" + c[:12]])
            await page.wait_for_timeout(1800)
            ctrls = await page.evaluate(_VISCTRLS)
            result[c] = ctrls
            szlike = [x["label"] for x in ctrls if any(k in x["label"].lower() for k in ("height", "width", "diameter", "dieline", "size", "cutting"))]
            print(f"  [{c[:26]:26}] size/cut ctrls: {szlike}", file=sys.stderr)
        (OUT / f"sticker_validity_{slug}.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
        await b.close()


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1] if len(sys.argv) > 1 else "label-sticker"))
