"""Shared Excard helpers: UTF-8 console, browser launch (system Edge), login."""
import os, sys, io, random, asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).parent
load_dotenv(HERE / ".env")

USERNAME = os.getenv("EXCARD_USERNAME", "").strip()
PASSWORD = os.getenv("EXCARD_PASSWORD", "").strip()
LOGIN_URL = os.getenv("EXCARD_LOGIN_URL", "https://www.excard.com.my/login").strip()
MIN_DELAY = int(os.getenv("CRAWL_MIN_DELAY_MS", "1500"))
MAX_DELAY = int(os.getenv("CRAWL_MAX_DELAY_MS", "3500"))
HEADLESS = os.getenv("HEADLESS", "false").strip().lower() == "true"

OUT = HERE / "output"
OUT.mkdir(exist_ok=True)


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


async def polite_pause():
    await asyncio.sleep(random.randint(MIN_DELAY, MAX_DELAY) / 1000)


async def launch_browser(pw):
    for channel in ("msedge", "chrome"):
        try:
            b = await pw.chromium.launch(headless=HEADLESS, channel=channel)
            log(f"Launched system browser via channel='{channel}'.")
            return b
        except Exception as e:
            log(f"  channel='{channel}' unavailable ({type(e).__name__}); trying next.")
    log("Falling back to bundled Chromium.")
    return await pw.chromium.launch(headless=HEADLESS)


async def login(page) -> bool:
    if not PASSWORD:
        raise SystemExit("No password set in crawler/.env (EXCARD_PASSWORD=).")
    log(f"Opening login page: {LOGIN_URL}")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded")
    await polite_pause()
    await page.fill("#mainContent_txtUsernameMid", USERNAME)
    await page.fill("#mainContent_txtPasswordMid", PASSWORD)
    await polite_pause()
    await page.click("#mainContent_btnLogin")
    try:
        await page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    ok = "login" not in page.url.lower()
    log(f"Login {'OK' if ok else 'FAILED'} -> {page.url}")
    return ok
