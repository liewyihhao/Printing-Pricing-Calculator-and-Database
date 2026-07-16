"""Generate ui/products/<slug>.html — one SEO-optimised landing page per product, plus
ui/products/index.html.

Each page:
  * ranks for "<product> printing [malaysia]" style keywords (title, meta, H1, intro copy,
    Product + BreadcrumbList JSON-LD, breadcrumbs),
  * lists the full customisation options (mirrored from the order form, same data as specs.html),
  * offers print-ready templates from ui/templates/<slug>/ (drop your own rights-cleared files
    there — the page auto-lists whatever is present, else shows a "request a template" note),
  * funnels to the price simulator (../calculator_standalone.html?product=<id>) and to Excard's
    order form ("Place order").

Data source: output/calculator_data.json. Order URLs: excard product pages (from
output/excard_catalogue.json built_as) with a v4 ordering-slug fallback.

  python -m app.build_product_pages
"""
from __future__ import annotations
import html, json, re
from pathlib import Path

from app.build_specs_page import (
    CATEGORIES, cat_of, clean_name, field_rows, _clean_note, SKIP_FIELD, slugify,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
UI = ROOT / "ui"
PDIR = UI / "products"
TDIR = UI / "templates"

CAT_LABEL = {k: l for k, l, _ in CATEGORIES}


def _rich_spec(slug: str) -> str:
    """Optional per-product depth: render output/spec_content/<slug>.json (our own factual,
    restructured spec content) as Excard-style sections. Returns "" if the file is absent."""
    f = OUT / "spec_content" / f"{slug}.json"
    if not f.is_file():
        return ""
    d = json.loads(f.read_text(encoding="utf-8"))
    out = []
    for sec in d.get("sections", []):
        title = html.escape(sec.get("title", ""))
        t = sec.get("type")
        if t == "cards":
            cards = "".join(
                f'<div class="matcard"><h4>{html.escape(it.get("name",""))}</h4>'
                f'<ul>{"".join(f"<li>{html.escape(x)}</li>" for x in it.get("ideal", []))}</ul></div>'
                for it in sec.get("items", []))
            body = f'<div class="matcards">{cards}</div>'
        elif t == "keyvalue":
            rows = "".join(f'<tr><th>{html.escape(r.get("k",""))}</th>'
                           f'<td>{html.escape(r.get("v",""))}</td></tr>' for r in sec.get("rows", []))
            body = f'<table class="kv"><tbody>{rows}</tbody></table>'
        else:
            body = f'<p class="about">{html.escape(sec.get("text",""))}</p>'
        note = f'<p class="rich-note">{html.escape(sec["note"])}</p>' if sec.get("note") else ""
        out.append(f'<div class="rich"><h3 class="sec-ttl">{title}</h3>{body}{note}</div>')
    return "".join(out)


def _templates_for(slug: str):
    """List files present under ui/templates/<slug>/ (the folder you drop rights-cleared
    template files into). Returns [(filename, rel_href, size_label)]."""
    d = TDIR / slug
    if not d.is_dir():
        return []
    out = []
    for f in sorted(d.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            kb = f.stat().st_size / 1024
            size = f"{kb/1024:.1f} MB" if kb >= 1024 else f"{kb:.0f} KB"
            out.append((f.name, f"../templates/{slug}/{html.escape(f.name)}", size))
    return out


def _intro(name: str, cat_label: str, opt_labels: list[str]) -> str:
    n = clean_name(name)
    opts = ", ".join(o.lower() for o in opt_labels[:4] if o)
    bits = [f"Custom <strong>{html.escape(n)} printing</strong> in Malaysia, made simple."]
    if opts:
        bits.append(f"Configure {html.escape(opts)} and more, then get an instant, "
                    f"market-matched price online — no waiting for a quote.")
    bits.append(f"Download a print-ready template, check the price in our simulator, and place "
                f"your order in minutes.")
    return " ".join(bits)


def _page(prod, cat_key, prev_p, next_p):
    pid = prod["id"]
    name = clean_name(prod["name"])
    slug = slugify(prod["name"])
    cat_label = CAT_LABEL.get(cat_key, "Print")
    exact = prod.get("accuracy") == 0
    opt_labels = [f.get("label") or f.get("key") for f in prod.get("fields", [])
                  if not f.get("key", "").startswith("ex_") and f.get("key") not in SKIP_FIELD]
    intro = _intro(name, cat_label, opt_labels)

    # ---- options table (reuse specs field rendering) → Excard-style spec table rows ----
    rows = field_rows(prod)
    specs_html = "".join(
        f'<tr><th>{lab}</th>'
        f'<td><div class="opts">{ch}</div>{f"<p class=n>{html.escape(nt)}</p>" if nt else ""}</td></tr>'
        for lab, ch, nt in rows) or '<tr><td class="n">Fixed specification — contact us to configure.</td></tr>'

    # ---- templates ----
    tpls = _templates_for(slug)
    if tpls:
        thtml = '<div class="tpl-grid">' + "".join(
            f'<a class="tpl" href="{href}" download><span class="tpl__i">⬇</span>'
            f'<span class="tpl__n">{html.escape(fn)}</span><span class="tpl__s">{sz}</span></a>'
            for fn, href, sz in tpls) + '</div>'
    else:
        thtml = ('<p class="tpl-empty">Print-ready templates (die-lines &amp; artwork guides) for '
                 f'{html.escape(name)} are coming soon. Start from the specification below and '
                 f'<a href="../calculator_standalone.html?product={pid}">configure &amp; order</a>.</p>')

    # ---- SEO structured data ----
    kw_desc = (f"Custom {name} printing in Malaysia. Options: "
               + ", ".join(str(o) for o in opt_labels if o))[:290]
    ld_product = {"@context": "https://schema.org", "@type": "Product", "name": name,
                  "category": cat_label, "description": kw_desc,
                  "brand": {"@type": "Brand", "name": "Printoka"}}
    ld_crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Products", "item": "index.html"},
        {"@type": "ListItem", "position": 2, "name": cat_label, "item": f"index.html#{cat_key}"},
        {"@type": "ListItem", "position": 3, "name": name, "item": f"{slug}.html"}]}

    acc_badge = ('<span class="badge badge--ok">Exact market price</span>' if exact
                 else '<span class="badge badge--ref">Reference price · ~5–10%</span>')
    nav_prev = (f'<a class="pager" href="{slugify(prev_p["name"])}.html">← {html.escape(clean_name(prev_p["name"]))}</a>'
                if prev_p else '<span></span>')
    nav_next = (f'<a class="pager pager--r" href="{slugify(next_p["name"])}.html">{html.escape(clean_name(next_p["name"]))} →</a>'
                if next_p else '<span></span>')

    return (_PROD_TMPL
            .replace("__NAME__", html.escape(name))
            .replace("__SLUG__", slug)
            .replace("__CATKEY__", cat_key)
            .replace("__CATLABEL__", html.escape(cat_label))
            .replace("__DESC__", html.escape(kw_desc))
            .replace("__INTRO__", intro)
            .replace("__ACCBADGE__", acc_badge)
            .replace("__SIMURL__", f"../calculator_standalone.html?product={pid}")
            .replace("__RICHSPEC__", _rich_spec(slug))
            .replace("__SPECS__", specs_html)
            .replace("__TEMPLATES__", thtml)
            .replace("__PREV__", nav_prev)
            .replace("__NEXT__", nav_next)
            .replace("__LDPRODUCT__", json.dumps(ld_product, ensure_ascii=False))
            .replace("__LDCRUMBS__", json.dumps(ld_crumbs, ensure_ascii=False)))


