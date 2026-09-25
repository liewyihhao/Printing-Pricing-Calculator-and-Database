/*
 * Printoka operations layer on top of the job state machine (store.js + domain.js):
 *
 *   · Ops settings (CMS): hubs, outlets, machines, couriers — editable by managers/admin
 *   · Every job carries a destination, an assigned hub/outlet and a shipping label from the moment
 *     the order is placed (Qn 752 CF1 "all orders automatically include a shipping label and an
 *     assigned hub or outlet")
 *   · Send to internal production with delivery instructions → Hub / Outlet / Customer (Qn 752 CF1)
 *   · Award a job to a printer that hasn't quoted, with an explicit confirmation (Qn 752 CF2)
 *   · Interactive progress forms: in-house production, hub handling, logistics packing (Qn 750/732)
 *   · Side effects of every transition: status timestamps, shipments, label regeneration,
 *     customer/outlet/hub notifications, and the order's customer-facing progress
 *   · KPIs per department, sales performance, hub performance and the action tracker —
 *     all computed from the jobs, orders and the append-only audit log (never hand-entered)
 */
const store = require('./store');
const D = require('./domain');

const now = () => new Date().toISOString();
const DAY = 864e5;

// ---- settings (CMS) ---------------------------------------------------------
const EAST_MY = ['Sarawak', 'Sabah', 'Labuan'];
const MY_STATES = ['Johor', 'Kedah', 'Kelantan', 'Melaka', 'Malacca', 'Negeri Sembilan', 'Pahang', 'Penang', 'Pulau Pinang', 'Perak', 'Perlis', 'Sabah', 'Sarawak', 'Selangor', 'Terengganu', 'Kuala Lumpur', 'Labuan', 'Putrajaya'];
const DEFAULT_CONFIG = {
  hubs: [
    { id: 'HUB-MIRI', name: 'Miri Hub (HQ facility)', address: 'Lot 1565, Piasau Industrial Estate, 98000 Miri, Sarawak', states: EAST_MY.slice(), countries: ['BN'] },
    { id: 'HUB-KL', name: 'Klang Valley Hub', address: '', states: MY_STATES.filter(s => EAST_MY.indexOf(s) < 0), countries: ['SG'] },
  ],
  outlets: [
    { id: 'KL-Damansara', name: 'KL Damansara Outlet', address: '', hub: 'HUB-KL', pickup: true },
    { id: 'Miri', name: 'Miri Outlet (own facility)', address: 'Lot 1565, Piasau Industrial Estate, 98000 Miri, Sarawak', hub: 'HUB-MIRI', pickup: true },
  ],
  machines: ['Digital press 1', 'Digital press 2', 'Offset press', 'Large-format printer', 'Sticker / label cutter', 'Finishing line'],
  couriers: ['J&T Express', 'Pos Laju', 'GDEX', 'City-Link Express', 'Lalamove', 'Printoka van'],
  productionSite: 'Printoka Production · Miri',
  productionAddress: 'Lot 1565, Piasau Industrial Estate, 98000 Miri, Sarawak',
  productionPhone: '014-969 0799',
};
function config() {
  const db = store.load();
  if (!db.opsConfig) db.opsConfig = JSON.parse(JSON.stringify(DEFAULT_CONFIG));
  ['productionAddress', 'productionPhone'].forEach(k => { if (db.opsConfig[k] == null) db.opsConfig[k] = DEFAULT_CONFIG[k]; });
  return db.opsConfig;
}
function saveConfig(patch, actor) {
  const c = config();
  ['hubs', 'outlets', 'machines', 'couriers', 'productionSite', 'productionAddress', 'productionPhone'].forEach(k => { if (patch[k] !== undefined) c[k] = patch[k]; });
  store.logEvent({ actor: actor || 'admin', role: 'production_director', action: 'ops_settings', jobId: null, from: null, to: null, note: 'Operations settings updated (' + Object.keys(patch).join(', ') + ')' });
  store.save(); return c;
}
const hubById = id => config().hubs.find(x => x.id === id) || null;
const outletById = id => config().outlets.find(x => x.id === id || x.name === id) || null;

// which hub serves an address / outlet (East Malaysia + Brunei → Miri; the rest → Klang Valley)
function hubForText(text, country) {
  const hubs = config().hubs; const t = String(text || '');
  for (const hb of hubs) if ((hb.states || []).some(s => new RegExp('\\b' + s + '\\b', 'i').test(t))) return hb.id;
  for (const hb of hubs) if (country && (hb.countries || []).indexOf(country) >= 0) return hb.id;
  return (hubs[hubs.length - 1] || {}).id || null;
}
function hubForDestination(dest) {
  if (!dest) return null;
  if (dest.type === 'hub') return dest.id;
  if (dest.type === 'outlet') { const o = outletById(dest.id); return (o && o.hub) || hubForText(o && o.address); }
  return hubForText(dest.address, dest.country);
}
function destOf(type, id, j, ord) {
  if (type === 'production') { const c = config(); return { type: 'production', id: 'PRODUCTION', name: c.productionSite, address: c.productionAddress || '', phone: c.productionPhone || '' }; }
  if (type === 'hub') { const hb = hubById(id || j.hub) || config().hubs[0]; return { type: 'hub', id: hb.id, name: hb.name, address: hb.address || '' }; }
  if (type === 'outlet') { const o = outletById(id) || outletById((j.finalDestination || {}).id) || config().outlets[0]; return { type: 'outlet', id: o.id, name: o.name, address: o.address || '' }; }
  // customer: the order's delivery address
  const fd = j.finalDestination && j.finalDestination.type === 'customer' ? j.finalDestination : null;
  if (fd) return Object.assign({}, fd);
  const addr = ord && (typeof ord.shipTo === 'string' ? ord.shipTo : ord.shipTo ? [ord.shipTo.line1, ord.shipTo.line2, ord.shipTo.postcode, ord.shipTo.city, ord.shipTo.state].filter(Boolean).join(', ') : '');
  return { type: 'customer', id: null, name: j.customer, address: addr || '', phone: (ord && ord.customer && ord.customer.phone) || '' };
}
function origin(j) {
  if (j.route === 'outsource' && j.outsource && j.outsource.awardedTo) { const v = j.outsource.vendors.find(x => x.vendorId === j.outsource.awardedTo); return (v && v.vendorName) || 'Partner printer'; }
  if (j.status === 'at_hub' || (j.shipments || []).some(s => s.to && s.to.type === 'hub' && s.receivedAt)) { const hb = hubById(j.hub); return hb ? hb.name : 'Hub'; }
  return config().productionSite;
}
// the shipping label that travels with the job; regenerated whenever the destination changes
function makeLabel(j) {
  const d = j.destination || {}; const hb = hubById(j.hub);
  const leg = (j.shipments || []).length + 1;
  j.label = { id: 'LBL-' + j.id + (leg > 1 ? '-' + leg : ''), orderId: j.orderId, jobId: j.id, from: origin(j),
    toType: d.type, toName: d.name, toAddress: d.address || '', toPhone: d.phone || '', attn: j.customer,
    product: j.product, qty: j.qty, parcels: j.parcels || 1, hub: hb ? hb.name : '', instructions: j.instructions || '', createdAt: now() };
  return j.label;
}
// give a job its destination / hub / label / timestamps if it doesn't have them yet
function normalizeJob(j) {
  const ord = j.orderId ? store.order(j.orderId) : null;
  let changed = false;
  if (!j.finalDestination) {
    const ful = (ord && ord.fulfillment) || {};
    j.finalDestination = ful.method === 'pickup' ? destOf('outlet', ful.outlet || (j.fulfillmentOutlet), j, ord) : destOf('customer', null, j, ord);
    changed = true;
  }
  // (no hub routing in the production flow — parcels go production → outlet / customer)
  if (!j.destination) { j.destination = Object.assign({}, j.finalDestination); changed = true; }
  if (!j.label) { makeLabel(j); changed = true; }
  if (!j.statusAt) { j.statusAt = { [j.status]: j.updatedAt || j.createdAt || now() }; changed = true; }
  if (!j.progress) { j.progress = {}; changed = true; }
  return changed;
}

