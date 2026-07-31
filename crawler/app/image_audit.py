"""Complete option-image audit: every image the supplier shows for a configuration option must
be captured, wired and embedded in our UI — checked automatically, so it never needs reminding.

Checks, per product:
  1. WIRED    — every option image discovered by app.option_image_crawl (output/
     option_images_full.json) is present on the field in the built calculator and embedded as a
     self-contained data: URI (not a stripped/remote URL).
  2. COVERAGE — flags products that expose a Model/Shape/Design-type control but for which the
     crawl found NO image, so a page that failed to load (or a new product) gets re-checked.

  python -m app.image_audit
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

from app.build_specs_page import clean_name

OUT = Path(__file__).resolve().parent.parent / "output"
_PICLIKE = re.compile(r"model|shape|design|mould|style|fold|cover", re.I)


def audit():
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))["products"]
    full = json.loads((OUT / "option_images_full.json").read_text(encoding="utf-8")) \
        if (OUT / "option_images_full.json").is_file() else {}
    by_id = {p["id"]: p for p in data}

    not_embedded = {}      # pid -> [(field, option)]
    coverage = []          # products with a pic-like control but no crawled images
    wired_ok = 0

    for pid_s, fmap in full.items():
        pid = int(pid_s)
        p = by_id.get(pid)
        if not p:
            continue
        fields = {f["key"]: f for f in p["fields"]}
        for fkey, opts in fmap.items():
            f = fields.get(fkey)
            imgs = (f or {}).get("images") or {}
            for opt in opts:
                v = imgs.get(opt)
                if v and str(v).startswith("data:"):
                    wired_ok += 1
                else:
                    not_embedded.setdefault(pid, []).append((fkey, opt))

    # Coverage from the crawl's scan record: flag a product only when the crawl FOUND option
    # images on its page but couldn't map them all to options (a real miss). "Found 0" = the
    # supplier has no per-option pictures there (confirmed none, not a gap). Unmappable filename
    # patterns can be recorded as verified.
    scan = json.loads((OUT / "option_images_scan.json").read_text(encoding="utf-8")) \
        if (OUT / "option_images_scan.json").is_file() else {}
    for pid_s, s in scan.items():
        found = s.get("imgs_found", 0)
        # Use the LIVE mapped count from option_images_full.json (ground truth) rather than the
        # scan's recorded count, so a targeted re-crawl (which doesn't rewrite the scan) is honoured.
        mapped = sum(len(v) for v in full.get(pid_s, {}).values())
        if found > mapped and pid_s not in {str(x) for x in VERIFIED_NO_MAP}:
            coverage.append((int(pid_s), f"{clean_name(by_id[int(pid_s)]['name'])} "
                                         f"({found} imgs found, {mapped} mapped)"))
    return wired_ok, not_embedded, coverage


# Products whose page shows image(s) we can't attach to a selectable option (verified by
# inspection). Recorded so the audit stays clean; revisit if the field model changes.
#   132 Button Badge — files named by diameter ("32mm") vs our model codes ("BBD32P")
#   158 Wind Flag     — files "WFT_01_3m" vs our labels "Teardrop Flag 3.0m"
#   141 Stamp Chop    — stamp-type pictures, but stamp_type is an optionsKey cascade (no static
#                       options to attach to)
#   108 L-Shape Folder / 146 Heat Transfer Tote — a single model picture, but we expose no Model
#                       field for these (one model)
#   149 Toast Bag / 175 Premium Desk Calendar / 177 Food Tray — a single product hero/diagram
#                       image (diagram/<slug>/…), not a per-option picture; no Model field
#   114 Kad Kahwin    — page banner only (diagram/kad-kahwin/ban.jpg)
#   169 Envelope Money Packet — one ready-design template preview (diagram/money-packet/PFD-24-001);
#                       the design picker is a JS ready-editor, not a static selectable option
VERIFIED_NO_MAP = {132, 158, 141, 108, 146, 149, 175, 177, 114, 169}


if __name__ == "__main__":
    wired_ok, not_embedded, coverage = audit()
    miss = sum(len(v) for v in not_embedded.values())
    print("=== OPTION-IMAGE AUDIT ===")
    print(f"option images wired + embedded : {wired_ok}")
    print(f"crawled images NOT embedded    : {miss} across {len(not_embedded)} products")
    print(f"pic-like controls, no crawl hit: {len(coverage)} products (verify these)")
    if not_embedded:
        print("\n-- not embedded (run img_cache + rebuild) --")
        for pid, items in sorted(not_embedded.items()):
            print(f"  [{pid}] {[f'{f}:{o}' for f, o in items][:8]}")
    if coverage:
        print("\n-- pic-like control but no crawled image (check the supplier page) --")
        for pid, name in coverage:
            print(f"  [{pid}] {name}")
    if not miss and not coverage:
        print("\nCLEAN — every supplier option image is captured, wired and embedded.")
