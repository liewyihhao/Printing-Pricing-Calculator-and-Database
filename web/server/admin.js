/*
 * Admin backoffice — the WordPress / WooCommerce admin features on the custom stack:
 *
 *   WooCommerce Orders   status (cancel), order notes (private / to customer), refunds (to wallet or
 *                        manual), edit billing / shipping, resend confirmation
 *   WooCommerce Coupons  create / edit / disable store-wide coupons (percent or fixed, min spend,
 *                        expiry, usage limits, per-customer limit, allowed emails)
 *   Customers / Users    edit profile, pin a membership tier, wallet credit / debit (TeraWallet),
 *                        disable, login-as-user (the "Login as User" plugin)
 *   Reports / Analytics  live revenue, orders, AOV, tiers, top products, channels, liabilities
 *   Settings             tax per country, shipping, payment methods, membership tiers — and the
 *                        checkout totals are re-checked against them on the server
 *   Content              posts (blog), FAQs, media uploads
 * Every change is written to the audit log with the admin's name.
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const store = require('./store');

const now = () => new Date().toISOString();
const r2 = n => Math.round(Number(n || 0) * 100) / 100;
const log = (actor, action, note, extra) => store.logEvent(Object.assign({ actor: actor || 'admin', role: 'admin', action, jobId: null, from: null, to: null, note }, extra || {}));

// ---------------------------------------------------------------- settings with defaults
const DEFAULT_TIERS = [
  { name: 'Standard', threshold: 0, pct: 0 }, { name: 'Bronze', threshold: 1000, pct: 5 }, { name: 'Silver', threshold: 3000, pct: 8 },
  { name: 'Gold', threshold: 5000, pct: 10 }, { name: 'Platinum', threshold: 10000, pct: 15 },
];
function commerce() {
  const s = store.settings();
  if (!s.tax) s.tax = { MY: { label: 'SST', rate: 8 }, SG: { label: 'GST', rate: 9 }, BN: { label: 'Tax', rate: 0 } };
  if (!s.shipping) s.shipping = { flat: 12, freeOver: 0, pickupDiscountPct: 0 };
  if (!s.payments) s.payments = { testMode: true, methods: {
    card_test: { enabled: true, label: 'Card (Stripe)' }, ipay88: { enabled: true, label: 'iPay88 · FPX / cards' }, tng: { enabled: true, label: "Touch 'n Go eWallet" },
    bank_transfer: { enabled: true, label: 'Bank transfer', bankName: 'Maybank', accountName: 'Yushan Corporation Sdn Bhd', accountNo: '' }, credit_term: { enabled: true, label: 'Credit terms (approved accounts)' } } };
  if (!s.membership) s.membership = { tiers: DEFAULT_TIERS.map(t => Object.assign({}, t)), windowMonths: 12 };
  if (!s.currency) s.currency = { MY: 1, SG: 0.31, BN: 0.31 }; // display rate from RM (Printoka Settings → Country)
  return s;
}
function tierPct(tier) { const t = commerce().membership.tiers.find(x => x.name === tier); return t ? Number(t.pct) || 0 : 0; }

// ---------------------------------------------------------------- store-wide coupons
function coupons() { const db = store.load(); if (!db.coupons) db.coupons = []; return db.coupons; }
function saveCoupon(b, actor) {
  const code = String(b.code || '').trim().toUpperCase();
  if (!/^[A-Z0-9_-]{3,30}$/.test(code)) return { error: 'Code must be 3–30 letters, numbers, - or _.' };
  const type = b.type === 'fixed' ? 'fixed' : 'percent';
  const amount = Number(b.amount);
  if (!(amount > 0) || (type === 'percent' && amount > 100)) return { error: 'Enter a valid discount amount.' };
  let c = b.id ? coupons().find(x => x.id === b.id) : null;
  if (!c && coupons().some(x => x.code === code)) return { error: 'That code already exists.' };
  if (!c) { c = { id: 'CP-' + crypto.randomBytes(3).toString('hex').toUpperCase(), usedCount: 0, usedBy: {}, createdAt: now(), createdBy: actor }; coupons().push(c); }
  Object.assign(c, { code, type, amount, description: String(b.description || '').slice(0, 200), minSpend: Number(b.minSpend) || 0, expires: b.expires || null,
    usageLimit: b.usageLimit ? Number(b.usageLimit) : null, perCustomer: b.perCustomer ? Number(b.perCustomer) : null,
    allowedEmails: String(b.allowedEmails || '').split(/[\s,;]+/).map(x => x.trim().toLowerCase()).filter(Boolean), status: b.status === 'disabled' ? 'disabled' : 'active', updatedAt: now() });
  log(actor, 'coupon_save', c.code + ' · ' + (type === 'percent' ? amount + '%' : 'RM ' + amount) + ' · ' + c.status);
  store.save(); return { coupon: c };
}
function deleteCoupon(id, actor) { const i = coupons().findIndex(x => x.id === id); if (i < 0) return { error: 'Coupon not found.' }; const c = coupons().splice(i, 1)[0]; log(actor, 'coupon_delete', c.code); store.save(); return { ok: true }; }
// personal (sign-up) codes first, then store-wide coupons
function checkAnyCoupon(userId, code, subtotal) {
  const r = store.checkCoupon(userId, code, subtotal);
  if (r.ok || !/isn’t valid on your account/.test(r.error || '')) return r;
  const want = String(code || '').trim().toUpperCase();
  const c = coupons().find(x => x.code === want); if (!c) return r;
  const u = userId && store.findCustomer(userId);
  if (!u) return { error: 'Sign in to use a discount code.' };
  if (c.status !== 'active') return { error: 'That code is no longer active.' };
  if (c.expires && new Date(c.expires + 'T23:59:59') < new Date()) return { error: 'That code has expired.' };
  if (c.usageLimit && c.usedCount >= c.usageLimit) return { error: 'That code has reached its usage limit.' };
  if (c.perCustomer && (c.usedBy[userId] || 0) >= c.perCustomer) return { error: 'You have already used this code.' };
  if (c.allowedEmails.length && c.allowedEmails.indexOf(String(u.email).toLowerCase()) < 0) return { error: 'That code isn’t valid on your account.' };
  const sub = Number(subtotal) || 0;
  if (sub < (c.minSpend || 0)) return { error: 'This code applies to orders of RM ' + c.minSpend + ' or more.', code: c.code, minSpend: c.minSpend, pct: c.type === 'percent' ? c.amount : 0, amount: c.type === 'fixed' ? c.amount : 0 };
  const discount = c.type === 'fixed' ? Math.min(c.amount, sub) : r2(sub * c.amount / 100);
  return { ok: true, code: c.code, pct: c.type === 'percent' ? c.amount : 0, amount: c.type === 'fixed' ? c.amount : 0, minSpend: c.minSpend || 0, discount, storeWide: true };
}
function recordCouponUse(code, userId) {
  const c = coupons().find(x => x.code === String(code || '').toUpperCase()); if (!c) return;
  c.usedCount = (c.usedCount || 0) + 1; if (userId) c.usedBy[userId] = (c.usedBy[userId] || 0) + 1; store.save();
}

// ---------------------------------------------------------------- checkout totals re-check
// The browser shows the totals, the server decides them: member discount from the ACCOUNT's
// tier (guests get none), tax from the configured rates, shipping from the configured fee.
function verifyTotals(body, user) {
  const s = commerce();
  const sub = r2(body.subtotal);
  const lines = r2((body.items || []).reduce((a, it) => a + (Number(it.lineTotal) || 0), 0));
  if (Math.abs(lines - sub) > 0.05) return { error: 'Your cart total doesn’t add up. Please refresh your cart and try again.' };
  const pct = user && user.type === 'customer' ? tierPct(user.tier || 'Standard') : 0;
  const md = r2(sub * pct / 100);
  if (Math.abs((Number(body.memberDiscount) || 0) - md) > 0.05) return { error: 'Your member discount has changed. Please refresh your cart and try again.', memberDiscount: md };
  const after = sub - md - (Number(body.couponDiscount) || 0);
  const rates = Object.keys(s.tax).map(k => Number(s.tax[k].rate) || 0);
  const taxOk = rates.some(rt => Math.abs(r2(after * rt / 100) - (Number(body.tax) || 0)) <= 0.05);
  if (!taxOk) return { error: 'Tax on your order has changed. Please refresh your cart and try again.' };
  const ship = Number(s.shipping.flat) || 0; const free = Number(s.shipping.freeOver) || 0;
  const expShip = (body.items || []).length ? (free && sub >= free ? 0 : ship) : 0;
  if (Math.abs((Number(body.shipping) || 0) - expShip) > 0.05) return { error: 'The delivery fee has changed. Please refresh your cart and try again.', shipping: expShip };
  const total = r2(after + (Number(body.tax) || 0) + expShip);
  if (Math.abs(total - (Number(body.total) || 0)) > 0.1) return { error: 'Your order total has changed. Please refresh your cart and try again.' };
  const m = (s.payments.methods || {})[(body.payment && body.payment.method) || 'bank_transfer'];
  if (m && m.enabled === false) return { error: 'That payment method is not available right now.' };
  return { ok: true, memberDiscount: md, shipping: expShip, total };
}

// ---------------------------------------------------------------- orders (WooCommerce order screen)
const SHIPPED = ['dispatched', 'at_hub', 'ready_collect', 'completed'];
function orderNote(oid, text, toCustomer, actor) {
  const o = store.order(oid); if (!o) return { error: 'Order not found.' };
  if (!String(text || '').trim()) return { error: 'Write a note first.' };
  o.notes = o.notes || [];
  o.notes.unshift({ id: 'NT-' + crypto.randomBytes(3).toString('hex').toUpperCase(), ts: now(), by: actor, text: String(text).slice(0, 2000), toCustomer: !!toCustomer });
  if (toCustomer && o.userId) store.notify({ type: 'customer', id: o.userId }, { kind: 'order_note', title: 'A note about your order ' + o.id, body: String(text).slice(0, 400), cta: 'View order →', orderId: o.id });
  if (toCustomer && o.customer && o.customer.email) store.sendEmail('order-confirmation', { to: o.customer.email, name: o.customer.name, subject: 'A note about your order ' + o.id, body: 'Hi ' + (o.customer.name || 'there') + ',\n\n' + text });
  log(actor, 'order_note', oid + (toCustomer ? ' (to customer)' : ' (private)'));
  store.save(); return { order: o };
}
function cancelOrder(oid, reason, actor) {
  const o = store.order(oid); if (!o) return { error: 'Order not found.' };
  const js = (o.jobIds || []).map(store.job).filter(Boolean);
  if (js.some(j => SHIPPED.indexOf(j.status) >= 0)) return { error: 'Part of this order has already shipped — refund instead of cancelling.' };
  js.forEach(j => { const from = j.status; j.status = 'cancelled'; j.cancelledAt = now(); j.statusAt = Object.assign(j.statusAt || {}, { cancelled: now() }); store.logEvent({ actor, role: 'admin', action: 'cancel', jobId: j.id, from, to: 'cancelled', note: reason || 'Order cancelled' }); });
  o.status = 'cancelled'; o.progress = 'cancelled'; o.progressLabel = 'Cancelled'; o.cancelledAt = now(); o.cancelReason = reason || '';
  if (o.userId) store.notify({ type: 'customer', id: o.userId }, { kind: 'order_cancelled', title: 'Order ' + o.id + ' was cancelled', body: reason ? 'Reason: ' + reason : 'Contact us if you have any questions.', orderId: o.id });
  log(actor, 'order_cancel', oid + (reason ? ' — ' + reason : ''));
  store.save(); return { order: o };
}
function refundOrder(oid, amount, method, reason, actor) {
  const o = store.order(oid); if (!o) return { error: 'Order not found.' };
  const refunded = (o.refunds || []).reduce((s, x) => s + x.amount, 0);
  amount = r2(amount);
  if (!(amount > 0)) return { error: 'Enter a refund amount.' };
  if (amount > r2((o.total || 0) + (o.creditApplied || 0) - refunded)) return { error: 'That is more than the amount left to refund.' };
  if (method === 'wallet') { if (!o.userId) return { error: 'Guest orders can only be refunded manually.' }; store.creditEntry(o.userId, { reason: 'REFUND', amount, actor, orderId: oid }); }
  o.refunds = o.refunds || [];
  o.refunds.push({ id: 'RF-' + crypto.randomBytes(3).toString('hex').toUpperCase(), ts: now(), amount, method: method === 'wallet' ? 'wallet' : 'manual', reason: reason || '', by: actor });
  o.refundedTotal = r2(refunded + amount);
  if (o.refundedTotal >= r2((o.total || 0) + (o.creditApplied || 0))) o.status = 'refunded';
  if (o.userId) store.notify({ type: 'customer', id: o.userId }, { kind: 'refund', title: 'Refund of RM ' + amount.toFixed(2) + ' for ' + o.id, body: (method === 'wallet' ? 'Added to your Printoka wallet.' : 'We’ll transfer it to you shortly.') + (reason ? ' Reason: ' + reason : ''), orderId: o.id });
  log(actor, 'order_refund', oid + ' RM ' + amount.toFixed(2) + ' (' + (method === 'wallet' ? 'wallet' : 'manual') + ')' + (reason ? ' — ' + reason : ''));
  store.save(); return { order: o };
}
function updateOrderAddress(oid, b, actor) {
  const o = store.order(oid); if (!o) return { error: 'Order not found.' };
  if (b.billing !== undefined) o.billing = b.billing;
  if (b.shipTo !== undefined) {
    const js = (o.jobIds || []).map(store.job).filter(Boolean);
    if (js.some(j => SHIPPED.indexOf(j.status) >= 0)) return { error: 'Already shipped — the delivery address can no longer change.' };
    o.shipTo = b.shipTo;
    js.forEach(j => { if (j.finalDestination && j.finalDestination.type === 'customer') { j.finalDestination.address = typeof b.shipTo === 'string' ? b.shipTo : [b.shipTo.line1, b.shipTo.postcode, b.shipTo.city, b.shipTo.state].filter(Boolean).join(', '); if (j.destination && j.destination.type === 'customer') j.destination.address = j.finalDestination.address; j.label = null; } });
  }
  log(actor, 'order_address', oid); store.save(); return { order: o };
}
function resendConfirmation(oid, actor) {
  const o = store.order(oid); if (!o) return { error: 'Order not found.' };
  if (!o.customer || !o.customer.email) return { error: 'This order has no customer email.' };
  store.sendEmail('order-confirmation', { to: o.customer.email, name: o.customer.name, subject: 'Order ' + o.id + ' confirmed', body: 'Hi ' + (o.customer.name || 'there') + ',\n\nHere is your order ' + o.id + ' again — total RM ' + (o.total || 0).toFixed(2) + '.\n\nTrack it anytime from your dashboard.' });
  log(actor, 'order_resend', oid); return { ok: true };
}

// ---------------------------------------------------------------- customers (WP users + TeraWallet + Login as User)
function updateCustomer(id, b, actor) {
  const c = store.customers().find(x => x.id === id && x.type === 'customer'); if (!c) return { error: 'Customer not found.' };
  const before = JSON.stringify({ name: c.name, phone: c.phone, company: c.company, tier: c.tier, pinned: c.tierPinned, disabled: c.disabled });
  ['name', 'phone', 'company'].forEach(k => { if (b[k] !== undefined) c[k] = String(b[k]); });
  if (b.email !== undefined) { const e = String(b.email).trim().toLowerCase(); if (!/.+@.+\..+/.test(e)) return { error: 'Enter a valid email.' }; if (store.customers().some(x => x.email === e && x.id !== id)) return { error: 'Another account uses that email.' }; c.email = e; }
  if (b.tier !== undefined) { if (!commerce().membership.tiers.some(t => t.name === b.tier)) return { error: 'Unknown tier.' }; c.tier = b.tier; c.tierPinned = b.tierPinned !== false; }
  if (b.creditTerms !== undefined) c.creditTerms = !!b.creditTerms;
  if (b.disabled !== undefined) c.disabled = !!b.disabled;
  log(actor, 'customer_edit', c.email + ' ' + before + ' → ' + JSON.stringify({ name: c.name, phone: c.phone, company: c.company, tier: c.tier, pinned: c.tierPinned, disabled: c.disabled }));
  store.save(); return { customer: store.publicCustomer(c) };
}
function walletAdjust(id, amount, note, actor) {
  const c = store.findCustomer(id); if (!c || c.type !== 'customer') return { error: 'Customer not found.' };
  amount = r2(amount); if (!amount) return { error: 'Enter an amount (negative to debit).' };
  if ((c.creditBalance || 0) + amount < 0) return { error: 'That would take the wallet below zero.' };
  const r = store.creditEntry(id, { reason: amount > 0 ? 'ADJUSTMENT' : 'DEBIT', amount, actor: actor + (note ? ' · ' + note : '') });
  return Object.assign({ customer: store.publicCustomer(store.findCustomer(id)) }, r);
}
function loginAs(id, actor) {
  const c = store.findCustomer(id); if (!c || c.type !== 'customer') return { error: 'Customer not found.' };
  const token = store.newSession(c.id);
  log(actor, 'login_as_user', 'Signed in as ' + c.email);
  return { token, customer: store.publicCustomer(c) };
}

// ---------------------------------------------------------------- reports / analytics (live)
function analytics(days) {
  days = Number(days) || 30; const DAY = 864e5, t0 = Date.now() - days * DAY, tp = t0 - days * DAY;
  const paid = store.orders().filter(o => o.payment && o.payment.status === 'validated' && o.status !== 'cancelled');
  const at = o => Date.parse(o.payment.paidAt || o.createdAt);
  const cur = paid.filter(o => at(o) >= t0), prev = paid.filter(o => at(o) >= tp && at(o) < t0);
  const sum = a => r2(a.reduce((s, o) => s + (o.total || 0) - (o.refundedTotal || 0), 0));
  const custs = store.customers().filter(c => c.type === 'customer');
  const tiers = {}; custs.forEach(c => { tiers[c.tier || 'Standard'] = (tiers[c.tier || 'Standard'] || 0) + 1; });
  const prod = {}; cur.forEach(o => (o.items || []).forEach(it => { prod[it.product] = r2((prod[it.product] || 0) + (it.lineTotal || 0)); }));
  const chan = {}; cur.forEach(o => { const k = o.channel || 'online'; chan[k] = chan[k] || { orders: 0, revenue: 0 }; chan[k].orders++; chan[k].revenue = r2(chan[k].revenue + (o.total || 0)); });
  const pending = store.orders().filter(o => o.payment && o.payment.status !== 'validated' && o.status !== 'cancelled');
  const quotes = store.quotes();
  return { days, revenue: sum(cur), revenuePrev: sum(prev), orders: cur.length, ordersPrev: prev.length, aov: cur.length ? r2(sum(cur) / cur.length) : 0,
    newCustomers: custs.filter(c => Date.parse(c.createdAt || 0) >= t0).length, customers: custs.length,
    tiers: commerce().membership.tiers.map(t => ({ name: t.name, count: tiers[t.name] || 0 })),
    topProducts: Object.keys(prod).map(k => ({ product: k, revenue: prod[k] })).sort((a, b) => b.revenue - a.revenue).slice(0, 8),
    channels: Object.keys(chan).map(k => Object.assign({ channel: k }, chan[k])),
    pendingPayments: { count: pending.length, value: r2(pending.reduce((s, o) => s + (o.total || 0), 0)) },
    walletLiability: r2(custs.reduce((s, c) => s + (c.creditBalance || 0), 0)),
    quotes: { open: quotes.filter(q => ['requested', 'issued', 'reviewed', 'amendment'].indexOf(q.status) >= 0).length, accepted: quotes.filter(q => q.status === 'accepted' && Date.parse(q.acceptedAt || q.createdAt || 0) >= t0).length },
    refunds: r2(store.orders().reduce((s, o) => s + (o.refunds || []).filter(x => Date.parse(x.ts) >= t0).reduce((a, x) => a + x.amount, 0), 0)) };
}

// ---------------------------------------------------------------- content: posts, FAQs, media
const CDIR = path.join(__dirname, '..', 'content');
const readJ = (f, d) => { try { return JSON.parse(fs.readFileSync(path.join(CDIR, f), 'utf8')); } catch (e) { return d; } };
const writeJ = (f, v) => fs.writeFileSync(path.join(CDIR, f), JSON.stringify(v, null, 1));
const slugify = s => String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 80);
function savePost(b, actor) {
  const posts = readJ('blog.json', []);
  if (!String(b.title || '').trim()) return { error: 'Give the post a title.' };
  let p = b.slug && b.originalSlug ? posts.find(x => x.slug === b.originalSlug) : null;
  const slug = slugify(b.slug || b.title);
  if (!p && posts.some(x => x.slug === slug)) return { error: 'A post with that URL already exists.' };
  if (!p) { p = { slug, date: new Date().toISOString().slice(0, 10) }; posts.unshift(p); }
  Object.assign(p, { slug, title: String(b.title), tag: b.tag || p.tag || 'Guides', excerpt: String(b.excerpt || '').slice(0, 400), body: b.body != null ? String(b.body) : p.body, status: b.status === 'draft' ? 'draft' : 'published', url: '/blog/' + slug + '/', updatedAt: now() });
  writeJ('blog.json', posts); log(actor, 'post_save', p.slug + ' (' + p.status + ')'); return { post: p };
}
function deletePost(slug, actor) { const posts = readJ('blog.json', []); const i = posts.findIndex(x => x.slug === slug); if (i < 0) return { error: 'Post not found.' }; posts.splice(i, 1); writeJ('blog.json', posts); log(actor, 'post_delete', slug); return { ok: true }; }
function saveFaq(b, actor) {
  const faq = readJ('faq.json', []);
  const cat = faq.find(c => c.id === b.catId); if (!cat) return { error: 'FAQ topic not found.' };
  if (!String(b.q || '').trim() || !String(b.a || '').trim()) return { error: 'Write both the question and the answer.' };
  if (b.index != null && cat.questions[b.index]) cat.questions[b.index] = { q: String(b.q), a: String(b.a) };
  else cat.questions.push({ q: String(b.q), a: String(b.a) });
  writeJ('faq.json', faq); log(actor, 'faq_save', cat.title + ': ' + String(b.q).slice(0, 60)); return { faq };
}
function deleteFaq(catId, index, actor) { const faq = readJ('faq.json', []); const cat = faq.find(c => c.id === catId); if (!cat || !cat.questions[index]) return { error: 'Question not found.' }; const q = cat.questions.splice(index, 1)[0]; writeJ('faq.json', faq); log(actor, 'faq_delete', q.q.slice(0, 60)); return { faq }; }
const MEDIA_OK = { png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', webp: 'image/webp', gif: 'image/gif', svg: 'image/svg+xml', pdf: 'application/pdf' };
function uploadMedia(b, actor) {
  const name = String(b.name || '').toLowerCase().replace(/[^a-z0-9._-]+/g, '-');
  const ext = (name.split('.').pop() || '');
  if (!MEDIA_OK[ext]) return { error: 'Only PNG, JPG, WEBP, GIF, SVG or PDF files.' };
  const m = String(b.data || '').match(/^data:[^;]+;base64,(.+)$/); if (!m) return { error: 'No file data.' };
  const buf = Buffer.from(m[1], 'base64'); if (buf.length > 8 * 1024 * 1024) return { error: 'Files must be 8 MB or smaller.' };
  const dir = path.join(__dirname, '..', 'assets', 'uploads'); fs.mkdirSync(dir, { recursive: true });
  const file = Date.now().toString(36) + '-' + name; fs.writeFileSync(path.join(dir, file), buf);
  log(actor, 'media_upload', file + ' (' + Math.round(buf.length / 1024) + ' KB)'); return { file: 'assets/uploads/' + file, name: file };
}
function deleteMedia(file, actor) {
  const f = String(file || ''); if (!/^assets\/uploads\/[a-z0-9._-]+$/.test(f)) return { error: 'Only uploaded files can be deleted.' };
  try { fs.unlinkSync(path.join(__dirname, '..', f)); } catch (e) { return { error: 'File not found.' }; }
  log(actor, 'media_delete', f); return { ok: true };
}

module.exports = { commerce, tierPct, coupons, saveCoupon, deleteCoupon, checkAnyCoupon, recordCouponUse, verifyTotals, orderNote, cancelOrder, refundOrder, updateOrderAddress, resendConfirmation, updateCustomer, walletAdjust, loginAs, analytics, savePost, deletePost, saveFaq, deleteFaq, uploadMedia, deleteMedia };
