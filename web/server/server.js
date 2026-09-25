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
const ops = require('./ops');
const admin = require('./admin');
const files = require('./files');
const outlet = require('./outlet');
const supplier = require('./supplier');
ops.migrate();
const content = require('./content');
const seoProduct = require('./seo-product');

const PORT = process.env.PORT || 4611;
const WEB_ROOT = path.join(__dirname, '..'); // web/
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.map': 'application/json', '.pdf': 'application/pdf', '.webp': 'image/webp', '.gif': 'image/gif', '.ico': 'image/x-icon' };

function send(res, code, body, type) {
  res.writeHead(code, { 'Content-Type': type || 'application/json; charset=utf-8', 'Cache-Control': 'no-cache' });
  res.end(typeof body === 'string' || Buffer.isBuffer(body) ? body : JSON.stringify(body));
}
function readBody(req) {
  return new Promise(resolve => { let b = ''; req.on('data', c => b += c); req.on('end', () => { try { resolve(b ? JSON.parse(b) : {}); } catch (e) { resolve({}); } }); });
}

// enrich a job for the client (queue label + actions available to the given role)
function jobView(j, role) {
  if (ops.normalizeJob(j)) store.save();
  return Object.assign({}, j, {
    statusLabel: (D.STATUS[j.status] || {}).label,
    queue: (D.STATUS[j.status] || {}).queue,
    actions: role ? D.availableActions(j, role) : [],
  });
}

