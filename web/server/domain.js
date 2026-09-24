/*
 * Printoka operations domain — the unified job/quote state machine, hard gates,
 * RBAC, priority function and audit contract from the two operations guidebooks.
 * Pure logic, no I/O. Consumed by server.js.
 *
 * Guidebook anchors:
 *   Prod §1.7 non-negotiables (system entry, payment validated, artwork==order, traceable)
 *   Prod §1.8 workflow (Prepress → Scheduler → Logistics)  ·  Prepress §2.5 status classes
 *   Scheduler §3.4 priority (deadline, then payment-confirmation time)
 *   Outlet §4 intake  ·  Prod §1.4/§1.5 roles & strict reporting
 *   Qn 732 Hub system · Qn 750 Production/Prepress/Logistics · Qn 752 order-sent + direct award
 *
 * Physical flow after production (in-house or vendor):
 *   ready (logistics) ─dispatch→ in transit to the job's current destination
 *     destination = customer → deliver → completed
 *     destination = outlet   → receive_outlet → ready for collection → collect → completed
 *     destination = hub      → receive_hub → at hub (QC, relabel/repack) → forward → in transit to
 *                              the final destination (outlet or customer) → …
 *   A vendor ships straight from its own press (vendor_ship) to the destination on its label.
 */

// ---- roles ----------------------------------------------------------------
const ROLES = {
  // outlet
  cs_walkin: { label: 'Customer Service (Walk-in)', dept: 'outlet', tier: 'staff' },
  print_consultant: { label: 'Printing Consultant (B2B)', dept: 'outlet', tier: 'staff' },
  store_manager: { label: 'Store / Assistant Manager', dept: 'outlet', tier: 'manager' },
  // production departments
  prepress_staff: { label: 'Prepress Staff', dept: 'prepress', tier: 'staff' },
  prepress_manager: { label: 'Prepress Manager', dept: 'prepress', tier: 'manager' },
  scheduler_staff: { label: 'Scheduler Staff', dept: 'scheduler', tier: 'staff' },
  scheduler_manager: { label: 'Scheduler Manager', dept: 'scheduler', tier: 'manager' },
  production_staff: { label: 'Production Staff', dept: 'production', tier: 'staff' },
  production_manager: { label: 'Production Manager', dept: 'production', tier: 'manager' },
  logistics_staff: { label: 'Logistics Staff', dept: 'logistics', tier: 'staff' },
  logistics_manager: { label: 'Logistics Manager', dept: 'logistics', tier: 'manager' },
  production_director: { label: 'Production Director', dept: 'all', tier: 'director' },
  // hub (consolidation / relabel / repack)
  hub: { label: 'Hub Staff', dept: 'hub', tier: 'staff' },
  hub_manager: { label: 'Hub Manager', dept: 'hub', tier: 'manager' },
  // external
  printer: { label: 'Outsource Printer', dept: 'vendor', tier: 'staff' },
};

// ---- job statuses ---------------------------------------------------------
// Each status belongs to a department "queue" (drives GET /queues/:dept).
const STATUS = {
  intake: { label: 'Intake — acknowledge', queue: 'outlet' },
  prepress: { label: 'Prepress — file check', queue: 'prepress' },
  prepress_issue: { label: 'Prepress — issue / fixing', queue: 'prepress' },
  escalated: { label: 'Escalated to manager', queue: 'prepress' },
  rejected: { label: 'Artwork rejected — awaiting new file', queue: 'outlet' },
  scheduling: { label: 'Scheduler — queue & allocate', queue: 'scheduler' },
  printing: { label: 'In production (in-house floor)', queue: 'production' },
  outsourcing: { label: 'Outsourced — printer producing', queue: 'scheduler' },
  logistics: { label: 'Logistics — pack & dispatch', queue: 'logistics' },
  dispatched: { label: 'In transit', queue: 'logistics' },
  at_hub: { label: 'At hub — check, relabel & forward', queue: 'hub' },
  ready_collect: { label: 'Ready for collection at outlet', queue: 'outlet' },
  completed: { label: 'Completed / delivered', queue: 'done' },
  cancelled: { label: 'Cancelled', queue: 'done' },
};

const OUTLET = ['cs_walkin', 'print_consultant', 'store_manager'];
const PREPRESS = ['prepress_staff', 'prepress_manager'];
const SCHEDULER = ['scheduler_staff', 'scheduler_manager', 'production_manager'];
const FLOOR = ['production_staff', 'production_manager'];
const PRODUCTION = SCHEDULER;
const LOGISTICS = ['logistics_staff', 'logistics_manager'];
const HUB = ['hub', 'hub_manager'];

