"""Temp probe: capture the real /Product/CheckPrice spec schema for target products and
print the full field-key set, so we can see which products actually carry HotStamping /
Embossing / DeBoss spec fields (ground truth, vs the shared-template option_audit dump)."""
import asyncio, json, sys
from app.checkprice_enum import _capture

SLUGS = sys.argv[1:] or [
    "folder", "greeting-card", "money-packet",
    "premium-money-packet", "hot-stamping-money-packet", "envelope-money-packet",
]

async def main():
    for slug in SLUGS:
        try:
            spec, type_str, cols, axes, qty_col, agg, cookie = await _capture(slug)
        except SystemExit as e:
            print(f"\n=== {slug}: CAPTURE FAILED: {e}")
            continue
        except Exception as e:
            print(f"\n=== {slug}: ERROR {type(e).__name__}: {e}")
            continue
        print(f"\n=== {slug}  type={type_str!r}")
        if spec is None:
            print("  (LOCAL price column — no CheckPrice spec)")
            print("  metrics cols:", cols)
            continue
        keys = list(spec.keys())
        hs = [k for k in keys if any(t in k.lower() for t in ("hotstamp", "emboss", "deboss", "foil", "hs"))]
        print("  ALL spec keys:", keys)
        print("  >>> HS/emboss keys:", hs)
        print("  >>> HS/emboss values:", {k: spec[k] for k in hs})

asyncio.run(main())
