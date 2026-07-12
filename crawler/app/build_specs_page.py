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
            cards.append(
                f'<article class="prod" id="p-{p["id"]}">'
                f'<div class="prod__h"><h3>{name}</h3>'
                f'<a class="cta" href="calculator_standalone.html">Get a price<svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 4l4 4-4 4" stroke-linecap="round" stroke-linejoin="round"/></svg></a></div>'
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
  :root{--ink:#0a2540;--muted:#425466;--faint:#697386;--hair:#e6ebf1;--bg:#f6f9fc;--card:#fff;
    --blurple:#635bff;--chip:#f0f3f9;--onreq:#8a6d1f;--onreqbg:#fbf1d3;
    --shadow:0 1px 2px rgba(60,66,87,.06),0 1px 1px rgba(0,0,0,.03);}
  *{box-sizing:border-box}
  html,body{overflow-x:hidden}
  body{margin:0;background:var(--bg);color:var(--ink);line-height:1.5;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif}
  a{color:inherit;text-decoration:none}
  .wrap{max-width:1080px;margin:0 auto;padding:0 24px}

  header.hero{background:linear-gradient(102deg,#3ee0d8 0%,#3b8bff 30%,#635bff 60%,#8b5cf6 100%);
    color:#fff;padding:56px 24px 66px;clip-path:polygon(0 0,100% 0,100% calc(100% - 40px),0 100%)}
  .hero .wrap{padding-bottom:8px}
  .brand{display:flex;align-items:center;gap:11px;margin-bottom:26px}
  .orb{height:30px;width:30px;border-radius:50%;
    background:conic-gradient(from 210deg,#42e8e0,#3b8bff,#635bff,#8b5cf6,#ff5c8a,#ffcb57,#42e8e0)}
  .brand b{font-size:17px;letter-spacing:-.02em} .brand span{opacity:.75;font-size:13.5px}
  header h1{margin:0 0 10px;font-size:clamp(28px,4vw,42px);letter-spacing:-.03em;font-weight:800;line-height:1.08}
  header p{margin:0;max-width:64ch;font-size:clamp(15px,1.4vw,17px);opacity:.92}

  .toolbar{position:sticky;top:0;z-index:20;background:rgba(246,249,252,.86);backdrop-filter:blur(8px);
    border-bottom:1px solid var(--hair)}
  .toolbar .wrap{display:flex;gap:12px;align-items:center;padding:12px 24px;flex-wrap:wrap}
  #q{flex:1;min-width:180px;border:1px solid var(--hair);border-radius:9px;background:#fff;
    padding:9px 12px;font-size:14px;color:var(--ink);box-shadow:var(--shadow)}
  #q:focus{outline:none;border-color:var(--blurple);box-shadow:0 0 0 3px rgba(99,91,255,.15)}
  .navchips{display:flex;gap:7px;flex-wrap:wrap}
  .navchip{font-size:12.5px;color:var(--muted);background:#fff;border:1px solid var(--hair);
    border-radius:20px;padding:6px 11px;box-shadow:var(--shadow)}
  .navchip:hover{border-color:#cdd6e4;color:var(--ink)}
  .navchip b{color:var(--blurple);font-weight:700;margin-left:2px}

  main{padding:34px 0 70px}
  .cat{margin-bottom:40px;scroll-margin-top:66px}
  .cat__h{display:flex;align-items:baseline;gap:12px;margin:0 2px 16px;padding-bottom:10px;border-bottom:1px solid var(--hair)}
  .cat__h h2{margin:0;font-size:20px;letter-spacing:-.02em}
  .cat__c{font-size:12.5px;color:var(--faint)}
  .cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px}

  .prod{background:var(--card);border:1px solid var(--hair);border-radius:14px;padding:18px 18px 8px;
    box-shadow:var(--shadow);scroll-margin-top:72px}
  .prod__h{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:4px}
  .prod__h h3{margin:0;font-size:16px;letter-spacing:-.01em}
  .cta{flex:none;display:inline-flex;align-items:center;gap:4px;color:var(--blurple);font-weight:600;
    font-size:12.5px;border:1px solid #e4e2ff;background:#f4f3ff;border-radius:8px;padding:5px 9px}
  .cta:hover{background:#ecebff}
  .prod__d{margin:2px 0 12px;color:var(--faint);font-size:12.5px;line-height:1.5}
  .specs{margin-top:8px}
  .spec{display:grid;grid-template-columns:132px 1fr;gap:12px;padding:10px 0;border-top:1px solid #f0f3f8;align-items:start}
  .spec:first-child{border-top:none}
  .spec__k{font-size:12.5px;font-weight:600;color:var(--muted)}
  .spec__k .cond{display:block;font-weight:400;color:var(--faint);font-size:11px;margin-top:2px}
  .spec__v{display:flex;flex-wrap:wrap;gap:5px;align-items:flex-start}
  .opt{font-size:12px;background:var(--chip);color:#334155;border-radius:6px;padding:3px 8px;line-height:1.35}
  .opt.onreq{background:var(--onreqbg);color:var(--onreq)}
  .opt em{font-style:normal;opacity:.8;font-size:10.5px}
  .cust{font-size:12px;color:var(--faint);font-style:italic}
  .spec__v .n,.specs>.n{flex-basis:100%;color:var(--faint);font-size:11px;margin:3px 0 0}
  .n{color:var(--faint);font-size:11px;margin:3px 0 0}

  footer{border-top:1px solid var(--hair);color:var(--faint);font-size:12.5px}
  footer .wrap{display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;padding:22px 24px 50px}
  footer a{color:var(--blurple)}
  .empty{display:none;text-align:center;color:var(--faint);padding:50px 0;font-size:14px}
  @media (max-width:560px){.cards{grid-template-columns:1fr}.spec{grid-template-columns:1fr;gap:4px}}
</style>
<script type="application/ld+json">__LD__</script>
</head>
<body>
  <header class="hero"><div class="wrap">
    <div class="brand"><span class="orb"></span><b>Printoka</b><span>/ product specifications</span></div>
    <h1>Every product, every option</h1>
    <p>Browse our full print catalogue and the customisation we offer — sizes, papers, print colours, lamination, binding and finishing. __TOTAL__ products across __NCAT__ categories. Pick a product, configure it, and get an instant price.</p>
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
