"""Excard site intelligence — a broad, structured read of the supplier's public website so the
project understands their full catalogue, content and structure.

Two layers:
  1) SITE INVENTORY  — categorise every URL in the public sitemap (products, templates, help/
     education, ready-stock, static) so we know the shape of the whole site.
  2) PRODUCT INTEL   — for each /product/ page, extract a structured record: the spec sections
     present, materials, print colours, finishing, production limits (min/max size + thickness),
     standard sizes, and whether it ships downloadable templates / PDFs / an FAQ.

Facts only (dimensions, materials, structure) — no prose, images or PDFs are reproduced. Plain
HTTP, paced to honour robots.txt (Crawl-delay: 10 → we use a courteous delay).

  python -m app.excard_intel [--fast] [slug ...]     # writes output/excard_intelligence.json
"""
from __future__ import annotations
import json, re, sys, time
from pathlib import Path

from app.spec_fact_crawl import _get, _text, _facts_from, BASE

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
SITEMAP = "https://www.excard.com.my/sitemap.xml"
DELAY = 4.0   # seconds between page fetches (courteous; robots asks 10)

_SECTION_KEYS = ["Product Intro", "Product Spec", "Artwork Spec", "Artwork Specification",
                 "Template", "Price List", "Delivery", "FAQ", "Ready Stock"]
_INS_TTL = re.compile(r'class="[^"]*ins-ttl[^"]*"[^>]*>\s*([^<]{2,60}?)\s*<', re.I)
_HEADS = re.compile(r"<h[3-5][^>]*>\s*([^<]{3,55}?)\s*</h[3-5]>", re.I)
_HEAD_SKIP = re.compile(r"login|sign|cart|menu|footer|copyright|©|newsletter|follow us|contact us|"
                        r"become|member|password|search|track order", re.I)


def _sections_in(html_str):
    found = list(dict.fromkeys(t.strip() for t in _INS_TTL.findall(html_str) if t.strip()))
    if len(found) < 3:
        for t in _HEADS.findall(html_str):
            t = t.strip()
            if t and not _HEAD_SKIP.search(t) and t not in found:
                found.append(t)
    return found[:24]
_LAM = re.compile(r"(Gloss Lamination|Matte Lamination|Soft Touch Lamination|UV Varnish|"
                  r"Gloss Water[- ]?Based Varnish|Spot UV|Matte Laminate|Gloss Laminate)", re.I)
_COLOUR = re.compile(r"\b([124]C)\b|\bCMYK\b", re.I)


def categorize_sitemap():
    xml = _get(SITEMAP)
    if xml.startswith("ERR"):
        raise SystemExit(f"sitemap fetch failed: {xml}")
    urls = re.findall(r"<loc>([^<]+)</loc>", xml)
    buckets = {"product": [], "product-template": [], "help": [], "ready": [], "spec": [], "other": []}
    for u in urls:
        path = u.split("excard.com.my", 1)[-1]
        if "/product/" in path:
            buckets["product"].append(u)
        elif "/product-template/" in path:
            buckets["product-template"].append(u)
        elif re.search(r"help|artwork|guide|faq|tutorial|how-to", path, re.I):
            buckets["help"].append(u)
        elif re.search(r"ready|stock", path, re.I):
            buckets["ready"].append(u)
        elif re.search(r"spec", path, re.I):
            buckets["spec"].append(u)
        else:
            buckets["other"].append(u)
    return urls, buckets


def product_intel(slug: str):
    """Structured intelligence for one product from its spec page."""
    html_str = ""
    for url in (f"{BASE}product/{slug}?view=prd_spec", f"{BASE}{slug}?view=prd_spec"):
        html_str = _get(url)
        if len(html_str) > 40000:
            break
    if len(html_str) < 40000:
        return {"slug": slug, "fetched": False}
    txt = _text(html_str)
    title = ""
    m = re.search(r"<title>([^<]+)</title>", html_str, re.I)
    if m:
        title = re.split(r"[|:]", m.group(1))[0].strip()
    sections = [k for k in _SECTION_KEYS if re.search(re.escape(k), html_str, re.I)]
    ins = _sections_in(html_str)
    facts = _facts_from(txt)
    lam = sorted(set(m.title() for m in _LAM.findall(html_str)))
    colours = sorted({(c or "CMYK").upper() for c in (_COLOUR.findall(txt)[:20] or [])})
    rec = {
        "slug": slug, "fetched": True, "title": title,
        "tabs": sections,
        "spec_sections": ins[:20],
        "materials_hint": ins.count("Paper Material") > 0,
        "print_colours": colours,
        "finishing": lam,
        "min_max": facts["min_max"], "thickness_micron": facts["thickness_micron"],
        "standard_sizes": facts["sizes"][:20],
        "has_template": bool(re.search(r"/product-template/", html_str, re.I)),
        "has_pdf": bool(re.search(r'href="[^"]+\.pdf', html_str, re.I)),
        "has_faq": bool(re.search(r'id="faq"|>\s*FAQ', html_str, re.I)),
        "has_artwork_spec": bool(re.search(r"artwork[_ ]spec", html_str, re.I)),
        "has_price_list": bool(re.search(r"Price List", html_str, re.I)),
    }
    return rec


def run(targets=None, fast=False):
    urls, buckets = categorize_sitemap()
    prod_urls = buckets["product"]
    slugs = [u.rsplit("/", 1)[-1] for u in prod_urls]
    if targets:
        slugs = [s for s in slugs if s in set(targets)]
    delay = 0.5 if fast else DELAY
    intel = []
    for i, s in enumerate(slugs):
        rec = product_intel(s)
        intel.append(rec)
        got = rec.get("fetched")
        print(f"  [{i+1}/{len(slugs)}] {s[:34]:34} "
              f"{'sections=' + str(len(rec.get('spec_sections', []))) if got else 'FETCH FAILED'}"
              f"{' pdf' if rec.get('has_pdf') else ''}{' tmpl' if rec.get('has_template') else ''}"
              f"{' faq' if rec.get('has_faq') else ''}", file=sys.stderr)
        if i < len(slugs) - 1:
            time.sleep(delay)
    # aggregate site-level intelligence
    mats = {}
    for r in intel:
        for s in r.get("spec_sections", []):
            mats[s] = mats.get(s, 0) + 1
    summary = {
        "site": {"sitemap_urls": len(urls),
                 "by_type": {k: len(v) for k, v in buckets.items()},
                 "help_pages": buckets["help"][:20]},
        "products": {"count": len(intel),
                     "fetched": sum(1 for r in intel if r.get("fetched")),
                     "with_pdf": sum(1 for r in intel if r.get("has_pdf")),
                     "with_template": sum(1 for r in intel if r.get("has_template")),
                     "with_faq": sum(1 for r in intel if r.get("has_faq")),
                     "with_min_max": sum(1 for r in intel if r.get("min_max"))},
        "common_spec_sections": sorted(mats.items(), key=lambda kv: -kv[1])[:20],
    }
    out = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "summary": summary,
           "sitemap": {k: v for k, v in buckets.items()}, "products": intel}
    (OUT / "excard_intelligence.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n=== SITE INTELLIGENCE SUMMARY ===", file=sys.stderr)
    print(json.dumps(summary, ensure_ascii=False, indent=1), file=sys.stderr)
    print(f"\nwrote output/excard_intelligence.json ({len(intel)} products)", file=sys.stderr)
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--fast"]
    run(targets=args or None, fast="--fast" in sys.argv)