// ---- migration: settings + the accounts the new dashboards need ------------
function migrate() {
  const db = store.load();
  config();
  const add = (email, name, type, role, extra) => {
    if (store.customers().some(c => c.email === email)) return;
    const { salt, hash } = store.hashPassword('printoka');
    store.customers().push(Object.assign({ id: 'S-' + Math.random().toString(36).slice(2, 7).toUpperCase(), email, passHash: hash, salt, name, type, role, outlet: null, tier: 'Standard', spend12mo: 0, creditBalance: 0, addresses: [], creditLedger: [], createdAt: now() }, extra || {}));
  };
  add('prepress-manager@printoka.com', 'Prepress Manager', 'production', 'prepress_manager');
  add('logistics-manager@printoka.com', 'Logistics Manager', 'production', 'logistics_manager');
  add('hub@printoka.com', 'Hub Staff (Klang Valley)', 'hub', 'hub_staff', { hub: 'HUB-KL' });
  add('hub-miri@printoka.com', 'Hub Staff (Miri)', 'hub', 'hub_staff', { hub: 'HUB-MIRI' });
  add('hub-manager@printoka.com', 'Hub Manager', 'hub', 'hub_manager', { hub: null });
  add('internal@printoka.com', 'Printoka Internal Production (Miri)', 'vendor', 'printer_manager', { internal: true });
  add('scheduler-manager@printoka.com', 'Scheduler Manager', 'production', 'scheduler_manager');
  // production and scheduler are ONE department (guidebook §1.2): fold the old logins in
  store.customers().forEach(c => {
    if (c.type !== 'production') return;
    if (c.role === 'production_manager') { c.role = 'production_director'; if (c.name === 'Production Manager') c.name = 'Production Director'; }
    if (c.role === 'production_staff') { c.role = 'scheduler'; if (/^Production Staff/.test(c.name)) c.name = c.name.replace(/^Production Staff/, 'Scheduler Staff'); }
  });
  // printer company accounts are the printer's MANAGER login; staff logins hang off the company (vendorId)
  store.customers().filter(c => c.type === 'vendor' && c.role === 'vendor').forEach(c => { c.role = 'printer_manager'; });
  const lf = store.customers().find(c => c.email === 'vendor@printoka.com');
  if (lf) add('vendor-staff@printoka.com', 'LargeFormat Co — Print Staff', 'vendor', 'printer_staff', { vendorId: lf.id });
  // plain product names everywhere ("Flyer (= Loose Sheet Litho)" → "Flyer")
  (db.orders || []).forEach(o => (o.items || []).forEach(it => { it.product = store.productName(it.product); }));
  (db.jobs || []).forEach(j => { j.product = store.productName(j.product); if (j.label && j.label.product) j.label.product = store.productName(j.label.product); });
  (db.jobs || []).forEach(j => { normalizeJob(j); const lp = j.progress && j.progress.logistics; if (lp && lp.picked && !lp.verified) lp.verified = lp.picked;
    // hubs are no longer in the production flow: jobs still in production go to production / their own destination
    if ((j.destination || {}).type === 'hub' && ['scheduling', 'printing', 'printed', 'logistics'].indexOf(j.status) >= 0) { j.destination = Object.assign({}, j.finalDestination); makeLabel(j); }
    if ((j.destination || {}).type === 'hub' && j.status === 'outsourcing') { j.destination = destOf('production', null, j); makeLabel(j); }
  });
  // an order reaches the scheduler only once every artwork on it is approved: hold approved items whose siblings are still in prepress
  const open = ['intake', 'prepress', 'prepress_issue', 'escalated', 'rejected'];
  (db.jobs || []).forEach(j => { if (j.status === 'scheduling' && j.orderId && (db.jobs || []).some(x => x.orderId === j.orderId && x.id !== j.id && open.indexOf(x.status) >= 0)) { j.status = 'artwork_ready'; j.statusAt = Object.assign(j.statusAt || {}, { artwork_ready: j.statusAt && j.statusAt.scheduling || new Date().toISOString() }); } });
  store.save();
}

// ---- customer-facing order progress, derived from its jobs ------------------
const PROGRESS_LABEL = { awaiting_payment: 'Awaiting payment', received: 'Order received', artwork_check: 'Artwork check', action_required: 'Action needed: artwork', in_production: 'In production', shipped: 'Shipped', ready_for_collection: 'Ready for collection', completed: 'Completed' };
function syncOrder(oid) {
  const o = oid && store.order(oid); if (!o) return null;
  const js = (o.jobIds || []).map(store.job).filter(Boolean); if (!js.length) return o;
  const st = js.map(j => j.status); const all = arr => st.every(s => arr.indexOf(s) >= 0); const any = arr => st.some(s => arr.indexOf(s) >= 0);
  let p = 'received';
  if (o.payment && o.payment.status !== 'validated' && !js.some(j => j.creditTerms)) p = 'awaiting_payment';
  else if (any(['rejected'])) p = 'action_required';
  else if (all(['completed'])) p = 'completed';
  else if (all(['ready_collect', 'completed'])) p = 'ready_for_collection';
  else if (all(['dispatched', 'at_hub', 'ready_collect', 'completed'])) p = 'shipped';
  else if (any(['scheduling', 'to_outsource', 'to_inhouse', 'printing', 'outsourcing', 'printed', 'inbound', 'logistics', 'dispatched', 'at_hub', 'ready_collect', 'completed'])) p = 'in_production';
  else if (any(['prepress', 'prepress_issue', 'escalated', 'artwork_ready'])) p = 'artwork_check';
  if (o.progress !== p) { o.progress = p; o.progressLabel = PROGRESS_LABEL[p]; o.progressAt = now(); }
  return o;
}
function onOrderCreated(o) {
  (o.jobIds || []).forEach(jid => { const j = store.job(jid); if (j) normalizeJob(j); });
  syncOrder(o.id); store.save();
}