def _index(by_cat, cat_meta):
    total = sum(len(v) for v in by_cat.values())
    nav = "".join(f'<a href="#{k}" class="navchip">{html.escape(l)} <b>{len(by_cat[k])}</b></a>'
                  for k, l in cat_meta)
    secs = []
    for key, label in cat_meta:
        cards = "".join(
            f'<a class="pcard" href="{slugify(p["name"])}.html">'
            f'<span class="pcard__o">{html.escape(clean_name(p["name"])[0])}</span>'
            f'<span class="pcard__n">{html.escape(clean_name(p["name"]))}</span>'
            f'{"<span class=pcard__b>Exact price</span>" if p.get("accuracy")==0 else ""}</a>'
            for p in by_cat[key])
        secs.append(f'<section class="cat" id="{key}"><div class="cat__h"><h2>{html.escape(label)}</h2>'
                    f'<span class="cat__c">{len(by_cat[key])} products</span></div>'
                    f'<div class="pcards">{cards}</div></section>')
    return (_INDEX_TMPL.replace("__NAV__", nav).replace("__SECTIONS__", "".join(secs))
            .replace("__TOTAL__", str(total)).replace("__NCAT__", str(len(cat_meta))))


def build():
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))
    prods = data["products"]
    PDIR.mkdir(parents=True, exist_ok=True)
    TDIR.mkdir(parents=True, exist_ok=True)

    by_cat = {k: [] for k, _l, _k in CATEGORIES}
    for p in prods:
        by_cat[cat_of(p["name"])].append(p)
    for k in by_cat:
        by_cat[k].sort(key=lambda p: clean_name(p["name"]))
    cat_meta = [(k, l) for k, l, _ in CATEGORIES if by_cat[k]]

    # flat ordered list for prev/next pagers
    ordered = [p for k, _l in cat_meta for p in by_cat[k]]
    n = 0
    for i, p in enumerate(ordered):
        cat_key = cat_of(p["name"])
        page = _page(p, cat_key, ordered[i - 1] if i else None,
                     ordered[i + 1] if i + 1 < len(ordered) else None)
        (PDIR / f"{slugify(p['name'])}.html").write_text(page, encoding="utf-8")
        n += 1
    (PDIR / "index.html").write_text(_index(by_cat, cat_meta), encoding="utf-8")
    print(f"wrote {n} product pages + index to ui/products/ (order flow -> calculator, no external links)")


