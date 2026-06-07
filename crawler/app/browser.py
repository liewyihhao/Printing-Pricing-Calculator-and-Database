"""Browser lifecycle: launch system Edge, login, and session recovery."""
from __future__ import annotations

import asyncio
import random

from playwright.async_api import async_playwright, Page, Browser

from . import config
from .logging_setup import log


async def polite_pause():
    await asyncio.sleep(random.randint(config.MIN_DELAY_MS, config.MAX_DELAY_MS) / 1000)


async def launch(pw) -> Browser:
    """Prefer system Edge/Chrome (bundled Chromium fails with SxS on this host)."""
    for channel in ("msedge", "chrome"):
        try:
            b = await pw.chromium.launch(headless=config.HEADLESS, channel=channel)
            log.info("browser.launched", channel=channel, headless=config.HEADLESS)
            return b
        except Exception as e:
            log.warning("browser.channel_unavailable", channel=channel, error=type(e).__name__)
    log.warning("browser.fallback_bundled_chromium")
    return await pw.chromium.launch(headless=config.HEADLESS)


async def login(page: Page, username: str | None = None,
                password: str | None = None) -> bool:
    # Default to the primary account; callers can pass a second account's creds.
    username = username if username is not None else config.USERNAME
    password = password if password is not None else config.PASSWORD
    if not password:
        raise SystemExit("No EXCARD password configured (.env)")
    log.info("login.start", url=config.LOGIN_URL, user=username[:3] + "***")
    await page.goto(config.LOGIN_URL, wait_until="domcontentloaded")
    await polite_pause()
    # A "BECOME OUR MEMBER" signup modal (#excard-form) can pop up over the login
    # form on a fresh session and intercept clicks. Hide it (and any backdrop)
    # without navigating, so the underlying login form stays intact.
    try:
        await page.evaluate(
            "() => { for (const id of ['excard-form','excard-form-bg',"
            "'excard-form-overlay']) { const o=document.getElementById(id);"
            " if(o){o.style.display='none';o.style.pointerEvents='none';} } }")
    except Exception:
        pass
    await page.wait_for_selector("#mainContent_txtUsernameMid", timeout=15000)
    await page.fill("#mainContent_txtUsernameMid", username)
    await page.fill("#mainContent_txtPasswordMid", password)
    await polite_pause()
    # Submit reliably: pressing Enter in the password box triggers the ASP.NET
    # default-button postback (mimics a human and avoids overlay click issues).
    # Fall back to a real button click if that doesn't navigate.
    try:
        async with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
            await page.press("#mainContent_txtPasswordMid", "Enter")
    except Exception:
        # Fallback submit; ignore navigation races (we verify by URL below).
        try:
            await page.click("#mainContent_btnLogin", timeout=10000)
        except Exception:
            try:
                await page.eval_on_selector("#mainContent_btnLogin", "el => el.click()")
            except Exception:
                pass
    try:
        await page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    ok = "login" not in page.url.lower()
    log.info("login.result", ok=ok, url=page.url)
    return ok


async def is_logged_out(page: Page) -> bool:
    """A redirect to /login (or presence of the login button) means the session
    expired."""
    if "login" in page.url.lower():
        return True
    try:
        return await page.locator("#mainContent_btnLogin").count() > 0
    except Exception:
        return False


async def ensure_session(page: Page) -> None:
    """Re-login if the session has expired."""
    if await is_logged_out(page):
        log.warning("session.expired_reloging_in")
        if not await login(page):
            raise RuntimeError("Re-login failed during crawl.")
