"""Probe the live lo-loose-sheet form's VALIDITY behaviour: which controls are visible + their
options + hint/restriction notes, for different paper/size selections — so we can replicate
Excard's exact valid-combo space (conditional lamination, mutual exclusions, per-paper 1C, etc.).

  python -m app.loose_validity_probe
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from app import browser as B
from app.readymade_enum import login_v4

OUT = Path(__file__).resolve().parent.parent / "output"
V4 = "https://v4.excard.com.my/ordering/lo-loose-sheet"

# select a size + paper by matching option text, then read visible controls + notes
_SET = """(args) => {
  const [sizeRx, paperRx] = args;
  const pick = (nameRx, valRx) => {
    for (const sel of document.querySelectorAll('select')) {
      if (nameRx.test((sel.name||sel.id||'').toLowerCase())) {
        const i = [...sel.options].findIndex(o => valRx.test(o.text));
        if (i>=0){ sel.selectedIndex=i; sel.dispatchEvent(new Event('input',{bubbles:true})); sel.dispatchEvent(new Event('change',{bubbles:true})); return sel.options[i].text; }
      }
    }
    return null;
  };
  const s = pick(/size/, new RegExp(sizeRx));
  const p = pick(/paper/, new RegExp(paperRx));
  return {size:s, paper:p};
}"""

_READ = """() => {
  const vis = el => el && el.offsetParent!==null && el.getBoundingClientRect().height>1;
  const sections = [];
  let cur = null;
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  let node;
  const rows = [];
  while ((node = walk.nextNode())) {
    if (node.classList && node.classList.contains('bigtitle_Ord')) { cur = (node.textContent||'').trim(); continue; }
    if ((node.tagName==='SELECT' || (node.tagName==='INPUT' && /radio|checkbox/.test(node.type))) && vis(node)) {
      const g = node.closest('.form-group,.row,.mb-3,.field') || node.parentElement;
      const lab = g && g.querySelector('label,.control-label,b') ? g.querySelector('label,.control-label,b').textContent.trim() : (node.name||'');
      if (rows.length && rows[rows.length-1].label===lab) continue;
      let opts = [];
      if (node.tagName==='SELECT') opts = [...node.options].map(o=>o.text.trim()).filter(t=>t && !/^-|select/i.test(t));
      const note = (g && g.querySelector('small,.hint,.note,.text-muted,.help-block')) ? g.querySelector('small,.hint,.note,.text-muted,.help-block').textContent.trim() : '';
      rows.push({section:cur, label:lab.slice(0,40), opts:opts.slice(0,10), note:note.slice(0,180)});
    }
  }
  return rows;
}"""


async def snapshot(page, size_rx, paper_rx):
    picked = await page.evaluate(_SET, [size_rx, paper_rx])
    await page.wait_for_timeout(2500)
    rows = await page.evaluate(_READ)
    return {"picked": picked, "rows": rows}


async def run():
    out = {}
    async with async_playwright() as pw:
        b = await B.launch(pw)
        page = await b.new_page(viewport={"width": 1400, "height": 1800})
        await login_v4(page)
        await page.goto(V4, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(6000)
        for tag, (srx, prx) in {
            "A3_Simili": ("A3", "Simili.*100"),
            "A3_GlossArtPaper": ("A3", "Gloss Art Paper 100"),
            "A3_GlossArtCard": ("A3", "Gloss Art Card"),
            "A1_GlossArtCard": ("A1", "Gloss Art Card"),
        }.items():
            out[tag] = await snapshot(page, srx, prx)
            print(f"\n== {tag}: picked {out[tag]['picked']} ==", file=sys.stderr)
            for r in out[tag]["rows"]:
                if r["section"] in ("Optional Finishing", "General", "OPTIONAL FINISHING", "GENERAL"):
                    print(f"   [{r['section']}] {r['label']:20} opts={r['opts'][:6]}  note={r['note'][:90]}", file=sys.stderr)
        (OUT / "loose_validity.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        await b.close()


if __name__ == "__main__":
    asyncio.run(run())
