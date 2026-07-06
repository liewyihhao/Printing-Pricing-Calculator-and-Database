"""Magnet EXACT sampler via /Product/CheckPrice.

Shape axes: Rectangle/Square and Custom Die-Cut (with round corner) use preset sizes.
Round is price-neutral by size — one curve covers all diameters.
Custom Die-Cut prices are identical to Rectangle/Square — both use the same curves.
Multiple Dieline is not priced (returns 0 from API) — remains CONTACT.
Lamination (Matte/Gloss/Soft Touch) is price-neutral at the base price level.

Usage:
  python -m app.magnet_cp_sampler          # sample + build params
  python -m app.magnet_cp_sampler --validate
"""
from __future__ import annotations
import base64, json, ssl, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.voucher_cp_sampler import _get_session_cookie

OUT = Path(__file__).resolve().parent.parent / "output"
SAMPLES_FILE = OUT / "magnet_cp_samples.json"
PARAMS_FILE  = OUT / "magnet_cp_params.json"

CHECKPRICE_URL = "https://devv2.excard.com.my/Product/CheckPrice"
_B64 = base64.b64encode(b"ExcardAPI:EXCARDPNCAPI").decode()
_API_KEY = "RjvaNM0xSDxcKyneFhFFxek42Nrnd4FuE9rScoHQ"
_CTX = ssl._create_unverified_context()
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065

# Preset sizes for Rectangle/Square (and Custom Die-Cut — same prices)
# format: (Printoka label, API size string)
RECT_SIZES = [
    ("50mm × 35mm",   "50mm x 35mm"),
    ("70mm × 45mm",   "70mm x 45mm"),
    ("90mm × 54mm",   "90mm x 54mm"),   # business card magnet
    ("90mm × 90mm",   "90mm x 90mm"),   # square
    ("100mm × 70mm",  "100mm x 70mm"),
    ("120mm × 80mm",  "120mm x 80mm"),
    ("148mm × 105mm", "148mm x 105mm"), # A6
]

# Round magnets: price is identical regardless of diameter (tested 45-76mm)
ROUND_API_SIZE = "50mm"

QTYS = ["10","20","30","40","50","70","100","150","200","250","300","400","500","700","1000"]


def _fetch(cat, api_size, qty, cookie, retries=3):
    spec = {
        "Product": "Magnet", "Category": cat, "Size": api_size,
        "Lamination": "Matte Lamination (Front)",
        "Quantity": str(qty), "Country": "99", "Courier": "Default",
    }
    body = json.dumps({"type": "Magnet", "spec": [spec]}).encode()
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
                time.sleep(1.0 * (attempt + 1))
    return None


def run(max_workers: int = 2) -> dict:  # CheckPrice not concurrency-safe: workers<=2
    cookie = _get_session_cookie()
    if not cookie:
        raise SystemExit("Failed to get session cookie")

    curves: dict[str, dict[str, float]] = {}
    if SAMPLES_FILE.exists():
        try:
            curves = json.loads(SAMPLES_FILE.read_text(encoding="utf-8"))
            print(f"Resumed: {len(curves)} curves", file=sys.stderr)
        except Exception:
            pass

    tasks = []
    for label, api_sz in RECT_SIZES:
        for q in QTYS:
            key = f"Rectangle/Square|{label}"
            if q not in curves.get(key, {}):
                tasks.append((key, "Rectangle/Square", api_sz, q))
    for q in QTYS:
        key = "Round"
        if q not in curves.get(key, {}):
            tasks.append((key, "Round", ROUND_API_SIZE, q))

    print(f"magnet CP: {len(tasks)} tasks pending", file=sys.stderr)
    if not tasks:
        print("Already complete.", file=sys.stderr)
        return curves

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_fetch, cat, sz, q, cookie): (key, q)
                for (key, cat, sz, q) in tasks}
        for fu in as_completed(futs):
            key, q = futs[fu]
            p = fu.result()
            if p is not None:
                curves.setdefault(key, {})[q] = p

    SAMPLES_FILE.write_text(json.dumps(curves), encoding="utf-8")
    print(f"Done: {len(curves)} curves", file=sys.stderr)
    return curves


def build_params(curves: dict | None = None) -> dict:
    if curves is None:
        curves = json.loads(SAMPLES_FILE.read_text(encoding="utf-8"))

    # Rect sizes list (preserving order)
    rect_size_labels = [label for label, _ in RECT_SIZES]
    rect_curves: dict[str, dict[str, float]] = {}
    for label in rect_size_labels:
        key = f"Rectangle/Square|{label}"
        if key in curves and curves[key]:
            rect_curves[label] = {str(q): p for q, p in curves[key].items()}

    round_curve = curves.get("Round", {})

    params = {
        "source": "checkprice-api",
        "type": "Magnet",
        "note": ("Rectangle/Square and Custom Die-Cut share the same price table. "
                 "Round is size-neutral. Multiple Dieline: contact us."),
        "rect_sizes": rect_size_labels,
        "rect_curves": rect_curves,
        "round_curve": {str(q): p for q, p in round_curve.items()},
        "weight_factor": WEIGHT_FACTOR,
        "tier_discounts": TIER_DISCOUNTS,
    }
    PARAMS_FILE.write_text(json.dumps(params, indent=2), encoding="utf-8")
    total = sum(len(v) for v in rect_curves.values()) + len(round_curve)
    print(f"Wrote {PARAMS_FILE}: {len(rect_curves)} rect sizes + round, {total} pts")
    return params


def validate(params: dict | None = None, n: int = 6):
    import random
    if params is None:
        params = json.loads(PARAMS_FILE.read_text(encoding="utf-8"))
    cookie = _get_session_cookie()
    errors = []

    # Validate a few rect sizes
    items = list(params["rect_curves"].items())
    for label, qmap in random.sample(items, min(n, len(items))):
        api_sz = next(a for l, a in RECT_SIZES if l == label)
        qtys = sorted(qmap.keys(), key=int)
        q = qtys[len(qtys) // 2]
        expected = qmap[q]
        got = _fetch("Rectangle/Square", api_sz, q, cookie)
        pct = abs(got - expected) / expected * 100 if got else 999
        status = "OK" if pct < 0.01 else "MISMATCH"
        print(f"  {status} rect {label} q={q}: expected={expected} got={got} ({pct:.2f}%)")
        if pct > 0.01:
            errors.append((label, q, expected, got))

    # Validate round
    q = "100"
    expected = params["round_curve"].get(q)
    got = _fetch("Round", ROUND_API_SIZE, q, cookie)
    pct = abs(got - expected) / expected * 100 if got and expected else 999
    status = "OK" if pct < 0.01 else "MISMATCH"
    print(f"  {status} Round q={q}: expected={expected} got={got} ({pct:.2f}%)")
    if pct > 0.01:
        errors.append(("Round", q, expected, got))

    print(f"Validated: {len(errors)} errors")
    return errors


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--validate" in args:
        validate()
    else:
        curves = run()
        build_params(curves)
        validate()
