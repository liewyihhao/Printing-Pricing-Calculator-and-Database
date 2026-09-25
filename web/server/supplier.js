/*
 * Printers & hubs — rebuilt from the original printoka-3rd-party-supplier plugin
 * (class-lx-printing-job-statuses.php, dashboard/class-ajax.php, views/card/*.pug).
 *
 * Printing-job status (per outsourced job, the original 9):
 *   Quote requested → Quote partly received → Quotes received → Printer assigned
 *   → Draft Pending Approval (printer uploads a draft) → Draft approved (HQ approves)
 *   → Shipped to hub (printer) → Shipped (hub enters delivery details) → Paid (HQ paid the printer)
 * Printer cards: Request Quote (amount + document) · Upload Draft · Quote · Job Status ("Shipped to hub")
 * Hub card: Delivery Details (tracking numbers, delivery company, delivery order) → Shipped
 * Printer custom quotes: HQ asks printers to price a customer's custom quote; one-time submission
 * of weight (kg), amount (RM) and a quote document.
 * Documents: Purchase Order + Hub Label (printer, once assigned), Shipping Label (hub).
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const store = require('./store');

const now = () => new Date().toISOString();
let _ops = null; const ops = () => _ops || (_ops = require('./ops'));
const ROOT = path.join(__dirname, '..', '..', 'private-files', 'jobs');
const QROOT = path.join(__dirname, '..', '..', 'private-files', 'quotes');
const safe = n => String(n || 'file').replace(/[\\/:*?"<>|\u0000-\u001f]+/g, '-').replace(/\s+/g, ' ').trim().slice(0, 120) || 'file';
const MIME = { pdf: 'application/pdf', jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp', svg: 'image/svg+xml', zip: 'application/zip' };

// ---------------------------------------------------------------- the original 9 statuses
const STATUSES = {
  'quote-requested': { label: 'Quote requested', color: '#0073AA', icon: 'file-text' },
  'quote-partly-received': { label: 'Quote partly received', color: '#00A0D2', icon: 'clipboard' },
  'quotes-received': { label: 'Quotes received', color: '#00B9EB', icon: 'check' },
  'printer-assigned': { label: 'Printer assigned', color: '#00C2B2', icon: 'printer' },
  'draft-pending-approval': { label: 'Draft Pending Approval', color: '#00A0D2', icon: 'clipboard' },
  'draft-approved': { label: 'Draft approved', color: '#00C2B2', icon: 'check' },
  'shipped-to-hub': { label: 'Shipped to production', color: '#009D9A', icon: 'truck' },
  shipped: { label: 'Shipped', color: '#005082', icon: 'box' },
  paid: { label: 'Paid', color: '#67A2B2', icon: 'dollar-sign' },
};
const ORDER = Object.keys(STATUSES);
function printingStatus(j) {
  const o = j && j.outsource; if (!o) return null;
  if (o.paidAt) return 'paid';
  if (!o.awardedTo) return o.status === 'quotes_received' ? 'quotes-received' : o.status === 'partly_received' ? 'quote-partly-received' : 'quote-requested';
  if (j.status === 'outsourcing') { const d = o.draft; if (d && d.approvedAt) return 'draft-approved'; if (d && d.file && !d.rejectedAt) return 'draft-pending-approval'; return 'printer-assigned'; }
  // with production: the printer delivered, logistics is receiving / repacking it
  if (['inbound', 'logistics', 'at_hub'].indexOf(j.status) >= 0) return 'shipped-to-hub';
  if (j.status === 'dispatched' && (j.destination || {}).type === 'hub') return 'shipped-to-hub';
  return 'shipped';
}
const statusInfo = slug => slug ? Object.assign({ id: slug, step: ORDER.indexOf(slug) + 1, of: ORDER.length }, STATUSES[slug]) : null;
// a printer that quoted but lost the job only sees that it went elsewhere
const LOST = { id: 'not-awarded', label: 'Awarded to another printer', color: '#8a9199', icon: 'x', step: 4, of: ORDER.length };
function statusFor(j, me) { const co = coOf(me); const o = j.outsource || {}; if (co && o.awardedTo && o.awardedTo !== co) return LOST; return statusInfo(printingStatus(j)); }

// ---------------------------------------------------------------- files (drafts, quote documents, delivery orders)
function saveBlob(dir, b, prefix) {
  const m = String(b.data || '').match(/^data:[^;]*;base64,(.+)$/); if (!m) return { error: 'No file received.' };
  const buf = Buffer.from(m[1], 'base64'); if (buf.length > 60 * 1024 * 1024) return { error: 'File is larger than 60 MB.' };
  const name = safe(b.name); const id = (prefix || 'F') + crypto.randomBytes(5).toString('hex').toUpperCase();
  fs.mkdirSync(dir, { recursive: true }); fs.writeFileSync(path.join(dir, id + '-' + name), buf);
  return { id, name, stored: id + '-' + name, size: buf.length, at: now() };
}
function jobFiles(j) { const out = []; const o = j.outsource || {};
  (o.vendors || []).forEach(v => { if (v.document) out.push(Object.assign({ kind: 'quote', vendorId: v.vendorId }, v.document)); });
  (o.draftHistory || []).concat(o.draft && o.draft.file ? [o.draft.file] : []).forEach(f => out.push(Object.assign({ kind: 'draft', vendorId: o.awardedTo }, f)));
  if (j.hubDelivery && j.hubDelivery.document) out.push(Object.assign({ kind: 'delivery-order' }, j.hubDelivery.document));
  if (j.dispatchDelivery && j.dispatchDelivery.document) out.push(Object.assign({ kind: 'dispatch-order' }, j.dispatchDelivery.document));
  (j.proofs || []).forEach(f => out.push(Object.assign({ kind: 'proof' }, f)));
  return out; }
// prepress rejection proof (§2.7: attach a visual proof — screenshot)
function saveProof(jid, me, b) {
  const j = store.job(jid); if (!j) return { error: 'Job not found.' };
  if (!/\.(png|jpe?g|webp|pdf)$/i.test(String(b.name || ''))) return { error: 'The proof must be a screenshot (PNG / JPG) or a PDF.' };
  const f = saveBlob(path.join(ROOT, jid), b, 'R'); if (f.error) return f;
  f.by = me.name; j.proofs = j.proofs || []; j.proofs.push(f); store.save();
  return { file: { id: f.id, name: f.name } };
}
function readJobFile(j, fid, me) {
  const f = jobFiles(j).find(x => x.id === fid); if (!f) return { error: 'File not found.', code: 404 };
  if (me.type === 'vendor') { const co = me.vendorId || me.id; if (f.vendorId !== co) return { error: 'Not allowed.', code: 403 }; }
  if (me.type === 'hub' && f.kind !== 'delivery-order') return { error: 'Not allowed.', code: 403 };
  const p = path.join(ROOT, j.id, f.stored); if (!p.startsWith(ROOT) || !fs.existsSync(p)) return { error: 'File missing on disk.', code: 404 };
  return { file: f, data: fs.readFileSync(p), type: MIME[(f.name.split('.').pop() || '').toLowerCase()] || 'application/octet-stream' };
}

// ---------------------------------------------------------------- what each account may see of a job
const coOf = me => me && me.type === 'vendor' ? (me.vendorId || me.id) : null;
function vendorCanSee(j, me) { const co = coOf(me); return !!(co && j.outsource && (j.outsource.vendors || []).some(v => v.vendorId === co)); }
function hubCanSee(j, me) { return !me.hub || j.hub === me.hub || ((j.destination || {}).type === 'hub' && j.destination.id === me.hub) || (j.shipments || []).some(s => s.to && s.to.type === 'hub' && s.to.id === me.hub); }
function canSee(j, me) { if (!j || !me) return false; if (me.type === 'vendor') return vendorCanSee(j, me); if (me.type === 'hub') return hubCanSee(j, me); return me.type !== 'customer'; }
function hubDetails(j, hubId) { const cfg = ops().config(); const hb = (cfg.hubs || []).find(x => x.id === (hubId || j.hub)); return hb ? { id: hb.id, name: hb.name, address: hb.address || '', phone: hb.phone || '' } : null; }
// where the printer delivers: production (logistics receives) or the outlet (legacy: a hub)
function deliverTo(j) {
  const d = j.destination || {};
  if (d.type === 'production' || d.type === 'outlet') { const o = d.type === 'outlet' ? ops().outletById(d.id) : null; return { type: d.type, name: d.name, address: d.address || (o && o.address) || '', phone: d.phone || '' }; }
  if (d.type === 'hub') return Object.assign({ type: 'hub' }, hubDetails(j, d.id));
  const p = ops().destOf('production'); return { type: 'production', name: p.name, address: p.address, phone: p.phone };
}
function activities(j, me) {
  const out = [];
  store.audit({ jobId: j.id }).forEach(e => {
    const vendorSafe = ['submit_quote', 'award_po', 'award_direct', 'draft_upload', 'draft_approve', 'draft_reject', 'vendor_ship', 'receive_hub', 'forward', 'hub_delivery', 'vendor_paid', 'request_quotes'];
    if (me.type === 'vendor' && vendorSafe.indexOf(e.action) < 0 && !(e.to && ['dispatched', 'at_hub'].indexOf(e.to) >= 0)) return;
    if (me.type === 'vendor' && e.action === 'submit_quote' && e.actor !== coOf(me)) return;
    const acc = store.findCustomer(e.actor) || store.customers().find(c => c.name === e.actor && c.type === 'vendor');
    const by = (acc && acc.name) || e.actor;
    const own = me.type === 'vendor' && !!acc && (acc.id === coOf(me) || acc.vendorId === coOf(me));
    out.push({ title: ACT_TITLE[e.action] || (e.to ? (require('./domain').STATUS[e.to] || {}).label || e.to : e.action.replace(/_/g, ' ')), text: me.type === 'vendor' && /award/.test(e.action) ? (j.outsource && j.outsource.po ? 'PO ' + j.outsource.po : '') : (e.note || ''), by: me.type === 'vendor' && !own ? 'Printoka' : by, at: e.ts });
  });
  return out.sort((a, b) => String(b.at).localeCompare(String(a.at)));
}
const ACT_TITLE = { submit_quote: 'Quote submitted', award_po: 'Printer assigned', award_direct: 'Printer assigned', draft_upload: 'Draft uploaded', draft_approve: 'Draft approved', draft_reject: 'Draft rejected', vendor_ship: 'Shipped to hub', hub_delivery: 'Shipped', dispatch_details: 'Delivery details', vendor_paid: 'Paid', request_quotes: 'Quote requested', receive_hub: 'Received at hub', forward: 'Forwarded from hub' };
function documents(j, me) {
  const o = j.outsource || {}; const d = [];
  const staff = me.type !== 'vendor' && me.type !== 'hub';
  if (o.awardedTo && ((me.type === 'vendor' && o.awardedTo === coOf(me)) || staff)) { d.push({ id: 'purchase-order', label: 'Purchase Order' }); d.push({ id: 'hub-label', label: 'Delivery Label' }); }
  if (me.type === 'hub' || staff) d.push({ id: 'shipping-label', label: 'Shipping Label' });
  return d;
}
function orderDetails(j) {
  const o = j.orderId && store.order(j.orderId); const fd = j.finalDestination || {};
  const a = o && o.shipTo && typeof o.shipTo === 'object' ? o.shipTo : null;
  return { orderNumber: o ? String(o.id).replace(/^PO-/, '') : j.orderId, name: (a && a.name) || (o && o.customer && o.customer.name) || j.customer, phone: (a && a.phone) || (o && o.customer && o.customer.phone) || fd.phone || '',
    address: fd.type === 'customer' ? (a ? [a.line1, a.line2, [a.postcode, a.city].filter(Boolean).join(' '), a.state].filter(Boolean).join(', ') : fd.address) : (fd.name + (fd.address ? ', ' + fd.address : '')),
    postcode: (a && a.postcode) || ((String(fd.address || '').match(/\b\d{5}\b/) || [])[0]) || '', to: fd.type || 'customer', toName: fd.name || '' };
}
function jobDetails(j) {
  const o = j.orderId && store.order(j.orderId); const idx = o ? (o.jobIds || []).indexOf(j.id) : -1; const it = o && idx >= 0 ? o.items[idx] : null;
  const arts = o ? (o.files || []).filter(f => f.kind === 'artwork' && f.line === idx + 1).map(f => ({ id: f.id, name: f.name, orderId: o.id })) : [];
  return { product: j.product, spec: (it && it.spec) || j.spec || '', qty: j.qty, artworks: arts.length ? arts : ((j.artwork && j.artwork.file && !/^pending-upload/.test(j.artwork.file)) ? [{ name: j.artwork.file }] : []), deadline: j.deadline, instructions: j.instructions || '' };
}
// the printing-job view every account shares (printer: only its own quote, no customer contact)
function view(j, me) {
  const o = j.outsource || {}; const co = coOf(me);
  const mine = co ? (o.vendors || []).find(v => v.vendorId === co) : null;
  const pub = f => f ? { id: f.id, name: f.name, at: f.at } : null;
  const v = {
    status: statusFor(j, me), po: o.po || null, poNumber: o.poNumber || null, awarded: !!o.awardedTo, awardedToMe: !!(co && o.awardedTo === co), paidAt: o.paidAt || null,
    draft: o.draft ? { file: pub(o.draft.file), at: o.draft.at, by: o.draft.by, approvedAt: o.draft.approvedAt || null, approvedBy: o.draft.approvedBy || null, rejectedAt: o.draft.rejectedAt || null, rejectReason: o.draft.rejectReason || '' } : null,
    job: (me.type === 'vendor' && o.awardedTo && o.awardedTo !== co) ? Object.assign(jobDetails(j), { artworks: [] }) : jobDetails(j), deliverTo: deliverTo(j), documents: documents(j, me), activities: activities(j, me),
    hubDelivery: j.hubDelivery ? { tracking: j.hubDelivery.tracking, company: j.hubDelivery.company, document: pub(j.hubDelivery.document), at: j.hubDelivery.at, by: j.hubDelivery.by } : null,
    dispatchDelivery: j.dispatchDelivery && me.type !== 'vendor' ? { tracking: j.dispatchDelivery.tracking, company: j.dispatchDelivery.company, document: pub(j.dispatchDelivery.document), at: j.dispatchDelivery.at, by: j.dispatchDelivery.by } : null,
  };
  if (me.type === 'vendor') {
    v.myQuote = mine ? { amount: mine.price, leadDays: mine.leadDays, note: mine.note, submittedAt: mine.submittedAt, document: pub(mine.document), awardedAmount: o.awardedTo === co ? mine.price : null } : null;
    v.canQuote = me.role !== 'printer_staff' && !o.awardedTo;
    v.canShip = o.awardedTo === co && j.status === 'outsourcing' && !!(o.draft && o.draft.approvedAt);
  } else {
    v.quotes = (o.vendors || []).map(x => ({ vendorId: x.vendorId, vendorName: x.vendorName, amount: x.price, leadDays: x.leadDays, submittedAt: x.submittedAt, document: pub(x.document), awarded: x.vendorId === o.awardedTo }));
    v.customer = orderDetails(j);
    v.canApproveDraft = !!(o.draft && o.draft.file && !o.draft.approvedAt && !o.draft.rejectedAt && j.status === 'outsourcing');
  }
  return v;
}
// what a printer sees of the job itself (no customer contact, order or payment details)
function vendorJob(j, me) {
  const d = j.destination || {}; const mineNow = !!(me && j.outsource && j.outsource.awardedTo === coOf(me));
  // before the award a printer only learns the kind of destination, never the customer's address
  const dest = d.type === 'customer' && !mineNow ? { type: 'customer', name: 'Customer delivery (address on the shipping label after award)' } : { type: d.type, id: d.id, name: d.name, address: d.address };
  return { id: j.id, product: j.product, spec: j.spec, qty: j.qty, status: j.status, deadline: j.deadline, createdAt: j.createdAt, instructions: j.instructions || '', parcels: j.parcels || 1,
    destination: dest, hub: j.hub, label: mineNow ? j.label : null, outsource: j.outsource ? { po: j.outsource.po, awardedTo: j.outsource.awardedTo, status: j.outsource.status } : null, shipments: (j.shipments || []).filter(s => s.byVendor || s.leg === 1).map(s => ({ courier: s.courier, tracking: s.tracking, at: s.at })) };
}
function listRow(j, me) {
  const s = statusFor(j, me); const o = j.outsource || {}; const co = coOf(me);
  const mine = co ? (o.vendors || []).find(v => v.vendorId === co) : (o.vendors || []).find(v => v.vendorId === o.awardedTo);
  const ord = j.orderId && store.order(j.orderId);
  return { id: j.id, product: j.product, qty: j.qty, amount: mine && mine.price != null ? mine.price : null, status: s ? s.label : (require('./domain').STATUS[j.status] || {}).label, statusId: s ? s.id : j.status, color: s ? s.color : null, date: (ord && ord.createdAt) || j.createdAt, po: o.po || null, submitted: !!(mine && mine.submittedAt) };
}

// ---------------------------------------------------------------- printer actions
function submitQuote(jid, me, b) {
  const j = store.job(jid); if (!j || !j.outsource) return { error: 'No open quote request.' };
  const co = coOf(me); const v = (j.outsource.vendors || []).find(x => x.vendorId === co); if (!v) return { error: 'You were not invited to quote this job.' };
  if (me.role === 'printer_staff') return { error: 'Only your printer manager can submit prices.' };
  if (j.outsource.awardedTo) return { error: 'This job has already been awarded.' };
  const amount = Number(b.amount != null ? b.amount : b.price);
  if (!(amount > 0)) return { error: 'Please enter a quote amount.' };
  const changed = v.price !== amount || !!b.documentData;
  if (!changed && v.submittedAt) return { error: 'No changes required.' };
  v.price = amount; v.leadDays = Number(b.leadDays) || v.leadDays || 0; v.note = b.note || v.note || ''; v.submittedAt = now();
  if (b.documentData) { const f = saveBlob(path.join(ROOT, jid), { data: b.documentData, name: b.documentName || 'quote.pdf' }, 'Q'); if (f.error) return f; v.document = f; }
  const n = j.outsource.vendors.filter(x => x.submittedAt).length;
  j.outsource.status = n === j.outsource.vendors.length ? 'quotes_received' : 'partly_received';
  store.logEvent({ actor: co, role: 'printer', action: 'submit_quote', jobId: jid, from: null, to: null, note: 'Quote RM ' + amount.toFixed(2) + (v.leadDays ? ' · ' + v.leadDays + ' days' : '') });
  if (j.outsource.status === 'quotes_received') store.notify({ type: 'role', role: 'scheduler' }, { kind: 'quotes_received', title: 'All printer quotes are in for ' + jid, body: j.product + ' · ' + n + ' quote(s) — compare and award.', jobId: jid });
  store.save(); return { ok: true, message: 'Quote update successfully!' };
}
function uploadDraft(jid, me, b) {
  const j = store.job(jid); const co = coOf(me); if (!j || !j.outsource || j.outsource.awardedTo !== co) return { error: 'This job is not awarded to your company.' };
  if (j.status !== 'outsourcing') return { error: 'This job has already shipped.' };
  if (!b.data) return { error: 'Please fill in the required field.' };
  const o = j.outsource; if (o.draft && o.draft.approvedAt) return { error: 'The draft has already been approved.' };
  const f = saveBlob(path.join(ROOT, jid), b, 'D'); if (f.error) return f;
  const first = !o.draft || !o.draft.file || o.draft.rejectedAt;
  if (o.draft && o.draft.file) { o.draftHistory = o.draftHistory || []; o.draftHistory.push(o.draft.file); }
  o.draft = { file: f, at: now(), by: me.name };
  store.logEvent({ actor: me.name, role: 'printer', action: 'draft_upload', jobId: jid, from: null, to: null, note: f.name });
  if (first) {
    store.notify({ type: 'role', role: 'scheduler' }, { kind: 'draft_uploaded', title: 'Printer draft to approve — ' + jid, body: (o.vendors.find(v => v.vendorId === co) || {}).vendorName + ' uploaded a draft for ' + j.product + '. Approve it so they can start printing.', jobId: jid });
    store.sendEmail('draft-uploaded', { to: 'print@printoka.com', name: 'Printoka HQ', subject: 'Draft uploaded — ' + (o.po || jid), body: 'A printer uploaded a draft for ' + j.product + ' (' + jid + '). Please review and approve it before printing starts.' });
  }
  store.save(); return { ok: true, message: 'Draft upload successfully!' };
}
function decideDraft(jid, decision, reason, actor, role) {
  const j = store.job(jid); if (!j || !j.outsource || !j.outsource.draft || !j.outsource.draft.file) return { error: 'No draft to review.' };
  const d = j.outsource.draft; if (d.approvedAt) return { error: 'The draft has already been approved.' };
  if (decision === 'approve') { d.approvedAt = now(); d.approvedBy = actor; d.rejectedAt = null; }
  else if (decision === 'reject') { if (!String(reason || '').trim()) return { error: 'Tell the printer what to change.' }; d.rejectedAt = now(); d.rejectedBy = actor; d.rejectReason = String(reason).slice(0, 600); }
  else return { error: 'Unknown decision.' };
  store.logEvent({ actor, role, action: decision === 'approve' ? 'draft_approve' : 'draft_reject', jobId: jid, from: null, to: null, note: decision === 'approve' ? 'The administrator has approved the draft.' : d.rejectReason });
  const v = store.findCustomer(j.outsource.awardedTo);
  if (v) {
    store.notify({ type: 'customer', id: v.id }, { kind: 'draft_' + decision, title: decision === 'approve' ? 'Draft approved — you may start printing' : 'Draft needs changes', body: (j.outsource.po || jid) + ' · ' + j.product + (decision === 'approve' ? '' : ': ' + d.rejectReason), jobId: jid });
    if (v.email) store.sendEmail('draft-' + decision, { to: v.email, name: v.name, subject: (decision === 'approve' ? 'Draft approved — ' : 'Draft needs changes — ') + (j.outsource.po || jid), body: decision === 'approve' ? 'The administrator has approved the draft. You may proceed with printing.\nAfter shipping the items to the hub, update the status to "Shipped to hub".' : 'Please upload a corrected draft:\n' + d.rejectReason });
  }
  store.save(); return { ok: true };
}
// printer "Job Status" card: Draft approved → Shipped to hub
function shipToHub(jid, me, b) {
  const j = store.job(jid); const co = coOf(me); if (!j || !j.outsource || j.outsource.awardedTo !== co) return { error: 'This job is not awarded to your company.' };
  if (b.status && b.status !== 'shipped-to-hub') return { error: 'No changes required.' };
  if (!(j.outsource.draft && j.outsource.draft.approvedAt)) return { error: 'Please wait for admin approve the draft before start printing.' };
  const action = (j.destination || {}).type === 'outlet' ? 'vendor_ship_outlet' : 'vendor_ship';
  const r = ops().transition(jid, 'printer', me.name, action, { courier: b.courier || 'Printer delivery', tracking: b.tracking || '' });
  if (r.error) return r;
  const last = (j.shipments || []).slice(-1)[0]; if (last) last.byVendor = co;
  store.save(); return { ok: true, message: 'Status update successfully!' };
}
// "Delivery Details" card (original hub card, reused by logistics): tracking numbers + delivery company
// + delivery order. Hub: at hub → forward ("Shipped"). Logistics: packed → dispatch. Afterwards: edit the details.
const HUB_ROLES = ['hub', 'hub_manager', 'production_director'], LOG_ROLES = ['logistics_staff', 'logistics_manager', 'production_director'];
function deliveryStage(j) { if (j.status === 'at_hub') return 'hub'; if (j.status === 'logistics') return 'logistics'; if (j.hubDelivery) return 'hub'; if (j.dispatchDelivery) return 'logistics'; return null; }
function deliveryDetails(jid, me, role, b) {
  const j = store.job(jid); if (!j) return { error: 'Job not found.' };
  const stage = deliveryStage(j);
  if (!stage) return { error: j.status === 'dispatched' ? 'Receive the parcel at the hub first.' : 'This job is not ready to ship yet.' };
  if (stage === 'hub' && (HUB_ROLES.indexOf(role) < 0 || (me.type === 'hub' && !hubCanSee(j, me)))) return { error: 'Only the hub team can update the hub delivery details.' };
  if (stage === 'logistics' && LOG_ROLES.indexOf(role) < 0) return { error: 'Only the logistics team can dispatch from production.' };
  const key = stage === 'hub' ? 'hubDelivery' : 'dispatchDelivery';
  const tracking = String(b.tracking || '').split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  if (!tracking.length) return { error: 'Please enter tracking number' };
  const company = String(b.company || '').trim(); if (!company) return { error: 'Please fill in the required field.' };
  let doc = j[key] && j[key].document;
  if (b.documentData) { const f = saveBlob(path.join(ROOT, jid), { data: b.documentData, name: b.documentName || 'delivery-order.pdf' }, 'O'); if (f.error) return f; doc = f; }
  const prev = j[key];
  if (prev && prev.tracking.join('\n') === tracking.join('\n') && prev.company === company && doc === prev.document) return { error: 'No changes required.' };
  const leaving = (stage === 'hub' && j.status === 'at_hub') || (stage === 'logistics' && j.status === 'logistics');
  if (leaving) {
    const r = ops().transition(jid, role, me.name, stage === 'hub' ? 'forward' : 'dispatch', { courier: company, tracking: tracking.join(', '), destType: stage === 'hub' ? b.destType : undefined, destId: stage === 'hub' ? b.destId : undefined });
    if (r.error) return r;
  } else {
    // already on its way: correct the courier / tracking on that leg
    const legs = j.shipments || []; const leg = stage === 'hub' ? legs[legs.length - 1] : legs[0];
    if (leg) { leg.courier = company; leg.tracking = tracking.join(', '); }
    j.courier = company; j.tracking = tracking.join(', ');
  }
  j[key] = { tracking, company, document: doc || null, at: now(), by: me.name };
  store.logEvent({ actor: me.name, role, action: stage === 'hub' ? 'hub_delivery' : 'dispatch_details', jobId: jid, from: null, to: null, note: company + ' · ' + tracking.join(', ') });
  store.save(); return { ok: true, message: 'Delivery details update successfully!', stage };
}
function markPaid(jid, actor, role, b) {
  const j = store.job(jid); if (!j || !j.outsource || !j.outsource.awardedTo) return { error: 'No printer assigned.' };
  if (j.outsource.paidAt) return { error: 'Already marked paid.' };
  if (j.status === 'outsourcing') return { error: 'The printer has not shipped yet.' };
  j.outsource.paidAt = now(); j.outsource.paidBy = actor; j.outsource.paidRef = String((b && b.reference) || '').slice(0, 80);
  store.logEvent({ actor, role, action: 'vendor_paid', jobId: jid, from: null, to: null, note: (j.outsource.po || '') + (j.outsource.paidRef ? ' · ' + j.outsource.paidRef : '') });
  store.save(); return { ok: true };
}
// the running purchase-order number (original option "opt_purchaseordernumber")
function poNumber(j) {
  const o = j.outsource; if (!o || !o.awardedTo) return null;
  if (!o.poNumber) { const db = store.load(); db.settings = db.settings || {}; const n = Number(db.settings.purchaseOrderNumber) || 1001; o.poNumber = n; db.settings.purchaseOrderNumber = n + 1; store.save(); }
  return o.poNumber;
}
function documentData(j, kind, me) {
  if (!documents(j, me).some(d => d.id === kind)) return { error: 'Not allowed.' };
  const o = j.outsource || {}; const v = o.awardedTo && store.findCustomer(o.awardedTo); const mine = (o.vendors || []).find(x => x.vendorId === o.awardedTo) || {};
  const base = { kind, jobId: j.id, job: jobDetails(j), hub: deliverTo(j) };
  if (kind === 'purchase-order') return Object.assign(base, { poNumber: poNumber(j), vendor: { name: (v && (v.company || v.name)) || mine.vendorName, address: (v && ((v.addresses || [])[0] ? [v.addresses[0].line1, v.addresses[0].line2, [v.addresses[0].postcode, v.addresses[0].city].filter(Boolean).join(' '), v.addresses[0].state].filter(Boolean).join(', ') : v.address)) || '' }, shipping: me.type === 'vendor' ? { name: (j.destination || {}).name, address: (j.destination || {}).address } : orderDetails(j), amount: mine.price });
  if (kind === 'hub-label') return Object.assign(base, { poNumber: poNumber(j) });
  return Object.assign(base, { order: orderDetails(j) });
}

// ---------------------------------------------------------------- printer custom quotes
function requestPrinterQuotes(qid, b, actor) {
  const q = store.quote(qid); if (!q) return { error: 'Quote not found.' };
  const ids = (b.vendorIds || []).filter(Boolean); if (!ids.length) return { error: 'Pick at least one printer.' };
  q.printerQuotes = q.printerQuotes || { requestedAt: now(), printers: [] };
  q.printerQuotes.hub = b.hub || q.printerQuotes.hub || null;
  ids.forEach(id => { if (q.printerQuotes.printers.some(p => p.vendorId === id)) return; const v = store.findCustomer(id); if (!v || v.type !== 'vendor') return;
    q.printerQuotes.printers.push({ vendorId: id, vendorName: v.name, amount: null, weight: null, document: null, submittedAt: null, requestedAt: now() });
    store.notify({ type: 'customer', id }, { kind: 'printer_custom_quote', title: 'New custom quote request', body: ((q.requirement && q.requirement.product) || 'Custom job') + ' — submit your weight and price.', quoteId: qid });
    if (v.email) store.sendEmail('request-quote-printer', { to: v.email, name: v.name, subject: 'Custom quote request — ' + ((q.requirement && q.requirement.product) || qid), body: 'Hi ' + v.name + ',\n\nPrintoka would like your price for a custom job. Sign in to your printer account → Custom Quotes to submit it.' }); });
  q.printerActivity = q.printerActivity || []; q.printerActivity.push({ ts: now(), actor, action: 'Quote requested', note: ids.length + ' printer(s)' });
  store.save(); return { quote: q };
}
function customQuoteStatus(q, co) { const p = ((q.printerQuotes || {}).printers || []).find(x => x.vendorId === co); return p && p.submittedAt ? 'Quote submitted' : 'Pending quote'; }
function vendorCustomQuotes(me) {
  const co = coOf(me);
  return store.quotes().filter(q => q.printerQuotes && q.printerQuotes.printers.some(p => p.vendorId === co)).map(q => { const p = q.printerQuotes.printers.find(x => x.vendorId === co);
    return { id: q.id, product: (q.requirement && q.requirement.product) || 'Custom job', qty: (q.requirement && q.requirement.qty) || null, amount: p.amount, status: customQuoteStatus(q, co), date: p.requestedAt || q.printerQuotes.requestedAt }; })
    .sort((a, b) => String(b.date).localeCompare(String(a.date)));
}
function vendorCustomQuote(qid, me) {
  const q = store.quote(qid); const co = coOf(me); const p = q && q.printerQuotes && q.printerQuotes.printers.find(x => x.vendorId === co);
  if (!p) return { error: 'Access denied: You are not authorized to view this.' };
  const r = q.requirement || {};
  return { quote: { id: q.id, product: r.product || 'Custom job', quantity: r.qty || '', specification: r.quoteData || [r.size, r.material, r.finishing, r.remarks].filter(Boolean).join('\n'), status: customQuoteStatus(q, co),
    mine: { amount: p.amount, weight: p.weight, document: p.document ? { id: p.document.id, name: p.document.name } : null, submittedAt: p.submittedAt },
    activities: (q.printerActivity || []).filter(a => !a.vendorId || a.vendorId === co).slice().reverse().map(a => ({ title: a.action, text: a.note || '', by: a.vendorId ? a.actor : 'Printoka', at: a.ts })),
    hub: q.printerQuotes.hub ? hubDetails({}, q.printerQuotes.hub) : null, canSubmit: !p.submittedAt && me.role !== 'printer_staff' } };
}
function submitCustomQuote(qid, me, b) {
  const q = store.quote(qid); const co = coOf(me); const p = q && q.printerQuotes && q.printerQuotes.printers.find(x => x.vendorId === co);
  if (!p) return { error: 'Access denied: You are not authorized to view this.' };
  if (me.role === 'printer_staff') return { error: 'Only your printer manager can submit prices.' };
  if (p.submittedAt) return { error: 'You can submit the quote only once.' };
  const amount = Number(b.amount), weight = String(b.weight || '').trim();
  if (!(amount > 0) || !weight) return { error: 'Please fill in the required field.' };
  if (b.documentData) { const f = saveBlob(path.join(QROOT, qid), { data: b.documentData, name: b.documentName || 'quote.pdf' }, 'P'); if (f.error) return f; p.document = f; }
  p.amount = amount; p.weight = weight; p.submittedAt = now(); p.by = me.name;
  q.printerActivity = q.printerActivity || []; q.printerActivity.push({ ts: now(), actor: me.name, vendorId: co, action: 'Amount changed', note: 'to RM ' + amount.toFixed(2) });
  if (q.printerQuotes.printers.every(x => x.submittedAt)) store.notify({ type: 'role', role: 'scheduler' }, { kind: 'printer_quotes_in', title: 'All printer quotes received — ' + qid, body: ((q.requirement && q.requirement.product) || 'Custom job') + ': ' + q.printerQuotes.printers.map(x => x.vendorName + ' RM ' + x.amount).join(', '), quoteId: qid });
  store.save(); return { ok: true, message: 'Quote update successfully!' };
}
function readCustomQuoteDoc(qid, vendorId, me) {
  const q = store.quote(qid); const p = q && q.printerQuotes && q.printerQuotes.printers.find(x => x.vendorId === vendorId);
  if (!p || !p.document) return { error: 'File not found.', code: 404 };
  if (me.type === 'vendor' && coOf(me) !== vendorId) return { error: 'Not allowed.', code: 403 };
  const f = path.join(QROOT, qid, p.document.stored); if (!f.startsWith(QROOT) || !fs.existsSync(f)) return { error: 'File missing on disk.', code: 404 };
  return { file: p.document, data: fs.readFileSync(f), type: MIME[(p.document.name.split('.').pop() || '').toLowerCase()] || 'application/octet-stream' };
}

module.exports = { STATUSES, printingStatus, statusInfo, view, vendorJob, listRow, canSee, vendorCanSee, hubCanSee, submitQuote, uploadDraft, decideDraft, shipToHub, deliveryDetails, markPaid, saveProof, deliverTo, documentData, readJobFile,
  requestPrinterQuotes, vendorCustomQuotes, vendorCustomQuote, submitCustomQuote, readCustomQuoteDoc };
