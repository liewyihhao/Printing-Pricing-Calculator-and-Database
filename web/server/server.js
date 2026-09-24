/*
 * Printoka dev server — dependency-free Node HTTP.
 * Serves the static app (web/) AND the operations + catalogue API on one origin.
 * Run:  node web/server/server.js   (wired as the `printoka-web` preview)
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');
const zlib = require('zlib');
const D = require('./domain');
const store = require('./store');
const content = require('./content');
const seoProduct = require('./seo-product');

const PORT = process.env.PORT || 4611;
const WEB_ROOT = path.join(__dirname, '..'); // web/
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.woff2': 'font/woff2', '.map': 'application/json' };

function send(res, code, body, type) {
  res.writeHead(code, { 'Content-Type': type || 'application/json; charset=utf-8', 'Cache-Control': 'no-cache' });
  res.end(typeof body === 'string' || Buffer.isBuffer(body) ? body : JSON.stringify(body));
}
function readBody(req) {
  return new Promise(resolve => { let b = ''; req.on('data', c => b += c); req.on('end', () => { try { resolve(b ? JSON.parse(b) : {}); } catch (e) { resolve({}); } }); });
}

// enrich a job for the client (queue label + actions available to the given role)
function jobView(j, role) {
  return Object.assign({}, j, {
    statusLabel: (D.STATUS[j.status] || {}).label,
    queue: (D.STATUS[j.status] || {}).queue,
    actions: role ? D.availableActions(j, role) : [],
  });
}

async function api(req, res, pathname, query) {
  const seg = pathname.replace(/^\/api\//, '').split('/').filter(Boolean);
  const role = query.role || (req.headers['x-role']) || 'production_director';
  const actor = query.actor || req.headers['x-actor'] || role;

  // GET /api/health
  if (seg[0] === 'health') return send(res, 200, { ok: true, ts: store.now() });
  // POST /api/seed  — reset demo data
  if (seg[0] === 'seed' && req.method === 'POST') { store.reset(); return send(res, 200, { ok: true, reset: true }); }
  // GET /api/roles
  if (seg[0] === 'roles') return send(res, 200, { roles: D.ROLES });
  // GET /api/users
  if (seg[0] === 'users') return send(res, 200, { users: store.users() });

  // GET /api/queues/:dept  — jobs for a department queue, priority-sorted, with role actions
  if (seg[0] === 'queues') {
    const dept = seg[1];
    const jobs = store.jobs().filter(j => (D.STATUS[j.status] || {}).queue === dept).sort(D.priorityCompare);
    return send(res, 200, { dept, count: jobs.length, jobs: jobs.map(j => jobView(j, role)) });
  }
  // GET /api/jobs  (all)  |  POST /api/jobs  (create at intake)  |  GET /api/jobs/:id
  if (seg[0] === 'jobs' && !seg[1] && req.method === 'POST') {
    const body = await readBody(req);
    const j = store.createJob(body);
    return send(res, 200, { ok: true, job: jobView(j, role) });
  }
  if (seg[0] === 'jobs' && !seg[1]) {
    const jobs = store.jobs().slice().sort(D.priorityCompare).map(j => jobView(j, role));
    return send(res, 200, { count: jobs.length, jobs });
  }
  if (seg[0] === 'jobs' && seg[1] && !seg[2]) {
    const j = store.job(seg[1]); if (!j) return send(res, 404, { error: 'not found' });
    return send(res, 200, { job: jobView(j, role), audit: store.audit({ jobId: seg[1] }) });
  }
  // POST /api/jobs/:id/transition  { action, payload }
  if (seg[0] === 'jobs' && seg[2] === 'transition' && req.method === 'POST') {
    const body = await readBody(req);
    const r = store.applyTransition(seg[1], body.role || role, body.actor || actor, body.action, body.payload || {});
    if (r.error) return send(res, 400, r);
    return send(res, 200, { ok: true, job: jobView(r.job, body.role || role), from: r.from, to: r.to });
  }
  // GET /api/audit?jobId=
  if (seg[0] === 'audit') return send(res, 200, { audit: store.audit(query.jobId ? { jobId: query.jobId } : null) });

  // ---- auth: customer accounts + sessions ----
  const token = req.headers['x-token'] || query.token;
  if (seg[0] === 'auth' && seg[1] === 'register' && req.method === 'POST') {
    const r = store.registerCustomer(await readBody(req));
    return send(res, r.error ? 400 : 200, r);
  }
  if (seg[0] === 'auth' && seg[1] === 'login' && req.method === 'POST') {
    const r = store.loginCustomer(await readBody(req));
    return send(res, r.error ? 401 : 200, r);
  }
  if (seg[0] === 'auth' && seg[1] === 'logout' && req.method === 'POST') { store.logout(token); return send(res, 200, { ok: true }); }
  if (seg[0] === 'auth' && seg[1] === 'me') {
    const c = store.sessionCustomer(token);
    return c ? send(res, 200, { customer: c }) : send(res, 401, { error: 'not signed in' });
  }

  // ---- account: address book + credit ledger (require a session) ----
  if (seg[0] === 'account') {
    const me = store.sessionCustomer(token);
    if (!me) return send(res, 401, { error: 'not signed in' });
    if (seg[1] === 'addresses' && !seg[2]) {
      if (req.method === 'GET') return send(res, 200, { addresses: store.getAddresses(me.id) });
      if (req.method === 'POST') return send(res, 200, store.addAddress(me.id, await readBody(req)));
    }
    if (seg[1] === 'addresses' && seg[2] && req.method === 'DELETE') return send(res, 200, store.deleteAddress(me.id, seg[2]));
    if (seg[1] === 'addresses' && seg[2] === 'default' && seg[3] && req.method === 'POST') return send(res, 200, store.setDefaultAddress(me.id, seg[3]));
    if (seg[1] === 'credit' && !seg[2]) {
      if (req.method === 'GET') return send(res, 200, store.getCredit(me.id));
      if (req.method === 'POST') { const b = await readBody(req); return send(res, 200, store.creditEntry(me.id, { reason: b.reason, amount: b.amount, actor: b.actor || 'system', orderId: b.orderId })); }
    }
    // POST /api/account/coupon {code, subtotal} → is this member code valid for this cart?
    if (seg[1] === 'coupon' && req.method === 'POST') { const b = await readBody(req); return send(res, 200, store.checkCoupon(me.id, b.code, b.subtotal)); }
    if (seg[1] === 'profile' && req.method === 'POST') return send(res, 200, store.updateProfile(me.id, await readBody(req)));
    if (seg[1] === 'password' && req.method === 'POST') { const b = await readBody(req); const r = store.changePassword(me.id, b.current, b.next); return send(res, r.error ? 400 : 200, r); }
    return send(res, 404, { error: 'unknown account route' });
  }

  // ---- customer orders (storefront checkout → ops pipeline) ----
  // POST /api/orders  — place an order (creates linked jobs at intake)
  if (seg[0] === 'orders' && !seg[1] && req.method === 'POST') {
    const body = await readBody(req);
    if (!body.items || !body.items.length) return send(res, 400, { error: 'cart is empty' });
    const me = store.sessionCustomer(token); if (me) body.userId = me.id;
    // member promo code: re-verify server-side (owner, minimum spend) and use the server's discount
    if (body.coupon) {
      const r = store.checkCoupon(body.userId, body.coupon, body.subtotal);
      if (!r.ok) return send(res, 400, { error: r.error });
      if (Math.abs((Number(body.couponDiscount) || 0) - r.discount) > 0.01) return send(res, 400, { error: 'Your discount code amount has changed. Please refresh your cart and try again.' });
      body.coupon = r.code; body.couponDiscount = r.discount;
    } else { body.couponDiscount = 0; }
    const o = store.createOrder(body);
    return send(res, 200, { ok: true, order: o });
  }
  if (seg[0] === 'orders' && !seg[1]) {
    const me = store.sessionCustomer(token);
    return send(res, 200, { orders: (me && me.type === 'customer') ? store.ordersForUser(me.id) : store.orders() });
  }
  // ---- admin backoffice data (require an admin session) ----
  if (seg[0] === 'admin') {
    const me = store.sessionCustomer(token);
    if (!me || me.type !== 'admin') return send(res, 401, { error: 'admin sign-in required' });
    if (seg[1] === 'customers') return send(res, 200, { customers: store.customers().filter(c => c.type === 'customer').map(store.publicCustomer) });
    if (seg[1] === 'staff') return send(res, 200, { staff: store.customers().filter(c => c.type !== 'customer').map(store.publicCustomer) });
    if (seg[1] === 'roles') return send(res, 200, { roles: D.ROLES });
    if (seg[1] === 'emails' && !seg[2]) {
      if (req.method === 'GET') return send(res, 200, { templates: store.emailTemplates().map(t => Object.assign({}, t, store.emailStats(t.id))), outbox: store.emailOutbox(60) });
    }
    if (seg[1] === 'emails' && seg[2] && req.method === 'POST') { const b = await readBody(req); return send(res, 200, { templates: store.setEmailActive(seg[2], b.active, me.name || me.email).map(t => Object.assign({}, t, store.emailStats(t.id))) }); }
    return send(res, 404, { error: 'unknown admin route' });
  }
  // ---- custom invoices (staff prepare an invoice to a customer; customers see their own) ----
  if (seg[0] === 'custom-invoices' && !seg[1] && req.method === 'POST') {
    const me = store.sessionCustomer(token); if (!me || me.type === 'customer' || me.type === 'vendor') return send(res, 401, { error: 'staff sign-in required' });
    return send(res, 200, { ok: true, invoice: store.createCustomInvoice(await readBody(req), me) });
  }
  if (seg[0] === 'custom-invoices' && !seg[1]) {
    const me = store.sessionCustomer(token);
    return send(res, 200, { invoices: (me && me.type === 'customer') ? store.customInvoicesForUser(me.id) : store.customInvoices() });
  }
  if (seg[0] === 'custom-invoices' && seg[1] && req.method === 'POST') {
    const me = store.sessionCustomer(token); if (!me || me.type === 'customer' || me.type === 'vendor') return send(res, 401, { error: 'staff sign-in required' });
    const r = store.updateCustomInvoice(seg[1], await readBody(req), me.name || me.email); return send(res, r.error ? 400 : 200, r);
  }
  if (seg[0] === 'custom-invoices' && seg[1]) { const inv = store.customInvoice(seg[1]); return inv ? send(res, 200, { invoice: inv }) : send(res, 404, { error: 'not found' }); }

  // GET /api/orders/:id  — order + live job statuses (confirmation / tracking / management view)
  if (seg[0] === 'orders' && seg[1] && !seg[2]) {
    const o = store.orderView(seg[1]); if (!o) return send(res, 404, { error: 'order not found' });
    // a signed-in customer may only read their own order; staff and public order-number tracking see it
    const me = store.sessionCustomer(token);
    if (me && me.type === 'customer' && o.userId && o.userId !== me.id) return send(res, 403, { error: 'not your order' });
    return send(res, 200, { order: o });
  }
  // POST /api/orders/:id/pay  — validate a pending (bank-transfer/test) payment
  if (seg[0] === 'orders' && seg[2] === 'pay' && req.method === 'POST') {
    const r = store.validateOrderPayment(seg[1], actor);
    if (r.error) return send(res, 400, r);
    return send(res, 200, { ok: true, order: store.orderView(seg[1]) });
  }

  // GET /api/catalogue  — persisted admin overrides (merged over catalogue.js defaults client-side)
  if (seg[0] === 'catalogue' && !seg[1]) {
    if (req.method === 'GET') return send(res, 200, { overrides: store.catalogue() });
  }
  // PATCH/POST /api/catalogue/:id  { displayName, categoryId, hidden }
  if (seg[0] === 'catalogue' && seg[1] && (req.method === 'PATCH' || req.method === 'POST')) {
    const body = await readBody(req);
    const patch = {};
    ['displayName', 'categoryId', 'hidden', 'slug'].forEach(k => { if (body[k] !== undefined) patch[k] = body[k]; });
    const saved = store.setOverride(seg[1], patch, actor);
    return send(res, 200, { ok: true, id: seg[1], override: saved });
  }

  // ---- staff creates a customer account ("Create new user") ----
  if (seg[0] === 'customers' && !seg[1] && req.method === 'POST') {
    const me = store.sessionCustomer(token); if (!me || me.type === 'customer' || me.type === 'vendor') return send(res, 401, { error: 'staff sign-in required' });
    const r = store.createCustomerByStaff(await readBody(req), me); return send(res, r.error ? 400 : 200, r);
  }

  // ---- store settings (announcement bar): public read, admin write ----
  if (seg[0] === 'settings' && !seg[1]) {
    if (req.method === 'GET') return send(res, 200, { settings: store.settings() });
    if (req.method === 'POST') { const me = store.sessionCustomer(token); if (!me || me.type !== 'admin') return send(res, 401, { error: 'admin sign-in required' }); return send(res, 200, { settings: store.updateSettings(await readBody(req), me.name || me.email) }); }
  }

  // ---- notifications (in-app, scoped to the signed-in user) ----
  if (seg[0] === 'notifications' && !seg[1]) {
    const me = store.sessionCustomer(token); if (!me) return send(res, 401, { error: 'sign-in required' });
    return send(res, 200, { notifications: store.notificationsFor(me) });
  }
  if (seg[0] === 'notifications' && seg[2] === 'read' && req.method === 'POST') {
    const me = store.sessionCustomer(token); if (!me) return send(res, 401, { error: 'sign-in required' });
    return send(res, 200, store.markNotificationRead(me, seg[1]));
  }

  // ---- custom quotes ----
  if (seg[0] === 'quotes' && !seg[1] && req.method === 'POST') {
    const me = store.sessionCustomer(token); const body = await readBody(req);
    // outlet walk-in: sign the customer up + file a quote request to the scheduler
    if (body.walkin && me && me.type === 'outlet') { const r = store.createWalkinQuote(body, me); return send(res, r.error ? 400 : 200, r.error ? r : Object.assign({ ok: true }, r)); }
    // staff/outlet may prepare a manual quote (with a free-text body + direct price)
    if (body.manual && me && me.type !== 'customer' && me.type !== 'vendor') return send(res, 200, { ok: true, quote: store.createManualQuote(body, me) });
    return send(res, 200, { ok: true, quote: store.createQuote(body, me) });
  }
  if (seg[0] === 'quotes' && seg[2] === 'remark' && req.method === 'POST') {
    const me = store.sessionCustomer(token); if (!me || me.type === 'customer' || me.type === 'vendor') return send(res, 401, { error: 'staff sign-in required' });
    const b = await readBody(req); const r = store.setQuoteRemark(seg[1], b.remarks, me.name || me.email); return send(res, r.error ? 400 : 200, r);
  }
  if (seg[0] === 'quotes' && seg[2] === 'view' && req.method === 'POST') {
    const me = store.sessionCustomer(token); if (!me) return send(res, 401, { error: 'sign-in required' });
    return send(res, 200, store.viewQuote(seg[1], me));
  }
  if (seg[0] === 'quotes' && seg[2] === 'decision' && req.method === 'POST') {
    const me = store.sessionCustomer(token); if (!me || me.type !== 'outlet') return send(res, 401, { error: 'outlet sign-in required' });
    const b = await readBody(req); const r = store.recordQuoteDecision(seg[1], b.decision, b.remark, me); return send(res, r.error ? 400 : 200, r);
  }
  if (seg[0] === 'quotes' && !seg[1]) {
    const me = store.sessionCustomer(token);
    let list = store.quotes();
    if (me && me.type === 'customer') list = store.quotesForUser(me.id);
    else if (me && me.type === 'outlet') list = list.filter(q => q.outlet === me.outlet); // outlet sees only its own quotes
    return send(res, 200, { quotes: list });
  }
  if (seg[0] === 'quotes' && seg[1] && !seg[2]) { const q = store.quote(seg[1]); return q ? send(res, 200, { quote: q }) : send(res, 404, { error: 'not found' }); }
  if (seg[0] === 'quotes' && seg[2] === 'price' && req.method === 'POST') {
    const me = store.sessionCustomer(token); if (!me || me.type === 'customer' || me.type === 'vendor') return send(res, 401, { error: 'staff sign-in required' });
    const r = store.priceQuote(seg[1], await readBody(req), me.name || me.email); return send(res, r.error ? 400 : 200, r);
  }
  if (seg[0] === 'quotes' && seg[2] === 'accept' && req.method === 'POST') {
    const me = store.sessionCustomer(token); const r = store.acceptQuote(seg[1], me ? me.email : 'customer'); return send(res, r.error ? 400 : 200, r);
  }
  if (seg[0] === 'quotes' && seg[2] === 'reject' && req.method === 'POST') {
    const b = await readBody(req); const me = store.sessionCustomer(token); const r = store.rejectQuote(seg[1], b.reason, me ? me.email : 'customer'); return send(res, r.error ? 400 : 200, r);
  }

  // ---- outsource / vendor quotation flow ----
  if (seg[0] === 'vendors' && !seg[1]) return send(res, 200, { vendors: store.vendorAccounts().map(v => ({ id: v.id, name: v.name })) });
  if (seg[0] === 'vendor' && seg[1] === 'requests') {
    const me = store.sessionCustomer(token); if (!me || me.type !== 'vendor') return send(res, 401, { error: 'vendor sign-in required' });
    return send(res, 200, { jobs: store.vendorRequests(me.id) });
  }
  if (seg[0] === 'jobs' && seg[2] === 'request-quotes' && req.method === 'POST') {
    const b = await readBody(req); const r = store.requestVendorQuotes(seg[1], b.vendorIds, actor);
    return send(res, r.error ? 400 : 200, r);
  }
  if (seg[0] === 'jobs' && seg[2] === 'quote' && req.method === 'POST') {
    const me = store.sessionCustomer(token); if (!me || me.type !== 'vendor') return send(res, 401, { error: 'vendor sign-in required' });
    const b = await readBody(req); const r = store.submitVendorQuote(seg[1], me.id, b);
    return send(res, r.error ? 400 : 200, r);
  }
  if (seg[0] === 'jobs' && seg[2] === 'award' && req.method === 'POST') {
    const b = await readBody(req); const r = store.awardVendorPO(seg[1], b.vendorId, actor);
    return send(res, r.error ? 400 : 200, r);
  }

  // ---- content: blog / Learning Hub + programmatic SEO landing pages ----
  if (seg[0] === 'content' && seg[1] === 'blog' && !seg[2]) return send(res, 200, { posts: content.blogList() });
  if (seg[0] === 'content' && seg[1] === 'blog' && seg[2]) {
    const p = content.blogPost(seg[2]); if (!p) return send(res, 404, { error: 'not found' });
    return send(res, 200, { post: p });
  }
  if (seg[0] === 'content' && seg[1] === 'faq') return send(res, 200, { faq: content.faqList() });
  if (seg[0] === 'content' && seg[1] === 'downloads') return send(res, 200, { downloads: content.downloadsList() });
  if (seg[0] === 'content' && seg[1] === 'media') return send(res, 200, { media: content.mediaList() });
  if (seg[0] === 'content' && seg[1] === 'seo' && !seg[2]) return send(res, 200, { pages: content.seoList(query.locale) });
  if (seg[0] === 'content' && seg[1] === 'seo' && seg[2]) {
    const p = content.seoPage(seg[2], query.locale); if (!p) return send(res, 404, { error: 'not found' });
    return send(res, 200, { page: p });
  }

  return send(res, 404, { error: 'unknown api route', path: pathname });
}

// text types worth gzipping (the 20MB engine.js compresses ~95%). Images are already compressed.
const GZIP_RE = /\b(text\/|application\/(javascript|json|xml)|image\/svg)/i;
function sendStatic(req, res, data, type) {
  const ae = String((req.headers && req.headers['accept-encoding']) || '');
  if (GZIP_RE.test(type || '') && /\bgzip\b/.test(ae) && data && data.length > 512) {
    return zlib.gzip(data, (e, gz) => {
      if (e) return send(res, 200, data, type);
      res.writeHead(200, { 'Content-Type': type, 'Content-Encoding': 'gzip', 'Vary': 'Accept-Encoding', 'Cache-Control': 'no-cache' });
      res.end(gz);
    });
  }
  send(res, 200, data, type);
}
function serveStatic(req, res, pathname) {
  let rel = decodeURIComponent(pathname);
  if (rel === '/' || rel === '') rel = '/index.html';
  const filePath = path.normalize(path.join(WEB_ROOT, rel));
  if (!filePath.startsWith(WEB_ROOT)) return send(res, 403, 'forbidden', 'text/plain');
  fs.readFile(filePath, (err, data) => {
    if (err) {
      // SPA fallback: extensionless content URLs (/blog/<slug>/, /<service>-printing-<city>/, /au/...)
      // serve the app shell; the client reads location.pathname and routes to the right page.
      if (!path.extname(filePath)) return fs.readFile(path.join(WEB_ROOT, 'index.html'), (e, html) => e ? send(res, 404, 'Not found', 'text/plain') : sendStatic(req, res, html, MIME['.html']));
      return send(res, 404, 'Not found: ' + rel, 'text/plain');
    }
    sendStatic(req, res, data, MIME[path.extname(filePath).toLowerCase()] || 'application/octet-stream');
  });
}

http.createServer(async (req, res) => {
  const parsed = url.parse(req.url, true);
  // real public origin (honour a reverse proxy's forwarded host/proto in production)
  const proto = (req.headers['x-forwarded-proto'] || 'http').split(',')[0].trim();
  const host = (req.headers['x-forwarded-host'] || req.headers.host || ('localhost:' + PORT)).split(',')[0].trim();
  const origin = proto + '://' + host;
  try {
    if (parsed.pathname.indexOf('/api/') === 0) return await api(req, res, parsed.pathname, parsed.query);
    if (parsed.pathname === '/sitemap.xml') return send(res, 200, content.sitemapXml(origin), 'application/xml; charset=utf-8');
    // robots.txt — allow crawling, point at the sitemap, keep app/ops routes out of the index
    if (parsed.pathname === '/robots.txt') return send(res, 200, [
      'User-agent: *',
      'Allow: /',
      'Disallow: /api/',
      'Disallow: /cart', 'Disallow: /checkout', 'Disallow: /dash', 'Disallow: /admin',
      'Disallow: /production', 'Disallow: /vendor', 'Disallow: /invoices',
      'Host: ' + host,
      'Sitemap: ' + origin + '/sitemap.xml', '',
    ].join('\n'), 'text/plain; charset=utf-8');
    // Product SEO page (SSR) — full content in the initial HTML, at /<slug>-printing.
    // The /configure/ sub-route is the interactive configurator (SPA), handled by serveStatic.
    const pm = parsed.pathname.match(/^\/([a-z0-9-]+-printing)\/?$/);
    if (pm) { try { const html = seoProduct.page(pm[1], origin); if (html) return sendStatic(req, res, Buffer.from(html), MIME['.html']); } catch (e) { /* fall through to SPA */ } }
    return serveStatic(req, res, parsed.pathname);
  } catch (e) { send(res, 500, { error: String(e && e.message || e) }); }
}).listen(PORT, () => console.log('Printoka dev server on http://localhost:' + PORT + ' (static + /api)'));
