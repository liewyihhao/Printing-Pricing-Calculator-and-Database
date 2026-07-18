"""Crawl the supplier's public product-spec pages and extract the FACTUAL production figures a
graphic designer checks before sending to print — min/max production size, material thickness,
and the standard size list. Facts only (dimensions/limits are not copyrightable); no prose,
images or PDFs are reproduced.

Writes output/spec_facts/<our-slug>.json. Fast: plain HTTP (no login/browser), threaded.

  python -m app.spec_fact_crawl [slug-or-id ...]      # default: all products
"""
from __future__ import annotations
import json, re, ssl, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.build_specs_page import clean_name, slugify

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
FACTS = OUT / "spec_facts"
_CTX = ssl._create_unverified_context()
BASE = "https://www.excard.com.my/"


def _base_slug(name):
    base = re.split(r"[—(]", clean_name(name))[0]
    return re.sub(r"[^a-z0-9]+", "-", base.strip().lower()).strip("-")


def _excard_slugs():
    """our product id -> [candidate excard slugs], best-guess first. Excard's spec-page slug is
    usually the base product name hyphenated (business-card, mug, bill-book); we also try the
    catalogue slug and the v4 ordering slug."""
    from app.build_standalone import _PRICELIST_FROM_OPTIONS as PLO
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))
    cand = {p["id"]: [_base_slug(p["name"])] for p in data["products"]}
    for pid, (slug, _tag) in PLO.items():
        cand.setdefault(pid, []).append(slug.lower())
    try:
        cat = json.loads((OUT / "excard_catalogue.json").read_text(encoding="utf-8"))["products"]
        for c in cat:
            slug = c.get("slug") or (c.get("url", "").rstrip("/").split("/")[-1])
            for b in (c.get("built_as") or []):
                m = re.search(r"\((\d+)\)", b)
                if m and slug:
                    cand.setdefault(int(m.group(1)), []).append(slug)
    except Exception:
        pass
    # dedupe, keep order
    return {pid: list(dict.fromkeys(s for s in v if s)) for pid, v in cand.items()}


def _get(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=25, context=_CTX) as r:
            return r.read().decode("utf-8", "ignore")
    except Exception:
        return ""


def _text(html_str):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html_str, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t)


_SIZE = re.compile(r"(\d{1,4}(?:\.\d+)?\s*mm\s*[xX×]\s*\d{1,4}(?:\.\d+)?\s*mm)")
_DIAM = re.compile(r"Diameter\s*(\d{1,4}\s*mm)", re.I)


def _facts_from(txt):
    def norm(s): return re.sub(r"\s+", "", s).replace("X", "x").replace("×", "x")
    sizes = list(dict.fromkeys(norm(s) for s in _SIZE.findall(txt)))
    # min/max production size: look for "Min ... <size> ... Max ... <size>"
    minmax = []
    for m in re.finditer(r"Min\s*:?\s*(?:Diameter\s*)?([0-9.]+\s*mm(?:\s*[xX×]\s*[0-9.]+\s*mm)?)"
                         r".{0,80}?Max\s*:?\s*(?:Diameter\s*)?([0-9.]+\s*mm(?:\s*[xX×]\s*[0-9.]+\s*mm)?)",
                         txt, re.I | re.S):
        pair = (norm(m.group(1)), norm(m.group(2)))
        if pair not in minmax:
            minmax.append(pair)
    thickness = list(dict.fromkeys(re.findall(r"(\d{2,3})\s*Micron", txt, re.I)))
    return {"sizes": sizes[:24], "min_max": minmax[:6], "thickness_micron": thickness[:6]}


def crawl_one(pid, name, slugs):
    """Try each candidate slug in both URL forms (the two templates expose different facts for
    different products); union everything found."""
    got = {"excard_slug": None, "sizes": [], "min_max": [], "thickness_micron": [], "sources": []}
    for s in slugs:
        for url in (f"{BASE}product/{s}?view=prd_spec", f"{BASE}{s}?view=prd_spec"):
            html_str = _get(url)
            if len(html_str) > 40000 and re.search(r"prd_spec|Product Spec|Paper Material|Artwork Spec", html_str, re.I):
                f = _facts_from(_text(html_str))
                got["excard_slug"] = got["excard_slug"] or s
                got["sources"].append(url)
                for k in ("sizes", "min_max", "thickness_micron"):
                    for v in f[k]:
                        if v not in got[k]:
                            got[k].append(v)
        if got["min_max"] or got["thickness_micron"]:   # enough — stop at first slug that yields real facts
            break
    got["sizes"] = got["sizes"][:24]
    return got


def run(targets=None, max_workers=6):
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))
    cand = _excard_slugs()
    prods = data["products"]
    if targets:
        tl = set(str(t).lower() for t in targets)
        prods = [p for p in prods if str(p["id"]) in tl or slugify(p["name"]) in tl]
    FACTS.mkdir(parents=True, exist_ok=True)
    tasks = [(p["id"], p["name"], cand.get(p["id"], [slugify(clean_name(p["name"]))])) for p in prods]
    ok = hit = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(crawl_one, pid, name, slugs): (pid, name) for pid, name, slugs in tasks}
        for fu in as_completed(futs):
            pid, name = futs[fu]
            res = fu.result()
            (FACTS / f"{slugify(clean_name(name))}.json").write_text(
                json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
            ok += 1
            got = res.get("excard_slug") and (res["sizes"] or res["min_max"] or res["thickness_micron"])
            hit += 1 if got else 0
            print(f"  [{ok}/{len(tasks)}] {clean_name(name)[:34]:34} "
                  f"{'✓ ' + (res.get('excard_slug') or '') if got else '· no facts'}", file=sys.stderr)
    print(f"spec_facts: {ok} products, {hit} with facts -> output/spec_facts/", file=sys.stderr)


if __name__ == "__main__":
    run(sys.argv[1:] or None)
