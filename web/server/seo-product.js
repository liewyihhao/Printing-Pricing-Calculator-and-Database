/*
 * Server-side Product SEO page (Part 1 of the redesign handoff).
 * Renders a fully static, indexable HTML document per product at /<slug>-printing —
 * all content is in the initial response (no client fetch, no hydration needed to read it).
 * Sizes / materials / finishing / options / from-price are derived from the SAME pricing
 * engine the configurator uses, so they never drift. The interactive configurator lives at
 * /<slug>-printing/configure/ (the SPA), which this page links to via "Check Price Now".
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');
// original printoka.com product + option photos (shared with the SPA)
const PKI = (function () { try { return require(path.join(__dirname, '..', 'product-images.js')); } catch (e) { return null; } })();
const origImg = f => f ? '/assets/original/' + f : null;
const optImg = (key, val, id) => PKI ? origImg(PKI.option(key, val, id)) : null;
// finishing type → original finishing photo
const FIN_IMG = [[/spot uv/i, 'matte-laminationspot-uv.jpg'], [/hot stamp/i, 'hot-stamping-gold.jpg'], [/round corner/i, 'round-corner.jpg'], [/emboss/i, 'emboss-finishing.jpg'],
  [/matte? lamin/i, 'matte-lamination.jpg'], [/gloss lamin/i, 'gloss-lamination.jpg'], [/water ?base|varnish/i, 'gloss-waterbased.jpg']];

// ---- design tokens (from the handoff, lifted from the live stylesheet) ----
const T = { brand: '#E52220', brandDark: '#c71917', amber: '#FF9A2E', ink: '#212121', inkDark: '#231f20', muted: '#616161', hairline: '#eaeaea', line: '#eef1f4', alt: '#FAFAFA', white: '#ffffff' };

// ---- engine + catalogue (loaded once) ----
let _E = null, _cat = null;
function engine() {
  if (_E) return _E;
  try { global.window = global.window || {}; require(path.join(__dirname, '..', 'pricing', 'engine.js')); _E = global.window.PricingEngine || null; } catch (e) { _E = null; }
  return _E;
}
function catalogue() {
  if (_cat) return _cat;
  try { const code = fs.readFileSync(path.join(__dirname, '..', 'catalogue.js'), 'utf8'); const sb = { window: {} }; vm.runInNewContext(code, sb); _cat = sb.window.PrintokaCatalogueDefaults || {}; } catch (e) { _cat = {}; }
  return _cat;
}
function slugify(s) { return String(s || '').toLowerCase().replace(/&/g, ' and ').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, ''); }
function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }

// ---- resolve a slug (e.g. "business-cards-printing") to a product record + display info ----
function resolve(slug) {
  const E = engine(); if (!E) return null;
  const bare = String(slug || '').replace(/-printing$/, '');
  const cat = catalogue(); const ov = (cat && cat.overrides) || {};
  const prods = (E.DATA && E.DATA.products) || [];
  for (const p of prods) {
    const o = ov[p.id] || ov[String(p.id)] || {};
    if (o.hidden) continue;
    const name = o.displayName || p.name;
    if (slugify(name) === bare) return { prod: p, name: name, displayName: name, override: o, catId: o.category || null };
  }
  return null;
}
function categoryLabel(catId) {
  const cat = catalogue();
  const c = (cat.categories || []).find(x => x.id === catId);
  return (c && (c.label || c.name)) || 'Products';
}

// ---- derive the option facts from the engine (never hand-authored) ----
const NONE_RE = /^(no|not required|no required|none|not applicable|no hot stamping|no hole punching|no round corner|no fold(ing)?|standard)$/i;
function optionsOf(prod, key, cfg) { const E = engine(); try { const o = E.localOptions(prod, key, cfg) || []; return o.map(v => Array.isArray(v) ? v[0] : v); } catch (e) { const f = (prod.fields || []).find(x => x.key === key); return (f && f.options) || []; } }
function baseCfg(prod) { const E = engine(); const cfg = {}; (prod.fields || []).forEach(f => { const o = optionsOf(prod, f.key, cfg); if (o.length) cfg[f.key] = o[0]; }); return cfg; }
function facts(r) {
  const E = engine(), prod = r.prod, cfg = baseCfg(prod);
  const fieldOpts = key => { const f = (prod.fields || []).find(x => x.key === key); return f ? optionsOf(prod, key, cfg).filter(v => !NONE_RE.test(String(v))) : []; };
  const findField = re => (prod.fields || []).find(f => re.test(f.key) && optionsOf(prod, f.key, cfg).length);
  const sizeF = findField(/size/i), matF = findField(/paper|material|stock/i);
  const sizes = sizeF ? optionsOf(prod, sizeF.key, cfg).filter(v => !/other|custom/i.test(v)) : [];
  const materials = matF ? optionsOf(prod, matF.key, cfg).filter(v => !NONE_RE.test(String(v))) : [];
  // Finishing = the finishing TYPES available, not every option value. Lamination variants
  // keep their type but drop the (Front)/(Both) side; Spot UV, Hot Stamping, Round Corner and
  // Embossing collapse to a single "is available" label (no colours, RC codes or sides).
  const finishing = []; const addFin = l => { if (l && finishing.indexOf(l) < 0) finishing.push(l); };
  (prod.fields || []).forEach(f => {
    const k = f.key; const opts = optionsOf(prod, f.key, cfg).filter(v => !NONE_RE.test(String(v)));
    if (!opts.length) return;
    if (/hot_stamping_colour|foil/i.test(k)) return;                 // colours: never listed
    if (/round_corner_position/i.test(k)) return;                    // RC die codes: never listed
    if (/lamination|varnish|coat/i.test(k)) opts.forEach(v => String(v).split('+').forEach(part => addFin(part.replace(/\s*\((?:both|front|back)\)\s*/ig, '').trim())));
    else if (/spot_uv|spotuv|silkscreen/i.test(k)) addFin('Spot UV');
    else if (/hot_stamping|stamp/i.test(k)) addFin('Hot Stamping');
    else if (/round_corner/i.test(k)) addFin('Round Corner');
    else if (/emboss/i.test(k)) addFin('Embossing');
  });
  // the "types to configure" = the product's top-level category/model field values
  const catField = (prod.fields || []).find(f => /^(category|model|type)$/i.test(f.key) && optionsOf(prod, f.key, cfg).length);
  const types = catField ? optionsOf(prod, catField.key, cfg) : [];
  const typeKey = catField ? catField.key : null;
  // full options table (label + values)
  const optLabel = r.override && r.override.optLabel || {};
  const labelOv = r.override && r.override.label || {};
  const options = (prod.fields || []).map(f => { const vals = optionsOf(prod, f.key, cfg); if (!vals.length) return null;
    return { key: f.key, label: labelOv[f.key] || f.label || f.key, values: vals.map(v => (optLabel[f.key] && optLabel[f.key][v]) || v) }; }).filter(Boolean);
  // quantity + from-price (sample the break points, lowest per-piece)
  const qopts = (prod.quantity && prod.quantity.options) || [100, 500, 1000];
  const moq = qopts[0] || null;
  let sample = qopts.slice(); if (sample.length > 6) { const pick = [0, (sample.length / 3) | 0, (2 * sample.length / 3) | 0, sample.length - 1]; sample = pick.map(i => sample[i]); }
  let from = null;
  sample.forEach(qn => { try { const q = E.localQuote(prod, cfg, qn); const cash = q && (q.printoka_cash != null ? q.printoka_cash : q.cash); if (cash != null && qn) { const pp = cash / qn; if (from == null || pp < from) from = pp; } } catch (e) {} });
  return { id: prod.id, sizeKey: sizeF ? sizeF.key : 'size', matKey: matF ? matF.key : 'paper', name: r.name, catId: r.catId, catLabel: categoryLabel(r.catId), sizes, materials, finishing, types, typeKey, options, moq, qopts, from };
}

