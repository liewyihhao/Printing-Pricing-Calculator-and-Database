"""Full configuration audit for a product's Excard ordering page.

Phase 1 (enumerate): drive the v4 /ordering/<slug> page and extract EVERY configuration
control in DOM order — from the first field down through Finishing to the Delivery section —
with its section heading, label, control type, and full option list. Nothing is skipped.
This is read-only (no CheckPrice) so it is safe to run while a sampler is active.

Phase 2 (price relationships) lives in each product's sampler / probe: for every enumerated
control we toggle its values against a base config via CheckPrice and record the delta, then
classify PRICE-AXIS vs NEUTRAL. (Run only when no other CheckPrice job is active — the API is
not concurrency-safe.)

  python -m app.option_audit bill-book label-sticker roll-form-sticker ...
Writes output/option_audit/<slug>.json
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from app import browser as B
from app.readymade_enum import login_v4

OUT = Path(__file__).resolve().parent.parent / "output" / "option_audit"
OUT.mkdir(parents=True, exist_ok=True)
V4 = "https://v4.excard.com.my/ordering/"

# Extract every control (select / radio-group / checkbox / text|number input) in DOM order,
# tagging each with the nearest preceding section heading, and whether it is currently visible.
_JS = r"""() => {
  const out = [];
  const headThemes = ['General','Layers','Print','Colour','Color','Quantity','Finishing',
    'Delivery','Paper','Size','Binding','Cover','Content','Lamination','Option','Shipping','Address'];
  // walk the whole document in order
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT, null);
  let section = '(top)';
  const seenRadio = {};
  const norm = t => (t||'').replace(/\s+/g,' ').trim();
  const labelFor = el => {
    // nearest label: <label for=id>, wrapping label, or preceding text cell
    if (el.id){ const l=document.querySelector(`label[for="${el.id}"]`); if(l) return norm(l.innerText); }
    let p = el.closest('tr,.form-group,.row,.field,div');
    for (let i=0;i<4 && p;i++){ const lb=p.querySelector('label,th,.label'); if(lb && !lb.contains(el)) return norm(lb.innerText); p=p.parentElement; }
    return norm((el.name||el.id||'').split('$').pop());
  };
  let node = walker.currentNode;
  while (node) {
    const tag = node.tagName;
    // section heading detection: short bold/section-styled text
    const txt = norm(node.innerText);
    if (node.children.length<=2 && txt && txt.length<40 &&
        (/(^|\b)(General|Layers Configuration|Print Colou?r|Quantity|Finishing|Delivery|Paper|Binding|Options?)\b/i.test(txt)) &&
        (getComputedStyle(node).backgroundColor!=='rgba(0, 0, 0, 0)' || /section|title|heading|panel-head/i.test(node.className))) {
      section = txt;
    }
    if (tag==='SELECT') {
      if(!/^__|viewstate/i.test(node.name||'')){
        out.push({section, type:'select', label:labelFor(node), name:(node.name||node.id||'').split('$').pop(),
          visible: !!node.offsetParent, n: node.options.length,
          options:[...node.options].map(o=>norm(o.text)).filter(Boolean)});
      }
    } else if (tag==='INPUT') {
      const t=(node.type||'').toLowerCase();
      if (t==='radio') {
        const nm=node.name; if(seenRadio[nm]) { node=walker.nextNode(); continue; } seenRadio[nm]=1;
        const grp=[...document.querySelectorAll(`input[type=radio][name="${nm.replace(/"/g,'\\"')}"]`)];
        out.push({section, type:'radio', label:labelFor(node), name:(nm||'').split('$').pop(),
          visible: grp.some(r=>r.offsetParent),
          options: grp.map(r=>{const l=document.querySelector(`label[for="${r.id}"]`); return norm(l?l.innerText:r.value);})});
      } else if (t==='checkbox') {
        out.push({section, type:'checkbox', label:labelFor(node), name:(node.name||'').split('$').pop(), visible:!!node.offsetParent});
      } else if (t==='text'||t==='number'||t===''){
        if(!/^__|viewstate|search|track/i.test(node.name||node.id||''))
          out.push({section, type:'input', label:labelFor(node), name:(node.name||node.id||'').split('$').pop(),
            visible:!!node.offsetParent, placeholder:norm(node.placeholder)});
      }
    } else if (tag==='TEXTAREA') {
      out.push({section, type:'textarea', label:labelFor(node), name:(node.name||'').split('$').pop(), visible:!!node.offsetParent});
    }
    node = walker.nextNode();
  }
  return out;
}"""


async def enumerate_page(page, slug):
    info = {"slug": slug, "url": None, "error": None, "controls": []}
    try:
        await page.goto(V4 + slug, wait_until="networkidle", timeout=45000)
    except Exception as e:
        info["error"] = "goto:" + str(e)[:100]
    await page.wait_for_timeout(4000)
    info["url"] = page.url
    body = await page.evaluate("() => document.body ? document.body.innerText.slice(0,120) : ''")
    if "Runtime Error" in body or "Server Error" in body:
        info["error"] = "v4 page 500 (Runtime Error) — use www /spec form for this product"
        return info
    try:
        info["controls"] = await page.evaluate(_JS)
    except Exception as e:
        info["error"] = "enum:" + str(e)[:120]
    return info


async def run(slugs):
    async with async_playwright() as pw:
        b = await B.launch(pw)
        page = await b.new_page()
        await login_v4(page)
        for slug in slugs:
            info = await enumerate_page(page, slug)
            (OUT / f"{slug}.json").write_text(json.dumps(info, indent=1))
            secs = {}
            for c in info["controls"]:
                secs.setdefault(c["section"], 0)
                secs[c["section"]] += 1
            print(f"[{slug}] err={info['error']} controls={len(info['controls'])} sections={secs}", file=sys.stderr)
        await b.close()


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1:] or ["bill-book"]))
