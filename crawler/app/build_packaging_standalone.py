"""Build the offline packaging configurator: ui/packaging_standalone.html.

Bakes catalogue + options + engine params + per-box dielines into the page as window.PKG_DATA
(packaging.html uses baked data + a JS engine port when PKG_DATA is present — no server,
no network except the three.js CDN). Double-click to run.

  python -m app.build_packaging_standalone
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
UI = ROOT / "ui"


def _load(p, d=None):
    f = OUT / p
    return json.loads(f.read_text()) if f.exists() else d


def main():
    data = {
        "catalogue": _load("packaging_catalogue_ui.json", []),
        "options": _load("packaging_optioncat.json", {}),
        "params": _load("packaging_params.json", {}),
        "dielines": _load("packaging_dielines.json", {}),
        "dielines_multi": _load("packaging_dielines_multi.json", {}),
    }
    html = (UI / "packaging.html").read_text(encoding="utf-8")
    inject = "<script>window.PKG_DATA=" + json.dumps(data, separators=(",", ":")) + ";</script>\n"
    # inject right before the module script so window.PKG_DATA exists first
    marker = '<script type="module">'
    html = html.replace(marker, inject + marker, 1)
    html = html.replace("<title>Printoka — Packaging Boxes</title>",
                        "<title>Printoka — Packaging Boxes (offline)</title>")
    # embed box images as self-contained data URIs (removes external image hosts)
    cache = _load("img_data_uris.json", {})
    for url, datauri in cache.items():
        if url in html:
            html = html.replace(url, datauri)
    out = UI / "packaging_standalone.html"
    out.write_text(html, encoding="utf-8")
    kb = out.stat().st_size / 1024
    print(f"wrote {out.name}: {kb:.0f} KB  (boxes={len(data['catalogue'])}, "
          f"dielines={len(data['dielines'])}, materials={len(data['options'].get('materials', []))})")


if __name__ == "__main__":
    main()