// ---- CMS-style copy, generated (mirrors the client's productSeo / catWhy) ----
const WHY_BULLETS = {
  'business-essentials': ['Make a sharp first impression at every meeting', 'Put your contact details in every prospect’s hand', 'Look established from the first hello'],
  'flyers-leaflets': ['Put your promotion straight into people’s hands', 'Drive walk-ins with an offer they can hold', 'Reach a whole neighbourhood on a small budget'],
  'labels-stickers': ['Brand every product you sell', 'Seal your packaging with your own mark', 'Turn plain boxes into shelf appeal'],
  'books-stationery': ['Keep your brand on a desk all year', 'Give clients something they use every day', 'Collect your story in one book'],
  'cards-invitations': ['Set the tone for the big day', 'Give guests something worth keeping', 'Add foil and texture people want to touch'],
  'large-format': ['Get seen from across the street', 'Own your storefront and events', 'Stand tall at every roadshow'],
  'packaging-boxes': ['Protect your product in transit', 'Turn unboxing into your best advert', 'Own the shelf with custom print'],
  'apparel-gifts': ['Put your brand on your team', 'Turn events into walking billboards', 'Give gifts people actually use'],
};
function money(n) { return 'RM ' + (Math.round(n * 100) / 100).toFixed(2); }
function copy(f, name) {
  const why = WHY_BULLETS[f.catId] || ['Get an exact price before you order', 'Choose from 100+ products in one place', 'Print with a free artwork check'];
  const axes = f.options.map(o => o.label.toLowerCase()).filter(l => !/category|model|type/.test(l)).slice(0, 4).join(', ');
  const intro = 'Order ' + name + ' online and see the exact price as you configure it. Set ' + (axes || 'your specification') + ', then order across Malaysia, Singapore and Brunei. You pay exactly what the configurator shows, at checkout and on your invoice.';
  const sizesCopy = f.sizes.length ? ('Choose from sizes like ' + f.sizes.slice(0, 5).join(', ') + '. You can also enter a custom size where supported.') : 'Choose your size in the configurator, or enter a custom size where supported.';
  const moqCopy = 'Minimum order is ' + (f.moq ? f.moq.toLocaleString() : '') + ' pcs' + (f.from != null ? ', from ' + money(f.from) + ' per piece' : '') + '. Larger runs bring the price per piece down, and members save 5% to 15% automatically at checkout.';
  const turnaround = 'Upload your artwork and our prepress team checks trim, bleed, resolution and colour before printing. Turnaround is 3 working days after approval, with nationwide delivery or free pickup in the Klang Valley.';
  const faq = [];
  if (f.sizes.length) faq.push(['What sizes are available for ' + name + '?', 'Available sizes include ' + f.sizes.slice(0, 6).join(', ') + '. You can also enter a custom size where supported.']);
  if (f.materials.length || f.finishing.length) faq.push(['What materials and finishes can I choose?', (f.materials.length ? 'Materials include ' + f.materials.slice(0, 5).join(', ') + '. ' : '') + (f.finishing.length ? 'Finishes include ' + f.finishing.slice(0, 4).map(x => x.toLowerCase()).join(', ') + '.' : '')]);
  if (f.moq) faq.push(['What is the minimum order for ' + name + '?', 'The minimum order is ' + f.moq.toLocaleString() + ' pcs. Larger runs lower the price per piece.']);
  faq.push(['How long does ' + name + ' printing take?', 'Standard turnaround is 3 working days after your artwork is approved by prepress.']);
  faq.push(['Can I get ' + name + ' delivered or pick it up?', 'Both. Choose nationwide courier delivery, or free self-pickup at a Klang Valley outlet.']);
  return { why, intro, sizesCopy, moqCopy, turnaround, faq };
}

// ---- to-scale size rectangles + material weight bars (computed from parsed values) ----
function parseSize(s) { const m = String(s).match(/(\d+(?:\.\d+)?)\s*mm\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm/i); return m ? { w: +m[1], h: +m[2] } : null; }
function parseWeight(s) { let m = String(s).match(/(\d+(?:\.\d+)?)\s*gsm/i); if (m) return { unit: 'gsm', v: +m[1] }; m = String(s).match(/(\d+(?:\.\d+)?)\s*micron/i); if (m) return { unit: 'mm', v: +m[1] / 1000 }; m = String(s).match(/(\d+(?:\.\d+)?)\s*mm/i); if (m) return { unit: 'mm', v: +m[1] }; return null; }
function weightBucket(w, group) { const vals = group.filter(g => g.unit === w.unit).map(g => g.v); const min = Math.min.apply(null, vals), max = Math.max.apply(null, vals); if (vals.length < 2 || min === max) return null; const t = (w.v - min) / (max - min); return t < 0.34 ? { bars: 1, label: 'Lightest' } : t < 0.67 ? { bars: 2, label: 'Mid weight' } : { bars: 3, label: 'Heaviest' }; }

