/*
 * Printoka operations domain — the job state machine, hard gates, RBAC and priority rules from the
 * PRINTOKA PRODUCTION OPERATION MANUAL (Guidebook to Printoka Production, v1.0). Pure logic, no I/O.
 *
 * Organisation (§1.2): Production Director → Prepress / Scheduler / Logistics managers → their staff.
 *   Director: final authority, inter-department conflicts, overall KPI (§1.4)
 *   Managers: oversee daily operations, approve escalations, own the department KPI, report daily (§1.4)
 *   Staff:    execute tasks only, no override authority, escalate immediately (§1.4)
 *
 * Workflow (§1.8) — no skipping steps, no parallel shortcuts:
 *   1 Order enters system (payment confirmed)
 *   2 Prepress checks & approves the file   PASS → scheduler · MINOR → fix + approval · MAJOR → reject
 *                                           to outlet · CRITICAL → escalate to the prepress manager (§2.5)
 *   3 Scheduler queues the job              in-house: machine + time slot · outsourced: best quote (§3.5)
 *   4 Printing execution                    in-house printing done → logistics; the printer ships to production
 *   5 Logistics receives, packs & ships     the scheduler's job is done once logistics receives it; a shipment
 *                                           is complete when the customer / outlet receives it or the
 *                                           scheduler confirms delivery
 * Printers deliver to production (logistics receives) or straight to the outlet (§3.5).
 */

// ---- roles (§1.2 / §1.4) -----------------------------------------------------
const ROLES = {
  // outlet
  cs_walkin: { label: 'Customer Service (Walk-in)', dept: 'outlet', tier: 'staff' },
  print_consultant: { label: 'Printing Consultant (B2B)', dept: 'outlet', tier: 'staff' },
  store_manager: { label: 'Store / Assistant Manager', dept: 'outlet', tier: 'manager' },
  // production
  production_director: { label: 'Production Director', dept: 'all', tier: 'director' },
  prepress_staff: { label: 'Prepress Staff', dept: 'prepress', tier: 'staff' },
  prepress_manager: { label: 'Prepress Manager', dept: 'prepress', tier: 'manager' },
  scheduler_staff: { label: 'Scheduler Staff', dept: 'scheduler', tier: 'staff' },
  scheduler_manager: { label: 'Scheduler Manager', dept: 'scheduler', tier: 'manager' },
  logistics_staff: { label: 'Logistics Staff', dept: 'logistics', tier: 'staff' },
  logistics_manager: { label: 'Logistics Manager', dept: 'logistics', tier: 'manager' },
  // hub (legacy: no longer part of the production flow; kept for parcels already routed to a hub)
  hub: { label: 'Hub Staff', dept: 'hub', tier: 'staff' },
  hub_manager: { label: 'Hub Manager', dept: 'hub', tier: 'manager' },
  // external
  printer: { label: 'Outsource Printer', dept: 'vendor', tier: 'staff' },
  customer: { label: 'Customer', dept: 'customer', tier: 'staff' },
};

// ---- job statuses: each belongs to one department queue ----------------------
const STATUS = {
  // prepress statuses (user, 2026-09-25): New Order → Preflight → (Pending Customer Approval | Pending Customer Amendment) → scheduler New Order
  intake: { label: 'New Order', queue: 'prepress', step: 2 },
  prepress: { label: 'Preflight', queue: 'prepress', step: 2 },
  prepress_issue: { label: 'Pending Approval', queue: 'prepress', step: 2 },
  escalated: { label: 'Escalated to Manager', queue: 'prepress', step: 2 },
  rejected: { label: 'Pending Amendment', queue: 'prepress', step: 2 },
  scheduling: { label: 'New Order', queue: 'scheduler', step: 3 },
  printing: { label: 'Printing — in-house', queue: 'scheduler', step: 4 },
  outsourcing: { label: 'Printing — outsourced', queue: 'scheduler', step: 4 },
  // logistics statuses (user, 2026-09-25): Pending Receiving → Pending Pickup → Shipped → Completed
  printed: { label: 'Pending Receiving', queue: 'logistics', step: 5 },
  inbound: { label: 'Pending Receiving', queue: 'logistics', step: 5 },
  logistics: { label: 'Pending Pickup', queue: 'logistics', step: 5 },
  dispatched: { label: 'Shipped', queue: 'logistics', step: 5 },
  at_hub: { label: 'At hub (legacy)', queue: 'hub', step: 5 },
  ready_collect: { label: 'Ready for collection at outlet', queue: 'outlet', step: 5 },
  completed: { label: 'Completed', queue: 'done', step: 5 },
  cancelled: { label: 'Cancelled', queue: 'done', step: 5 },
};
const STEPS = ['Order entered', 'Prepress', 'Scheduler', 'Printing', 'Logistics'];

