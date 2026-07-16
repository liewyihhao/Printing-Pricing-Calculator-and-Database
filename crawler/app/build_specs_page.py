"""Generate ui/specs.html — a customer-facing, SEO-friendly Product Specifications page that
lists every product's customization options (exactly the spec we offer, mirrored from the
source order forms). Data source: output/calculator_data.json (the parity-complete fields),
grouped by the same categories the calculator uses.

  python -m app.build_specs_page
"""
from __future__ import annotations
import html
import json
import re
from pathlib import Path

# Internal/engineering wording that must never appear on the customer-facing page.
_JARGON = re.compile(
    r"check\s*price|/product|\bv4\b|order engine|curves?\b|combos?\b|param|workers?|\bapi\b|"
    r"addon|delta|sampl|\baxis\b|axes\b|pricelist|\bplx\b|readymade|metrics|crawl|\bcsv\b|"
    r"lookup|interp|kpi|excard|devv2|cookie|schema|enumerat", re.I)


def _clean_note(note):
    return note if (note and not _JARGON.search(note)) else ""

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
UI = ROOT / "ui"

CATEGORIES = [
    ("cards", "Cards & Stationery", ["business card", "pvc card", "name card", "letterhead",
        "envelope", "folder", "kad ", "voucher", "computer form", "bookmark", "money packet",
        "greeting card", "creative cut", "tent card", "id card", "lanyard", "stamp"]),
    ("print", "Books & Pads", ["booklet", "notepad", "bill-book", "wire-o notebook", "loose sheet",
        "brochure", "flyer", "customprint", "menu", "hard cover", "perfect bind"]),
    ("stickers", "Stickers & Labels", ["sticker", "label", "magnet", "cling", "car sticker", "roll form"]),
    ("signage", "Marketing & Signage", ["banner", "bunting", "roll-up", "wobbler", "hanger",
        "standee", "poster", "foamboard", "pop display", "wind flag", "x-ccessories"]),
    ("packaging", "Packaging & Bags", ["bag", "pouch", "box", "papan kopi", "sachet", "mask keeper",
        "non-woven", "kotak", "food tray", "packaging"]),
    ("calendar", "Calendars", ["calendar"]),
    ("promo", "Promo & Apparel", ["mug", "pillow", "badge", "fan", "hand fan", "button", "canvas",
        "arch file", "shirt", "jacket", "muslimah", "sweatshirt", "hoodies", "cap", "cooler", "toast"]),
]


def cat_of(name):
    n = (name or "").lower()
    for key, _label, kws in CATEGORIES:
        if key in ("promo",):
            continue
        if any(k in n for k in kws):
            return key
    for key, _label, kws in CATEGORIES:
        if key == "promo" and any(k in n for k in kws):
            return "promo"
    return "print"


SKIP_FIELD = {"custom_w", "custom_h"}


def clean_name(name):
    # keep the meaningful name incl. method/variant (e.g. "Bunting — Gear X Stand",
    # "Booklet — Litho (Offset)"); only drop internal "(= alias)" engineering notes.
    return re.sub(r"\s*\(=\s*[^)]*\)", "", name).strip()


def slugify(name):
    """Canonical per-product page slug (shared with build_product_pages)."""
    s = clean_name(name).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return re.sub(r"-+", "-", s)


def field_rows(prod):
    """Return list of (label, choices_html, note) for a product's customer-facing options."""
    contact = {}
    for r in prod.get("contactWhen", []) or []:
        for v in r.get("values", []):
            contact[(r["field"], v)] = r.get("note", "")
    rows = []
    for f in prod.get("fields", []):
        key = f.get("key", "")
        if key.startswith("ex_") or key in SKIP_FIELD:
            continue
        label = f.get("label") or key
        note = _clean_note(f.get("note") or "")
        sw = f.get("showWhen")
        if sw:
            parent = sw.get("field", "")
            plabel = next((x.get("label") for x in prod["fields"] if x.get("key") == parent), parent)
            label += f' <span class="cond">· shown when {html.escape(str(plabel))} is selected</span>'
        if f.get("type") == "number":
            choices = f'<span class="cust">enter a value in mm</span>'
        else:
            opts = f.get("options") or []
            chips = []
            for o in opts:
                cn = contact.get((key, o))
                cls = "opt onreq" if cn is not None else "opt"
                title = f' title="{html.escape(cn)}"' if cn else ""
                tag = ' <em>· on request</em>' if cn is not None else ""
                chips.append(f'<span class="{cls}"{title}>{html.escape(str(o))}{tag}</span>')
            choices = "".join(chips) if chips else "—"
        rows.append((label, choices, note))
    return rows


