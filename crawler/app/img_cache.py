"""Download supplier option-diagram images and cache them as self-contained base64 data URIs
in output/img_data_uris.json, so the standalone calculator embeds every option image and needs
no network at runtime.

Sources of URLs (merged):
  1. every v4_options/<slug>_options.json capture's `imageOptions`
  2. output/option_images.json (envelope / folder families)
  3. output/option_images_full.json (per-product per-field option images from option_image_crawl)

Images are thumbnailed (default max 240px, JPEG/PNG) to keep the bundle small.

  python -m app.img_cache            # refresh the cache from all known URL sources
"""
from __future__ import annotations
import base64, io, json, ssl, sys, urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
CACHE = OUT / "img_data_uris.json"
V4 = OUT / "v4_options"
_CTX = ssl._create_unverified_context()
MAX_PX = 240
MAX_PX_DIAGRAM = 560          # educational spec-diagram images: larger so labels stay legible


def _all_urls():
    urls = set()
    for f in V4.glob("*_options.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for u in (d.get("imageOptions") or {}).values():
            if u:
                urls.add(u)
    for name in ("option_images.json", "option_images_full.json"):
        p = OUT / name
        if not p.is_file():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        # option_images.json: {family:{field:{opt:url}}}; full: {pid:{field:{opt:url}}}
        for fam in d.values():
            for fld in fam.values():
                for u in fld.values():
                    if u:
                        urls.add(u)
    return urls


def _spec_diagram_urls():
    """Educational diagram image URLs referenced by spec_content "images" sections (booklet
    binding methods, etc.). Cached larger than option thumbnails so their labels stay readable."""
    urls = set()
    for f in (OUT / "spec_content").glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for key in ("sections", "artwork", "templates"):
            for sec in d.get(key, []) or []:
                if sec.get("type") == "images":
                    for it in sec.get("images", []):
                        if it.get("url"):
                            urls.add(it["url"])
    return urls


def _download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25, context=_CTX) as r:
        return r.read()


def _to_datauri(raw, max_px=MAX_PX):
    from PIL import Image
    im = Image.open(io.BytesIO(raw))
    im.load()
    has_alpha = im.mode in ("RGBA", "LA", "P")
    im = im.convert("RGBA") if has_alpha else im.convert("RGB")
    w, h = im.size
    if max(w, h) > max_px:
        s = max_px / max(w, h)
        im = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
    buf = io.BytesIO()
    if has_alpha:
        im.save(buf, "PNG", optimize=True)
        mime = "image/png"
    else:
        im.save(buf, "JPEG", quality=82, optimize=True)
        mime = "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(buf.getvalue()).decode()}"


def refresh(force=False):
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.is_file() else {}
    # (url-set, thumbnail size) groups — option images small, educational diagrams larger.
    groups = [(_all_urls(), MAX_PX), (_spec_diagram_urls(), MAX_PX_DIAGRAM)]
    n_urls = len(set().union(*[g[0] for g in groups]))
    todo = [(u, mp) for urls, mp in groups for u in urls if force or u not in cache]
    print(f"img_cache: {n_urls} image URLs, {len(todo)} to fetch "
          f"({len(cache)} already cached)", file=sys.stderr)
    ok = fail = 0
    for i, (u, mp) in enumerate(sorted(todo), 1):
        try:
            cache[u] = _to_datauri(_download(u), mp)
            ok += 1
        except Exception as e:  # noqa: BLE001
            fail += 1
            print(f"  FAIL {u} :: {str(e)[:60]}", file=sys.stderr)
        if i % 20 == 0:
            print(f"  {i}/{len(todo)}", file=sys.stderr)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    kb = CACHE.stat().st_size / 1024
    print(f"img_cache: +{ok} cached, {fail} failed; total {len(cache)} images, {kb/1024:.1f} MB",
          file=sys.stderr)
    return ok, fail


if __name__ == "__main__":
    refresh(force="--force" in sys.argv)
