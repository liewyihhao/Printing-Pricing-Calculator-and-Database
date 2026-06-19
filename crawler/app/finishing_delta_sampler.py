"""Sample the price DELTA of newly-added finishing so it becomes priced (not 'quoted
separately'):
  * loose Envelope  (products 21 & 50): delta vs no-envelope across qty → per-piece add.
  * booklet Cover Lamination (19 & 37): delta vs no-lamination across qty/size → per-cover add.

  python -m app.finishing_delta_sampler envelope [account]
  python -m app.finishing_delta_sampler booklet_lam [account]
"""
from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .logging_setup import log
from .order_capture import _select, _check_delivery, _parse_breakdown, _TOGGLE_HELPER, QTY_SEL

OUT = Path(__file__).resolve().parent.parent / "output"


async def _wait(page):
    try: await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception: pass
    await asyncio.sleep(0.8)


async def _price(page, code=98):
    await _check_delivery(page, _TOGGLE_HELPER.get(code, 99)); await _check_delivery(page, code)
    return _parse_breakdown(await page.evaluate("()=>document.body.innerText")).get("before_discount")


async def envelope(account_id=1):
    """Loose envelope delta: configure a base loose config, sweep qty at no-envelope vs
    each envelope option; the delta is the envelope's added price."""
    a = accounts.get(account_id)
    URLS = {21: "https://www.excard.com.my/spec/Litho/Loose_Sheet",
            50: "https://www.excard.com.my/spec/Digital/Loose_Sheet"}
    cfg = {21: dict(size="A4 (210mm x 297mm)", paper="Gloss Art Card 250gsm (2 sides coated) - Best Seller",
                    colour="4C (Both)", qtys=[100, 500, 1000]),
           50: dict(size="210mm x 297mm (A4)", paper="Gloss Art Card 250gsm (2 side coated)",
                    colour=None, qtys=[50, 100, 200])}
    data = {}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for pid, url in URLS.items():
            c = cfg[pid]; rows = []
            await page.goto(url, wait_until="domcontentloaded"); await _wait(page)
            await _select(page, "select[name$='ddlSize']", c["size"])
            await _select(page, "select[name$='ddlPaper']", c["paper"])
            if c["colour"]:
                await _select(page, "select[name$='rblPrintColourSide'], select[name$='ddlPrintColourSide']", c["colour"])
            # envelope options offered
            envs = await page.locator("select[name$='rblEnvelope']").first.evaluate(
                "el=>[...el.options].map(o=>o.text.trim())") if await page.locator("select[name$='rblEnvelope']").count() else []
            envs = [e for e in envs if e and not e.startswith("-")][:2]   # 2 representative envelopes
            for q in c["qtys"]:
                await _select(page, QTY_SEL, str(q))
                await _select(page, "select[name$='rblEnvelope']", "- Not Required -")
                base = await _price(page)
                for ev in envs:
                    await _select(page, "select[name$='rblEnvelope']", ev)
                    p = await _price(page)
                    rows.append({"qty": q, "envelope": ev, "base": base, "with": p,
                                 "delta": (p - base) if (p and base) else None})
                await _select(page, "select[name$='rblEnvelope']", "- Not Required -")
            data[str(pid)] = rows
            log.info("env.done", pid=pid, n=len(rows))
        try: await b.close()
        except Exception: pass
    (OUT / "finishing_envelope.json").write_text(json.dumps(data, indent=1))
    for pid, rows in data.items():
        for r in rows:
            print(f"  {pid} q{r['qty']} {r['envelope'][:22]}: base {r['base']} +env {r['with']} Δ={r['delta']}")


async def booklet_lam(account_id=1):
    """Booklet cover-lamination delta vs no lamination, a few sizes × qty."""
    from .booklet_capture import configure_booklet, BookletSpec
    a = accounts.get(account_id)
    specs = [(37, "Digital", "Gloss Art Card 250gsm (2 sides coated)"),
             (19, "Litho", "Gloss Art Card 250gsm (2 side coated)")]
    LAMS = ["Matte Lamination (Both)", "Gloss Lamination (Both)", "Matte Lamination (Front)"]
    data = {}
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1400})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for pid, method, cover in specs:
            rows = []
            for size in ["A4 (210mm x 297mm)", "A5 (148mm x 210mm)"]:
                spec = BookletSpec(product_id=pid, spec_url=f"https://www.excard.com.my/spec/{method}/Booklet",
                                   orientation="Portrait", size=size, ordertype="Soft Cover",
                                   binding="Saddle Stitch", page="16", cover_paper=cover, cover_colour="4C",
                                   content_paper="Simili 80gsm", content_colour="4C (Both)")
                try:
                    await configure_booklet(page, spec)
                except Exception as e:  # noqa: BLE001 — partial config may still reach lamination+price
                    log.info("lam.cfg_warn", pid=pid, size=size, err=str(e)[:50])
                await asyncio.sleep(1.0)
                lam_sel = "select[name$='ddlCoverLamination']"
                if not await page.locator(lam_sel).count():
                    continue
                for q in ([100, 300] if pid == 37 else [100, 300]):
                    await _select(page, QTY_SEL, str(q))
                    await _select(page, lam_sel, "- Please Select -") if False else None
                    # base = first try a 'none' — but lamination may be required; use the
                    # cheapest (Matte Front) as ref if no 'none' exists.
                    base = await _price(page)
                    for lam in LAMS:
                        if not await _select(page, lam_sel, lam):
                            continue
                        p = await _price(page)
                        rows.append({"size": size, "qty": q, "lam": lam, "base_noLamSelected": base,
                                     "with": p})
                log.info("lam.size", pid=pid, size=size, n=len(rows))
            data[str(pid)] = rows
        try: await b.close()
        except Exception: pass
    (OUT / "finishing_booklet_lam.json").write_text(json.dumps(data, indent=1))
    for pid, rows in data.items():
        for r in rows[:12]:
            print(f"  {pid} {r['size'][:6]} q{r['qty']} {r['lam'][:22]}: base {r['base_noLamSelected']} with {r['with']}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "envelope"
    acct = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    asyncio.run({"envelope": envelope, "booklet_lam": booklet_lam}[mode](acct))