def build():
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))
    prods = [p for p in data["products"] if p.get("engine") != "contact" or True]  # include all
    # group
    by_cat = {key: [] for key, _l, _k in CATEGORIES}
    for p in prods:
        by_cat[cat_of(p["name"])].append(p)
    for key in by_cat:
        by_cat[key].sort(key=lambda p: clean_name(p["name"]))

    total = len(prods)
    cat_meta = [(k, l) for k, l, _ in CATEGORIES if by_cat[k]]

    # ---- JSON-LD (ItemList of products) for SEO ----
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": "Printoka product specifications",
          "numberOfItems": total, "itemListElement": []}
    pos = 1
    for key, _l, _k in CATEGORIES:
        for p in by_cat.get(key, []):
            opts = [f.get("label") for f in p.get("fields", []) if not f.get("key", "").startswith("ex_") and f.get("key") not in SKIP_FIELD]
            ld["itemListElement"].append({"@type": "ListItem", "position": pos, "item": {
                "@type": "Product", "name": clean_name(p["name"]),
                "description": "Customisation options: " + ", ".join(str(o) for o in opts if o)[:280]}})
            pos += 1

    # ---- nav + sections ----
    nav = "".join(f'<a href="#{k}" class="navchip">{html.escape(l)} <b>{len(by_cat[k])}</b></a>' for k, l in cat_meta)
    sections = []
    for key, label in cat_meta:
        cards = []
        for p in by_cat[key]:
            name = html.escape(clean_name(p["name"]))
            raw = _clean_note((p.get("note") or "").strip())
            desc = html.escape(raw) if raw else (
                f"Fully customisable {html.escape(clean_name(p['name']))} — choose your specification below and get an instant price.")
            rows = field_rows(p)
            body = "".join(
                f'<div class="spec"><div class="spec__k">{lab}</div>'
                f'<div class="spec__v">{ch}{f"<p class=n>{html.escape(nt)}</p>" if nt else ""}</div></div>'
                for lab, ch, nt in rows) or '<p class="n">Fixed specification — contact us to configure.</p>'
            purl = f'products/{slugify(p["name"])}.html'
            cards.append(
                f'<article class="prod" id="p-{p["id"]}">'
                f'<div class="prod__h"><h3><a href="{purl}">{name}</a></h3>'
                f'<a class="cta" href="{purl}">View product<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 4l4 4-4 4" stroke-linecap="round" stroke-linejoin="round"/></svg></a></div>'
                + (f'<p class="prod__d">{desc}</p>' if desc else "")
                + f'<div class="specs">{body}</div></article>')
        sections.append(
            f'<section class="cat" id="{key}"><div class="cat__h"><h2>{html.escape(label)}</h2>'
            f'<span class="cat__c">{len(by_cat[key])} products</span></div>'
            f'<div class="cards">{"".join(cards)}</div></section>')

    tmpl = _PAGE.replace("__NAV__", nav).replace("__SECTIONS__", "".join(sections))\
        .replace("__TOTAL__", str(total)).replace("__NCAT__", str(len(cat_meta)))\
        .replace("__LD__", json.dumps(ld, ensure_ascii=False))
    (UI / "specs.html").write_text(tmpl, encoding="utf-8")
    print(f"wrote ui/specs.html — {total} products across {len(cat_meta)} categories")


