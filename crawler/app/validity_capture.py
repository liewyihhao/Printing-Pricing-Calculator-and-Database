"""Capture each product's CONDITIONAL validity from the live v4 form: which controls are visible
and what options they carry as the primary driver field(s) change — so we can replicate Excard's
exact valid-combo space, not just option presence.

Method (gentle, per the SPA-crash rules): load form, set every select to its first real option
(baseline), then for the first 1-2 driver selects iterate each of their values (others reset to
first) and record the visible controls + their options. Writes output/validity/<id>.json.

  python -m app.validity_capture            # all non-contact products (resumable)
  python -m app.validity_capture 21 1 123   # specific ids
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from app import browser as B
from app.readymade_enum import login_v4
from app.v4_form_capture import _candidates

OUT = Path(__file__).resolve().parent.parent / "output"
VDIR = OUT / "validity"
V4 = "https://v4.excard.com.my/ordering/"

# set one named select to a value (by option text); return the text set
_SETONE = """(args) => {
  const [name, valText] = args;
  for (const sel of document.querySelectorAll('select')) {
    if ((sel.name||sel.id) === name) {
      const i = [...sel.options].findIndex(o => o.text.trim() === valText);
      if (i>=0){ sel.selectedIndex=i; sel.dispatchEvent(new Event('input',{bubbles:true})); sel.dispatchEvent(new Event('change',{bubbles:true})); return valText; }
    }
  }
  return null;
}"""

# reset every select to its first real option; return list of driver selects (name, options)
_BASELINE = """() => {
  const drivers = [];
  for (const sel of document.querySelectorAll('select')) {
    const nm = sel.name||sel.id||'';
    if (/qty|quantity|country|courier|favourite|product$/i.test(nm)) continue;
    const opts = [...sel.options].map(o=>o.text.trim()).filter(t=>t && !/^-|please select/i.test(t));
    if (opts.length) {
      const i = [...sel.options].findIndex(o=>opts.includes(o.text.trim()));
      if (i>=0){ sel.selectedIndex=i; sel.dispatchEvent(new Event('input',{bubbles:true})); sel.dispatchEvent(new Event('change',{bubbles:true})); }
    }
    drivers.push({name: nm, options: opts});
  }
  return drivers;
}"""

# read visible config controls (section + options) — skip chrome
_SNAP = """() => {
  const vis = el => el && el.offsetParent!==null && el.getBoundingClientRect().height>1;
  const rows = [];
  let cur = null;
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
  let node;
  const SKIPSEC = /delivery|net price|add name|quantity|artwork|summary/i;
  while ((node = walk.nextNode())) {
    if (node.classList && node.classList.contains('bigtitle_Ord')) { cur=(node.textContent||'').trim(); continue; }
    if (!cur || SKIPSEC.test(cur)) continue;              // only within a real config section
    if ((node.tagName==='SELECT' || (node.tagName==='INPUT'&&/radio|checkbox/.test(node.type))) && vis(node)) {
      const nm = node.name||node.id||'';
      if (!nm || /qty|quantity|country|courier|favourite|product$|custom|review|filter/i.test(nm)) continue;
      const g = node.closest('.form-group,.row,.mb-3,.field')||node.parentElement;
      const lab = g&&g.querySelector('label,.control-label,b') ? g.querySelector('label,.control-label,b').textContent.trim() : nm;
      if (rows.length && rows[rows.length-1].label===lab) continue;
      let opts=[]; if(node.tagName==='SELECT') opts=[...node.options].map(o=>o.text.trim()).filter(t=>t && !/^-|please select/i.test(t));
      rows.push({section:cur, name:nm, label:lab.slice(0,40), opts:opts.slice(0,20)});
    }
  }
  return rows;
}"""


async def capture_product(page, prod):
    for slug in await _candidates(prod):
        try:
            await page.goto(V4 + slug, wait_until="domcontentloaded", timeout=45000)
        except Exception:
            continue
        await page.wait_for_timeout(5500)
        try:
            await page.evaluate(_BASELINE)
        except Exception:
            continue
        await page.wait_for_timeout(1500)
        try:
            base = await page.evaluate(_SNAP)
        except Exception:
            base = []
        if not base:
            continue
        # drivers = the config-cascade selects others depend on (General-section selects with >=2
        # options), e.g. paper / size / category / model. Vary the first 3.
        varying = [r for r in base if r.get("opts") and len(r["opts"]) >= 2
                   and "general" in (r.get("section", "").lower())][:2]
        variations = {}
        for d in varying:
            variations[d["name"]] = {"label": d["label"], "values": {}}
            for val in d["opts"][:16]:
                try:
                    await page.evaluate(_BASELINE)                 # reset others to first
                    await page.wait_for_timeout(350)
                    await page.evaluate(_SETONE, [d["name"], val])
                    await page.wait_for_timeout(1100)
                    snap = await page.evaluate(_SNAP)
                except Exception:
                    snap = []
                variations[d["name"]]["values"][val] = snap
        return {"slug": slug, "baseline": base, "drivers": [d["name"] for d in varying], "variations": variations}
    return {"slug": None, "baseline": [], "variations": {}, "error": "no form"}


async def run(ids=None):
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))["products"]
    if ids:
        idset = {int(i) for i in ids}
        data = [p for p in data if p["id"] in idset]
    VDIR.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        b = await B.launch(pw)
        page = await b.new_page(viewport={"width": 1400, "height": 2000})
        await login_v4(page)
        for i, p in enumerate(data):
            if p.get("engine") == "contact":
                continue
            f = VDIR / f"{p['id']}.json"
            if f.is_file() and not ids:                    # resumable
                continue
            try:
                info = await capture_product(page, p)
            except Exception as e:
                info = {"slug": None, "baseline": [], "variations": {}, "error": str(e)[:100]}
            info["id"] = p["id"]; info["name"] = p["name"]
            f.write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
            nd = len(info.get("variations", {}))
            print(f"[{i+1}/{len(data)}] id{p['id']:>3} {p['name'][:30]:30} slug={info.get('slug')} "
                  f"drivers={info.get('drivers')} base={len(info.get('baseline',[]))}", file=sys.stderr)
        await b.close()


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1:] or None))
