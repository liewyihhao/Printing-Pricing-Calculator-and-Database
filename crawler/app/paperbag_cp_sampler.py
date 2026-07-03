"""Paper Bag CheckPrice sampler — enumerate 7 models x 2 papers x 3 lams x 29 qtys.

Saves output/paperbag_cp_samples.json + builds output/paperbag_plx_params.json.

Key findings:
  - Hot Stamping: price-neutral (all sizes same price)
  - Rope Colour: price-neutral (all colours same price)
  - Lamination: Matte+Spot UV adds a significant delta; Gloss=Matte (same price)
  - Paper: small delta (~RM2 per 100 bags)

Usage:
  python -m app.paperbag_cp_sampler         # sample + build params
  python -m app.paperbag_cp_sampler --only-build  # build params from existing samples
"""
from __future__ import annotations
import json, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
SAMPLES_FILE = OUT / "paperbag_cp_samples.json"
PARAMS_FILE = OUT / "paperbag_plx_params.json"

MODEL_SIZE = {
    "PBG 001": "180mm x 80mm x 230mm",
    "PBG 002": "220mm x 80mm x 230mm",
    "PBG 003": "250mm x 95mm x 350mm",
    "PBG 004": "200mm x 95mm x 290mm",
    "PBG 005": "320mm x 95mm x 230mm",
    "PBG 006": "370mm x 120mm x 295mm",
    "PBG 007": "320mm x 120mm x 420mm",
}
PAPERS = ["Gloss Art Paper 157gsm", "Gloss Art Card 190gsm"]
LAMINATIONS = ["Gloss Lamination", "Matte Lamination", "Matte Lamination + Spot UV"]
QTYS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500,
        2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000, 6500, 7000,
        7500, 8000, 8500, 9000, 9500, 10000]

# CheckPrice API
import base64, ssl, urllib.request
CHECKPRICE_URL = "https://devv2.excard.com.my/Product/CheckPrice"
_HDR = {
    "Authorization": "Basic " + base64.b64encode(b"ExcardAPI:EXCARDPNCAPI").decode(),
    "Api-Key": "RjvaNM0xSDxcKyneFhFFxek42Nrnd4FuE9rScoHQ",
    "Content-Type": "application/json; charset=utf-8",
}
_CTX = ssl._create_unverified_context()


def _fetch(model: str, paper: str, lam: str, qty: int, retries: int = 3) -> float | None:
    size = MODEL_SIZE[model]
    spec = {
        "Product": "Paper Bag", "Model": model, "Size": size, "Paper": paper,
        "Lamination": lam, "RopeColour": "Black", "HotStampingSize": "Not Required",
        "Quantity": str(qty), "PrintColour": "4C (Front)",
        "Country": "99", "Courier": "Default",
    }
    body = json.dumps({"type": "Paper Bag", "spec": [spec]}).encode()
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


def run(max_workers: int = 8):
    existing: dict = {}
    if SAMPLES_FILE.exists():
        existing = json.loads(SAMPLES_FILE.read_text())

    tasks = []
    for model in MODEL_SIZE:
        for paper in PAPERS:
            for lam in LAMINATIONS:
                for qty in QTYS:
                    key = f"{model}|{paper}|{lam}"
                    if str(qty) not in existing.get(key, {}):
                        tasks.append((model, paper, lam, qty))

    total = len(tasks)
    cached = sum(len(v) for v in existing.values())
    print(f"Paperbag CP sampler: {total} calls to fetch ({cached} cached)", flush=True)
    if not tasks:
        print("All done.")
        return existing

    done = 0; fails = []
    lock_data = dict(existing)

    def _work(item):
        model, paper, lam, qty = item
        p = _fetch(model, paper, lam, qty)
        return model, paper, lam, qty, p

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_work, t): t for t in tasks}
        for fut in as_completed(futs):
            model, paper, lam, qty, p = fut.result()
            done += 1
            key = f"{model}|{paper}|{lam}"
            if p is not None:
                lock_data.setdefault(key, {})[str(qty)] = p
            else:
                fails.append((model, paper, lam, qty))
            if done % 100 == 0 or done == total:
                pct = done / total * 100
                print(f"  {done}/{total} ({pct:.0f}%), fails={len(fails)}", flush=True)
                SAMPLES_FILE.write_text(json.dumps(lock_data, sort_keys=True))

    SAMPLES_FILE.write_text(json.dumps(lock_data, sort_keys=True))
    print(f"Done. {len(fails)} failures: {fails[:5]}")
    return lock_data


def build_params(data: dict) -> dict:
    params = {
        "engine": "paperbag_checkprice",
        "models": list(MODEL_SIZE.keys()),
        "model_size": MODEL_SIZE,
        "papers": PAPERS,
        "laminations": LAMINATIONS,
        "rope_colour_neutral": True,
        "hot_stamping_neutral": True,
        "curves": {},
        "note": (
            "Exact pricelist from v4 CheckPrice API. Axes: model x paper x lamination x qty. "
            "Rope colour and hot stamping are price-neutral (verified). "
            "Lamination delta: Gloss=Matte; Matte+Spot UV adds a large premium."
        ),
    }
    for key, curve in data.items():
        params["curves"][key] = {str(q): curve[str(q)] for q in QTYS if str(q) in curve}
    return params


def main():
    build_only = "--only-build" in sys.argv
    if build_only:
        data = json.loads(SAMPLES_FILE.read_text())
    else:
        data = run()

    params = build_params(data)
    total = sum(len(v) for v in params["curves"].values())
    print(f"Params: {len(params['curves'])} curves, {total} price points")
    PARAMS_FILE.write_text(json.dumps(params))
    print(f"Saved to {PARAMS_FILE}")


if __name__ == "__main__":
    main()