# ---------------------------------------------------------------- templates
# Design language mirrored from the supplier's product-spec page: white/airy, system font,
# large light-weight muted section titles, bold-teal tabbed nav, signature yellow primary CTA,
# clean minimal spec tables.
_STYLE = r"""
  :root{--ink:#212529;--muted:#546e7a;--faint:#7d879c;--hair:#e6e9ee;--line:#eef1f4;--bg:#fff;
    --teal:#005b7f;--teal-d:#00485f;--yellow:#fdb913;--yellow-d:#e9a800;--link:#007bff;
    --red:#c72926;--chip:#eef4f7;--chipink:#2b5563;--onreq:#a1660a;--onreqbg:#fff5e2;
    --shadow:0 1px 2px rgba(20,40,60,.05),0 1px 1px rgba(0,0,0,.03);}
  *{box-sizing:border-box} html,body{overflow-x:hidden}
  body{margin:0;background:var(--bg);color:var(--ink);line-height:1.55;font-size:14px;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,"Noto Sans",sans-serif}
  a{color:inherit;text-decoration:none}
  .wrap{max-width:1040px;margin:0 auto;padding:0 22px}
  /* top brand bar */
  .topbar{border-top:3px solid var(--yellow);border-bottom:1px solid var(--hair);background:#fff}
  .topbar .wrap{display:flex;align-items:center;gap:11px;height:56px}
  .orb{height:26px;width:26px;border-radius:50%;
    background:conic-gradient(from 210deg,#00b3c4,#0d6385,#005b7f,#00485f,#fdb913,#00b3c4)}
  .topbar b{font-size:16px;letter-spacing:-.01em;color:var(--ink)}
  .topbar .cat{color:var(--faint);font-size:13px}
  .topbar .spacer{margin-left:auto}
  .topbar .mini{font-size:13px;font-weight:600;color:var(--teal)}
  /* header */
  header.hero{background:#fff;padding:22px 0 0}
  .crumbs{font-size:12.5px;color:var(--faint);margin-bottom:12px}
  .crumbs a{color:var(--teal)}.crumbs a:hover{text-decoration:underline}
  header h1{margin:0 0 8px;font-size:clamp(25px,3.4vw,34px);letter-spacing:-.01em;font-weight:700;line-height:1.15;color:var(--ink)}
  header p.lead{margin:0;max-width:70ch;font-size:15px;color:var(--muted)}
  .badge{display:inline-block;margin-top:14px;font-size:12px;font-weight:700;border-radius:5px;padding:4px 10px}
  .badge--ok{background:#e6f4ea;color:#1a7d3f} .badge--ref{background:#f1f3f5;color:#6c757d}
  .ctarow{display:flex;gap:11px;flex-wrap:wrap;margin:18px 0 4px}
  .btn{display:inline-flex;align-items:center;gap:8px;border-radius:8px;padding:11px 20px;font-size:15px;
    font-weight:700;border:1px solid transparent;cursor:pointer}
  .btn--order{background:var(--yellow);color:#3a2c00}.btn--order:hover{background:var(--yellow-d)}
  .btn--price{background:var(--teal);color:#fff}.btn--price:hover{background:var(--teal-d)}
  .btn--ghost{background:#fff;color:var(--teal);border-color:#cfdbe2}.btn--ghost:hover{border-color:var(--teal)}
  .btn svg{height:15px;width:15px}
  /* tabbed sub-nav */
  .tabs{position:sticky;top:0;z-index:10;background:#fff;border-bottom:1px solid var(--hair);margin-top:20px}
  .tabs .wrap{display:flex;gap:26px}
  .tab{appearance:none;background:none;border:none;cursor:pointer;padding:14px 2px;font-size:15px;font-weight:700;
    color:var(--faint);border-bottom:3px solid transparent;margin-bottom:-1px}
  .tab:hover{color:var(--teal)}
  .tab.active{color:var(--teal);border-bottom-color:var(--yellow)}
  main{padding:26px 0 64px}
  .panel{display:none}
  .panel.show{display:block}
  .sec-ttl{font-size:23px;font-weight:300;color:var(--faint);margin:0 0 4px;letter-spacing:.01em}
  .sec-sub{margin:0 0 18px;color:var(--muted);font-size:13.5px}
  /* spec table */
  .spectable{width:100%;border-collapse:collapse}
  .spectable tr{border-bottom:1px solid var(--line)}
  .spectable tr:last-child{border-bottom:none}
  .spectable th{text-align:left;vertical-align:top;width:180px;padding:14px 16px 14px 0;
    font-size:13px;font-weight:700;color:var(--teal)}
  .spectable th .cond{display:block;font-weight:400;color:var(--faint);font-size:11px;margin-top:3px}
  .spectable td{padding:13px 0}
  .opts{display:flex;flex-wrap:wrap;gap:6px}
  .opt{font-size:12.5px;background:var(--chip);color:var(--chipink);border-radius:5px;padding:4px 9px;line-height:1.35}
  .opt.onreq{background:var(--onreqbg);color:var(--onreq)}
  .opt em{font-style:normal;opacity:.85;font-size:11px}
  .cust{font-size:12.5px;color:var(--faint);font-style:italic}
  .n{color:var(--faint);font-size:11.5px;margin:5px 0 0}
  /* templates */
  .tpl-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}
  .tpl{display:flex;align-items:center;gap:11px;border:1px solid var(--hair);border-radius:8px;padding:12px 14px;background:#fff}
  .tpl:hover{border-color:var(--teal);background:#f6fbfd}
  .tpl__i{height:28px;width:28px;border-radius:7px;background:#e7f2f6;color:var(--teal);display:grid;place-items:center;font-size:14px}
  .tpl__n{font-size:13.5px;font-weight:600;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .tpl__s{font-size:12px;color:var(--faint)}
  .tpl-empty{font-size:14px;color:var(--muted)}.tpl-empty a{color:var(--teal);font-weight:600}
  /* order card + about */
  .ordercard{border:1px solid var(--hair);border-radius:10px;padding:20px;background:#fbfdfe;max-width:420px;margin-top:6px}
  .ordercard .price-hint{font-size:13px;color:var(--muted);margin:0 0 14px}
  .ordercard .aside-cta{display:flex;flex-direction:column;gap:10px}
  .about{color:var(--muted);font-size:14.5px;line-height:1.75;max-width:74ch}
  .about p{margin:0 0 12px}
  .pager-row{display:flex;justify-content:space-between;gap:12px;margin-top:34px;padding-top:20px;border-top:1px solid var(--hair)}
  .pager{font-size:13px;color:var(--teal);font-weight:600}
  .pager:hover{text-decoration:underline}.pager--r{margin-left:auto}
  footer{border-top:1px solid var(--hair);color:var(--faint);font-size:12.5px;margin-top:24px}
  footer .wrap{display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;padding:22px 0 46px}
  footer a{color:var(--teal)}
  /* rich spec sections (optional per-product depth) */
  .rich{margin-bottom:28px}
  .rich .sec-ttl{margin-bottom:12px}
  .matcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
  .matcard{border:1px solid var(--hair);border-radius:9px;padding:14px 15px;background:#fff}
  .matcard h4{margin:0 0 8px;font-size:14px;color:var(--teal);font-weight:700}
  .matcard ul{margin:0;padding-left:16px;color:var(--muted);font-size:12.5px;line-height:1.65}
  .kv{width:100%;border-collapse:collapse}
  .kv tr{border-bottom:1px solid var(--line)}.kv tr:last-child{border-bottom:none}
  .kv th{text-align:left;vertical-align:top;width:210px;padding:12px 16px 12px 0;font-size:13px;font-weight:700;color:var(--teal)}
  .kv td{padding:12px 0;font-size:13.5px;color:var(--ink)}
  .rich-note{font-size:12.5px;color:var(--faint);margin-top:8px}
  @media(max-width:560px){.spectable th,.kv th{width:120px}.tabs .wrap{gap:18px;overflow-x:auto}}
"""

