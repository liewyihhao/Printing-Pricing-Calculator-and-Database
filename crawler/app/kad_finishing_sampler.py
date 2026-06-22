"""Sample the FINISHING dimensions the parity checker flagged as missing on the Kad
products: Lamination (Matte/Gloss x Front/Both) for both Kad Kahwin & Kad Terima Kasih,
and Envelope (White/Pink) for Kad Kahwin. Captured at each product's reference config so
they can be added as factors/deltas. Hot stamping stays a block charge (quoted separately).

Saves output/kad_finishing.json: {kadkahwin:{lamination:[...],envelope:[...]}, kadterima:{lamination:[...]}}

  python -m app.kad_finishing_sampler [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .logging_setup import log
from .billbook_sampler import _sel, _safe_read, _wait

OUT = Path(__file__).resolve().parent.parent / "output"
LAMS = ["Matte Lamination (Front)", "Matte Lamination (Both)",
        "Gloss Lamination (Front)", "Gloss Lamination (Both)"]
QTYS = [100, 500]

KAHWIN = dict(url="https://www.excard.com.my/spec/Digital/Kad_Kahwin",
              size="A5 (148mm x 210mm)", paper="Gloss Art Card 260gsm (2 sides coated)")
TERIMA = dict(url="https://www.excard.com.my/spec/Digital/kad_Terima_Kasih",
              size="52mm x 52mm", paper="Gloss Art Card 260gsm (2 sides coated)")


async def _radio(page, name, value):
    loc = page.locator(f"input[name$='{name}']"); n = await loc.count()
    for i in range(n):
        if (await loc.nth(i).get_attribute("value")) == value:
            try:
                await loc.nth(i).check()
            except Exception:
                await page.evaluate("(el)=>el.click()", await loc.nth(i).element_handle())
            await _wait(page); await asyncio.sleep(0.7); return True
    return False


async def _base(page, cfg, kahwin=False):
    await page.goto(cfg["url"], wait_until="domcontentloaded"); await _wait(page); await asyncio.sleep(0.8)
    if kahwin:
        await _radio(page, "rblOrderType", "1,Standard Kad Kahwin")
    if not await _sel(page, "ddlSize", cfg["size"]):
        return False
    if not await _sel(page, "ddlPaper", cfg["paper"]):
        return False
    await _sel(page, "rblPrintColourSide", "4C (Front)")
    await asyncio.sleep(0.4)
    return True


async def _read(page, q):
    if not await _sel(page, "comboQty", str(q)):
        return None
    await asyncio.sleep(1.0)
    return (await _safe_read(page)).get("before_discount")


async def run(account_id=1):
    a = accounts.get(account_id)
    out = OUT / "kad_finishing.json"
    data = json.loads(out.read_text()) if out.exists() else {"kadkahwin": {"lamination": [], "envelope": []},
                                                             "kadterima": {"lamination": []}}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1600})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)

        # Kad Terima Kasih lamination
        if not data["kadterima"]["lamination"]:
            for lam in LAMS:
                if not await _base(page, TERIMA):
                    continue
                if not await _sel(page, "rblLaminationSide", lam):
                    continue
                for q in QTYS:
                    c = await _read(page, q)
                    if c:
                        data["kadterima"]["lamination"].append({"lam": lam, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("kt.lam", lam=lam[:22])

        # Kad Kahwin lamination
        if not data["kadkahwin"]["lamination"]:
            for lam in LAMS:
                if not await _base(page, KAHWIN, kahwin=True):
                    continue
                if not await _sel(page, "rblLaminationSide", lam):
                    continue
                for q in QTYS:
                    c = await _read(page, q)
                    if c:
                        data["kadkahwin"]["lamination"].append({"lam": lam, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("kk.lam", lam=lam[:22])

        # Kad Kahwin envelope (White/Pink) at Matte Front lamination
        if not data["kadkahwin"]["envelope"]:
            for env in ("Not Required", "White", "Pink"):
                if not await _base(page, KAHWIN, kahwin=True):
                    continue
                await _sel(page, "rblLaminationSide", "Matte Lamination (Front)")
                if env != "Not Required":
                    await _radio(page, "rblEnvelope", env)
                for q in QTYS:
                    c = await _read(page, q)
                    if c:
                        data["kadkahwin"]["envelope"].append({"env": env, "qty": q, "cash": c})
                out.write_text(json.dumps(data, indent=0)); log.info("kk.env", env=env)

        try: await b.close()
        except Exception: pass
    out.write_text(json.dumps(data, indent=0))
    print(f"wrote {out.name}: KK lam={len(data['kadkahwin']['lamination'])} env={len(data['kadkahwin']['envelope'])} "
          f"KT lam={len(data['kadterima']['lamination'])}")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