// ---- after every transition: timestamps, shipments, labels, notifications ---
function custNotify(j, kind, title, body) {
  const o = j.orderId && store.order(j.orderId);
  if (o && o.userId) store.notify({ type: 'customer', id: o.userId }, { kind, title, body, cta: 'Track your order →', orderId: o.id });
  return o;
}
// who took the job in each part — shown on the job page ("Handled by")
function claim(j, role, actor) {
  const dq = (D.STATUS[j.status] || {}).queue;
  if (['prepress', 'scheduler', 'logistics'].indexOf(dq) < 0 || D.deptOf(role) !== dq) return false;
  j.owner = j.owner || {}; if (j.owner[dq]) return false;
  j.owner[dq] = actor; j.ownerAt = Object.assign({}, j.ownerAt, { [dq]: now() });
  store.logEvent({ actor, role, action: 'claim', jobId: j.id, from: null, to: null, note: dq }); store.save(); return true;
}
function handlers(j) {
  const o = j.orderId && store.order(j.orderId); const ow = j.owner || {}, at = j.ownerAt || {};
  const firstAt = (acts) => { const e = store.audit({ jobId: j.id }).find(x => acts.indexOf(x.action) >= 0); return e || null; };
  const q = o && o.fromQuote && store.quote(o.fromQuote);
  const orderBy = q && q.issuedBy ? 'Outlet — ' + q.issuedBy.name : o && o.outlet && o.createdByStaff ? 'Outlet — ' + o.createdByStaff : 'Online — ' + ((o && o.customer && o.customer.name) || j.customer);
  const printer = j.outsource && j.outsource.awardedTo ? ((j.outsource.vendors || []).find(v => v.vendorId === j.outsource.awardedTo) || {}).vendorName : null;
  const dl = firstAt(['customer_received', 'receive_outlet', 'deliver']);
  const ev = a => { const e = firstAt(a); return e ? e.ts : null; };
  return [
    { part: 'Order', who: orderBy, at: (o && o.createdAt) || j.createdAt },
    { part: 'Prepress', who: ow.prepress || null, at: at.prepress || ev(['approve', 'flag_minor', 'reject_major', 'escalate']) },
    { part: 'Scheduler', who: ow.scheduler || null, at: at.scheduler || ev(['assign_inhouse', 'assign_outsource']) },
    { part: 'Printing', who: j.route === 'inhouse' ? 'In-house — ' + (j.machine || 'machine') : printer ? 'Printer — ' + printer : null, at: ev(['assign_inhouse', 'assign_outsource']) },
    { part: 'Logistics', who: ow.logistics || null, at: at.logistics || ev(['receive', 'dispatch']) },
    { part: 'Delivery', who: dl ? (dl.action === 'customer_received' ? 'Customer — ' + dl.actor : dl.action === 'receive_outlet' ? 'Outlet — ' + dl.actor : 'Scheduler — ' + dl.actor) : null, at: dl ? dl.ts : null },
  ];
}
// who asked for this delivery: outlet staff (walk-in / counter order) or the customer on the website
function requestedBy(j) {
  const o = j.orderId && store.order(j.orderId);
  const out = (o && o.outlet) || j.outlet || (j.channel === 'outlet' && j.fulfillmentOutlet) || null;
  if (out) { const ol = outletById(out); return { type: 'outlet', outlet: ol ? ol.name : String(out) }; }
  if (j.channel === 'outlet' || (o && o.channel === 'outlet')) return { type: 'outlet', outlet: null };
  return { type: 'customer' };
}
// the outlet a job belongs to (its quote/counter outlet, or the pickup outlet)
function outletOfJob(j) {
  const o = j.orderId && store.order(j.orderId);
  return (o && o.outlet) || j.outlet || (j.finalDestination && j.finalDestination.type === 'outlet' && j.finalDestination.id) || (o && o.fulfillment && o.fulfillment.method === 'pickup' && o.fulfillment.outlet) || null;
}
// Pending Approval: prepress amended the artwork → a warm, clear email asks the customer to approve it
// (the issues found, which ones prepress fixed, the amended file, and a reply to go ahead)
function requestArtworkApproval(j, payload, actor) {
  const issues = (Array.isArray(payload.issues) ? payload.issues : []).map(x => ({ text: String(x.text || '').slice(0, 200) })).filter(x => x.text);
  const file = payload.fileId ? (j.proofs || []).find(f => f.id === payload.fileId) : null;
  const note = String(payload.note || '').trim().slice(0, 1000);
  const o = j.orderId && store.order(j.orderId), c = (o && o.customer) || {};
  const req = { issues, folding: !!payload.folding, note, file: file ? { id: file.id, name: file.name } : null, by: actor, at: now(), emailedTo: null, emailedAt: null };
  if (c.email) {
    const st = (store.settings().store) || {};
    const who = String(actor || '').replace(/\s*\(.*\)\s*$/, '') || 'Our prepress team';
    const lines = ['Hi ' + (c.name || 'there') + ',', '',
      'Thank you so much for choosing Printoka! Before your order goes to print, our prepress team gave your artwork a careful check, and we’d love a quick thumbs-up from you.', '',
      'Order: ' + (o.id || j.orderId), 'Item: ' + j.product + ' × ' + (j.qty || 0).toLocaleString() + ' (' + j.id + ')', ''];
    if (issues.length) {
      lines.push('Here’s what we noticed:');
      issues.forEach(x => lines.push('  • ' + x.text));
      lines.push('');
    }
    if (file) lines.push('We’ve amended the file for you and attached it (' + file.name + ') so you can see exactly how it will print.', '');
    if (req.folding) lines.push('Could you also take a moment to check that the folding looks right to you?', '');
    if (note) lines.push('A note from our team: ' + note, '');
    lines.push('If everything looks good, simply reply to this email and we’ll send it to print straight away.', '',
      'Would you rather make a change yourself? That’s perfectly fine. Just reply with your updated artwork and we’ll check it again for you right away.', '',
      'If you have any questions at all, we’re always happy to help:',
      '  ' + who + ', Printoka Prepress', '  ' + [st.supportPhone, st.supportEmail].filter(Boolean).join(' · '), '',
      'Warm regards,', 'The Printoka Team');
    const e = store.sendEmail('artwork-approval', { to: c.email, name: c.name, jobId: j.id, replyTo: st.supportEmail || null,
      subject: 'A quick check on your artwork for order ' + (o.id || j.orderId),
      body: lines.join('\n'), attachments: file ? [{ id: file.id, name: file.name, jobId: j.id }] : [] });
    if (e) { req.emailedTo = c.email; req.emailedAt = e.ts; }
  }
  j.approvalRequest = req;
}
// An order reaches the scheduler only when prepress has approved EVERY artwork on it (user, 2026-09-25):
// an approved item waits as "Artwork Approved" while its siblings are still in prepress; the last approval releases them all.
const PREPRESS_OPEN = ['intake', 'prepress', 'prepress_issue', 'escalated', 'rejected'];
const siblingsOf = j => j.orderId ? store.jobs().filter(x => x.orderId === j.orderId && x.id !== j.id && x.status !== 'cancelled') : [];
function holdOrRelease(j, actor) {
  const sibs = siblingsOf(j);
  if (sibs.some(x => PREPRESS_OPEN.indexOf(x.status) >= 0)) {
    j.status = 'artwork_ready'; j.statusAt.artwork_ready = now();
    store.logEvent({ actor, role: 'system', action: 'hold_for_order', jobId: j.id, from: 'scheduling', to: 'artwork_ready', note: 'Artwork approved — waiting for the other items on ' + j.orderId });
    return;
  }
  sibs.filter(x => x.status === 'artwork_ready').forEach(x => {
    normalizeJob(x); x.status = 'scheduling'; x.statusAt.scheduling = now(); x.updatedAt = now();
    store.logEvent({ actor, role: 'system', action: 'release_order', jobId: x.id, from: 'artwork_ready', to: 'scheduling', note: 'All artwork on ' + j.orderId + ' approved — to the scheduler' });
  });
}
function afterTransition(j, from, to, action, actor, payload) {
  payload = payload || {};
  normalizeJob(j);
  if (action === 'flag_minor') requestArtworkApproval(j, payload, actor);
  if (to === 'scheduling') { holdOrRelease(j, actor); if (j.status !== 'scheduling') { syncOrder(j.orderId); store.save(); return; } }
  j.statusAt[to] = now();
  if (to === 'printing') j.route = 'inhouse';
  if (to === 'outsourcing') j.route = 'outsource';
  if (action === 'resubmit' && payload.file) { j.artwork = Object.assign({}, j.artwork, { file: payload.file, checkStatus: 'pending', resubmittedAt: now() }); j.artworkMatches = true; }
  const ship = (courier, tracking) => {
    j.shipments = j.shipments || [];
    j.shipments.push({ leg: j.shipments.length + 1, from: origin(j), to: Object.assign({}, j.destination), courier: courier || '', tracking: tracking || '', labelId: j.label && j.label.id, at: now(), by: actor });
    j.courier = courier || j.courier; j.tracking = tracking || j.tracking || '';
  };
  if (action === 'forward') {
    // hub relabels for the final leg (outlet or customer) unless told otherwise
    const t = payload.destType || (j.finalDestination && j.finalDestination.type) || 'customer';
    j.destination = destOf(t, payload.destId || (j.finalDestination || {}).id, j, store.order(j.orderId));
    makeLabel(j); j.label.from = (hubById(j.hub) || {}).name || 'Hub';
  }
  if (action === 'dispatch' || action === 'vendor_ship' || action === 'vendor_ship_outlet' || action === 'forward') ship(payload.courier, payload.tracking);
  if (action === 'receive' || action === 'receive_hub' || action === 'receive_outlet' || action === 'deliver') { const legs = j.shipments || []; const last = legs[legs.length - 1]; if (last && !last.receivedAt) { last.receivedAt = now(); last.receivedBy = actor; } }
  // outsourced job received at production (§4.4): relabel it for its final destination
  if (action === 'receive') { j.destination = Object.assign({}, j.finalDestination); makeLabel(j); j.label.from = config().productionSite; }
  if (to === 'inbound') store.notify({ type: 'role', role: 'logistics' }, { kind: 'inbound', title: 'Outsourced job on its way to production', body: j.id + ' · ' + j.product + ' for ' + j.customer + ' via ' + (j.courier || 'the printer') + (j.tracking ? ' · ' + j.tracking : '') + '. Receive and verify it when it arrives.', jobId: j.id });
  if (to === 'printed') store.notify({ type: 'role', role: 'logistics' }, { kind: 'to_pack', title: 'In-house job printed — receive it', body: j.id + ' · ' + j.product + ' for ' + j.customer + ' → ' + ((j.destination || {}).name || 'customer') + '.', jobId: j.id });
  if (to === 'scheduling') store.notify({ type: 'role', role: 'scheduler' }, { kind: 'to_schedule', title: 'Approved job ready to queue', body: j.id + ' · ' + j.product + ' for ' + j.customer + (j.deadline ? ' · due ' + j.deadline.slice(0, 10) : '') + '.', jobId: j.id });
  if (to === 'escalated') store.notify({ type: 'role', role: 'prepress_manager' }, { kind: 'escalated', title: 'Critical file escalated to you', body: j.id + ' · ' + j.product + ': ' + (payload.reason || '') , jobId: j.id });
  const o = store.order(j.orderId);
  const dn = (j.destination || {}).name || 'its destination';
  if (to === 'scheduling' && action === 'approve') custNotify(j, 'artwork_ok', 'Your artwork passed our check ✅', 'Good news: ' + j.product + ' passed prepress and is now queued for production.');
  if (to === 'rejected') {
    custNotify(j, 'artwork_issue', 'We need a fix on your artwork', 'Our prepress team found an issue with ' + j.product + ': ' + (payload.reason || 'see details') + (payload.suggestion ? '. Suggested correction: ' + payload.suggestion : '') + '. Please send a corrected file and we’ll check it straight away.');
    const oo = outletOfJob(j); if (oo) store.notify({ type: 'outlet', outlet: oo }, { kind: 'artwork_rejected', title: 'Artwork rejected — contact the customer', body: j.id + ' · ' + j.product + ': ' + (payload.reason || '') + (payload.suggestion ? ' → ' + payload.suggestion : ''), jobId: j.id });
  }
  if (to === 'dispatched') {
    const d = j.destination || {};
    if (d.type === 'customer') custNotify(j, 'shipped', 'Your order is on its way 🚚', j.product + ' has shipped with ' + (j.courier || 'our courier') + (j.tracking ? ' (tracking ' + j.tracking + ')' : '') + '.');
    if (d.type === 'hub') {
      store.notify({ type: 'hub', hub: d.id }, { kind: 'inbound', title: 'Parcel on its way to your hub', body: j.id + ' · ' + j.product + ' for ' + j.customer + ' via ' + (j.courier || 'courier') + (j.tracking ? ' · ' + j.tracking : '') + '.', jobId: j.id });
      if (o && o.customer && o.customer.email) store.sendEmail('shipped-hub', { to: o.customer.email, name: o.customer.name, subject: 'Your order ' + o.id + ' is heading to our hub', body: 'Hi ' + (o.customer.name || 'there') + ',\n\n' + j.product + ' has left production and is on its way to ' + dn + ' for final checks before it comes to you.' });
    }
    if (d.type === 'outlet') store.notify({ type: 'outlet', outlet: d.id }, { kind: 'inbound', title: 'Parcel on its way to your outlet', body: j.id + ' · ' + j.product + ' for ' + j.customer + ' — receive it and the customer is told it’s ready to collect.', jobId: j.id });
  }
  if (to === 'ready_collect') {
    custNotify(j, 'ready_collect', 'Ready for collection 🎉', j.product + ' is waiting for you at ' + dn + '.');
    if (o && o.customer && o.customer.email) store.sendEmail('ready-for-collection', { to: o.customer.email, name: o.customer.name, subject: 'Order ' + o.id + ' is ready for collection', body: 'Hi ' + (o.customer.name || 'there') + ',\n\nYour ' + j.product + ' is ready for collection at ' + dn + (j.destination && j.destination.address ? ' (' + j.destination.address + ')' : '') + '.\nPlease bring your order number ' + o.id + '.' });
  }
  if (to === 'completed') custNotify(j, 'completed', 'Order complete', j.product + ' has been ' + (from === 'ready_collect' ? 'collected' : 'delivered') + '. Thank you for printing with Printoka!');
  syncOrder(j.orderId);
  store.save();
}