_PROD_TMPL = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Custom __NAME__ Printing Malaysia | Instant Price &amp; Templates — Printoka</title>
<meta name="description" content="__DESC__. Download print-ready templates, check the price instantly and order online with Printoka.">
<meta name="keywords" content="__NAME__ printing, custom __NAME__, __NAME__ Malaysia, __NAME__ template, print __NAME__ online">
<meta property="og:title" content="Custom __NAME__ Printing — Printoka">
<meta property="og:description" content="__DESC__">
<meta name="robots" content="index,follow">
<link rel="canonical" href="__SLUG__.html">
<style>__STYLE__</style>
<script type="application/ld+json">__LDPRODUCT__</script>
<script type="application/ld+json">__LDCRUMBS__</script>
</head>
<body>
  <div class="topbar"><div class="wrap">
    <span class="orb"></span><b>Printoka</b><span class="cat">/ __CATLABEL__</span>
    <span class="spacer"></span>
    <a class="mini" href="../calculator_standalone.html">Pricing calculator</a>
  </div></div>

  <header class="hero"><div class="wrap">
    <nav class="crumbs"><a href="../index.html">Home</a> › <a href="index.html">Products</a> ›
      <a href="index.html#__CATKEY__">__CATLABEL__</a> › <span>__NAME__</span></nav>
    <h1>__NAME__ Printing</h1>
    <p class="lead">__INTRO__</p>
    <div>__ACCBADGE__</div>
    <div class="ctarow">
      <a class="btn btn--order" href="__SIMURL__">Order Now</a>
      <a class="btn btn--price" href="__SIMURL__">Get a Price
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M6 4l4 4-4 4" stroke-linecap="round" stroke-linejoin="round"/></svg></a>
    </div>
  </div></header>

  <nav class="tabs"><div class="wrap">
    <button class="tab active" data-tab="spec">Product Spec</button>
    <button class="tab" data-tab="templates">Templates</button>
    <button class="tab" data-tab="about">About &amp; Order</button>
  </div></nav>

  <main class="wrap">
    <section class="panel show" id="spec">
      __RICHSPEC__
      <h2 class="sec-ttl">Configurable Options</h2>
      <p class="sec-sub">Every option you can set for __NAME__ when you order — mirrored from our live order form.</p>
      <table class="spectable"><tbody>__SPECS__</tbody></table>
    </section>

    <section class="panel" id="templates">
      <h2 class="sec-ttl">Print-ready Templates</h2>
      <p class="sec-sub">Set up your artwork on the correct die-line and bleed before you order.</p>
      __TEMPLATES__
    </section>

    <section class="panel" id="about">
      <h2 class="sec-ttl">About __NAME__ &amp; Ordering</h2>
      <div class="about">
        <p>Looking to print __NAME__ in Malaysia? Printoka shows every specification up front, gives you
        an exact price in seconds, and provides a downloadable template so your artwork is production-ready.
        Configure your __NAME__ exactly how you need it, compare membership-tier savings, and order online.</p>
      </div>
      <div class="ordercard">
        <p class="price-hint">Instant price, then order — the whole flow stays on Printoka.</p>
        <div class="aside-cta">
          <a class="btn btn--order" href="__SIMURL__" style="justify-content:center">Order Now</a>
          <a class="btn btn--price" href="__SIMURL__" style="justify-content:center">Get a Price</a>
        </div>
      </div>
    </section>

    <div class="pager-row">__PREV____NEXT__</div>
  </main>

  <footer><div class="wrap">
    <span><a href="index.html">← All products</a> · <a href="../specs.html">Full specifications</a></span>
    <span>Printoka · custom __NAME__ printing</span>
  </div></footer>

  <script>
    // Tabs: progressive enhancement — all sections are in the DOM (SEO-safe); JS shows one at a time.
    var tabs=document.querySelectorAll('.tab'), panels=document.querySelectorAll('.panel');
    tabs.forEach(function(t){t.addEventListener('click',function(){
      tabs.forEach(function(x){x.classList.remove('active');}); t.classList.add('active');
      panels.forEach(function(p){p.classList.toggle('show',p.id===t.dataset.tab);});
      history.replaceState(null,'','#'+t.dataset.tab);
    });});
    // deep-link to a tab via hash
    if(location.hash){var el=document.querySelector('.tab[data-tab="'+location.hash.slice(1)+'"]');if(el)el.click();}
  </script>