const MY_STATES = ['Johor', 'Kedah', 'Kelantan', 'Melaka', 'Negeri Sembilan', 'Pahang', 'Penang', 'Perak', 'Perlis', 'Sabah', 'Sarawak', 'Selangor', 'Terengganu', 'Kuala Lumpur', 'Labuan', 'Putrajaya'];
const TRUST = [['Instant online pricing', 'See the exact price before you order'], ['Free artwork check', 'Prepress reviews every file'], ['30+ partner vendors', 'Plus our own facility in Miri'], ['Member discounts', 'Save 5% to 15% every order'], ['Nationwide delivery', 'Or free Klang Valley pickup'], ['Since 2018', 'Trusted by businesses across MY']];

// ---- render ----
function page(slug, origin, opts) {
  const r = resolve(slug); if (!r) return null;
  const f = facts(r), name = f.name, c = copy(f, name);
  const productUrl = origin + '/' + slug;
  const configUrl = '/' + slug + '/configure/';
  const h1 = 'Print ' + name + ' Online in Malaysia';
  const title = (h1 + ' | Printoka').slice(0, 60);
  const desc = c.intro.slice(0, 155);
  const catUrl = f.catId ? origin + '/products/' + f.catId : origin + '/products';
  const asset = (PKI && PKI.products[f.id] && origImg(PKI.products[f.id])) || (function () { try { const p = path.join(__dirname, '..', 'assets', 'products', slugify(name) + '.jpg'); return fs.existsSync(p) ? '/assets/products/' + slugify(name) + '.jpg' : null; } catch (e) { return null; } })();
  const ogImg = origin + (asset || '/assets/social/og-default.png');

  // JSON-LD
  const jsonld = [
    { '@context': 'https://schema.org', '@type': 'Product', name: name + ' Printing', description: desc, brand: { '@type': 'Brand', name: 'Printoka' }, category: f.catLabel,
      image: ogImg, offers: Object.assign({ '@type': 'AggregateOffer', priceCurrency: 'MYR', availability: 'https://schema.org/InStock', offerCount: (f.qopts || []).length || 1, url: productUrl }, f.from != null ? { lowPrice: f.from.toFixed(2) } : {}) },
    { '@context': 'https://schema.org', '@type': 'FAQPage', mainEntity: c.faq.map(q => ({ '@type': 'Question', name: q[0], acceptedAnswer: { '@type': 'Answer', text: q[1] } })) },
    { '@context': 'https://schema.org', '@type': 'BreadcrumbList', itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: origin + '/' },
      { '@type': 'ListItem', position: 2, name: f.catLabel, item: catUrl },
      { '@type': 'ListItem', position: 3, name: name, item: productUrl } ] },
  ];

  // sections
  const S = [];
  const sec = (id, inner) => '<section id="' + id + '" class="pk-sec">' + inner + '</section>';
  // hero — orange banner replicating the printoka.com product header: product cutout (left),
  // "Print Your {name} Online Now!" (centre), three benefit blocks (right).
  const heroBenefits = [
    ['Schedule your delivery', 'Door-to-door, nationwide'],
    ['Satisfaction guaranteed', 'Quality you can rely on'],
    ['Exclusive member pricing', 'Save 5–15% as a member'],
  ];
  // a branded illustration so the hero is never lopsided when a product has no cutout photo yet
  const heroFallback = '<div class="pk-hero-img pk-hero-fallback" aria-hidden="true"><svg viewBox="0 0 220 180" width="220" height="180" fill="none">'
    + '<rect x="18" y="46" width="150" height="104" rx="9" fill="rgba(255,255,255,.16)"/>'
    + '<rect x="34" y="30" width="150" height="104" rx="9" fill="rgba(255,255,255,.30)"/>'
    + '<rect x="50" y="14" width="150" height="104" rx="9" fill="#fff"/>'
    + '<circle cx="74" cy="42" r="9" fill="#E52220"/>'
    + '<rect x="90" y="37" width="82" height="7" rx="3.5" fill="#e2e2e2"/><rect x="90" y="50" width="58" height="6" rx="3" fill="#ededed"/>'
    + '<rect x="66" y="74" width="118" height="6" rx="3" fill="#f0f0f0"/><rect x="66" y="88" width="96" height="6" rx="3" fill="#f0f0f0"/><rect x="66" y="102" width="70" height="6" rx="3" fill="#f0f0f0"/>'
    + '</svg></div>';
  S.push('<section id="top" class="pk-hero"><div class="pk-hero-in">'
    + (asset ? '<div class="pk-hero-img"><img src="' + esc(asset) + '" alt="' + esc(name + ' printed by Printoka') + '" width="300" height="220" fetchpriority="high"></div>' : heroFallback)
    + '<div class="pk-hero-c"><h1><span class="pk-h-sm">Print Your</span><span class="pk-h-lg">' + esc(name) + '</span><span class="pk-h-md">Online Now!</span></h1>'
    + '<p class="pk-hero-tag">configure, upload and print</p></div>'
    + '<div class="pk-hero-benefits">' + heroBenefits.map(b => '<div class="pk-hb"><div class="pk-hb-h">' + esc(b[0]) + '</div><div class="pk-hb-c">' + esc(b[1]) + '</div></div>').join('') + '</div>'
    + '</div></section>');
  // Choose the type to configure (before "Why Printoka?"). More than 5 types => a horizontal
  // carousel (scroll left/right) instead of a wrapping grid.
  if (f.types.length) {
    const cards = f.types.map(t => '<a class="pk-type" href="' + esc(configUrl + '?' + f.typeKey + '=' + encodeURIComponent(t)) + '">' + (optImg(f.typeKey, t, f.id) ? '<div class="pk-type-ph pk-type-photo"><img src="' + esc(optImg(f.typeKey, t, f.id)) + '" alt="' + esc(t + ' ' + name) + '" loading="lazy"></div>' : '<div class="pk-type-ph" aria-hidden="true"><img src="/assets/icons/cropped-favicon-192x192.png" alt=""></div>') + '<div class="pk-type-l">' + esc(t) + '</div><span class="pk-btn pk-btn-sm">Check Price</span></a>').join('');
    const body = f.types.length > 5
      ? '<div class="pk-carousel"><button type="button" class="pk-car-btn pk-car-prev" aria-label="Scroll left">‹</button><div class="pk-car-track">' + cards + '</div><button type="button" class="pk-car-btn pk-car-next" aria-label="Scroll right">›</button></div>'
      : '<div class="pk-grid pk-types">' + cards + '</div>';
    S.push(sec('types', '<h2>Choose the type of ' + esc(name) + ' to configure</h2>' + body));
  } else {
    // a product with no type choice still shows its one item as a card (same layout as the multi-type grid)
    const one = '<a class="pk-type" href="' + esc(configUrl) + '">' + (asset ? '<div class="pk-type-ph pk-type-photo"><img src="' + esc(asset) + '" alt="' + esc(name) + '" loading="lazy"></div>' : '<div class="pk-type-ph" aria-hidden="true"><img src="/assets/icons/cropped-favicon-192x192.png" alt=""></div>') + '<div class="pk-type-l">' + esc(name) + '</div><span class="pk-btn pk-btn-sm">Check Price</span></a>';
    S.push(sec('types', '<h2>Choose the type of ' + esc(name) + ' to configure</h2><div class="pk-grid pk-types pk-types-one">' + one + '</div>'));
  }
  // Why Printoka? — light band with six icon benefits
  const ICON = {
    thumb: '<path d="M7 11v9M2 13a2 2 0 0 1 2-2h3v9H4a2 2 0 0 1-2-2v-5zM7 11l4-8a2 2 0 0 1 2 2v4h5a2 2 0 0 1 2 2.3l-1.2 6A2 2 0 0 1 17 20H7"/>',
    clock: '<path d="M6 2h12M6 22h12M8 2c0 4 8 6 8 10s-8 6-8 10M16 2c0 4-8 6-8 10"/>',
    truck: '<path d="M1 6h13v11H1zM14 9h4l3 3v5h-7zM6 20a2 2 0 1 0 0-.1M18 20a2 2 0 1 0 0-.1"/>',
    shield: '<path d="M12 2l8 3v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V5zM9 12l2 2 4-4"/>',
    card: '<path d="M2 5h20v14H2zM2 10h20"/>',
    shop: '<path d="M3 9l1-5h16l1 5M3 9h18v11H3zM3 9a3 3 0 0 0 6 0 3 3 0 0 0 6 0 3 3 0 0 0 6 0"/>',
  };
  const svg = p => '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="' + T.brand + '" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + p + '</svg>';
  const WHY6 = [
    [svg(ICON.thumb), 'Superior Quality', ''],
    [svg(ICON.clock), 'Instant Price Quotation', ''],
    [svg(ICON.truck), 'Configurable Delivery Options', ''],
    [svg(ICON.shield), 'Professional Print Experts at your service', ''],
    [svg(ICON.card), 'Credit Terms for Corporate Members', 'Subject to application'],
    [svg(ICON.shop), 'Membership Plans', ''],
  ];
  S.push('<section id="why" class="pk-why"><div class="pk-why-in"><h2>Why Printoka?</h2>'
    + '<p class="pk-why-sub">The exclusive benefits you get as a member of Printoka.com.</p>'
    + '<div class="pk-why-grid">' + WHY6.map(w => '<div class="pk-why-i"><span class="pk-why-icon">' + w[0] + '</span><div class="pk-why-l">' + esc(w[1]) + '</div>' + (w[2] ? '<div class="pk-why-note">' + esc(w[2]) + '</div>' : '') + '</div>').join('') + '</div>'
    + '</div></section>');
  // sizes (to scale)
  if (f.sizes.length) {
    const parsed = f.sizes.map(s => ({ s, d: parseSize(s) }));
    const maxDim = Math.max.apply(null, parsed.filter(p => p.d).map(p => Math.max(p.d.w, p.d.h)).concat([1]));
    const scale = 120 / maxDim;
    S.push(sec('sizes', '<h2>Our supported ' + esc(name) + ' sizes</h2>' + (parsed.some(p => optImg(f.sizeKey, p.s, f.id)) ? '' : '<p class="pk-scale-note">Shown to scale.</p>') + '<div class="pk-grid pk-sizes">'
      + parsed.map(p => '<div class="pk-size"><div class="pk-size-box">' + (optImg(f.sizeKey, p.s, f.id) ? '<img src="' + esc(optImg(f.sizeKey, p.s, f.id)) + '" alt="' + esc(p.s + ' ' + name) + '" loading="lazy">' : p.d ? '<span style="width:' + (p.d.w * scale).toFixed(1) + 'px;height:' + (p.d.h * scale).toFixed(1) + 'px"></span>' : '<span class="pk-size-na"></span>') + '</div><div class="pk-size-l">' + esc(p.s) + '</div></div>').join('')
      + '</div><a class="pk-btn" href="' + esc(configUrl) + '">Configure your ' + esc(name) + '</a>'));
  }
  // materials (weight bars)
  if (f.materials.length) {
    const parsedW = f.materials.map(m => ({ m, w: parseWeight(m) }));
    const group = parsedW.filter(x => x.w).map(x => x.w);
    S.push(sec('materials', '<h2>Our supported ' + esc(name) + ' printing materials</h2><div class="pk-grid pk-mats">'
      + parsedW.map(x => { const b = x.w ? weightBucket(x.w, group) : null; const mi = optImg(f.matKey, x.m, f.id); return '<div class="pk-mat' + (mi ? ' pk-has-img' : '') + '">' + (mi ? '<img class="pk-tile-img" src="' + esc(mi) + '" alt="' + esc(x.m) + '" loading="lazy">' : '') + '<div class="pk-mat-l">' + esc(x.m) + '</div>'
        + (b ? '<div class="pk-bars">' + [1, 2, 3].map(i => '<span class="' + (i <= b.bars ? 'on' : '') + '"></span>').join('') + '</div><div class="pk-mat-c">' + b.label + '</div>' : '<div class="pk-mat-c pk-mat-c-neutral">Stock option</div>') + '</div>'; }).join('') + '</div>'));
  }
  // finishing
  if (f.finishing.length) {
    S.push(sec('finishing', '<h2>Finishing for your ' + esc(name) + '</h2><div class="pk-grid pk-fins">'
      + f.finishing.map(x => { const fi = (FIN_IMG.find(r => r[0].test(x)) || [])[1]; return fi ? '<div class="pk-fin pk-has-img"><img class="pk-tile-img" src="' + origImg(fi) + '" alt="' + esc(x + ' finishing') + '" loading="lazy"><div>' + esc(x) + '</div></div>' : '<div class="pk-fin">' + esc(x) + '</div>'; }).join('') + '</div>'));
  }
  // delivery — a full-width attention-catching banner (reassurance + states + CTA)
  S.push('<section id="delivery" class="pk-deliver"><div class="pk-deliver-in">'
    + '<h2>We Deliver Your ' + esc(name) + ' Anywhere in Malaysia</h2>'
    + '<p class="pk-deliver-sub">Fast, tracked, door-to-door delivery to every state, or free Klang Valley pickup.</p>'
    + '<ul class="pk-states">' + MY_STATES.map(s => '<li>' + esc(s) + '</li>').join('') + '</ul>'
    + '<a class="pk-btn pk-btn-lg" href="' + esc(configUrl) + '">Configure your ' + esc(name) + '</a>'
    + '</div></section>');
  // FAQ — native <details> accordion styled like the printoka.com FAQ (no JS needed)
  S.push('<section class="pk-wa"><div class="pk-wa-txt"><div class="pk-wa-h">Can’t find what you need?</div><div class="pk-wa-s">Chat with us using Whatsapp</div>'
    + '<a class="pk-wa-tel" href="tel:+60149690799"><span aria-hidden="true"><img src="/assets/icons/phone.svg" alt="" height="16"></span>+60 14 969 0799</a></div>'
    + '<div class="pk-wa-img" role="img" aria-label="Printoka customer service"></div></section>');
  S.push('<section id="faq" class="pk-faq-sec"><h2>' + esc(name) + ' printing FAQ</h2><div class="pk-faq">'
    + c.faq.map((q, i) => '<details class="pk-faq-item"' + (i === 0 ? ' open' : '') + '><summary>' + esc(q[0]) + '<span class="pk-faq-ch" aria-hidden="true">▾</span></summary><div class="pk-faq-a">' + esc(q[1]) + '</div></details>').join('')
    + '</div><a class="pk-btn" href="/contact">Ask a question</a></section>');

  // header — a faithful static replica of the app's runtime.js chrome (logo, red Products
  // button, search, locale, login, cart, country), so the SEO page matches the storefront.
  const navCats = ['business-essentials', 'flyers-leaflets', 'labels-stickers', 'books-stationery', 'cards-invitations', 'large-format', 'packaging-boxes', 'apparel-gifts'];
  const header = '<div class="pk-headwrap"><header class="pk-head"><div class="pk-head-in">'
    + '<a class="pk-logo" href="/" aria-label="Printoka home"><img src="/assets/icons/logo.png" alt="Printoka" width="125" height="38"></a>'
    + '<a class="pk-products" href="/products">Products <img src="/assets/icons/dropdown.svg" alt="" height="7"></a>'
    + '<form class="pk-search" action="/search" method="get" role="search"><input name="q" placeholder="Search products" aria-label="Search products"><button type="submit" aria-label="Search"><img src="/assets/icons/search.svg" alt="" height="13"></button></form>'
    + '<div class="pk-head-r"><span class="pk-loc">EN</span><span class="pk-div"></span>'
    + '<a class="pk-login" href="/auth"><img src="/assets/icons/user.svg" alt="" height="18">Login/ Signup</a>'
    + '<a class="pk-cart" href="/cart" aria-label="Cart"><img src="/assets/icons/cart.svg" alt="" height="19"></a>'
    + '<span class="pk-country"><img src="/assets/icons/flag-my.jpg" alt="Malaysia" width="22" height="15">MY</span></div>'
    + '</div></header></div>';
  // footer — identical to the original printoka.com footer (links, company details); same as runtime.js
  const flink = (l) => '<a href="' + esc(l[1]) + '">' + esc(l[0]) + '</a>';
  const fcol = (title, items) => '<div class="pk-fcol"><div class="pk-fcol-h">' + esc(title) + '</div>' + items.map(flink).join('') + '</div>';
  const ext = ' target="_blank" rel="noopener noreferrer"';
  const footer = '<footer class="pk-foot"><div class="pk-foot-in">'
    + fcol('Printoka', [['About Us', '/about-us'], ['Customized Printing Solutions', '/customized-printing-solutions'], ['Become Our Printers', '/partners'], ['Printoka Membership Plans', '/membership'], ['Terms & Conditions', '/terms']])
    + fcol('Support', [['General FAQs', '/support'], ['Blog', '/learn'], ['Guides for Closing Artwork', '/support#guides-for-closing-artwork'], ['Templates Download', '/downloads']])
    + '<div class="pk-fcol"><div class="pk-fcol-h">Country</div><div class="pk-flags">'
    + [['flag-my.jpg', 'Malaysia', '/'], ['flag-sg.jpg', 'Singapore', 'https://printokasingapore.com/'], ['flag-bn.jpg', 'Brunei', 'https://printokabrunei.com/'], ['flag-au.jpg', 'Australia', '/au/'], ['flag-nz.jpg', 'New Zealand', '/nz/']].map(c => '<a href="' + c[2] + '"' + (/^https?:/.test(c[2]) ? ext : '') + ' title="' + c[1] + '"><img src="/assets/icons/' + c[0] + '" alt="' + c[1] + '" width="34" height="22"></a>').join('')
    + '</div><div class="pk-fcol-h">Follow us</div><div class="pk-social">'
    + [['facebook.svg', 'Facebook', 'https://www.facebook.com/Printoka-Malaysia-414898672398006/', '#3b5998'], ['instagram-line.svg', 'Instagram', 'https://www.instagram.com/printoka_group', '#e1306c'], ['linkedin-fill.svg', 'LinkedIn', 'https://www.linkedin.com/company/51652879/', '#0e76a8']].map(x => '<a href="' + x[2] + '"' + ext + ' aria-label="' + x[1] + '" style="background:' + x[3] + '"><img src="/assets/icons/' + x[0] + '" alt="" width="20" height="20"></a>').join('')
    + '</div></div>'
    + '<div class="pk-fcol"><img class="pk-flogo" src="/assets/icons/logo.png" alt="Printoka" width="158" height="48">'
    + '<div class="pk-fneed">Can’t find what you need?</div><div class="pk-fneed-s">Chat with us using Whatsapp</div>'
    + '<a class="pk-fcontact" href="https://wa.me/60149690799"' + ext + '><img src="/assets/icons/whatsapp.svg" alt="" width="16" height="16">Contact us</a></div>'
    + '</div><div class="pk-foot-in2">'
    + fcol('What we Do', [['Online Printing Malaysia', '/online-printing-malaysia'], ['Stickers Printing Malaysia', '/digital-stickers-and-labels-printing'], ['Business Card Printing Malaysia', '/business-cards-printing'], ['Packaging Printing Malaysia', '/packaging-printing-in-malaysia'], ['Brochure and Flyer Printing Malaysia', '/brochure-and-flyer-printing-malaysia']])
    + '<img class="pk-fart" src="/assets/icons/footer-1.png" alt="" loading="lazy" width="580" height="300"></div>'
    + '<div class="pk-foot-bar">All rights reserved &copy; 2013-2022 Printoka.com | This website is managed and operated by Yushan Corporation Sdn Bhd (561674-X) |<br>Registered address: Lot 1565, Piasau Industrial Estate, 98000 Miri, Sarawak, Malaysia</div></footer>';

  const html = '<!doctype html><html lang="en-MY"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    + '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    + '<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&display=swap" rel="stylesheet">'
    + '<meta name="theme-color" content="#E52220">'
    + '<title>' + esc(title) + '</title>'
    + '<meta name="description" content="' + esc(desc) + '">'
    + '<meta name="robots" content="index,follow">'
    + '<link rel="canonical" href="' + esc(productUrl) + '">'
    + ['en-MY', 'x-default'].map(l => '<link rel="alternate" hreflang="' + l + '" href="' + esc(productUrl) + '">').join('')
    + '<meta property="og:type" content="product"><meta property="og:site_name" content="Printoka">'
    + '<meta property="og:title" content="' + esc(title) + '"><meta property="og:description" content="' + esc(desc) + '">'
    + '<meta property="og:url" content="' + esc(productUrl) + '"><meta property="og:image" content="' + esc(ogImg) + '">'
    + '<meta name="twitter:card" content="summary_large_image">'
    + '<link rel="icon" href="/assets/icons/cropped-favicon-32x32.png" sizes="32x32"><link rel="icon" href="/assets/icons/cropped-favicon-192x192.png" sizes="192x192"><link rel="apple-touch-icon" href="/assets/icons/cropped-favicon-180x180.png">'
    + (asset ? '<link rel="preload" as="image" href="' + esc(asset) + '">' : '')
    + jsonld.map(j => '<script type="application/ld+json">' + JSON.stringify(j) + '</script>').join('')
    + '<style>' + css() + '</style></head><body>'
    + header + '<main class="pk-main">' + S.join('') + '</main>' + footer
    + '<script>document.querySelectorAll(".pk-carousel").forEach(function(c){var t=c.querySelector(".pk-car-track");var p=c.querySelector(".pk-car-prev"),n=c.querySelector(".pk-car-next");function s(d){t.scrollBy({left:d*Math.max(240,t.clientWidth*0.8),behavior:"auto"})}if(p)p.onclick=function(){s(-1)};if(n)n.onclick=function(){s(1)}});</script>'
    + '</body></html>';
  return html;
}

