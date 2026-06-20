"""Sample Envelope (Litho) prices.

Drivers: MODEL (rblMould — 17 envelope moulds, image radios; code encodes size + window
NW/W), PRINT COLOUR/side (12), QUANTITY (1000..20000). Compulsory: Die-Cutting, Folding +
Gluing (included). Decomposition to keep the crawl tractable:
  * core:   each model x 4C(Front) over the full qty ladder  -> per-model base curve
  * colour: representative model x all 12 colours at {1000, 5000} -> colour factor vs 4C(Front)
  * check:  a 2nd model x a few colours to confirm the factor is model-independent

Saves output/envelope_samples.json:
  {"core":[{model,size,colour,qty,cash}], "colour":[{model,colour,qty,cash}], "check":[...]}

  python -m app.envelope_sampler [account]
"""
from __future__ import annotations
import asyncio, json, sys, re
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .logging_setup import log
from .billbook_sampler import _sel, _safe_read, _wait, _opts

OUT = Path(__file__).resolve().parent.parent / "output"
URL = "https://www.excard.com.my/spec/Litho/Envelope"
# (id_prefix, code) from rblMould radio values
MODELS = [("452", "OE4496NW"), ("453", "OE4496W"), ("454", "OE9013NW"), ("12", "EV4090NW"),
          ("13", "EV4090W"), ("14", "EV4286NW"), ("15", "EV4286W"), ("16", "EV4496NW"),
          ("17", "EV4496W"), ("18", "EV6390NW"), ("19", "EV7010NW"), ("21", "EV9013NW"),
          ("22", "EV1015NW"), ("95", "IS4286NW"), ("96", "IS6390NW"), ("98", "OP8642NW"),
          ("100", "OP6344NW")]
COLOURS = ["1C (Front)", "1C (Both)", "1C (Front)/2C (Back)", "1C (Front)/4C (Back)",
           "2C (Front)", "2C (Front)/1C (Back)", "2C (Both)", "2C (Front)/4C (Back)",
           "4C (Front)", "4C (Front)/1C (Back)", "4C (Front)/2C (Back)", "4C (Both)"]
QTYS = [1000, 2000, 3000, 4000, 5000, 10000, 15000, 20000]
REF_MODEL = ("16", "EV4496NW")   # representative for the colour factor table
CHK_MODEL = ("21", "EV9013NW")   # 2nd model to validate factor model-independence


async def _select_mould(page, pfx):
    ok = await page.evaluate(
        r"""(pfx)=>{const rs=[...document.querySelectorAll("input[name$='rblMould']")];
            const r=rs.find(x=>x.value.startsWith(pfx+","));if(!r)return false;r.click();return true;}""", pfx)
    await _wait(page); await asyncio.sleep(1.5)
    return ok


async def _size(page):
    txt = await page.evaluate("()=>document.body.innerText")
    m = re.search(r"Size\s*\t?\s*(\d+\s*mm\s*x\s*\d+\s*mm)", txt)
    return m.group(1).replace(" ", "") if m else ""


async def _config(page, pfx, colour):
    await page.goto(URL, wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.8)
    if not await _select_mould(page, pfx):
        return None
    for _ in range(8):  # colour select appears after mould postback
        if await page.locator("select[name$='rblPrintColourSide']").count():
            break
        await asyncio.sleep(0.5)
    if not await _sel(page, "rblPrintColourSide", colour):
        return None
    await asyncio.sleep(0.8)
    return await _size(page)


async def _sweep(page, qtys):
    res = {}; prev = None
    for q in qtys:
        if not await _sel(page, "comboQty", str(q)):
            continue
        await asyncio.sleep(1.0)
        c = (await _safe_read(page)).get("before_discount")
        if c and c != prev:
            res[q] = c; prev = c
        elif c == prev:
            await _sel(page, "comboQty", str(qtys[0])); await _sel(page, "comboQty", str(q))
            await asyncio.sleep(1.0); c = (await _safe_read(page)).get("before_discount")
            if c:
                res[q] = c; prev = c
    return res


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "envelope_samples.json"
    data = json.loads(out.read_text()) if out.exists() else {"core": [], "colour": [], "check": []}
    core_done = {r["model"] for r in data["core"]
                 if sum(1 for x in data["core"] if x["model"] == r["model"]) >= 6}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1600})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        # 1) CORE: each model x 4C(Front) over qty ladder
        for pfx, code in MODELS:
            if code in core_done:
                continue
            size = await _config(page, pfx, "4C (Front)")
            if size is None:
                log.info("env.cfg_fail", model=code); continue
            res = await _sweep(page, QTYS)
            for q, c in res.items():
                data["core"].append({"model": code, "size": size, "colour": "4C (Front)", "qty": q, "cash": c})
            out.write_text(json.dumps(data, indent=0)); log.info("env.core", model=code, size=size, n=len(res))

        # 2) COLOUR factor table on REF model at {1000, 5000}
        if not data["colour"]:
            for colour in COLOURS:
                size = await _config(page, REF_MODEL[0], colour)
                if size is None:
                    continue
                res = await _sweep(page, [1000, 5000])
                for q, c in res.items():
                    data["colour"].append({"model": REF_MODEL[1], "colour": colour, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("env.colour", colour=colour, n=len(res))

        # 3) CHECK colour-factor model-independence on a 2nd model (subset)
        if not data["check"]:
            for colour in ["1C (Front)", "2C (Front)", "4C (Both)"]:
                size = await _config(page, CHK_MODEL[0], colour)
                if size is None:
                    continue
                res = await _sweep(page, [1000, 5000])
                for q, c in res.items():
                    data["check"].append({"model": CHK_MODEL[1], "colour": colour, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("env.check", colour=colour, n=len(res))

        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: core={len(data['core'])} colour={len(data['colour'])} check={len(data['check'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
