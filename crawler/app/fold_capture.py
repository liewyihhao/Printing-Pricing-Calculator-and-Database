"""Capture the loose-sheet FOLDING CODE diagrams from the v4 SPA order form. Each fold code
(1Fa, 2Fa, …) shows a dieline diagram in the "Optional Finishing" section once a Size is picked.
It's JS-rendered, so we set Size via light JS events, then screenshot each fold card by its
bounding box. img_cache embeds the PNGs as data: URIs; build_standalone wires them on the field.

  python -m app.fold_capture <v4-slug>          # e.g. lo-loose-sheet
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from app import browser as B
from app.readymade_enum import login_v4

OUT = Path(__file__).resolve().parent.parent / "output"
V4 = "https://v4.excard.com.my/ordering/"

# Set the earliest cascade selects (Size, Paper, Print Colour) to their first real option via
# native value + change/input events (lighter than Playwright select_option, which crashed the SPA).
_SET_SELECTS = r"""() => {
  const done = [];
  for (const sel of document.querySelectorAll('select')) {
    const opts = [...sel.options].map(o => o.text.trim());
    // Prefer an A4 size (matches the reference diagrams); else the first real option.
    let idx = opts.findIndex(t => /\bA4\b/.test(t));
    if (idx < 0) idx = opts.findIndex(t => t && !/select/i.test(t) && t !== '-' && !/not required/i.test(t));
    if (idx > 0) {
      sel.selectedIndex = idx;
      sel.dispatchEvent(new Event('input', {bubbles:true}));
      sel.dispatchEvent(new Event('change', {bubbles:true}));
      done.push((sel.name || sel.id || '') + '=' + opts[idx]);
    }
  }
  return done;
}"""

_FIND_CARDS = r"""() => {
  const codeRe = /^\s*(\d[Ff][a-d])\s*[—-]\s*[A-Za-z]/;
  const res = []; const seen = new Set();
  for (const el of document.querySelectorAll('div,figure,li,label')) {
    const t = (el.textContent||'').trim();
    const m = t.match(codeRe);
    if (!m || t.length > 60 || seen.has(m[1])) continue;
    let card = el;
    for (let k=0;k<5 && card.parentElement;k++){
      const r = card.getBoundingClientRect();
      if (r.width>=120 && r.width<=420 && r.height>=120) break;
      card = card.parentElement;
    }
    const r = card.getBoundingClientRect();
    if (r.width < 60 || r.height < 60) continue;
    seen.add(m[1]);
    res.push({code:m[1], x:r.left+scrollX, y:r.top+scrollY, w:r.width, h:r.height});
  }
  return res;
}"""


async def capture(page, slug):
    await page.goto(V4 + slug, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(6000)
    try:
        done = await page.evaluate(_SET_SELECTS)
        print("set selects:", done[:8], file=sys.stderr)
    except Exception as e:
        print("set selects failed:", str(e)[:80], file=sys.stderr)
    await page.wait_for_timeout(3000)
    # Turn ON Folding Type = Required (a radio) so the fold-code grid becomes visible.
    try:
        clicked = await page.evaluate(r"""() => {
          for (const inp of document.querySelectorAll('input[type=radio]')) {
            const lab = (inp.closest('label')?.textContent ||
                         document.querySelector(`label[for='${inp.id}']`)?.textContent ||
                         inp.parentElement?.textContent || '').trim();
            if (/^required$/i.test(lab)) {
              inp.click();
              inp.checked = true;
              inp.dispatchEvent(new Event('change', {bubbles:true}));
              return lab;
            }
          }
          return null;
        }""")
        print("folding required clicked:", clicked, file=sys.stderr)
    except Exception as e:
        print("required click failed:", str(e)[:80], file=sys.stderr)
    await page.wait_for_timeout(3500)
    cards = await page.evaluate(_FIND_CARDS)
    print(f"fold cards: {[c['code'] for c in cards]}", file=sys.stderr)
    ddir = OUT / "fold_diagrams" / slug
    ddir.mkdir(parents=True, exist_ok=True)
    saved = {}
    for c in cards:
        try:
            clip = {"x": max(0, c["x"]), "y": max(0, c["y"]), "width": c["w"], "height": c["h"]}
            p = ddir / f"{c['code']}.png"
            await page.screenshot(path=str(p), clip=clip)
            saved[c["code"]] = str(p.relative_to(OUT))
        except Exception as e:
            print(f"  {c['code']}: {str(e)[:60]}", file=sys.stderr)
    (OUT / f"fold_diagrams_{slug}.json").write_text(
        json.dumps(saved, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"saved {len(saved)} -> output/fold_diagrams/{slug}/", file=sys.stderr)


async def run(slug):
    async with async_playwright() as pw:
        b = await B.launch(pw)
        page = await b.new_page(viewport={"width": 1500, "height": 3200})
        await login_v4(page)
        await capture(page, slug)
        await b.close()


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1] if len(sys.argv) > 1 else "lo-loose-sheet"))
