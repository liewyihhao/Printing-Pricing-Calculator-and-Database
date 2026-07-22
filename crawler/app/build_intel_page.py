"""Render ui/intelligence.html — an internal dashboard of the Excard site intelligence gathered
by app.excard_intel (output/excard_intelligence.json). Data is baked in (self-contained).

  python -m app.excard_intel        # gather/refresh the intelligence
  python -m app.build_intel_page    # render the dashboard
"""
from __future__ import annotations
import html, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
UI = ROOT / "ui"


def build():
    d = json.loads((OUT / "excard_intelligence.json").read_text(encoding="utf-8"))
    s = d["summary"]; site = s["site"]; prod = s["products"]
    tiles = [
        ("Sitemap URLs", site["sitemap_urls"]),
        ("Products", prod["count"]),
        ("Product pages read", prod["fetched"]),
        ("With downloadable PDF", prod["with_pdf"]),
        ("With template", prod["with_template"]),
        ("With FAQ", prod["with_faq"]),
        ("With production limits", prod["with_min_max"]),
        ("Help / education pages", site["by_type"].get("help", 0)),
    ]
    tile_html = "".join(
        f'<div class="card p-4"><div class="text-[12px] text-slate-500">{html.escape(t)}</div>'
        f'<div class="text-[26px] font-bold mt-0.5">{v}</div></div>' for t, v in tiles)

    inv = site["by_type"]
    inv_html = "".join(
        f'<div class="flex justify-between py-1.5 border-b border-slate-100"><span class="text-slate-600">{html.escape(k)}</span>'
        f'<span class="font-semibold tabular-nums">{v}</span></div>' for k, v in inv.items())
    help_html = "".join(f'<li><a class="text-indigo-600 hover:underline" href="{html.escape(u)}" target="_blank" rel="noopener nofollow">{html.escape(u.split("/")[-1])}</a></li>'
                        for u in site.get("help_pages", []))

    rows = []
    for r in sorted(d["products"], key=lambda x: x.get("slug", "")):
        if not r.get("fetched"):
            rows.append(f'<tr><td class="px-3 py-2">{html.escape(r.get("slug",""))}</td>'
                        f'<td class="px-3 py-2 text-red-500" colspan="6">not fetched</td></tr>')
            continue
        def chip(ok): return ('<span class="chip ok">yes</span>' if ok else '<span class="chip no">—</span>')
        fin = ", ".join(r.get("finishing", [])[:3]) or "—"
        mm = r.get("min_max") or []
        mmtxt = (f'{mm[0][0]}→{mm[0][1]}' if mm else "—")
        rows.append(
            f'<tr class="border-t border-slate-100">'
            f'<td class="px-3 py-2 font-medium">{html.escape(r.get("title") or r.get("slug"))}</td>'
            f'<td class="px-3 py-2 text-slate-500">{len(r.get("tabs",[]))}</td>'
            f'<td class="px-3 py-2 text-slate-500 max-w-[220px] truncate">{html.escape(fin)}</td>'
            f'<td class="px-3 py-2 text-center">{chip(r.get("has_template"))}</td>'
            f'<td class="px-3 py-2 text-center">{chip(r.get("has_pdf"))}</td>'
            f'<td class="px-3 py-2 text-center">{chip(r.get("has_faq"))}</td>'
            f'<td class="px-3 py-2 text-slate-500">{html.escape(mmtxt)}</td></tr>')

    common = "".join(
        f'<span class="chip sec">{html.escape(str(k))} · {v}</span>' for k, v in s.get("common_spec_sections", [])[:16])

    page = _PAGE.replace("__TILES__", tile_html).replace("__INV__", inv_html)\
        .replace("__HELP__", help_html).replace("__ROWS__", "".join(rows))\
        .replace("__COMMON__", common).replace("__GEN__", html.escape(d.get("generated_at", "")))\
        .replace("__NPROD__", str(prod["count"]))
    (UI / "intelligence.html").write_text(page, encoding="utf-8")
    print(f"wrote ui/intelligence.html — {prod['count']} products, {site['sitemap_urls']} sitemap URLs")


_PAGE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Printoka — Supplier Site Intelligence</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>
  body{font-family:Inter,system-ui,sans-serif;background:#f6f8fc;color:#0f172a}
  .card{background:#fff;border:1px solid #e8edf5;border-radius:14px;box-shadow:0 1px 2px rgba(16,24,40,.04)}
  .chip{display:inline-block;font-size:11px;border-radius:5px;padding:2px 7px;font-weight:600}
  .chip.ok{background:#dcfce7;color:#166534}.chip.no{background:#f1f5f9;color:#94a3b8}
  .chip.sec{background:#eef2ff;color:#4338ca;margin:2px}
  th{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:#64748b;text-align:left}
</style></head>
<body class="p-6 sm:p-10">
  <div class="max-w-6xl mx-auto">
    <div class="flex items-center gap-3 mb-1">
      <div class="h-9 w-9 rounded-lg grid place-items-center text-white font-bold" style="background:linear-gradient(135deg,#6366f1,#8b5cf6)">P</div>
      <h1 class="text-[22px] font-bold">Supplier Site Intelligence</h1>
      <span class="ml-auto text-[12px] text-slate-400">generated __GEN__</span>
    </div>
    <p class="text-slate-500 text-[13.5px] mb-6">A structured read of the supplier's public website — catalogue shape, per-product content and facts. Read-only; facts only.</p>

    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">__TILES__</div>

    <div class="grid md:grid-cols-3 gap-4 mb-6">
      <div class="card p-5"><h2 class="font-semibold mb-2">Site inventory</h2><div class="text-[13px]">__INV__</div></div>
      <div class="card p-5"><h2 class="font-semibold mb-2">Help &amp; education pages</h2><ul class="text-[13px] space-y-1 list-disc pl-4">__HELP__</ul></div>
      <div class="card p-5"><h2 class="font-semibold mb-2">Common spec sections</h2><div>__COMMON__</div></div>
    </div>

    <div class="card overflow-hidden">
      <div class="px-5 py-3 border-b border-slate-100 font-semibold">Per-product intelligence · __NPROD__ products</div>
      <div class="overflow-x-auto"><table class="w-full text-[13px]">
        <thead><tr class="bg-slate-50">
          <th class="px-3 py-2">Product</th><th class="px-3 py-2">Tabs</th><th class="px-3 py-2">Finishing</th>
          <th class="px-3 py-2 text-center">Template</th><th class="px-3 py-2 text-center">PDF</th>
          <th class="px-3 py-2 text-center">FAQ</th><th class="px-3 py-2">Min→Max</th>
        </tr></thead><tbody>__ROWS__</tbody></table></div>
    </div>
    <p class="text-slate-400 text-[12px] mt-6">Source: app/excard_intel.py → output/excard_intelligence.json. Refresh with <code>python -m app.excard_intel</code>.</p>
  </div>
</body></html>
"""

if __name__ == "__main__":
    build()
