"""Configure the form, click Generate Price List, and capture ALL network
responses + any popup, to find where the real price data comes from."""
import os, asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from excard import log, polite_pause, launch_browser, login, OUT

PRICE_URL = os.getenv("EXCARD_PRICE_URL", "https://www.excard.com.my/price-list/Litho/21").strip()
M = "ctl00$mainContent$order_spec_controller1$order_spec_standard_matrix1$"
captured = []


async def main():
    async with async_playwright() as pw:
        b = await launch_browser(pw)
        ctx = await b.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        page = await ctx.new_page()

        async def on_response(resp):
            try:
                url = resp.url
                if "excard.com.my" not in url:
                    return
                if any(url.split("?")[0].endswith(x) for x in
                       (".png", ".jpg", ".jpeg", ".css", ".js", ".woff", ".woff2", ".gif", ".svg", ".ico")):
                    return
                body = await resp.body()
                captured.append((resp.request.method, resp.status,
                                 resp.headers.get("content-type", "")[:30], url, len(body), body))
            except Exception:
                pass
        page.on("response", on_response)
        ctx.on("page", lambda p: log(f"!! popup/new page opened: {p.url}"))

        if not await login(page):
            raise SystemExit("login failed")
        await page.goto(PRICE_URL, wait_until="domcontentloaded"); await polite_pause()
        await page.select_option(f"select[name='{M}ddlSize']", label="A4 (210mm x 297mm)")
        await page.wait_for_load_state("networkidle"); await polite_pause()
        await page.select_option(f"select[name='{M}ddlPaper']",
                                 label="Gloss Art Card 250gsm (2 sides coated) - Best Seller")
        await page.wait_for_load_state("networkidle"); await polite_pause()
        # Lamination is a <select> (name has rbl prefix but it's a dropdown).
        lam = page.locator("select").filter(
            has=page.locator("option:text-is('Matte Lamination (Front)')")).first
        if await lam.count():
            await lam.select_option(label="Matte Lamination (Front)")
            await page.wait_for_load_state("networkidle")
            log("Lamination selected.")
        else:
            log("⚠ lamination select not found")
        await polite_pause()

        # Confirm client validation passes before generating.
        valid = await page.evaluate(
            "() => typeof Page_ClientValidate==='function' ? Page_ClientValidate('order_spec') : null")
        log(f"Page_ClientValidate('order_spec') -> {valid}")

        log("Triggering Generate via __doPostBack; recording network…")
        captured.clear()
        await page.evaluate("() => __doPostBack('ctl00$mainContent$btnPriceList','')")
        await asyncio.sleep(9)  # let the postback complete
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass

        log(f"Pages now open: {[p.url for p in ctx.pages]}")
        log(f"Captured {len(captured)} Excard responses:")
        for i, (meth, st, ct, url, n, body) in enumerate(captured):
            has_rm = b"RM" in body
            log(f"  [{i}] {meth} {st} {n}B {ct} rm={has_rm} {url[:80]}")
            if has_rm and n < 3_000_000:
                (OUT / f"net_{i}.html").write_bytes(body)
                txt = body.decode("utf-8", "replace")
                hits = [ln.strip() for ln in txt.splitlines() if "RM" in ln and any(c.isdigit() for c in ln)][:8]
                for h in hits:
                    log(f"        RM> {h[:120]}")

        # Also dump what the main page now shows.
        body_txt = await page.evaluate("() => document.body.innerText")
        rm_lines = [ln.strip() for ln in body_txt.splitlines() if "RM" in ln][:10]
        log(f"Main page RM lines: {rm_lines}")
        await page.screenshot(path=str(OUT / "probe_network_after.png"), full_page=True)
        await b.close()

asyncio.run(main())