function css() {
  return [
    '.pk-foot{margin-top:56px;border-top:16px solid ' + T.brand + ';background:#fff}.pk-foot-in{max-width:1240px;margin:0 auto;padding:44px 20px 0;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:28px 40px;align-items:start}.pk-foot-in2{max-width:1240px;margin:0 auto;padding:24px 20px 0;display:flex;gap:30px;flex-wrap:wrap;align-items:flex-end}.pk-foot-in2 .pk-fcol{flex:0 1 300px;padding-bottom:30px}.pk-fart{flex:1 1 480px;max-width:580px;width:100%;height:auto;margin:0 auto;display:block}',
    '.pk-fcol-h{font-size:11px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:#4a4a4a;margin:0 0 14px}.pk-fcol a{display:block;font-size:15px;color:' + T.ink + ';text-decoration:none;padding:6px 0}.pk-flags{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:26px}.pk-flags a{padding:0}.pk-flags img{display:block;width:34px;height:22px;object-fit:cover}',
    '.pk-social{display:flex;gap:12px}.pk-social a{height:42px;width:42px;border-radius:50%;display:grid;place-items:center;padding:0}.pk-social img{filter:brightness(0) invert(1)}.pk-flogo{height:48px;width:auto;display:block;margin-bottom:30px}.pk-fneed{font-size:19px;font-weight:500;margin-bottom:8px}.pk-fneed-s{font-size:14px;color:' + T.muted + ';margin-bottom:18px}',
    '.pk-fcontact{display:inline-flex!important;align-items:center;gap:8px;background:' + T.brand + ';color:#fff!important;font-size:15px;font-weight:500;padding:11px 26px!important;border-radius:3px}.pk-fcontact img{filter:brightness(0) invert(1)}.pk-foot-bar{background:#f7f7f7;padding:16px 20px;text-align:center;font-size:13.5px;color:#555;line-height:1.7}',
    '.pk-wa{max-width:1180px;margin:40px auto 44px;display:flex;flex-wrap:wrap;background:#f7f7f7;border-radius:4px;overflow:hidden}.pk-wa-txt{flex:1 1 380px;padding:40px 44px;display:flex;flex-direction:column;justify-content:center;gap:10px}.pk-wa-h{font-size:28px;font-weight:500;letter-spacing:-.01em}.pk-wa-s{font-size:15px;color:' + T.muted + '}',
    '.pk-wa-tel{display:inline-flex;align-items:center;gap:14px;margin-top:14px;color:' + T.brand + ';font-size:30px;text-decoration:none}.pk-wa-tel span{height:38px;width:38px;border-radius:50%;background:' + T.brand + ';display:grid;place-items:center}.pk-wa-tel img{filter:brightness(0) invert(1)}.pk-wa-img{flex:0 1 440px;min-height:260px;background:url(/assets/icons/question.jpg) center/cover no-repeat;clip-path:polygon(18% 0,100% 0,100% 100%,0 100%)}@media(max-width:760px){.pk-wa-img,.pk-fart{display:none}.pk-wa-txt{padding:28px 22px}.pk-wa-tel{font-size:22px}}',
    '*{box-sizing:border-box}body{margin:0;font-family:Montserrat,system-ui,sans-serif;-webkit-font-smoothing:antialiased;color:' + T.ink + ';background:' + T.white + ';line-height:1.6}',
    'a{color:' + T.brand + ';text-decoration:none}a:hover{color:' + T.brandDark + '}img{max-width:100%;height:auto}',
    ':where(a,button):focus-visible{outline:2px solid ' + T.brand + ';outline-offset:2px}',
    '.pk-main{max-width:1180px;margin:0 auto;padding:0 20px}',
    '.pk-sec{scroll-margin-top:76px;padding:46px 0;border-top:1px solid ' + T.line + '}',
    '.pk-sec h2{font-size:20px;font-weight:600;letter-spacing:-.01em;margin:0 0 16px;text-align:center}.pk-sec h3{font-size:16px;font-weight:600;margin:22px 0 8px}',
    '.pk-sec p{font-size:14px;color:' + T.muted + ';line-height:1.8;max-width:80ch;margin-left:auto;margin-right:auto;text-align:center}',
    // header (matches runtime.js chrome)
    '.pk-headwrap{position:sticky;top:0;z-index:60}.pk-head{background:rgba(255,255,255,.96);backdrop-filter:blur(8px);border-bottom:1px solid ' + T.hairline + '}',
    '.pk-head-in{max-width:1180px;margin:0 auto;padding:10px 20px;min-height:64px;display:flex;align-items:center;flex-wrap:wrap;gap:10px 18px}',
    '.pk-logo{display:flex;align-items:center;white-space:nowrap}.pk-logo img{display:block;flex:none;height:38px;width:auto}',
    '.pk-products{display:flex;align-items:center;gap:6px;background:' + T.brand + ';color:#fff;font-weight:600;font-size:13.5px;border-radius:3px;padding:9px 15px;white-space:nowrap}.pk-products:hover{color:#fff}.pk-products img{height:7px;width:auto;filter:brightness(0) invert(1)}',
    '.pk-search{display:flex;align-items:center;flex:1 1 260px;min-width:120px;border:1px solid ' + T.hairline + ';border-radius:3px;overflow:hidden}.pk-search input{flex:1;border:0;padding:0 12px;font:400 13px Montserrat,sans-serif;color:' + T.ink + ';min-width:0;outline:none}.pk-search button{border:0;background:' + T.brand + ';padding:11px 15px;display:flex;cursor:pointer}.pk-search button img{height:13px;width:auto;filter:brightness(0) invert(1)}',
    '.pk-head-r{display:flex;align-items:center;gap:14px;font-size:13px;color:' + T.inkDark + ';white-space:nowrap}.pk-head-r a{color:' + T.inkDark + '}.pk-loc{cursor:default}.pk-div{width:1px;height:16px;background:' + T.hairline + '}',
    '.pk-login{display:flex;align-items:center;gap:7px;font-size:13.5px}.pk-login img{height:18px;width:auto}.pk-cart{display:flex}.pk-cart img{height:19px;width:auto}.pk-country{display:flex;align-items:center;gap:6px}.pk-country img{height:15px;width:22px;object-fit:cover;display:block}',
    // hero (orange banner, printoka.com product-header layout)
    '.pk-hero{background:linear-gradient(115deg,#F26722 0%,#EF5A28 45%,#E52220 100%);color:#fff;overflow:hidden}',
    '.pk-hero-in{max-width:1180px;margin:0 auto;padding:34px 20px;display:flex;flex-wrap:wrap;gap:28px;align-items:center;min-height:216px}',
    '.pk-hero-img{flex:0 0 auto}.pk-hero-img img{height:190px;width:auto;filter:drop-shadow(0 18px 30px rgba(0,0,0,.28))}.pk-hero-fallback{display:flex;align-items:center;justify-content:center}.pk-hero-fallback svg{filter:drop-shadow(0 16px 28px rgba(0,0,0,.22))}',
    '.pk-hero-c{flex:1 1 300px}.pk-hero h1{margin:0;display:flex;flex-direction:column;line-height:1.08;font-weight:400}',
    '.pk-h-sm{font-size:26px}.pk-h-lg{font-size:40px;font-weight:700;letter-spacing:-.01em}.pk-h-md{font-size:30px;font-weight:500}',
    '.pk-hero-tag{margin:12px 0 0;font-size:20px;font-weight:300;color:rgba(255,255,255,.95)}',
    '.pk-hero-benefits{flex:0 1 320px;display:flex;flex-direction:column;gap:14px}',
    '.pk-hb-h{font-weight:700;font-size:15px}.pk-hb-c{font-size:13px;color:rgba(255,255,255,.92);padding-left:14px;position:relative;margin-top:2px;line-height:1.5}.pk-hb-c:before{content:"";position:absolute;left:0;top:8px;width:5px;height:5px;border-radius:50%;background:#fff}',
    // buttons
    '.pk-btn{display:inline-block;background:' + T.brand + ';color:#fff;font-weight:600;font-size:14px;padding:11px 20px;border-radius:8px}.pk-btn:hover{background:' + T.brandDark + ';color:#fff}.pk-btn-lg{padding:13px 26px;font-size:14px}.pk-btn-sm{padding:9px 14px;font-size:12.5px;margin-top:auto}',
    // why printoka (light band, six icon benefits)
    '.pk-why{background:' + T.alt + '}.pk-why-in{max-width:1180px;margin:0 auto;padding:44px 20px;text-align:center}.pk-why h2{font-size:22px;font-weight:600;letter-spacing:-.01em;margin:0 0 8px}.pk-why-sub{font-size:14px;color:' + T.muted + ';margin:0 auto 30px;max-width:64ch}',
    '.pk-why-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:22px}.pk-why-i{display:flex;flex-direction:column;align-items:center;gap:10px}',
    '.pk-why-icon{width:56px;height:56px;border-radius:50%;border:1.5px solid ' + T.brand + ';display:flex;align-items:center;justify-content:center;background:#fff}',
    '.pk-why-l{font-size:14px;font-weight:500;color:' + T.ink + ';line-height:1.4;max-width:20ch}.pk-why-note{font-size:10px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:' + T.muted + '}',
    // grids
    '.pk-grid{display:grid;gap:14px}.pk-types{grid-template-columns:repeat(auto-fill,minmax(200px,1fr))}.pk-types-one{grid-template-columns:minmax(200px,240px);justify-content:center}.pk-sizes{grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}.pk-mats{grid-template-columns:repeat(auto-fill,minmax(190px,1fr))}.pk-fins{grid-template-columns:repeat(auto-fill,minmax(180px,1fr))}',
    '.pk-type{display:flex;flex-direction:column;border:1px solid ' + T.hairline + ';border-radius:10px;overflow:hidden;background:#fff;color:' + T.ink + '}.pk-type:hover{color:' + T.ink + '}',
    '.pk-type-ph{background:' + T.alt + ';padding:30px 8px;display:flex;align-items:center;justify-content:center}.pk-type-ph img{height:36px;width:auto;opacity:.16}.pk-type-l{font-weight:600;font-size:14px;padding:12px 14px 8px}',
    // secondary (outline) CTA on type cards — dials back the repeated solid red; fills on card hover
    '.pk-type .pk-btn-sm{margin:auto 14px 14px;text-align:center;background:#fff;color:' + T.brand + ';border:1px solid ' + T.brand + '}.pk-type:hover .pk-btn-sm{background:' + T.brand + ';color:#fff}',
    // carousel (used when >5 type cards): horizontal scroll with arrow buttons
    '.pk-carousel{display:flex;align-items:center;gap:10px}.pk-car-track{flex:1;min-width:0;overflow-x:auto;white-space:nowrap;scroll-snap-type:x proximity;padding:2px 0}',
    '.pk-car-track::-webkit-scrollbar{height:7px}.pk-car-track::-webkit-scrollbar-thumb{background:' + T.hairline + ';border-radius:4px}',
    '.pk-car-track>.pk-type{display:inline-flex;flex-direction:column;width:220px;min-height:222px;vertical-align:top;white-space:normal;margin-right:14px;scroll-snap-align:start}',
    '.pk-car-btn{flex:none;align-self:center;width:40px;height:40px;border-radius:50%;border:1px solid ' + T.hairline + ';background:#fff;color:' + T.brand + ';font-size:22px;line-height:1;cursor:pointer;display:flex;align-items:center;justify-content:center}.pk-car-btn:hover{background:' + T.brand + ';color:#fff;border-color:' + T.brand + '}',
    '@media(max-width:600px){.pk-car-btn{display:none}}',
    '.pk-scale-note{font-size:11.5px;color:#9e9e9e;margin:-8px 0 14px}',
    '.pk-size{border:1px solid ' + T.hairline + ';border-radius:10px;padding:12px;text-align:center}.pk-size-box{height:128px;display:flex;align-items:center;justify-content:center}.pk-size-box span{background:#fff;border:1.5px solid ' + T.brand + ';border-radius:2px;display:block}.pk-size-na{width:60px;height:40px;border-style:dashed!important;border-color:' + T.hairline + '!important}.pk-size-l{font-size:12.5px;font-weight:500;margin-top:8px}',
    '.pk-mat{border:1px solid ' + T.hairline + ';border-radius:10px;padding:14px}.pk-mat-l{font-size:13.5px;font-weight:500}.pk-bars{display:flex;gap:4px;margin:9px 0 5px}.pk-bars span{height:6px;flex:1;border-radius:3px;background:' + T.hairline + '}.pk-bars span.on{background:' + T.brand + '}.pk-mat-c{font-size:11.5px;color:' + T.muted + '}.pk-mat-c-neutral{color:#9e9e9e}',
    '.pk-has-img{padding:0 0 12px;overflow:hidden}.pk-has-img>*:not(img){padding-left:14px;padding-right:14px}.pk-tile-img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;margin-bottom:10px;border-bottom:1px solid ' + T.hairline + '}.pk-fin.pk-has-img{border-left:1px solid ' + T.hairline + ';padding-bottom:12px}',
    '.pk-size-box img{max-height:128px;max-width:100%;object-fit:contain}.pk-type-photo{padding:0;background:#fff}.pk-type-photo img{height:150px;width:100%;object-fit:contain;opacity:1}',
    '.pk-fin{border:1px solid ' + T.hairline + ';border-left:3px solid ' + T.brand + ';border-radius:8px;padding:12px 14px;font-size:13.5px;font-weight:500}',
    // delivery banner (attention-catching: gradient band, white text, check-circle states, CTA)
    '.pk-deliver{background:linear-gradient(90deg,#FF9A2E,#F02B29);color:#fff;border-radius:16px;margin:40px 0;box-shadow:0 18px 40px rgba(229,34,32,.18)}',
    '.pk-deliver-in{padding:42px 28px;text-align:center}.pk-deliver h2{color:#fff;font-size:22px;font-weight:700;letter-spacing:-.01em;margin:0 0 10px}',
    '.pk-deliver-sub{color:rgba(255,255,255,.94);font-size:14.5px;line-height:1.7;max-width:62ch;margin:0 auto 26px}',
    '.pk-states{list-style:none;margin:0 auto 28px;padding:0;max-width:860px;display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px;text-align:left}',
    '.pk-states li{font-size:14px;font-weight:500;color:#fff;padding-left:30px;position:relative;line-height:1.5}.pk-states li:before{content:"\\2713";position:absolute;left:0;top:0;width:20px;height:20px;border-radius:50%;background:#fff;color:' + T.brand + ';font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center}',
    '.pk-deliver .pk-btn{background:#fff;color:' + T.brand + '}.pk-deliver .pk-btn:hover{background:#fff;color:' + T.brandDark + '}',
    // FAQ accordion (native <details>, styled like the printoka.com FAQ) — section centred,
    // Q&A text kept left-aligned inside the centred block
    '.pk-faq-sec{text-align:center}.pk-faq-sec h2{font-size:20px;font-weight:600;letter-spacing:-.01em;margin:0 0 6px}.pk-faq{max-width:900px;margin:0 auto;text-align:left;border-top:1px solid ' + T.line + '}',
    '.pk-faq-item{border-bottom:1px solid ' + T.line + '}.pk-faq-item summary{list-style:none;cursor:pointer;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:17px 2px;font-size:14.5px;font-weight:600;color:' + T.ink + '}.pk-faq-item summary::-webkit-details-marker{display:none}',
    '.pk-faq-ch{flex:none;color:' + T.brand + ';font-size:13px;transition:transform .15s}.pk-faq-item[open] .pk-faq-ch{transform:rotate(180deg)}',
    '.pk-faq-a{padding:0 2px 18px;font-size:13.5px;color:' + T.muted + ';line-height:1.75}.pk-faq-sec .pk-btn{margin-top:20px}',
    // footer (matches app footer)
    '@media(max-width:760px){.pk-search{order:5;flex:1 1 100%}}',
  ].join('');
}

module.exports = { page, resolve };
