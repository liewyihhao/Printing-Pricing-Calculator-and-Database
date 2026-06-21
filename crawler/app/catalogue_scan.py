"""Auto catalogue check-up: scan Excard's full product catalogue (from sitemap.xml),
detect what's NEW / removed since the last scan, and compute our coverage (which products
we've built). Output drives an auto-updating coverage view in the UI.

  python -m app.catalogue_scan            # scan + diff + write coverage
  python -m app.catalogue_scan --print    # also print the report

Schedule it (e.g. daily) so the UI always reflects Excard's latest catalogue.
"""
from __future__ import annotations
import json, re, sys, datetime
from pathlib import Path
import requests

OUT = Path(__file__).resolve().parent.parent / "output"
SITEMAP = "https://www.excard.com.my/sitemap.xml"
SNAP = OUT / "excard_catalogue.json"
COVERAGE = OUT / "catalogue_coverage.json"
UA = "Mozilla/5.0 (compatible; PrintokaCatalogueBot/1.0)"

# our built product families → the Excard /product/<slug> they correspond to
BUILT = {
    "business-card": ["Business Card (id 1)"],
    "loose-sheet": ["Loose Sheet Litho (21)", "Loose Sheet Digital (50)"],
    "flyer": ["Loose Sheet (flyer = loose sheet)"],
    "brochure": ["Loose Sheet Litho (alias, id 101)"],
    "customprint": ["Loose Sheet Litho (alias, id 103)"],
    "notepad": ["Notepad Litho (104)"],
    "letterhead": ["Letterhead Litho (105)"],
    "envelope": ["Envelope Litho (106)"],
    "folder": ["Folder Litho — Presentation Folder (107)"],
    "l-shape-folder": ["L-Shape Plastic Folder Digital (108)"],
    "bookmark": ["Bookmark Digital (109)"],
    "voucher": ["Voucher Litho (110)"],
    "computer-form": ["Computer Form Litho NCR (111)"],
    "wire-o-notebook": ["Wire-O Notebook Litho (112)"],
    "pvc-card": ["PVC Card Digital (113)"],
    "kad-kahwin": ["Kad Kahwin Digital (114)"],
    "kad-terima-kasih": ["Kad Terima Kasih Digital (115)"],
    "booklet": ["Booklet Litho (19)", "Booklet Digital (37)"],
    "bill-book": ["Bill-Book Litho (24)"],
    "label-sticker-with-hot-stamping": ["Label Sticker Letterpress (61)"],
    "roll-form-sticker": ["Label Sticker Digital (60)"],
    "label-sticker": ["Label Sticker Digital (60)"],
    # packaging boxes are the packmage DIY tool (separate subdomain) — 67 boxes built
    "kotak-cenderahati": ["Packaging Boxes (67 styles)"],
}
# rough category grouping by slug keyword (sitemap has no category)
CATS = [("Stickers & Labels", ["sticker", "label", "cling", "car-sticker"]),
        ("Packaging & Boxes", ["bag", "box", "pouch", "paper-bag", "kotak", "sachet", "tray"]),
        ("Books & Stationery", ["book", "notepad", "letterhead", "envelope", "folder", "form",
                                 "notebook", "voucher", "bill", "loose-sheet", "flyer", "brochure"]),
        ("Calendars & Diary", ["calendar", "diary", "planner"]),
        ("Cards", ["card", "kad", "pvc"]),
        ("Large Format", ["banner", "bunting", "roll-up", "stand", "wobbler", "tent"]),
        ("Apparel & Gifts", ["shirt", "mug", "fan", "magnet", "badge", "pillow", "mask", "hanger",
                              "lanyard", "stamp", "menu"]),
        ("Money Packet", ["money-packet", "packet"]),
        ("Misc", ["arch-file", "papan-kopi", "customprint"])]


def _cat(slug):
    s = slug.lower()
    for name, kws in CATS:
        if any(k in s for k in kws):
            return name
    return "Other"


def scan():
    r = requests.get(SITEMAP, headers={"User-Agent": UA}, timeout=30); r.raise_for_status()
    slugs = sorted(set(re.findall(r"/product/([A-Za-z0-9\-]+)", r.text)))
    products = [{"slug": s, "name": s.replace("-", " ").title(),
                 "url": f"https://www.excard.com.my/product/{s}", "category": _cat(s)} for s in slugs]
    return {"scanned_at": datetime.datetime.now().isoformat(timespec="seconds"), "count": len(products),
            "products": products}


def coverage():
    prev = json.loads(SNAP.read_text()) if SNAP.exists() else {"products": []}
    prev_slugs = {p["slug"] for p in prev.get("products", [])}
    cur = scan()
    cur_slugs = {p["slug"] for p in cur["products"]}
    new = sorted(cur_slugs - prev_slugs)
    removed = sorted(prev_slugs - cur_slugs)
    for p in cur["products"]:
        p["built"] = p["slug"] in BUILT
        p["built_as"] = BUILT.get(p["slug"], [])
        p["is_new"] = p["slug"] in new and bool(prev_slugs)  # only flag new if we had a baseline
    cov = {"scanned_at": cur["scanned_at"], "total": cur["count"],
           "built": sum(1 for p in cur["products"] if p["built"]),
           "new_since_last": new if prev_slugs else [], "removed_since_last": removed,
           "products": sorted(cur["products"], key=lambda p: (p["category"], p["slug"]))}
    SNAP.write_text(json.dumps(cur, indent=1))          # update baseline snapshot
    COVERAGE.write_text(json.dumps(cov, indent=1))
    return cov


if __name__ == "__main__":
    cov = coverage()
    print(f"Excard catalogue: {cov['total']} products | built {cov['built']} | "
          f"new since last: {cov['new_since_last'] or 'none'} | removed: {cov['removed_since_last'] or 'none'}")
    if "--print" in sys.argv:
        for p in cov["products"]:
            mark = "[BUILT]" if p["built"] else ("[NEW]" if p["is_new"] else "[ -- ]")
            print(f"  {mark} [{p['category']}] {p['name']}" + (f"  -> {', '.join(p['built_as'])}" if p["built"] else ""))
