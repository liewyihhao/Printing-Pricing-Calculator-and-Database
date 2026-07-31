"""Crawl every product's order page and capture the image the supplier shows for each option
value (model / shape / material pictures), so our UI can show the same ones — completely, not
product-by-product on reminder.

Supplier option images live on predictable CDNs (…/images/member/order_*/<value>.jpg,
…/diagram/…, …/spec-model/…). They're in the order-page DOM even when the control is a plain
<select>, so we collect every such <img>, then map each to a (field, option) by matching the
image's file name to an option value.

Writes output/option_images_full.json = {product_id: {field_key: {option: url}}}.
app.img_cache then downloads them; build_standalone wires them onto the fields.

  python -m app.option_image_crawl [slug-or-id ...]     # default: all products
"""
from __future__ import annotations
import asyncio, json, re, sys, urllib.parse
from pathlib import Path

from playwright.async_api import async_playwright
from app import browser as B
from app.readymade_enum import login_v4
from app.build_specs_page import clean_name
from app.product_quantity import _base_slug, _ALIAS

OUT = Path(__file__).resolve().parent.parent / "output"
V4 = "https://v4.excard.com.my/ordering/"
# CDN paths that carry per-option pictures (not layout/banner/icon chrome)
_OPT_IMG = re.compile(r"/images/member/order|/diagram/|/spec-model/", re.I)
_CHROME = re.compile(r"logo|banner|icon|getquote|pplan|master/|/v3/|placeholder|loading", re.I)
# generic file names that are NOT per-option pictures (a shared guide, or the product hero)
_GENERIC = re.compile(r"deboss-?area|hot-?stamp|artwork|guide|sample|bleed|template|"
                      r"_order\b|-order\b|extralarge", re.I)


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _stem(url):
    path = urllib.parse.urlparse(url).path
    name = urllib.parse.unquote(path.rsplit("/", 1)[-1])
    return _norm(re.sub(r"\.(jpg|jpeg|png|gif|webp)$", "", name, flags=re.I))


async def _collect(page, slug):
    """Return [(img_url, stem)] of option-image candidates on a product's order page."""
    try:
        await page.goto(V4 + slug, wait_until="domcontentloaded", timeout=40000)
    except Exception:
        return []
    await page.wait_for_timeout(3200)
    urls = await page.evaluate(
        "() => [...document.querySelectorAll('img')].map(i => i.src || i.getAttribute('data-src') || '')")
    out, seen = [], set()
    for u in urls:
        if u and _OPT_IMG.search(u) and not _CHROME.search(u) and not _GENERIC.search(u) and u not in seen:
            seen.add(u)
            out.append((u, _stem(u)))
    return out


# Supplier image filenames sometimes drift from the option label they picture (their file naming
# vs our parity-correct select value). Expand variants across the known drifts so the real
# per-option picture still attaches. Keep the option label itself untouched (parity).
#   dtf<->dtp : "UV DTF Stickering" option is filed as "UV-DTP-Stickering.png" (Leather Wire-O #163)
_FILENAME_SYNONYMS = [("dtf", "dtp")]


def _variants(option):
    """Normalized tokens an option value might appear as in an image file name:
    the value itself, plus "model 1" -> "m1" and any embedded code like "BBD32P"/"3SS-M2"."""
    on = _norm(option)
    vs = {on}
    m = re.search(r"model\s*([0-9]+)", option, re.I)
    if m:
        vs.add("m" + m.group(1))
    for tok in re.findall(r"[a-z]{1,4}[- ]?[0-9]{1,3}[a-z]*", option, re.I):
        vs.add(_norm(tok))
    for a, b in _FILENAME_SYNONYMS:            # tolerate supplier filename spelling drift
        for v in list(vs):
            if a in v:
                vs.add(v.replace(a, b))
            if b in v:
                vs.add(v.replace(b, a))
    return {v for v in vs if len(v) >= 2}


def _map_to_fields(product, imgs):
    """{field_key: {option: url}} — an image maps to an option whose value (or a code/variant of
    it) matches its file stem."""
    result = {}
    for f in product.get("fields", []):
        for o in (f.get("options") or []):
            variants = _variants(o)
            if not variants:
                continue
            for url, stem in imgs:
                if stem and any(v == stem or v in stem or stem in v for v in variants):
                    result.setdefault(f["key"], {})[o] = url
                    break
    return result


async def run(targets=None):
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))["products"]
    if targets:
        tl = {str(t).lower() for t in targets}
        data = [p for p in data if str(p["id"]) in tl or _base_slug(p["name"]) in tl]
    full = {}
    if (OUT / "option_images_full.json").is_file():
        full = json.loads((OUT / "option_images_full.json").read_text(encoding="utf-8"))
    scan = {}
    async with async_playwright() as pw:
        b = await B.launch(pw)
        page = await b.new_page()
        await login_v4(page)
        for i, p in enumerate(data):
            if p.get("engine") == "contact":
                continue
            own = _base_slug(p["name"])                    # a product's OWN page has its own model
            imgs = await _collect(page, own)               # images; only fall back to the shared-
            if not imgs:                                   # form alias if the own page has none.
                alias = _ALIAS.get(own, own)
                if alias != own:
                    imgs = await _collect(page, alias)
            mapped = _map_to_fields(p, imgs)
            if mapped:
                full[str(p["id"])] = mapped
            n = sum(len(v) for v in mapped.values())
            scan[str(p["id"])] = {"imgs_found": len(imgs), "mapped": n}
            print(f"  [{i+1}/{len(data)}] {clean_name(p['name'])[:32]:32} "
                  f"{len(imgs)} imgs -> {n} option pics {list(mapped)}", file=sys.stderr)
        await b.close()
    (OUT / "option_images_full.json").write_text(json.dumps(full, ensure_ascii=False, indent=1), encoding="utf-8")
    if not targets:            # a full run gives a complete scan record for the image audit
        (OUT / "option_images_scan.json").write_text(json.dumps(scan, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(v) for prod in full.values() for v in prod.values())
    print(f"\noption_images_full: {len(full)} products, {total} option images "
          f"-> output/option_images_full.json", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(run(sys.argv[1:] or None))
