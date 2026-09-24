/*
 * Persistence + seed for the Printoka operations backend.
 * File-backed JSON store (swap for Postgres later — the API surface stays the same).
 * Every mutation appends an AuditEvent (Prod §1.7 "every action traceable in system logs").
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const D = require('./domain');

const DATA_FILE = path.join(__dirname, 'data.json');
let db = null;

function now() { return new Date().toISOString(); }
function id(prefix) { return prefix + '-' + Math.random().toString(36).slice(2, 8).toUpperCase(); }

function seed() {
  const t = Date.parse('2026-09-10T09:00:00+08:00');
  const hrs = h => new Date(t + h * 3600e3).toISOString();
  const users = Object.keys(D.ROLES).map((role, i) => ({ id: 'U' + (i + 1), role, name: D.ROLES[role].label, outlet: D.ROLES[role].dept === 'outlet' ? 'KL-Damansara' : null }));
  // A spread of jobs across the lifecycle so every queue has real content.
  const jobs = [
    { id: 'J-24817-1', orderId: 'O-24817', channel: 'online', customer: 'Lim Wei Sheng', product: 'Business Card', spec: '54×89mm · Gloss Art Card 310gsm · Matte lam · 1,000 pcs', qty: 1000, price: 86.42,
      status: 'prepress', paymentValidated: true, paymentValidatedAt: hrs(-2), creditTerms: false, artwork: { file: 'bizcard-final-v3.pdf', checkStatus: 'pending' }, artworkMatches: true, deadline: hrs(48), acknowledgedAt: hrs(-2) },
    { id: 'J-24820-1', orderId: 'O-24820', channel: 'online', customer: 'Sunrise Cafe', product: 'Flyer (= Loose Sheet Litho)', spec: 'A5 · 128gsm · 4C both · 2,000 pcs', qty: 2000, price: 268.0,
      status: 'prepress', paymentValidated: true, paymentValidatedAt: hrs(-1), artwork: { file: 'flyer-a5.pdf', checkStatus: 'pending' }, artworkMatches: false, deadline: hrs(24), acknowledgedAt: hrs(-1) },
    { id: 'J-24805-1', orderId: 'O-24805', channel: 'outlet', customer: 'Borneo Dental', product: 'Booklet — Litho (Offset)', spec: 'A4 · Saddle · 8pp · 1,000 pcs', qty: 1000, price: 1028.51,
      status: 'scheduling', paymentValidated: true, paymentValidatedAt: hrs(-6), artwork: { file: 'booklet-a4.pdf', checkStatus: 'pass' }, artworkMatches: true, deadline: hrs(72), owner: { prepress: 'U4' } },
    { id: 'J-24799-1', orderId: 'O-24799', channel: 'online', customer: 'Studio North', product: 'Label Sticker — Digital', spec: '50mm circle · Vinyl · gloss · 500 pcs', qty: 500, price: 92.0,
      status: 'printing', paymentValidated: true, paymentValidatedAt: hrs(-20), artwork: { file: 'labels-round.pdf', checkStatus: 'pass' }, artworkMatches: true, deadline: hrs(12), machine: 'Digital-01', owner: { prepress: 'U4', scheduler: 'U6' } },
    { id: 'J-24788-1', orderId: 'O-24788', channel: 'outsourced', customer: 'MSK Logistics', product: 'Banner — Litho', spec: '3m×1m · 4C · 6 pcs', qty: 6, price: 480.0,
      status: 'outsourcing', paymentValidated: true, paymentValidatedAt: hrs(-30), artwork: { file: 'banner.pdf', checkStatus: 'pass' }, artworkMatches: true, deadline: hrs(30), printer: 'LargeFormat Co', po: 'PO-1188', owner: { prepress: 'U4', scheduler: 'U6' } },
    { id: 'J-24770-1', orderId: 'O-24770', channel: 'online', customer: 'Rimba Resort', product: 'Notepad — Litho', spec: 'A6 · 50 sheets · 300 pads', qty: 300, price: 640.0,
      status: 'logistics', paymentValidated: true, paymentValidatedAt: hrs(-40), artwork: { file: 'notepad.pdf', checkStatus: 'pass' }, artworkMatches: true, deadline: hrs(8), owner: { prepress: 'U4', scheduler: 'U6' } },
    { id: 'J-24999-1', orderId: 'O-24999', channel: 'online', customer: 'Kopitiam 88', product: 'Business Card', spec: '54×89mm · 260gsm · 4C both · 500 pcs', qty: 500, price: 60.0,
      status: 'intake', paymentValidated: false, artwork: { file: 'kopitiam-card.pdf', checkStatus: 'pending' }, artworkMatches: true, deadline: hrs(36) },
  ];
  const audit = [{ id: id('A'), ts: hrs(-2), actor: 'system', role: 'system', action: 'seed', jobId: null, from: null, to: null, note: 'Demo data seeded' }];
  // Seeded staff login accounts (password: "printoka"). Customers self-register (type customer).
  const staff = [
    { email: 'admin@printoka.com', name: 'Admin', type: 'admin', role: 'admin' },
    { email: 'outlet@printoka.com', name: 'Nadia (Outlet Staff)', type: 'outlet', role: 'outlet_staff', outlet: 'KL-Damansara' },
    { email: 'outlet-manager@printoka.com', name: 'Outlet Manager', type: 'outlet', role: 'outlet_manager', outlet: 'KL-Damansara' },
    { email: 'prepress@printoka.com', name: 'Nazri (Prepress)', type: 'production', role: 'prepress' },
    { email: 'scheduler@printoka.com', name: 'Hafiz (Scheduler)', type: 'production', role: 'scheduler' },
    { email: 'logistics@printoka.com', name: 'Logistics Staff', type: 'production', role: 'logistics' },
    { email: 'production@printoka.com', name: 'Production Manager', type: 'production', role: 'production_manager' },
    { email: 'vendor@printoka.com', name: 'LargeFormat Co', type: 'vendor', role: 'vendor' },
    { email: 'vendor2@printoka.com', name: 'Cetak Utara', type: 'vendor', role: 'vendor' },
    { email: 'vendor3@printoka.com', name: 'Borneo Press', type: 'vendor', role: 'vendor' },
  ].map((s, i) => {
    const { salt, hash } = hashPassword('printoka');
    return { id: 'S-' + (i + 1), email: s.email, passHash: hash, salt, name: s.name, type: s.type, role: s.role, outlet: s.outlet || null, tier: 'Standard', spend12mo: 0, creditBalance: 0, addresses: [], creditLedger: [], createdAt: now() };
  });
  // A demo retail customer WITH order history — so the management-side order view has real
  // content: artworks, billing + shipping, payment proof, invoice/slip and customer history.
  const demoAddr = { name: 'Samantha LIM', phone: '0178016899', line1: 'Lot 599, Jalan Kampung Luak 1', line2: '', city: 'Miri', postcode: '98000', state: 'Sarawak', country: 'MY' };
  const demo = (() => { const { salt, hash } = hashPassword('printoka'); return { id: 'C-DEMO01', email: 'samantha@printoka.my', passHash: hash, salt, type: 'customer', role: 'customer', name: 'Samantha LIM', phone: '0178016899', company: '', tier: 'Silver', spend12mo: 3242.5, creditBalance: 0, addresses: [Object.assign({ id: 'A-DEMO01', label: 'Home', isDefault: true }, demoAddr)], creditLedger: [], createdAt: hrs(-24 * 120) }; })();
  staff.push(demo);
  const mkOrder = (o) => {
    const items = o.items.map((it, i) => ({ lineNo: i + 1, productId: it.productId || null, product: it.product, spec: it.spec || '', qty: it.qty, unitPrice: Math.round((it.lineTotal / it.qty) * 100) / 100, lineTotal: it.lineTotal, artworks: it.artworks || [] }));
    const subtotal = Math.round(items.reduce((s, it) => s + it.lineTotal, 0) * 100) / 100;
    const tax = Math.round(subtotal * 0.08 * 100) / 100;
    const shipFee = o.shipFee != null ? o.shipFee : 12;
    const total = Math.round((subtotal + tax + shipFee) * 100) / 100;
    return { id: o.id, userId: demo.id, channel: o.channel || 'online', customer: { name: demo.name, email: demo.email, phone: demo.phone, company: '' }, billing: demoAddr, shipTo: demoAddr, payment: o.payment, items, subtotal, memberDiscount: 0, tax, shipping: shipFee, total, tier: 'Silver', status: o.payment.status === 'validated' ? 'paid' : 'pending_payment', jobIds: [], createdAt: o.createdAt };
  };
  const orders = [
    mkOrder({ id: 'PO-2026-7X3MAR', createdAt: hrs(-1), payment: { method: 'card_test', gateway: 'Stripe', status: 'validated', paidAt: hrs(-1), reference: 'ch_3L8EIWMA6w9JqiBn1Q6qDFcj', proof: null },
      items: [
        { product: 'Stickers and Labels', qty: 1200, lineTotal: 176.0, artworks: ['Assorted Nuts (mooncake) (1).png', 'Moon Biscuits.png', 'SYWL.png', 'WL.png'],
          spec: 'Custom Size: 25mm (L) x 25mm (W) · Quantity (pcs): 300 · Material: Mirrorkote Glossy Stickers · Sticker Shape: Round Shape · Sticker Lamination: None · Sticker Delivery Sheet Size: Place on A3 · Urgency: Standard · Shipping Method: Air Courier · Artworks Quantity: 4' },
        { product: 'Stickers and Labels', qty: 300, lineTotal: 62.0, artworks: ['logo FINAL (PRINT).png'],
          spec: 'Custom Size: 50mm (L) x 50mm (W) · Quantity (pcs): 300 · Material: Mirrorkote Glossy Stickers · Sticker Shape: Square or Rectangular · Sticker Lamination: None · Sticker Delivery Sheet Size: Place on A3 · Urgency: Standard · Shipping Method: Air Courier' },
      ] }),
    mkOrder({ id: 'PO-2026-6KD22M', createdAt: hrs(-24 * 6), payment: { method: 'ipay88', gateway: 'iPay88 · FPX (Maybank2u)', status: 'validated', paidAt: hrs(-24 * 6), reference: 'T2026090612345678', proof: null },
      items: [{ product: 'Business Card', qty: 1000, lineTotal: 86.0, artworks: ['samantha-bizcard-v2.pdf'],
        spec: 'Custom Size: 54mm x 89mm · Material: 310gsm Art Card · Lamination: Matte 1 Side · Printing: 4C x 4C both side · Quantity: 1,000 pcs' }] }),
    mkOrder({ id: 'PO-2026-5RN91X', createdAt: hrs(-24 * 11), shipFee: 25, payment: { method: 'bank_transfer', gateway: 'Manual bank-in (Maybank)', status: 'pending', paidAt: null, reference: 'BT-5RN91X', proof: 'bank-in-slip-5RN91X.jpg' },
      items: [{ product: 'Booklet — Litho (Offset)', qty: 300, lineTotal: 1120.0, artworks: ['catalogue-2026-cover.pdf', 'catalogue-2026-content.pdf'],
        spec: 'Size: A5 (Closed) · Cover: 250gsm Art Card + Matte Lam 1S · Content: 80gsm Woodfree · Binding: Saddle Stitch · Pages: 24pp incl. cover · Quantity: 300 books' }] }),
    mkOrder({ id: 'PO-2026-4MB07C', createdAt: hrs(-24 * 20), payment: { method: 'card_test', gateway: 'Stripe', status: 'validated', paidAt: hrs(-24 * 20), reference: 'ch_3K7DHVLA5x8IphAm0P5pCEbi', proof: null },
      items: [{ product: 'Flyer', qty: 2000, lineTotal: 268.0, artworks: ['promo-flyer-a5.pdf'],
        spec: 'Size: A5 · Material: 128gsm Art Paper Glossy · Printing: 4C both side · Quantity: 2,000 pcs' }] }),
  ];
  // Custom invoices manually prepared by admin/outlet to customers (WP post-type: Custom Invoice).
  const customInvoices = [
    { id: 'CINV-2026-0001', number: 'INV07092026001', date: '2026-09-07', status: 'paid', userId: demo.id, userName: 'Kee Meng Lim', currency: 'MYR', price: 195.0, orderId: '40044',
      description: 'Flyer printing.\nSize: A4 Size (Open Size)\nMaterial: 128gsm Art Paper Glossy\nPrinting: 4C Colourful Both Side\nFinishing: Half Folding into A5\nQuantity: 1000 pieces\nPrice: RM195.00 in total include delivery.', createdBy: { name: 'Admin', type: 'admin', outlet: '' }, createdAt: hrs(-24 * 4) },
    { id: 'CINV-2026-0002', number: 'INV08052026007', date: '2026-08-05', status: 'paid', userId: demo.id, userName: 'Samantha LIM', currency: 'MYR', price: 705.0, orderId: '',
      description: 'Bill book printing (2-ply NCR).\nSize: A5 · 2-ply carbonless · Numbering + perforation\nBinding: Glue top, 50 sets per book\nQuantity: 30 books\nPrice: RM705.00 include delivery.', createdBy: { name: 'Nadia (Outlet Staff)', type: 'outlet', outlet: 'KL-Damansara' }, createdAt: hrs(-24 * 37) },
    { id: 'CINV-2026-0003', number: 'INV05252026004', date: '2026-05-25', status: 'unpaid', userId: demo.id, userName: 'Samantha LIM', currency: 'MYR', price: 114.0, orderId: '',
      description: 'Sticker printing.\nCustom Size: 45mm circle · Mirrorkote Glossy\nQuantity: 500 pcs\nPrice: RM114.00 include delivery.', createdBy: { name: 'Admin', type: 'admin', outlet: '' }, createdAt: hrs(-24 * 60) },
  ];
  // A manually-prepared custom quote (WP post-type: Custom Quote) with a rich free-text quote body.
  const manualQuotes = [
    { id: 'Q-8HDAVH', userId: demo.id, channel: 'online', manual: true, customer: { name: 'Shakeen Kaur', email: 'shakeen.kaur@printoka.my', phone: '', company: '' },
      requirement: { product: 'Book Printing', qty: '2300', size: '', material: '', finishing: '', remarks: '', weight: '200',
        quoteData: 'READERS 1, 3, 4, 5, 10\nSize: A5 Size (Closed Size)\nBook Orientation: Portrait\nCover Material: 250gsm Art Card Gloss Coated\nCover Finishing: Matte Laminate 1 Side\nContent Material: 80gsm Woodfree Simili Paper\nContent Printing: 4C x 4C\nBinding: Saddle Stitch Binding\nPages: 10-24 printed pages including cover\nArtworks Quantity: 100 books each title\n\nTotal price for all items: RM37,325.00\n(-) Special discount: RM1,500.00\nFinal Price: RM35,825.00\nLead time: estimate 14 to 21 days\nPrice includes delivery to Singapore via courier; tax and import duty excluded.' },
      artworkFile: null, price: 35825, leadDays: 21, status: 'issued', note: '', remarks: 'Not followed up', staff: { name: 'Admin Printoka', outlet: '' }, orderId: null,
      createdAt: hrs(-24 * 30), issuedAt: hrs(-24 * 30), history: [{ ts: hrs(-24 * 30), actor: 'Admin Printoka', action: 'issued', price: 35825 }] },
  ];
  // seeded notifications so each role's bell has content on first load
  const notes = [
    { id: 'N-SEED01', ts: hrs(-1), read: false, recipient: { type: 'role', role: 'prepress' }, kind: 'order_placed', title: 'A fresh order just landed for artwork check', body: 'Order PO-2026-7X3MAR has come in for Samantha LIM (2 items). Have a look at the files whenever you’re ready.', cta: 'Open the order →', orderId: 'PO-2026-7X3MAR' },
    { id: 'N-SEED02', ts: hrs(-24 * 30), read: false, recipient: { type: 'customer', id: demo.id }, kind: 'quote_issued', title: 'Good news — your quote is ready! 🎉', body: 'Your quote for Book Printing comes to RM 35,825, ready in about 21 days. Take a look whenever you like and let us know what you’d like to do.', cta: 'View your quote →', quoteId: 'Q-8HDAVH' },
  ];
  // catalogue = admin display-name/category overrides on top of catalogue.js defaults (product id -> patch)
  return { users, jobs, audit, catalogue: {}, orders, quotes: manualQuotes, customInvoices, notifications: notes, customers: staff, sessions: {}, meta: { seededAt: now() } };
}

function load() {
  if (db) return db;
  try { db = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8')); }
  catch (e) { db = seed(); save(); }
  return db;
}
function save() { fs.writeFileSync(DATA_FILE, JSON.stringify(db, null, 2)); }
function reset() { db = seed(); save(); return db; }

function jobs() { return load().jobs; }
function job(jid) { return load().jobs.find(j => j.id === jid); }
function users() { return load().users; }

function audit(filter) {
  const a = load().audit;
  if (filter && filter.jobId) return a.filter(e => e.jobId === filter.jobId);
  return a;
}

function logEvent(ev) {
  load().audit.push(Object.assign({ id: id('A'), ts: now() }, ev));
}

// ---- notifications (in-app; email/WhatsApp are separate channels) ----------
// recipient shapes: {type:'customer',id} · {type:'outlet',outlet} · {type:'role',role:'prepress'|'scheduler'|'logistics'}
function notifications() { const db = load(); if (!db.notifications) db.notifications = []; return db.notifications; }
function notify(recipient, payload) {
  notifications().unshift(Object.assign({ id: 'N-' + crypto.randomBytes(4).toString('hex').toUpperCase(), ts: now(), read: false, recipient }, payload));
}
// does this staff user cover a production role's notifications? (manager + admin see their chain)
function userCoversRole(user, role) {
  if (!user) return false;
  if (user.type === 'admin') return true;
  const r = user.role;
  if (role === 'scheduler') return r === 'scheduler' || r === 'scheduler_manager' || r === 'production_manager';
  if (role === 'prepress') return r === 'prepress' || r === 'prepress_manager' || r === 'production_manager';
  if (role === 'logistics') return r === 'logistics' || r === 'logistics_manager' || r === 'production_manager';
  return false;
}
function notificationsFor(user) {
  if (!user) return [];
  return notifications().filter(n => {
    const rc = n.recipient || {};
    if (rc.type === 'customer') return user.type === 'customer' && rc.id === user.id;
    if (rc.type === 'outlet') return user.type === 'outlet' && user.outlet === rc.outlet;
    if (rc.type === 'role') return userCoversRole(user, rc.role);
    return false;
  });
}
function markNotificationRead(user, nid) {
  const list = notificationsFor(user);
  if (nid === 'all') { list.forEach(n => n.read = true); }
  else { const n = list.find(x => x.id === nid); if (n) n.read = true; }
  save(); return { notifications: notificationsFor(user) };
}

// ---- Follow-Up emails: automated system emails per trigger (WordPress "Follow-Up" replacement) ----
// Templates mirror the live admin's Follow-Up list. Sends are LOGGED to an outbox (no real SMTP);
// each event appends a rendered email + tracks Sent/Opens/Clicks stats.
const EMAIL_TEMPLATES = [
  { id: 'new-account', name: 'New Account - reset password', trigger: 'Customer account created', type: 'Single Email', delay: 'Single Email', to: 'customer' },
  { id: 'wallet-transaction', name: 'Wallet transaction', trigger: 'Wallet credit/debit', type: 'Single Email', delay: 'Single Email', to: 'customer' },
  { id: 'order-confirmation', name: 'Order confirmation', trigger: 'Order placed', type: 'Purchase Email', delay: 'Immediately after order', to: 'customer' },
  { id: 'order-feedback', name: 'New order feedback received', trigger: 'Customer submits feedback', type: 'Single Email', delay: 'Single Email', to: 'admin' },
  { id: 'printer-draft', name: 'Printer uploaded draft', trigger: 'Vendor uploads a draft', type: 'Single Email', delay: 'Single Email', to: 'customer' },
  { id: 'all-quotes-received', name: 'All custom quotes received', trigger: 'All vendor quotes are in', type: 'Single Email', delay: 'Single Email', to: 'scheduler' },
  { id: 'request-quote-printer', name: 'Request for custom quote (Printer)', trigger: 'Scheduler requests a vendor quote', type: 'Single Email', delay: 'Single Email', to: 'vendor' },
  { id: 'quote-issued', name: 'Custom quote ready', trigger: 'Scheduler issues a quote', type: 'Single Email', delay: 'Single Email', to: 'customer' },
  { id: 'ready-for-collection', name: 'Goods Ready for Collection', trigger: 'Order status: ready-for-collect', type: 'Purchase Email', delay: '1 minute after Order Status: ready-for-collect', to: 'customer' },
  { id: 'shipped-hub', name: 'Shipped to hub', trigger: 'Job shipped to hub', type: 'Single Email', delay: 'Single Email', to: 'customer' },
  { id: 'job-assigned-hub', name: 'Job assigned to hub', trigger: 'Job assigned to a hub', type: 'Single Email', delay: 'Single Email', to: 'hub' },
  { id: 'job-award-printer', name: 'Job award to printer', trigger: 'PO awarded to a vendor', type: 'Single Email', delay: 'Single Email', to: 'vendor' },
];
function emailConfig() { const db = load(); if (!db.emailConfig) db.emailConfig = {}; return db.emailConfig; } // id -> {active:false} overrides (default active)
function emails() { const db = load(); if (!db.emails) db.emails = []; return db.emails; } // outbox
function emailTemplates() { const cfg = emailConfig(); return EMAIL_TEMPLATES.map(t => ({ ...t, active: cfg[t.id] ? cfg[t.id].active !== false : true })); }
function emailActive(id) { const c = emailConfig()[id]; return c ? c.active !== false : true; }
function setEmailActive(id, active, actor) {
  const cfg = emailConfig(); cfg[id] = { active: !!active };
  logEvent({ actor: actor || 'admin', role: 'production_director', action: 'email_toggle', jobId: null, from: null, to: null, note: id + ' -> ' + (active ? 'active' : 'inactive') });
  save(); return emailTemplates();
}
function sendEmail(templateId, opts) {
  opts = opts || {};
  if (!emailActive(templateId)) return null; // deactivated → not sent
  const t = EMAIL_TEMPLATES.find(x => x.id === templateId); if (!t) return null;
  const e = {
    id: 'E-' + crypto.randomBytes(4).toString('hex').toUpperCase(), ts: now(), templateId, template: t.name,
    to: opts.to || '—', toName: opts.name || '', subject: opts.subject || t.name, body: opts.body || '',
    opened: false, clicked: false,
  };
  emails().unshift(e);
  logEvent({ actor: 'system', role: 'system', action: 'email_sent', jobId: null, from: null, to: null, note: t.name + ' → ' + e.to });
  // NOTE: real delivery goes through SMTP/ESP here — kept as an in-app outbox for the prototype.
  save(); return e;
}
function emailOutbox(limit) { return emails().slice(0, limit || 100); }
function emailStats(id) {
  const sent = emails().filter(e => e.templateId === id);
  return { sent: sent.length, opens: sent.filter(e => e.opened).length, clicks: sent.filter(e => e.clicked).length };
}

// Apply a validated transition (domain.resolveTransition already checked gates/RBAC).
function applyTransition(jid, role, actor, action, payload) {
  const j = job(jid);
  if (!j) return { error: 'Job not found' };
  const res = D.resolveTransition(j, role, action, payload || {});
  if (res.error) return { error: res.error, gate: res.gate };
  const from = j.status, t = res.transition;
  // first-touch ownership per department (Prod E-rule; Outlet §4)
  const dept = D.ROLES[role] && D.ROLES[role].dept;
  j.owner = j.owner || {};
  if (dept && dept !== 'all' && !j.owner[dept]) j.owner[dept] = actor;
  // merge payload fields the transition captured (machine, printer, courier, reason, proof, tracking…)
  (t.requires || []).forEach(f => { if (payload && payload[f] != null) j[f] = payload[f]; });
  j.status = t.to;
  j.updatedAt = now();
  logEvent({ actor, role, action, jobId: jid, from, to: t.to, note: (payload && payload.reason) || t.note || '', payload: payload || {} });
  save();
  return { job: j, from, to: t.to };
}

// ---- create an order/job at intake (outlet walk-in or online) ----
function createJob(body) {
  const db = load();
  const jid = 'J-' + (10000 + Math.floor(Math.random() * 89999)) + '-1';
  const j = {
    id: jid, orderId: 'O-' + jid.slice(2, 7), channel: body.channel || 'outlet',
    customer: body.customer || 'Walk-in customer', product: body.product || 'Business Card',
    spec: body.spec || '', qty: Number(body.qty) || 100, price: Number(body.price) || 0,
    status: 'intake', paymentValidated: !!body.paymentValidated, paymentValidatedAt: body.paymentValidated ? now() : null,
    creditTerms: !!body.creditTerms, artwork: { file: body.artworkFile || 'artwork.pdf', checkStatus: 'pending' },
    artworkMatches: body.artworkMatches !== false, deadline: body.deadline || null, createdAt: now(), owner: {},
  };
  db.jobs.push(j);
  logEvent({ actor: body.actor || 'outlet', role: 'store_manager', action: 'create_order', jobId: jid, from: null, to: 'intake', note: 'Order created (' + j.channel + ') — ' + j.customer + ' · ' + j.product });
  save();
  return j;
}

// ---- customer orders (storefront checkout → jobs into the ops pipeline) ----
function orders() { const db = load(); if (!db.orders) db.orders = []; return db.orders; }
function order(oid) { return orders().find(o => o.id === oid); }
function createOrder(body) {
  const db = load();
  const yr = new Date().getFullYear();
  const num = 10000 + Math.floor(Math.random() * 89999);
  const oid = 'PO-' + yr + '-' + num;
  const cust = body.customer || {};
  const items = (body.items || []).map((it, i) => ({
    lineNo: i + 1, productId: it.productId, product: it.product || it.name, spec: it.spec || '',
    qty: Number(it.qty) || 1, unitPrice: Number(it.unitPrice) || 0, lineTotal: Number(it.lineTotal) || 0,
    artworks: it.artworks || (it.artworkFile ? [it.artworkFile] : []),
  }));
  // payment: real gateways (stripe/ipay88/fpx/tng) are stubbed to test-mode; bank_transfer stays pending admin validation
  const method = (body.payment && body.payment.method) || 'bank_transfer';
  const GATEWAY = { card_test: 'Stripe', stripe: 'Stripe', ipay88: 'iPay88', fpx: 'iPay88 · FPX', tng: "Touch 'n Go eWallet", bank_transfer: 'Manual bank-in', credit_term: 'Credit terms' };
  const paid = method !== 'bank_transfer' && method !== 'credit_term';
  const jobIds = [];
  // Web/online orders skip the outlet: once paid they go STRAIGHT to prepress (no acknowledge step).
  // Unpaid (bank transfer) waits at intake until payment is validated, then is bumped to prepress.
  items.forEach(it => {
    const jid = 'J-' + num + '-' + it.lineNo;
    const j = {
      id: jid, orderId: oid, channel: 'online', customer: cust.name || 'Online customer',
      product: it.product, spec: it.spec, qty: it.qty, price: it.lineTotal, status: paid ? 'prepress' : 'intake',
      paymentValidated: paid, paymentValidatedAt: paid ? now() : null, creditTerms: method === 'credit_term',
      artwork: { file: (it.artworks && it.artworks[0]) || it.artworkFile || 'pending-upload.pdf', checkStatus: 'pending' }, artworkMatches: true,
      deadline: body.deadline || null, createdAt: now(), acknowledgedAt: paid ? now() : null, owner: {},
    };
    db.jobs.push(j); jobIds.push(jid);
  });
  const ful = body.fulfillment || {};
  const shipTo = body.shipTo || ful.address || (cust.line1 ? cust : null) || null;
  const o = {
    id: oid, userId: body.userId || null, channel: 'online', customer: cust, fulfillment: ful,
    billing: body.billing || shipTo || null, shipTo,
    payment: { method, gateway: GATEWAY[method] || method, reference: (body.payment && body.payment.reference) || (paid ? (method === 'ipay88' ? 'T' + Date.now() : 'ch_' + Math.random().toString(36).slice(2, 12)) : null), proof: (body.payment && body.payment.proof) || null, status: paid ? 'validated' : 'pending', paidAt: paid ? now() : null },
    items, subtotal: Number(body.subtotal) || 0, memberDiscount: Number(body.memberDiscount) || 0,
    coupon: body.coupon || null, couponDiscount: Number(body.couponDiscount) || 0,   // already verified by the route (checkCoupon)
    tax: Number(body.tax) || 0, shipping: Number(body.shipping) || 0, total: Number(body.total) || 0,
    tier: body.tier || 'Standard', status: paid ? 'paid' : 'pending_payment', jobIds, creditApplied: 0, createdAt: now(),
  };
  // apply store credit if requested — capped server-side to balance and order total
  if (body.userId && Number(body.creditApplied) > 0) {
    const cu = findCustomer(body.userId);
    const applied = Math.min(Number(body.creditApplied), cu ? (cu.creditBalance || 0) : 0, o.total);
    if (applied > 0) { o.creditApplied = Math.round(applied * 100) / 100; o.total = Math.round((o.total - applied) * 100) / 100; }
  }
  orders().push(o);
  if (o.creditApplied) creditEntry(body.userId, { reason: 'ORDER_OFFSET', amount: -o.creditApplied, actor: 'customer', orderId: oid });
  // web order successfully placed & paid → prepress is notified an order is in their queue
  if (paid) notify({ type: 'role', role: 'prepress' }, { kind: 'order_placed', title: 'A fresh order just landed for artwork check', body: 'Order ' + oid + ' has come in for ' + (cust.name || 'a customer') + ' (' + items.length + ' item' + (items.length === 1 ? '' : 's') + ')' + (body.fromQuote ? ', from quote ' + body.fromQuote : '') + '. Have a look at the files whenever you’re ready.', cta: 'Open the order →', orderId: oid });
  logEvent({ actor: cust.email || 'online', role: 'customer', action: 'place_order', jobId: null, from: null, to: o.status, note: oid + ' — ' + items.length + ' item(s) · ' + (cust.name || '') + ' · ' + method });
  if (cust.email) sendEmail('order-confirmation', { to: cust.email, name: cust.name, subject: 'Order ' + oid + ' confirmed', body: 'Hi ' + (cust.name || 'there') + ',\n\nThank you — we’ve received order ' + oid + ' (' + items.length + ' item' + (items.length === 1 ? '' : 's') + '), total RM ' + o.total.toFixed(2) + '.\n' + (paid ? 'Payment confirmed — it’s moving into prepress now.' : 'We’ll begin production once payment is confirmed.') + '\n\nTrack it anytime from your dashboard.' });
  save();
  return o;
}
// mark a pending order paid (bank-transfer validated by admin, or a test payment)
function validateOrderPayment(oid, actor) {
  const o = order(oid); if (!o) return { error: 'order not found' };
  o.payment.status = 'validated'; o.payment.paidAt = now(); o.status = 'paid';
  (o.jobIds || []).forEach(jid => { const j = job(jid); if (j) { j.paymentValidated = true; j.paymentValidatedAt = now(); if (j.channel === 'online' && j.status === 'intake') { j.status = 'prepress'; j.acknowledgedAt = now(); } } });
  // payment cleared → the web order can now move into prepress; notify prepress
  notify({ type: 'role', role: 'prepress' }, { kind: 'order_placed', title: 'Payment’s in — an order is ready for you', body: 'We’ve confirmed payment for ' + (o.customer && o.customer.name || 'a customer') + ', so order ' + oid + ' is all set for its artwork check.', cta: 'Open the order →', orderId: oid });
  logEvent({ actor: actor || 'admin', role: 'store_manager', action: 'validate_payment', jobId: null, from: 'pending_payment', to: 'paid', note: oid + ' payment validated' });
  save();
  return { order: o };
}
// customer updates their own profile (Account Information)
function updateProfile(userId, body) {
  const c = findCustomer(userId); if (!c) return { error: 'not signed in' };
  if (body.name != null) c.name = body.name;
  if (body.phone != null) c.phone = body.phone;
  if (body.company != null) c.company = body.company;
  if (body.newsletter != null) c.newsletter = !!body.newsletter;
  save();
  return { customer: publicCustomer(c) };
}
function changePassword(userId, current, next) {
  const c = findCustomer(userId); if (!c) return { error: 'not signed in' };
  if (!verifyPassword(current, c.salt, c.passHash)) return { error: 'Your current password is incorrect.' };
  if (!next || String(next).length < 6) return { error: 'New password must be at least 6 characters.' };
  const { salt, hash } = hashPassword(next); c.salt = salt; c.passHash = hash; save();
  return { ok: true };
}
// order + live status of each linked job (for confirmation & tracking) + customer history (management view)
function orderView(oid) {
  const o = order(oid); if (!o) return null;
  const email = (o.customer && o.customer.email) || '';
  const mine = orders().filter(x => (o.userId && x.userId === o.userId) || (email && x.customer && x.customer.email === email));
  const revenue = mine.filter(x => x.payment && x.payment.status === 'validated').reduce((s, x) => s + (x.total || 0), 0);
  const history = { totalOrders: mine.length, totalRevenue: Math.round(revenue * 100) / 100, avgOrderValue: mine.length ? Math.round((revenue / mine.length) * 100) / 100 : 0 };
  return Object.assign({}, o, { jobs: (o.jobIds || []).map(jid => job(jid)).filter(Boolean), customerHistory: history });
}

// ---- customer accounts + sessions (dependency-free auth via node:crypto) ----
function customers() { const db = load(); if (!db.customers) db.customers = []; return db.customers; }
function sessions() { const db = load(); if (!db.sessions) db.sessions = {}; return db.sessions; }
function hashPassword(pw, salt) {
  salt = salt || crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(String(pw), salt, 64).toString('hex');
  return { salt, hash };
}
function verifyPassword(pw, salt, hash) {
  try {
    const h = crypto.scryptSync(String(pw), salt, 64);
    return crypto.timingSafeEqual(h, Buffer.from(hash, 'hex'));
  } catch (e) { return false; }
}
function publicCustomer(c) {
  if (!c) return null;
  const { passHash, salt, ...rest } = c; return rest;
}
function newSession(userId) {
  const token = crypto.randomBytes(24).toString('hex');
  sessions()[token] = { userId, createdAt: now() };
  save();
  return token;
}
// Member promo code issued at sign-up (the original printoka.com offer): 15% off, no expiry,
// reusable, on all products, for purchases of RM 800 or more. Each account gets its own code.
const WELCOME_COUPON = { pct: 15, minSpend: 800, multiUse: true, expires: null, label: '15% member discount' };
function newWelcomeCoupon() {
  return Object.assign({ code: 'WELCOME15-' + crypto.randomBytes(3).toString('hex').toUpperCase(), createdAt: now() }, WELCOME_COUPON);
}
// is `code` one of this customer's coupons, and does `subtotal` qualify? → { ok, code, pct, discount } | { error }
function checkCoupon(userId, code, subtotal) {
  const c = userId && findCustomer(userId);
  if (!c) return { error: 'Sign in to use your member code.' };
  const want = String(code || '').trim().toUpperCase();
  const cp = (c.coupons || []).find(x => String(x.code).toUpperCase() === want);
  if (!cp) return { error: 'That code isn’t valid on your account.' };
  if (cp.expires && new Date(cp.expires) < new Date()) return { error: 'That code has expired.' };
  if (!cp.multiUse && cp.usedAt) return { error: 'That code has already been used.' };
  const sub = Number(subtotal) || 0;
  if (sub < cp.minSpend) return { error: 'This code applies to orders of RM ' + cp.minSpend + ' or more.', code: cp.code, pct: cp.pct, minSpend: cp.minSpend };
  return { ok: true, code: cp.code, pct: cp.pct, minSpend: cp.minSpend, discount: Math.round(sub * cp.pct) / 100 };
}
function registerCustomer(body) {
  const email = String(body.email || '').trim().toLowerCase();
  if (!email || !body.password) return { error: 'Email and password are required.' };
  if (String(body.password).length < 6) return { error: 'Password must be at least 6 characters.' };
  if (customers().find(c => c.email === email)) return { error: 'An account with that email already exists.' };
  const { salt, hash } = hashPassword(body.password);
  const c = {
    id: 'C-' + crypto.randomBytes(4).toString('hex').toUpperCase(), email, passHash: hash, salt, type: 'customer', role: 'customer',
    name: body.name || email.split('@')[0], phone: body.phone || '', company: body.company || '',
    tier: 'Standard', spend12mo: 0, creditBalance: 0, addresses: [], creditLedger: [], createdAt: now(),
    coupons: [newWelcomeCoupon()],
  };
  customers().push(c);
  const cp = c.coupons[0];
  logEvent({ actor: email, role: 'customer', action: 'register', jobId: null, from: null, to: null, note: 'New customer account ' + c.id + ' · promo ' + cp.code });
  sendEmail('new-account', { to: c.email, name: c.name, subject: 'Welcome to Printoka — here’s your 15% discount code', body: 'Hi ' + c.name + ',\n\nYour Printoka account is ready. As a welcome, here’s your member discount code:\n\n' + cp.code + '\n\n15% off every order of RM ' + cp.minSpend + ' or more. No expiry, use it as many times as you like, on all products. Enter it in your cart.\n\nHappy printing,\nThe Printoka team' });
  save();
  return { customer: publicCustomer(c), token: newSession(c.id) };
}
function loginCustomer(body) {
  const email = String(body.email || '').trim().toLowerCase();
  const c = customers().find(x => x.email === email);
  // NOTE: migrated WP users would verify against their phpass hash here, then re-hash into scrypt (audit §9).
  if (!c || !verifyPassword(body.password, c.salt, c.passHash)) return { error: 'Wrong email or password.' };
  return { customer: publicCustomer(c), token: newSession(c.id) };
}
function sessionCustomer(token) {
  const s = token && sessions()[token]; if (!s) return null;
  return publicCustomer(customers().find(c => c.id === s.userId));
}
function logout(token) { if (token && sessions()[token]) { delete sessions()[token]; save(); } return { ok: true }; }
function ordersForUser(userId) { return orders().filter(o => o.userId === userId); }
function findCustomer(userId) { return customers().find(c => c.id === userId); }

// ---- address book (B8) ----
function getAddresses(userId) { const c = findCustomer(userId); return c ? (c.addresses || []) : []; }
function addAddress(userId, a) {
  const c = findCustomer(userId); if (!c) return { error: 'not signed in' };
  c.addresses = c.addresses || [];
  const addr = { id: 'A-' + crypto.randomBytes(3).toString('hex').toUpperCase(), label: a.label || 'Address', name: a.name || c.name, phone: a.phone || c.phone, line1: a.line1 || '', line2: a.line2 || '', city: a.city || '', postcode: a.postcode || '', state: a.state || '', country: a.country || 'MY', isDefault: !!a.isDefault || c.addresses.length === 0 };
  if (addr.isDefault) c.addresses.forEach(x => x.isDefault = false);
  c.addresses.push(addr); save();
  return { addresses: c.addresses };
}
function deleteAddress(userId, addrId) {
  const c = findCustomer(userId); if (!c) return { error: 'not signed in' };
  const was = (c.addresses || []).find(x => x.id === addrId);
  c.addresses = (c.addresses || []).filter(x => x.id !== addrId);
  if (was && was.isDefault && c.addresses.length) c.addresses[0].isDefault = true;
  save(); return { addresses: c.addresses };
}
function setDefaultAddress(userId, addrId) {
  const c = findCustomer(userId); if (!c) return { error: 'not signed in' };
  (c.addresses || []).forEach(x => x.isDefault = x.id === addrId);
  save(); return { addresses: c.addresses };
}

// ---- credit-balance ledger (B6) ----
function getCredit(userId) { const c = findCustomer(userId); return c ? { balance: c.creditBalance || 0, ledger: c.creditLedger || [] } : { balance: 0, ledger: [] }; }
function creditEntry(userId, { reason, amount, actor, orderId }) {
  const c = findCustomer(userId); if (!c) return { error: 'not signed in' };
  amount = Math.round(Number(amount) * 100) / 100;
  c.creditBalance = Math.round(((c.creditBalance || 0) + amount) * 100) / 100;
  c.creditLedger = c.creditLedger || [];
  c.creditLedger.unshift({ id: 'L-' + crypto.randomBytes(3).toString('hex').toUpperCase(), ts: now(), reason: reason || 'ADJUSTMENT', amount, actor: actor || 'system', orderId: orderId || null, balanceAfter: c.creditBalance });
  logEvent({ actor: actor || 'system', role: 'customer', action: 'credit', jobId: null, from: null, to: null, note: c.id + ' ' + reason + ' ' + amount + ' → ' + c.creditBalance });
  sendEmail('wallet-transaction', { to: c.email, name: c.name, subject: 'Wallet ' + (amount >= 0 ? 'top-up' : 'deduction') + ' — RM ' + Math.abs(amount).toFixed(2), body: 'Hi ' + c.name + ',\n\nA ' + (amount >= 0 ? 'credit' : 'debit') + ' of RM ' + Math.abs(amount).toFixed(2) + ' (' + (reason || 'adjustment') + ') was applied to your Printoka wallet.\nNew balance: RM ' + c.creditBalance.toFixed(2) + '.' + (orderId ? '\nReference: ' + orderId : '') });
  save();
  return { balance: c.creditBalance, ledger: c.creditLedger };
}

// ---- store settings (announcement bar, etc.) ----
function settings() {
  const db = load();
  if (!db.settings) db.settings = {};
  const s = db.settings;
  if (!s.announcement) s.announcement = { text: 'Members save up to 15% on every order — sign in to see your price. Free delivery on orders over RM 300.', cta: 'Find out more', link: 'membership', hidden: false };
  if (!s.store) s.store = { name: 'Printoka', supportEmail: 'print@printoka.com', supportPhone: '+60 14 969 0799', countries: 'Malaysia, Singapore, Brunei', currency: 'MYR (RM)' };
  if (!s.theme) s.theme = { primary: '#E52220', heroTitle: 'Custom printing, priced instantly.', heroSub: 'Configure any of 100+ products and see the exact price in seconds.' };
  return s;
}
function updateSettings(patch, actor) {
  const s = settings();
  Object.keys(patch || {}).forEach(k => {
    if (patch[k] && typeof patch[k] === 'object' && !Array.isArray(patch[k])) s[k] = Object.assign({}, s[k], patch[k]);
    else s[k] = patch[k];
  });
  logEvent({ actor: actor || 'admin', role: 'production_director', action: 'settings_edit', jobId: null, from: null, to: null, note: 'settings updated: ' + Object.keys(patch || {}).join(', ') });
  save();
  return s;
}

// ---- catalogue overrides (admin display-name / category edits) ----
function catalogue() { const db = load(); if (!db.catalogue) db.catalogue = {}; return db.catalogue; }
function setOverride(pid, patch, actor) {
  const c = catalogue();
  c[String(pid)] = Object.assign({}, c[String(pid)], patch);
  logEvent({ actor: actor || 'admin', role: 'production_director', action: 'catalogue_edit', jobId: null, from: null, to: null, note: 'product ' + pid + ': ' + JSON.stringify(patch) });
  save();
  return c[String(pid)];
}

// ---- outsource / vendor quotation flow (Scheduler ↔ Vendor/Hub) ----
// Scheduler requests quotes from vendors → vendors respond price+lead time →
// scheduler awards a PO to the best → vendor prints a shipping label. (audit §5 lifecycle)
function vendorAccounts() { return customers().filter(c => c.type === 'vendor'); }
function requestVendorQuotes(jobId, vendorIds, actor) {
  const j = job(jobId); if (!j) return { error: 'job not found' };
  if (!vendorIds || !vendorIds.length) return { error: 'pick at least one vendor' };
  j.outsource = { status: 'requested', requestedAt: now(),
    vendors: vendorIds.map(vid => { const v = findCustomer(vid) || {}; return { vendorId: vid, vendorName: v.name || vid, price: null, leadDays: null, note: '', submittedAt: null }; }),
    awardedTo: null, po: null, label: null };
  vendorIds.forEach(vid => { const v = findCustomer(vid); if (v && v.email) sendEmail('request-quote-printer', { to: v.email, name: v.name, subject: 'Quote request — ' + j.product + ' (job ' + jobId + ')', body: 'Hi ' + v.name + ',\n\nWe’d like your best price and lead time for:\n' + j.product + ' · ' + (j.spec || '') + ' · qty ' + j.qty + '\nDeliver to: ' + (j.fulfillmentOutlet || 'destination outlet') + '.\n\nSubmit your quote in your vendor portal.' }); });
  logEvent({ actor: actor || 'scheduler', role: 'scheduler_staff', action: 'request_quotes', jobId, from: j.status, to: 'requested', note: 'Quotes requested from ' + vendorIds.length + ' vendor(s)' });
  save(); return { job: j };
}
function submitVendorQuote(jobId, vendorId, body) {
  const j = job(jobId); if (!j || !j.outsource) return { error: 'no open quote request' };
  const v = j.outsource.vendors.find(x => x.vendorId === vendorId); if (!v) return { error: 'you were not invited to quote this job' };
  if (j.outsource.awardedTo) return { error: 'this job has already been awarded' };
  v.price = Number(body.price) || 0; v.leadDays = Number(body.leadDays) || 0; v.note = body.note || ''; v.submittedAt = now();
  const submitted = j.outsource.vendors.filter(x => x.submittedAt).length;
  j.outsource.status = submitted === j.outsource.vendors.length ? 'quotes_received' : 'partly_received';
  logEvent({ actor: vendorId, role: 'printer', action: 'submit_quote', jobId, from: null, to: j.outsource.status, note: 'Quote RM ' + v.price + ' · ' + v.leadDays + ' days' });
  save(); return { job: j };
}
function awardVendorPO(jobId, vendorId, actor) {
  const j = job(jobId); if (!j || !j.outsource) return { error: 'no quote request' };
  const v = j.outsource.vendors.find(x => x.vendorId === vendorId && x.submittedAt); if (!v) return { error: 'that vendor has not submitted a quote' };
  const po = 'PO-' + (jobId.replace(/[^0-9]/g, '').slice(0, 5) || '00000') + '-' + Math.floor(Math.random() * 900 + 100);
  j.outsource.awardedTo = vendorId; j.outsource.status = 'awarded'; j.outsource.po = po; j.outsource.awardedAt = now();
  j.outsource.label = { id: 'LBL-' + po, po, vendor: v.vendorName, customer: j.customer, order: j.orderId, dest: (j.fulfillmentOutlet || 'KL Damansara Outlet'), product: j.product, qty: j.qty };
  j.status = 'outsourcing';
  const av = findCustomer(vendorId);
  if (av && av.email) sendEmail('job-award-printer', { to: av.email, name: v.vendorName, subject: 'You won the job — ' + po, body: 'Hi ' + v.vendorName + ',\n\nCongratulations — ' + po + ' has been awarded to you.\n' + j.product + ' · qty ' + j.qty + ' @ RM ' + v.price + ' · ' + v.leadDays + ' days.\nPrint the shipping label from your vendor portal and deliver to ' + ((j.outsource.label && j.outsource.label.dest) || 'the destination outlet') + '.' });
  logEvent({ actor: actor || 'scheduler', role: 'scheduler_staff', action: 'award_po', jobId, from: 'quotes_received', to: 'outsourcing', note: 'Awarded ' + po + ' to ' + v.vendorName + ' @ RM ' + v.price });
  save(); return { job: j };
}
function vendorRequests(vendorId) { return jobs().filter(j => j.outsource && j.outsource.vendors.some(v => v.vendorId === vendorId)); }

// ---- custom quotes (request → price/issue → accept becomes an order) ----
function quotes() { const db = load(); if (!db.quotes) db.quotes = []; return db.quotes; }
function quote(qid) { return quotes().find(q => q.id === qid); }
function quotesForUser(userId) { return quotes().filter(q => q.userId === userId); }
function createQuote(body, user) {
  const qid = 'QT-' + (1000 + Math.floor(Math.random() * 8999));
  const cust = body.customer || (user ? { name: user.name, email: user.email, phone: user.phone, company: user.company } : {});
  const q = {
    id: qid, userId: user ? user.id : null, channel: (user && user.type === 'outlet') ? 'outlet' : 'online', customer: cust,
    requirement: { product: body.product || '', size: body.size || '', material: body.material || '', finishing: body.finishing || '', qty: body.qty || '', remarks: body.remarks || '' },
    // custom-quote questionnaire (Customized Printing Solutions): form id + every [section, question, answer]
    form: body.form || null, answers: Array.isArray(body.answers) ? body.answers.slice(0, 80).map(a => [String(a[0] || ''), String(a[1] || ''), String(a[2] || '')]) : null,
    artworkFile: body.artworkFile || null, status: 'requested', price: null, leadDays: null, note: '', orderId: null,
    createdAt: now(), history: [{ ts: now(), actor: (user && user.email) || cust.email || 'guest', action: 'requested' }],
  };
  quotes().push(q);
  logEvent({ actor: (user && user.email) || cust.email || 'guest', role: 'customer', action: 'quote_request', jobId: null, from: null, to: 'requested', note: qid + ' · ' + (q.requirement.product || 'custom') });
  save(); return q;
}
function priceQuote(qid, body, actor) {
  const q = quote(qid); if (!q) return { error: 'quote not found' };
  q.price = Number(body.price) || 0; q.leadDays = Number(body.leadDays) || 0; q.note = body.note || ''; q.status = 'issued'; q.issuedAt = now(); q.viewedAt = null;
  q.history.push({ ts: now(), actor: actor || 'staff', action: 'issued', price: q.price });
  // quote sent to the customer's account → notify customer, and the originating outlet (if walk-in)
  const qprod = (q.requirement && q.requirement.product) || 'your job';
  if (q.userId) notify({ type: 'customer', id: q.userId }, { kind: 'quote_issued', title: 'Good news — your quote is ready! 🎉', body: 'Your quote for ' + qprod + ' comes to RM ' + q.price.toLocaleString() + (q.leadDays ? ', ready in about ' + q.leadDays + ' day' + (q.leadDays === 1 ? '' : 's') : '') + '. Take a look whenever you like and let us know what you’d like to do.', cta: 'View your quote →', quoteId: qid });
  if (q.outlet) notify({ type: 'outlet', outlet: q.outlet }, { kind: 'quote_issued', title: 'Your customer’s quote is on its way to them', body: 'We’ve priced ' + ((q.customer && q.customer.name) || 'your customer') + '’s quote for ' + qprod + ' at RM ' + q.price.toLocaleString() + ' and sent it to their account. We’ll let you know as soon as they’ve had a look.', cta: 'See the quote →', quoteId: qid });
  if (q.customer && q.customer.email) sendEmail('quote-issued', { to: q.customer.email, name: q.customer.name, subject: 'Your quote ' + qid + ' is ready — RM ' + q.price.toLocaleString(), body: 'Hi ' + ((q.customer && q.customer.name) || 'there') + ',\n\nGood news — your quote for ' + qprod + ' is ready: RM ' + q.price.toLocaleString() + (q.leadDays ? ', ready in about ' + q.leadDays + ' days' : '') + '.\nSign in to view it and accept & pay, or ask for changes.' });
  logEvent({ actor: actor || 'staff', role: 'scheduler_staff', action: 'quote_issued', jobId: null, from: 'requested', to: 'issued', note: qid + ' · RM ' + q.price });
  save(); return { quote: q };
}
// customer opens/views an issued quote → mark reviewed, notify the originating outlet
function viewQuote(qid, user) {
  const q = quote(qid); if (!q) return { error: 'quote not found' };
  if (!user || user.id !== q.userId) return { quote: q }; // only the owner viewing counts
  if (!q.viewedAt && (q.status === 'issued' || q.status === 'reviewed')) {
    q.viewedAt = now(); if (q.status === 'issued') q.status = 'reviewed';
    q.history.push({ ts: now(), actor: user.email || user.name, action: 'reviewed' });
    if (q.outlet) notify({ type: 'outlet', outlet: q.outlet }, { kind: 'quote_reviewed', title: ((q.customer && q.customer.name) || 'Your customer') + ' just had a look at their quote', body: ((q.customer && q.customer.name) || 'Your customer') + ' has opened quote ' + qid + '. This could be a lovely moment to check in and see what they think.', cta: 'Follow up →', quoteId: qid });
    logEvent({ actor: user.email || 'customer', role: 'customer', action: 'quote_reviewed', jobId: null, from: 'issued', to: 'reviewed', note: qid });
    save();
  }
  return { quote: q };
}
function rejectQuote(qid, reason, actor) {
  const q = quote(qid); if (!q) return { error: 'quote not found' };
  q.status = 'rejected'; q.rejectReason = reason || ''; q.history.push({ ts: now(), actor: actor || 'customer', action: 'rejected', note: reason || '' });
  save(); return { quote: q };
}
function acceptQuote(qid, actor) {
  const q = quote(qid); if (!q) return { error: 'quote not found' };
  if (q.status !== 'issued' && q.status !== 'reviewed') return { error: 'only an issued quote can be accepted' };
  const qty = Number(q.requirement.qty) || 1;
  const o = createOrder({
    userId: q.userId, customer: q.customer,
    items: [{ productId: null, product: q.requirement.product || 'Custom quote', spec: q.requirement.quoteData || [q.requirement.size, q.requirement.material, q.requirement.finishing].filter(Boolean).join(' · '), qty, unitPrice: q.price / qty, lineTotal: q.price, artworks: q.artworkFile ? [q.artworkFile] : [] }],
    subtotal: q.price, memberDiscount: 0, tax: 0, shipping: 0, total: q.price, payment: { method: 'card_test' }, fromQuote: qid,
  });
  q.status = 'accepted'; q.orderId = o.id; q.decision = 'proceed'; q.history.push({ ts: now(), actor: actor || 'customer', action: 'accepted', note: 'Order ' + o.id });
  // customer converted the quote to an order → the originating outlet is notified (prepress already notified by createOrder)
  if (q.outlet) notify({ type: 'outlet', outlet: q.outlet }, { kind: 'quote_converted', title: 'Wonderful — ' + ((q.customer && q.customer.name) || 'your customer') + ' is going ahead! 🎉', body: ((q.customer && q.customer.name) || 'Your customer') + ' has accepted quote ' + qid + ', and it’s now order ' + o.id + ' making its way into production.', cta: 'View the order →', quoteId: qid, orderId: o.id });
  logEvent({ actor: actor || 'customer', role: 'customer', action: 'quote_accepted', jobId: null, from: q.status, to: 'accepted', note: qid + ' → order ' + o.id });
  save(); return { quote: q, order: o };
}
// walk-in quote: outlet staff signs the customer up + files a quote request to the Scheduler
function createWalkinQuote(body, staff) {
  const c = body.customer || {};
  let cust = null, createdAccount = false, tempPassword = null;
  const email = String(c.email || '').trim().toLowerCase();
  if (email) cust = customers().find(x => x.email === email && x.type === 'customer');
  if (!cust) {
    tempPassword = 'pk' + crypto.randomBytes(3).toString('hex');
    const reg = registerCustomer({ email: email || ('walkin+' + crypto.randomBytes(3).toString('hex') + '@printoka.my'), password: tempPassword, name: c.name || 'Walk-in customer', phone: c.phone || '', company: c.company || '' });
    if (reg.error) return { error: reg.error };
    cust = findCustomer(reg.customer.id); createdAccount = true;
    if (cust) { cust.createdByOutlet = staff && staff.outlet; cust.walkinCreated = true; }
  }
  const qid = 'QT-' + (1000 + Math.floor(Math.random() * 8999));
  const q = {
    id: qid, userId: cust.id, channel: 'outlet', walkin: true, outlet: (staff && staff.outlet) || null, requestedByStaff: (staff && staff.name) || 'Outlet', assignedTo: 'scheduler',
    customer: { name: cust.name, email: cust.email, phone: cust.phone, company: cust.company || '' },
    requirement: { product: body.product || 'Custom job', qty: body.qty || '', size: body.size || '', material: body.material || '', finishing: body.finishing || '', remarks: body.remarks || '', quoteData: body.quoteData || '' },
    artworkFile: body.artworkFile || null, status: 'requested', price: null, leadDays: null, note: '', remarks: '', decision: null, viewedAt: null, orderId: null,
    createdAt: now(), history: [{ ts: now(), actor: (staff && staff.name) || 'outlet', action: 'requested', note: 'Walk-in at ' + ((staff && staff.outlet) || 'outlet') }],
  };
  quotes().push(q);
  // quote request goes to the Scheduler for review/pricing
  notify({ type: 'role', role: 'scheduler' }, { kind: 'quote_request', title: 'A walk-in quote is waiting for your pricing', body: ((staff && staff.outlet) || 'An outlet') + ' has a new request from ' + cust.name + ' for ' + q.requirement.product + (q.requirement.qty ? ' × ' + q.requirement.qty : '') + '. Pop in a price whenever you get a chance.', cta: 'Price this quote →', quoteId: qid });
  logEvent({ actor: (staff && staff.email) || 'outlet', role: 'store_manager', action: 'walkin_quote', jobId: null, from: null, to: 'requested', note: qid + ' · ' + cust.name + ' → scheduler' });
  save();
  return { quote: q, customer: publicCustomer(cust), createdAccount, tempPassword };
}
// outlet/admin creates a customer account on the customer's behalf ("Create new user")
function createCustomerByStaff(body, staff) {
  const email = String(body.email || '').trim().toLowerCase();
  if (!email) return { error: 'An email address is required to create the account.' };
  if (customers().find(c => c.email === email)) return { error: 'An account with that email already exists.' };
  const tempPassword = 'pk' + crypto.randomBytes(3).toString('hex');
  const name = [body.firstName, body.lastName].filter(Boolean).join(' ') || body.name || email.split('@')[0];
  const reg = registerCustomer({ email, password: tempPassword, name, phone: body.phone || '', company: body.company || '' });
  if (reg.error) return reg;
  const c = findCustomer(reg.customer.id);
  if (c) {
    c.createdByOutlet = (staff && staff.outlet) || null; c.walkinCreated = true; c.promoOptIn = !!body.promo;
    if (body.address || body.city || body.country) c.addresses = [{ id: 'A-' + crypto.randomBytes(3).toString('hex').toUpperCase(), label: 'Home', name, phone: body.phone || '', line1: body.address || '', line2: '', city: body.city || '', postcode: body.postcode || '', state: body.state || '', country: body.country || 'MY', isDefault: true }];
    save();
  }
  return { customer: publicCustomer(c), tempPassword, createdAccount: true };
}
// outlet records the customer's decision (proceed / not_proceed / amend) and pushes it to the Scheduler
function recordQuoteDecision(qid, decision, remark, staff) {
  const q = quote(qid); if (!q) return { error: 'quote not found' };
  q.decision = decision; q.remarks = remark || q.remarks || '';
  q.history.push({ ts: now(), actor: (staff && staff.name) || 'outlet', action: 'decision', note: decision + (remark ? ' — ' + remark : '') });
  if (decision === 'amend') {
    q.status = 'amendment';
    notify({ type: 'role', role: 'scheduler' }, { kind: 'quote_amend', title: ((q.customer && q.customer.name) || 'A customer') + ' would like a little change', body: ((q.outlet) || 'The outlet') + ' has passed on a change request for ' + qid + ': ' + (remark || 'the customer would like an amendment') + '. Could you take another look when you have a moment?', cta: 'Revisit the quote →', quoteId: qid });
  } else if (decision === 'not_proceed') {
    q.status = 'declined';
    notify({ type: 'role', role: 'scheduler' }, { kind: 'quote_declined', title: 'Heads up — ' + qid + ' won’t be going ahead', body: ((q.customer && q.customer.name) || 'The customer') + ' has decided not to proceed for now' + (remark ? ' (' + remark + ')' : '') + '. Nothing more needed on this one.', quoteId: qid });
  } else if (decision === 'proceed') {
    // outlet confirms the customer wants it — convert to an order on their behalf
    return acceptQuote(qid, (staff && staff.name) || 'outlet');
  }
  logEvent({ actor: (staff && staff.name) || 'outlet', role: 'store_manager', action: 'quote_decision', jobId: null, from: null, to: q.status, note: qid + ' · ' + decision });
  save(); return { quote: q };
}

// ---- manual custom quote (staff/outlet prepares a quote directly, with a free-text body) ----
function createManualQuote(body, staff) {
  const qid = 'Q-' + crypto.randomBytes(3).toString('hex').toUpperCase();
  const cust = body.customer || {};
  const price = Number(body.price) || 0;
  const q = {
    id: qid, userId: body.userId || null, channel: (staff && staff.type === 'outlet') ? 'outlet' : 'online', manual: true, customer: cust,
    requirement: { product: body.product || 'Custom job', qty: body.qty || '', size: '', material: '', finishing: '', remarks: '', weight: body.weight || '', quoteData: body.quoteData || '' },
    artworkFile: body.artworkFile || null, price, leadDays: Number(body.leadDays) || 0, status: price > 0 ? 'issued' : 'requested', note: body.note || '', remarks: body.remarks || '',
    staff: { name: (staff && staff.name) || 'Staff', outlet: (staff && staff.outlet) || '' }, orderId: null, createdAt: now(),
    history: [{ ts: now(), actor: (staff && staff.name) || 'staff', action: price > 0 ? 'issued' : 'created', price }],
  };
  if (price > 0) q.issuedAt = now();
  quotes().push(q);
  logEvent({ actor: (staff && staff.email) || 'staff', role: 'store_manager', action: 'quote_created', jobId: null, from: null, to: q.status, note: qid + ' · ' + q.requirement.product + ' · RM ' + price });
  save(); return q;
}
function setQuoteRemark(qid, remarks, actor) {
  const q = quote(qid); if (!q) return { error: 'quote not found' };
  q.remarks = remarks || ''; save(); return { quote: q };
}

// ---- custom invoices (staff/outlet prepares an invoice directly to a customer) ----
function customInvoices() { const db = load(); if (!db.customInvoices) db.customInvoices = []; return db.customInvoices; }
function customInvoice(cid) { return customInvoices().find(x => x.id === cid); }
function customInvoicesForUser(userId) { return customInvoices().filter(x => x.userId === userId); }
function createCustomInvoice(body, staff) {
  const cid = 'CINV-' + new Date().getFullYear() + '-' + String(customInvoices().length + 1).padStart(4, '0');
  const inv = {
    id: cid, number: body.number || ('INV' + new Date().getFullYear() + String(customInvoices().length + 1).padStart(3, '0')),
    date: body.date || now().slice(0, 10), status: body.status || 'unpaid', userId: body.userId || null, userName: body.userName || '',
    currency: body.currency || 'MYR', price: Number(body.price) || 0, orderId: body.orderId || '', description: body.description || '',
    createdBy: { name: (staff && staff.name) || 'Staff', type: (staff && staff.type) || 'admin', outlet: (staff && staff.outlet) || '' }, createdAt: now(),
  };
  customInvoices().unshift(inv);
  logEvent({ actor: (staff && staff.email) || 'staff', role: 'store_manager', action: 'custom_invoice_created', jobId: null, from: null, to: inv.status, note: cid + ' · ' + inv.userName + ' · RM ' + inv.price });
  save(); return inv;
}
function updateCustomInvoice(cid, patch, actor) {
  const inv = customInvoice(cid); if (!inv) return { error: 'invoice not found' };
  ['number', 'date', 'status', 'userId', 'userName', 'currency', 'price', 'orderId', 'description'].forEach(k => { if (patch[k] !== undefined) inv[k] = k === 'price' ? Number(patch[k]) || 0 : patch[k]; });
  logEvent({ actor: actor || 'staff', role: 'store_manager', action: 'custom_invoice_edit', jobId: null, from: null, to: inv.status, note: cid + ' updated' });
  save(); return { invoice: inv };
}

module.exports = { checkCoupon, load, save, reset, jobs, job, users, audit, applyTransition, logEvent, now, id, catalogue, setOverride, createJob, orders, order, createOrder, validateOrderPayment, orderView, registerCustomer, loginCustomer, sessionCustomer, logout, ordersForUser, publicCustomer, customers, findCustomer, getAddresses, addAddress, deleteAddress, setDefaultAddress, getCredit, creditEntry, vendorAccounts, requestVendorQuotes, submitVendorQuote, awardVendorPO, vendorRequests, quotes, quote, quotesForUser, createQuote, priceQuote, rejectQuote, acceptQuote, createManualQuote, setQuoteRemark, customInvoices, customInvoice, customInvoicesForUser, createCustomInvoice, updateCustomInvoice, notifications, notify, notificationsFor, markNotificationRead, viewQuote, createWalkinQuote, recordQuoteDecision, createCustomerByStaff, updateProfile, changePassword, settings, updateSettings, emailTemplates, emailOutbox, emailStats, setEmailActive, sendEmail };