</body>
</html>
""".replace("__STYLE__", _STYLE)

_INDEX_TMPL = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Print Products &amp; Custom Printing Malaysia — Printoka</title>
<meta name="description" content="Browse __TOTAL__ custom print products across __NCAT__ categories — business cards, booklets, stickers, banners, packaging and more. Templates, instant pricing and online ordering.">
<meta name="robots" content="index,follow">
<link rel="canonical" href="index.html">
<style>__STYLE__
  .navchips{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
  .navchip{font-size:12.5px;color:var(--teal);background:var(--chip);border-radius:6px;padding:6px 11px;font-weight:600}
  .navchip:hover{background:#dfeef4}.navchip b{font-weight:700;margin-left:3px;color:var(--faint)}
  .cat{margin-bottom:36px;scroll-margin-top:70px}
  .cat__h{display:flex;align-items:baseline;gap:12px;margin:0 0 14px;padding-bottom:10px;border-bottom:1px solid var(--hair)}
  .cat__h h2{margin:0;font-size:22px;font-weight:300;color:var(--faint)}.cat__c{font-size:12.5px;color:var(--faint)}
  .pcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px}
  .pcard{display:flex;align-items:center;gap:11px;background:#fff;border:1px solid var(--hair);
    border-radius:9px;padding:13px 14px}
  .pcard:hover{border-color:var(--teal);background:#f8fcfd}
  .pcard__o{height:32px;width:32px;border-radius:8px;background:linear-gradient(135deg,#0d6385,#005b7f);
    color:#fff;display:grid;place-items:center;font-weight:700;font-size:14px;flex:none}
  .pcard__n{font-size:13.5px;font-weight:600;flex:1;min-width:0;color:var(--ink)}
  .pcard__b{font-size:10px;color:#1a7d3f;background:#e6f4ea;border-radius:5px;padding:2px 6px;font-weight:700}
</style>
</head>
<body>
  <div class="topbar"><div class="wrap">
    <span class="orb"></span><b>Printoka</b><span class="cat">/ products</span>
    <span class="spacer"></span>
    <a class="mini" href="../calculator_standalone.html">Pricing calculator</a>
  </div></div>
  <header class="hero"><div class="wrap">
    <h1>Custom printing, priced instantly</h1>
    <p class="lead">__TOTAL__ products across __NCAT__ categories. Pick a product to see its full
      specification, download a template, check the price and order.</p>
    <nav class="navchips">__NAV__</nav>
  </div></header>
  <main class="wrap" style="padding-top:30px">__SECTIONS__</main>
  <footer><div class="wrap">
    <span><a href="../specs.html">Full specifications</a> · <a href="../calculator_standalone.html">Pricing calculator</a></span>
    <span>Printoka · products</span>
  </div></footer>
</body>
</html>
""".replace("__STYLE__", _STYLE)


if __name__ == "__main__":
    build()
