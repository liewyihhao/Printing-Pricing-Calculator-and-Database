/*
 * Production — rebuilt on the PRINTOKA PRODUCTION OPERATION MANUAL (Guidebook to Printoka Production).
 * One production login; what you see depends on your role:
 *   Production Director — every department, daily reports, settings (final authority)
 *   Prepress manager / staff — file check (Pass · Minor · Major · Critical)
 *   Scheduler manager / staff — queue, in-house printing (machine + time slot), outsourcing
 *   Logistics manager / staff — receive outsourced jobs, pack & label, dispatch, confirm delivery
 * Same look as the outlet / customer account (account.js): header tabs, quick links, tables,
 * and one job page with the step's card, clear instructions and plainly named buttons.
 */
(function () {
  const C = window.PKComponent; if (!C) return;
  const P = C.prototype;

  const inp = { font: '400 13.5px Montserrat,sans-serif', padding: '9px 12px', border: '1px solid ' + HAIR, borderRadius: 8, width: '100%', background: '#fff' };
  const Btn = (label, onClick, kind, disabled) => h('button', { type: 'button', disabled: !!disabled, onClick: disabled ? undefined : onClick,
    style: { font: '600 13.5px Montserrat,sans-serif', padding: '11px 16px', borderRadius: 8, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? .5 : 1, textAlign: 'left',
      border: '1px solid ' + (kind === 'primary' ? TEAL : kind === 'danger' ? '#f5c8c7' : '#d9d9d9'), background: kind === 'primary' ? TEAL : '#fff', color: kind === 'primary' ? '#fff' : kind === 'danger' ? '#c71917' : INK } }, label);
  const Row = (...kids) => h('div', { style: { display: 'flex', gap: 8, flexWrap: 'wrap' } }, kids);
  const FG = (label, control, req, hint) => h('label', { style: { display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13, fontWeight: 600, color: INK } }, h('span', null, label, req ? h('span', { style: { color: TEAL } }, ' *') : null), hint ? h('span', { style: { fontSize: 12.5, fontWeight: 400, color: MUT } }, hint) : null, control);
  const note = t => h('p', { style: { margin: 0, fontSize: 13, color: MUT, lineHeight: 1.6 } }, t);
  const box = (t, tone) => h('div', { style: { fontSize: 13, lineHeight: 1.55, borderRadius: 8, padding: '11px 13px', background: tone === 'ok' ? '#e6f4ea' : tone === 'bad' ? '#fdecec' : '#fff8e6', color: tone === 'ok' ? '#1f5e2a' : tone === 'bad' ? '#8c1c13' : '#8a4b00' } }, t);
  const when = ts => { if (!ts) return '—'; const d = new Date(ts); return d.toLocaleDateString('en-GB').replace(/\//g, '-') + ' ' + d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }).toLowerCase(); };
  const dmy = ts => { if (!ts) return '—'; const d = new Date(ts); return String(d.getDate()).padStart(2, '0') + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + d.getFullYear(); };
  const link = (t, fn) => h('span', { onClick: fn, style: { color: TEAL, fontWeight: 600, cursor: 'pointer' } }, t);
  const ta = (v, set, rows) => h('textarea', { rows: rows || 4, value: v, onChange: e => set(e.target.value), style: Object.assign({}, inp, { resize: 'vertical' }) });

  // ---------------------------------------------------------------- who sees what
  const ROUTES = {
    production_director: ['production', 'prepress', 'scheduler', 'logistics'], production_manager: ['production', 'prepress', 'scheduler', 'logistics'],
    prepress: ['prepress'], prepress_manager: ['prepress'], scheduler: ['scheduler'], scheduler_manager: ['scheduler'], production_staff: ['scheduler'],
    logistics: ['logistics'], logistics_manager: ['logistics'],
  };
  const origAccess = P.access, origHome = P.homeFor;
  P.access = function () { if (this.userType() === 'production') return (ROUTES[this.userRole()] || ['prepress']).concat(['artwork', 'auth']); return origAccess.call(this); };
  P.homeFor = function (u) { u = u || this.state.user || {}; if (u.type === 'production') return (ROUTES[u.role] || ['prepress'])[0]; return origHome.call(this, u); };
  const isDirector = c => c.userType() === 'admin' || /^production_(director|manager)$/.test(c.userRole());
  const isManager = c => isDirector(c) || /_manager$/.test(c.userRole());
  const deptOf = c => ({ prepress: 'prepress', prepress_manager: 'prepress', scheduler: 'scheduler', scheduler_manager: 'scheduler', production_staff: 'scheduler', logistics: 'logistics', logistics_manager: 'logistics' })[c.userRole()] || null;
  const inDept = (c, d) => isDirector(c) || deptOf(c) === d;

  // queues (guidebook §1.8 steps)
  const Q = { prepress: ['prepress', 'prepress_issue', 'escalated'], scheduler: ['scheduling', 'printing', 'outsourcing'], logistics: ['printed', 'inbound', 'logistics', 'dispatched'] };
  const STEP = { intake: 1, prepress: 2, prepress_issue: 2, escalated: 2, rejected: 2, scheduling: 3, printing: 4, outsourcing: 4, printed: 5, inbound: 5, logistics: 5, dispatched: 5, at_hub: 5, ready_collect: 5, completed: 5, cancelled: 5 };
  const STEPS = ['Order entered', 'Prepress', 'Scheduler', 'Printing', 'Logistics'];
  const overdue = j => j.deadline && Date.parse(j.deadline) < Date.now() && ['completed', 'cancelled', 'ready_collect'].indexOf(j.status) < 0;
  const tone = j => j.status === 'completed' ? 'ok' : (j.status === 'rejected' || j.status === 'escalated' || overdue(j)) ? 'bad' : 'teal';

  // ---------------------------------------------------------------- page shell (same as the outlet account)
  const SHELL = { production: ['Production Director', 'layers'], prepress: ['Prepress', 'check'], scheduler: ['Scheduler', 'printer'], logistics: ['Logistics', 'truck'] };
  P.pShell = function (route, tabs, content) {
    const v = this.state.acView; const S = SHELL[route];
    const tab = tabs.indexOf(this.state.sTab) >= 0 ? this.state.sTab : tabs[0];
    const shell = { tabs, active: tab, icon: S[1], accent: 'linear-gradient(180deg,#1f3b73,#2e6bd9)', sub: S[0], menu: [['Dashboard', () => this.setState({ acView: null, sTab: tabs[0] })], ['Individual report', () => this.acOpen({ kind: 'individual' })]] };
    if (isDirector(this)) shell.menu = shell.menu.concat([['Prepress', () => this.go('prepress')], ['Scheduler', () => this.go('scheduler')], ['Logistics', () => this.go('logistics')], ['Director dashboard', () => this.go('production')]].filter(m => m[0] !== S[0]));
    let body;
    if (v && v.kind === 'job') { const d = this.acGet('job_' + v.id, '/api/jobs/' + encodeURIComponent(v.id)); const st = d && d.job ? STEP[d.job.status] || 1 : 0; if (st) shell.progress = { text: STEPS[st - 1] + ' - Step ' + st + ' of 5', width: st * 20 }; body = this.pJob(d, tabs); }
    else if (v && v.kind === 'quote') body = this.pQuote(v.id, tabs);
    else if (v && v.kind === 'individual') body = this.opsIndividual(() => this.setState({ acView: null }));
    else body = content(tab);
    return this.acPage(shell, body);
  };
  const openJob = (c, j) => c.acOpen({ kind: 'job', id: j.id });
  // one table for every list: job, product, customer, due, status
  P.pTable = function (key, title, jobs, extra) {
    const list = jobs.slice().sort((a, b) => { const da = a.deadline ? Date.parse(a.deadline) : Infinity, db = b.deadline ? Date.parse(b.deadline) : Infinity; if (da !== db) return da - db; return (Date.parse(a.paymentValidatedAt || 0) || Infinity) - (Date.parse(b.paymentValidatedAt || 0) || Infinity); });
    // "Handled by": who took the job in the department it is in now
    const handler = j => { const dq = j.queue || ({ prepress: 'prepress', prepress_issue: 'prepress', escalated: 'prepress', scheduling: 'scheduler', printing: 'scheduler', outsourcing: 'scheduler' })[j.status] || 'logistics'; return (j.owner || {})[dq] || '—'; };
    return this.acList({ key, title, action: extra, cols: ['Job', 'Product', 'Customer', 'Due', 'Handled by', 'Status'],
      rows: list.map(j => ({ date: j.createdAt, status: j.statusLabel || j.status, search: [j.id, j.orderId, j.customer, j.product, handler(j)],
        cells: [link(j.id, () => openJob(this, j)), j.product + ' × ' + (j.qty || 0).toLocaleString(), j.customer, h('span', { style: { color: overdue(j) ? '#c71917' : MUT, fontWeight: overdue(j) ? 700 : 400 } }, j.deadline ? dmy(j.deadline) + (overdue(j) ? ' · overdue' : '') : '—'), handler(j), this.pillDot(j.statusLabel || j.status, tone(j))] })) });
  };
  P.pTiles = function (items) { return this.acCard(this.acQuick(items)); };
  const jobsIn = (c, statuses) => c.opsJobs().filter(j => statuses.indexOf(j.status) >= 0);

  // ================================================================== PREPRESS
  P.s_prepress = function () {
    const tabs = ['Dashboard', 'Files', 'KPI'].concat(isManager(this) ? ['Daily report'] : []);
    return this.pShell('prepress', tabs, tab => {
      if (tab === 'Files') return this.pTable('pf', 'Files', jobsIn(this, ['prepress', 'prepress_issue', 'escalated', 'rejected']));
      if (tab === 'KPI') return this.pKpi('prepress');
      if (tab === 'Daily report') return this.pDaily('prepress');
      const q = jobsIn(this, Q.prepress);
      return [this.pTiles([
        { label: 'Files to check', value: jobsIn(this, ['prepress']).length, icon: 'check', color: 'teal', onClick: () => this.setState({ sTab: 'Files', pf_s: 'Prepress — file check' }) },
        { label: 'Minor issues', value: jobsIn(this, ['prepress_issue']).length, icon: 'edit-3', color: 'orange', onClick: () => this.setState({ sTab: 'Files', pf_s: 'Prepress — minor issue, awaiting approval' }) },
        { label: 'Escalated to manager', value: jobsIn(this, ['escalated']).length, icon: 'layers', color: 'red', onClick: () => this.setState({ sTab: 'Files', pf_s: 'Prepress — escalated to manager' }) },
        { label: 'Rejected to outlet', value: jobsIn(this, ['rejected']).length, icon: 'file', color: 'red', onClick: () => this.setState({ sTab: 'Files', pf_s: 'Rejected — returned to outlet' }) }])]
        .concat(this.pTable('pd', 'Your queue', q));
    });
  };

  // ================================================================== SCHEDULER
  // Quote request · Quote Pending from Printer · Jobs Outsourced · Jobs Inhouse
  const recent = ts => !ts || Date.now() - Date.parse(ts) < 30 * 864e5;
  const quoteFrom = q => q.outlet ? 'Outlet — ' + String(q.outlet).replace(/-/g, ' ') : 'Website customer';
  // a quote request is done once the priced quote is opened by the customer or the outlet
  const qrState = q => {
    if (['requested', 'amendment'].indexOf(q.status) >= 0 || q.price == null) return ['To price', 'warn', false];
    if (q.viewedAt || q.outletOpenedAt || ['reviewed', 'accepted', 'rejected', 'declined'].indexOf(q.status) >= 0) return ['Done — opened by ' + (q.viewedAt || q.status === 'reviewed' ? 'customer' : 'outlet'), 'ok', true];
    return ['Quoted — waiting to be opened', 'teal', false];
  };
  // a printer quote request is done once every printer's quote is in and opened by the scheduler
  const pqState = (printers, awarded) => {
    const got = printers.filter(p => p.submittedAt), unseen = got.filter(p => !p.seenAt);
    if (awarded || (printers.length && got.length === printers.length && !unseen.length)) return ['Done — quotes received', 'ok', true];
    if (unseen.length) return ['Quote received — open to review', 'bad', false];
    return ['Waiting for printers (' + got.length + ' of ' + printers.length + ')', 'warn', false];
  };
  const receivedByLogistics = j => !!(j.statusAt && (j.statusAt.logistics || j.statusAt.dispatched && j.dispatchDelivery)) || ['logistics'].indexOf(j.status) >= 0;
  const outState = j => {
    if (j.status === 'outsourcing') return [j.printing ? j.printing.status : 'Printing — outsourced', 'teal', false];
    if (j.status === 'inbound') return ['Printer shipped — waiting for logistics', 'warn', false];
    if (j.status === 'dispatched' && !receivedByLogistics(j)) return ['Printer shipped to the outlet', 'warn', false];
    return ['Done — received', 'ok', true];
  };
  const inState = j => j.status === 'printing' ? ['Printing on ' + (j.machine || 'machine'), 'teal', false] : j.status === 'printed' ? ['Printed — waiting for logistics', 'warn', false] : ['Done — received by logistics', 'ok', true];
  // a list with a clear state per row; open rows first, done rows (last 30 days) after
  P.pStateList = function (key, title, rows, cols) {
    rows = rows.filter(r => !r.state[2] || recent(r.date)).sort((a, b) => (a.state[2] - b.state[2]) || String(a.due || '9').localeCompare(String(b.due || '9')));
    return this.acList({ key, title, cols: cols.concat(['Status']), rows: rows.map(r => ({ date: r.date, status: r.state[0].replace(/ \(.*\)$/, ''), search: r.search, cells: r.cells.concat([this.pillDot(r.state[0], r.state[1])]) })) });
  };
  P.pQuoteRequests = function () {
    const qs = (this.acGet('p_quotes', '/api/quotes') || {}).quotes; if (!qs) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    return this.pStateList('qr', 'Quote request', qs.map(q => ({ date: q.createdAt, state: qrState(q), search: [q.id, q.customer && q.customer.name, q.requirement && q.requirement.product, q.outlet],
      cells: [link(q.id, () => this.acOpen({ kind: 'quote', id: q.id })), quoteFrom(q) + (q.issuedBy ? ' · ' + q.issuedBy.name : ''), (q.requirement && q.requirement.product) || '—', (q.customer && q.customer.name) || '—', (q.handler && q.handler.name) || '—', q.price != null ? this.rm(q.price) : '—'] })), ['Quote', 'From', 'Product', 'Customer', 'Handled by', { label: 'Price', right: true }]);
  };
  P.pPrinterPending = function () {
    const qs = ((this.acGet('p_quotes', '/api/quotes') || {}).quotes) || [];
    const rows = this.opsJobs().filter(j => j.outsource && (j.outsource.vendors || []).length && j.outsource.requestedAt).map(j => ({ date: j.outsource.requestedAt, state: pqState(j.outsource.vendors, !!j.outsource.awardedTo), search: [j.id, j.product, j.customer],
      cells: [link(j.id, () => openJob(this, j)), 'Job', j.product, (j.outsource.vendors || []).map(v => v.vendorName + (v.submittedAt ? ' — RM ' + Number(v.price).toFixed(2) : '')).join(', ')] }))
      .concat(qs.filter(q => q.printerQuotes && q.printerQuotes.printers.length).map(q => ({ date: q.printerQuotes.requestedAt, state: pqState(q.printerQuotes.printers, false), search: [q.id, q.requirement && q.requirement.product],
        cells: [link(q.id, () => this.acOpen({ kind: 'quote', id: q.id })), 'Custom quote', (q.requirement && q.requirement.product) || '—', q.printerQuotes.printers.map(p => p.vendorName + (p.submittedAt ? ' — RM ' + Number(p.amount).toFixed(2) : '')).join(', ')] })));
    return this.pStateList('pq', 'Quote Pending from Printer', rows, ['Ref', 'For', 'Product', 'Printers']);
  };
  P.pJobsOutsourced = function () {
    return this.pStateList('jo', 'Jobs Outsourced', this.opsJobs().filter(j => j.outsource && j.outsource.awardedTo).map(j => ({ date: j.createdAt, due: j.deadline, state: outState(j), search: [j.id, j.product, j.customer, j.outsource.po],
      cells: [link(j.id, () => openJob(this, j)), j.product + ' × ' + (j.qty || 0).toLocaleString(), ((j.outsource.vendors || []).find(v => v.vendorId === j.outsource.awardedTo) || {}).vendorName || '—', j.deadline ? dmy(j.deadline) : '—'] })), ['Job', 'Product', 'Printer', 'Due']);
  };
  P.pJobsInhouse = function () {
    return this.pStateList('ji', 'Jobs Inhouse', this.opsJobs().filter(j => j.route === 'inhouse' && ['scheduling'].indexOf(j.status) < 0).map(j => ({ date: j.createdAt, due: j.deadline, state: inState(j), search: [j.id, j.product, j.customer, j.machine],
      cells: [link(j.id, () => openJob(this, j)), j.product + ' × ' + (j.qty || 0).toLocaleString(), (j.machine || '—') + (j.slot ? ' · ' + when(j.slot) : ''), j.deadline ? dmy(j.deadline) : '—'] })), ['Job', 'Product', 'Machine · slot', 'Due']);
  };
  P.s_scheduler = function () {
    const tabs = ['Dashboard', 'Quote request', 'Quote Pending from Printer', 'Jobs Outsourced', 'Jobs Inhouse'].concat(isManager(this) ? ['KPI', 'Daily report'] : []);
    return this.pShell('scheduler', tabs, tab => {
      if (tab === 'Quote request') return this.pQuoteRequests();
      if (tab === 'Quote Pending from Printer') return this.pPrinterPending();
      if (tab === 'Jobs Outsourced') return this.pJobsOutsourced();
      if (tab === 'Jobs Inhouse') return this.pJobsInhouse();
      if (tab === 'KPI') return this.pKpi('scheduler');
      if (tab === 'Daily report') return this.pDaily('scheduler');
      const qs = ((this.acGet('p_quotes', '/api/quotes') || {}).quotes) || [], jobs = this.opsJobs();
      const open = arr => arr.filter(s => !s[2]).length;
      const pending = jobs.filter(j => j.outsource && (j.outsource.vendors || []).length && j.outsource.requestedAt).map(j => pqState(j.outsource.vendors, !!j.outsource.awardedTo)).concat(qs.filter(q => q.printerQuotes && q.printerQuotes.printers.length).map(q => pqState(q.printerQuotes.printers, false)));
      return [this.pTiles([
        { label: 'Quote request', value: open(qs.map(qrState)), icon: 'edit-3', color: 'teal', onClick: () => this.setState({ sTab: 'Quote request' }) },
        { label: 'Quote Pending from Printer', value: open(pending), icon: 'file', color: 'orange', onClick: () => this.setState({ sTab: 'Quote Pending from Printer' }) },
        { label: 'Jobs Outsourced', value: open(jobs.filter(j => j.outsource && j.outsource.awardedTo).map(outState)), icon: 'truck', color: 'teal', onClick: () => this.setState({ sTab: 'Jobs Outsourced' }) },
        { label: 'Jobs Inhouse', value: open(jobs.filter(j => j.route === 'inhouse' && j.status !== 'scheduling').map(inState)), icon: 'printer', color: 'teal', onClick: () => this.setState({ sTab: 'Jobs Inhouse' }) }])]
        .concat(this.pTable('sd', 'New jobs — print in-house or outsource', jobsIn(this, ['scheduling'])))
        .concat(this.pTable('sdl', 'Shipped to customers — confirm delivery', jobs.filter(j => j.status === 'dispatched' && (j.destination || {}).type === 'customer')))
        ;
    });
  };

  // ================================================================== LOGISTICS
  // Incoming Jobs (from printers) · Completed Jobs (from in-house) · Shipped
  const logState = j => ['inbound', 'printed'].indexOf(j.status) >= 0 ? ['Waiting to receive', 'warn', false] : j.status === 'logistics' ? ['Received — pack and ship', 'teal', false] : ['Done — shipped', 'ok', true];
  const shipState = j => j.status === 'dispatched' ? ['Shipped — waiting for delivery', 'teal', false] : ['Done — ' + (j.status === 'completed' ? 'delivered' : 'received by the outlet'), 'ok', true];
  const logRows = (c, list, st) => list.map(j => ({ date: j.createdAt, due: j.deadline, state: st(j), search: [j.id, j.product, j.customer],
    cells: [link(j.id, () => openJob(c, j)), j.product + ' × ' + (j.qty || 0).toLocaleString(), j.customer, (j.finalDestination || {}).name || '—'] }));
  const wasShipped = j => !!(j.dispatchDelivery || (j.statusAt && j.statusAt.logistics && ['dispatched', 'ready_collect', 'completed'].indexOf(j.status) >= 0));
  P.s_logistics = function () {
    const tabs = ['Dashboard', 'Incoming Jobs', 'Completed Jobs', 'Shipped'].concat(isManager(this) ? ['KPI', 'Daily report'] : []);
    const jobs = this.opsJobs();
    const incoming = jobs.filter(j => j.route === 'outsource' && (['inbound', 'logistics'].indexOf(j.status) >= 0 || wasShipped(j)));
    const completed = jobs.filter(j => j.route === 'inhouse' && (['printed', 'logistics'].indexOf(j.status) >= 0 || wasShipped(j)));
    const shipped = jobs.filter(j => (j.destination || {}).type !== 'hub' && (j.status === 'dispatched' || (wasShipped(j) && ['ready_collect', 'completed'].indexOf(j.status) >= 0)));
    const cols = ['Job', 'Product', 'Customer', 'Deliver to'];
    return this.pShell('logistics', tabs, tab => {
      if (tab === 'Incoming Jobs') return this.pStateList('li', 'Incoming Jobs — from printers', logRows(this, incoming, logState), cols);
      if (tab === 'Completed Jobs') return this.pStateList('lc', 'Completed Jobs — from in-house', logRows(this, completed, logState), cols);
      if (tab === 'Shipped') return this.pStateList('ls', 'Shipped', logRows(this, shipped, shipState), cols);
      if (tab === 'KPI') return this.pKpi('logistics');
      if (tab === 'Daily report') return this.pDaily('logistics');
      const open = (list, st) => list.filter(j => !st(j)[2]).length;
      return [this.pTiles([
        { label: 'Incoming Jobs', value: open(incoming, logState), icon: 'truck', color: 'orange', onClick: () => this.setState({ sTab: 'Incoming Jobs' }) },
        { label: 'Completed Jobs', value: open(completed, logState), icon: 'printer', color: 'teal', onClick: () => this.setState({ sTab: 'Completed Jobs' }) },
        { label: 'Shipped', value: open(shipped, shipState), icon: 'box', color: 'teal', onClick: () => this.setState({ sTab: 'Shipped' }) }])]
        .concat(this.pStateList('ld', 'To receive and ship', logRows(this, incoming.concat(completed).filter(j => !logState(j)[2]), logState), cols));
    });
  };

  // ================================================================== PRODUCTION DIRECTOR
  P.s_production = function () {
    const tabs = ['Dashboard', 'Prepress', 'Scheduler', 'Logistics', 'Reports', 'Settings'];
    return this.pShell('production', tabs, tab => {
      if (tab === 'Prepress' || tab === 'Scheduler' || tab === 'Logistics') { const d = tab.toLowerCase(); return this.pKpiTiles(d).concat(this.pTable('dir_' + d, tab, jobsIn(this, Q[d].concat(d === 'prepress' ? ['rejected'] : [])))); }
      if (tab === 'Reports') return this.pReports();
      if (tab === 'Settings') return this.pSettings();
      const all = this.opsJobs();
      const attention = all.filter(j => j.status === 'escalated' || (overdue(j) && Q.prepress.concat(Q.scheduler, Q.logistics).indexOf(j.status) >= 0));
      return [this.pTiles([
        { label: 'Prepress', value: jobsIn(this, Q.prepress).length, icon: 'check', color: 'teal', onClick: () => this.setState({ sTab: 'Prepress' }) },
        { label: 'Scheduler', value: jobsIn(this, Q.scheduler).length, icon: 'printer', color: 'teal', onClick: () => this.setState({ sTab: 'Scheduler' }) },
        { label: 'Logistics', value: jobsIn(this, Q.logistics).length, icon: 'truck', color: 'orange', onClick: () => this.setState({ sTab: 'Logistics' }) },
        { label: 'Needs attention', value: attention.length, icon: 'layers', color: 'red' }])]
        .concat(this.pTable('dir_att', 'Needs attention — escalated or overdue', attention));
    });
  };

  // ================================================================== the job page
  P.pJob = function (d, tabs) {
    if (!d) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    if (d.error) return [h('div', { key: 'e', style: { color: '#c0392b' } }, d.error)];
    const j = d.job, pr = d.printing || {}, id = j.id;
    const acts = {}; (j.actions || []).forEach(a => { if (a.permitted) acts[a.action] = a; });
    const main = [];
    const card = this.pStepCard(j, pr, acts); if (card) main.push(card);
    if (j.outsource && inDept(this, 'scheduler')) main.push(this.pOutsourceCard(j, pr));
    main.push(this.acC('Order details', [h('b', { key: 'p' }, j.product), this.acSpec((pr.job && pr.job.spec) || j.spec),
      this.acDL([['Quantity', (j.qty || 0).toLocaleString()], ['Customer', j.customer], ['Due', j.deadline ? when(j.deadline) + (overdue(j) ? ' — overdue' : '') : '—'], ['Deliver to', j.finalDestination ? (j.finalDestination.name || j.finalDestination.type) + (j.finalDestination.address ? ', ' + j.finalDestination.address : '') : '—'], j.instructions ? ['Instructions', j.instructions] : null, j.machine ? ['Machine', j.machine + (j.slot ? ' · ' + when(j.slot) : '')] : null]),
      (pr.job && pr.job.artworks || []).length ? h('div', { key: 'a', style: { background: ALT, borderRadius: 6, padding: 12, display: 'flex', flexDirection: 'column', gap: 6 } }, h('b', { style: { fontSize: 12.5 } }, 'Artwork'), pr.job.artworks.map((a, i) => a.id ? h('span', { key: i }, link('📄 ' + a.name, () => this.openOrderFile(a.orderId, a))) : h('span', { key: i, style: { color: MUT } }, '📄 ' + a.name))) : null]));
    // documents open as PDFs on the page (not for prepress — they only check files)
    const docs = deptOf(this) === 'prepress' ? [] : (pr.documents || []);
    // who took the job in each part (the first person in each department to open it)
    const hb = (d.handlers || []).map(x => [x.part, x.who ? h('span', null, x.who, x.at ? h('span', { style: { display: 'block', fontSize: 12, color: FAINT } }, when(x.at)) : null) : h('span', { style: { color: FAINT } }, 'Not yet')]);
    const aside = [hb.length ? this.acC('Handled by', this.acDL(hb)) : null, docs.length ? this.acC('Documents (PDF)', h('div', { style: { display: 'flex', flexDirection: 'column', gap: 8 } }, docs.map(x => Btn('View ' + x.label, () => this.openJobDoc(id, x.id))))) : null];
    const typeTab = tabs.indexOf('Files') >= 0 ? 'Files'
      : tabs.indexOf('Jobs Inhouse') >= 0 ? (j.route === 'inhouse' ? 'Jobs Inhouse' : j.route === 'outsource' ? 'Jobs Outsourced' : 'Dashboard')
      : tabs.indexOf('Incoming Jobs') >= 0 ? (j.status === 'dispatched' || j.status === 'completed' || j.status === 'ready_collect' ? 'Shipped' : j.route === 'inhouse' ? 'Completed Jobs' : 'Incoming Jobs') : tabs[1];
    return this.acSingle({ home: tabs[0], type: typeTab, title: '#' + id, statusNode: this.pillDot(j.statusLabel || j.status, tone(j)) }, main, aside);
  };
  // the one card for the step the job is at — only the department that owns the step can act
  P.pStepCard = function (j, pr, acts) {
    const id = j.id, st = j.status, role = this.userRole();
    const act = (action, payload, ok) => this.jPost('/api/jobs/' + id + '/transition', { action, payload: payload || {} }, ok, () => this.setState({ acModal: null, acForm: {} }));
    const blocked = a => a && a.blockedBy && a.blockedBy.length ? box(a.blockedBy.join(' '), 'bad') : null;
    // Step 2 — prepress file check (§2.4 order: basic → technical → content; §2.5 result)
    if (Q.prepress.indexOf(st) >= 0) {
      if (!inDept(this, 'prepress')) return this.acC('Prepress', note('The prepress team is checking this file.'));
      if (st === 'escalated' && !acts.approve) return this.acC('Escalated', [box('Escalated to the prepress manager: ' + (j.reason || '') + '. Waiting for the manager’s decision.')]);
      const CL = [['Basic verification', ['Product type matches the file', 'Quantity is correct', 'Size matches the specs']],
        ['Technical check', ['Resolution at least 300 dpi', 'Colour mode is CMYK', 'Bleed at least 3 mm', 'Safe margin respected', 'Fonts outlined / embedded', 'No white lines', 'No RGB colour', 'No complex or risky die-cutting', 'No Pantone colour', 'No elements outside the safe zone', 'No similar colours under 10%', 'No toning / colour under 10%']],
        ['Content check', ['No missing fonts', 'No alignment issues', 'No cropping errors']]];
      const ticked = this.acF('fc') || {}; const allTicked = CL.every(g => g[1].every(x => ticked[x]));
      const tick = x => this.acSetF('fc', Object.assign({}, ticked, { [x]: !ticked[x] }));
      const approve = acts.approve;
      return this.acC(st === 'prepress_issue' ? 'Minor issue — fix and get approval' : 'File check', [
        st === 'prepress_issue' ? box('Minor issue: ' + (j.reason || '') + '. Fix the file, send it to the customer (through the outlet) and release it once they approve.') : note('Check the file in this order. Tick each point, then choose the result.'),
        st !== 'prepress_issue' ? CL.map(g => h('div', { key: g[0], style: { display: 'flex', flexDirection: 'column', gap: 6 } }, h('b', { style: { fontSize: 13 } }, g[0]),
          g[1].map(x => h('label', { key: x, style: { display: 'flex', gap: 10, alignItems: 'center', fontSize: 13, cursor: 'pointer' } }, h('input', { type: 'checkbox', checked: !!ticked[x], onChange: () => tick(x), style: { width: 17, height: 17 } }), x)))) : null,
        blocked(approve),
        h('div', { key: 'b', style: { display: 'flex', flexDirection: 'column', gap: 8 } },
          approve && st === 'prepress_issue' ? Btn('Customer approved the fix — release to scheduler', () => this.pModal('Release to scheduler', [['approval', 'How did the customer approve the fix?', 'e.g. Approved by WhatsApp to the KL outlet, 25 Sep 10:30']], v => act('approve', { approval: v.approval }, 'Released to the scheduler.')), 'primary', !approve.enabled) : null,
          approve && st !== 'prepress_issue' ? Btn('Pass — release to scheduler', () => act('approve', {}, 'Passed — released to the scheduler.'), 'primary', !approve.enabled || !allTicked) : null,
          approve && st !== 'prepress_issue' && !allTicked ? note('Tick every check to pass the file.') : null,
          acts.flag_minor ? Btn('Minor issue — fix internally and get approval', () => this.pModal('Minor issue', [['reason', 'What needs fixing?', 'e.g. Bleed is 2 mm — extending it to 3 mm']], v => act('flag_minor', v, 'Marked as a minor issue.'))) : null,
          acts.reject_major ? Btn('Major issue — reject and return to outlet', () => this.pRejectModal(j), 'danger') : null,
          acts.escalate ? Btn('Critical — escalate to prepress manager', () => this.pModal('Escalate to manager', [['reason', 'Why is it critical?', '']], v => act('escalate', v, 'Escalated to the prepress manager.'))) : null)]);
    }
    if (st === 'rejected') return this.acC('Rejected — returned to outlet', [box('Issue: ' + (j.reason || '—') + (j.suggestion ? ' · Suggested correction: ' + j.suggestion : ''), 'bad'),
      (j.proofs || []).length ? link('📄 Proof: ' + j.proofs[j.proofs.length - 1].name, () => this.jDownload('/api/jobs/' + id + '/files/' + j.proofs[j.proofs.length - 1].id, j.proofs[j.proofs.length - 1].name)) : null,
      acts.resubmit ? Btn('Corrected file received — check again', () => this.pModal('Corrected file received', [['file', 'File name', 'e.g. bizcard-v2.pdf']], v => act('resubmit', v, 'Back in the prepress queue.')), 'primary') : null]);
    // Step 3 — scheduler (§3.5): confirm approval + payment, then in-house (machine + slot) or outsource
    if (st === 'scheduling') {
      if (!inDept(this, 'scheduler')) return this.acC('Scheduler', note('Waiting for the scheduler to queue this job.'));
      const a = acts.assign_inhouse; const cfg = this.state.opsConfig || { machines: [] };
      const machine = this.acF('machine') || cfg.machines[0] || '', slot = this.acF('slot'), parcels = this.acF('parcels') || '1';
      return this.acC('Schedule this job', [
        note('Priority is set only by the customer’s deadline, then payment time. Print it on one of our machines, or outsource it to the printer with the best quote below.'),
        blocked(a),
        h('b', { key: 'h1' }, 'Print in-house'),
        h('div', { key: 'f', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 12 } },
          FG('Machine', h('select', { value: machine, onChange: e => this.acSetF('machine', e.target.value), style: inp }, cfg.machines.map(m => h('option', { key: m }, m))), 1),
          FG('Time slot', h('input', { type: 'datetime-local', value: slot, onChange: e => this.acSetF('slot', e.target.value), style: inp }), 1),
          FG('Parcels', h('input', { type: 'number', min: 1, value: parcels, onChange: e => this.acSetF('parcels', e.target.value), style: inp }))),
        FG('Delivery instructions for logistics', h('input', { value: this.acF('instr'), onChange: e => this.acSetF('instr', e.target.value), placeholder: 'optional', style: inp })),
        h('div', { key: 'b' }, Btn('Queue in-house', () => this.jPost('/api/jobs/' + id + '/send-internal', { machine, slot, parcels, instructions: this.acF('instr') || undefined }, 'Queued on ' + machine + '.', () => this.setState({ acForm: {} })), 'primary', !a || !a.enabled || !machine || !slot))]);
    }
    // Step 4 — printing (in-house), monitored by the scheduler (§3.5 step 4, §3.6, §3.7)
    if (st === 'printing') {
      if (!inDept(this, 'scheduler')) return this.acC('Printing', note('Printing in-house on ' + (j.machine || 'a machine') + '.'));
      return this.acC('Printing in-house', [this.acDL([['Machine', j.machine], ['Time slot', j.slot ? when(j.slot) : '—'], ['Due', j.deadline ? when(j.deadline) : '—']]),
        note('When printing is finished, check the spec and quality against the order, then send it to logistics.'),
        h('div', { key: 'b', style: { display: 'flex', flexDirection: 'column', gap: 8 } },
          acts.finish ? Btn('Printing done — send to logistics', () => this.setState({ acForm: {}, acModal: { title: 'Printing done', body: () => [
            h('label', { key: 'q', style: { display: 'flex', gap: 10, fontSize: 13.5, alignItems: 'flex-start', cursor: 'pointer' } }, h('input', { type: 'checkbox', checked: !!this.acF('qc'), onChange: e => this.acSetF('qc', e.target.checked), style: { marginTop: 3 } }), 'The spec and print quality match the order.'),
            h('div', { key: 'b' }, Btn('Send to logistics', () => act('finish', { qc: true }, 'Sent to logistics.'), 'primary', !this.acF('qc')))] } }), 'primary') : null)]);
    }
    if (st === 'outsourcing') return inDept(this, 'scheduler') ? null : this.acC('Printing', note('Outsourced to a printer.'));
    // Step 5 — logistics (§4.4 receiving, §4.5 packing + delivery)
    const cl = (group, keys) => { const prog = (j.progress && j.progress[group]) || {}; const can = inDept(this, 'logistics');
      return keys.map(k => { const v = prog[k[0]]; return h('label', { key: k[0], style: { display: 'flex', gap: 10, alignItems: 'center', fontSize: 13, cursor: can ? 'pointer' : 'default' } },
        h('input', { type: 'checkbox', checked: !!v, disabled: !can, onChange: e => this.opsStep(id, group, k[0], e.target.checked), style: { width: 17, height: 17 } }), h('span', { style: { flex: 1 } }, k[1]), v ? h('span', { style: { fontSize: 12, color: FAINT } }, v.by) : null); }); };
    // Incoming Jobs (printer) — verify, then receive (this marks the scheduler's outsourced job done)
    if (st === 'inbound') {
      if (!inDept(this, 'logistics')) return this.acC('Logistics', note('The printer has shipped it — waiting for logistics to receive it.'));
      const RC = [['matched', 'The job matches the order'], ['quantity', 'Quantity is correct'], ['quality', 'Finishing quality is good'], ['unlabelled', 'Printer labels removed']];
      const pd = pr.printerDelivery;
      return this.acC('Receive from printer', [
        pd ? this.acDL([['Printer', ((j.outsource && (j.outsource.vendors || []).find(v => v.vendorId === j.outsource.awardedTo)) || {}).vendorName], ['Delivery company', pd.company], ['Tracking number', (pd.tracking || []).join(', ')], pd.document ? ['Delivery order', link(pd.document.name, () => this.jDownload('/api/jobs/' + id + '/files/' + pd.document.id, pd.document.name))] : null]) : null,
        note('When the parcel arrives, check it and tick each point, then press Received.'), cl('receiving', RC), blocked(acts.receive),
        acts.receive ? h('div', { key: 'b' }, Btn('Received', () => act('receive', {}, 'Received.'), 'primary', !acts.receive.enabled)) : null]);
    }
    // Completed Jobs (in-house) — receive from production (this marks the scheduler's in-house job done)
    if (st === 'printed') {
      if (!inDept(this, 'logistics')) return this.acC('Logistics', note('Printed — waiting for logistics to receive it.'));
      return this.acC('Receive from production', [note('Collect the printed job from production, then press Received.'),
        acts.receive ? h('div', { key: 'b' }, Btn('Received', () => act('receive', {}, 'Received.'), 'primary')) : null]);
    }
    if (st === 'logistics') {
      if (!inDept(this, 'logistics')) return this.acC('Logistics', note('Received by logistics — being packed.'));
      return this.pDispatchCard(j, pr, acts, cl);
    }
    // Shipped — complete when the customer or outlet receives it, or the scheduler confirms delivery
    if (st === 'dispatched') {
      const toCustomer = (j.destination || {}).type === 'customer';
      return this.acC('Shipped', [this.acDL([['Courier', j.courier], ['Tracking', j.tracking], ['To', ((j.destination || {}).name || '') + ((j.destination || {}).address ? ', ' + j.destination.address : '')]]),
        note(toCustomer ? 'Complete when the customer confirms they received it, or when the scheduler confirms delivery.' : 'Complete when the outlet receives it.'),
        toCustomer && acts.deliver && inDept(this, 'scheduler') ? h('div', { key: 'b' }, Btn('Delivered — mark complete', () => act('deliver', {}, 'Marked delivered.'), 'primary')) : null]);
    }
    if (st === 'at_hub') return this.acC('At the hub', note('This parcel was sent to a hub before hubs were removed from the flow. The hub team forwards it.'));
    if (st === 'ready_collect') return this.acC('At the outlet', note('Ready for the customer to collect.'));
    if (st === 'completed') return this.acC('Completed', box('Delivered / collected.', 'ok'));
    return null;
  };
  // Delivery SOP (§4.5): courier from HQ's list, dispatch (time recorded), then confirmation
  P.pDispatchCard = function (j, pr, acts, cl) {
    const cfg = this.state.opsConfig || { couriers: [] }; const dd = pr.dispatchDelivery || {}; const packing = j.status === 'logistics';
    const F = (k, def) => this.acF(k) !== '' ? this.acF(k) : def;
    const tracking = F('dTracking', (dd.tracking || []).join('\n')), courier = F('dCourier', dd.company || cfg.couriers[0] || '');
    const a = acts.dispatch;
    const PC = [['verified', 'Checked — order vs item, quantity and quality'], ['packed', 'Packed — protected from damage'], ['labelled', 'Shipping label stuck on every parcel']];
    return this.acC('Pack & ship', [
      note('Pack the order, print the shipping label, then enter the courier and tracking number and press Ship.'),
      cl ? cl('logistics', PC) : null,
      h('div', { key: 'lb' }, Btn('View Shipping Label (PDF)', () => this.openJobDoc(j.id, 'shipping-label'))),
      this.acDL([['Deliver to', ((j.destination || {}).name || '—') + ((j.destination || {}).address ? ', ' + j.destination.address : '')], ['Parcels', j.parcels || 1]]),
      FG('Courier', h('select', { value: courier, onChange: e => this.acSetF('dCourier', e.target.value), style: inp }, cfg.couriers.map(c => h('option', { key: c }, c))), 1, 'Only the delivery companies selected by HQ.'),
      FG('Tracking number', ta(tracking, v => this.acSetF('dTracking', v), 3), 1, 'One per line if there is more than one parcel.'),
      FG('Delivery order', h('div', { style: { display: 'flex', flexDirection: 'column', gap: 6 } }, dd.document ? link('📄 ' + dd.document.name, () => this.jDownload('/api/jobs/' + j.id + '/files/' + dd.document.id, dd.document.name)) : null, this.jPickFile('dDoc'))),
      packing && a && a.blockedBy && a.blockedBy.length ? box(a.blockedBy.join(' '), 'bad') : null,
      h('div', { key: 'b' }, Btn(packing ? 'Ship' : 'Save changes', () => this.jPost('/api/jobs/' + j.id + '/delivery', { tracking, company: courier, documentData: this.acF('dDocData') || undefined, documentName: this.acF('dDocName') || undefined }, packing ? 'Dispatched.' : 'Delivery details saved.', () => this.setState({ acForm: {} })), 'primary', !tracking.trim() || (packing && (!a || !a.enabled))))]);
  };
  // outsourcing (§3.5 rules: cost, production time, logistics — never preference or pressure)
  P.pOutsourceCard = function (j, pr) {
    const o = j.outsource || {}; const id = j.id; const vendors = (this.acGet('vendors', '/api/vendors') || {}).vendors || [];
    const quotes = pr.quotes || [];
    const canAward = !o.awardedTo && j.status === 'scheduling';
    const rows = quotes.map(q => h('tr', { key: q.vendorId }, [q.vendorName, q.amount != null ? 'RM ' + Number(q.amount).toFixed(2) : 'no quote yet', q.leadDays ? q.leadDays + ' days' : '—',
      q.document ? link(q.document.name, () => this.jDownload('/api/jobs/' + id + '/files/' + q.document.id, q.document.name)) : '—',
      q.awarded ? this.pillDot('Awarded', 'ok') : canAward && q.submittedAt ? Btn('Award', () => this.pAwardModal(j, q)) : ''].map((c, i) => h('td', { key: i, style: { padding: '9px 8px', borderTop: '1px solid ' + LINE, fontSize: 13 } }, c))));
    return this.acC(o.awardedTo ? 'Outsourced' : 'Outsource', [
      !o.awardedTo ? note('Choose the printer by cost, production time and delivery to the outlet or production only.') : null,
      quotes.length ? h('div', { key: 't', style: { overflowX: 'auto' } }, h('table', { style: { width: '100%', borderCollapse: 'collapse' } }, h('thead', null, h('tr', null, ['Printer', 'Quote', 'Time', 'Document', ''].map(c => h('th', { key: c, style: { textAlign: 'left', padding: '6px 8px', fontSize: 12 } }, c)))), h('tbody', null, rows))) : null,
      canAward && !quotes.length ? [h('div', { key: 'v', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(200px,1fr))', gap: 8 } }, vendors.map(v => { const picked = this.acF('vids') || []; return h('label', { key: v.id, style: { display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, cursor: 'pointer' } }, h('input', { type: 'checkbox', checked: picked.indexOf(v.id) >= 0, onChange: () => this.acSetF('vids', picked.indexOf(v.id) >= 0 ? picked.filter(x => x !== v.id) : picked.concat([v.id])) }), v.name); })),
        h('div', { key: 'rb' }, Btn('Request quotes', () => this.jPost('/api/jobs/' + id + '/request-quotes', { vendorIds: this.acF('vids') || [] }, 'Quote requests sent.', () => this.setState({ acForm: {} })), 'primary', !(this.acF('vids') || []).length))] : null,
      canAward && /scheduler_manager/.test(this.userRole()) || (canAward && isDirector(this)) ? h('div', { key: 'dir' }, Btn('Award without a quote…', () => this.pAwardModal(j, null))) : null,
      pr.po ? this.acDL([['Purchase order', pr.po], ['Printer delivers to', (j.destination || {}).name]]) : null,
      pr.printerDelivery ? this.acDL([['Printer shipped', when(pr.printerDelivery.at)], ['Delivery company', pr.printerDelivery.company], ['Tracking number', (pr.printerDelivery.tracking || []).join(', ')], pr.printerDelivery.document ? ['Delivery order', link(pr.printerDelivery.document.name, () => this.jDownload('/api/jobs/' + id + '/files/' + pr.printerDelivery.document.id, pr.printerDelivery.document.name))] : null]) : null,
      o.awardedTo && j.status === 'outsourcing' ? note('Purchase order sent. Waiting for the printer to finish the job and enter the delivery details.') : null,
      // the scheduler pays the printer once Printoka has received the job
      inDept(this, 'scheduler') && pr.awarded && !pr.paidAt && pr.status && pr.status.id === 'shipped' ? Btn('Mark printer paid', () => this.pModal('Mark printer paid', [['reference', 'Payment reference', 'e.g. IBG-7781']], v => this.jPost('/api/jobs/' + id + '/vendor-paid', v, 'Printer marked paid.', () => this.setState({ acModal: null }))), 'primary') : null,
      pr.paidAt ? box('Printer paid.', 'ok') : null]);
  };

  // ---------------------------------------------------------------- pop-ups (one question each, one button)
  P.pModal = function (title, fields, submit, submitLabel) {
    this.setState({ acForm: {}, acModal: { title, body: () => fields.map(f => FG(f[1], ta(this.acF(f[0]), v => this.acSetF(f[0], v), 3), 1, f[2] || null))
      .concat([h('div', { key: 'b' }, Btn(submitLabel || 'Confirm', () => { const v = {}; fields.forEach(f => { v[f[0]] = this.acF(f[0]); }); submit(v); }, 'primary', fields.some(f => !String(this.acF(f[0]) || '').trim())))]) } });
  };
  P.pRejectModal = function (j) {
    this.setState({ acForm: {}, acModal: { title: 'Reject and return to outlet', body: () => [
      note('Never use vague reasons like “file problem”. State the issue, attach a screenshot and suggest the correction.'),
      FG('Issue', ta(this.acF('reason'), v => this.acSetF('reason', v), 3), 1, 'e.g. Text runs into the 3 mm bleed on the right edge'),
      FG('Screenshot', this.jPickFile('proof'), 1),
      FG('Suggested correction', ta(this.acF('suggestion'), v => this.acSetF('suggestion', v), 3), 1, 'e.g. Move the text 5 mm inwards and resend the PDF'),
      h('div', { key: 'b' }, Btn('Reject and return to outlet', () => this.aFetchJ('/api/jobs/' + j.id + '/proof', { name: this.acF('proofName'), data: this.acF('proofData') }).then(f => {
        if (!this.acDone(f)) return; this.jPost('/api/jobs/' + j.id + '/transition', { action: 'reject_major', payload: { reason: this.acF('reason'), proof: f.file.id, suggestion: this.acF('suggestion') } }, 'Rejected and returned to the outlet.', () => this.setState({ acModal: null, acForm: {} })); }), 'primary', !this.acF('reason') || !this.acF('suggestion') || !this.acF('proofData')))] } });
  };
  P.pAwardModal = function (j, q) {
    const pickup = j.finalDestination && j.finalDestination.type === 'outlet'; const vendors = (this.acGet('vendors', '/api/vendors') || {}).vendors || [];
    this.setState({ acForm: {}, acModal: { title: q ? 'Award to ' + q.vendorName : 'Award without a quote', body: () => [
      q ? this.acDL([['Quote', 'RM ' + Number(q.amount).toFixed(2)], ['Production time', q.leadDays ? q.leadDays + ' days' : '—']]) : FG('Printer', h('select', { value: this.acF('vid'), onChange: e => this.acSetF('vid', e.target.value), style: inp }, [h('option', { key: '', value: '' }, 'Choose a printer…')].concat(vendors.map(v => h('option', { key: v.id, value: v.id }, v.name)))), 1),
      FG('The printer delivers to', h('select', { value: this.acF('dest') || 'production', onChange: e => this.acSetF('dest', e.target.value), style: inp }, [h('option', { key: 'p', value: 'production' }, 'Production — logistics receives, repacks and delivers')].concat(pickup ? [h('option', { key: 'o', value: 'outlet' }, 'Straight to ' + j.finalDestination.name)] : [])), 1),
      !q ? h('label', { key: 'c', style: { display: 'flex', gap: 10, fontSize: 13, color: '#8a4b00', background: '#fff8e6', borderRadius: 8, padding: '10px 12px', cursor: 'pointer' } }, h('input', { type: 'checkbox', checked: !!this.acF('confirm'), onChange: e => this.acSetF('confirm', e.target.checked) }), 'This printer didn’t submit a quote yet. Please make sure it is internal production.') : null,
      h('div', { key: 'b' }, Btn('Confirm award', () => this.jPost('/api/jobs/' + j.id + '/award', { vendorId: q ? q.vendorId : this.acF('vid'), destType: this.acF('dest') || 'production', confirmNoQuote: !q ? !!this.acF('confirm') : undefined }, 'Job awarded.', () => this.setState({ acModal: null, acForm: {} })), 'primary', !q && (!this.acF('vid') || !this.acF('confirm'))))] } });
  };

  // ---------------------------------------------------------------- KPI (§7)
  P.pKpiTiles = function (dept) {
    const k = (this.acGet('kpi_' + dept, '/api/ops/kpi?dept=' + dept + '&days=30') || {}).kpi;
    if (!k) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    return [this.acCard(h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))' } }, (k.metrics || []).map(m => h('div', { key: m.label, style: { padding: 20, boxShadow: '1px 1px 0 ' + HAIR } },
      h('div', { style: { fontWeight: 700, fontSize: 14 } }, m.label), h('div', { style: { fontSize: 28, fontWeight: 600, marginTop: 8 } }, String(m.value)), h('div', { style: { fontSize: 12.5, color: MUT, marginTop: 4 } }, m.note)))))];
  };
  P.pKpi = function (dept) {
    const k = (this.acGet('kpi_' + dept, '/api/ops/kpi?dept=' + dept + '&days=30') || {}).kpi;
    const me = (this.state.user || {}).name; const mgr = isManager(this);
    const staff = k ? (k.staff || []).filter(s => mgr || s.actor === me) : [];
    return [h('h1', { key: 't', style: { fontSize: 34, fontWeight: 600, margin: '6px 0 0' } }, mgr ? 'Department KPI' : 'My KPI'), note('Last 30 days, from the actions recorded in the system.')].concat(mgr ? this.pKpiTiles(dept) : [])
      .concat([h('div', { key: 's' }, this.dataCard(['Staff', { label: 'Actions', right: true }, { label: 'Average time', right: true }, { label: dept === 'prepress' ? 'Within SLA' : 'On time', right: true }],
        staff.map(s => [s.actor, String(s.count), s.avgMins == null ? '—' : s.avgMins + ' min', (dept === 'prepress' ? s.slaPct : s.onTimePct) == null ? '—' : (dept === 'prepress' ? s.slaPct : s.onTimePct) + '%']), { minWidth: 560, empty: 'No actions recorded yet.' }))]);
  };

  // ---------------------------------------------------------------- daily report (§1.6): manager → director
  P.pDaily = function (dept) {
    const kind = this.state.drKind || (new Date().getHours() < 13 ? 'morning' : 'evening');
    const f = (this.acGet('dr_' + dept, '/api/ops/daily-report?dept=' + dept) || {}).figures;
    const past = (this.acGet('drl_' + dept, '/api/ops/reports') || {}).reports || [];
    const list = (arr, fn, empty) => arr && arr.length ? h('ul', { style: { margin: 0, paddingLeft: 18, fontSize: 13, lineHeight: 1.7 } }, arr.map((x, i) => h('li', { key: i }, fn(x)))) : note(empty);
    const field = (k, label, hint) => FG(label, ta(this.acF(k), v => this.acSetF(k, v), 3), 0, hint);
    return [h('h1', { key: 't', style: { fontSize: 34, fontWeight: 600, margin: '6px 0 0' } }, 'Daily report'),
      h('div', { key: 'k', style: { display: 'flex', gap: 8 } }, [['morning', 'Morning report'], ['evening', 'End-of-day report']].map(x => Btn(x[1], () => this.setState({ drKind: x[0] }), kind === x[0] ? 'primary' : null))),
      !f ? h('div', { key: 'l', style: { color: FAINT } }, 'Loading…') : this.acC(kind === 'morning' ? 'Morning report — start of day' : 'End-of-day report', kind === 'morning' ? [
        this.acDL([['Total jobs pending', String(f.pending)]]), h('b', { key: 'u' }, 'Urgent jobs'), list(f.urgent, x => x.id + ' · ' + x.product + ' · due ' + dmy(x.deadline), 'No urgent jobs.'),
        f.machines ? [h('b', { key: 'm' }, 'Machines'), list(f.machines, x => x.machine + ': ' + x.jobs + ' job(s) printing' + (x.downToday ? ' · down today' : ''), '')] : null,
        field('status', 'Machine / manpower status', 'e.g. Offset press under service until 11am; 1 staff on leave'),
        h('div', { key: 'b' }, Btn('Submit to Production Director', () => this.jPost('/api/ops/daily-report', { dept, kind, status: this.acF('status') }, 'Morning report submitted.', () => { this.acDrop('drl_'); this.setState({ acForm: {} }); }), 'primary'))] : [
        this.acDL([['Jobs completed', String(f.completed)], ['Tomorrow’s backlog', f.backlog.length + ' job(s)']]),
        h('b', { key: 'd' }, 'Jobs past the customer deadline'), list(f.delayed, x => x.id + ' · ' + x.product, 'None.'),
        field('backlog', 'Notes for tomorrow'),
        h('div', { key: 'b' }, Btn('Submit to Production Director', () => this.jPost('/api/ops/daily-report', { dept, kind, backlog: this.acF('backlog') }, 'End-of-day report submitted.', () => { this.acDrop('drl_'); this.setState({ acForm: {} }); }), 'primary'))]),
      h('div', { key: 'p' }, this.dataCard(['Date', 'Report', 'By', 'Pending', 'Completed', 'Past deadline'], past.map(r => [r.date, r.kind === 'morning' ? 'Morning' : 'End of day', r.by, String(r.figures.pending), r.kind === 'evening' ? String(r.figures.completed) : '—', r.kind === 'evening' ? String((r.figures.delayed || []).length) : '—']), { minWidth: 600, empty: 'No reports submitted yet.' }))];
  };
  P.pReports = function () {
    const rs = (this.acGet('drl_all', '/api/ops/reports') || {}).reports || [];
    const today = new Date().toISOString().slice(0, 10);
    const has = (d, k) => rs.some(r => r.dept === d && r.kind === k && r.date === today);
    return [h('h1', { key: 't', style: { fontSize: 34, fontWeight: 600, margin: '6px 0 0' } }, 'Daily reports'),
      this.dataCard(['Department', 'Morning report', 'End-of-day report'], ['prepress', 'scheduler', 'logistics'].map(d => [d[0].toUpperCase() + d.slice(1), this.pillDot(has(d, 'morning') ? 'Submitted' : 'Not yet', has(d, 'morning') ? 'ok' : 'warn'), this.pillDot(has(d, 'evening') ? 'Submitted' : 'Not yet', has(d, 'evening') ? 'ok' : 'warn')]), { minWidth: 480 }),
      h('div', { key: 'l', style: { display: 'flex', flexDirection: 'column', gap: 12 } }, rs.map(r => this.acC(r.date + ' · ' + r.dept[0].toUpperCase() + r.dept.slice(1) + ' · ' + (r.kind === 'morning' ? 'Morning' : 'End of day') + ' · ' + r.by, [
        this.acDL([['Pending', String(r.figures.pending)], ['Urgent', r.figures.urgent.map(x => x.id).join(', ') || '—'], r.kind === 'evening' ? ['Completed', String(r.figures.completed)] : null, r.kind === 'evening' ? ['Past deadline', (r.figures.delayed || []).map(x => x.id).join(', ') || '—'] : null,
          r.notes.status ? ['Machine / manpower', r.notes.status] : null, r.notes.backlog ? ['Notes for tomorrow', r.notes.backlog] : null])])))];
  };

  // ---------------------------------------------------------------- settings
  P.pSettings = function () {
    const cfg = this.state.opsConfig; if (!cfg) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    const F = (k, def) => this.acF(k) !== '' ? this.acF(k) : def;
    const v = { machines: F('machines', cfg.machines.join('\n')), couriers: F('couriers', cfg.couriers.join('\n')), site: F('site', cfg.productionSite || ''), address: F('address', cfg.productionAddress || ''), phone: F('phone', cfg.productionPhone || '') };
    return [h('h1', { key: 't', style: { fontSize: 34, fontWeight: 600, margin: '6px 0 0' } }, 'Settings'),
      this.acC('Production site', [note('Printers deliver outsourced jobs here; it is also the sender on every label.'),
        FG('Name', h('input', { value: v.site, onChange: e => this.acSetF('site', e.target.value), style: inp }), 1), FG('Address', ta(v.address, x => this.acSetF('address', x), 2), 1), FG('Phone', h('input', { value: v.phone, onChange: e => this.acSetF('phone', e.target.value), style: inp }))]),
      this.acC('Machines', FG('One machine per line', ta(v.machines, x => this.acSetF('machines', x), 6))),
      this.acC('Delivery companies', FG('One per line — logistics can only choose from this list', ta(v.couriers, x => this.acSetF('couriers', x), 6))),
      h('div', { key: 'b' }, Btn('Save settings', () => this.opsFetch('/api/ops/config', { machines: v.machines.split('\n').map(s => s.trim()).filter(Boolean), couriers: v.couriers.split('\n').map(s => s.trim()).filter(Boolean), productionSite: v.site, productionAddress: v.address, productionPhone: v.phone })
        .then(d => { if (this.acDone(d, 'Settings saved.')) this.setState({ opsConfig: d.config, acForm: {} }); }), 'primary'))];
  };

  // ---------------------------------------------------------------- a quote request (from an outlet or a website customer)
  // Opening it takes it (the scheduler's name goes in the log). Reply with the internal production
  // price, or ask printers first and reply using their quote. The reply goes to the customer and the outlet.
  P.pQuote = function (qid, tabs) {
    const d = this.acGet('q1_' + qid, '/api/quotes/' + encodeURIComponent(qid)); if (!d) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    const q = d.quote; if (!q) return [h('div', { key: 'e' }, 'Quote not found.')];
    if (!(this._pqOpened || {})[qid]) { this._pqOpened = Object.assign({}, this._pqOpened, { [qid]: 1 }); setTimeout(() => this.acDrop('p_quotes'), 0); } // list shows the new handler
    const refresh =() => { this.acDrop('q1_'); this.acDrop('p_quotes'); this.setState({ acForm: {} }); };
    const r = q.requirement || {}; const open = ['requested', 'amendment', 'issued', 'reviewed'].indexOf(q.status) >= 0;
    const pq = (q.printerQuotes || {}).printers || [];
    const replied = pq.filter(p => p.submittedAt);
    const bases = ['Internal production price'].concat(replied.map(p => 'Printer quote — ' + p.vendorName + ' (RM ' + Number(p.amount).toFixed(2) + ')'));
    const basis = this.acF('basis') || q.priceBasis || bases[0];
    const main = [
      this.acC('Specifications', [h('b', { key: 'p' }, r.product || 'Custom job'), h('div', { key: 's', style: { whiteSpace: 'pre-wrap', lineHeight: 1.7 } }, r.quoteData || [r.size, r.material, r.finishing, r.qty && 'Qty ' + r.qty, r.remarks].filter(Boolean).join('\n'))]),
      open ? this.acC('Ask a printer for a quote', [
        note('Optional. Ask one or more printers, wait for their reply, then use their quote below.'),
        pq.length ? this.dataCard(['Printer', 'Weight (kg)', { label: 'Amount', right: true }, 'Document'], pq.map(p => [p.vendorName, p.weight || '—', p.amount != null ? this.rm(p.amount) : 'Waiting for reply', p.document ? link(p.document.name, () => this.jDownload('/api/quotes/' + q.id + '/printer-quotes/' + p.vendorId + '/document', p.document.name)) : '—']), { minWidth: 480 }) : null,
        h('div', { key: 'v', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(200px,1fr))', gap: 8 } }, ((this.acGet('vendors', '/api/vendors') || {}).vendors || []).filter(v => !pq.some(p => p.vendorId === v.id)).map(v => { const picked = this.acF('qv') || []; return h('label', { key: v.id, style: { display: 'flex', gap: 8, fontSize: 13, cursor: 'pointer' } }, h('input', { type: 'checkbox', checked: picked.indexOf(v.id) >= 0, onChange: () => this.acSetF('qv', picked.indexOf(v.id) >= 0 ? picked.filter(x => x !== v.id) : picked.concat([v.id])) }), v.name); })),
        h('div', { key: 'b' }, Btn('Ask printer to quote', () => this.aFetchJ('/api/quotes/' + q.id + '/printer-quotes', { vendorIds: this.acF('qv') || [] }).then(x => { if (this.acDone(x, 'Printer asked to quote.')) refresh(); }), null, !(this.acF('qv') || []).length))]) : null,
      open ? this.acC(q.price != null ? 'Quote sent — change the price' : 'Reply with the price', [
        note('The customer and the outlet receive the quote as soon as you send it.'),
        FG('Price based on', h('select', { value: basis, onChange: e => this.acSetF('basis', e.target.value), style: inp }, bases.map(b => h('option', { key: b, value: b }, b))), 1),
        h('div', { key: 'f', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 12 } },
          FG('Price to customer (RM)', h('input', { type: 'number', value: this.acF('price') !== '' ? this.acF('price') : (q.price != null ? q.price : ''), onChange: e => this.acSetF('price', e.target.value), style: inp }), 1),
          FG('Lead time (days)', h('input', { type: 'number', value: this.acF('lead') !== '' ? this.acF('lead') : (q.leadDays || ''), onChange: e => this.acSetF('lead', e.target.value), style: inp }))),
        h('div', { key: 'b' }, Btn('Send quote', () => this.aFetchJ('/api/quotes/' + q.id + '/price', { price: this.acF('price') || q.price, leadDays: this.acF('lead') || q.leadDays, basis }).then(x => { if (this.acDone(x, 'Quote sent to the customer' + (q.outlet ? ' and the outlet.' : '.'))) refresh(); }), 'primary', !(this.acF('price') || q.price)))]) : null,
    ];
    // opening the quote marks received printer quotes as seen ("Quote Pending from Printer" → done)
    if (pq.some(p => p.submittedAt && !p.seenAt) && !(this._pqSeen || {})[q.id]) { this._pqSeen = Object.assign({}, this._pqSeen, { [q.id]: 1 }); this.aFetchJ('/api/quotes/' + q.id + '/printer-quotes').then(() => { this.acDrop('p_quotes'); }); }
    // the log: who took the quote at each step
    const LABEL = { issued: 'Quoted', reviewed: 'Opened by the customer', accepted: 'Accepted by the customer', rejected: 'Rejected', 'Pending Quote': 'Quote request sent to the scheduler' };
    const log = (q.history || []).filter(x => !(x.action === 'issued' && q.outlet)).slice().reverse().map(x => ({ title: LABEL[x.action] || String(x.action || '').replace(/^./, c => c.toUpperCase()), by: x.actor, at: x.ts, text: [x.price != null ? 'RM ' + Number(x.price).toFixed(2) : '', x.note || ''].filter(Boolean).join(' · ') }));
    const aside = [
      this.acC('Handled by', this.acDL([['Requested by', q.issuedBy ? q.issuedBy.name + ' (' + quoteFrom(q) + ')' : 'Website customer'], ['Scheduler', q.handler ? q.handler.name : ((q.history || []).find(x => x.action === 'issued') || {}).actor || 'Not yet'], ['Printer', pq.length ? pq.map(p => p.vendorName).join(', ') : '—']])),
      this.acC('Customer', this.acDL([['Name', q.customer && q.customer.name], ['Email', q.customer && q.customer.email], ['Phone', q.customer && q.customer.phone]])),
      this.acC('Log', this.acStatusList(log)),
    ];
    return this.acSingle({ home: tabs[0], type: 'Quote request', title: q.id, statusNode: this.pillDot(qrState(q)[0], qrState(q)[1]) }, main, aside);
  };
})();