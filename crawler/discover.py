"""
Printoka × Excard — Phase 1 discovery crawler.

Goal of THIS script (intentionally narrow):
  1. Log into excard.com.my with reseller credentials from .env
  2. Open the Litho price-list page
  3. Discover the real page structure: every form, <select> + its <option>s,
     inputs, radios/checkboxes, and any pricing table on the page
  4. Save a full snapshot (HTML + screenshot + structured JSON of the options)

It does NOT yet generate combinations or store prices. We look at the real
structure first, then design the full crawler against what actually exists.

Run:  python discover.py
"""

import os
import sys
import io
import json
import random
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

# Windows consoles default to cp1252 and choke on non-ASCII; force UTF-8.
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).parent
load_dotenv(HERE / ".env")

USERNAME = os.getenv("EXCARD_USERNAME", "").strip()
PASSWORD = os.getenv("EXCARD_PASSWORD", "").strip()
PRICE_URL = os.getenv("EXCARD_PRICE_URL", "https://www.excard.com.my/price-list/Litho/21").strip()
LOGIN_URL = os.getenv("EXCARD_LOGIN_URL", "https://www.excard.com.my/login").strip()
MIN_DELAY = int(os.getenv("CRAWL_MIN_DELAY_MS", "1500"))
MAX_DELAY = int(os.getenv("CRAWL_MAX_DELAY_MS", "3500"))
HEADLESS = os.getenv("HEADLESS", "false").strip().lower() == "true"

OUT = HERE / "output"
OUT.mkdir(exist_ok=True)
STAMP = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


async def polite_pause():
    await asyncio.sleep(random.randint(MIN_DELAY, MAX_DELAY) / 1000)


async def launch_browser(pw):
    """Prefer the system Edge/Chrome channel (runtime deps already satisfied on
    Windows), and fall back to Playwright's bundled Chromium if needed."""
    for channel in ("msedge", "chrome"):
        try:
            b = await pw.chromium.launch(headless=HEADLESS, channel=channel)
            log(f"Launched system browser via channel='{channel}'.")
            return b
        except Exception as e:
            log(f"  channel='{channel}' unavailable ({type(e).__name__}); trying next.")
    log("Falling back to bundled Chromium.")
    return await pw.chromium.launch(headless=HEADLESS)


async def try_login(page):
    """Best-effort login. Excard's exact login form is unknown, so we probe
    several common patterns and report what we found rather than assuming."""
    log(f"Opening login page: {LOGIN_URL}")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded")
    await polite_pause()

    # Excard is ASP.NET WebForms with several login forms on one responsive page
    # (sidebar, mobile, main). The main page login uses the *Mid fields + the
    # btnLogin postback button. We target that exact set, with fallbacks.
    field_sets = [
        ("#mainContent_txtUsernameMid", "#mainContent_txtPasswordMid", "#mainContent_btnLogin"),
        ("#TemplatedContent1__product_txtusername", "#TemplatedContent1__product_txtpassword", None),
        ("#TemplatedContent1__product_mtxtusername", "#TemplatedContent1__product_mtxtpassword", None),
    ]
    user_field = pass_field = submit = None
    for u, p, s in field_sets:
        if await page.query_selector(u) and await page.query_selector(p):
            user_field, pass_field, submit = u, p, s
            break

    if not user_field:
        log("⚠ Could not find a known login form. Saving login page for inspection.")
        await snapshot(page, "login_page")
        return False

    log(f"Filling login form ({user_field}).")
    await page.fill(user_field, USERNAME)
    await page.fill(pass_field, PASSWORD)
    await polite_pause()

    if submit and await page.query_selector(submit):
        await page.click(submit)
    else:
        await page.press(pass_field, "Enter")

    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except PWTimeout:
        pass
    await polite_pause()

    # Heuristic: login worked if we're no longer sitting on the login page.
    still_login = "login" in page.url.lower()
    ok = not still_login
    log(f"Login {'appears successful' if ok else 'may have FAILED'} (url now: {page.url})")
    return ok


async def first_match(page, selectors):
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                return sel
        except Exception:
            continue
    return None


async def discover_options(page):
    """Dump every form control on the page into a structured dict."""
    log("Discovering form controls (selects, inputs, radios)…")
    data = await page.evaluate(
        """() => {
            const out = { selects: [], radios_checkboxes: [], text_inputs: [], buttons: [], tables: 0 };
            document.querySelectorAll('select').forEach(s => {
                out.selects.push({
                    name: s.name || s.id || null,
                    label: (s.labels && s.labels[0] && s.labels[0].innerText.trim()) || null,
                    options: [...s.options].map(o => ({ value: o.value, text: o.text.trim() }))
                });
            });
            const seen = new Set();
            document.querySelectorAll("input[type=radio], input[type=checkbox]").forEach(i => {
                const key = i.name || i.id;
                out.radios_checkboxes.push({
                    type: i.type, name: i.name || null, id: i.id || null,
                    value: i.value, checked: i.checked,
                    label: (i.labels && i.labels[0] && i.labels[0].innerText.trim()) || null
                });
            });
            document.querySelectorAll("input[type=text], input[type=number], input:not([type])").forEach(i => {
                out.text_inputs.push({ name: i.name || null, id: i.id || null, placeholder: i.placeholder || null });
            });
            document.querySelectorAll("button, input[type=submit]").forEach(b => {
                out.buttons.push((b.innerText || b.value || '').trim());
            });
            out.tables = document.querySelectorAll('table').length;
            return out;
        }"""
    )
    return data


async def snapshot(page, label):
    html_path = OUT / f"{STAMP}_{label}.html"
    png_path = OUT / f"{STAMP}_{label}.png"
    html_path.write_text(await page.content(), encoding="utf-8")
    await page.screenshot(path=str(png_path), full_page=True)
    log(f"  ↳ saved {html_path.name} and {png_path.name}")


async def main():
    if not PASSWORD:
        log("✗ No password set. Copy .env.example to .env and fill EXCARD_PASSWORD, then re-run.")
        sys.exit(1)

    async with async_playwright() as pw:
        browser = await launch_browser(pw)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
        )
        page = await context.new_page()

        try:
            await try_login(page)

            log(f"Opening price list: {PRICE_URL}")
            await page.goto(PRICE_URL, wait_until="domcontentloaded")
            await polite_pause()
            await snapshot(page, "price_list")

            options = await discover_options(page)
            report = {
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "price_url": PRICE_URL,
                "final_url": page.url,
                "page_title": await page.title(),
                "discovery": options,
            }
            report_path = OUT / f"{STAMP}_discovery.json"
            report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

            log("──────── DISCOVERY SUMMARY ────────")
            log(f"  Page title : {report['page_title']}")
            log(f"  Selects    : {len(options['selects'])}")
            for s in options["selects"]:
                log(f"     • {s['label'] or s['name']}: {len(s['options'])} options "
                    f"e.g. {[o['text'] for o in s['options'][:4]]}")
            log(f"  Radios/checks: {len(options['radios_checkboxes'])}")
            log(f"  Text inputs : {len(options['text_inputs'])}")
            log(f"  Tables      : {options['tables']}")
            log(f"  Full report : output/{report_path.name}")
            log("───────────────────────────────────")
            log("Review the JSON + screenshot, then we design the full crawler against real structure.")

        except Exception as e:
            log(f"✗ Error: {e!r}")
            try:
                await snapshot(page, "error_state")
            except Exception:
                pass
            raise
        finally:
            await polite_pause()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
