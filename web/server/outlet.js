/*
 * Outlet system — rebuilt from the original printoka.com outlet account
 * (themes/printoka-child/includes/classes/account/outlet/* + printoka-quote-remarks).
 *
 * Custom quotes (per outlet, issued by a staff member):
 *   New quote (product · specifications · requester · artwork) → "Pending Quote" (awaiting HQ quote)
 *   HQ prices it (admin / scheduler) → "Quoted", remark "Issued", follow-up due in 7 days
 *   Outlet may adjust weight / price → "Quoted" again
 *   No follow-up for 7 days → remark "Not followed up" (staff reminded)
 *   Outlet: "Followed up" (next reminder in 3 days) or "Rejected" (reasons)
 *   Customer accepts → order; paid → remark "Billed"
 *   Progress: Quote Details (1/4) → Awaiting Response (2/4) → Follow-Up (3/4) → Accepted/Rejected/Unable (4/4)
 * Orders (the outlet's quote orders, its counter orders and pickups at the outlet):
 *   Pending payment → Payment Received / Bank Slip Received · Shipped to Outlet → Ready for Collect → Collected
 *   Progress: Draft → Pending payment → Payment received → Processing → Shipped (5 steps)
 * Performance: outlet sales by month + product table; individual (per staff) sales, orders, new
 * accounts, quotes issued, quotes followed up, sales conversion.
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const store = require('./store');

const now = () => new Date().toISOString();
const DAY = 864e5;
const r2 = n => Math.round(Number(n || 0) * 100) / 100;
let _ops = null; const ops = () => _ops || (_ops = require('./ops'));
let _files = null; const files = () => _files || (_files = require('./files'));

// ---------------------------------------------------------------- quotes
const outletOf = me => (me && me.outlet) || null;
const isManager = me => me && (me.role === 'outlet_manager' || me.type === 'admin');
function refreshFollowUp(q) {
  // the original 7-day / 3-day "lx_quote_no_follow_up" reminder, evaluated lazily
  if (['issued', 'reviewed'].indexOf(q.status) < 0) return false;
  if (q.remarks === 'Not followed up' || !q.followUpDueAt) return false;
  if (Date.now() < Date.parse(q.followUpDueAt)) return false;
  q.remarks = 'Not followed up'; q.history = q.history || [];
  q.history.push({ ts: now(), actor: 'system', action: 'Not followed up' });
  if (q.outlet) store.notify({ type: 'outlet', outlet: q.outlet }, { kind: 'quote_followup', title: 'Quote ' + q.id + ' needs a follow-up', body: 'No follow-up has been recorded for ' + ((q.customer && q.customer.name) || 'the customer') + '’s quote. Give them a call and record it.', quoteId: q.id });
  const staff = q.issuedBy && store.findCustomer(q.issuedBy.id);
  if (staff && staff.email) store.sendEmail('quote-issued', { to: staff.email, name: staff.name, subject: 'Quote ' + q.id + ' has not been followed up', body: 'Hi ' + staff.name + ',\n\nQuote ' + q.id + ' (' + ((q.requirement && q.requirement.product) || 'custom job') + ') has had no follow-up. Please contact the customer and record the follow-up in your outlet account.' });
  return true;
}
function statusOf(q) {
  if (q.status === 'accepted') return 'Accepted';
  if (q.status === 'rejected' || q.status === 'declined') return 'Rejected';
  if (q.status === 'unable') return 'Unable to quote';
  if (q.status === 'issued' || q.status === 'reviewed' || q.status === 'quoted') return q.remarks === 'Not followed up' ? 'Not followed up' : 'Quoted';
  return 'Pending Quote';
}
function stateOf(status) { return ({ 'Pending Quote': 'waiting-quote', Quoted: 'pending-response', 'Not followed up': 'follow-up', Accepted: 'accepted', Rejected: 'rejected', 'Unable to quote': 'unable-to-quote' })[status] || 'waiting-quote'; }
function progressOf(state) {
  return ({ 'pending-response': ['Awaiting Response - Step 2 of 4', 50], 'follow-up': ['Follow-Up - Step 3 of 4', 75], accepted: ['Accepted - Step 4 of 4', 100], rejected: ['Rejected - Step 4 of 4', 100], 'unable-to-quote': ['Unable to quote - Step 4 of 4', 100] })[state] || ['Quote Details - Step 1 of 4', 25];
}
function quoteView(q, full) {
  refreshFollowUp(q);
  const status = statusOf(q), state = stateOf(status), pg = progressOf(state);
  const v = { id: q.id, date: q.createdAt, product: (q.requirement && q.requirement.product) || '', status, state, progress: { text: pg[0], width: pg[1] },
    price: q.price, currency: q.currency || 'MYR', weight: q.weight || '', remarks: q.remarks || '', orderId: q.orderId || null, canEdit: ['accepted', 'rejected', 'declined', 'unable'].indexOf(q.status) < 0,
    issuedBy: q.issuedBy ? q.issuedBy.name : (q.requestedByStaff || ''), customerName: (q.customer && q.customer.name) || '' };
  if (!full) return v;
  const cust = q.userId ? store.findCustomer(q.userId) : null;
  const addr = cust && ((cust.addresses || []).find(a => a.isDefault) || (cust.addresses || [])[0]);
  return Object.assign(v, {
    spec: (q.requirement && (q.requirement.quoteData || [q.requirement.size, q.requirement.material, q.requirement.finishing, q.requirement.qty && ('Qty ' + q.requirement.qty), q.requirement.remarks].filter(Boolean).join('\n'))) || '',
    artwork: q.artwork || (q.artworkFile ? { name: q.artworkFile } : null),
    requester: cust ? { id: cust.id, name: cust.name, email: cust.email, phone: cust.phone || (addr && addr.phone) || '', address: addr ? [addr.line1, addr.line2, [addr.postcode, addr.city].filter(Boolean).join(' '), addr.state, addr.country].filter(Boolean).join(', ') : '' } : (q.customer ? { name: q.customer.name, email: q.customer.email, phone: q.customer.phone } : null),
    rejectReason: q.rejectReason || '', lastFollowUp: q.lastFollowUpAt ? { at: q.lastFollowUpAt, by: q.lastFollowUpBy } : null,
    // HQ's raw 'issued' entry is shown once, as the outlet's "Quoted"
    statuses: (q.history || []).filter(h => h.action !== 'issued').slice().reverse().map(h => ({ status: String(h.action).charAt(0).toUpperCase() + String(h.action).slice(1), by: h.actor, at: h.ts, note: h.note || '' })),
  });
}
function canQuote(q, me) { return q && me && (me.type === 'admin' || (me.type === 'outlet' && q.outlet && q.outlet === outletOf(me))); }
function listQuotes(me) { const o = outletOf(me); const l = store.quotes().filter(q => q.outlet && (me.type === 'admin' || q.outlet === o)); const ch = l.map(q => refreshFollowUp(q)).some(Boolean); if (ch) store.save(); return l.slice().sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt))).map(q => quoteView(q)); }
function getQuote(qid, me) { const q = store.quote(qid); if (!canQuote(q, me)) return { error: 'Access denied: You are not authorized to view this.' }; const v = quoteView(q, true); store.save(); return { quote: v }; }
const QROOT = path.join(__dirname, '..', '..', 'private-files', 'quotes');
function saveQuoteArtwork(q, b, me) {
  if (!b.artworkData) return null;
  const name = String(b.artworkFileName || b.artworkName || 'artwork').replace(/[\\/:*?"<>|\u0000-\u001f]+/g, '-').slice(0, 120);
  const m = String(b.artworkData).match(/^data:[^;]*;base64,(.+)$/); if (!m) return null;
  const buf = Buffer.from(m[1], 'base64'); if (buf.length > 60 * 1024 * 1024) return { error: 'Artwork must be 60 MB or smaller.' };
  const dir = path.join(QROOT, q.id); fs.mkdirSync(dir, { recursive: true });
  const id = 'F' + crypto.randomBytes(5).toString('hex').toUpperCase(); fs.writeFileSync(path.join(dir, id + '-' + name), buf);
  q.artwork = { id, name: b.artworkName || name, file: name, stored: id + '-' + name, size: buf.length, at: now(), by: me.name };
  return q.artwork;
}
function saveSpec(qid, b, me) {
  if (!me || me.type !== 'outlet') return { error: 'Outlet sign-in required.' };
  if (!String(b.product || '').trim() || !String(b.specifications || '').trim() || !b.requesterId) return { error: 'Please fill in the required field.' };
  const cust = store.findCustomer(b.requesterId); if (!cust || cust.type !== 'customer') return { error: 'Choose the requester (customer account).' };
  let q;
  if (!qid) {
    q = { id: 'Q-' + crypto.randomBytes(3).toString('hex').toUpperCase(), channel: 'outlet', outlet: outletOf(me), issuedBy: { id: me.id, name: me.name }, requestedByStaff: me.name,
      status: 'requested', remarks: 'Issued', price: null, currency: 'MYR', weight: '', orderId: null, createdAt: now(), history: [{ ts: now(), actor: me.name, action: 'Pending Quote', note: 'Created at ' + (outletOf(me) || 'outlet') }] };
    store.quotes().push(q);
    store.notify({ type: 'role', role: 'scheduler' }, { kind: 'quote_request', title: 'New outlet quote to price', body: 'Outlet ' + (outletOf(me) || '') + ' requested a quote for ' + b.product + ' (' + cust.name + ').', cta: 'Price this quote →', quoteId: q.id });
    store.sendEmail('request-quote-printer', { to: 'print@printoka.com', name: 'Printoka HQ', subject: 'Outlet quote request — ' + b.product, body: 'Outlet ' + (outletOf(me) || '') + ' (' + me.name + ') requested a custom quote.\nProduct: ' + b.product + '\nRequester: ' + cust.name + '\nQuote: ' + q.id });
  } else {
    q = store.quote(qid); if (!canQuote(q, me)) return { error: 'Access denied: You are not authorized to view this.' };
    if (!quoteView(q).canEdit) return { error: 'This quote can no longer be edited.' };
    q.history.push({ ts: now(), actor: me.name, action: 'Specifications updated' });
  }
  q.userId = cust.id; q.customer = { name: cust.name, email: cust.email, phone: cust.phone || '', company: cust.company || '' };
  q.requirement = Object.assign({}, q.requirement, { product: String(b.product), quoteData: String(b.specifications), qty: 1 });
  const aw = saveQuoteArtwork(q, b, me); if (aw && aw.error) return aw;
  store.logEvent({ actor: me.name, role: 'outlet', action: qid ? 'quote_spec' : 'quote_create', jobId: null, from: null, to: null, note: q.id + ' · ' + b.product });
  store.save(); return { quote: quoteView(q, true) };
}
// HQ priced / re-priced: start the 7-day follow-up clock
function onIssued(q) { if (!q) return; q.remarks = 'Issued'; q.followUpDueAt = new Date(Date.now() + 7 * DAY).toISOString(); q.history.push({ ts: now(), actor: 'HQ', action: 'Quoted', note: 'RM ' + q.price }); store.save(); }
function outletPrice(qid, b, me) {
  const q = store.quote(qid); if (!canQuote(q, me)) return { error: 'Access denied: You are not authorized to view this.' };
  if (!b.weight || !b.price) return { error: 'Please fill in the required field.' };
  const price = r2(b.price); if (!(price > 0)) return { error: 'Enter a valid price.' };
  const old = q.price; q.weight = String(b.weight); q.currency = b.currency || q.currency || 'MYR';
  if (old == null || r2(old) !== price) { q.price = price; q.history.push({ ts: now(), actor: me.name, action: 'Amount changed', note: 'to ' + q.currency + ' ' + price.toFixed(2) }); }
  q.status = 'issued'; q.issuedAt = q.issuedAt || now(); q.remarks = 'Issued'; q.lastFollowUpAt = null; q.followUpDueAt = new Date(Date.now() + 7 * DAY).toISOString();
  q.history.push({ ts: now(), actor: me.name, action: 'Quoted' });
  if (q.userId) store.notify({ type: 'customer', id: q.userId }, { kind: 'quote_issued', title: 'Your quote is ready', body: 'Quote ' + q.id + ' for ' + q.requirement.product + ': RM ' + q.price.toFixed(2) + '.', cta: 'View your quote →', quoteId: q.id });
  store.save(); return { quote: quoteView(q, true) };
}
function followUp(qid, me) {
  const q = store.quote(qid); if (!canQuote(q, me)) return { error: 'Access denied: You are not authorized to view this.' };
  q.remarks = 'Followed up'; q.lastFollowUpAt = now(); q.lastFollowUpBy = me.name; q.followUpDueAt = new Date(Date.now() + 3 * DAY).toISOString();
  q.followups = q.followups || []; q.followups.push({ staffId: me.id, staff: me.name, at: now() });
  q.history.push({ ts: now(), actor: me.name, action: 'Followed up' });
  store.save(); return { quote: quoteView(q, true) };
}
function rejectQuote(qid, reasons, me) {
  const q = store.quote(qid); if (!canQuote(q, me)) return { error: 'Access denied: You are not authorized to view this.' };
  if (!String(reasons || '').trim()) return { error: 'Please fill in the required field.' };
  q.status = 'rejected'; q.remarks = 'Rejected'; q.rejectReason = String(reasons); q.history.push({ ts: now(), actor: me.name, action: 'Rejected', note: String(reasons).slice(0, 200) });
  store.save(); return { quote: quoteView(q, true) };
}
function quoteArtwork(qid, me) {
  const q = store.quote(qid); if (!q || !(canQuote(q, me) || (me && me.type !== 'customer') || (me && q.userId === me.id))) return { error: 'Not allowed.' };
  if (!q.artwork || !q.artwork.stored) return { error: 'No artwork file.' };
  const p = path.join(QROOT, q.id, q.artwork.stored); if (!fs.existsSync(p)) return { error: 'File missing.' };
  return { name: q.artwork.file || q.artwork.name, data: fs.readFileSync(p) };
}
// quote accepted → the order carries the quote's artwork as a real file
function onAccepted(q, o) {
  if (!q || !o) return;
  if (q.artwork && q.artwork.stored) {
    const src = path.join(QROOT, q.id, q.artwork.stored);
    if (fs.existsSync(src)) {
      const dir = path.join(__dirname, '..', '..', 'private-files', 'orders', o.id); fs.mkdirSync(dir, { recursive: true });
      const id = 'F' + crypto.randomBytes(5).toString('hex').toUpperCase(), stored = id + '-' + q.artwork.file;
      fs.copyFileSync(src, path.join(dir, stored));
      o.files = o.files || []; o.files.push({ id, name: q.artwork.file, stored, size: q.artwork.size, kind: 'artwork', line: 1, at: now(), by: 'quote ' + q.id });
      const it = (o.items || [])[0]; if (it) it.artworks = [q.artwork.file];
      const j = store.job((o.jobIds || [])[0]); if (j) j.artwork = Object.assign({}, j.artwork, { file: q.artwork.file, fileId: id, checkStatus: 'pending' });
    }
  }
  o.fromQuote = q.id; o.outlet = q.outlet || o.outlet || null; o.issuedBy = q.issuedBy || null; o.orderType = 'custom-quote';
  store.save();
}
function onPaid(o) { if (!o || !o.fromQuote) return; const q = store.quote(o.fromQuote); if (q && q.remarks !== 'Billed') { q.remarks = 'Billed'; q.history.push({ ts: now(), actor: 'system', action: 'Billed', note: o.id }); store.save(); } }

// ---------------------------------------------------------------- orders
const PAID = o => o.payment && o.payment.status === 'validated';
function outletOrders(me) {
  const oid = outletOf(me);
  const fromQuotes = {}; store.quotes().forEach(q => { if (q.orderId && (me.type === 'admin' || q.outlet === oid)) fromQuotes[q.orderId] = q; });
  return store.orders().filter(o => fromQuotes[o.id] || (o.outlet && o.outlet === oid) || (o.fulfillment && o.fulfillment.method === 'pickup' && o.fulfillment.outlet === oid) || (me.type === 'admin' && (o.outlet || fromQuotes[o.id])))
    .map(o => { if (fromQuotes[o.id] && !o.fromQuote) { o.fromQuote = fromQuotes[o.id].id; o.outlet = fromQuotes[o.id].outlet; o.issuedBy = fromQuotes[o.id].issuedBy || null; } return o; });
}
// the order status the outlet sees (WooCommerce-style label), from the live jobs
function orderStatus(o) {
  const js = (o.jobIds || []).map(store.job).filter(Boolean); const st = js.map(j => j.status); const any = a => st.some(s => a.indexOf(s) >= 0); const all = a => st.length && st.every(s => a.indexOf(s) >= 0);
  const toOutlet = j => j.status === 'dispatched' && j.destination && j.destination.type === 'outlet';
  const toHub = j => j.status === 'dispatched' && j.destination && j.destination.type === 'hub';
  if (o.status === 'cancelled') return ['cancelled', 'Cancelled'];
  if (o.status === 'refunded') return ['refunded', 'Refunded'];
  if (!PAID(o)) return (o.payment && o.payment.proof) ? ['pending', 'Pending Payment (slip uploaded)'] : ['pending', 'Pending Payment'];
  if (any(['rejected'])) return ['issues-found', 'Issues Found'];
  if (js.some(j => j.artwork && /^pending-upload/.test(j.artwork.file || ''))) return ['pending-artwork', 'Pending Artwork'];
  if (all(['completed'])) return js.some(j => (j.statusAt || {}).ready_collect) ? ['collected', 'Collected'] : ['completed', 'Completed'];
  if (all(['ready_collect', 'completed'])) return ['ready-for-collect', 'Ready for Collect'];
  if (js.some(toOutlet)) return ['shipped-to-outlet', 'Shipped to Outlet'];
  if (any(['at_hub'])) return ['hub-arrived', 'Arrived at Hub'];
  if (js.some(toHub)) return ['hub-shipped', 'Shipped to Hub'];
  if (all(['dispatched', 'completed', 'ready_collect'])) return ['shipped', 'Shipped'];
  if (any(['scheduling', 'printing', 'outsourcing', 'logistics', 'dispatched'])) return ['processing', 'Processing'];
  return ['payment-received', 'Payment Received'];
}
const STAGES = ['draft', 'pending_payment', 'payment_received', 'processing', 'shipped'];
const STAGE_OF = { pending: 1, 'pending-artwork': 2, 'issues-found': 2, 'payment-received': 2, processing: 3, 'hub-shipped': 4, 'hub-arrived': 4, shipped: 4, 'shipped-to-outlet': 4, 'ready-for-collect': 4, collected: 4, completed: 4, cancelled: 1, refunded: 4 };
function nextActions(o, key) {
  if (key === 'pending') { const a = ['payment-received']; if ((o.payment && o.payment.method) === 'bank_transfer') a.push('bank-slip-receive'); return a; }
  if (key === 'shipped-to-outlet') return ['ready-for-collect'];
  if (key === 'ready-for-collect') return ['collected'];
  return [];
}
const ACTION_LABEL = { 'payment-received': 'Payment Received', 'bank-slip-receive': 'Bank Slip Received', 'ready-for-collect': 'Ready for Collect', collected: 'Collected' };
function orderListView(o) { const s = orderStatus(o); return { id: o.id, date: o.createdAt, status: s[1], statusKey: s[0], customer: (o.customer && o.customer.name) || '', total: o.total, fromQuote: o.fromQuote || null, pickup: !!(o.fulfillment && o.fulfillment.method === 'pickup') }; }
function canOrder(o, me) { return !!o && (me.type === 'admin' || outletOrders(me).some(x => x.id === o.id)); }
function orderDetail(oid, me) {
  const o = store.order(oid); if (!canOrder(o, me)) return { error: 'Access denied: You are not authorized to view this.' };
  const s = orderStatus(o), stage = STAGE_OF[s[0]] != null ? STAGE_OF[s[0]] : 2;
  const js = (o.jobIds || []).map(store.job).filter(Boolean);
  const shipped = js.map(j => (j.shipments || []).slice(-1)[0]).filter(Boolean);
  const log = [];
  (o.notes || []).forEach(n => log.push({ title: n.toCustomer ? 'Note to customer' : 'Note', text: n.text, by: n.by, at: n.ts }));
  if (o.createdAt) log.push({ title: 'Order placed', text: (o.channel || 'online') + ' · ' + ((o.payment && (o.payment.gateway || o.payment.method)) || ''), by: 'system', at: o.createdAt });
  if (o.payment && o.payment.paidAt) log.push({ title: 'Payment Received', text: o.payment.reference ? 'Ref ' + o.payment.reference : '', by: o.payment.validatedBy || 'system', at: o.payment.paidAt });
  js.forEach(j => store.audit({ jobId: j.id }).forEach(e => { if (e.to) log.push({ title: (require('./domain').STATUS[e.to] || {}).label || e.to, text: j.product + (e.note ? ' — ' + e.note : ''), by: e.actor, at: e.ts }); }));
  log.sort((a, b) => String(b.at).localeCompare(String(a.at)));
  const issues = js.filter(j => j.status === 'rejected').map(j => j.product + ': ' + (j.reason || 'artwork issue'));
  return { order: Object.assign(store.orderView(oid), {
    outletStatus: s[1], outletStatusKey: s[0],
    progress: { text: s[1] + ' - Step ' + (stage + 1) + ' of ' + STAGES.length, width: Math.round((stage + 1) / STAGES.length * 100) },
    nextActions: nextActions(o, s[0]).map(k => ({ key: k, label: ACTION_LABEL[k] })),
    statusLog: log, issues, delivery: shipped.length ? shipped.map(sh => ({ courier: sh.courier, tracking: sh.tracking, to: sh.to && sh.to.name })) : null,
    canInvoice: PAID(o) }) };
}
function orderAction(oid, action, me) {
  const o = store.order(oid); if (!canOrder(o, me)) return { error: 'Access denied: You are not authorized to view this.' };
  const s = orderStatus(o)[0]; if (nextActions(o, s).indexOf(action) < 0) return { error: 'That status change is not available for this order now.' };
  const who = me.name || me.email;
  if (action === 'payment-received' || action === 'bank-slip-receive') {
    const r = store.validateOrderPayment(oid, who); if (r.error) return r;
    o.payment.validatedBy = who; if (action === 'bank-slip-receive') o.payment.bankSlipReceived = true;
    (o.jobIds || []).forEach(jid => { const j = store.job(jid); if (j) { ops().normalizeJob(j); j.statusAt = Object.assign(j.statusAt || {}, { [j.status]: now() }); } });
    onPaid(o);
  } else {
    const role = require('./domain').opsRoleFor(me);
    const act = action === 'ready-for-collect' ? 'receive_outlet' : 'collect';
    const from = action === 'ready-for-collect' ? 'dispatched' : 'ready_collect';
    const errs = []; (o.jobIds || []).forEach(jid => { const j = store.job(jid); if (j && j.status === from) { const r = ops().transition(jid, role, who, act, {}); if (r.error) errs.push(r.error); } });
    if (errs.length) return { error: errs[0] };
  }
  ops().syncOrder(oid); store.save();
  return orderDetail(oid, me);
}
function orderNote(oid, text, me) {
  const o = store.order(oid); if (!canOrder(o, me)) return { error: 'Access denied: You are not authorized to view this.' };
  if (!String(text || '').trim()) return { error: 'Write a note first.' };
  o.notes = o.notes || []; o.notes.unshift({ id: 'NT-' + crypto.randomBytes(3).toString('hex').toUpperCase(), ts: now(), by: me.name, text: 'Note: ' + String(text).slice(0, 2000), toCustomer: false });
  store.save(); return orderDetail(oid, me);
}
function orderAddress(oid, b, me) {
  const o = store.order(oid); if (!canOrder(o, me)) return { error: 'Access denied: You are not authorized to view this.' };
  const r = require('./admin').updateOrderAddress(oid, { shipTo: { name: b.name, phone: b.phone, line1: b.line1, line2: b.line2, postcode: b.postcode, city: b.city, state: b.state, country: b.country || 'MY' } }, me.name);
  if (r.error) return r; return orderDetail(oid, me);
}

// ---------------------------------------------------------------- dashboard + performance
function dashboard(me) {
  const qs = listQuotes(me), os = outletOrders(me).map(orderListView);
  return { followUp: qs.filter(q => q.status === 'Not followed up').length,
    orders: os.filter(o => ['pending', 'pending-artwork', 'issues-found'].indexOf(o.statusKey) >= 0).length,
    incoming: os.filter(o => o.statusKey === 'shipped-to-outlet').length,
    delivery: os.filter(o => o.statusKey === 'ready-for-collect').length };
}
function months24() { const out = []; const d = new Date(); d.setDate(1); d.setHours(0, 0, 0, 0); for (let i = 23; i >= 0; i--) { const m = new Date(d.getFullYear(), d.getMonth() - i, 1); out.push({ key: m.getFullYear() + '-' + String(m.getMonth() + 1).padStart(2, '0'), label: m.toLocaleString('en', { month: 'short' }) + ' ' + m.getFullYear() }); } return out; }
const ym = ts => { const d = new Date(ts); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0'); };
function staffList(me) {
  if (!isManager(me)) return [];
  return store.customers().filter(c => c.type === 'outlet' && c.outlet === outletOf(me)).map(c => ({ id: c.id, name: c.name, role: c.role }));
}
function performance(me, individual, staffId) {
  const M = months24(); const blank = () => { const o = {}; M.forEach(m => { o[m.key] = 0; }); return o; };
  let who = null;
  if (individual) {
    who = me.id;
    if (staffId && staffId !== me.id) { if (!staffList(me).some(s => s.id === staffId)) return { error: 'You can only view your own outlet’s staff.' }; who = staffId; }
  }
  const qs = store.quotes().filter(q => q.outlet === outletOf(me) && (!individual || (q.issuedBy && q.issuedBy.id === who)));
  const qOrders = {}; qs.forEach(q => { if (q.orderId) qOrders[q.orderId] = q; });
  const orders = individual ? store.orders().filter(o => qOrders[o.id]) : outletOrders(me);
  const paid = orders.filter(o => PAID(o) && o.status !== 'cancelled');
  const sales = blank(), byProduct = {}, ordersCount = blank();
  paid.forEach(o => { const k = ym(o.payment.paidAt || o.createdAt); if (sales[k] == null) return; (o.items || []).forEach(it => { const n = String(it.product || 'Other').replace(/^Custom Quote:\s*/, ''); sales[k] = r2(sales[k] + (it.lineTotal || 0)); byProduct[n] = byProduct[n] || blank(); byProduct[n][k] = r2(byProduct[n][k] + (it.lineTotal || 0)); }); });
  orders.forEach(o => { const k = ym(o.createdAt); if (ordersCount[k] != null) ordersCount[k]++; });
  const out = { months: M, sales, byProduct };
  if (individual) {
    const quotesIssued = blank(), conv = {}, paidQ = blank(), followed = blank(), newAcc = blank();
    qs.forEach(q => { const k = ym(q.createdAt); if (quotesIssued[k] != null) quotesIssued[k]++; const o = q.orderId && store.order(q.orderId); if (o && PAID(o) && paidQ[k] != null) paidQ[k]++; });
    M.forEach(m => { conv[m.key] = quotesIssued[m.key] ? Math.round(paidQ[m.key] / quotesIssued[m.key] * 100) : null; });
    store.quotes().forEach(q => (q.followups || []).forEach(f => { if (f.staffId === who) { const k = ym(f.at); if (followed[k] != null) followed[k]++; } }));
    store.customers().forEach(c => { if (c.createdByStaffId === who) { const k = ym(c.createdAt); if (newAcc[k] != null) newAcc[k]++; } });
    Object.assign(out, { orders: ordersCount, quotesIssued, conversion: conv, quotesFollowedUp: followed, newAccounts: newAcc, staff: (store.findCustomer(who) || {}).name });
  }
  return { performance: out };
}
function searchCustomers(q) {
  const s = String(q || '').toLowerCase();
  return store.customers().filter(c => c.type === 'customer' && (!s || [c.name, c.email, c.phone].join(' ').toLowerCase().indexOf(s) >= 0)).slice(0, 20).map(c => ({ value: c.id, label: c.name + ' (' + c.email + ')' }));
}

module.exports = { listQuotes, getQuote, saveSpec, onIssued, outletPrice, followUp, rejectQuote, quoteArtwork, onAccepted, onPaid, outletOrders, orderListView, orderDetail, orderAction, orderNote, orderAddress, dashboard, performance, staffList, searchCustomers, refreshFollowUp };
