"""Auto-generate per-product rich spec content for EVERY product, from our own catalogue data
(output/calculator_data.json) — no scraping of the supplier's copyrighted spec/artwork PDFs.

For each product it writes output/spec_content/<slug>.json with three content areas the product
page renders as tabs:
  - "sections"  → Product Spec  (an "at a glance" summary from the product's own options)
  - "artwork"   → Artwork Spec   (original, archetype-tailored print-artwork guidance)
  - "templates" → Template sizes (standard sizes + bleed/safe-area setup)

Existing hand-authored files are respected: only MISSING content areas are filled, so richer
manual content (e.g. label-sticker) is never clobbered.

  python -m app.build_spec_content
"""
from __future__ import annotations
import json
from pathlib import Path

from app.build_specs_page import clean_name, slugify
from app.product_art import archetype_of

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
SC = OUT / "spec_content"


def _find(prod, keys, labelkw):
    for f in prod.get("fields", []):
        k = (f.get("key") or "").lower()
        lab = (f.get("label") or "").lower()
        if k in keys or any(w in lab for w in labelkw):
            return f
    return None


def _opts(prod, keys, labelkw):
    f = _find(prod, keys, labelkw)
    if not f:
        return []
    return [str(o) for o in (f.get("options") or []) if not str(o).lower().startswith(("other", "others", "custom"))]


# ---- Product Spec: an "at a glance" summary (the full detail is in the options table below) ----
def _sections(prod):
    papers = _opts(prod, {"paper", "papermaterials", "material", "paper_tint"}, {"paper", "material"})
    colours = _opts(prod, {"colour", "printcolour", "print_colour"}, {"print colour", "colour"})
    lams = _opts(prod, {"lamination", "finishing", "surface", "cover_lamination", "lam"}, {"lamination", "finishing", "surface"})
    sizes = _opts(prod, {"size"}, {"size"})
    rows = []
    if papers:
        rows.append({"k": "Materials / paper", "v": ", ".join(papers[:6]) + ("…" if len(papers) > 6 else "")})
    if colours:
        rows.append({"k": "Print colour", "v": ", ".join(colours[:6])})
    if lams:
        rows.append({"k": "Finishing", "v": ", ".join(lams[:6]) + ("…" if len(lams) > 6 else "")})
    if sizes:
        rows.append({"k": "Standard sizes", "v": f"{len(sizes)} sizes available — see Template Sizes"})
    if not rows:
        return []
    return [{"title": "At a glance", "type": "keyvalue", "rows": rows}]


# ---- Artwork Spec: original, archetype-tailored guidance ----
_DPI = {"banner": "150 dpi at final size (or 300 dpi at 1:2). Vector art scales without loss.",
        "apparel": "300 dpi at print size, or vector.",
        "default": "300 dpi at 100% size. Vector art (AI/EPS/PDF) is ideal and stays sharp."}
_BLEED = {"banner": "Add bleed as advised for the finishing (hem / pole pocket / eyelets).",
          "default": "3 mm on every side — extend background artwork into the bleed."}

