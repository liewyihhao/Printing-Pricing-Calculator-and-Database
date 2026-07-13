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
from app.build_standalone import _PRICELIST_FROM_OPTIONS as _PLO

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
UI = ROOT / "ui"
PDIR = UI / "products"
TDIR = UI / "templates"

CAT_LABEL = {k: l for k, l, _ in CATEGORIES}
EXCARD_SEARCH = "https://www.excard.com.my/"


def _order_urls():
    """id -> Excard order URL. Prefer the verified www product page (from the catalogue's
    built_as map); fall back to the v4 ordering slug; else Excard home/search."""
    m = {}
    try:
        cat = json.loads((OUT / "excard_catalogue.json").read_text(encoding="utf-8"))["products"]
        for c in cat:
            for b in (c.get("built_as") or []):
                mm = re.search(r"\((\d+)\)", b)
                if mm and c.get("url"):
                    m[int(mm.group(1))] = c["url"]
    except Exception:
        pass
    for pid, (slug, _tag) in _PLO.items():
        m.setdefault(pid, f"https://v4.excard.com.my/ordering/{slug.lower()}")
    return m


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


def _page(prod, cat_key, order_url, prev_p, next_p):
    pid = prod["id"]
    name = clean_name(prod["name"])
    slug = slugify(prod["name"])
    cat_label = CAT_LABEL.get(cat_key, "Print")
    exact = prod.get("accuracy") == 0
    opt_labels = [f.get("label") or f.get("key") for f in prod.get("fields", [])
                  if not f.get("key", "").startswith("ex_") and f.get("key") not in SKIP_FIELD]
    intro = _intro(name, cat_label, opt_labels)

    # ---- options table (reuse specs field rendering) ----
    rows = field_rows(prod)
    specs_html = "".join(
        f'<div class="spec"><div class="spec__k">{lab}</div>'
        f'<div class="spec__v">{ch}{f"<p class=n>{html.escape(nt)}</p>" if nt else ""}</div></div>'
        for lab, ch, nt in rows) or '<p class="n">Fixed specification — contact us to configure.</p>'

    # ---- templates ----
    tpls = _templates_for(slug)
    if tpls:
        thtml = '<div class="tpl-grid">' + "".join(
            f'<a class="tpl" href="{href}" download><span class="tpl__i">⬇</span>'
            f'<span class="tpl__n">{html.escape(fn)}</span><span class="tpl__s">{sz}</span></a>'
            for fn, href, sz in tpls) + '</div>'
    else:
        thtml = ('<p class="tpl-empty">Print-ready templates (die-lines &amp; artwork guides) for '
                 f'{html.escape(name)} are coming soon. <a href="{html.escape(order_url)}" '
                 'target="_blank" rel="noopener nofollow">Request a template</a> or start from the '
                 'specification below.</p>')

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
            .replace("__ORDERURL__", html.escape(order_url))
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
    orders = _order_urls()
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
        url = orders.get(p["id"], EXCARD_SEARCH)
        page = _page(p, cat_key, url, ordered[i - 1] if i else None,
                     ordered[i + 1] if i + 1 < len(ordered) else None)
        (PDIR / f"{slugify(p['name'])}.html").write_text(page, encoding="utf-8")
        n += 1
    (PDIR / "index.html").write_text(_index(by_cat, cat_meta), encoding="utf-8")
    print(f"wrote {n} product pages + index to ui/products/ "
          f"({sum(1 for p in prods if p['id'] in orders)} with an Excard order link)")