// transition + side effects in one call (what every route uses)
function transition(jid, role, actor, action, payload) {
  const r = store.applyTransition(jid, role, actor, action, payload || {});
  if (r.error) return r;
  afterTransition(r.job, r.from, r.to, action, actor, payload || {});
  r.to = r.job.status; // e.g. an approved item held as Artwork Approved until the rest of its order is approved
  return r;
}

// ---- interactive progress forms ------------------------------------------------
// SOP checklists: logistics receiving (§4.4) and packing (§4.5); hub (legacy)
const STEP_GROUPS = {
  receiving: { keys: D.CHECKLISTS.receiving.map(c => c[0]), roles: ['logistics_staff', 'logistics_manager'], status: ['inbound'] },
  // in-house jobs start at the print-label page (no Received page), so the label step is open at 'printed' too
  logistics: { keys: D.CHECKLISTS.logistics.map(c => c[0]), roles: ['logistics_staff', 'logistics_manager'], status: ['logistics', 'printed'] },
  hub: { keys: D.CHECKLISTS.hub.map(c => c[0]), roles: ['hub', 'hub_manager'], status: ['at_hub'] },
};
function setStep(jid, group, key, done, role, actor, note) {
  const j = store.job(jid); if (!j) return { error: 'Job not found' };
  const g = STEP_GROUPS[group]; if (!g || g.keys.indexOf(key) < 0) return { error: 'Unknown step' };
  if (role !== 'production_director' && g.roles.indexOf(role) < 0) return { error: 'Your role can’t update this form.' };
  if (g.status.indexOf(j.status) < 0) return { error: 'This form is not open for the job’s current stage.' };
  normalizeJob(j);
  j.progress[group] = j.progress[group] || {};
  if (done) j.progress[group][key] = { at: now(), by: actor, note: note || '' };
  else delete j.progress[group][key];
  const dept = (D.ROLES[role] || {}).dept; j.owner = j.owner || {}; if (dept && dept !== 'all' && !j.owner[dept]) j.owner[dept] = actor;
  store.logEvent({ actor, role, action: 'progress_' + group, jobId: jid, from: null, to: null, note: key + (done ? ' ✓' : ' ✗') + (note ? ' — ' + note : '') });
  store.save(); return { job: j };
}