const OUTLET = ['cs_walkin', 'print_consultant', 'store_manager'];
const PREPRESS = ['prepress_staff', 'prepress_manager'];
const SCHEDULER = ['scheduler_staff', 'scheduler_manager'];
const LOGISTICS = ['logistics_staff', 'logistics_manager'];
const HUB = ['hub', 'hub_manager'];

// ---- checklists the system holds staff to (SOPs) -------------------------------
const CHECKLISTS = {
  // Receiving SOP §4.4
  receiving: [['matched', 'Outsourced order matches the physical item'], ['quantity', 'Quantity checked'], ['quality', 'Finishing quality checked'], ['unlabelled', 'Printer labels removed for relabelling']],
  // Packing (user, 2026-09-25): one step — the shipping label is printed, then the shipping page opens
  logistics: [['labelled', 'Shipping label printed']],
  hub: [['checked', 'Parcel checked against the order'], ['qc', 'Quality check passed'], ['relabelled', 'Relabelled / repacked']],
};
const checklistGate = (group, what) => job => {
  const s = (job.progress && job.progress[group]) || {}; const missing = CHECKLISTS[group].filter(c => !s[c[0]]).map(c => c[0]);
  return missing.length ? 'Complete the ' + what + ' first (' + missing.join(', ') + ').' : null;
};

// ---- gates: non-negotiable production policy (§1.7) ----------------------------
const destType = job => (job.destination && job.destination.type) || 'customer';
const GATES = {
  payment: job => (job.paymentValidated || job.creditTerms)
    ? null : 'No job proceeds without payment confirmation (bank transfer has to be validated).',
  artworkMatch: job => (job.artworkMatches || job.customerAuthorizedMismatch)
    ? null : 'Order details do not match the artwork requirement — the customer has to authorise it first.',
  artworkPresent: job => job.artwork && job.artwork.file && !/^pending-upload/.test(job.artwork.file)
    ? null : 'No artwork file attached to this job yet.',
  receivingDone: checklistGate('receiving', 'receiving checklist'),
  packingDone: job => ((job.progress && job.progress.logistics) || {}).labelled ? null : 'Print the shipping label first.',
  logisticsDone: checklistGate('logistics', 'packing checklist'),
  hubDone: checklistGate('hub', 'hub progress form'),
  destCustomer: job => destType(job) === 'customer' ? null : 'This parcel is going to a ' + destType(job) + ', not the customer.',
  destOutlet: job => destType(job) === 'outlet' ? null : 'This parcel is not addressed to an outlet.',
  destProduction: job => destType(job) === 'production' ? null : 'This parcel is not addressed to production.',
  destHub: job => destType(job) === 'hub' ? null : 'This parcel is not addressed to a hub.',
};

