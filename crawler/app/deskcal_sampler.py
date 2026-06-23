"""Sample Desk Calendar prices (Hard Stand + Soft Stand).

Hard Stand: rdCategory (3 models) x rdModel (8/16/24 sheets) x qty
Soft Stand: qty only (Wire-O with cardboard cover)

  python -m app.deskcal_sampler [account]

Saves output/deskcal_samples.json:
  {"hard": [{cat, model, sheets, qty, cash}], "soft": [{qty, cash}]}
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .logging_setup import log
from .billbook_sampler import _sel, _safe_read, _wait, _radio

OUT = Path(__file__).resolve().parent.parent / "output"
HARD_URL = "https://www.excard.com.my/spec/Litho/Desk_Calendar_(Hard_Stand)"
SOFT_URL = "https://www.excard.com.my/spec/Litho/Desk_Calendar_(Soft_Stand)"

HARD_CATS = [("1", "WDCH 001 (Portrait)"), ("2", "WDCH 002 (Landscape)"), ("3", "DCHS 001 (Hot Stamping - Portrait)")]
HARD_QTYS = [10, 20, 30, 40, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 3000, 4000]
SOFT_QTYS = [100, 200, 300, 500, 1000, 1500, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]


async def _get_models(page):
    """Get rdModel radio options (value, label) from current page."""
    return await page.evaluate(
        "() => { var out = [];"
        " var rs = document.querySelectorAll('input[type=radio][name$=rdModel]');"
        " for (var i=0; i<rs.length; i++) {"
        "   if (!rs[i].offsetParent) continue;"
        "   var p = rs[i].closest('label') || rs[i].parentElement;"
        "   var lbl = p ? p.innerText.trim() : rs[i].value;"
        "   out.push({value: rs[i].value, label: lbl});"
        " }"
        " return out; }"
    )


async def sample_hard(page, data: dict):
    # Hard Stand: rdCategory (1=Portrait, 2=Landscape, 3=HotStamping-Portrait) x comboQty
    # No rdModel on this form — category IS the model.
    for cat_val, cat_label in HARD_CATS:
        await page.goto(HARD_URL, wait_until="domcontentloaded")
        await _wait(page); await asyncio.sleep(1.5)
        if not await _radio(page, "rdCategory", cat_val):
            log.warning("deskcal.hard.cat_fail", cat=cat_val); continue
        await asyncio.sleep(1.0)
        prev = None
        for q in HARD_QTYS:
            if any(r["cat"] == cat_val and r["qty"] == q for r in data["hard"]):
                prev = next((r["cash"] for r in data["hard"] if r["cat"] == cat_val and r["qty"] == q), prev)
                continue
            if not await _sel(page, "comboQty", str(q)):
                log.warning("deskcal.hard.qty_fail", cat=cat_val, qty=q); continue
            # Each qty has a distinct price; poll until the price actually CHANGES off the
            # previous qty's value (guards against reading the pre-AJAX stale price).
            c = None
            for _ in range(12):
                await asyncio.sleep(0.7)
                c = (await _safe_read(page)).get("before_discount")
                if c is not None and (prev is None or c != prev):
                    break
            if not c:
                log.warning("deskcal.hard.no_price", cat=cat_val, qty=q); continue
            rec = {"cat": cat_val, "cat_label": cat_label, "qty": q, "cash": c}
            data["hard"].append(rec); prev = c
            log.info("deskcal.hard", cat=cat_val, qty=q, cash=c)


async def sample_soft(page, data: dict):
    await page.goto(SOFT_URL, wait_until="domcontentloaded")
    await _wait(page); await asyncio.sleep(1.5)
    for q in SOFT_QTYS:
        if any(r["qty"] == q for r in data["soft"]):
            continue
        if not await _sel(page, "comboQty", str(q)):
            log.warning("deskcal.soft.qty_fail", qty=q); continue
        await asyncio.sleep(1.0)
        r = await _safe_read(page)
        c = r.get("before_discount")
        if not c:
            log.warning("deskcal.soft.no_price", qty=q); continue
        data["soft"].append({"qty": q, "cash": c})
        log.info("deskcal.soft", qty=q, cash=c)


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "deskcal_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"hard": [], "soft": []}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1600})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        await sample_hard(page, data)
        out.write_text(json.dumps(data, indent=0))
        await sample_soft(page, data)
        out.write_text(json.dumps(data, indent=0))
        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"hard={len(data['hard'])} soft={len(data['soft'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
