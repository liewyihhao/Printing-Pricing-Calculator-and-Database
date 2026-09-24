/*
 * Content subsystem — blog/Learning Hub, programmatic SEO landing pages, and the
 * sitemap. Migrated from the live printoka.com WordPress site (Rank Math sitemaps
 * gave the full URL inventory; blog bodies fetched from the live articles).
 * Dependency-free: reads the JSON in web/content/.
 */
const fs = require('fs');
const path = require('path');

const DIR = path.join(__dirname, '..', 'content');
function readJson(name, fallback) {
  try { return JSON.parse(fs.readFileSync(path.join(DIR, name), 'utf8')); } catch (e) { return fallback; }
}
let _blog = null, _seo = null, _faq = null, _downloads = null;
function blog() { if (!_blog) _blog = readJson('blog.json', []); return _blog; }
function seo() { if (!_seo) _seo = readJson('seo-data.json', []); return _seo; }
function faqList() { if (!_faq) _faq = readJson('faq.json', []); return _faq; }
function downloadsList() { if (!_downloads) _downloads = readJson('downloads.json', []); return _downloads; }
// media library — the image assets shipped with the app (product photos + brand icons)
function mediaList() {
  const A = path.join(__dirname, '..', 'assets');
  const scan = (sub, kind) => { try { return fs.readdirSync(path.join(A, sub)).filter(f => /\.(jpg|jpeg|png|svg|webp|gif)$/i.test(f)).map(f => ({ file: 'assets/' + sub + '/' + f, name: f, kind, ext: f.split('.').pop().toLowerCase() })); } catch (e) { return []; } };
  return scan('uploads', 'Uploaded').concat(scan('original', 'Original site image'), scan('products', 'Product image'), scan('icons', 'Icon / UI'));
}

// Learning Hub list — no body, adds a bodyReady flag so the UI can show which are live.
function blogList() {
  return blog().map(p => ({ slug: p.slug, title: p.title, date: p.date, tag: p.tag, excerpt: p.excerpt, url: p.url, bodyReady: !!p.body }));
}
function blogPost(slug) { return blog().find(p => p.slug === slug) || null; }

function seoList(locale) {
  const all = seo();
  return locale ? all.filter(p => p.locale === locale) : all;
}
function seoPage(slug, locale) {
  return seo().find(p => p.slug === slug && (!locale || p.locale === locale)) || seo().find(p => p.slug === slug) || null;
}

// Crawlable product + category URLs — built from the same product list + display-name
// overrides the client uses, so each /<name>-printing path matches what the app resolves.
// The 20MB engine is required once and cached (dev/prototype server).
let _prodUrls = null;
function slugify(s) { return String(s || '').toLowerCase().replace(/&/g, ' and ').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, ''); }
function productUrls() {
  if (_prodUrls) return _prodUrls;
  const urls = [];
  try {
    const cat = (function () { try { const vm = require('vm'); const code = fs.readFileSync(path.join(__dirname, '..', 'catalogue.js'), 'utf8'); const sandbox = { window: {} }; vm.runInNewContext(code, sandbox); return sandbox.window.PrintokaCatalogueDefaults || {}; } catch (e) { return {}; } })();
    const overrides = (cat && cat.overrides) || {};
    (cat.categories || []).forEach(c => { if (c && c.id) urls.push('/products/' + c.id); });
    // load the pricing engine into a private global to read the product list
    const engPath = path.join(__dirname, '..', 'pricing', 'engine.js');
    global.window = global.window || {};
    require(engPath);
    const E = global.window.PricingEngine;
    const prods = (E && E.DATA && E.DATA.products) || [];
    const seen = {};
    prods.forEach(p => {
      const ov = overrides[p.id] || overrides[String(p.id)];
      if (ov && ov.hidden) return;
      const name = (ov && ov.displayName) || p.name;
      const slug = slugify(name) + '-printing';
      if (!seen[slug]) { seen[slug] = 1; urls.push('/' + slug); }
    });
  } catch (e) { /* engine not loadable → product URLs omitted, core sitemap still served */ }
  _prodUrls = urls;
  return urls;
}

// Full XML sitemap — blog + SEO landing pages + product/category + core storefront routes.
// Preserves the live URL structure for SEO continuity (audit §9).
function sitemapXml(origin) {
  const base = (origin || 'https://printoka.com').replace(/\/$/, '');
  const urls = [];
  ['/', '/blog/', '/about-us/', '/products'].forEach(u => urls.push(u));
  productUrls().forEach(u => urls.push(u));
  blog().forEach(p => urls.push(p.url));
  // only the major "keeper" city landing pages are indexable (the long-tail are noindexed to
  // avoid doorway-page duplication), so the sitemap lists only those (content-strategy §4).
  const KEEP = { 'kuala-lumpur': 1, 'petaling-jaya': 1, 'shah-alam': 1, 'klang': 1, 'klang-valley': 1, 'penang': 1, 'pulau-pinang': 1, 'georgetown': 1, 'george-town': 1, 'johor-bahru': 1, 'iskandar-puteri': 1, 'ipoh': 1, 'kuching': 1, 'miri': 1, 'kota-kinabalu': 1, 'seremban': 1, 'melaka': 1, 'malaysia': 1, 'singapore': 1, 'brunei': 1, 'bandar-seri-begawan': 1, 'australia': 1, 'new-zealand': 1, 'nz': 1, 'solutions': 1 };
  seo().forEach(p => { const city = String(p.slug || '').replace(/^.*?-printing-/, '').replace(/^in-/, ''); if (KEEP[city]) urls.push(p.path); });
  const seenU = {};
  const body = urls.filter(u => (u && !seenU[u] && (seenU[u] = 1))).map(u => `  <url><loc>${base}${u}</loc></url>`).join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</urlset>\n`;
}

// admin edits write the JSON files; drop the caches so the next read sees them
function reload() { _blog = null; _faq = null; _downloads = null; }
module.exports = { reload, blogList, blogPost, seoList, seoPage, sitemapXml, faqList, downloadsList, mediaList };
