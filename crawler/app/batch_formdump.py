"""Batch form dumper: one login, dump many /spec forms. Triage tool.

  python -m app.batch_formdump
"""
from __future__ import annotations
import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts
from .parity_formdump import _dump_all

OUT = Path(__file__).resolve().parent.parent / "output"
BASE = "https://www.excard.com.my"
TARGETS = {
    "money_packet": "/spec/Litho/Money_Packet",
    "non_woven_bag": "/spec/Litho/Non_Woven_Bag",
    "standing_pouch": "/spec/Litho/Standing_Pouch",
    "magnet": "/spec/Digital/Magnet",
    "button_badge": "/spec/Digital/button_badge",
    "shirt": "/spec/Digital/Shirt",
    "hand_fan": "/spec/Digital/Hand_Fan",
    "hanger": "/spec/Digital/Hanger",
    "hard_cover_menu": "/spec/Digital/Hard_Cover_Menu",
    "mask_keeper": "/spec/Digital/Mask_Keeper",
}


async def run(account_id=1):
    a = accounts.get(account_id)
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1600})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for tag, path in TARGETS.items():
            try:
                await page.goto(BASE + path, wait_until="domcontentloaded")
                try: await page.wait_for_load_state("networkidle", timeout=15000)
                except Exception: pass
                await asyncio.sleep(2.0)
                d = await _dump_all(page); d["url"] = BASE + path
                OUT.joinpath(f"formdump_{tag}.json").write_text(json.dumps(d, indent=1))
                sels = {s["name"]: s["options"][:14] for s in d["selects"] if s["name"] and s["name"] not in ("",)}
                print(f"=== {tag} ({path}) ===")
                print("  SELECTS:", {k: v for k, v in sels.items() if "Country" not in k})
                print("  RADIOS:", {k: v for k, v in d["radios"].items() if "Country" not in k and "Courier" not in k})
            except Exception as e:  # noqa: BLE001
                print(f"=== {tag}: ERROR {str(e)[:80]}")
        try: await b.close()
        except Exception: pass


if __name__ == "__main__":
    asyncio.run(run())
