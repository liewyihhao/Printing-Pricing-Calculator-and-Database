"""Generalized EXACT-price enumerator for v4 metrics products that price via the
/Product/CheckPrice API (no local price column, empty price-list DataTable).

Method (the universal one — see memory 'excard-readymade-pricing-api'):
 1. Drive the v4 ordering page ONCE to capture (a) a real CheckPrice request = the exact
    spec schema (`type` + spec field keys, which are camel/UPPER variants of the metrics
    columns), and (b) `window.metrics` = every VALID option combo + orderable quantities.
 2. Derive the distinct non-qty option axes and their valid combos from the metrics.
 3. Price each (combo × qty) via the direct devv2 CheckPrice endpoint (static Basic-auth +
    Api-Key + the logged-in session cookie), threaded. Field values are mapped from the
    metrics columns onto the captured spec keys by normalized-name match.
 4. Write output/v4_options/<slug>_options.json in the standard capture shape so the build
    pipeline (_wire_pricelist_products) turns it into an EXACT, validity-enforced product.

CLI:  python -m app.checkprice_enum kad-terima-kasih [--limit-axes col1,col2]
"""
from __future__ import annotations
import asyncio, base64, json, re, ssl, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from playwright.async_api import async_playwright
from app import browser as B
from app.readymade_enum import login_v4

OUT = Path(__file__).resolve().parent.parent / "output"
V4 = "https://v4.excard.com.my/ordering/"
CHECKPRICE_URL = "https://devv2.excard.com.my/Product/CheckPrice"
_B64 = base64.b64encode(b"ExcardAPI:EXCARDPNCAPI").decode()
_API_KEY = "RjvaNM0xSDxcKyneFhFFxek42Nrnd4FuE9rScoHQ"
_CTX = ssl._create_unverified_context()

_NOISE = re.compile(r"price|date|process\s*day|weight|print\s*method|fee|delivery|shipment|compulsory", re.I)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


async def _capture(slug: str, price_axes=None):
    """Return (schema_template, type_str, cols, agg, qty_col, cookie).
    `agg` = {combo_tuple(over price_axes or all option axes) -> sorted qty list}, computed
    IN THE BROWSER so huge metrics arrays (e.g. kad-kahwin 388k rows) never cross the bridge.
    `price_axes` (list of metrics column names) restricts the combo axes to the price-
    determining ones (drop price-neutral axes like Lamination/Folding to avoid combinatorial blowup)."""
    hold = {}
    async with async_playwright() as pw:
        b = await B.launch(pw); page = await b.new_page()
        await login_v4(page)

        async def on(r):
            if "CheckPrice" in r.url and "req" not in hold:
                try: hold["req"] = r.request.post_data_json
                except Exception: pass
        page.on("response", lambda r: asyncio.create_task(on(r)))

        await page.goto(V4 + slug, wait_until="networkidle", timeout=40000)
        await page.wait_for_timeout(3000)
        cols = await page.evaluate("() => (Array.isArray(window.metrics)&&window.metrics.length)?Object.keys(window.metrics[0]):[]")
        if not cols:
            await b.close(); raise SystemExit(f"{slug}: no window.metrics")
        # drive one valid combo to trigger a CheckPrice (learn the schema)
        selids = await page.evaluate(
            "() => [...document.querySelectorAll('select')].filter(s=>s.offsetParent && "
            "!/country|courier|track/i.test(s.id)).map(s=>s.id)")
        for sid in selids:
            try:
                await page.evaluate(
                    "(id)=>{const s=document.getElementById(id);"
                    "if(s&&s.options.length>1){s.selectedIndex=1;"
                    "s.dispatchEvent(new Event('change',{bubbles:true}));}}", sid)
                await page.wait_for_timeout(600)
            except Exception:
                pass
        await page.evaluate(
            "()=>{const qi=[...document.querySelectorAll('input')].find(i=>/qty|quantity/i.test(i.id+i.className));"
            "if(qi){qi.value='100';qi.dispatchEvent(new Event('input',{bubbles:true}));qi.dispatchEvent(new Event('change',{bubbles:true}));}}")
        for _ in range(20):
            await page.wait_for_timeout(400)
            if "req" in hold:
                break
        cookies = await page.context.cookies()
        cookie = "; ".join(f"{c['name']}={c['value']}" for c in cookies if "excard" in c.get("domain", "").lower())
        await b.close()
    if "req" not in hold:
        raise SystemExit(f"{slug}: never captured a CheckPrice request (page may not use the API)")
    spec = hold["req"]["spec"][0]
    return spec, hold["req"]["type"], metrics, cookie