// ---- transition table ----------------------------------------------------------
// from -> [{ action, to, roles, gates, requires, note }]. The Production Director may perform any
// transition (final authority, §1.4). Staff never approve escalations — managers do.
const TRANSITIONS = {
  // New Order: prepress checks the order details, the payment and the customer, then marks it processed → Preflight
  intake: [
    { action: 'process', to: 'prepress', roles: PREPRESS, gates: ['payment'], note: 'Order processed — details, payment and customer checked. To preflight.' },
  ],
  // Step 2 — Prepress (§2.4–2.7)
  prepress: [
    { action: 'approve', to: 'scheduling', roles: PREPRESS, gates: ['artworkPresent'], note: 'PASS — released to the scheduler.' },
    { action: 'flag_minor', to: 'prepress_issue', roles: PREPRESS, requires: ['reason'], note: 'MINOR ISSUE — prepress amended the file and asked the customer to approve it.' },
    { action: 'reject_major', to: 'rejected', roles: PREPRESS, requires: ['reason'], note: 'MAJOR ISSUE — prepress contacted the customer for a new file.' },
    { action: 'escalate', to: 'escalated', roles: ['prepress_staff'], requires: ['reason'], note: 'CRITICAL — escalated to the prepress manager.' },
  ],
  prepress_issue: [
    { action: 'approve', to: 'scheduling', roles: PREPRESS, gates: ['artworkPresent'], requires: ['approval'], note: 'Customer approved the amended file — released to the scheduler.' },
    { action: 'reject_major', to: 'rejected', roles: PREPRESS, requires: ['reason'] },
    { action: 'escalate', to: 'escalated', roles: ['prepress_staff'], requires: ['reason'] },
  ],
  escalated: [
    { action: 'approve', to: 'scheduling', roles: ['prepress_manager'], gates: ['artworkPresent'], note: 'Manager approved — released to the scheduler.' },
    { action: 'flag_minor', to: 'prepress_issue', roles: ['prepress_manager'], requires: ['reason'], note: 'Manager: fix internally and seek approval.' },
    { action: 'reject_major', to: 'rejected', roles: ['prepress_manager'], requires: ['reason'] },
  ],
  rejected: [
    { action: 'resubmit', to: 'prepress', roles: OUTLET.concat(PREPRESS), requires: ['file'], note: 'Customer resubmitted the file — back to preflight.' },
  ],
  // Step 3 — Scheduler (§3.5 SOP: confirm prepress approval + payment, assign machine/printer, queue with a time slot)
  scheduling: [
    { action: 'assign_inhouse', to: 'printing', roles: SCHEDULER, gates: ['payment'], requires: ['machine', 'slot'], note: 'Queued in-house on a machine and time slot.' },
    { action: 'assign_outsource', to: 'outsourcing', roles: SCHEDULER, gates: ['payment'], requires: ['printer'], note: 'Outsourced to the printer with the best quote (cost, time, logistics).' },
  ],
  // Step 4 — Printing execution, monitored by the scheduler (§3.5 step 4)
  printing: [
    { action: 'finish', to: 'printed', roles: SCHEDULER, requires: ['qc'], note: 'Printed; spec and quality checked — handed to logistics.' },
  ],
  // in-house job done — the scheduler's job is complete once logistics receives it
  printed: [
    { action: 'receive', to: 'logistics', roles: LOGISTICS, note: 'Received from in-house production.' },
  ],
  outsourcing: [
    // the printer finishes the job, ships it and enters the delivery details (no draft step)
    { action: 'vendor_ship', to: 'inbound', roles: SCHEDULER.concat(['printer'], LOGISTICS), gates: ['destProduction'], requires: ['courier'], note: 'Printer shipped the job to production — delivery details entered.' },
    { action: 'vendor_ship_outlet', to: 'dispatched', roles: SCHEDULER.concat(['printer'], LOGISTICS), gates: ['destOutlet'], requires: ['courier'], note: 'Printer shipped the job straight to the outlet — delivery details entered.' },
  ],
  // Step 5 — Logistics (§4.4 receiving · §4.5 packing, delivery)
  inbound: [
    { action: 'receive', to: 'logistics', roles: LOGISTICS, note: 'Outsourced job received from the printer — to packing.' },
  ],
  logistics: [
    { action: 'dispatch', to: 'dispatched', roles: LOGISTICS, gates: ['packingDone'], requires: ['courier'], note: 'Assigned to the courier and dispatched.' },
  ],
  dispatched: [
    // shipped → complete when the customer (or outlet) receives it, or the scheduler confirms delivery
    { action: 'customer_received', to: 'completed', roles: ['customer'], gates: ['destCustomer'], note: 'Customer confirmed they received the order.' },
    { action: 'deliver', to: 'completed', roles: SCHEDULER, gates: ['destCustomer'], note: 'Scheduler confirmed the delivery.' },
    { action: 'receive_outlet', to: 'ready_collect', roles: OUTLET, gates: ['destOutlet'], note: 'Outlet received the parcel — customer notified it is ready for collection.' },
    { action: 'receive_hub', to: 'at_hub', roles: HUB, gates: ['destHub'], note: 'Hub received the parcel (legacy hub routing).' },
  ],
  at_hub: [
    { action: 'forward', to: 'dispatched', roles: HUB, gates: ['hubDone'], requires: ['courier'], note: 'Forwarded from the hub (legacy hub routing).' },
  ],
  ready_collect: [
    { action: 'collect', to: 'completed', roles: OUTLET, note: 'Customer collected the order.' },
  ],
};

