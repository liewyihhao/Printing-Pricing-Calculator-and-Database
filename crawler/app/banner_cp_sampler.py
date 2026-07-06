"""Banner CheckPrice sampler — enumerate all 20 sizes × qtys 1-300 via v4 API.

Saves output/banner_cp_samples.json:
  {size: {qty: price}, ...}   (material is price-neutral, eyelets additive)

Usage:
  python -m app.banner_cp_sampler
  python -m app.banner_cp_sampler --build   # also builds params + validates
"""
from __future__ import annotations
import argparse, json, sys, time, math
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
SAMPLES_FILE = OUT / "banner_cp_samples.json"
PARAMS_FILE = OUT / "banner_plx_params.json"

# All 20 sizes with their mandatory orientation
SIZES = [
    ("3ft x 2ft", "Landscape"),
    ("4ft x 2ft", "Landscape"),
    ("6ft x 2ft", "Landscape"),
    ("4ft x 3ft", "Landscape"),
    ("8ft x 3ft", "Landscape"),
    ("10ft x 3ft", "Landscape"),
    ("8ft x 4ft", "Landscape"),
    ("10ft x 4ft", "Landscape"),
    ("18ft x 3ft", "Landscape"),
    ("20ft x 4ft", "Landscape"),
    ("2ft x 3ft", "Portrait"),
    ("2ft x 4ft", "Portrait"),
    ("2ft x 6ft", "Portrait"),
    ("3ft x 4ft", "Portrait"),
    ("3ft x 8ft", "Portrait"),
    ("3ft x 10ft", "Portrait"),
    ("4ft x 8ft", "Portrait"),
    ("4ft x 10ft", "Portrait"),
    ("3ft x 18ft", "Portrait"),
    ("4ft x 20ft", "Portrait"),
]
QTY_RANGE = range(1, 301)  # 1-300 inclusive

# Eyelet delta: (top_eyelet - 2) * 5 + (bottom_eyelet - 2) * 5 per banner
# Material: Tarpaulin 300gsm == 380gsm (price-neutral, verified)
MATERIAL = "Tarpaulin 300gsm"
TOP_EYELET = 2
BOT_EYELET = 2

# CheckPrice API
import base64, ssl, urllib.request
CHECKPRICE_URL = "https://devv2.excard.com.my/Product/CheckPrice"
_HDR = {
    "Authorization": "Basic " + base64.b64encode(b"ExcardAPI:EXCARDPNCAPI").decode(),
    "Api-Key": "RjvaNM0xSDxcKyneFhFFxek42Nrnd4FuE9rScoHQ",
    "Content-Type": "application/json; charset=utf-8",
}
_CTX = ssl._create_unverified_context()


def _fetch(size: str, orientation: str, qty: int, retries: int = 3) -> float | None:
    spec = {
        "Product": "Banner", "Size": size, "Material": MATERIAL,
        "Orientation": orientation, "Quantity": str(qty),
        "PrintColour": "4C (Front)", "Country": "99", "Courier": "Default",
        "Paper": "", "Package": "Normal", "Lamination": "",
        "TopEyelet": str(TOP_EYELET), "BottomEyelet": str(BOT_EYELET),
    }
    body = json.dumps({"type": "Banner", "spec": [spec]}).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(CHECKPRICE_URL, data=body, headers=_HDR, method="POST")
            with urllib.request.urlopen(req, timeout=20, context=_CTX) as r:
                raw = r.read()
            if not raw:
                continue
            d = json.loads(raw.decode())
            p = float(str(d.get("Price", "0")).replace(",", ""))
            return p if p > 0 else None
        except Exception:
            if attempt < retries - 1:
                time.sleep(1.0 * (attempt + 1))
    return None


def run(max_workers: int = 2):  # CheckPrice not concurrency-safe: workers<=2
    # Load existing samples for resume
    existing: dict[str, dict[str, float]] = {}
    if SAMPLES_FILE.exists():
        existing = json.loads(SAMPLES_FILE.read_text())

    tasks = []
    for size, orient in SIZES:
        cur = existing.get(size, {})
        for qty in QTY_RANGE:
            if str(qty) not in cur:
                tasks.append((size, orient, qty))

    total_needed = len(tasks)
    print(f"Banner CP sampler: {total_needed} calls to fetch "
          f"({sum(len(v) for v in existing.values())} already cached)", flush=True)

    if not tasks:
        print("All done — samples complete.")
        return existing

    done = 0
    fails = []
    lock_data = dict(existing)

    def _work(item):
        size, orient, qty = item
        p = _fetch(size, orient, qty)
        return size, qty, p

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_work, t): t for t in tasks}
        for fut in as_completed(futs):
            size, qty, p = fut.result()
            done += 1
            if p is not None:
                lock_data.setdefault(size, {})[str(qty)] = p
            else:
                fails.append((size, qty))
            if done % 100 == 0 or done == total_needed:
                pct = done / total_needed * 100
                print(f"  {done}/{total_needed} ({pct:.0f}%), fails={len(fails)}", flush=True)
                # Checkpoint save
                SAMPLES_FILE.write_text(json.dumps(lock_data, sort_keys=True))

    SAMPLES_FILE.write_text(json.dumps(lock_data, sort_keys=True))
    print(f"Done. {len(fails)} failures: {fails[:10]}")
    return lock_data


def build_params(data: dict) -> dict:
    """Build pricelist params from sampled data.

    params = {
      sizes: {size: {qty: price, ...}, ...},
      eyelet_delta_per_extra: 5.0,   # RM per each extra eyelet above minimum of 2
      material_neutral: true,         # 300gsm == 380gsm
      note: "..."
    }
    """
    params: dict = {
        "engine": "banner_checkprice",
        "eyelet_delta_per_extra": 5.0,
        "material_neutral": True,
        "min_eyelets": 2,
        "sizes": {},
        "note": (
            "Exact per-size price lookup from v4 CheckPrice API. "
            "Qty range 1-300. Material is price-neutral (300gsm=380gsm). "
            "Eyelet delta: (top_eyelet-2)*5 + (bot_eyelet-2)*5 RM per banner."
        ),
    }
    for size, _, in SIZES:
        curve = data.get(size, {})
        if curve:
            # Store as {str(qty): float} for exact lookup
            params["sizes"][size] = {str(q): curve[str(q)] for q in range(1, 301) if str(q) in curve}
    return params


def validate(params: dict, data: dict, n_spot: int = 50):
    import random
    errs = []
    sizes_p = params["sizes"]
    for _ in range(n_spot):
        size = random.choice(list(sizes_p.keys()))
        qty = random.randint(1, 300)
        actual = data.get(size, {}).get(str(qty))
        predicted = sizes_p[size].get(str(qty))
        if actual is not None and predicted is not None:
            err = abs(actual - predicted) / actual if actual else 0
            errs.append(err)
    if errs:
        import statistics
        print(f"Validation ({len(errs)} spots): median={statistics.median(errs)*100:.2f}%, "
              f"max={max(errs)*100:.2f}%")
    else:
        print("No validation points.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true", help="Also build params after sampling")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    data = run(max_workers=args.workers)

    if args.build:
        params = build_params(data)
        total_pts = sum(len(v) for v in params["sizes"].values())
        print(f"Params built: {len(params['sizes'])} sizes, {total_pts} total price points")
        validate(params, data)
        PARAMS_FILE.write_text(json.dumps(params))
        print(f"Saved → {PARAMS_FILE}")


if __name__ == "__main__":
    main()
