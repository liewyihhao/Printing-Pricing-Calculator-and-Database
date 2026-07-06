"""Bill-Book EXACT sampler via direct /Product/CheckPrice.

Schema: type='BILL BOOK'. Price axes: packform × size × orientation × layers × colour × sets.
Paper-layer colour is price-neutral (all NCR White). Numbering is price-neutral.
HolePunch is additive (sampled separately at 2 qtys, then treated as a per-book delta).

Usage:
  python -m app.billbook_cp_sampler          # sample all (background-safe, resumes)
  python -m app.billbook_cp_sampler --build  # also build plx_params + validate
"""
from __future__ import annotations
import json, math, re, ssl, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.voucher_cp_sampler import _get_session_cookie
from app import checkprice_enum as C

OUT = Path(__file__).resolve().parent.parent / "output"
SAMPLES_FILE = OUT / "billbook_cp_samples.json"
PARAMS_FILE  = OUT / "billbook_plx_params.json"

CHECKPRICE_URL = "https://devv2.excard.com.my/Product/CheckPrice"
import base64
_B64 = base64.b64encode(b"ExcardAPI:EXCARDPNCAPI").decode()
_API_KEY = "RjvaNM0xSDxcKyneFhFFxek42Nrnd4FuE9rScoHQ"
_CTX = ssl._create_unverified_context()
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065

# Printoka-label → API size string (strip parenthetical prefix)
_SIZE_MAP = {
    "145mm x 210mm": "145mm x 210mm",
    "A4 (210mm x 297mm)": "210mm x 297mm",
    "B5 (176mm x 250mm)": "176mm x 250mm",
    "90mm x 140mm": "90mm x 140mm",
    "90mm x 177mm": "90mm x 177mm",
    "95mm x 210mm": "95mm x 210mm",
    "95mm x 225mm": "95mm x 225mm",
    "105mm x 145mm": "105mm x 145mm",
    "105mm x 175mm": "105mm x 175mm",
    "107mm x 190mm": "107mm x 190mm",
    "110mm x 210mm": "110mm x 210mm",
    "120mm x 210mm": "120mm x 210mm",
    "120mm x 230mm": "120mm x 230mm",
    "125mm x 175mm": "125mm x 175mm",
    "135mm x 210mm": "135mm x 210mm",
    "145mm x 148mm": "145mm x 148mm",
    "145mm x 190mm": "145mm x 190mm",
    "148mm x 190mm": "148mm x 190mm",
    "148mm x 291mm": "148mm x 291mm",
    "160mm x 240mm": "160mm x 240mm",
    "165mm x 210mm": "165mm x 210mm",
    "170mm x 190mm": "170mm x 190mm",
    "173mm x 206mm": "173mm x 206mm",
    "180mm x 280mm": "180mm x 280mm",
    "190mm x 210mm": "190mm x 210mm",
    "190mm x 270mm": "190mm x 270mm",
    "190mm x 290mm": "190mm x 290mm",
    "190mm x 297mm": "190mm x 297mm",
    "192mm x 268mm": "192mm x 268mm",
    "194mm x 205mm": "194mm x 205mm",
    "206mm x 240mm": "206mm x 240mm",
    "206mm x 330mm": "206mm x 330mm",
    "210mm x 270mm": "210mm x 270mm",
    "210mm x 291mm": "210mm x 291mm",
    "B4 (250mm x 353mm)": "250mm x 353mm",
    "291mm x 420mm": "291mm x 420mm",
    "F3 (330mm x 420mm)": "330mm x 420mm",
}

# Colour-label → API string
_COLOUR_MAP = {
    "1C (Front)": "1C (Front)",
    "2C (Front)": "2C (Front)",
    "4C (Front)": "4C (Front)",
    "1C (Both)": "1C (Both)",
    "2C (Front) / 1C (Back)": "2C (Front) + 1C (Back)",
    "4C (Front) / 1C (Back)": "4C (Front) + 1C (Back)",
}