// ---- gates (server-side, non-negotiable) ----------------------------------
// Return null if the gate passes, or a human-readable reason if it blocks.
const destType = job => (job.destination && job.destination.type) || 'customer';
const GATES = {
  payment: job => (job.paymentValidated || job.creditTerms)
    ? null : 'No production without payment confirmation (bank transfer must be validated), unless on credit terms.',
  artworkMatch: job => (job.artworkMatches || job.customerAuthorizedMismatch)
    ? null : 'Order details do not match the artwork requirement — needs customer authorization to proceed.',
  artworkPresent: job => job.artwork && job.artwork.file && !/^pending-upload/.test(job.artwork.file)
    ? null : 'No artwork file attached to this job yet.',
  // in-house progress form: every production step ticked before it leaves the floor
  productionDone: job => {
    const steps = (job.progress && job.progress.inhouse) || {};
    const missing = ['setup', 'printing', 'finishing', 'qc'].filter(k => !steps[k]);
    return missing.length ? 'Complete the production progress form first (' + missing.join(', ') + ').' : null;
  },
  // logistics packing form / hub progress form: every step ticked before the parcel leaves
  logisticsDone: job => {
    const s = (job.progress && job.progress.logistics) || {}; const missing = ['picked', 'packed', 'labelled'].filter(k => !s[k]);
    return missing.length ? 'Complete the logistics status update first (' + missing.join(', ') + ').' : null;
  },
  hubDone: job => {
    const s = (job.progress && job.progress.hub) || {}; const missing = ['checked', 'qc', 'relabelled'].filter(k => !s[k]);
    return missing.length ? 'Complete the hub progress form first (' + missing.join(', ') + ').' : null;
  },
  // original supplier flow: the printer prints only after HQ approves its draft
  draftApproved: job => (!job.outsource || !job.outsource.awardedTo || (job.outsource.draft && job.outsource.draft.approvedAt))
    ? null : 'Please wait for admin approve the draft before start printing.',
  destCustomer: job => destType(job) === 'customer' ? null : 'This parcel is going to a ' + destType(job) + ', not the customer.',
  destOutlet: job => destType(job) === 'outlet' ? null : 'This parcel is not addressed to an outlet.',
  destHub: job => destType(job) === 'hub' ? null : 'This parcel is not addressed to a hub.',
};

// ---- transition table -----------------------------------------------------
// from -> [{ action, to, roles:[...], gates:[...], requires:[fields], note }]
// production_director may perform any transition (override authority, Prod §1.4).
const TRANSITIONS = {
  intake: [
    { action: 'acknowledge', to: 'prepress', roles: OUTLET,
      gates: ['payment'], note: 'Acknowledge within 5 min and release to prepress (Outlet §4.2).' },
  ],
  prepress: [
    { action: 'approve', to: 'scheduling', roles: PREPRESS,
      gates: ['artworkPresent', 'artworkMatch'], note: 'PASS → release to production (Prepress §2.5).' },
    { action: 'flag_minor', to: 'prepress_issue', roles: PREPRESS,
      requires: ['reason'], note: 'MINOR ISSUE → fix internally & seek approval (Prepress §2.5).' },
    { action: 'reject_major', to: 'rejected', roles: PREPRESS,
      requires: ['reason', 'proof'], note: 'MAJOR ISSUE → reject to outlet/customer with issue + visual proof (Prepress §2.7).' },
    { action: 'escalate', to: 'escalated', roles: ['prepress_staff'],
      requires: ['reason'], note: 'CRITICAL → escalate to manager (Prepress §2.5).' },
  ],
  prepress_issue: [
    { action: 'approve', to: 'scheduling', roles: ['prepress_manager'],
      gates: ['artworkPresent', 'artworkMatch'], note: 'Manager approves the internal fix.' },
    { action: 'reject_major', to: 'rejected', roles: PREPRESS, requires: ['reason', 'proof'] },
  ],
  escalated: [
    { action: 'approve', to: 'scheduling', roles: ['prepress_manager'], gates: ['artworkPresent', 'artworkMatch'] },
    { action: 'reject_major', to: 'rejected', roles: ['prepress_manager'], requires: ['reason', 'proof'] },
  ],
  rejected: [
    { action: 'resubmit', to: 'prepress', roles: OUTLET.concat(PREPRESS),
      requires: ['file'], note: 'Customer sent a corrected file — back to prepress for a fresh check.' },
  ],
  scheduling: [
    { action: 'assign_inhouse', to: 'printing', roles: PRODUCTION,
      gates: ['payment'], requires: ['machine'], note: 'Send to internal production with delivery instructions (Qn 752 CF1).' },
    { action: 'assign_outsource', to: 'outsourcing', roles: PRODUCTION,
      gates: ['payment'], requires: ['printer'], note: 'Award to printer by best quote/time/logistics (Scheduler §3.5).' },
  ],
  printing: [
    { action: 'finish', to: 'logistics', roles: FLOOR, gates: ['productionDone'],
      note: 'Set-up → Printing → Finishing → QC done — hand to logistics.' },
  ],
  outsourcing: [
    { action: 'vendor_ship', to: 'dispatched', roles: PRODUCTION.concat(['printer'], LOGISTICS),
      gates: ['draftApproved'], requires: ['courier'], note: 'Printer shipped the parcel with the Printoka label to its destination.' },
  ],
  logistics: [
    { action: 'dispatch', to: 'dispatched', roles: LOGISTICS,
      gates: ['logisticsDone'], requires: ['courier'], note: 'Pack, label, assign courier, dispatch (Logistics §4.5).' },
  ],
  dispatched: [
    { action: 'deliver', to: 'completed', roles: LOGISTICS, gates: ['destCustomer'],
      note: 'Courier confirmed delivery to the customer.' },
    { action: 'receive_hub', to: 'at_hub', roles: HUB.concat(LOGISTICS), gates: ['destHub'],
      note: 'Hub received the parcel (Logistics §4.4).' },
    { action: 'receive_outlet', to: 'ready_collect', roles: OUTLET, gates: ['destOutlet'],
      note: 'Outlet received the parcel — customer notified it is ready for collection.' },
  ],
  at_hub: [
    { action: 'forward', to: 'dispatched', roles: HUB, gates: ['hubDone'], requires: ['courier'],
      note: 'Checked, relabelled/repacked and forwarded to the final destination.' },
  ],
  ready_collect: [
    { action: 'collect', to: 'completed', roles: OUTLET, note: 'Customer collected the order (Outlet §4.5).' },
  ],
};

