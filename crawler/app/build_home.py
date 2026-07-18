"""Generate ui/home.html — the customer-facing homepage (supplier-style: hero, category grid,
popular products, value props, how-it-works, education band), in the Printoka design system.

  python -m app.build_home
"""
from __future__ import annotations
import html, json
from pathlib import Path

from app.build_specs_page import CATEGORIES, cat_of, clean_name, slugify
from app.product_art import svg_for, ART_KEYFRAMES

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
UI = ROOT / "ui"

FEATURED = ["Business Card", "Label Sticker — Digital", "Flyer", "Booklet — Litho (Offset)",
            "Banner — Litho", "Kad Kahwin — Digital", "Mug — Litho", "Paper Bag — Litho"]

VALUES = [
    ("₽", "Instant agent pricing", "See the exact market-matched price the moment you configure — plus your membership-tier savings. No waiting for a quote."),
    ("◫", "Every spec, up front", "Materials, sizes, print colours and finishing for all 93 products — so you choose with confidence."),
    ("✎", "Artwork made easy", "Clear artwork specs and print-ready templates for every product, so your files are production-ready first time."),
    ("➜", "Order online in minutes", "Configure, price and place your order in one flow — the whole journey stays on Printoka."),
]
STEPS = [
    ("Configure &amp; price", "Pick a product, set your options and quantity, and get an instant price with tier savings."),
    ("Prepare your artwork", "Follow the product's artwork spec and download the matching template — bleed, resolution and cut lines sorted."),
    ("Order &amp; we produce", "Place your order online, upload artwork, and we handle production and delivery."),
]


def build():
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))
    prods = data["products"]
    by_name = {clean_name(p["name"]): p for p in prods}

    # category cards with a representative product's art + count
    by_cat = {k: [] for k, _l, _k in CATEGORIES}
    for p in prods:
        by_cat[cat_of(p["name"])].append(p)
    cat_cards = []
    for key, label, _kw in CATEGORIES:
        items = by_cat.get(key) or []
        if not items:
            continue
        rep = next((p for p in items if p.get("accuracy") == 0), items[0])
        cat_cards.append(
            f'<a class="catcard" href="products/index.html#{key}">'
            f'<div class="pa-thumb catcard__art">{svg_for(rep["name"])}</div>'
            f'<div class="catcard__b"><span class="catcard__n">{html.escape(label)}</span>'
            f'<span class="catcard__c">{len(items)} products</span></div></a>')

    feat_cards = []
    for name in FEATURED:
        p = by_name.get(name) or next((v for k, v in by_name.items() if name.split(" —")[0] in k), None)
        if not p:
            continue
        feat_cards.append(
            f'<a class="pcard" href="products/{slugify(p["name"])}.html">'
            f'<div class="pa-thumb">{svg_for(p["name"])}</div>'
            f'<div class="pcard__foot"><span class="pcard__n">{html.escape(clean_name(p["name"]))}</span>'
            f'{"<span class=pcard__b>Exact price</span>" if p.get("accuracy")==0 else ""}</div></a>')

    # a small hero art collage (three floating product illustrations)
    hero_art = "".join(f'<div class="hero-art herofloat hf{i}">{svg_for(n)}</div>'
                       for i, n in enumerate(["Business Card", "Label Sticker — Digital", "Paper Bag — Litho"]))

    value_html = "".join(
        f'<div class="value"><div class="value__i">{ic}</div>'
        f'<h3>{html.escape(t)}</h3><p>{d}</p></div>' for ic, t, d in VALUES)
    step_html = "".join(
        f'<div class="step"><div class="step__n">{i+1}</div><div><h3>{t}</h3><p>{d}</p></div></div>'
        for i, (t, d) in enumerate(STEPS))

    page = (_PAGE
            .replace("__CATCARDS__", "".join(cat_cards))
            .replace("__FEATURED__", "".join(feat_cards))
            .replace("__HEROART__", hero_art)
            .replace("__VALUES__", value_html)
            .replace("__STEPS__", step_html)
            .replace("__TOTAL__", str(len(prods)))
            .replace("__NCAT__", str(len(cat_cards)))
            .replace("__ARTCSS__", ART_KEYFRAMES))
    (UI / "home.html").write_text(page, encoding="utf-8")
    print(f"wrote ui/home.html — {len(cat_cards)} categories, {len(feat_cards)} featured products")


_PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Printoka — Custom Printing Malaysia, Priced Instantly | Cards, Stickers, Banners &amp; More</title>
<meta name="description" content="Custom printing in Malaysia with instant, market-matched pricing and membership savings. Business cards, stickers, flyers, booklets, banners, packaging and more — configure, price and order online, with full specs, artwork guides and templates.">
<meta property="og:title" content="Printoka — Custom Printing, Priced Instantly">
<meta property="og:description" content="Instant agent pricing, full product specs, artwork guides and online ordering.">
<meta name="robots" content="index,follow">
<link rel="canonical" href="home.html">
<style>
  :root{--ink:#212529;--muted:#546e7a;--faint:#7d879c;--hair:#e6e9ee;--line:#eef1f4;--bg:#fff;
    --teal:#005b7f;--teal-d:#00485f;--yellow:#fdb913;--yellow-d:#e9a800;--chip:#eef4f7;--chipink:#2b5563;
    --shadow:0 1px 2px rgba(20,40,60,.05),0 1px 1px rgba(0,0,0,.03);}
  *{box-sizing:border-box} html,body{overflow-x:hidden}
  body{margin:0;background:var(--bg);color:var(--ink);line-height:1.55;font-size:14px;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,"Noto Sans",sans-serif}
  a{color:inherit;text-decoration:none}
  .wrap{max-width:1100px;margin:0 auto;padding:0 24px}
  .btn{display:inline-flex;align-items:center;gap:8px;border-radius:8px;padding:12px 22px;font-size:15px;font-weight:700;border:1px solid transparent;cursor:pointer}
  .btn--order{background:var(--yellow);color:#3a2c00}.btn--order:hover{background:var(--yellow-d)}
  .btn--price{background:var(--teal);color:#fff}.btn--price:hover{background:var(--teal-d)}
  .btn--ghost{background:#fff;color:var(--teal);border-color:#cfdbe2}.btn--ghost:hover{border-color:var(--teal)}
  /* nav */
  .nav{position:sticky;top:0;z-index:30;background:rgba(255,255,255,.92);backdrop-filter:blur(8px);
    border-top:3px solid var(--yellow);border-bottom:1px solid var(--hair)}
  .nav .wrap{display:flex;align-items:center;gap:16px;height:60px}
  .orb{height:28px;width:28px;border-radius:50%;background:conic-gradient(from 210deg,#00b3c4,#0d6385,#005b7f,#00485f,#fdb913,#00b3c4)}
  .brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:17px;letter-spacing:-.01em}
  .nav a.link{color:var(--muted);font-size:14px;font-weight:600}.nav a.link:hover{color:var(--teal)}
  .nav .links{display:flex;gap:20px;margin-left:8px}
  .nav .right{margin-left:auto;display:flex;gap:10px;align-items:center}
  @media(max-width:720px){.nav .links{display:none}}
  /* hero */
  .hero{padding:52px 0 46px;background:linear-gradient(180deg,#f5fbfd,#fff)}
  .hero .wrap{display:flex;gap:36px;align-items:center;flex-wrap:wrap}
  .hero__copy{flex:1 1 420px;min-width:0}
  .hero h1{font-size:clamp(30px,4.6vw,46px);line-height:1.08;letter-spacing:-.02em;margin:0 0 14px;font-weight:800}
  .hero h1 span{color:var(--teal)}
  .hero p.sub{font-size:clamp(15px,1.6vw,18px);color:var(--muted);max-width:56ch;margin:0 0 22px}
  .hero .cta{display:flex;gap:12px;flex-wrap:wrap}
  .hero .trust{margin-top:18px;color:var(--faint);font-size:12.5px}
  .hero__art{flex:1 1 360px;position:relative;height:300px;min-width:280px}
  .hero-art{position:absolute;width:56%;filter:drop-shadow(0 14px 26px rgba(10,51,69,.14))}
  .hf0{top:6%;left:2%;width:60%;z-index:2}.hf1{top:34%;right:0;width:52%;z-index:3}.hf2{bottom:0;left:16%;width:50%;z-index:1;opacity:.96}
  .herofloat .pa-float{animation:paFloat 5s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
  .hf1 .pa-float{animation-delay:.8s}.hf2 .pa-float{animation-delay:1.6s}
  .herofloat .pa-shine{animation:paShine 6s ease-in-out infinite}
  /* sections */
  section{padding:46px 0}
  .sec-h{text-align:center;max-width:60ch;margin:0 auto 30px}
  .sec-h h2{font-size:clamp(22px,3vw,30px);letter-spacing:-.02em;margin:0 0 8px;font-weight:800}
  .sec-h p{color:var(--muted);font-size:15px;margin:0}
  .eyebrow{color:var(--teal);font-weight:700;font-size:12.5px;letter-spacing:.06em;text-transform:uppercase;margin-bottom:6px}
  /* category grid */
  .cats{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}
  .catcard{border:1px solid var(--hair);border-radius:13px;overflow:hidden;background:#fff;transition:.18s}
  .catcard:hover{border-color:var(--teal);box-shadow:0 10px 24px rgba(10,51,69,.10);transform:translateY(-2px)}
  .catcard__art{aspect-ratio:16/10;background:#eef4f7}
  .catcard__b{display:flex;align-items:center;justify-content:space-between;padding:13px 15px}
  .catcard__n{font-weight:700;font-size:14.5px}.catcard__c{font-size:12px;color:var(--faint)}
  /* products */
  .alt{background:#f7fafc}
  .pcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px}
  .pcard{display:flex;flex-direction:column;background:#fff;border:1px solid var(--hair);border-radius:12px;overflow:hidden;transition:.18s}
  .pcard:hover{border-color:var(--teal);box-shadow:0 8px 20px rgba(10,51,69,.10);transform:translateY(-2px)}
  .pa-thumb{width:100%;aspect-ratio:4/3;background:#eef4f7;overflow:hidden}
  .pcard__foot{display:flex;align-items:center;gap:8px;padding:11px 13px}
  .pcard__n{font-size:13.5px;font-weight:600;flex:1;min-width:0}
  .pcard__b{font-size:10px;color:#1a7d3f;background:#e6f4ea;border-radius:5px;padding:2px 6px;font-weight:700;white-space:nowrap}
  .center{text-align:center;margin-top:26px}
  /* values */
  .values{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:18px}
  .value{border:1px solid var(--hair);border-radius:13px;padding:20px;background:#fff}
  .value__i{height:38px;width:38px;border-radius:10px;background:var(--chip);color:var(--teal);display:grid;place-items:center;font-size:18px;margin-bottom:12px}
  .value h3{margin:0 0 6px;font-size:15.5px}.value p{margin:0;color:var(--muted);font-size:13px;line-height:1.6}
  /* steps */
  .steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px}
  .step{display:flex;gap:14px}
  .step__n{height:34px;width:34px;border-radius:50%;background:var(--teal);color:#fff;display:grid;place-items:center;font-weight:800;flex:none}
  .step h3{margin:0 0 4px;font-size:15.5px}.step p{margin:0;color:var(--muted);font-size:13px;line-height:1.6}
  /* education band */
  .edu{background:linear-gradient(102deg,#0d6385,#005b7f);color:#fff;border-radius:18px;padding:34px}
  .edu .wrap2{display:flex;gap:24px;align-items:center;justify-content:space-between;flex-wrap:wrap}
  .edu h2{margin:0 0 6px;font-size:24px}.edu p{margin:0;opacity:.9;max-width:60ch}
  .edu .btn--order{white-space:nowrap}
  footer{border-top:1px solid var(--hair);color:var(--faint);font-size:12.5px;margin-top:10px}
  footer .wrap{display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;padding:26px 24px 48px}
  footer a{color:var(--teal)}
  @media(max-width:640px){.hero__art{flex-basis:100%;height:240px}}
__ARTCSS__
</style>
</head>
<body>
  <nav class="nav"><div class="wrap">
    <a class="brand" href="home.html"><span class="orb"></span>Printoka</a>
    <div class="links">
      <a class="link" href="products/index.html">Products</a>
      <a class="link" href="specs.html">Specifications</a>
      <a class="link" href="calculator_standalone.html">Pricing</a>
    </div>
    <div class="right">
      <a class="btn btn--order" href="calculator_standalone.html">Get a price</a>
    </div>
  </div></nav>

  <header class="hero"><div class="wrap">
    <div class="hero__copy">
      <div class="eyebrow">Custom printing · Malaysia</div>
      <h1>Custom printing, <span>priced instantly.</span></h1>
      <p class="sub">Configure any of __TOTAL__ products and see the exact, market-matched price in seconds —
        with membership-tier savings, full specifications, artwork guides and print-ready templates. Order online, end to end.</p>
      <div class="cta">
        <a class="btn btn--price" href="calculator_standalone.html">Configure &amp; price
          <svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.9"><path d="M6 4l4 4-4 4" stroke-linecap="round" stroke-linejoin="round"/></svg></a>
        <a class="btn btn--ghost" href="products/index.html">Browse products</a>
      </div>
      <div class="trust">Exact prices on 83+ products · full option parity · artwork specs &amp; templates for every product</div>
    </div>
    <div class="hero__art">__HEROART__</div>
  </div></header>

  <section><div class="wrap">
    <div class="sec-h"><div class="eyebrow">Shop by category</div>
      <h2>What can we print for you?</h2>
      <p>__TOTAL__ products across __NCAT__ categories — pick a category to explore options, prices and templates.</p></div>
    <div class="cats">__CATCARDS__</div>
  </div></section>

  <section class="alt"><div class="wrap">
    <div class="sec-h"><div class="eyebrow">Popular right now</div><h2>Best-selling products</h2>
      <p>Exact market-matched pricing, configured and ordered online.</p></div>
    <div class="pcards">__FEATURED__</div>
    <div class="center"><a class="btn btn--ghost" href="products/index.html">See all products →</a></div>
  </div></section>

  <section><div class="wrap">
    <div class="sec-h"><div class="eyebrow">Why Printoka</div><h2>Pricing you can trust, help at every step</h2></div>
    <div class="values">__VALUES__</div>
  </div></section>

  <section class="alt"><div class="wrap">
    <div class="sec-h"><div class="eyebrow">How it works</div><h2>From idea to delivered in three steps</h2></div>
    <div class="steps">__STEPS__</div>
  </div></section>

  <section><div class="wrap">
    <div class="edu"><div class="wrap2">
      <div><h2>New to print? We'll guide your artwork.</h2>
        <p>Every product has a full specification, an artwork spec (bleed, resolution, colour, file format)
           and a print-ready template — so your files are right the first time.</p></div>
      <a class="btn btn--order" href="specs.html">Explore specifications</a>
    </div></div>
  </div></section>

  <footer><div class="wrap">
    <span>© Printoka · custom printing, priced instantly · <a href="products/index.html">Products</a> · <a href="specs.html">Specs</a> · <a href="calculator_standalone.html">Pricing</a></span>
    <span>Made in Malaysia</span>
  </div></footer>
</body>
</html>
"""

if __name__ == "__main__":
    build()
