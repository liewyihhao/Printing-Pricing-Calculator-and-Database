"""Sample Wire-O Notebook Exclusive Leather Cover prices.

ELC has distinct controls vs the other covers:
  rblModel     : Exclusive Brown / Exclusive Silver Brown / Exclusive Grey
  ddlIFCPaperMaterial: Simili 80gsm / Gloss Art Paper 100gsm
  rblAddonProcess: No Finishing / Deboss / Stickering
  ddlQty       : starts at 30 (min qty)
  No ddlCoverLamination (it's hidden for ELC)

  python -m app.wireo_elc_sampler [account]
"""
from __future__ import annotations
import asyncio, json, re, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .logging_setup import log

OUT = Path(__file__).resolve().parent.parent / "output"
URL = "https://www.excard.com.my/spec/Litho/Wire-O_Notebook"
MODELS = ["Exclusive Brown", "Exclusive Silver Brown", "Exclusive Grey"]
IFC_PAPERS = ["Simili 80gsm", "Gloss Art Paper 100gsm"]
ADDONS = ["No Finishing", "Deboss", "Stickering"]
QTYS = [30, 50, 100, 200, 300, 500, 1000, 3000]


def _parse_price(txt: str) -> float | None:
    """Extract 'PRICE BEFORE DISCOUNT RM X.XX' from page body text."""
    m = re.search(r"PRICE BEFORE DISCOUNT\s+RM\s*([\d,]+\.\d+)", txt)
    if m:
        return float(m.group(1).replace(",", ""))
    return None


async def _wait_idle(page):
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass
    await asyncio.sleep(0.4)


async def _click_radio(page, name, value):
    loc = page.locator(f"input[name$='{name}']")
    n = await loc.count()
    for i in range(n):
        if (await loc.nth(i).get_attribute("value")) == value:
            try:
                await loc.nth(i).check()
            except Exception:
                await page.evaluate("(el)=>el.click()", await loc.nth(i).element_handle())
            await _wait_idle(page)
            return True
    return False


async def _select(page, name, value):
    loc = page.locator(f"select[name$='{name}']")
    if not await loc.count():
        return False
    try:
        await loc.first.select_option(value)
        await _wait_idle(page)
        return True
    except Exception:
        return False


async def _read_price(page) -> float | None:
    txt = await page.evaluate("()=>document.body.innerText")
    return _parse_price(txt)


async def run(account_id=1):
    a = accounts.get(account_id)
    file = OUT / "wireo_elc_samples.json"
    existing = json.loads(file.read_text()) if file.exists() else []
    done_keys = {(r["model"], r["ifc"], r["addon"]) for r in existing}

    results = list(existing)
    async with async_playwright() as pw:
        b = await launch(pw)
        ctx = await b.new_context(viewport={"width": 1440, "height": 1500})
        page = await ctx.new_page()
        await login(page, username=a.username, password=a.password)

        for model in MODELS:
            for ifc in IFC_PAPERS:
                for addon in ADDONS:
                    if (model, ifc, addon) in done_keys:
                        log.info("wireo_elc.skip", model=model, ifc=ifc, addon=addon)
                        continue

                    # Fresh page per combo to avoid stale state
                    await page.goto(URL, wait_until="domcontentloaded")
                    await asyncio.sleep(1.2)

                    if not await _click_radio(page, "rblOrderDesc", "Exclusive Leather Cover"):
                        log.warning("wireo_elc.fail_elc"); continue
                    await asyncio.sleep(0.6)

                    if not await _click_radio(page, "rblModel", model):
                        log.warning("wireo_elc.fail_model", model=model); continue
                    await asyncio.sleep(0.4)

                    if not await _select(page, "ddlIFCPaperMaterial", ifc):
                        log.warning("wireo_elc.fail_ifc", ifc=ifc); continue
                    await asyncio.sleep(0.4)

                    if not await _click_radio(page, "rblAddonProcess", addon):
                        log.warning("wireo_elc.fail_addon", addon=addon); continue
                    await asyncio.sleep(0.4)

                    combo_rows = []
                    prev_cash = None
                    for q in QTYS:
                        if not await _select(page, "ddlQty", str(q)):
                            log.info("wireo_elc.qty_na", q=q); continue
                        await asyncio.sleep(1.5)
                        cash = await _read_price(page)
                        if cash and cash != prev_cash and cash > 0:
                            combo_rows.append({"model": model, "ifc": ifc, "addon": addon,
                                               "qty": q, "cash": cash})
                            prev_cash = cash
                            log.info("wireo_elc.pt", model=model[:12], ifc=ifc[:10],
                                     addon=addon[:12], qty=q, cash=cash)
                        elif cash == prev_cash:
                            log.info("wireo_elc.same", qty=q, cash=cash)
                        else:
                            log.warning("wireo_elc.no_price", qty=q)

                    results.extend(combo_rows)
                    file.write_text(json.dumps(results, indent=0))
                    log.info("wireo_elc.combo_done", model=model, ifc=ifc, addon=addon,
                             pts=len(combo_rows))

        try:
            await b.close()
        except Exception:
            pass

    file.write_text(json.dumps(results, indent=0))
    print(f"wrote {file.name}: {len(results)} rows "
          f"({len(MODELS)*len(IFC_PAPERS)*len(ADDONS)} combos x {len(QTYS)} qtys)")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