function roleCan(role, t) {
  if (role === 'production_director') return true; // override authority
  return (t.roles || []).indexOf(role) !== -1;
}

// Compute the transitions a given role may attempt on a job right now,
// annotated with any blocking gate/requirement (so the UI can show *why* disabled).
function availableActions(job, role) {
  const list = TRANSITIONS[job.status] || [];
  return list.map(t => {
    const permitted = roleCan(role, t);
    const gateBlock = (t.gates || []).map(g => GATES[g](job)).filter(Boolean);
    return {
      action: t.action, to: t.to, toLabel: STATUS[t.to] && STATUS[t.to].label,
      note: t.note, requires: t.requires || [],
      permitted, blockedBy: gateBlock, enabled: permitted && gateBlock.length === 0,
    };
  });
}

// Validate + return the resolved transition (or an error object). Does not mutate.
function resolveTransition(job, role, action, payload) {
  const t = (TRANSITIONS[job.status] || []).find(x => x.action === action);
  if (!t) return { error: `Action "${action}" is not valid from status "${job.status}".` };
  if (!roleCan(role, t)) return { error: `Role "${role}" may not perform "${action}".` };
  for (const g of (t.gates || [])) { const r = GATES[g](job); if (r) return { error: r, gate: g }; }
  for (const f of (t.requires || [])) { if (!payload || payload[f] == null || payload[f] === '') return { error: `Missing required field "${f}" for "${action}".` }; }
  return { transition: t };
}

// Priority: ONLY (1) customer deadline, then (2) payment-confirmation time (Scheduler §3.4).
function priorityCompare(a, b) {
  const da = a.deadline ? Date.parse(a.deadline) : Infinity;
  const db = b.deadline ? Date.parse(b.deadline) : Infinity;
  if (da !== db) return da - db;
  const pa = a.paymentValidatedAt ? Date.parse(a.paymentValidatedAt) : Infinity;
  const pb = b.paymentValidatedAt ? Date.parse(b.paymentValidatedAt) : Infinity;
  return pa - pb;
}

// Staff account role (login) → state-machine role. Decided on the SERVER from the session,
// never from what the browser claims.
const ACCOUNT_ROLE = {
  admin: 'production_director', production_manager: 'production_manager', production_staff: 'production_staff',
  prepress: 'prepress_staff', prepress_manager: 'prepress_manager',
  scheduler: 'scheduler_staff', scheduler_manager: 'scheduler_manager',
  logistics: 'logistics_staff', logistics_manager: 'logistics_manager',
  outlet_staff: 'cs_walkin', outlet_manager: 'store_manager',
  hub: 'hub', hub_staff: 'hub', hub_manager: 'hub_manager',
  vendor: 'printer', printer_manager: 'printer', printer_staff: 'printer',
};
function opsRoleFor(account) {
  if (!account) return null;
  if (account.type === 'admin') return 'production_director';
  return ACCOUNT_ROLE[account.role] || null;
}

module.exports = { ROLES, STATUS, GATES, TRANSITIONS, roleCan, availableActions, resolveTransition, priorityCompare, opsRoleFor };