_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Product Specifications & Customisation Options — Printoka</title>
<meta name="description" content="Browse every Printoka print product and its full customisation options — sizes, papers, print colours, lamination, binding and finishing — for __TOTAL__ products across __NCAT__ categories. Configure and get an instant price.">
<meta property="og:title" content="Product Specifications — Printoka">
<meta property="og:description" content="Every product and its customisation options, in one place.">
<meta name="robots" content="index,follow">
<link rel="canonical" href="specs.html">
<style>
  :root{--ink:#212529;--muted:#546e7a;--faint:#7d879c;--hair:#e6e9ee;--line:#eef1f4;--bg:#fff;--card:#fff;
    --teal:#005b7f;--teal-d:#00485f;--yellow:#fdb913;--chip:#eef4f7;--chipink:#2b5563;
    --onreq:#a1660a;--onreqbg:#fff5e2;--shadow:0 1px 2px rgba(20,40,60,.05),0 1px 1px rgba(0,0,0,.03);}
  *{box-sizing:border-box}
  html,body{overflow-x:hidden}
  body{margin:0;background:var(--bg);color:var(--ink);line-height:1.55;font-size:14px;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,"Noto Sans",sans-serif}
  a{color:inherit;text-decoration:none}
  .wrap{max-width:1080px;margin:0 auto;padding:0 24px}

  .topbar{border-top:3px solid var(--yellow);border-bottom:1px solid var(--hair);background:#fff}
  .topbar .wrap{display:flex;align-items:center;gap:11px;height:56px}
  .topbar b{font-size:16px;color:var(--ink)}.topbar .sub{color:var(--faint);font-size:13px}
  .topbar .spacer{margin-left:auto}.topbar .mini{font-size:13px;font-weight:600;color:var(--teal)}
  header.hero{background:#fff;padding:26px 0 6px}
  .brand{display:flex;align-items:center;gap:11px;margin-bottom:14px}
  .orb{height:28px;width:28px;border-radius:50%;
    background:conic-gradient(from 210deg,#00b3c4,#0d6385,#005b7f,#00485f,#fdb913,#00b3c4)}
  .brand b{font-size:16px;color:var(--ink)} .brand span{color:var(--faint);font-size:13.5px}
  header h1{margin:0 0 8px;font-size:clamp(26px,3.4vw,36px);letter-spacing:-.01em;font-weight:700;line-height:1.12;color:var(--ink)}
  header p{margin:0;max-width:70ch;font-size:15px;color:var(--muted)}

  .toolbar{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.9);backdrop-filter:blur(8px);
    border-bottom:1px solid var(--hair)}
  .toolbar .wrap{display:flex;gap:12px;align-items:center;padding:12px 24px;flex-wrap:wrap}
  #q{flex:1;min-width:180px;border:1px solid var(--hair);border-radius:8px;background:#fff;
    padding:9px 12px;font-size:14px;color:var(--ink)}
  #q:focus{outline:none;border-color:var(--teal);box-shadow:0 0 0 3px rgba(0,91,127,.14)}
  .navchips{display:flex;gap:8px;flex-wrap:wrap}
  .navchip{font-size:12.5px;color:var(--teal);background:var(--chip);border-radius:6px;padding:6px 11px;font-weight:600}
  .navchip:hover{background:#dfeef4}
  .navchip b{color:var(--faint);font-weight:700;margin-left:3px}

  main{padding:30px 0 70px}
  .cat{margin-bottom:38px;scroll-margin-top:66px}
  .cat__h{display:flex;align-items:baseline;gap:12px;margin:0 0 16px;padding-bottom:10px;border-bottom:1px solid var(--hair)}
  .cat__h h2{margin:0;font-size:23px;font-weight:300;color:var(--faint)}
  .cat__c{font-size:12.5px;color:var(--faint)}
  .cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px}

  .prod{background:var(--card);border:1px solid var(--hair);border-radius:11px;padding:18px 18px 10px;
    scroll-margin-top:72px}
  .prod:hover{border-color:#cfdbe2}
  .prod__h{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:4px}
  .prod__h h3{margin:0;font-size:16px;font-weight:700}.prod__h h3 a:hover{color:var(--teal)}
  .cta{flex:none;display:inline-flex;align-items:center;gap:4px;color:#3a2c00;font-weight:700;
    font-size:12.5px;background:var(--yellow);border-radius:7px;padding:6px 11px}
  .cta:hover{background:#e9a800}
  .prod__d{margin:2px 0 12px;color:var(--faint);font-size:12.5px;line-height:1.5}
  .specs{margin-top:8px}
  .spec{display:grid;grid-template-columns:132px 1fr;gap:12px;padding:11px 0;border-top:1px solid var(--line);align-items:start}
  .spec:first-child{border-top:none}
  .spec__k{font-size:12.5px;font-weight:700;color:var(--teal)}
  .spec__k .cond{display:block;font-weight:400;color:var(--faint);font-size:11px;margin-top:2px}
  .spec__v{display:flex;flex-wrap:wrap;gap:5px;align-items:flex-start}
  .opt{font-size:12px;background:var(--chip);color:var(--chipink);border-radius:5px;padding:3px 8px;line-height:1.35}
  .opt.onreq{background:var(--onreqbg);color:var(--onreq)}
  .opt em{font-style:normal;opacity:.85;font-size:10.5px}
  .cust{font-size:12px;color:var(--faint);font-style:italic}
  .spec__v .n,.specs>.n{flex-basis:100%;color:var(--faint);font-size:11px;margin:3px 0 0}
  .n{color:var(--faint);font-size:11px;margin:3px 0 0}

  footer{border-top:1px solid var(--hair);color:var(--faint);font-size:12.5px}
  footer .wrap{display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;padding:22px 24px 50px}
  footer a{color:var(--teal)}
  .empty{display:none;text-align:center;color:var(--faint);padding:50px 0;font-size:14px}
  @media (max-width:560px){.cards{grid-template-columns:1fr}.spec{grid-template-columns:1fr;gap:4px}}
</style>
<script type="application/ld+json">__LD__</script>
</head>
<body>
  <div class="topbar"><div class="wrap">
    <span class="orb"></span><b>Printoka</b><span class="sub">/ product specifications</span>
    <span class="spacer"></span><a class="mini" href="calculator_standalone.html">Pricing calculator</a>
  </div></div>
  <header class="hero"><div class="wrap">
    <h1>Every product, every option</h1>
    <p>Browse our full print catalogue and the customisation we offer — sizes, papers, print colours, lamination, binding and finishing. __TOTAL__ products across __NCAT__ categories. Pick a product, view its full spec and get an instant price.</p>
  </div></header>

  <div class="toolbar"><div class="wrap">
    <input id="q" type="search" placeholder="Search products — e.g. card, sticker, box, banner…" aria-label="Search products">
    <nav class="navchips">__NAV__</nav>
  </div></div>

  <main class="wrap">
    __SECTIONS__
    <p class="empty" id="empty">No products match your search.</p>
  </main>

  <footer><div class="wrap">
    <span>Options mirror our live order forms. <a href="calculator_standalone.html">Open the pricing calculator →</a></span>
    <span>Printoka · product specifications</span>
  </div></footer>

  <script>
    // Progressive enhancement: instant search filter (page is fully readable without JS for SEO).
    const q=document.getElementById('q'), empty=document.getElementById('empty');
    const prods=[...document.querySelectorAll('.prod')].map(el=>({el,t:el.textContent.toLowerCase()}));
    const cats=[...document.querySelectorAll('.cat')];
    q&&q.addEventListener('input',()=>{
      const s=q.value.trim().toLowerCase(); let any=false;
      prods.forEach(p=>{const m=!s||p.t.includes(s);p.el.style.display=m?'':'none';if(m)any=true;});
      cats.forEach(c=>{const vis=[...c.querySelectorAll('.prod')].some(e=>e.style.display!=='none');c.style.display=vis?'':'none';});
      empty.style.display=any?'none':'block';
    });
    document.querySelectorAll('.navchip').forEach(a=>a.addEventListener('click',()=>{if(q){q.value='';q.dispatchEvent(new Event('input'));}}));
  </script>
</body>
</html>
"""

if __name__ == "__main__":
    build()
