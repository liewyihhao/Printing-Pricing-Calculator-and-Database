"""Enumerate EXACT prices for Excard 'readymade' products (Cap, shirts) by driving the
v4 ordering page's ReadyMade engine and reading its authenticated /Product/CheckPrice
responses. See memory 'excard-readymade-pricing-api' for the cracked method.

The engine's price XHR carries a per-request Authorization/Api-Key token that can't be
replayed, so we let the engine make the call and capture the response — triggering a
recompute by driving the real quantity input. Runs headless/unattended (no 45s eval cap
like the browser extension), paced politely.

Output: output/v4_options/<slug>_options.json in the standard capture shape so the normal
build pipeline (_wire_pricelist_products) turns it into an exact, validity-enforced product.

CLI:  python -m app.readymade_enum cap
"""
from __future__ import annotations
import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright
from app import browser as B

OUT = Path(__file__).resolve().parent.parent / "output"
V4 = "https://v4.excard.com.my/ordering/"

# Per-product enumeration config. `models` are the .shirt-model-card labels; `qtys` the grid.
# `country`/`courier` are fixed to a West-Malaysia default (product price is delivery-independent).
CONFIGS = {
    "cap": {
        "slug": "cap", "name": "Cap", "primaryAxis": "Model",
        "models": ["Baseball", "Trucker"],
        "qtys": [5, 10, 20, 30, 40, 50, 75, 100, 150, 200, 250, 300, 400, 500],
    },
}

QTY_INPUT = ".shirt-qty-input"


async def login_v4(page) -> bool:
    """v4.excard.com.my has its own login (separate from www). Sign in there directly."""
    from app import config
    await page.goto("https://v4.excard.com.my/home-visitor/", wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(1500)
    await page.fill("#TemplatedContent1_txtusername", config.USERNAME)
    await page.fill("#TemplatedContent1_txtpassword", config.PASSWORD)
    try:
        async with page.expect_navigation(wait_until="domcontentloaded", timeout=20000):
            await page.click("#TemplatedContent1_excardLogin")
    except Exception:
        await page.click("#TemplatedContent1_excardLogin")
    await page.wait_for_timeout(2000)
    ok = "visitor" not in page.url.lower()
    print("v4 login:", ok, page.url, file=sys.stderr)
    return ok


async def _add_model_row(page, model_label: str):
    """Open the +ADD MODEL modal, pick Adult + the given model card, accept default colour/
    printing, and confirm — leaving one order row with a quantity input."""
    await page.click("#shirt_add_model")
    await page.wait_for_selector(".shirt-model-card", timeout=15000)
    await page.wait_for_timeout(400)
    # Category = Adult (first radio in the popup)
    try:
        await page.check("input[name='shirt_popup_category'][value='Adult']")
    except Exception:
        pass
    await page.wait_for_timeout(200)
    # Select the model card whose text matches
    cards = page.locator(".shirt-model-card")
    n = await cards.count()
    for i in range(n):
        t = (await cards.nth(i).inner_text()).strip()
        if model_label.lower() in t.lower():
            await cards.nth(i).click()
            break
    await page.wait_for_timeout(400)
    # Confirm (footer ADD button)
    await page.click(".shirt-popup-footer")
    await page.wait_for_selector(QTY_INPUT, timeout=15000)
    await page.wait_for_timeout(500)


async def _remove_all_rows(page):
    """Reload to clear rows (simplest reliable reset between models)."""
    await page.reload(wait_until="networkidle")
    await page.wait_for_selector("#shirt_add_model", timeout=20000)
    await page.wait_for_timeout(800)


async def _price_for_qty(page, qty: int, hold: dict) -> float | None:
    """Type the quantity (real keystrokes) to trigger the engine's authenticated CheckPrice,
    and return the WM cash Price from the captured response."""
    hold["price"] = None
    inp = page.locator(QTY_INPUT).first
    await inp.click()
    await inp.press("Control+A")
    await inp.press("Delete")
    await inp.type(str(qty), delay=60)
    await inp.press("Tab")
    # wait for a fresh CheckPrice response for this qty
    for _ in range(40):
        await page.wait_for_timeout(300)
        if hold["price"] is not None and hold["qty"] == str(qty):
            return hold["price"]
    return None


async def enumerate_product(cfg: dict):
    async with async_playwright() as pw:
        b = await B.launch(pw)
        page = await b.new_page()
        ok = await login_v4(page)
        print("login ok:", ok, file=sys.stderr)

        hold = {"price": None, "qty": None}

        async def on_resp(resp):
            if "CheckPrice" in resp.url:
                try:
                    body = await resp.json()
                    req = resp.request.post_data_json
                    q = req["spec"][0]["TotalQuantity"] if req else None
                    hold["price"] = float(str(body.get("Price")).replace(",", ""))
                    hold["qty"] = str(q)
                except Exception:
                    pass

        page.on("response", lambda r: asyncio.create_task(on_resp(r)))

        await page.goto(V4 + cfg["slug"], wait_until="networkidle", timeout=30000)
        await page.wait_for_selector("#shirt_add_model", timeout=20000)
        await page.wait_for_timeout(1000)

        curves = {}
        for model in cfg["models"]:
            await _remove_all_rows(page)
            await _add_model_row(page, model)
            model_curve = {}
            for qty in cfg["qtys"]:
                p = await _price_for_qty(page, qty, hold)
                if p and p > 0:
                    model_curve[str(qty)] = p
                    print(f"  {model} qty {qty} -> {p}", file=sys.stderr)
                await page.wait_for_timeout(400)
            curves[model] = model_curve
        await b.close()
        return curves


def _write_capture(cfg: dict, curves: dict):
    axis = cfg["primaryAxis"]
    models = list(curves.keys())
    # curve keys are keyed by the single Model axis value
    out_curves = {m: curves[m] for m in models if curves[m]}
    distinct = {axis: models}
    deps = {m: {} for m in models}
    out = {
        "slug": cfg["slug"], "source": "readymade-checkprice-api",
        "rows": sum(len(c) for c in out_curves.values()),
        "optionCols": [axis], "primary": axis, "deps": deps,
        "imageField": None, "distinct": distinct, "imageOptions": {},
        "priceMeta": {"priceCol": "Price", "qtyCol": "Quantity",
                      "axisCols": [axis], "nCurves": len(out_curves)},
        "curves": out_curves,
    }
    p = OUT / "v4_options" / f"{cfg['slug']}_options.json"
    p.write_text(json.dumps(out), encoding="utf-8")
    print(f"wrote {p} ({len(out_curves)} curves)", file=sys.stderr)


async def main(slug):
    cfg = CONFIGS[slug]
    curves = await enumerate_product(cfg)
    _write_capture(cfg, curves)
    for m, c in curves.items():
        print(m, "->", c)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "cap"))
