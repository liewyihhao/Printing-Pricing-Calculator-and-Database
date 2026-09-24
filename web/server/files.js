/*
 * Order files — the customer's artworks (per order line) and the payment proof (bank-in slip).
 * Stored OUTSIDE the public web folder (repo-root /private-files/orders/<orderId>/) and only
 * streamed back through the API to the order's owner or to staff.
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const store = require('./store');

const ROOT = path.join(__dirname, '..', '..', 'private-files', 'orders');
const now = () => new Date().toISOString();
const ARTWORK_EXT = { pdf: 1, ai: 1, eps: 1, psd: 1, tif: 1, tiff: 1, jpg: 1, jpeg: 1, png: 1, svg: 1, cdr: 1, indd: 1, zip: 1 };
const PROOF_EXT = { pdf: 1, jpg: 1, jpeg: 1, png: 1, webp: 1, heic: 1 };
const MIME = { pdf: 'application/pdf', jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp', svg: 'image/svg+xml', tif: 'image/tiff', tiff: 'image/tiff', zip: 'application/zip' };
const safe = n => String(n || 'file').replace(/[\\/:*?"<>|\u0000-\u001f]+/g, '-').replace(/\s+/g, ' ').trim().slice(0, 120) || 'file';

// who may see / add files for an order: its customer, or staff (printers only for jobs awarded to them)
function canAccess(o, me) {
  if (!o || !me) return false;
  if (me.type === 'customer') return !!o.userId && o.userId === me.id;
  if (me.type === 'vendor') { const co = me.vendorId || me.id; return (o.jobIds || []).some(jid => { const j = store.job(jid); return j && j.outsource && j.outsource.awardedTo === co; }); }
  return true;
}
function saveFile(oid, b, me) {
  const o = store.order(oid); if (!o) return { error: 'Order not found.' };
  if (!canAccess(o, me) || me.type === 'vendor') return { error: 'Not allowed.' };
  const kind = b.kind === 'proof' ? 'proof' : 'artwork';
  const name = safe(b.name); const ext = (name.split('.').pop() || '').toLowerCase();
  if (kind === 'artwork' && !ARTWORK_EXT[ext]) return { error: 'Artwork must be PDF, AI, EPS, PSD, TIFF, JPG, PNG, SVG, CDR, INDD or ZIP.' };
  if (kind === 'proof' && !PROOF_EXT[ext]) return { error: 'Payment proof must be a PDF or an image.' };
  const m = String(b.data || '').match(/^data:[^;]*;base64,(.+)$/); if (!m) return { error: 'No file received.' };
  const buf = Buffer.from(m[1], 'base64');
  const max = kind === 'proof' ? 10 : 60;
  if (buf.length > max * 1024 * 1024) return { error: 'File is larger than ' + max + ' MB.' };
  const line = Number(b.line) || 1; const it = (o.items || [])[line - 1];
  if (kind === 'artwork' && !it) return { error: 'That order line does not exist.' };
  const id = 'F' + crypto.randomBytes(5).toString('hex').toUpperCase();
  const dir = path.join(ROOT, oid); fs.mkdirSync(dir, { recursive: true });
  const stored = id + '-' + name; fs.writeFileSync(path.join(dir, stored), buf);
  const rec = { id, name, stored, size: buf.length, kind, line: kind === 'artwork' ? line : null, at: now(), by: me.name || me.email };
  o.files = o.files || []; o.files.push(rec);
  if (kind === 'artwork') {
    it.artworks = (it.artworks || []).filter(a => !/^pending-upload/.test(a)).concat([name]);
    const j = store.job((o.jobIds || [])[line - 1]);
    if (j && (!j.artwork || !j.artwork.file || /^pending-upload/.test(j.artwork.file) || ['intake', 'prepress', 'prepress_issue'].indexOf(j.status) >= 0)) j.artwork = Object.assign({}, j.artwork, { file: name, fileId: id, checkStatus: 'pending', uploadedAt: now() });
  } else { o.payment = Object.assign({}, o.payment, { proof: name, proofFileId: id, proofAt: now() }); }
  store.logEvent({ actor: me.name || me.email, role: me.type, action: kind === 'proof' ? 'payment_proof' : 'artwork_upload', jobId: kind === 'artwork' ? (o.jobIds || [])[line - 1] || null : null, from: null, to: null, note: oid + ' · ' + name + ' (' + Math.round(buf.length / 1024) + ' KB)' });
  if (kind === 'proof') store.notify({ type: 'role', role: 'prepress' }, { kind: 'payment_proof', title: 'Payment proof uploaded', body: 'Order ' + oid + ' has a bank-in slip to validate.', orderId: oid });
  store.save();
  return { file: rec, order: store.orderView(oid) };
}
function readFile(oid, fileId, me) {
  const o = store.order(oid); if (!o) return { error: 'Order not found.', code: 404 };
  if (!canAccess(o, me)) return { error: 'Not allowed.', code: 403 };
  const f = (o.files || []).find(x => x.id === fileId); if (!f) return { error: 'File not found.', code: 404 };
  const p = path.join(ROOT, oid, f.stored); if (!p.startsWith(ROOT) || !fs.existsSync(p)) return { error: 'File missing on disk.', code: 404 };
  return { file: f, data: fs.readFileSync(p), type: MIME[(f.name.split('.').pop() || '').toLowerCase()] || 'application/octet-stream' };
}
module.exports = { saveFile, readFile, canAccess };
