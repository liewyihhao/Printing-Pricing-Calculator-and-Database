"""Re-sample Loose Sheet — Litho (product 21) real Excard prices from the old www
order page (OrderQuote was deleted, so the engine had no ground truth). Resumable:
skips (size,paper,colour) configs already in output/spot_samples_21.json. Saves the
same shape as the other samplers so a per-config curve + audit can use it.

    python -m app.litho_sampler [account]
"""
from __future__ import annotations
import json, sys, asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from sqlalchemy import select
from .browser import launch, login
from . import accounts, products
from .db import session_scope
from .models import OrderWork
from .order_capture import configure, sweep_quantities, available_quantities, OrderConfigSpec
from .logging_setup import log

OUT = Path(__file__).resolve().parent.parent / "output"
PID = 21


def configs():
    with session_scope() as s:
        rows = s.execute(select(OrderWork.size_label, OrderWork.paper_label,
                                OrderWork.colour_side)
                         .where(OrderWork.product_id == PID, OrderWork.status == "done",
                                OrderWork.package == "Normal").distinct()).all()
    return [(r[0], r[1], r[2], "Normal") for r in rows]


async def run(account_id=1, recycle_every=6):
    target = products.get(PID)
    a = accounts.get(account_id)
    out = OUT / "spot_samples_21.json"
    results = json.loads(out.read_text()) if out.exists() else []
    done = {(r["size"], r["paper"], r["colour"]) for r in results}
    cfgs = [c for c in configs() if (c[0], c[1], c[2]) not in done]
    print(f"litho 21: {len(cfgs)} configs to sample ({len(done)} already done)")
    async with async_playwright() as pw:
        browser = await launch(pw)
        ctx = await browser.new_context(viewport={"width": 1440, "height": 1300})
        page = await ctx.new_page()
        await login(page, username=a.username, password=a.password)
        n = 0
        for (size, paper, colour, pkg) in cfgs:
            if n and n % recycle_every == 0:
                try: await ctx.close()
                except Exception: pass
                ctx = await browser.new_context(viewport={"width": 1440, "height": 1300})
                page = await ctx.new_page()
                await login(page, username=a.username, password=a.password)
            spec = OrderConfigSpec(PID, size, paper, colour, pkg, 98, spec_url=target.spec_url)
            try:
                if await configure(page, spec):
                    qtys = await available_quantities(page)
                    rows = await sweep_quantities(page, spec, qtys)
                    for r in rows:
                        if r.before_discount:
                            results.append({"size": size, "paper": paper, "colour": colour,
                                            "package": pkg, "qty": r.quantity,
                                            "cash": r.before_discount, "weight": r.weight_kg})
                    out.write_text(json.dumps(results))
                    log.info("litho.captured", size=size, paper=paper, colour=colour,
                             n=len(rows), total=len(results))
            except Exception as e:  # noqa: BLE001
                log.error("litho.error", error=repr(e)[:120])
                try: await ctx.close()
                except Exception: pass
                ctx = await browser.new_context(viewport={"width": 1440, "height": 1300})
                page = await ctx.new_page()
                await login(page, username=a.username, password=a.password)
            n += 1
        try: await browser.close()
        except Exception: pass
    out.write_text(json.dumps(results))
    print(f"wrote output/spot_samples_21.json ({len(results)} points)")


if __name__ == "__main__":
    asyncio.run(run(int(sys.argv[1]) if len(sys.argv) > 1 else 1))