def _fetch(type_str, spec, cookie, retries=3):
    body = json.dumps({"type": type_str, "spec": [spec]}).encode()
    hdrs = {"Authorization": "Basic " + _B64, "Api-Key": _API_KEY,
            "Content-Type": "application/json; charset=utf-8", "Cookie": cookie}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(CHECKPRICE_URL, data=body, headers=hdrs, method="POST")
            with urllib.request.urlopen(req, timeout=25, context=_CTX) as r:
                raw = r.read()
            if raw:
                p = float(str(json.loads(raw.decode()).get("Price", "0")).replace(",", ""))
                return p if p > 0 else None
        except Exception:
            if attempt < retries - 1:
                time.sleep(1.0 * (attempt + 1))
    return None


def enumerate_product(slug: str, max_workers: int = 24):
    spec_tmpl, type_str, metrics, cookie = asyncio.run(_capture(slug))
    cols = list(metrics[0].keys())
    # option axes = non-noise, multi-valued columns except quantity
    qty_col = next((c for c in cols if re.match(r"quantity|qty", c, re.I)), None)
    def distinct(c): return list(dict.fromkeys(r[c] for r in metrics if r.get(c) is not None))
    opt = [c for c in cols if not _NOISE.search(c) and c != qty_col and len(distinct(c)) > 1]
    axes = opt  # curve axes (non-qty)
    # map each metrics column -> spec key by normalized name
    spec_keys = {k: k for k in spec_tmpl}
    col2key = {}
    for c in cols:
        m = next((k for k in spec_keys if _norm(k) == _norm(c)), None)
        if m:
            col2key[c] = m
    print(f"{slug}: type={type_str!r} axes={axes} qty={qty_col} "
          f"mapped={ {c:col2key[c] for c in axes if c in col2key} }", file=sys.stderr)

    # valid combos = distinct tuples over axes (from metrics), with their orderable qtys
    combos = {}
    for r in metrics:
        key = tuple(r[c] for c in axes)
        q = str(r.get(qty_col, "")).replace(",", "")
        if q.isdigit():
            combos.setdefault(key, set()).add(q)

    tasks = []
    for key, qtys in combos.items():
        base = dict(spec_tmpl)
        for c, v in zip(axes, key):
            if c in col2key:
                base[col2key[c]] = v
        for q in sorted(qtys, key=int):
            s = dict(base)
            if qty_col in col2key:
                s[col2key[qty_col]] = q
            elif "Quantity" in s:
                s["Quantity"] = q
            tasks.append(("|".join(map(str, key)), q, s))

    print(f"{slug}: {len(combos)} combos, {len(tasks)} CheckPrice calls", file=sys.stderr)
    curves: dict[str, dict[str, float]] = {}
    done = fail = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_fetch, type_str, s, cookie): (k, q) for k, q, s in tasks}
        for fu in as_completed(futs):
            k, q = futs[fu]
            p = fu.result()
            if p:
                curves.setdefault(k, {})[q] = p
            else:
                fail += 1
            done += 1
            if done % 200 == 0:
                print(f"  {done}/{len(tasks)} ({fail} failed)", file=sys.stderr)

    # build capture shape
    def distinct2(c): return distinct(c)
    primary = axes[0] if axes else None
    deps = {}
    if primary:
        for key in combos:
            pv = key[0]
            sub = deps.setdefault(pv, {a: [] for a in axes[1:]})
            for a, v in zip(axes[1:], key[1:]):
                if v not in sub[a]:
                    sub[a].append(v)
    out = {
        "slug": slug, "source": "checkprice-api", "rows": sum(len(c) for c in curves.values()),
        "optionCols": axes, "primary": primary, "deps": deps,
        "imageField": None, "distinct": {c: distinct2(c) for c in axes}, "imageOptions": {},
        "priceMeta": {"priceCol": "Price", "qtyCol": "Quantity", "axisCols": axes,
                      "nCurves": len(curves)},
        "curves": curves,
    }
    p = OUT / "v4_options" / f"{slug}_options.json"
    p.write_text(json.dumps(out), encoding="utf-8")
    print(f"wrote {p}: {len(curves)} curves ({fail} failed)", file=sys.stderr)
    return curves


if __name__ == "__main__":
    enumerate_product(sys.argv[1])
