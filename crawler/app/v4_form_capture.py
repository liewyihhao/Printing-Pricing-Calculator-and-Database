"""Capture each product's LIVE v4 order-form structure — the ground truth the www-based audits
can't see. For every product: the section each control sits under (General / Optional Finishing /
Add On / Delivery, from the teal `.bigtitle_Ord` headers), every control + its options, and which
options carry an image. Writes output/v4_form/<id>.json.

  python -m app.v4_form_capture            # all products
  python -m app.v4_form_capture 21 50 123  # specific product ids
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from app import browser as B
from app.readymade_enum import login_v4
from app.product_quantity import _base_slug, _ALIAS

OUT = Path(__file__).resolve().parent.parent / "output"
FDIR = OUT / "v4_form"
V4 = "https://v4.excard.com.my/ordering/"

# v4 ordering slug overrides where it differs from our base slug (verified from the live site).
_V4_SLUG = {
    "loose-sheet": "lo-loose-sheet", "brochure": "lo-loose-sheet", "flyer": "lo-loose-sheet",
    "customprint": "lo-loose-sheet",
}
# Per-product-id slug overrides (two products can share a base slug, e.g. desk-calendar variants).
_V4_SLUG_BY_ID = {
    110: "voucher-pad", 120: "hard-stand-desk-calendar", 121: "soft-stand-desk-calendar",
    145: "dtf-totebag-with-zip", 152: "standing-pouch-spout", 182: "muslimah",
    19: "bo-booklet", 37: "bo-booklet",
}

# Gently set every select to its first real option (reveals the cascade + conditional sections)
# and turn on any "Required" finishing radio — via native events (Playwright select_option crashes
# this SPA).
_REVEAL = r"""() => {
  for (const sel of document.querySelectorAll('select')) {
    const opts=[...sel.options].map(o=>o.text.trim());
    let i=opts.findIndex(t=>t && !/select|please|^-+$/i.test(t) && t!=='-');
    if (i>0){ sel.selectedIndex=i; sel.dispatchEvent(new Event('input',{bubbles:true})); sel.dispatchEvent(new Event('change',{bubbles:true})); }
  }
  for (const inp of document.querySelectorAll('input[type=radio]')) {
    const lab=(inp.closest('label')?.textContent || document.querySelector(`label[for='${inp.id}']`)?.textContent || inp.parentElement?.textContent || '').trim();
    if (/^required$/i.test(lab)){ inp.click(); inp.checked=true; inp.dispatchEvent(new Event('change',{bubbles:true})); }
  }
  return true;
}"""

# Extract sections (from .bigtitle_Ord) + controls in DOM order, assigning each control to the
# section header that precedes it. Options come from <select>, radio/checkbox groups, and custom
# image-picker cards (data-* / captioned cards). Records whether each option has an image.
_EXTRACT = r"""() => {
  const vis = el => { if(!el) return false; if(el.offsetParent===null && getComputedStyle(el).position!=='fixed') return false;
    const r=el.getBoundingClientRect(); return r.width>1 && r.height>1; };
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  const rows = [];
  const seenGroup = new Set();
  let node;
  while ((node = walk.nextNode())) {
    if (node.classList && node.classList.contains('bigtitle_Ord')) {
      const t=(node.textContent||'').trim();
      if (t && t.length<40) rows.push({kind:'section', name:t});
      continue;
    }
    const tag=node.tagName;
    if ((tag==='SELECT' || tag==='INPUT') && !vis(node)) continue;   // only VISIBLE config controls
    if (tag==='SELECT') {
      const g = node.closest('.form-group,.row,.mb-3,.field') || node.parentElement;
      const lab = (g && g.querySelector('label,.control-label,b,h5,h6')) ? g.querySelector('label,.control-label,b,h5,h6').textContent.trim() : (node.name||'');
      const opts=[...node.options].map(o=>o.text.trim()).filter(t=>t && !/^-+$/.test(t) && !/please select|^select /i.test(t));
      rows.push({kind:'control', ctype:'select', name:node.name||node.id||'', label:lab.slice(0,60), options:opts});
    } else if ((tag==='INPUT') && (node.type==='radio'||node.type==='checkbox')) {
      const grp = node.name || node.id;
      if (node.type==='radio' && seenGroup.has(grp)) continue;
      if (node.type==='radio') seenGroup.add(grp);
      // group label = nearest preceding label/heading outside the option list
      const box = node.closest('.form-group,.row,.mb-3,.field') || node.parentElement;
      const lab = (box && box.querySelector('label,.control-label,b,h5,h6')) ? box.querySelector('label,.control-label,b,h5,h6').textContent.trim() : grp;
      let opts=[];
      if (node.type==='radio') {
        opts=[...document.querySelectorAll(`input[type=radio][name='${grp}']`)].map(r=>{
          const l=(r.closest('label')?.textContent || document.querySelector(`label[for='${r.id}']`)?.textContent || r.parentElement?.textContent || '').trim();
          return l; }).filter(Boolean);
      } else {
        const l=(node.closest('label')?.textContent || document.querySelector(`label[for='${node.id}']`)?.textContent || '').trim();
        opts=[l||grp];
      }
      rows.push({kind:'control', ctype:node.type, name:grp, label:lab.slice(0,60), options:opts});
    }
  }
  // custom image-picker card grids (folding codes, colour swatches, model pictures): captioned
  // cards not tied to a <select>. Capture caption + whether it has an <img>/<svg>.
  const cards=[];
  for (const el of document.querySelectorAll('.custom-creasing-panel__item, .folding-item, [data-foldcode], .colour-item, .model-card, .shirt-model-card')) {
    const cap=(el.textContent||'').trim().slice(0,40);
    if (cap) cards.push({caption:cap, hasImg:!!el.querySelector('img'), hasSvg:!!el.querySelector('svg')});
  }
  const sectionCount = rows.filter(r=>r.kind==='section').length;
  return {rows, cards, sectionCount};
}"""


async def _candidates(prod):
    base = _base_slug(prod["name"])
    seen, out = set(), []
    for s in (_V4_SLUG_BY_ID.get(prod["id"]), _V4_SLUG.get(base), base, _ALIAS.get(base, base)):
        if s and s not in seen:
            seen.add(s); out.append(s)
    return out


async def capture_one(page, prod):
    for slug in await _candidates(prod):
        try:
            await page.goto(V4 + slug, wait_until="domcontentloaded", timeout=45000)
        except Exception:
            continue
        await page.wait_for_timeout(5500)
        try:
            await page.evaluate(_REVEAL)
        except Exception:
            pass
        await page.wait_for_timeout(3000)
        try:
            info = await page.evaluate(_EXTRACT)
        except Exception as e:
            info = {"rows": [], "cards": [], "sectionCount": 0, "error": str(e)[:80]}
        if info.get("sectionCount", 0) >= 1:
            info["slug"] = slug
            return info
    return {"rows": [], "cards": [], "sectionCount": 0, "slug": None, "error": "no form rendered"}


async def run(ids=None):
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))["products"]
    if ids:
        idset = {int(i) for i in ids}
        data = [p for p in data if p["id"] in idset]
    FDIR.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        b = await B.launch(pw)
        page = await b.new_page(viewport={"width": 1500, "height": 2400})
        await login_v4(page)
        for i, p in enumerate(data):
            if p.get("engine") == "contact":
                continue
            try:
                info = await capture_one(page, p)
            except Exception as e:
                info = {"rows": [], "cards": [], "sectionCount": 0, "error": str(e)[:100]}
            info["id"] = p["id"]; info["name"] = p["name"]
            (FDIR / f"{p['id']}.json").write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding="utf-8")
            secs = [r["name"] for r in info.get("rows", []) if r.get("kind") == "section"]
            nctrl = sum(1 for r in info.get("rows", []) if r.get("kind") == "control")
            print(f"[{i+1}/{len(data)}] id{p['id']:>3} {p['name'][:30]:30} slug={info.get('slug')} "
                  f"sections={secs} controls={nctrl} cards={len(info.get('cards',[]))}", file=sys.stderr)
        await b.close()


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1:] or None))