// ---- Qn 752 CF1: send the order to internal production with delivery instructions ----
// Scheduling SOP (§3.5): assign machine + time slot; the parcel goes to the order's own destination
// (the customer's address, or the pickup outlet) — logistics packs and delivers it after printing.
function sendInternal(jid, role, actor, body) {
  const j = store.job(jid); if (!j) return { error: 'Job not found' };
  normalizeJob(j);
  if (!body.machine) return { error: 'Pick the machine.' };
  if (!body.slot) return { error: 'Pick the time slot.' };
  const prev = { destination: j.destination, instructions: j.instructions, parcels: j.parcels };
  j.destination = Object.assign({}, j.finalDestination);
  if (body.instructions != null) j.instructions = String(body.instructions || '').slice(0, 600);
  j.parcels = Math.max(1, Number(body.parcels) || j.parcels || 1);
  j.route = 'inhouse';
  makeLabel(j);
  const r = transition(jid, role, actor, 'assign_inhouse', { machine: body.machine, slot: body.slot });
  if (r.error) { Object.assign(j, prev); makeLabel(j); store.save(); return r; }
  return { job: store.job(jid) };
}

// logistics chooses where a received job is shipped: the customer's delivery address, or an outlet
function sendTo(jid, role, actor, body) {
  const j = store.job(jid); if (!j) return { error: 'Job not found' };
  if (['logistics_staff', 'logistics_manager', 'production_director'].indexOf(role) < 0) return { error: 'Only logistics chooses where the parcel goes.' };
  if (j.status !== 'logistics' && j.status !== 'printed') return { error: 'Receive the job first; the destination can be changed until it is shipped.' };
  normalizeJob(j);
  const type = body.type === 'outlet' ? 'outlet' : 'customer';
  if (type === 'outlet' && !outletById(body.outletId)) return { error: 'Pick the outlet.' };
  // "customer" always goes back to the order's own delivery address
  if (j.finalDestination && j.finalDestination.type === 'customer' && !j.customerDestination) j.customerDestination = Object.assign({}, j.finalDestination);
  const d = type === 'outlet' ? destOf('outlet', body.outletId, j) : destOf('customer', null, Object.assign({}, j, { finalDestination: j.customerDestination || null }), store.order(j.orderId));
  if (type === 'customer' && !d.address) return { error: 'This order has no delivery address. Send it to an outlet instead.' };
  j.finalDestination = Object.assign({}, d); j.destination = Object.assign({}, d);
  makeLabel(j); j.label.from = config().productionSite;
  store.logEvent({ actor, role, action: 'send_to', jobId: jid, from: null, to: null, note: 'Send to ' + (type === 'outlet' ? d.name : 'customer — ' + (d.address || d.name)) });
  store.save(); return { job: j };
}

// ---- award (quoted, or Qn 752 CF2 direct award without a submitted quote) ------
function award(jid, role, actor, body) {
  const j = store.job(jid); if (!j) return { error: 'Job not found' };
  normalizeJob(j);
  const vendor = store.findCustomer(body.vendorId);
  if (!vendor || vendor.type !== 'vendor') return { error: 'Pick a printer.' };
  if (['scheduling', 'to_outsource'].indexOf(j.status) < 0) return { error: 'Only jobs waiting to be outsourced can be awarded.' };
  j.outsource = j.outsource || { status: 'direct', requestedAt: null, vendors: [], awardedTo: null, po: null };
  let v = j.outsource.vendors.find(x => x.vendorId === vendor.id);
  const quoted = !!(v && v.submittedAt);
  if (!quoted) {
    // Direct award: only the production manager / director, and only with the explicit confirmation
    if (['scheduler_manager', 'production_director'].indexOf(role) < 0) return { error: 'Only the scheduler manager or the production director can award a job without a submitted quote.' };
    if (body.confirmNoQuote !== true) return { error: 'Tick “This printer didn’t submit a quote yet. Please make sure it is internal production.” to confirm.' };
    if (!v) { v = { vendorId: vendor.id, vendorName: vendor.name, price: null, leadDays: null, note: '', submittedAt: null }; j.outsource.vendors.push(v); }
    if (body.price != null && body.price !== '') v.price = Number(body.price) || 0;
    if (body.leadDays != null && body.leadDays !== '') v.leadDays = Number(body.leadDays) || 0;
    v.directAward = true;
  }
  const po = 'PO-' + (jid.replace(/[^0-9]/g, '').slice(0, 5) || '00000') + '-' + Math.floor(Math.random() * 900 + 100);
  const prev = JSON.stringify(j.outsource);
  j.outsource.awardedTo = vendor.id; j.outsource.status = 'awarded'; j.outsource.po = po; j.outsource.awardedAt = now(); j.outsource.direct = !quoted;
  // where the printer delivers (§3.5): to production (logistics receives, repacks, relabels, delivers),
  // or straight to the outlet when the customer collects there
  const type = body.destType || 'production';
  if (type !== 'production' && type !== 'outlet') return { error: 'Printers deliver to production or to the outlet.' };
  if (type === 'outlet' && !(j.finalDestination && j.finalDestination.type === 'outlet')) return { error: 'This order is delivered to the customer — the printer must deliver to production so logistics can pack and send it.' };
  j.destination = type === 'outlet' ? Object.assign({}, j.finalDestination) : destOf('production', null, j);
  if (body.instructions) j.instructions = String(body.instructions).slice(0, 600);
  j.route = 'outsource';
  makeLabel(j);
  j.outsource.label = Object.assign({}, j.label, { po, vendor: vendor.name, dest: j.destination.name });
  const r = transition(jid, role, actor, 'assign_outsource', { printer: vendor.name, reason: quoted ? '' : 'Direct award — no quote submitted (confirmed by ' + actor + ')' });
  if (r.error) { j.outsource = JSON.parse(prev); store.save(); return r; }
  store.logEvent({ actor, role, action: quoted ? 'award_po' : 'award_direct', jobId: jid, from: 'scheduling', to: 'outsourcing', note: (quoted ? 'Awarded ' : 'Direct award (no quote) ') + po + ' to ' + vendor.name + (v.price != null ? ' @ RM ' + v.price : '') + ' → ' + j.destination.name });
  if (vendor.email) store.sendEmail('job-award-printer', { to: vendor.email, name: vendor.name, subject: 'You won the job — ' + po, body: 'Hi ' + vendor.name + ',\n\n' + po + ' has been awarded to you.\n' + j.product + ' · ' + (j.spec || '') + ' · qty ' + j.qty + (v.price != null ? ' @ RM ' + v.price : '') + '.\nPrint the shipping label from your portal and deliver to ' + j.destination.name + (j.destination.address ? ' (' + j.destination.address + ')' : '') + '.' + (j.instructions ? '\nInstructions: ' + j.instructions : '') });
  store.save();
  return { job: store.job(jid) };
}