_EXTRA = {
    "sticker": ("Die-line & cutting", [
        "Add your cut path as a separate spot colour named “CutContour” (set to overprint).",
        "Keep the die-line a single, smooth line — simpler shapes cut more cleanly.",
        "Leave 2–3 mm between the artwork edge and the cut on kiss-cut labels.",
        "Round tight internal corners to ≥ 3 mm radius."]),
    "box": ("Die-line & folding", [
        "Place your artwork on the supplied keyline/die-line, on its own layer.",
        "Keep the die-line as a non-printing spot colour.",
        "Extend background art 3 mm over every fold and glue flap.",
        "Avoid critical text or logos across fold / crease lines."]),
    "banner": ("Large-format setup", [
        "Design at final size, or a clean fraction (e.g. 1:10) — note the scale.",
        "Keep key content inside the safe area, away from eyelets and pole pockets.",
        "Convert hairlines to ≥ 1 pt so they hold at large size."]),
    "apparel": ("Print-area artwork", [
        "Supply as vector or a transparent-background PNG.",
        "Design within the printable area for the garment size.",
        "On dark fabric, note if a white underbase is needed.",
        "Avoid very fine lines and small reversed text."]),
    "book": ("Pagination & binding", [
        "Supply single pages in reading order (not spreads), including the cover.",
        "Saddle-stitch page counts are a multiple of 4.",
        "Keep text ≥ 8 mm from the spine on perfect-bound books.",
        "Number the pages to avoid ordering mistakes."]),
    "card": ("Card setup", [
        "Supply front and back as separate pages.",
        "For rounded corners, keep content ≥ 4 mm inside the trim.",
        "For spot UV or foil, supply a separate 100% black mask layer."]),
    "mug": ("Wrap template", [
        "Design on the supplied wrap template.",
        "Keep key content in the front visible zone, away from the handle.",
        "Leave a small gap at the wrap seam."]),
    "calendar": ("Layout & binding", [
        "Supply each panel/month as its own page in order.",
        "Allow for the binding/wire punch area at the top.",
        "Keep dates and text clear of the trim and punch holes."]),
}


def _artwork(prod):
    arch = archetype_of(prod["name"])
    dpi = _DPI.get(arch, _DPI["default"])
    bleed = _BLEED.get(arch, _BLEED["default"])
    secs = [{
        "title": "File format & setup", "type": "keyvalue", "rows": [
            {"k": "File format", "v": "Print-ready PDF preferred. AI, EPS, or high-resolution PNG/TIFF also accepted."},
            {"k": "Resolution", "v": dpi},
            {"k": "Colour mode", "v": "CMYK for accurate print colour (RGB is converted and can shift)."},
            {"k": "Bleed", "v": bleed},
            {"k": "Safe margin", "v": "Keep text and logos ≥ 3–5 mm inside the trim so nothing is cut off."},
            {"k": "Fonts", "v": "Outline or embed all fonts before exporting."},
        ]}]
    if arch in _EXTRA:
        title, items = _EXTRA[arch]
        secs.append({"title": title, "type": "list", "items": items})
    secs.append({"title": "Before you send", "type": "list", "items": [
        "Export at 1:1 scale (100%).",
        "Double-check spelling, contact details and the final size.",
        "Flatten transparencies, or supply layered files if we've asked for them.",
    ], "note": "Not sure? Send us your file and we'll check it before printing."})
    return secs


# ---- Template sizes ----
def _templates(prod):
    sizes = _opts(prod, {"size"}, {"size"})
    secs = []
    if sizes:
        secs.append({"title": "Standard sizes", "type": "list",
                     "items": [f"{s}  ·  add 3 mm bleed on each side" for s in sizes[:16]],
                     "note": "The size you order is the finished (trim) size."})
    secs.append({"title": "Setting up your file", "type": "keyvalue", "rows": [
        {"k": "Trim size", "v": "The finished size you order."},
        {"k": "Bleed", "v": "3 mm on every side (large formats per finishing)."},
        {"k": "Safe area", "v": "Keep important content ≥ 3–5 mm inside the trim."},
    ], "note": "Download the matching print-ready template below and design inside it."})
    return secs


def build():
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))
    SC.mkdir(parents=True, exist_ok=True)
    n = filled = 0
    for prod in data["products"]:
        slug = slugify(prod["name"])
        f = SC / f"{slug}.json"
        cur = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
        auto = {"sections": _sections(prod), "artwork": _artwork(prod), "templates": _templates(prod)}
        changed = False
        for key in ("sections", "artwork", "templates"):
            if key not in cur:             # respect existing content; only fill genuinely-absent areas
                cur[key] = auto[key]
                changed = True
        if changed or not f.is_file():
            f.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
            filled += 1
        n += 1
    print(f"spec_content: {n} products processed, {filled} written/updated -> output/spec_content/")


if __name__ == "__main__":
    build()
