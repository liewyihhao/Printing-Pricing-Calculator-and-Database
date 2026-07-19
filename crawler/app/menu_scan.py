"""Verify product coverage against Excard's authoritative product list — the public
sitemap.xml (all /product/ URLs). Plain HTTP, no login, no fragile mega-menu driving.

  python -m app.menu_scan
"""
from __future__ import annotations
import json, re, ssl, sys, urllib.request
from pathlib import Path

from app.build_specs_page import clean_name

OUT = Path(__file__).resolve().parent.parent / "output"
SITEMAP = "https://www.excard.com.my/sitemap.xml"
_CTX = ssl._create_unverified_context()


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _get(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=25, context=_CTX) as r:
            return r.read().decode("utf-8", "ignore")
    except Exception as e:  # noqa: BLE001
        return f"ERR {e}"


def excard_products():
    xml = _get(SITEMAP)
    if xml.startswith("ERR"):
        raise SystemExit(f"sitemap fetch failed: {xml}")
    slugs = [l.rsplit("/", 1)[-1] for l in re.findall(r"<loc>([^<]+)</loc>", xml) if "/product/" in l]
    return sorted(set(slugs))


def diff(slugs):
    ours = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))["products"]
    obases = {_norm(re.split(r"[—(]", p["name"])[0]) for p in ours}
    ofull = {_norm(clean_name(p["name"])) for p in ours}
    missing = []
    for s in slugs:
        nb = _norm(s.replace("-", ""))
        # match if a Printoka product's base/full name contains or equals the slug tokens
        hit = any(nb and (nb in ob or ob in nb) for ob in obases) or any(nb in f or f in nb for f in ofull)
        if not hit:
            missing.append(s)
    return missing


if __name__ == "__main__":
    slugs = excard_products()
    (OUT / "excard_menu.json").write_text(json.dumps(slugs, indent=1))
    print(f"Excard sitemap: {len(slugs)} product URLs", file=sys.stderr)
    miss = diff(slugs)
    print("\n=== Excard products with NO obvious match in our calculator ===")
    for m in sorted(miss):
        print("  ", m)
    print(f"\n({len(miss)} to review of {len(slugs)} sitemap products)")