// ---- KPIs / sales / performance (computed, never typed in) ---------------------
const inRange = (ts, days) => !days || (Date.now() - Date.parse(ts)) <= days * DAY;
const mins = (a, b) => Math.max(0, (Date.parse(b) - Date.parse(a)) / 6e4);
const avg = arr => arr.length ? Math.round(arr.reduce((s, x) => s + x, 0) / arr.length) : null;
const pct = (a, b) => b ? Math.round(a / b * 100) : null;
// when did this job last ENTER `status` before `ts`? (audit, falling back to creation)
function enteredAt(jobId, statuses, ts) {
  const ev = store.audit({ jobId }).filter(e => statuses.indexOf(e.to) >= 0 && Date.parse(e.ts) <= Date.parse(ts)).pop();
  if (ev) return ev.ts;
  const j = store.job(jobId); return j ? (j.createdAt || null) : null;
}
function dailySeries(events, days) {
  const out = []; const start = new Date(); start.setHours(0, 0, 0, 0);
  for (let i = days - 1; i >= 0; i--) {
    const d0 = start.getTime() - i * DAY, d1 = d0 + DAY;
    out.push({ day: new Date(d0).toISOString().slice(0, 10), n: events.filter(e => { const t = Date.parse(e.ts); return t >= d0 && t < d1; }).length });
  }
  return out;
}
// ---- daily reporting (§1.6): morning (start of day) and end-of-day, manager → director ----------
const QUEUE = { prepress: ['intake', 'prepress', 'prepress_issue', 'escalated', 'rejected', 'artwork_ready'], scheduler: ['scheduling', 'to_outsource', 'to_inhouse', 'printing', 'outsourcing'], logistics: ['printed', 'inbound', 'logistics', 'dispatched'] };
const LEAVES = { prepress: ['approve', 'reject_major'], scheduler: ['finish', 'vendor_ship', 'vendor_ship_outlet'], logistics: ['dispatch'] };
const startOfDay = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return d.getTime(); };
function reportFigures(dept) {
  const jobs = store.jobs(), q = jobs.filter(j => QUEUE[dept].indexOf(j.status) >= 0);
  const soon = Date.now() + DAY;
  const view = j => ({ id: j.id, product: j.product, customer: j.customer, status: (D.STATUS[j.status] || {}).label, deadline: j.deadline || null, machine: j.machine || null });
  const today = store.audit().filter(e => e.jobId && Date.parse(e.ts) >= startOfDay());
  const figures = {
    pending: q.length,
    urgent: q.filter(j => j.urgent || (j.deadline && Date.parse(j.deadline) <= soon)).sort(D.priorityCompare).map(view),
    completed: today.filter(e => LEAVES[dept].indexOf(e.action) >= 0).length,
    delayed: q.filter(j => j.deadline && Date.parse(j.deadline) < Date.now()).map(j => Object.assign(view(j), { reason: 'Past the customer deadline' })),
    backlog: q.sort(D.priorityCompare).map(view),
  };
  if (dept === 'scheduler') figures.machines = config().machines.map(m => ({ machine: m, jobs: jobs.filter(j => j.status === 'printing' && j.machine === m).length }));
  return figures;
}
function reports() { const db = store.load(); db.dailyReports = db.dailyReports || []; return db.dailyReports; }
function submitReport(dept, kind, body, me, role) {
  if (!QUEUE[dept]) return { error: 'Unknown department.' };
  if (kind !== 'morning' && kind !== 'evening') return { error: 'Pick the morning or end-of-day report.' };
  if (role !== 'production_director' && (D.deptOf(role) !== dept || D.tierOf(role) !== 'manager')) return { error: 'Daily reports are submitted by the department manager.' };
  const date = new Date().toISOString().slice(0, 10);
  const rec = { id: 'DR-' + date.replace(/-/g, '') + '-' + dept + '-' + kind, dept, kind, date, at: now(), by: me.name, figures: reportFigures(dept),
    notes: { status: String(body.status || '').slice(0, 1000), delays: String(body.delays || '').slice(0, 1000), errors: String(body.errors || '').slice(0, 1000), backlog: String(body.backlog || '').slice(0, 1000) } };
  const list = reports(); const i = list.findIndex(r => r.id === rec.id); if (i >= 0) list[i] = rec; else list.unshift(rec);
  store.logEvent({ actor: me.name, role, action: 'daily_report', jobId: null, from: null, to: null, note: dept + ' ' + (kind === 'morning' ? 'morning' : 'end-of-day') + ' report' });
  store.notify({ type: 'role', role: 'director' }, { kind: 'daily_report', title: (kind === 'morning' ? 'Morning' : 'End-of-day') + ' report — ' + dept, body: me.name + ': ' + rec.figures.pending + ' pending, ' + rec.figures.urgent.length + ' urgent' + (kind === 'evening' ? ', ' + rec.figures.completed + ' completed, ' + rec.figures.delayed.length + ' past deadline' : '') + '.' });
  store.save(); return { report: rec };
}
function listReports(role, days) {
  const cut = Date.now() - (Number(days) || 14) * DAY;
  return reports().filter(r => Date.parse(r.at) >= cut && (role === 'production_director' || r.dept === D.deptOf(role)));
}