# ---------------------------------------------------------------- templates
_STYLE = r"""
  :root{--ink:#0a2540;--muted:#425466;--faint:#697386;--hair:#e6ebf1;--bg:#f6f9fc;--card:#fff;
    --blurple:#635bff;--chip:#f0f3f9;--onreq:#8a6d1f;--onreqbg:#fbf1d3;
    --shadow:0 1px 2px rgba(60,66,87,.06),0 1px 1px rgba(0,0,0,.03);}
  *{box-sizing:border-box} html,body{overflow-x:hidden}
  body{margin:0;background:var(--bg);color:var(--ink);line-height:1.55;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Helvetica,Arial,sans-serif}
  a{color:inherit;text-decoration:none}
  .wrap{max-width:1000px;margin:0 auto;padding:0 24px}
  header.hero{background:linear-gradient(102deg,#3ee0d8 0%,#3b8bff 30%,#635bff 60%,#8b5cf6 100%);
    color:#fff;padding:22px 24px 60px;clip-path:polygon(0 0,100% 0,100% calc(100% - 38px),0 100%)}
  .brand{display:flex;align-items:center;gap:11px;margin-bottom:20px}
  .orb{height:28px;width:28px;border-radius:50%;
    background:conic-gradient(from 210deg,#42e8e0,#3b8bff,#635bff,#8b5cf6,#ff5c8a,#ffcb57,#42e8e0)}
  .brand b{font-size:16px;letter-spacing:-.02em}.brand span{opacity:.8;font-size:13px}
  .crumbs{font-size:12.5px;opacity:.9;margin-bottom:12px}.crumbs a:hover{text-decoration:underline}
  header h1{margin:0 0 10px;font-size:clamp(26px,4vw,40px);letter-spacing:-.03em;font-weight:800;line-height:1.1}
  header p.lead{margin:0;max-width:66ch;font-size:clamp(15px,1.4vw,17px);opacity:.95}
  .badge{display:inline-block;margin-top:14px;font-size:12px;font-weight:600;border-radius:20px;padding:5px 11px}
  .badge--ok{background:rgba(255,255,255,.18);color:#fff} .badge--ref{background:rgba(255,255,255,.14);color:#eef}
  main{padding:26px 0 60px}
  .ctarow{display:flex;gap:12px;flex-wrap:wrap;margin:-42px 0 30px;position:relative;z-index:5}
  .btn{display:inline-flex;align-items:center;gap:8px;border-radius:11px;padding:13px 20px;font-size:14.5px;
    font-weight:600;box-shadow:var(--shadow);border:1px solid transparent}
  .btn--primary{background:var(--blurple);color:#fff}.btn--primary:hover{background:#5147f5}
  .btn--ghost{background:#fff;color:var(--ink);border-color:var(--hair)}.btn--ghost:hover{border-color:#cdd6e4}
  .btn svg{height:15px;width:15px}
  .grid{display:grid;grid-template-columns:1fr;gap:20px}
  @media(min-width:820px){.grid{grid-template-columns:1.55fr 1fr}}
  .panel{background:var(--card);border:1px solid var(--hair);border-radius:16px;padding:22px 22px 14px;box-shadow:var(--shadow)}
  .panel h2{margin:0 0 4px;font-size:17px;letter-spacing:-.01em}
  .panel .sub{margin:0 0 14px;color:var(--faint);font-size:12.5px}
  .spec{display:grid;grid-template-columns:140px 1fr;gap:12px;padding:11px 0;border-top:1px solid #f0f3f8;align-items:start}
  .spec:first-child{border-top:none}
  .spec__k{font-size:12.5px;font-weight:600;color:var(--muted)}
  .spec__k .cond{display:block;font-weight:400;color:var(--faint);font-size:11px;margin-top:2px}
  .spec__v{display:flex;flex-wrap:wrap;gap:5px}
  .opt{font-size:12px;background:var(--chip);color:#334155;border-radius:6px;padding:3px 8px;line-height:1.35}
  .opt.onreq{background:var(--onreqbg);color:var(--onreq)}.opt em{font-style:normal;opacity:.8;font-size:10.5px}
  .cust{font-size:12px;color:var(--faint);font-style:italic}
  .n{color:var(--faint);font-size:11px;margin:3px 0 0;flex-basis:100%}
  .tpl-grid{display:grid;grid-template-columns:1fr;gap:9px}
  .tpl{display:flex;align-items:center;gap:11px;border:1px solid var(--hair);border-radius:10px;padding:11px 13px;background:#fbfcfe}
  .tpl:hover{border-color:var(--blurple);background:#f4f3ff}
  .tpl__i{height:26px;width:26px;border-radius:7px;background:#eef0ff;color:var(--blurple);display:grid;place-items:center;font-size:13px}
  .tpl__n{font-size:13px;font-weight:600;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .tpl__s{font-size:11.5px;color:var(--faint)}
  .tpl-empty{font-size:13px;color:var(--muted);margin:2px 0 12px}.tpl-empty a{color:var(--blurple);font-weight:600}
  aside .panel{position:sticky;top:18px}
  .aside-cta{display:flex;flex-direction:column;gap:10px;margin-top:6px}
  .seo{margin-top:26px;color:var(--muted);font-size:13.5px;line-height:1.7}
  .seo h2{color:var(--ink);font-size:17px;margin:0 0 8px}
  .pager-row{display:flex;justify-content:space-between;gap:12px;margin-top:30px}
  .pager{font-size:13px;color:var(--muted);background:#fff;border:1px solid var(--hair);border-radius:9px;padding:9px 13px;box-shadow:var(--shadow)}
  .pager:hover{border-color:#cdd6e4;color:var(--ink)}.pager--r{margin-left:auto}
  footer{border-top:1px solid var(--hair);color:var(--faint);font-size:12.5px;margin-top:20px}
  footer .wrap{display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;padding:22px 24px 46px}
  footer a{color:var(--blurple)}
  @media(max-width:560px){.spec{grid-template-columns:1fr;gap:4px}.ctarow{margin-top:-34px}}
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
  <header class="hero"><div class="wrap">
    <div class="brand"><span class="orb"></span><b>Printoka</b><span>/ __CATLABEL__</span></div>
    <nav class="crumbs"><a href="../index.html">Home</a> › <a href="index.html">Products</a> ›
      <a href="index.html#__CATKEY__">__CATLABEL__</a> › <span>__NAME__</span></nav>
    <h1>__NAME__ Printing</h1>
    <p class="lead">__INTRO__</p>
    __ACCBADGE__
  </div></header>

  <main class="wrap">
    <div class="ctarow">
      <a class="btn btn--primary" href="__SIMURL__">Check price / use the simulator
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 4l4 4-4 4" stroke-linecap="round" stroke-linejoin="round"/></svg></a>
      <a class="btn btn--ghost" href="__ORDERURL__" target="_blank" rel="noopener nofollow">Place order</a>
      <a class="btn btn--ghost" href="#templates">Download templates</a>
    </div>

    <div class="grid">
      <div>
        <section class="panel">
          <h2>Customisation options</h2>
          <p class="sub">Everything you can configure for __NAME__ — mirrored from our live order form.</p>
          <div class="specs">__SPECS__</div>
        </section>

        <section class="panel" id="templates" style="margin-top:20px">
          <h2>Print-ready templates</h2>
          <p class="sub">Set up your artwork on the correct die-line and bleed before you order.</p>
          __TEMPLATES__
        </section>

        <div class="seo">
          <h2>About __NAME__ printing</h2>
          <p>Looking to print __NAME__ in Malaysia? Printoka gives you every specification up front,
          an exact price in seconds, and a downloadable template so your artwork is production-ready.
          Configure your __NAME__ exactly how you need it, compare membership-tier savings, and place
          your order online.</p>
        </div>

        <div class="pager-row">__PREV____NEXT__</div>
      </div>

      <aside>
        <div class="panel">
          <h2>Get __NAME__ now</h2>
          <p class="sub">Instant price, then order.</p>
          <div class="aside-cta">
            <a class="btn btn--primary" href="__SIMURL__" style="justify-content:center">Check the price</a>
            <a class="btn btn--ghost" href="__ORDERURL__" target="_blank" rel="noopener nofollow" style="justify-content:center">Place order</a>
            <a class="btn btn--ghost" href="#templates" style="justify-content:center">Download template</a>
          </div>
        </div>
      </aside>
    </div>
  </main>

  <footer><div class="wrap">
    <span><a href="index.html">← All products</a> · <a href="../specs.html">Full specifications</a></span>
    <span>Printoka · custom __NAME__ printing</span>
  </div></footer>
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
  .navchips{display:flex;gap:7px;flex-wrap:wrap;margin-top:14px}
  .navchip{font-size:12.5px;color:#fff;background:rgba(255,255,255,.16);border-radius:20px;padding:6px 11px}
  .navchip b{font-weight:700;margin-left:2px}
  .cat{margin-bottom:36px;scroll-margin-top:16px}
  .cat__h{display:flex;align-items:baseline;gap:12px;margin:0 2px 14px;padding-bottom:10px;border-bottom:1px solid var(--hair)}
  .cat__h h2{margin:0;font-size:19px;letter-spacing:-.02em}.cat__c{font-size:12.5px;color:var(--faint)}
  .pcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}
  .pcard{display:flex;align-items:center;gap:11px;background:var(--card);border:1px solid var(--hair);
    border-radius:12px;padding:13px 14px;box-shadow:var(--shadow)}
  .pcard:hover{border-color:var(--blurple);transform:translateY(-1px);transition:.15s}
  .pcard__o{height:32px;width:32px;border-radius:9px;background:linear-gradient(135deg,#635bff,#8b5cf6);
    color:#fff;display:grid;place-items:center;font-weight:700;font-size:14px;flex:none}
  .pcard__n{font-size:13.5px;font-weight:600;flex:1;min-width:0}
  .pcard__b{font-size:10px;color:#0a7d55;background:#e7f7ef;border-radius:5px;padding:2px 6px;font-weight:700}
</style>
</head>
<body>
  <header class="hero"><div class="wrap">
    <div class="brand"><span class="orb"></span><b>Printoka</b><span>/ products</span></div>
    <h1>Custom printing, priced instantly</h1>
    <p class="lead">__TOTAL__ products across __NCAT__ categories. Pick a product to see its options,
      download a template, check the price and order.</p>
    <nav class="navchips">__NAV__</nav>
  </div></header>
  <main class="wrap" style="padding-top:34px">__SECTIONS__</main>
  <footer><div class="wrap">
    <span><a href="../specs.html">Full specifications</a> · <a href="../calculator_standalone.html">Pricing calculator</a></span>
    <span>Printoka · products</span>
  </div></footer>
</body>
</html>
""".replace("__STYLE__", _STYLE)


if __name__ == "__main__":
    build()