PACKFORMS = ["Book", "Pad"]
SIZES     = list(_SIZE_MAP.keys())
# Default orientation per packform. Orientation is price-affecting but the Printoka
# UI currently treats it as neutral (matching the old engine). We price at the default
# so the upgrade covers the main price axes (packform × size × layers × colour × sets).
DEFAULT_ORIENT = {
    "Book": "Landscape - Left side binding",
    "Pad":  "Landscape - Left side binding",
}
LAYERS   = ["2", "3", "4", "5", "6"]
COLOURS  = list(_COLOUR_MAP.keys())
SETS     = ["50", "100"]  # 100 only valid for 2-layer

# Orderable quantities on Excard bill-book order form
QTYS = ["10","20","30","40","50","60","70","80","90","100","150","200","300","500","1000"]

NCR_PAPER = "NCR White 50gsm"


def _paper_str(num_layers: int) -> str:
    return ",".join([NCR_PAPER] * num_layers)


def _spec(packform, api_size, orientation, layers_n, api_colour, sets_val, qty):
    return {
        "Product": "BILL BOOK",
        "Size": api_size,
        "IsCustomSize": "No",
        "CustomSize": "",
        "BindingType": packform,
        "Orientation": orientation,
        "PaperMaterials": "NCR",
        "Layers": str(layers_n),
        "Paper": _paper_str(layers_n),
        "PrintColour": api_colour,
        "Front K": "", "Front M": "", "Back K": "",
        "BackPrintLayer": "",
        "Quantity": str(qty),
        "Sets": sets_val,
        "IsNumbering": "yes",
        "HolePunch": "No",
        "IsCopyChange": "false",
        "IsDifferentArtwork": "false",
        "Ccs": "", "CcsFontSize": "", "InkColour": "",
        "NumberFrom": "", "NumberTo": "",
        "IsLastLayerPerforation": "No",
        "Country": "99",
        "Courier": "Default",
    }


def _fetch(spec, cookie, retries=3):
    body = json.dumps({"type": "BILL BOOK", "spec": [spec]}).encode()
    hdrs = {"Authorization": "Basic " + _B64, "Api-Key": _API_KEY,
            "Content-Type": "application/json; charset=utf-8", "Cookie": cookie}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(CHECKPRICE_URL, data=body, headers=hdrs, method="POST")
            with urllib.request.urlopen(req, timeout=25, context=_CTX) as r:
                raw = r.read()
            if raw:
                d = json.loads(raw)
                p = float(str(d.get("Price", "0")).replace(",", ""))
                return p if p > 0 else None
        except Exception:
            if attempt < retries - 1:
                time.sleep(1.0 * (attempt + 1))
    return None


def _make_key(packform, size_label, layers_n, colour_label, sets_val):
    return f"{packform}|{size_label}|{layers_n}L|{colour_label}|sets={sets_val}"


def _build_tasks() -> list[tuple]:
    tasks = []
    for packform in PACKFORMS:
        orient = DEFAULT_ORIENT[packform]
        for size_label in SIZES:
            api_size = _SIZE_MAP[size_label]
            for ln in LAYERS:
                layers_n = int(ln)
                for colour_label in COLOURS:
                    api_colour = _COLOUR_MAP[colour_label]
                    sets_options = ["50", "100"] if layers_n == 2 else ["50"]
                    for sets_val in sets_options:
                        key = _make_key(packform, size_label, layers_n, colour_label, sets_val)
                        for qty in QTYS:
                            tasks.append((key, qty, packform, api_size, orient, layers_n, api_colour, sets_val))
    return tasks


