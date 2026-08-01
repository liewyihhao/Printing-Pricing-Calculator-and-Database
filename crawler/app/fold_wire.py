"""Build output/fold_images.json = {product_id: {"fold": {optionValue: image_key}}} for the
loose-sheet family, from the fold diagrams captured by app.fold_capture. The image_key is the
diagram's posix relative path (output/fold_diagrams/<slug>/<code>.png), which app.img_cache
embeds as a data: URI and build_standalone._attach_images wires onto the fold field.

  python -m app.fold_wire
"""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"

# supplier order-form slug -> our product ids whose "fold" field it feeds
_SLUG_TO_PIDS = {
    "lo-loose-sheet": [21, 50, 101, 102, 103],   # Loose Sheet Litho + Digital + Brochure/Flyer/Customprint
}


def build():
    out = {}
    for slug, pids in _SLUG_TO_PIDS.items():
        d = OUT / "fold_diagrams" / slug
        if not d.is_dir():
            continue
        codes = {f.stem: f.relative_to(OUT).as_posix() for f in sorted(d.glob("*.png"))}
        if not codes:
            continue
        for pid in pids:
            out[str(pid)] = {"fold": dict(codes)}
    (OUT / "fold_images.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    total = sum(len(v["fold"]) for v in out.values())
    print(f"fold_images.json: {len(out)} products, {total} fold-diagram mappings")


if __name__ == "__main__":
    build()