function roleCan(role, t) {
  if (role === 'production_director') return true; // final authority (§1.4)
  return (t.roles || []).indexOf(role) !== -1;
}
function availableActions(job, role) {
  const list = TRANSITIONS[job.status] || [];
  return list.map(t => {
    const permitted = roleCan(role, t);
    const gateBlock = (t.gates || []).map(g => GATES[g](job)).filter(Boolean);
    return { action: t.action, to: t.to, toLabel: STATUS[t.to] && STATUS[t.to].label, note: t.note, requires: t.requires || [], permitted, blockedBy: gateBlock, enabled: permitted && gateBlock.length === 0 };
  });
}
function resolveTransition(job, role, action, payload) {
  const t = (TRANSITIONS[job.status] || []).find(x => x.action === action);
  if (!t) return { error: `Action "${action}" is not valid from status "${job.status}".` };
  if (!roleCan(role, t)) return { error: (ROLES[role] ? ROLES[role].label : role) + ' may not perform "' + action + '".' };
  for (const g of (t.gates || [])) { const r = GATES[g](job); if (r) return { error: r, gate: g }; }
  for (const f of (t.requires || [])) { if (!payload || payload[f] == null || payload[f] === '' || payload[f] === false) return { error: `Missing required field "${f}" for "${action}".` }; }
  return { transition: t };
}

// Priority is determined ONLY by (1) customer deadline, then (2) payment-confirmation time (§3.4).
function priorityCompare(a, b) {
  const da = a.deadline ? Date.parse(a.deadline) : Infinity;
  const db = b.deadline ? Date.parse(b.deadline) : Infinity;
  if (da !== db) return da - db;
  const pa = a.paymentValidatedAt ? Date.parse(a.paymentValidatedAt) : Infinity;
  const pb = b.paymentValidatedAt ? Date.parse(b.paymentValidatedAt) : Infinity;
  return pa - pb;
}


// Staff account role (login) → state-machine role, decided on the SERVER from the session.
// production_manager / production_staff are legacy logins: production and scheduler are one department.
const ACCOUNT_ROLE = {
  admin: 'production_director', production_director: 'production_director', production_manager: 'production_director', production_staff: 'scheduler_staff',
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
const deptOf = role => (ROLES[role] || {}).dept || null;
const tierOf = role => (ROLES[role] || {}).tier || null;

module.exports = { ROLES, STATUS, STEPS, CHECKLISTS, GATES, TRANSITIONS, roleCan, availableActions, resolveTransition, priorityCompare, opsRoleFor, deptOf, tierOf };