def run(max_workers: int = 2) -> dict:
    # NB: CheckPrice is NOT concurrency-safe — the server keeps one order-session per account
    # cookie, so >=4 concurrent calls corrupt prices (~0.787x underprice). workers<=2 is clean.
    # See memory checkprice-concurrency-corruption.
    cookie = _get_session_cookie()
    if not cookie:
        raise SystemExit("Failed to get session cookie")

    # Load existing samples (resume support)
    curves: dict[str, dict[str, float]] = {}
    if SAMPLES_FILE.exists():
        try:
            curves = json.loads(SAMPLES_FILE.read_text(encoding="utf-8"))
            print(f"Resumed: {len(curves)} curves loaded", file=sys.stderr)
        except Exception:
            pass

    tasks = _build_tasks()
    # Filter out already-sampled (key, qty) pairs
    pending = [(k, q, pf, sz, ort, ln, cl, sv) for (k, q, pf, sz, ort, ln, cl, sv) in tasks
               if q not in curves.get(k, {})]
    print(f"billbook CP: {len(tasks)} total, {len(pending)} pending", file=sys.stderr)
    if not pending:
        print("Already complete.", file=sys.stderr)
        return curves

    done = fail = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {
            ex.submit(_fetch, _spec(pf, sz, ort, ln, cl, sv, q), cookie): (k, q)
            for (k, q, pf, sz, ort, ln, cl, sv) in pending
        }
        for fu in as_completed(futs):
            k, q = futs[fu]
            p = fu.result()
            if p is not None:
                curves.setdefault(k, {})[q] = p
            else:
                fail += 1
            done += 1
            if done % 500 == 0:
                SAMPLES_FILE.write_text(json.dumps(curves), encoding="utf-8")
                print(f"  {done}/{len(pending)} ({fail} null)", file=sys.stderr)

    SAMPLES_FILE.write_text(json.dumps(curves), encoding="utf-8")
    print(f"Done: {len(curves)} curves, {fail}/{len(pending)} null", file=sys.stderr)
    return curves


def build_params(curves: dict | None = None) -> dict:
    """Build plx_params.json from sampled curves."""
    if curves is None:
        curves = json.loads(SAMPLES_FILE.read_text(encoding="utf-8"))

    # Filter out empty/null curves and invalid combos (no price returned at all)
    valid = {k: v for k, v in curves.items() if v}
    print(f"build_params: {len(valid)} valid curves from {len(curves)} total", file=sys.stderr)

    # Key format: "packform|size|NL|colour|sets=N"
    axes = ["packform", "size", "layers", "colour", "sets"]
    dist: dict[str, list] = {a: [] for a in axes}
    for k in valid:
        parts = k.split("|")
        if len(parts) < 5:
            continue
        packform, size_label, layers_str, colour_label, sets_str = parts[:5]
        layers_n = layers_str.replace("L", "")
        sets_val = sets_str.replace("sets=", "")
        vals = [packform, size_label, layers_n, colour_label, sets_val]
        for a, v in zip(axes, vals):
            if v not in dist[a]:
                dist[a].append(v)

    # Restructure curves with cleaned keys: "packform|size|layers|colour|sets"
    clean: dict[str, dict[str, float]] = {}
    for k, qmap in valid.items():
        parts = k.split("|")
        if len(parts) < 5:
            continue
        packform, size_label, layers_str, colour_label, sets_str = parts[:5]
        layers_n = layers_str.replace("L", "")
        sets_val = sets_str.replace("sets=", "")
        clean_key = f"{packform}|{size_label}|{layers_n}|{colour_label}|{sets_val}"
        clean[clean_key] = {str(q): p for q, p in qmap.items()}

    params = {
        "source": "checkprice-api",
        "type": "BILL BOOK",
        "rows": sum(len(v) for v in clean.values()),
        "axisCols": axes,
        "distinct": dist,
        "curves": clean,
        "weight_factor": WEIGHT_FACTOR,
        "tier_discounts": TIER_DISCOUNTS,
    }
    PARAMS_FILE.write_text(json.dumps(params), encoding="utf-8")
    print(f"Wrote {PARAMS_FILE}: {len(clean)} curves", file=sys.stderr)
    return params


