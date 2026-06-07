"""Spot-test sampler: collect a stratified sample of real Excard prices for a
product (no full crawl) to calibrate + validate the Printoka formula.

Saves output/spot_samples_<product>.json as a list of
  {size, paper, colour, package, qty, cash, weight}
"""
from __future__ import annotations
import json, asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch
from . import accounts, products
from .order_capture import configure, sweep_quantities, available_quantities, OrderConfigSpec
from .logging_setup import log

OUT = Path(__file__).resolve().parent.parent / "output"


async def sample(product_id: int, configs: list[tuple], account_id: int = 1,
                 recycle_every: int = 6):
    """configs = list of (size, paper, colour, package). Sweeps all quantities."""
    target = products.get(product_id)
    a = accounts.get(account_id)
    from .browser import login
    results = []
    async with async_playwright() as pw:
        browser = await launch(pw)
        ctx = await browser.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page()
        await login(page, username=a.username, password=a.password)
        done = 0
        for (size, paper, colour, pkg) in configs:
            if done and done % recycle_every == 0:        # refresh context to avoid wedge
                try: await ctx.close()
                except Exception: pass
                ctx = await browser.new_context(viewport={"width": 1440, "height": 1300})
                page = await ctx.new_page()
                await login(page, username=a.username, password=a.password)
            spec = OrderConfigSpec(product_id, size, paper, colour, pkg, 98,
                                   spec_url=target.spec_url)
            try:
                if not await configure(page, spec):
                    log.warning("spot.skip", size=size, paper=paper, colour=colour)
                    done += 1; continue
                qtys = await available_quantities(page)
                rows = await sweep_quantities(page, spec, qtys)
                for r in rows:
                    if r.before_discount:
                        results.append({"size": size, "paper": paper, "colour": colour,
                                        "package": pkg, "qty": r.quantity,
                                        "cash": r.before_discount, "weight": r.weight_kg})
                log.info("spot.captured", size=size, paper=paper, colour=colour,
                         n=len(rows), total=len(results))
                OUT.joinpath(f"spot_samples_{product_id}.json").write_text(
                    json.dumps(results, indent=0))  # incremental save
            except Exception as e:  # noqa: BLE001
                log.error("spot.error", error=repr(e)[:120])
                try: await ctx.close()
                except Exception: pass
                ctx = await browser.new_context(viewport={"width": 1440, "height": 1300})
                page = await ctx.new_page()
                await login(page, username=a.username, password=a.password)
            done += 1
        try: await browser.close()
        except Exception: pass
    OUT.joinpath(f"spot_samples_{product_id}.json").write_text(json.dumps(results, indent=0))
    log.info("spot.done", product=product_id, points=len(results))
    return len(results)


def stratified_digital_configs():
    """Representative grid for Digital Loose Sheet (product 50)."""
    opts = json.loads((Path(__file__).resolve().parent.parent / "crawler" /
                       "digital_options.json").read_text()) if False else None
    sizes = ["297mm x 420mm (A3)", "210mm x 297mm (A4)", "148mm x 210mm (A5)",
             "105mm x 148mm (A6)", "74mm x 105mm (A7)", "99mm x 210mm (DL)",
             "198mm x 210mm - (2DL)", "310mm x 445mm"]
    papers = ["Simili 100gsm", "Gloss Art Paper 128gsm", "Matte Art Paper 130gsm",
              "Gloss Art Card 250gsm (2 side coated)", "Gloss Art Card 360gsm (2 side coated)",
              "Linen 240gsm"]
    cfgs = []
    for s in sizes:
        for p in papers:
            cfgs.append((s, p, "4C (Both)", "Normal"))
        # a couple of 4C(Front) per size for colour coverage
        cfgs.append((s, "Gloss Art Paper 128gsm", "4C (Front)", "Normal"))
    return cfgs


if __name__ == "__main__":
    import sys
    pid = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    cfgs = stratified_digital_configs()
    print(f"sampling {len(cfgs)} configs for product {pid}...")
    asyncio.run(sample(pid, cfgs, account_id=int(sys.argv[2]) if len(sys.argv) > 2 else 1))