async function api(req, res, pathname, query) {
  const seg = pathname.replace(/^\/api\//, '').split('/').filter(Boolean);
  const token = req.headers['x-token'] || query.token;
  const staffMe = () => { const m = store.sessionCustomer(token); return m && m.type !== 'customer' ? m : null; };
  // ops endpoints: staff session required; role + actor are derived server-side from it
  const OPS = { queues: 1, jobs: 1, audit: 1, ops: 1, users: 1 };
  let role = null, actor = 'system', me0 = null;
  if (OPS[seg[0]] && !(seg[0] === 'ops' && seg[1] === 'outlets')) {
    me0 = staffMe();
    if (!me0) return send(res, 401, { error: 'staff sign-in required' });
    role = D.opsRoleFor(me0);
    if (!role) return send(res, 403, { error: 'your account has no operations role' });
    if (me0.type === 'vendor' && seg[0] !== 'jobs' && !(seg[0] === 'ops' && seg[1] === 'individual')) return send(res, 403, { error: 'not available to printers' });
    actor = me0.name || me0.email;
  }

  // GET /api/health
  if (seg[0] === 'health') return send(res, 200, { ok: true, ts: store.now() });
  // POST /api/seed  — reset demo data (administrators only)
  if (seg[0] === 'seed' && req.method === 'POST') { const a = store.sessionCustomer(token); if (!a || a.type !== 'admin') return send(res, 403, { error: 'administrators only' }); store.reset(); return send(res, 200, { ok: true, reset: true }); }
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
    body.actor = actor; if (!body.outlet && me0 && me0.outlet) body.outlet = me0.outlet;
    const j = store.createJob(body); ops.normalizeJob(j); store.save();
    return send(res, 200, { ok: true, job: jobView(j, role) });
  }
  if (seg[0] === 'jobs' && !seg[1]) {
    let list = store.jobs().slice();
    // printers see only the jobs they were asked to quote — without the customer's details
    if (me0.type === 'vendor') { const vj = list.filter(j => supplier.vendorCanSee(j, me0)).sort(D.priorityCompare).map(j => Object.assign(supplier.vendorJob(j, me0), { printing: supplier.listRow(j, me0), actions: [] })); return send(res, 200, { count: vj.length, role, jobs: vj }); }
    if (me0.type === 'hub' && me0.hub) list = list.filter(j => supplier.hubCanSee(j, me0));
    const jobs = list.sort(D.priorityCompare).map(j => Object.assign(jobView(j, role), j.outsource ? { printing: supplier.listRow(j, me0) } : {}));
    return send(res, 200, { count: jobs.length, role, jobs });
  }
  if (seg[0] === 'jobs' && seg[1] && !seg[2]) {
    const j = store.job(seg[1]); if (!j) return send(res, 404, { error: 'not found' });
    if (!supplier.canSee(j, me0)) return send(res, 403, { error: 'Access denied: You are not authorized to view this.' });
    if (me0.type === 'vendor') return send(res, 200, { job: supplier.vendorJob(j, me0), printing: supplier.view(j, me0), audit: [], order: null });
    // "Quote Pending from Printer" is done once a received printer quote has been opened by the scheduler
    if (['scheduler_staff', 'scheduler_manager', 'production_director'].indexOf(role) >= 0 && j.outsource) { let seen = false; (j.outsource.vendors || []).forEach(v => { if (v.submittedAt && !v.seenAt) { v.seenAt = store.now(); seen = true; } }); if (seen) store.save(); }
    ops.claim(j, role, actor); // the first staff member of the job's department to open it takes that part
    const o = j.orderId ? store.order(j.orderId) : null;
    return send(res, 200, { job: jobView(j, role), handlers: ops.handlers(j), printing: supplier.view(j, me0), audit: store.audit({ jobId: seg[1] }), order: o && me0.type !== 'hub' ? { id: o.id, customer: o.customer, shipTo: o.shipTo, fulfillment: o.fulfillment, payment: o.payment, total: o.total, progressLabel: o.progressLabel, createdAt: o.createdAt, items: o.items, files: (o.files || []).filter(f => f.kind === 'artwork') } : null });
  }
  // ---- printers & hubs (original printoka-3rd-party-supplier flow) ----
  if (seg[0] === 'jobs' && seg[1] && ['vendor-quote', 'ship-to-hub', 'delivery', 'vendor-paid', 'doc', 'files', 'proof'].indexOf(seg[2]) >= 0) {
    const j0 = store.job(seg[1]); if (!j0) return send(res, 404, { error: 'not found' });
    if (!supplier.canSee(j0, me0)) return send(res, 403, { error: 'Access denied: You are not authorized to view this.' });
    const out = r => send(res, r && r.error ? (r.code || 400) : 200, r);
    const APPROVERS = ['scheduler_staff', 'scheduler_manager', 'production_director'];
    if (seg[2] === 'doc') return out(supplier.documentData(j0, seg[3], me0));
    if (seg[2] === 'files') { const r = supplier.readJobFile(j0, seg[3], me0); if (r.error) return out(r); res.writeHead(200, { 'Content-Type': r.type, 'Content-Disposition': 'attachment; filename="' + r.file.name.replace(/"/g, '') + '"', 'Cache-Control': 'private, no-store' }); return res.end(r.data); }
    if (req.method !== 'POST') return send(res, 405, { error: 'POST only' });
    const b = await readBody(req);
    if (me0.type !== 'vendor' && me0.type !== 'hub') {
      if (seg[2] === 'proof') return ['prepress_staff', 'prepress_manager', 'production_director'].indexOf(role) >= 0 ? out(supplier.saveProof(seg[1], me0, b)) : send(res, 403, { error: 'prepress only' });
    }
    if (seg[2] === 'vendor-quote') return me0.type === 'vendor' ? out(supplier.submitQuote(seg[1], me0, b)) : send(res, 403, { error: 'printers only' });
    if (seg[2] === 'ship-to-hub') return me0.type === 'vendor' ? out(supplier.shipToHub(seg[1], me0, b)) : send(res, 403, { error: 'printers only' });
    if (seg[2] === 'delivery') return me0.type === 'vendor' ? send(res, 403, { error: 'not available to printers' }) : out(supplier.deliveryDetails(seg[1], me0, role, b));
    if (seg[2] === 'vendor-paid') return APPROVERS.indexOf(role) >= 0 ? out(supplier.markPaid(seg[1], actor, role, b)) : send(res, 403, { error: 'Only the scheduler pays printers.' });
  }
  // POST /api/jobs/:id/transition  { action, payload }
  if (seg[0] === 'jobs' && seg[2] === 'transition' && req.method === 'POST') {
    const body = await readBody(req);
    if (me0.type === 'vendor') { const j0 = store.job(seg[1]); if (!j0 || !j0.outsource || j0.outsource.awardedTo !== (me0.vendorId || me0.id) || body.action !== 'vendor_ship') return send(res, 403, { error: 'printers can only ship jobs awarded to them' }); }
    if (me0.type === 'hub' && !supplier.canSee(store.job(seg[1]), me0)) return send(res, 403, { error: 'This job is not at your hub.' });
    const r = ops.transition(seg[1], role, actor, body.action, body.payload || {});
    if (r.error) return send(res, 400, r);
    return send(res, 200, { ok: true, job: jobView(store.job(seg[1]), role), from: r.from, to: r.to });
  }
  // POST /api/jobs/:id/step  { group, key, done, note }  — interactive progress forms
  if (seg[0] === 'jobs' && seg[2] === 'step' && req.method === 'POST') {
    const b = await readBody(req); const r = ops.setStep(seg[1], b.group, b.key, b.done !== false, role, actor, b.note);
    return r.error ? send(res, 400, r) : send(res, 200, { ok: true, job: jobView(r.job, role) });
  }
  // POST /api/jobs/:id/send-internal  { machine, destType, destId, instructions, parcels }  (Qn 752 CF1)
  if (seg[0] === 'jobs' && seg[2] === 'send-internal' && req.method === 'POST') {
    const r = ops.sendInternal(seg[1], role, actor, await readBody(req));
    return r.error ? send(res, 400, r) : send(res, 200, { ok: true, job: jobView(r.job, role) });
  }
  // ---- ops settings (CMS), KPIs, sales, hub performance, action tracker ----
  if (seg[0] === 'ops' && seg[1] === 'outlets') return send(res, 200, { outlets: ops.config().outlets.filter(o => o.pickup !== false).map(o => ({ id: o.id, name: o.name, address: o.address })) });
  if (seg[0] === 'ops' && seg[1] === 'config') {
    if (req.method === 'POST') {
      if (['production_director', 'scheduler_manager', 'hub_manager', 'logistics_manager'].indexOf(role) < 0) return send(res, 403, { error: 'managers only' });
      return send(res, 200, { config: ops.saveConfig(await readBody(req), actor) });
    }
    return send(res, 200, { config: ops.config(), checklists: D.CHECKLISTS, errorTypes: D.ERROR_TYPES });
  }
  if (seg[0] === 'ops' && seg[1] === 'kpi') return send(res, 200, { kpi: ops.kpi(query.dept, query.days) });
  // individual performance report (per staff member; managers / the director / printer managers may pick staff)
  if (seg[0] === 'ops' && seg[1] === 'individual') { const r = ops.individual(me0, query.staff || null); return send(res, r.error && !r.staff ? 403 : 200, r); }
  // daily reporting (guidebook §1.6): the department manager submits; the production director reads all
  if (seg[0] === 'ops' && seg[1] === 'daily-report') {
    const dept = String(query.dept || (req.method === 'POST' ? '' : D.deptOf(role)) || '');
    if (req.method === 'POST') { const b = await readBody(req); const r = ops.submitReport(b.dept || D.deptOf(role), b.kind, b, me0, role); return send(res, r.error ? 400 : 200, r); }
    if (role !== 'production_director' && (D.deptOf(role) !== dept || D.tierOf(role) !== 'manager')) return send(res, 403, { error: 'Daily reports are for the department manager and the production director.' });
    return send(res, 200, { figures: ops.reportFigures(dept) });
  }
  if (seg[0] === 'ops' && seg[1] === 'reports') {
    if (['manager', 'director'].indexOf(D.tierOf(role)) < 0) return send(res, 403, { error: 'managers only' });
    return send(res, 200, { reports: ops.listReports(role, query.days) });
  }
  if (seg[0] === 'ops' && seg[1] === 'sales') {
    if (['production_director', 'scheduler_manager'].indexOf(role) < 0) return send(res, 403, { error: 'managers only' });
    return send(res, 200, { sales: ops.sales(query.days) });
  }
  if (seg[0] === 'ops' && seg[1] === 'hub-performance') return send(res, 200, { performance: ops.hubPerformance(query.hub || (me0.type === 'hub' ? me0.hub : null), query.days) });
  if (seg[0] === 'ops' && seg[1] === 'actions') {
    const managerish = /manager|director/.test(role);
    return send(res, 200, { actions: ops.actions(query.dept, { actor: (query.mine === '1' || !managerish) ? actor : null, days: Number(query.days) || 0 }) });
  }
  if (seg[0] === 'ops' && seg[1] === 'staff') return send(res, 200, { staff: store.customers().filter(c => c.type !== 'customer' && c.type !== 'vendor').map(c => ({ id: c.id, name: c.name, email: c.email, type: c.type, role: c.role, opsRole: D.opsRoleFor(c), outlet: c.outlet || null, hub: c.hub || null })) });
  // GET /api/audit?jobId=
  if (seg[0] === 'audit') return send(res, 200, { audit: store.audit(query.jobId ? { jobId: query.jobId } : null) });

  // ---- auth: customer accounts + sessions ----
  if (seg[0] === 'auth' && seg[1] === 'register' && req.method === 'POST') {
    const r = store.registerCustomer(await readBody(req));
    return send(res, r.error ? 400 : 200, r);
  }
  // account activation / password reset (original form-reset-password.php + lx_reset_password_content)
  if (seg[0] === 'auth' && seg[1] === 'reset-password') {
    if (req.method === 'POST') { const b = await readBody(req); const r = store.resetPassword(b.login, b.key, b.password_1, b.password_2); return send(res, r.error ? 400 : 200, r); }
    const r = store.resetCheck(query.login, query.key); if (r.error) return send(res, 400, { error: r.error });
    return send(res, 200, r.activate ? { title: 'Activate Your Account', subtitle: 'Set your password below to finalize your registration.', button: 'Activate your account', activate: true }
      : { title: 'Reset Password', subtitle: 'Enter a new password below.', button: 'Save', activate: false });
  }
  if (seg[0] === 'auth' && seg[1] === 'lost-password' && req.method === 'POST') { const b = await readBody(req); return send(res, 200, store.requestPasswordReset(b.email)); }
  if (seg[0] === 'auth' && seg[1] === 'login' && req.method === 'POST') {
    const lb = await readBody(req);
    // login portals: each sign-in page only admits its own kind of account
    const PORTAL = { member: ['customer'], printer: ['vendor'], hub: ['hub'], outlet: ['outlet'], production: ['production'], admin: ['admin'] };
    const who = store.customers().find(c => c.email === String(lb.email || '').trim().toLowerCase());
    if (lb.portal && PORTAL[lb.portal] && who && PORTAL[lb.portal].indexOf(who.type) < 0) {
      const home = Object.keys(PORTAL).find(k => PORTAL[k].indexOf(who.type) >= 0) || 'member';
      return send(res, 403, { error: 'This sign-in page is for ' + ({ member: 'customers', printer: 'printers', hub: 'hub staff', outlet: 'outlet staff', production: 'production staff', admin: 'administrators' })[lb.portal] + '. Please use the ' + ({ member: 'customer', printer: 'Printer', hub: 'Hub', outlet: 'Outlet', production: 'Production', admin: 'Admin' })[home] + ' login.', portal: home });
    }
    if (who && who.disabled) return send(res, 403, { error: 'This account has been disabled. Please contact your administrator.' });
    const r = store.loginCustomer(lb);
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
      if (req.method === 'POST') {
        const b = await readBody(req); const amt = Math.round(Number(b.amount) * 100) / 100;
        if (!(amt > 0) || amt > 20000) return send(res, 400, { error: 'Enter a top-up between RM 1 and RM 20,000.' });
        if (admin.commerce().payments.testMode) return send(res, 200, store.creditEntry(me.id, { reason: 'TOPUP', amount: amt, actor: 'customer (test payment)' }));
        const db0 = store.load(); db0.topups = db0.topups || [];
        const tu = { id: 'TU-' + Date.now().toString(36).toUpperCase(), userId: me.id, name: me.name, email: me.email, amount: amt, status: 'pending', createdAt: store.now() };
        db0.topups.unshift(tu); store.logEvent({ actor: me.email, role: 'customer', action: 'topup_request', jobId: null, from: null, to: null, note: tu.id + ' RM ' + amt }); store.save();
        return send(res, 200, Object.assign(store.getCredit(me.id), { pending: tu, message: 'Top-up of RM ' + amt.toFixed(2) + ' recorded — it is added once your payment is confirmed.' }));
      }
    }
    // POST /api/account/coupon {code, subtotal} → is this member code valid for this cart?
    if (seg[1] === 'coupon' && req.method === 'POST') { const b = await readBody(req); return send(res, 200, admin.checkAnyCoupon(me.id, b.code, b.subtotal)); }
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
    // member promo code / store coupon: re-verify server-side (owner, minimum spend, limits) and use the server's discount
    if (body.coupon) {
      const r = admin.checkAnyCoupon(body.userId, body.coupon, body.subtotal);
      if (r.storeWide) body._storeCoupon = r.code;
      if (!r.ok) return send(res, 400, { error: r.error });
      if (Math.abs((Number(body.couponDiscount) || 0) - r.discount) > 0.01) return send(res, 400, { error: 'Your discount code amount has changed. Please refresh your cart and try again.' });
      body.coupon = r.code; body.couponDiscount = r.discount;
    } else { body.couponDiscount = 0; }
    const vt = admin.verifyTotals(body, me && me.type === 'customer' ? me : null);
    if (vt.error) return send(res, 400, vt);
    // store the server's own figures (rounded), never the browser's
    body.memberDiscount = vt.memberDiscount; body.shipping = vt.shipping; body.total = vt.total;
    body.tax = Math.round((Number(body.tax) || 0) * 100) / 100; body.subtotal = Math.round((Number(body.subtotal) || 0) * 100) / 100;
    const o = store.createOrder(body);
    if (body._storeCoupon) admin.recordCouponUse(body._storeCoupon, body.userId);
    ops.onOrderCreated(o);
    return send(res, 200, { ok: true, order: store.order(o.id) });
  }
  if (seg[0] === 'orders' && !seg[1]) {
    const me = store.sessionCustomer(token);
    return send(res, 200, { orders: (me && me.type === 'customer') ? store.ordersForUser(me.id) : store.orders() });
  }
  // ---- admin backoffice data (require an admin session) ----
  if (seg[0] === 'admin') {
    const me = store.sessionCustomer(token);
    if (!me || me.type !== 'admin') return send(res, 401, { error: 'admin sign-in required' });
    if (seg[1] === 'customers' && !seg[2] && req.method === 'GET') return send(res, 200, { customers: store.customers().filter(c => c.type === 'customer').map(store.publicCustomer) });
    if (seg[1] === 'staff' && !seg[2] && req.method === 'GET') return send(res, 200, { staff: store.customers().filter(c => c.type !== 'customer').map(store.publicCustomer) });
    if (seg[1] === 'roles') return send(res, 200, { roles: D.ROLES, staffRoles: store.STAFF_ROLES });
    // WordPress Users → Add New / Edit role / disable / reset password
    if (seg[1] === 'staff' && !seg[2] && req.method === 'POST') { const r = store.createStaffAccount(await readBody(req), me.name || me.email); return send(res, r.error ? 400 : 200, r); }
    if (seg[1] === 'staff' && seg[2] && req.method === 'POST') { const r = store.updateStaffAccount(seg[2], await readBody(req), me.name || me.email); return send(res, r.error ? 400 : 200, r); }
    if (seg[1] === 'emails' && !seg[2]) {
      if (req.method === 'GET') return send(res, 200, { templates: store.emailTemplates().map(t => Object.assign({}, t, store.emailStats(t.id))), outbox: store.emailOutbox(60) });
    }
    if (seg[1] === 'emails' && seg[2] && req.method === 'POST') { const b = await readBody(req); return send(res, 200, { templates: store.setEmailActive(seg[2], b.active, me.name || me.email).map(t => Object.assign({}, t, store.emailStats(t.id))) }); }
    const who = me.name || me.email;
    if (seg[1] === 'analytics') return send(res, 200, { analytics: admin.analytics(query.days) });
    if (seg[1] === 'coupons' && !seg[2]) {
      if (req.method === 'POST') { const r = admin.saveCoupon(await readBody(req), who); return send(res, r.error ? 400 : 200, r); }
      return send(res, 200, { coupons: admin.coupons() });
    }
    if (seg[1] === 'coupons' && seg[3] === 'delete' && req.method === 'POST') { const r = admin.deleteCoupon(seg[2], who); return send(res, r.error ? 400 : 200, r); }
    if (seg[1] === 'orders' && seg[2] && req.method === 'POST') {
      const b = await readBody(req); let r;
      if (seg[3] === 'note') r = admin.orderNote(seg[2], b.text, b.toCustomer, who);
      else if (seg[3] === 'cancel') r = admin.cancelOrder(seg[2], b.reason, who);
      else if (seg[3] === 'refund') r = admin.refundOrder(seg[2], b.amount, b.method, b.reason, who);
      else if (seg[3] === 'address') r = admin.updateOrderAddress(seg[2], b, who);
      else if (seg[3] === 'resend') r = admin.resendConfirmation(seg[2], who);
      else return send(res, 404, { error: 'unknown order action' });
      if (!r.error && r.order) ops.syncOrder(seg[2]);
      return send(res, r.error ? 400 : 200, r.error ? r : Object.assign({ ok: true }, r, r.order ? { order: store.orderView(seg[2]) } : {}));
    }
    if (seg[1] === 'customers' && seg[2] && !seg[3] && req.method === 'POST') { const r = admin.updateCustomer(seg[2], await readBody(req), who); return send(res, r.error ? 400 : 200, r); }
    if (seg[1] === 'customers' && seg[3] === 'wallet' && req.method === 'POST') { const b = await readBody(req); const r = admin.walletAdjust(seg[2], b.amount, b.note, who); return send(res, r.error ? 400 : 200, r); }
    if (seg[1] === 'customers' && seg[3] === 'login-as' && req.method === 'POST') { const r = admin.loginAs(seg[2], who); return send(res, r.error ? 400 : 200, r); }
    if (seg[1] === 'customers' && seg[2] && !seg[3]) { const c = store.findCustomer(seg[2]); if (!c) return send(res, 404, { error: 'not found' }); return send(res, 200, { customer: store.publicCustomer(c), orders: store.ordersForUser(c.id), credit: store.getCredit(c.id) }); }
    if (seg[1] === 'posts' && !seg[2] && req.method === 'POST') { const r = admin.savePost(await readBody(req), who); content.reload(); return send(res, r.error ? 400 : 200, r); }
    if (seg[1] === 'posts' && seg[3] === 'delete' && req.method === 'POST') { const r = admin.deletePost(decodeURIComponent(seg[2]), who); content.reload(); return send(res, r.error ? 400 : 200, r); }
    if (seg[1] === 'faq' && !seg[2] && req.method === 'POST') { const r = admin.saveFaq(await readBody(req), who); content.reload(); return send(res, r.error ? 400 : 200, r); }
    if (seg[1] === 'faq' && seg[2] === 'delete' && req.method === 'POST') { const b = await readBody(req); const r = admin.deleteFaq(b.catId, b.index, who); content.reload(); return send(res, r.error ? 400 : 200, r); }
    if (seg[1] === 'media' && !seg[2] && req.method === 'POST') { const r = admin.uploadMedia(await readBody(req), who); return send(res, r.error ? 400 : 200, r); }
    if (seg[1] === 'media' && seg[2] === 'delete' && req.method === 'POST') { const b = await readBody(req); const r = admin.deleteMedia(b.file, who); return send(res, r.error ? 400 : 200, r); }
    if (seg[1] === 'topups' && !seg[2]) return send(res, 200, { topups: store.load().topups || [] });
    if (seg[1] === 'topups' && seg[3] === 'approve' && req.method === 'POST') {
      const tu = (store.load().topups || []).find(x => x.id === seg[2]); if (!tu || tu.status !== 'pending') return send(res, 400, { error: 'Top-up not pending.' });
      store.creditEntry(tu.userId, { reason: 'TOPUP', amount: tu.amount, actor: who }); tu.status = 'approved'; tu.approvedAt = store.now(); tu.approvedBy = who; store.save();
      return send(res, 200, { ok: true, topup: tu });
    }
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

  // order files: artworks per line + payment proof — private, owner or staff only
  if (seg[0] === 'orders' && seg[1] && seg[2] === 'files' && !seg[3] && req.method === 'POST') {
    const fme = store.sessionCustomer(token); if (!fme) return send(res, 401, { error: 'Please sign in to upload files.' });
    const r = files.saveFile(seg[1], await readBody(req), fme); return send(res, r.error ? 400 : 200, r);
  }
  if (seg[0] === 'orders' && seg[1] && seg[2] === 'files' && seg[3]) {
    const fme = store.sessionCustomer(token); if (!fme) return send(res, 401, { error: 'Please sign in.' });
    const r = files.readFile(seg[1], seg[3], fme); if (r.error) return send(res, r.code || 400, { error: r.error });
    res.writeHead(200, { 'Content-Type': r.type, 'Content-Length': r.data.length, 'Content-Disposition': (query.download ? 'attachment' : 'inline') + '; filename="' + r.file.name.replace(/"/g, '') + '"', 'Cache-Control': 'private, no-store' });
    return res.end(r.data);
  }
  // GET /api/orders/:id  — order + live job statuses (confirmation / tracking / management view)
  if (seg[0] === 'orders' && seg[1] && !seg[2]) {
    if (store.order(seg[1])) { (store.order(seg[1]).jobIds || []).forEach(jid => { const jj = store.job(jid); if (jj) ops.normalizeJob(jj); }); ops.syncOrder(seg[1]); }
    const o = store.orderView(seg[1]); if (!o) return send(res, 404, { error: 'order not found' });
    // a signed-in customer may only read their own order; staff and public order-number tracking see it
    const me = store.sessionCustomer(token);
    if (me && me.type === 'customer' && o.userId && o.userId !== me.id) return send(res, 403, { error: 'not your order' });
    return send(res, 200, { order: o });
  }
  // POST /api/orders/:id/pay  — validate a pending (bank-transfer/test) payment
  if (seg[0] === 'orders' && seg[2] === 'pay' && req.method === 'POST') {
    const payer = staffMe(); if (!payer || payer.type === 'vendor' || payer.type === 'hub') return send(res, 401, { error: 'staff sign-in required' });
    const r = store.validateOrderPayment(seg[1], payer.name || payer.email);
    if (!r.error) outlet.onPaid(store.order(seg[1]));
    if (!r.error) { const o = store.order(seg[1]); (o.jobIds || []).forEach(jid => { const jj = store.job(jid); if (jj) { ops.normalizeJob(jj); jj.statusAt = Object.assign(jj.statusAt || {}, { [jj.status]: store.now() }); } }); ops.syncOrder(seg[1]); store.save(); }
    if (r.error) return send(res, 400, r);
    return send(res, 200, { ok: true, order: store.orderView(seg[1]) });
  }
  // POST /api/orders/:id/received — the customer confirms their shipped order arrived (completes the shipment)
  if (seg[0] === 'orders' && seg[2] === 'received' && req.method === 'POST') {
    const cm = store.sessionCustomer(token); const o = store.order(seg[1]);
    if (!cm || cm.type !== 'customer' || !o || o.userId !== cm.id) return send(res, 403, { error: 'Only the customer who placed the order can confirm it arrived.' });
    const done = (o.jobIds || []).map(jid => ops.transition(jid, 'customer', cm.name || cm.email, 'customer_received', {})).filter(r => !r.error).length;
    if (!done) return send(res, 400, { error: 'Nothing on this order is out for delivery yet.' });
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
    if (req.method === 'GET') { admin.commerce(); return send(res, 200, { settings: store.settings() }); }
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
  // what a customer may see of a quote: never the printers, their prices, the price basis or internal handling
  const pubQuote = (q, me) => {
    if (!q || !me || me.type !== 'customer') return q;
    const c = Object.assign({}, q);
    ['printerQuotes', 'printerActivity', 'priceBasis', 'handler', 'outletOpenedAt', 'outletOpenedBy', 'followUpDueAt', 'remarks', 'lastFollowUpAt', 'lastFollowUpBy', 'followups', 'issuedBy', 'requestedByStaff'].forEach(k => { delete c[k]; });
    c.history = (q.history || []).filter(x => ['issued', 'reviewed', 'accepted', 'rejected'].indexOf(x.action) >= 0).map(x => ({ ts: x.ts, action: x.action, price: x.price }));
    // who handles it: walk-in → the outlet staff and the scheduler; website → the scheduler only (never the printer)
    const sched = q.handler ? q.handler.name : ((q.history || []).find(x => x.action === 'issued') || {}).actor || null;
    c.handledBy = { outletStaff: q.outlet ? ((q.issuedBy && q.issuedBy.name) || q.requestedByStaff || null) : null, scheduler: sched };
    return c;
  };
  if (seg[0] === 'quotes' && seg[2] === 'view' && req.method === 'POST') {
    const me = store.sessionCustomer(token); if (!me) return send(res, 401, { error: 'sign-in required' });
    const r = store.viewQuote(seg[1], me); return send(res, 200, r.quote ? Object.assign({}, r, { quote: pubQuote(r.quote, me) }) : r);
  }
  if (seg[0] === 'quotes' && seg[2] === 'decision' && req.method === 'POST') {
    const me = store.sessionCustomer(token); if (!me || me.type !== 'outlet') return send(res, 401, { error: 'outlet sign-in required' });
    const b = await readBody(req); const r = store.recordQuoteDecision(seg[1], b.decision, b.remark, me); if (r.order) ops.onOrderCreated(r.order); return send(res, r.error ? 400 : 200, r);
  }
  if (seg[0] === 'quotes' && !seg[1]) {
    const me = store.sessionCustomer(token);
    if (!me) return send(res, 200, { quotes: [] });
    let list = store.quotes();
    if (me.type === 'customer') list = store.quotesForUser(me.id).map(q => pubQuote(q, me));
    else if (me.type === 'outlet') list = list.filter(q => q.outlet === me.outlet); // outlet sees only its own quotes
    else if (me.type !== 'production' && me.type !== 'admin') list = []; // printers / hubs: not customers' quotes
    return send(res, 200, { quotes: list });
  }
  // a quote is visible to its requester, the staff, and (for outlet quotes) that outlet only
  const quoteAccess = (q, me) => !!(q && me && (me.type === 'admin' || me.type === 'production' || (me.type === 'customer' && (q.userId === me.id || (q.customer && q.customer.email && q.customer.email === me.email))) || (me.type === 'outlet' && (!q.outlet || q.outlet === me.outlet))));
  if (seg[0] === 'quotes' && seg[1] && (!seg[2] || seg[2] === 'accept' || seg[2] === 'reject')) {
    const q = store.quote(seg[1]); if (!q) return send(res, 404, { error: 'not found' });
    if (!quoteAccess(q, store.sessionCustomer(token))) return send(res, 403, { error: 'Access denied: You are not authorized to view this.' });
  }
  if (seg[0] === 'quotes' && seg[1] && !seg[2]) {
    // the first scheduler to open a quote request takes it — their name goes in the quote's log
    const q = store.quote(seg[1]), me = store.sessionCustomer(token);
    if (me && me.type === 'production' && /^scheduler/.test(me.role) && !q.handler && ['requested', 'amendment'].indexOf(q.status) >= 0) {
      q.handler = { id: me.id, name: me.name, at: store.now() };
      q.history.push({ ts: store.now(), actor: me.name, action: 'Handled by ' + me.name + ' (Scheduler)' }); store.save();
    }
    return send(res, 200, { quote: pubQuote(q, me) });
  }
  if (seg[0] === 'quotes' && seg[2] === 'price' && req.method === 'POST') {
    const me = store.sessionCustomer(token); if (!me || me.type === 'customer' || me.type === 'vendor') return send(res, 401, { error: 'staff sign-in required' });
    const r = store.priceQuote(seg[1], await readBody(req), me.name || me.email);
    if (!r.error && r.quote && !r.quote.handler) r.quote.handler = { id: me.id, name: me.name, at: store.now() };
    if (!r.error && r.quote && r.quote.outlet) outlet.onIssued(r.quote, me.name || me.email);
    return send(res, r.error ? 400 : 200, r);
  }
  // ---- outlet account (the original printoka.com outlet dashboard) ----
  if (seg[0] === 'outlet') {
    const me = store.sessionCustomer(token);
    if (!me || (me.type !== 'outlet' && me.type !== 'admin')) return send(res, 401, { error: 'Outlet sign-in required.' });
    const b = req.method === 'POST' ? await readBody(req) : {};
    const out = r => send(res, r && r.error ? 400 : 200, r);
    if (seg[1] === 'dashboard') return out(outlet.dashboard(me));
    if (seg[1] === 'customers') return out({ customers: outlet.searchCustomers(query.q) });
    if (seg[1] === 'staff') return out({ staff: outlet.staffList(me) });
    if (seg[1] === 'performance') return out(outlet.performance(me, query.individual === '1', query.staff || null));
    if (seg[1] === 'quotes' && !seg[2] && req.method === 'POST') return out(outlet.saveSpec(null, b, me));
    if (seg[1] === 'quotes' && !seg[2]) return out({ quotes: outlet.listQuotes(me) });
    if (seg[1] === 'quotes' && seg[2] && !seg[3]) return out(outlet.getQuote(seg[2], me));
    if (seg[1] === 'quotes' && seg[3] === 'spec') return out(outlet.saveSpec(seg[2], b, me));
    if (seg[1] === 'quotes' && seg[3] === 'price') return out(outlet.outletPrice(seg[2], b, me));
    if (seg[1] === 'quotes' && seg[3] === 'follow-up') return out(outlet.followUp(seg[2], me));
    if (seg[1] === 'quotes' && seg[3] === 'reject') return out(outlet.rejectQuote(seg[2], b.reasons, me));
    if (seg[1] === 'quotes' && seg[3] === 'artwork') { const r = outlet.quoteArtwork(seg[2], me); if (r.error) return out(r); res.writeHead(200, { 'Content-Type': 'application/octet-stream', 'Content-Disposition': 'attachment; filename="' + r.name.replace(/"/g, '') + '"', 'Cache-Control': 'private, no-store' }); return res.end(r.data); }
    if (seg[1] === 'orders' && !seg[2]) return out({ orders: outlet.outletOrders(me).map(outlet.orderListView).sort((x, y) => String(y.date).localeCompare(String(x.date))) });
    if (seg[1] === 'orders' && seg[2] && !seg[3]) return out(outlet.orderDetail(seg[2], me));
    if (seg[1] === 'orders' && seg[3] === 'status') return out(outlet.orderAction(seg[2], b.status, me));
    if (seg[1] === 'orders' && seg[3] === 'note') return out(outlet.orderNote(seg[2], b.note, me));
    if (seg[1] === 'orders' && seg[3] === 'address') return out(outlet.orderAddress(seg[2], b, me));
    return send(res, 404, { error: 'unknown outlet route' });
  }
  if (seg[0] === 'quotes' && seg[2] === 'accept' && req.method === 'POST') {
    const me = store.sessionCustomer(token); const r = store.acceptQuote(seg[1], me ? me.email : 'customer'); if (r.order) { outlet.onAccepted(r.quote, store.order(r.order.id)); ops.onOrderCreated(r.order); } return send(res, r.error ? 400 : 200, r.quote ? Object.assign({}, r, { quote: pubQuote(r.quote, me) }) : r);
  }
  if (seg[0] === 'quotes' && seg[2] === 'reject' && req.method === 'POST') {
    const b = await readBody(req); const me = store.sessionCustomer(token); const r = store.rejectQuote(seg[1], b.reason, me ? me.email : 'customer'); return send(res, r.error ? 400 : 200, r.quote ? Object.assign({}, r, { quote: pubQuote(r.quote, me) }) : r);
  }

  // ---- outsource / vendor quotation flow ----
  if (seg[0] === 'vendors' && !seg[1]) return send(res, 200, { vendors: store.vendorAccounts().filter(v => !v.vendorId).map(v => ({ id: v.id, name: v.name, internal: !!v.internal })) });
  if (seg[0] === 'vendor' && seg[1] === 'requests') {
    const me = store.sessionCustomer(token); if (!me || me.type !== 'vendor') return send(res, 401, { error: 'vendor sign-in required' });
    return send(res, 200, { jobs: store.vendorRequests(me.vendorId || me.id).map(j => Object.assign(supplier.vendorJob(j, me), { printing: supplier.listRow(j, me) })), company: me.vendorId || me.id, canQuote: me.role !== 'printer_staff' });
  }
  if (seg[0] === 'jobs' && seg[2] === 'request-quotes' && req.method === 'POST') {
    if (['production_director', 'scheduler_manager', 'scheduler_staff'].indexOf(role) < 0) return send(res, 403, { error: 'scheduler only' });
    const b = await readBody(req); const r = store.requestVendorQuotes(seg[1], b.vendorIds, actor);
    return send(res, r.error ? 400 : 200, r);
  }
  if (seg[0] === 'jobs' && seg[2] === 'quote' && req.method === 'POST') {
    const me = store.sessionCustomer(token); if (!me || me.type !== 'vendor') return send(res, 401, { error: 'vendor sign-in required' });
    if (me.role === 'printer_staff') return send(res, 403, { error: 'Only your printer manager can submit prices.' });
    const b = await readBody(req); const r = supplier.submitQuote(seg[1], me, b);
    return send(res, r.error ? 400 : 200, r.error ? r : Object.assign(r, { job: supplier.vendorJob(store.job(seg[1]), me) }));
  }
  // printer custom quotes (HQ asks printers to price a customer's custom quote; one-time submission)
  if (seg[0] === 'vendor' && seg[1] === 'custom-quotes') {
    const me = store.sessionCustomer(token); if (!me || me.type !== 'vendor') return send(res, 401, { error: 'vendor sign-in required' });
    const out = r => send(res, r && r.error ? (r.code || 400) : 200, r);
    if (!seg[2]) return out({ quotes: supplier.vendorCustomQuotes(me) });
    if (seg[3] === 'document') { const r = supplier.readCustomQuoteDoc(seg[2], me.vendorId || me.id, me); if (r.error) return out(r); res.writeHead(200, { 'Content-Type': r.type, 'Content-Disposition': 'attachment; filename="' + r.file.name.replace(/"/g, '') + '"', 'Cache-Control': 'private, no-store' }); return res.end(r.data); }
    if (req.method === 'POST') return out(supplier.submitCustomQuote(seg[2], me, await readBody(req)));
    return out(supplier.vendorCustomQuote(seg[2], me));
  }
  if (seg[0] === 'quotes' && seg[2] === 'printer-quotes') {
    const me = store.sessionCustomer(token); if (!me || ['admin', 'production'].indexOf(me.type) < 0) return send(res, 401, { error: 'staff sign-in required' });
    if (seg[3] && seg[4] === 'document') { const r = supplier.readCustomQuoteDoc(seg[1], seg[3], me); if (r.error) return send(res, r.code || 400, r); res.writeHead(200, { 'Content-Type': r.type, 'Content-Disposition': 'attachment; filename="' + r.file.name.replace(/"/g, '') + '"', 'Cache-Control': 'private, no-store' }); return res.end(r.data); }
    if (req.method === 'POST') { const r = supplier.requestPrinterQuotes(seg[1], await readBody(req), me.name || me.email); return send(res, r.error ? 400 : 200, r); }
    const q = store.quote(seg[1]); if (!q) return send(res, 404, { error: 'not found' });
    // opened by the scheduler → received printer quotes count as seen ("Quote Pending from Printer" done)
    if (q.printerQuotes) { let seen = false; q.printerQuotes.printers.forEach(p => { if (p.submittedAt && !p.seenAt) { p.seenAt = store.now(); seen = true; } }); if (seen) store.save(); }
    return send(res, 200, { printerQuotes: q.printerQuotes || null });
  }
  if (seg[0] === 'jobs' && seg[2] === 'award' && req.method === 'POST') {
    if (['production_director', 'scheduler_manager', 'scheduler_staff'].indexOf(role) < 0) return send(res, 403, { error: 'scheduler only' });
    const r = ops.award(seg[1], role, actor, await readBody(req));
    return r.error ? send(res, 400, r) : send(res, 200, { ok: true, job: jobView(r.job, role) });
  }
  // POST /api/vendor/jobs/:id/ship { courier, tracking } — the awarded printer ships with the Printoka label
  if (seg[0] === 'vendor' && seg[1] === 'jobs' && seg[3] === 'ship' && req.method === 'POST') {
    const vme = store.sessionCustomer(token); if (!vme || vme.type !== 'vendor') return send(res, 401, { error: 'vendor sign-in required' });
    const co = vme.vendorId || vme.id;
    const j0 = store.job(seg[2]); if (!j0 || !j0.outsource || j0.outsource.awardedTo !== co) return send(res, 403, { error: 'this job is not awarded to your company' });
    const b = await readBody(req); const r = ops.transition(seg[2], 'printer', vme.name, 'vendor_ship', { courier: b.courier, tracking: b.tracking });
    return r.error ? send(res, 400, r) : send(res, 200, { ok: true, job: store.job(seg[2]) });
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
  // never serve the server code, its data store (customers, sessions), dotfiles (.env), node_modules,
  // build scripts or source notes — only the public app files
  const relN = path.relative(WEB_ROOT, filePath).split(path.sep).join('/');
  if (/^(server|node_modules|private|src)(\/|$)/.test(relN) || relN.split('/').some(p => p.charAt(0) === '.') || /\.(md|mjs|sh|log|env|local|txt)$/i.test(relN) && !/^robots\.txt$/.test(relN) || /^content\/.*\.(json)$/.test(relN) || /(^|\/)_/.test(relN.replace(/^assets\/original\//, '')))
    return send(res, 404, 'Not found', 'text/plain');
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
