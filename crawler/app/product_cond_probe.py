"""Reusable focused conditional probe: drive one product's live v4 form, vary a named driver field
through its values, and dump the visible controls (+ options) per value — to find conditional
visibility / option rules for that product. Works where the bulk triage crashed.

  python -m app.product_cond_probe <slug> "<driver-label-regex>" ["<driver2-regex>" ...]
  e.g. python -m app.product_cond_probe money-packet "design" "mix design"
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from app import browser as B
from app.readymade_enum import login_v4

OUT = Path(__file__).resolve().parent.parent / "output"
V4 = "https://v4.excard.com.my/ordering/"

_VALUES = """(labRx) => {
  for (const sel of document.querySelectorAll('select')) {
    const g=sel.closest('.form-group,.row,.mb-3,.field')||sel.parentElement;
    const lab=g&&g.querySelector('label,b')?g.querySelector('label,b').textContent:'';
    if(new RegExp(labRx,'i').test(lab)) return [...sel.options].map(o=>o.text.trim()).filter(t=>t&&!/^-|please select/i.test(t));
  }
  return [];
}"""
_SET = """(args) => {
  const [labRx,val]=args;
  for (const sel of document.querySelectorAll('select')) {
    const g=sel.closest('.form-group,.row,.mb-3,.field')||sel.parentElement;
    const lab=g&&g.querySelector('label,b')?g.querySelector('label,b').textContent:'';
    if(new RegExp(labRx,'i').test(lab)){ const i=[...sel.options].findIndex(o=>o.text.trim()===val);
      if(i>=0){sel.selectedIndex=i;sel.dispatchEvent(new Event('input',{bubbles:true}));sel.dispatchEvent(new Event('change',{bubbles:true}));return true;} }
  }
  return false;
}"""
_SNAP = """() => {
  const vis=el=>el&&el.offsetParent!==null&&el.getBoundingClientRect().height>1;
  const rows=[]; let cur=null; const seen=new Set();
  const walk=document.createTreeWalker(document.body,NodeFilter.SHOW_ELEMENT); let n;
  while((n=walk.nextNode())){
    if(n.classList&&n.classList.contains('bigtitle_Ord')){cur=(n.textContent||'').trim();continue;}
    if(!cur||/delivery|net price|add name|quantity|summary/i.test(cur))continue;
    if((n.tagName==='SELECT'||(n.tagName==='INPUT'&&/radio|checkbox|text|number|file/.test(n.type)))&&vis(n)){
      const nm=n.name||n.id||''; if(/qty|country|courier|favourite|product$|job name/i.test(nm))continue;
      const g=n.closest('.form-group,.row,.mb-3,.field')||n.parentElement;
      const lab=g&&g.querySelector('label,b,.control-label')?g.querySelector('label,b,.control-label').textContent.trim():nm;
      if(!lab||seen.has(lab))continue; seen.add(lab);
      let opts=[]; if(n.tagName==='SELECT')opts=[...n.options].map(o=>o.text.trim()).filter(t=>t&&!/^-|please/i.test(t));
      rows.push({section:cur,label:lab.slice(0,36),type:n.type||'',opts:opts.slice(0,14)});
    }
  }
  return rows;
}"""


async def run(slug, drivers):
    async with async_playwright() as pw:
        b = await B.launch(pw)
        page = await b.new_page(viewport={"width": 1400, "height": 2400})
        await login_v4(page)
        await page.goto(V4 + slug, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(6000)
        result = {}
        for drv in drivers:
            vals = await page.evaluate(_VALUES, drv)
            result[drv] = {"values": {}}
            print(f"\n== driver /{drv}/ values={vals} ==", file=sys.stderr)
            for v in vals[:12]:
                await page.evaluate(_SET, [drv, v])
                await page.wait_for_timeout(1600)
                snap = await page.evaluate(_SNAP)
                result[drv]["values"][v] = snap
                print(f"  [{v[:26]:26}] ctrls={[r['label'] for r in snap]}", file=sys.stderr)
        (OUT / f"cond_{slug}.json").write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
        await b.close()


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1], sys.argv[2:] or ["design"]))