const DEPT_ACTIONS = {
  prepress: ['process', 'approve', 'reject_major', 'flag_minor', 'escalate', 'resubmit'],
  scheduler: ['assign_inhouse', 'assign_outsource', 'award_po', 'award_direct', 'request_quotes', 'quote_priced', 'finish', 'draft_approve', 'draft_reject', 'deliver'],
  logistics: ['receive', 'dispatch', 'progress_logistics', 'progress_receiving', 'dispatch_details'],
  hub: ['receive_hub', 'forward', 'progress_hub'],
};
// the guidebook's KPIs (§7), computed from the audit log and the jobs — never typed in
function guideKpi(dept, days) {
  const ev = store.audit().filter(e => e.jobId && inRange(e.ts, days));
  const jobs = store.jobs(); const byId = {}; jobs.forEach(j => { byId[j.id] = j; });
  const onTime = acts => { const xs = ev.filter(e => acts.indexOf(e.action) >= 0 && byId[e.jobId] && byId[e.jobId].deadline); return pct(xs.filter(e => Date.parse(e.ts) <= Date.parse(byId[e.jobId].deadline)).length, xs.length); };
  const m = (label, value, note) => ({ label, value, note });
  if (dept === 'prepress') {
    const checks = ev.filter(e => ['approve', 'reject_major', 'flag_minor', 'escalate'].indexOf(e.action) >= 0 && e.from === 'prepress');
    const times = checks.map(e => { const t0 = enteredAt(e.jobId, ['prepress'], e.ts); return t0 ? mins(t0, e.ts) : null; }).filter(x => x != null);
    const inSla = checks.filter(e => { const t0 = enteredAt(e.jobId, ['prepress'], e.ts); return t0 && mins(t0, e.ts) <= ((byId[e.jobId] || {}).urgent ? 10 : 30); }).length;
    const flagged = checks.filter(e => e.action !== 'approve').length, rejects = checks.filter(e => e.action === 'reject_major').length;
    return [m('File check speed', avg(times) == null ? '—' : avg(times) + ' min', pct(inSla, checks.length) == null ? 'no checks yet' : pct(inSla, checks.length) + '% within 30 min (urgent 10 min)'),
      m('Files checked', checks.length, flagged + ' with an issue'), m('Rejections', rejects, 'returned to the outlet')];
  }
  if (dept === 'scheduler') {
    const outT = ev.filter(e => e.action === 'assign_outsource').map(e => { const t0 = enteredAt(e.jobId, ['scheduling'], e.ts); return t0 ? mins(t0, e.ts) : null; }).filter(x => x != null);
    const inhouse = ev.filter(e => e.action === 'assign_inhouse'); const machines = config().machines;
    const used = machines.filter(mc => inhouse.some(e => ((e.payload || {}).machine) === mc)).length;
    const ot = onTime(['finish', 'vendor_ship', 'vendor_ship_outlet']);
    return [m('Time to outsource', avg(outT) == null ? '—' : (avg(outT) < 60 ? avg(outT) + ' min' : (avg(outT) / 60).toFixed(1) + ' h'), 'approved → printer awarded'),
      m('On-time completion', ot == null ? '—' : ot + '%', 'printed before the customer deadline'),
      m('Machine utilisation', used + ' of ' + machines.length, inhouse.length + ' in-house job(s)')];
  }
  const od = onTime(['deliver', 'customer_received', 'receive_outlet']);
  return [m('On-time delivery', od == null ? '—' : od + '%', 'received before the customer deadline'),
    m('Received', ev.filter(e => e.action === 'receive').length, 'from in-house and printers'), m('Shipped', ev.filter(e => e.action === 'dispatch').length, 'dispatched to customers and outlets')];
}
function kpi(dept, days) {
  days = Number(days) || 30;
  const ev = store.audit().filter(e => e.jobId && inRange(e.ts, days) && (DEPT_ACTIONS[dept] || []).indexOf(e.action) >= 0);
  const byActor = {};
  const row = a => byActor[a] = byActor[a] || { actor: a, count: 0, times: [], sla: 0, slaN: 0, rejects: 0, onTime: 0, onTimeN: 0 };
  ev.forEach(e => {
    const r = row(e.actor || 'unknown'); r.count++;
    const j = store.job(e.jobId) || {};
    if (dept === 'prepress' && ['approve', 'reject_major', 'flag_minor', 'escalate'].indexOf(e.action) >= 0) {
      const t0 = enteredAt(e.jobId, ['prepress'], e.ts); if (t0) { const m = mins(t0, e.ts); r.times.push(m); r.slaN++; if (m <= (j.urgent ? 10 : 30)) r.sla++; }
      if (e.action === 'reject_major') r.rejects++;
    }
    if (dept === 'scheduler' && (e.action === 'assign_inhouse' || e.action === 'assign_outsource')) {
      const t0 = enteredAt(e.jobId, ['scheduling'], e.ts); if (t0) r.times.push(mins(t0, e.ts));
    }
    if (dept === 'logistics' && e.action === 'dispatch') { const t0 = enteredAt(e.jobId, ['logistics'], e.ts); if (t0) r.times.push(mins(t0, e.ts)); }
    if (dept === 'hub' && e.action === 'forward') { const t0 = enteredAt(e.jobId, ['at_hub'], e.ts); if (t0) r.times.push(mins(t0, e.ts)); }
    if ((e.action === 'deliver' || e.action === 'finish' || e.action === 'forward') && j.deadline) { r.onTimeN++; if (Date.parse(e.ts) <= Date.parse(j.deadline)) r.onTime++; }
  });
  const staff = Object.values(byActor).map(r => ({ actor: r.actor, count: r.count, avgMins: avg(r.times), slaPct: pct(r.sla, r.slaN), rejects: r.rejects, rejectPct: pct(r.rejects, r.slaN), onTimePct: pct(r.onTime, r.onTimeN) })).sort((a, b) => b.count - a.count);
  const all = Object.values(byActor);
  const flat = k => all.reduce((s, r) => s.concat(r[k]), []);
  const sum = k => all.reduce((s, r) => s + r[k], 0);
  const jobs = store.jobs();
  const queueNow = QUEUE[dept] || (dept === 'hub' ? ['at_hub'] : []);
  const overdue = jobs.filter(j => queueNow.indexOf(j.status) >= 0 && j.deadline && Date.parse(j.deadline) < Date.now()).length;
  return { dept, days, actions: ev.length, metrics: QUEUE[dept] ? guideKpi(dept, days) : [], avgMins: avg(flat('times')), slaPct: pct(sum('sla'), sum('slaN')), rejectPct: pct(sum('rejects'), sum('slaN')), onTimePct: pct(sum('onTime'), sum('onTimeN')),
    inQueue: jobs.filter(j => queueNow.indexOf(j.status) >= 0).length, overdue, staff, series: dailySeries(ev, Math.min(days, 30)) };
}
function sales(days) {
  days = Number(days) || 30;
  const paid = store.orders().filter(o => o.payment && o.payment.status === 'validated');
  const inR = paid.filter(o => inRange(o.payment.paidAt || o.createdAt, days));
  const total = inR.reduce((s, o) => s + (o.total || 0), 0);
  const byProduct = {}; const byChannel = {};
  inR.forEach(o => { (o.items || []).forEach(it => { const k = it.product || 'Other'; byProduct[k] = byProduct[k] || { product: k, qty: 0, revenue: 0, lines: 0 }; byProduct[k].qty += it.qty || 0; byProduct[k].revenue += it.lineTotal || 0; byProduct[k].lines++; });
    const c = o.channel || 'online'; byChannel[c] = byChannel[c] || { channel: c, orders: 0, revenue: 0 }; byChannel[c].orders++; byChannel[c].revenue += o.total || 0; });
  // production route split: in-house vs outsourced revenue, printer cost and margin
  const route = { inhouse: { jobs: 0, revenue: 0, cost: 0 }, outsource: { jobs: 0, revenue: 0, cost: 0 }, unallocated: { jobs: 0, revenue: 0, cost: 0 } };
  store.jobs().filter(j => inRange(j.createdAt || now(), days)).forEach(j => {
    const k = j.route === 'inhouse' ? 'inhouse' : j.route === 'outsource' ? 'outsource' : 'unallocated';
    route[k].jobs++; route[k].revenue += j.price || 0;
    if (k === 'outsource' && j.outsource && j.outsource.awardedTo) { const v = j.outsource.vendors.find(x => x.vendorId === j.outsource.awardedTo); route[k].cost += (v && v.price) || 0; }
  });
  Object.values(route).forEach(r => { r.margin = r.revenue - r.cost; r.revenue = Math.round(r.revenue * 100) / 100; r.cost = Math.round(r.cost * 100) / 100; r.margin = Math.round(r.margin * 100) / 100; });
  const months = []; const d = new Date(); d.setDate(1); d.setHours(0, 0, 0, 0);
  for (let i = 5; i >= 0; i--) { const m0 = new Date(d.getFullYear(), d.getMonth() - i, 1), m1 = new Date(d.getFullYear(), d.getMonth() - i + 1, 1);
    const os = paid.filter(o => { const t = Date.parse(o.payment.paidAt || o.createdAt); return t >= m0.getTime() && t < m1.getTime(); });
    months.push({ month: m0.toLocaleString('en', { month: 'short' }).toUpperCase(), orders: os.length, revenue: Math.round(os.reduce((s, o) => s + (o.total || 0), 0) * 100) / 100 }); }
  const today = paid.filter(o => inRange(o.payment.paidAt || o.createdAt, 1));
  const pending = store.orders().filter(o => o.payment && o.payment.status !== 'validated');
  return { days, orders: inR.length, revenue: Math.round(total * 100) / 100, aov: inR.length ? Math.round(total / inR.length * 100) / 100 : 0,
    today: { orders: today.length, revenue: Math.round(today.reduce((s, o) => s + (o.total || 0), 0) * 100) / 100 },
    pendingPayment: { orders: pending.length, value: Math.round(pending.reduce((s, o) => s + (o.total || 0), 0) * 100) / 100 },
    byProduct: Object.values(byProduct).map(x => Object.assign(x, { revenue: Math.round(x.revenue * 100) / 100 })).sort((a, b) => b.revenue - a.revenue),
    byChannel: Object.values(byChannel).map(x => Object.assign(x, { revenue: Math.round(x.revenue * 100) / 100 })), route, months };
}
function hubPerformance(hubId, days) {
  days = Number(days) || 30;
  const js = store.jobs().filter(j => !hubId || j.hub === hubId || ((j.destination || {}).type === 'hub' && j.destination.id === hubId));
  const ids = {}; js.forEach(j => { ids[j.id] = 1; });
  const ev = store.audit().filter(e => ids[e.jobId]);
  const received = ev.filter(e => e.action === 'receive_hub'), forwarded = ev.filter(e => e.action === 'forward');
  const period = arr => ({ today: arr.filter(e => inRange(e.ts, 1)).length, week: arr.filter(e => inRange(e.ts, 7)).length, month: arr.filter(e => inRange(e.ts, 30)).length, all: arr.length });
  const dwell = forwarded.map(e => { const t0 = enteredAt(e.jobId, ['at_hub'], e.ts); return t0 ? mins(t0, e.ts) : null; }).filter(x => x != null);
  const inbound = js.filter(j => j.status === 'dispatched' && (j.destination || {}).type === 'hub' && (!hubId || j.destination.id === hubId));
  const atHub = js.filter(j => j.status === 'at_hub');
  return { hub: hubId || 'all', received: period(received), processed: period(forwarded), inbound: inbound.length, atHub: atHub.length,
    avgDwellMins: avg(dwell), overdue: atHub.filter(j => j.deadline && Date.parse(j.deadline) < Date.now()).length,
    series: dailySeries(forwarded.filter(e => inRange(e.ts, days)), Math.min(days, 30)), receivedSeries: dailySeries(received.filter(e => inRange(e.ts, days)), Math.min(days, 30)) };
}
function actions(dept, opts) {
  opts = opts || {};
  const acts = DEPT_ACTIONS[dept] || null;
  return store.audit().filter(e => e.jobId && (!acts || acts.indexOf(e.action) >= 0) && (!opts.actor || e.actor === opts.actor) && inRange(e.ts, opts.days || 0))
    .slice(-400).reverse().map(e => { const j = store.job(e.jobId) || {}; return Object.assign({}, e, { customer: j.customer, product: j.product, orderId: j.orderId }); });
}

