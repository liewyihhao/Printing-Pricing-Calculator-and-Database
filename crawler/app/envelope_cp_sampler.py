"""Envelope CheckPrice sampler — enumerate all model x colour x qty combinations via v4 API.

Saves output/envelope_cp_samples.json:
  {model: {colour: {qty: price}, ...}, ...}

Usage:
  python -m app.envelope_cp_sampler          # sample all
  python -m app.envelope_cp_sampler --build  # also build params + validate
"""
from __future__ import annotations
import argparse, base64, json, math, sys, ssl, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
SAMPLES_FILE = OUT / "envelope_cp_samples.json"
PARAMS_FILE = OUT / "envelope_plx_params.json"
OPTIONS_FILE = OUT / "v4_options" / "envelope_options.json"

CHECKPRICE_URL = "https://devv2.excard.com.my/Product/CheckPrice"
_HDR = {
    "Authorization": "Basic " + base64.b64encode(b"ExcardAPI:EXCARDPNCAPI").decode(),
    "Api-Key": "RjvaNM0xSDxcKyneFhFFxek42Nrnd4FuE9rScoHQ",
    "Content-Type": "application/json; charset=utf-8",
}
_CTX = ssl._create_unverified_context()

TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}


def _clean_size(s: str) -> str:
    """Strip parenthetical suffixes like '(Fit DL Size)' that the API doesn't accept."""
    import re
    return re.sub(r"\s*\([^)]+\)\s*$", "", s).strip()


def _load_options():
    """Load model/size/colour/qty info from the v4 options JSON."""
    with open(OPTIONS_FILE, encoding="utf-8") as f:
        opts = json.load(f)
    deps = opts["deps"]
    # Build: model -> {size, colours, qtys}
    configs = {}
    for model, dep in deps.items():
        sizes = dep.get("Size", [])
        size = _clean_size(sizes[0]) if sizes else ""
        colours = dep.get("Print Colour", [])
        qtys = [q for q in dep.get("Quantity", []) if q != "Other" and q.isdigit()]
        configs[model] = {"size": size, "colours": colours, "qtys": qtys}
    return configs


def _fetch(model: str, size: str, colour: str, qty: str, retries: int = 3) -> float | None:
    spec = {
        "Product": "Envelope", "Size": size, "Model": model,
        "PrintColour": colour, "Quantity": qty,
        "Country": "99", "Courier": "Default",
        "Paper": "", "Lamination": "", "Package": "Normal",
    }
    body = json.dumps({"type": "Envelope", "spec": [spec]}).encode()
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


def run(max_workers: int = 2) -> dict:  # CheckPrice not concurrency-safe: workers<=2
    configs = _load_options()
    # Load existing samples
    existing: dict[str, dict[str, dict[str, float]]] = {}
    if SAMPLES_FILE.exists():
        existing = json.loads(SAMPLES_FILE.read_text(encoding="utf-8"))

    # Build task list
    tasks = []
    for model, cfg in configs.items():
        for colour in cfg["colours"]:
            for qty in cfg["qtys"]:
                if existing.get(model, {}).get(colour, {}).get(qty) is None:
                    tasks.append((model, cfg["size"], colour, qty))

    total_needed = len(tasks)
    already_done = sum(len(c) * len(q) for mc in existing.values() for q in [mc] for c in [q])
    already_done = sum(
        len(cfg) for model_data in existing.values() for cfg in model_data.values()
    )
    print(f"Envelope CP sampler: {total_needed} calls to fetch ({already_done} already cached)", flush=True)

    if not tasks:
        print("All done — samples complete.")
        return existing

    data = {m: {c: dict(qtys) for c, qtys in model_data.items()} for m, model_data in existing.items()}
    done = 0
    fails = []

    def _work(item):
        m, sz, col, qty = item
        p = _fetch(m, sz, col, qty)
        return m, col, qty, p

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_work, t): t for t in tasks}
        for fut in as_completed(futs):
            m, col, qty, p = fut.result()
            done += 1
            if p is not None:
                data.setdefault(m, {}).setdefault(col, {})[qty] = p
            else:
                fails.append((m, col, qty))
            if done % 200 == 0 or done == total_needed:
                pct = done / total_needed * 100
                print(f"  {done}/{total_needed} ({pct:.0f}%), fails={len(fails)}", flush=True)
                SAMPLES_FILE.write_text(json.dumps(data, sort_keys=True, ensure_ascii=False), encoding="utf-8")

    SAMPLES_FILE.write_text(json.dumps(data, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    print(f"Done. {len(fails)} failures: {fails[:10]}")
    return data


def build_params(data: dict) -> dict:
    """Build pricelist params (curves: {model|colour: {qty: price}})."""
    curves: dict[str, dict[str, float]] = {}
    for model, by_colour in data.items():
        for colour, by_qty in by_colour.items():
            key = f"{model}|{colour}"
            if by_qty:
                curves[key] = {q: p for q, p in sorted(by_qty.items(), key=lambda x: int(x[0]))}

    configs = _load_options()
    model_meta: dict[str, dict] = {}
    for model, cfg in configs.items():
        model_meta[model] = {"size": cfg["size"], "colours": cfg["colours"]}

    params = {
        "engine": "envelope_checkprice",
        "curves": curves,
        "model_meta": model_meta,
        "note": (
            "Exact per-(model|colour) price lookup from v4 CheckPrice API. "
            "Qty log-interpolated between sampled order quantities."
        ),
    }
    PARAMS_FILE.write_text(json.dumps(params, ensure_ascii=False), encoding="utf-8")
    print(f"Params saved: {len(curves)} curves -> {PARAMS_FILE}")
    return params


def validate(params: dict) -> None:
    """Spot-check a sample of sampled points."""
    configs = _load_options()
    data = json.loads(SAMPLES_FILE.read_text(encoding="utf-8"))
    errors = []
    from app import envelope_engine as EV
    EV._CACHE.clear()  # force reload
    for model, by_colour in list(data.items())[:5]:
        cfg = configs.get(model, {})
        size = cfg.get("size", "")
        for colour, by_qty in list(by_colour.items())[:3]:
            for qty, expected in list(by_qty.items())[:5]:
                got = EV.cash_price(model, colour, int(qty))
                err = abs(got - expected) / expected if expected else 0
                if err > 0.001:
                    errors.append((model, colour, qty, expected, got, f"{err*100:.2f}%"))
    if errors:
        print(f"VALIDATION ERRORS ({len(errors)}):")
        for e in errors[:10]:
            print(f"  {e}")
    else:
        print("Validation OK — all spot-checked points match to <0.1%")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    args = ap.parse_args()

    data = run()
    if args.build or data:
        params = build_params(data)
        if args.build:
            validate(params)