def validate(params: dict | None = None, n_samples: int = 10):
    """Spot-check a few combos from the params against live CheckPrice."""
    import random
    if params is None:
        params = json.loads(PARAMS_FILE.read_text(encoding="utf-8"))
    cookie = _get_session_cookie()
    curves = params["curves"]
    keys = [k for k in curves if curves[k]]
    sample_keys = random.sample(keys, min(n_samples, len(keys)))
    errors = []
    for k in sample_keys:
        parts = k.split("|")
        if len(parts) < 5:
            continue
        packform, size_label, layers_n, colour_label, sets_val = parts[:5]
        api_size = _SIZE_MAP.get(size_label, size_label)
        api_colour = _COLOUR_MAP.get(colour_label, colour_label)
        orient = DEFAULT_ORIENT[packform]
        qtys = sorted(curves[k].keys(), key=int)
        qty = qtys[len(qtys)//2]
        expected = curves[k][qty]
        spec = _spec(packform, api_size, orient, int(layers_n), api_colour, sets_val, qty)
        got = _fetch(spec, cookie)
        pct = abs(got - expected) / expected * 100 if got else 999
        status = "OK" if pct < 0.01 else "MISMATCH"
        print(f"{status} {k} q={qty}: expected={expected} got={got} diff={pct:.2f}%")
        if pct > 0.01:
            errors.append((k, qty, expected, got))
    print(f"Validated {len(sample_keys)} combos, {len(errors)} errors")
    return errors


def write_options(params: dict | None = None):
    """Convert billbook_plx_params.json -> output/v4_options/bill-book_options.json in the
    standard capture shape consumed by build_standalone._wire_pricelist_products."""
    if params is None:
        params = json.loads(PARAMS_FILE.read_text(encoding="utf-8"))
    clean = {k: v for k, v in params["curves"].items() if v}
    axes = ["Binding", "Size", "Layers", "Print Colour", "Sets"]
    dist = {a: [] for a in axes}
    for k in clean:
        for a, v in zip(axes, k.split("|")):
            if v not in dist[a]:
                dist[a].append(v)
    deps = {}
    for k in clean:
        parts = k.split("|"); sub = deps.setdefault(parts[0], {a: [] for a in axes[1:]})
        for a, v in zip(axes[1:], parts[1:]):
            if v not in sub[a]:
                sub[a].append(v)
    out = {"slug": "bill-book", "source": "checkprice-api",
           "rows": sum(len(c) for c in clean.values()), "optionCols": axes, "primary": "Binding",
           "deps": deps, "imageField": None, "distinct": dist, "imageOptions": {},
           "priceMeta": {"priceCol": "Price", "qtyCol": "Quantity", "axisCols": axes,
                         "nCurves": len(clean)}, "curves": clean}
    (OUT / "v4_options" / "bill-book_options.json").write_text(json.dumps(out))
    print(f"wrote v4_options/bill-book_options.json: {len(clean)} curves", file=sys.stderr)
    return out


def validate_random(n_samples=60):
    """Sequential (workers=1) spot-check to measure corruption in the stored sample. Corruption
    only LOWERS price, so any config whose lone sequential fetch is HIGHER than stored was
    corrupted during sampling. Returns list of (key, qty, stored, live)."""
    import random
    params = json.loads(PARAMS_FILE.read_text(encoding="utf-8"))
    cookie = _get_session_cookie()
    curves = {k: v for k, v in params["curves"].items() if v}
    keys = random.sample(list(curves), min(n_samples, len(curves)))
    bad = []
    for k in keys:
        packform, size_label, layers_n, colour_label, sets_val = k.split("|")[:5]
        api_size = _SIZE_MAP.get(size_label, size_label)
        api_colour = _COLOUR_MAP.get(colour_label, colour_label)
        qtys = sorted(curves[k], key=int); qty = qtys[len(qtys) // 2]
        stored = curves[k][qty]
        got = _fetch(_spec(packform, api_size, DEFAULT_ORIENT[packform], int(layers_n), api_colour, sets_val, qty), cookie)
        if got and abs(got - stored) / stored > 0.005:
            bad.append((k, qty, stored, got))
            print(f"  CORRUPT {k} q={qty}: stored={stored} live={got} ({got/stored:.4f}x)", file=sys.stderr)
    print(f"validate_random: {len(bad)}/{len(keys)} corrupted", file=sys.stderr)
    return bad


def _interp_excl(curve: dict, target_q: str) -> float | None:
    """log-log interpolate the price at target_q from all OTHER points in the curve."""
    pts = sorted((int(q), p) for q, p in curve.items() if q != target_q and p)
    if len(pts) < 2:
        return None
    xs = [math.log(q) for q, _ in pts]; ys = [math.log(p) for _, p in pts]
    x = math.log(int(target_q))
    if x <= xs[0]:
        # extrapolate using first two
        t = (x - xs[0]) / (xs[1] - xs[0]); return math.exp(ys[0] + t * (ys[1] - ys[0]))
    if x >= xs[-1]:
        t = (x - xs[-2]) / (xs[-1] - xs[-2]); return math.exp(ys[-2] + t * (ys[-1] - ys[-2]))
    for i in range(1, len(xs)):
        if x <= xs[i]:
            t = (x - xs[i-1]) / (xs[i] - xs[i-1]); return math.exp(ys[i-1] + t * (ys[i] - ys[i-1]))
    return None


def _parse_raw_key(k):
    packform, size_label, layers_str, colour_label, sets_str = k.split("|")[:5]
    return (packform, size_label, layers_str.replace("L", ""), colour_label, sets_str.replace("sets=", ""))


def _theilsen_suspects(curve: dict, thresh: float = 0.90):
    """Robust log-log Theil-Sen fit of price vs qty; flag qtys whose price sits below the
    fitted trend by more than (1-thresh). Resistant to multiple (~0.787x) outliers per curve."""
    pts = sorted((int(q), p) for q, p in curve.items() if p)
    if len(pts) < 4:
        return []
    xs = [math.log(q) for q, _ in pts]; ys = [math.log(p) for _, p in pts]
    slopes = [(ys[j] - ys[i]) / (xs[j] - xs[i])
              for i in range(len(xs)) for j in range(i + 1, len(xs)) if xs[j] != xs[i]]
    slopes.sort(); slope = slopes[len(slopes) // 2]
    inters = sorted(ys[i] - slope * xs[i] for i in range(len(xs)))
    inter = inters[len(inters) // 2]
    out = []
    for (q, p), x in zip(pts, xs):
        pred = math.exp(inter + slope * x)
        if p / pred < thresh:
            out.append(str(q))
    return out


def repair(passes: int = 6):
    """Detect corruption (~0.787x underprice) in billbook_cp_samples.json and re-fetch just
    the suspect points SEQUENTIALLY (workers=1 = no session overlap = clean). Suspects are
    found with a robust Theil-Sen per-curve fit (handles multiple outliers per curve).
    Iterates until no suspects remain (corruption is independent per fetch)."""
    cookie = _get_session_cookie()
    curves = json.loads(SAMPLES_FILE.read_text(encoding="utf-8"))
    total_fixed = 0
    for it in range(passes):
        suspects = []
        for k, curve in curves.items():
            for q in _theilsen_suspects(curve):
                suspects.append((k, q))
        if not suspects:
            print(f"repair pass {it}: 0 suspects — clean", file=sys.stderr)
            break
        print(f"repair pass {it}: {len(suspects)} suspects, re-fetching sequentially...", file=sys.stderr)
        fixed = 0
        for k, q in suspects:
            pf, size_label, layers_n, colour_label, sets_val = _parse_raw_key(k)
            api_size = _SIZE_MAP.get(size_label, size_label)
            api_colour = _COLOUR_MAP.get(colour_label, colour_label)
            got = _fetch(_spec(pf, api_size, DEFAULT_ORIENT[pf], int(layers_n), api_colour, sets_val, q), cookie)
            if got and got > curves[k][q]:
                curves[k][q] = got; fixed += 1
        total_fixed += fixed
        SAMPLES_FILE.write_text(json.dumps(curves), encoding="utf-8")
        print(f"  fixed {fixed}/{len(suspects)}", file=sys.stderr)
    print(f"repair done: {total_fixed} points fixed", file=sys.stderr)
    params = build_params(curves)
    write_options(params)
    return curves


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--options" in args:      # just convert existing params -> options shape
        write_options()
    elif "--validate" in args:
        validate_random()
    elif "--repair" in args:
        repair()
    else:
        curves = run()
        if "--build" in args:
            params = build_params(curves)
            validate(params)
            write_options(params)