// ---- individual performance report (same idea as the outlet's original individual-performance report):
// monthly figures per staff member, computed from the actions they recorded
const M24 = () => { const out = []; const d = new Date(); d.setDate(1); d.setHours(0, 0, 0, 0); for (let i = 23; i >= 0; i--) { const m = new Date(d.getFullYear(), d.getMonth() - i, 1); out.push({ key: m.getFullYear() + '-' + String(m.getMonth() + 1).padStart(2, '0'), label: m.toLocaleString('en', { month: 'short' }) + ' ' + m.getFullYear() }); } return out; };
const ymOf = ts => { const d = new Date(ts); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0'); };
const DEPT_OF_ACCOUNT = { prepress: 'prepress', prepress_manager: 'prepress', scheduler: 'scheduler', scheduler_manager: 'scheduler', production_staff: 'scheduler', logistics: 'logistics', logistics_manager: 'logistics' };
function individualStaff(me) {
  const all = store.customers();
  if (me.type === 'vendor') { const co = me.vendorId || me.id; return me.role === 'printer_staff' ? [] : all.filter(c => c.type === 'vendor' && (c.id === co || c.vendorId === co)).map(c => ({ id: c.id, name: c.name, dept: 'printer' })); }
  const director = me.type === 'admin' || me.role === 'production_director' || me.role === 'production_manager';
  const myDept = DEPT_OF_ACCOUNT[me.role];
  if (!director && !/_manager$/.test(me.role)) return [];
  return all.filter(c => c.type === 'production' && DEPT_OF_ACCOUNT[c.role] && (director || DEPT_OF_ACCOUNT[c.role] === myDept)).map(c => ({ id: c.id, name: c.name, dept: DEPT_OF_ACCOUNT[c.role] }));
}
function individual(me, staffId) {
  let who = me;
  if (staffId && staffId !== me.id) { if (!individualStaff(me).some(s => s.id === staffId)) return { error: 'You can only view the staff you manage.' }; who = store.findCustomer(staffId); }
  const dept = who.type === 'vendor' ? 'printer' : DEPT_OF_ACCOUNT[who.role];
  if (!dept) return { error: 'The Production Director has no individual report — pick a staff member.', staff: individualStaff(me) };
  const M = M24(), blank = () => { const o = {}; M.forEach(m => { o[m.key] = 0; }); return o; };
  const name = who.name, ev = store.audit().filter(e => e.actor === name && e.ts);
  const jobs = {}; store.jobs().forEach(j => { jobs[j.id] = j; });
  const count = acts => { const s = blank(); ev.filter(e => acts.indexOf(e.action) >= 0).forEach(e => { const k = ymOf(e.ts); if (s[k] != null) s[k]++; }); return s; };
  const pctBy = (list, good) => { const n = blank(), g = blank(), out = {}; list.forEach(e => { const k = ymOf(e.ts); if (n[k] == null) return; n[k]++; if (good(e)) g[k]++; }); M.forEach(m => { out[m.key] = n[m.key] ? Math.round(g[m.key] / n[m.key] * 100) : null; }); return out; };
  const beforeDeadline = e => { const j = jobs[e.jobId]; return !j || !j.deadline || Date.parse(e.ts) <= Date.parse(j.deadline); };
  const r = { staff: name, dept, months: M, metrics: {} };
  if (dept === 'prepress') {
    const checks = ev.filter(e => ['approve', 'flag_minor', 'reject_major', 'escalate'].indexOf(e.action) >= 0 && e.from === 'prepress');
    const ck = blank(); checks.forEach(e => { const k = ymOf(e.ts); if (ck[k] != null) ck[k]++; });
    r.metrics = { filesChecked: ck, passed: count(['approve']), rejections: count(['reject_major']),
      withinSla: pctBy(checks, e => { const t0 = enteredAt(e.jobId, ['prepress'], e.ts); return t0 && mins(t0, e.ts) <= ((jobs[e.jobId] || {}).urgent ? 10 : 30); }) };
  } else if (dept === 'scheduler') {
    r.metrics = { jobsScheduled: count(['assign_inhouse', 'assign_outsource']), quotesReplied: count(['quote_issued']), printerQuotesAsked: count(['request_quotes', 'request_printer_quote']),
      onTime: pctBy(ev.filter(e => ['finish'].indexOf(e.action) >= 0), beforeDeadline) };
  } else if (dept === 'logistics') {
    r.metrics = { received: count(['receive']), shipped: count(['dispatch']), onTimeDelivery: pctBy(ev.filter(e => e.action === 'dispatch'), beforeDeadline) };
  } else {
    const co = who.vendorId || who.id; const won = blank(), paid = blank();
    store.jobs().forEach(j => { const o = j.outsource; if (!o || o.awardedTo !== co) return; const v = (o.vendors || []).find(x => x.vendorId === co) || {};
      if (o.awardedAt && won[ymOf(o.awardedAt)] != null) won[ymOf(o.awardedAt)]++;
      if (o.paidAt && paid[ymOf(o.paidAt)] != null) paid[ymOf(o.paidAt)] = Math.round((paid[ymOf(o.paidAt)] + (Number(v.price) || 0)) * 100) / 100; });
    r.metrics = { quotesSubmitted: count(['submit_quote']), purchaseOrders: won, delivered: count(['printer_delivery']), onTimeDelivery: pctBy(ev.filter(e => e.action === 'printer_delivery'), beforeDeadline), amountPaid: paid };
  }
  return { performance: r, staff: individualStaff(me) };
}

module.exports = { requestedBy, sendTo,individual, individualStaff, config, saveConfig, migrate, normalizeJob, makeLabel, syncOrder, onOrderCreated, afterTransition, transition, setStep, sendInternal, award, kpi, sales, hubPerformance, actions, hubById, outletById, STEP_GROUPS, PROGRESS_LABEL,
  reportFigures, submitReport, listReports, outletOfJob, destOf, claim, handlers };