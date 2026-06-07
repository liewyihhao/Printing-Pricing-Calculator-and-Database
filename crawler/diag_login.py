"""One-shot login diagnostic: attempt a single login and capture the result so
we can see WHY it fails (error message / CAPTCHA / block / code issue).
Does NOT attempt to bypass any challenge."""
import asyncio
from playwright.async_api import async_playwright
from app import config
from app.browser import launch, polite_pause
from app.config import OUTPUT_DIR


async def main():
    async with async_playwright() as pw:
        browser = await launch(pw)
        page = await (await browser.new_context(
            viewport={"width": 1440, "height": 1000})).new_page()
        await page.goto(config.LOGIN_URL, wait_until="domcontentloaded")
        await polite_pause()
        await page.fill("#mainContent_txtUsernameMid", config.USERNAME)
        await page.fill("#mainContent_txtPasswordMid", config.PASSWORD)
        await polite_pause()
        # Use a normal click (what the original working crawl used).
        try:
            await page.click("#mainContent_btnLogin", timeout=15000)
        except Exception as e:
            print("click error:", repr(e))
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        await polite_pause()

        url = page.url
        print("FINAL URL:", url)
        print("LOGGED IN:", "login" not in url.lower())
        body = (await page.evaluate("() => document.body.innerText")).lower()
        for flag in ["captcha", "recaptcha", "too many", "locked", "blocked",
                     "suspicious", "verify you are human", "try again later",
                     "incorrect", "invalid", "wrong password", "exceeded"]:
            if flag in body:
                print(f"  PAGE MENTIONS: '{flag}'")
        (OUTPUT_DIR / "diag_login.html").write_text(await page.content(), encoding="utf-8")
        await page.screenshot(path=str(OUTPUT_DIR / "diag_login.png"), full_page=True)
        print("Saved diag_login.png / diag_login.html")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
