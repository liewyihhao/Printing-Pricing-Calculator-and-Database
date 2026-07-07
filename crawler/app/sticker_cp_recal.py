"""Recalibrate sticker_engine formula params against CheckPrice data.

Samples CheckPrice for a grid of sizes/papers/qtys, then re-runs the differential
evolution fit. Writes sticker_params_digital.json with improved accuracy.

Usage:
  python -m app.sticker_cp_recal          # sample + calibrate
  python -m app.sticker_cp_recal --use-existing  # use existing CP samples file
"""
from __future__ import annotations
import base64, json, ssl, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.voucher_cp_sampler import _get_session_cookie

OUT = Path(__file__).resolve().parent.parent / "output"
SAMPLES_FILE = OUT / "sticker_cp_samples.json"

CHECKPRICE_URL = "https://devv2.excard.com.my/Product/CheckPrice"
_B64 = base64.b64encode(b"ExcardAPI:EXCARDPNCAPI").decode()
_API_KEY = "RjvaNM0xSDxcKyneFhFFxek42Nrnd4FuE9rScoHQ"
_CTX = ssl._create_unverified_context()

# Sample grid — sizes chosen to cover 1-140 ups range across both sheet sizes
SIZES = [
    (30, 30),    # ~140 ups
    (50, 30),    # ~100 ups
    (50, 50),    # ~48 ups
    (54, 89),    # ~21 ups  (Excard recommended: 89×54)
    (70, 100),   # ~18 ups
    (89, 54),    # same as 54×89 (symmetry check)
    (100, 70),   # ~12 ups
    (100, 100),  # ~12 ups
    (105, 74),   # ~10 ups
    (105, 148),  # ~8 ups   (Excard recommended: 148×105)
    (148, 105),  # same as 105×148 (symmetry check)
    (148, 210),  # ~4 ups   (Excard recommended)
    (200, 150),  # ~3 ups
    (210, 148),  # ~4 ups   (Excard recommended: 210×148)
    (210, 297),  # ~2 ups   (Excard recommended: A4)
    (297, 210),  # ~2 ups
]

PAPERS = [
    ("Mirror Kote", "Mirror Kote"),
    ("Mirror Kote (Strong Glue)", "Mirror Kote (Strong Glue)"),
    ("Transparent OPP", "Transparent OPP"),
    ("White PP(Polyprophylene)", "White PP (Polypropylene)"),
    ("White PE (Polyethylene)", "White PE (Polyethylene)"),
    ("Synthetic Paper", "Synthetic Paper"),
    ("Printing Paper", "Printing Paper"),
    ("Brown Craft Paper", "Brown Craft Paper"),
    ("Matte Silver Polyester", "Matte Silver Polyester"),
    ("Bright Silver Polyester", "Bright Silver Polyester"),
    ("Removable Transparent OPP", "Removable Transparent OPP"),
    ("Removable White PP", "Removable White PP"),
]

# Qtys covering 1-20 sheets for typical stickers
QTYS = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000]

CATEGORY = "Rectangle/Square"


def _fetch(h, w, paper_api, qty, cookie, retries=3):
    sz = f"{h}mm x {w}mm"
    spec = {
        "Product": "Label Sticker", "OrderDesc": "Sticker",
        "Category": CATEGORY, "Size": sz,
        "Paper": paper_api, "PrintColour": "4C",
        "Package": "", "Lamination": "",
        "DeliverySheetSize": "", "CuttingMethod": "Cut to Size",
        "Quantity": str(qty), "Sheet": "0", "ArtworkDieLine": "0",
        "IsMultipleDieLine": "false", "WasteRemoval": "", "EasyPeel": "No",
        "Country": "99", "Courier": "Default",
    }
    body = json.dumps({"type": "Label Sticker", "spec": [spec]}).encode()
    hdrs = {"Authorization": "Basic " + _B64, "Api-Key": _API_KEY,
            "Content-Type": "application/json; charset=utf-8", "Cookie": cookie}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(CHECKPRICE_URL, data=body, headers=hdrs, method="POST")
            with urllib.request.urlopen(req, timeout=20, context=_CTX) as r:
                raw = r.read()
            if raw:
                d = json.loads(raw)
                p = float(str(d.get("Price", "0")).replace(",", ""))
                return p if p > 0 else None
        except Exception:
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    return None


def run(max_workers: int = 2) -> list[dict]:  # CheckPrice not concurrency-safe: workers<=2
    cookie = _get_session_cookie()
    if not cookie:
        raise SystemExit("Cookie failed")

    existing: list[dict] = []
    if SAMPLES_FILE.exists():
        try:
            existing = json.loads(SAMPLES_FILE.read_text(encoding="utf-8"))
            print(f"Resumed: {len(existing)} samples", file=sys.stderr)
        except Exception:
            pass
    # Build set of already-sampled keys
    done_keys: set[tuple] = {(r["h"], r["w"], r["paper"], r["qty"]) for r in existing}

    tasks = []
    for h, w in SIZES:
        for paper_api, paper_label in PAPERS:
            for qty in QTYS:
                if (h, w, paper_label, qty) not in done_keys:
                    tasks.append((h, w, paper_api, paper_label, qty))

    print(f"sticker CP recal: {len(tasks)} tasks pending", file=sys.stderr)
    if not tasks:
        print("Already complete.", file=sys.stderr)
        return existing

    records = list(existing)
    fail = done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_fetch, h, w, paper_api, qty, cookie): (h, w, paper_label, qty)
                for (h, w, paper_api, paper_label, qty) in tasks}
        for fu in as_completed(futs):
            h, w, paper_label, qty = futs[fu]
            p = fu.result()
            if p is not None:
                records.append({"h": h, "w": w, "paper": paper_label, "colour": "4C",
                                 "category": CATEGORY, "qty": qty, "cash": p})
            else:
                fail += 1
            done += 1
            if done % 100 == 0:
                SAMPLES_FILE.write_text(json.dumps(records), encoding="utf-8")
                print(f"  {done}/{len(tasks)} ({fail} null)", file=sys.stderr)

    SAMPLES_FILE.write_text(json.dumps(records), encoding="utf-8")
    print(f"Done: {len(records)} samples, {fail} null", file=sys.stderr)
    return records


def recalibrate(samples: list[dict] | None = None):
    """Feed CP samples into the canonical calibrate_and_report and update sticker_params_digital.json."""
    if samples is None:
        samples = json.loads(SAMPLES_FILE.read_text(encoding="utf-8"))

    from . import sticker_engine as SE

    valid = [r for r in samples if r.get("cash") and r["cash"] > 0]
    print(f"Recalibrating with {len(valid)} CP samples", file=sys.stderr)

    # Back up original ASP.NET training data if not already backed up
    canon = OUT / "sticker_samples_digital.json"
    bak = OUT / "sticker_samples_digital_aspnet_backup.json"
    if canon.exists() and not bak.exists():
        bak.write_bytes(canon.read_bytes())
        print(f"Backed up original ASP.NET data → {bak.name}", file=sys.stderr)

    # Write CP samples as the new training data for calibrate_and_report
    canon.write_text(json.dumps(valid), encoding="utf-8")
    print(f"Wrote {len(valid)} CP samples → {canon.name}", file=sys.stderr)

    # Run canonical calibration (saves sticker_params_digital.json + spot_test_report)
    SE.calibrate_and_report("digital")


if __name__ == "__main__":
    args = sys.argv[1:]
    use_existing = "--use-existing" in args
    if not use_existing:
        samples = run()
    else:
        samples = json.loads(SAMPLES_FILE.read_text(encoding="utf-8"))
    recalibrate(samples)
