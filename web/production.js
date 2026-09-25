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
  const Q = { prepress: ['prepress', 'prepress_issue', 'escalated'], scheduler: ['scheduling', 'printing', 'outsourcing'], logistics: ['inbound', 'logistics', 'dispatched'] };
  const STEP = { intake: 1, prepress: 2, prepress_issue: 2, escalated: 2, rejected: 2, scheduling: 3, printing: 4, outsourcing: 4, inbound: 5, logistics: 5, dispatched: 5, at_hub: 5, ready_collect: 5, completed: 5, cancelled: 5 };
  const STEPS = ['Order entered', 'Prepress', 'Scheduler', 'Printing', 'Logistics'];
  const overdue = j => j.deadline && Date.parse(j.deadline) < Date.now() && ['completed', 'cancelled', 'ready_collect'].indexOf(j.status) < 0;
  const tone = j => j.status === 'completed' ? 'ok' : (j.status === 'rejected' || j.status === 'escalated' || overdue(j)) ? 'bad' : 'teal';

  // ---------------------------------------------------------------- page shell (same as the outlet account)
  const SHELL = { production: ['Production Director', 'layers'], prepress: ['Prepress', 'check'], scheduler: ['Scheduler', 'printer'], logistics: ['Logistics', 'truck'] };
  P.pShell = function (route, tabs, content) {
    const v = this.state.acView; const S = SHELL[route];
    const tab = tabs.indexOf(this.state.sTab) >= 0 ? this.state.sTab : tabs[0];
    const shell = { tabs, active: tab, icon: S[1], accent: 'linear-gradient(180deg,#1f3b73,#2e6bd9)', sub: S[0], menu: [['Dashboard', () => this.setState({ acView: null, sTab: tabs[0] })]] };
    if (isDirector(this)) shell.menu = shell.menu.concat([['Prepress', () => this.go('prepress')], ['Scheduler', () => this.go('scheduler')], ['Logistics', () => this.go('logistics')], ['Director dashboard', () => this.go('production')]].filter(m => m[0] !== S[0]));
    let body;
    if (v && v.kind === 'job') { const d = this.acGet('job_' + v.id, '/api/jobs/' + encodeURIComponent(v.id)); const st = d && d.job ? STEP[d.job.status] || 1 : 0; if (st) shell.progress = { text: STEPS[st - 1] + ' - Step ' + st + ' of 5', width: st * 20 }; body = this.pJob(d, tabs); }
    else if (v && v.kind === 'quote') body = this.pQuote(v.id, tabs);
    else body = content(tab);
    return this.acPage(shell, body);
  };
  const openJob = (c, j) => c.acOpen({ kind: 'job', id: j.id });
  // one table for every list: job, product, customer, due, status
  P.pTable = function (key, title, jobs, extra) {
    const list = jobs.slice().sort((a, b) => { const da = a.deadline ? Date.parse(a.deadline) : Infinity, db = b.deadline ? Date.parse(b.deadline) : Infinity; if (da !== db) return da - db; return (Date.parse(a.paymentValidatedAt || 0) || Infinity) - (Date.parse(b.paymentValidatedAt || 0) || Infinity); });
    return this.acList({ key, title, action: extra, cols: ['Job', 'Product', 'Customer', 'Due', 'Status'],
      rows: list.map(j => ({ date: j.createdAt, status: j.statusLabel || j.status, search: [j.id, j.orderId, j.customer, j.product],
        cells: [link(j.id, () => openJob(this, j)), j.product + ' × ' + (j.qty || 0).toLocaleString(), j.customer, h('span', { style: { color: overdue(j) ? '#c71917' : MUT, fontWeight: overdue(j) ? 700 : 400 } }, j.deadline ? dmy(j.deadline) + (overdue(j) ? ' · overdue' : '') : '—'), this.pillDot(j.statusLabel || j.status, tone(j))] })) });
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
        .concat(this.pTable('pd', 'Your queue', q)).concat([this.notifPanel()]);
    });
  };

  // ================================================================== SCHEDULER (queue, in-house printing, outsourcing)
  P.s_scheduler = function () {
    const tabs = ['Dashboard', 'Queue', 'Printing', 'Custom quotes', 'KPI'].concat(isManager(this) ? ['Daily report', 'Machines'] : []);
    return this.pShell('scheduler', tabs, tab => {
      if (tab === 'Queue') return this.pTable('sq', 'Queue — highest priority first', jobsIn(this, ['scheduling']));
      if (tab === 'Printing') return this.pTable('sp', 'Printing', jobsIn(this, ['printing', 'outsourcing']));
      if (tab === 'Custom quotes') return this.pQuotes();
      if (tab === 'KPI') return this.pKpi('scheduler');
      if (tab === 'Daily report') return this.pDaily('scheduler');
      if (tab === 'Machines') return this.pMachines();
      const drafts = this.opsJobs().filter(j => j.status === 'outsourcing' && j.outsource && j.outsource.draft && j.outsource.draft.file && !j.outsource.draft.approvedAt && !j.outsource.draft.rejectedAt);
      return [this.pTiles([
        { label: 'To schedule', value: jobsIn(this, ['scheduling']).length, icon: 'layers', color: 'teal', onClick: () => this.setState({ sTab: 'Queue' }) },
        { label: 'Printing in-house', value: jobsIn(this, ['printing']).length, icon: 'printer', color: 'teal', onClick: () => this.setState({ sTab: 'Printing', sp_s: 'Printing — in-house' }) },
        { label: 'Outsourced', value: jobsIn(this, ['outsourcing']).length, icon: 'truck', color: 'orange', onClick: () => this.setState({ sTab: 'Printing', sp_s: 'Printing — outsourced' }) },
        { label: 'Printer drafts to approve', value: drafts.length, icon: 'file', color: 'red', onClick: () => this.setState({ sTab: 'Printing', sp_s: 'Printing — outsourced' }) }])]
        .concat(this.pTable('sd', 'Queue — highest priority first', jobsIn(this, ['scheduling']))).concat([this.notifPanel()]);
    });
  };

  // ================================================================== LOGISTICS (receive, pack & label, dispatch, confirm)
  P.s_logistics = function () {
    const tabs = ['Dashboard', 'Receiving', 'Packing', 'In transit', 'KPI'].concat(isManager(this) ? ['Daily report'] : []);
    return this.pShell('logistics', tabs, tab => {
      if (tab === 'Receiving') return this.pTable('lr', 'Receiving — outsourced jobs', jobsIn(this, ['inbound']));
      if (tab === 'Packing') return this.pTable('lp', 'Packing & labelling', jobsIn(this, ['logistics']));
      if (tab === 'In transit') return this.pTable('lt', 'In transit', jobsIn(this, ['dispatched']).filter(j => (j.destination || {}).type !== 'hub'));
      if (tab === 'KPI') return this.pKpi('logistics');
      if (tab === 'Daily report') return this.pDaily('logistics');
      return [this.pTiles([
        { label: 'To receive', value: jobsIn(this, ['inbound']).length, icon: 'box', color: 'orange', onClick: () => this.setState({ sTab: 'Receiving' }) },
        { label: 'To pack & label', value: jobsIn(this, ['logistics']).length, icon: 'check', color: 'teal', onClick: () => this.setState({ sTab: 'Packing' }) },
        { label: 'In transit', value: jobsIn(this, ['dispatched']).length, icon: 'truck', color: 'teal', onClick: () => this.setState({ sTab: 'In transit' }) }])]
        .concat(this.pTable('ld', 'Your queue', jobsIn(this, Q.logistics))).concat([this.notifPanel()]);
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
      const attention = all.filter(j => j.status === 'escalated' || (overdue(j) && Q.prepress.concat(Q.scheduler, Q.logistics).indexOf(j.status) >= 0) || (j.delays || []).some(d => Date.parse(d.at) >= new Date().setHours(0, 0, 0, 0)));
      return [this.pTiles([
        { label: 'Prepress', value: jobsIn(this, Q.prepress).length, icon: 'check', color: 'teal', onClick: () => this.setState({ sTab: 'Prepress' }) },
        { label: 'Scheduler', value: jobsIn(this, Q.scheduler).length, icon: 'printer', color: 'teal', onClick: () => this.setState({ sTab: 'Scheduler' }) },
        { label: 'Logistics', value: jobsIn(this, Q.logistics).length, icon: 'truck', color: 'orange', onClick: () => this.setState({ sTab: 'Logistics' }) },
        { label: 'Needs attention', value: attention.length, icon: 'layers', color: 'red' }])]
        .concat(this.pTable('dir_att', 'Needs attention — escalated, overdue or delayed today', attention)).concat([this.notifPanel()]);
    });
  };

  // ================================================================== the job page
  P.pJob = function (d, tabs) {
    if (!d) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    if (d.error) return [h('div', { key: 'e', style: { color: '#c0392b' } }, d.error)];
    const j = d.job, pr = d.printing || {}, id = j.id;
    if (j.status === 'at_hub' || (j.destination || {}).type === 'hub') return this.jobSingle(d, 'production', tabs); // legacy hub parcels
    const acts = {}; (j.actions || []).forEach(a => { if (a.permitted) acts[a.action] = a; });
    const main = [];
    const card = this.pStepCard(j, pr, acts); if (card) main.push(card);
    if (j.outsource && inDept(this, 'scheduler')) main.push(this.pOutsourceCard(j, pr));
    main.push(this.acC('Order details', [h('b', { key: 'p' }, j.product), this.acSpec((pr.job && pr.job.spec) || j.spec),
      this.acDL([['Quantity', (j.qty || 0).toLocaleString()], ['Customer', j.customer], ['Due', j.deadline ? when(j.deadline) + (overdue(j) ? ' — overdue' : '') : '—'], ['Deliver to', j.finalDestination ? (j.finalDestination.name || j.finalDestination.type) + (j.finalDestination.address ? ', ' + j.finalDestination.address : '') : '—'], j.instructions ? ['Instructions', j.instructions] : null, j.machine ? ['Machine', j.machine + (j.slot ? ' · ' + when(j.slot) : '')] : null]),
      (pr.job && pr.job.artworks || []).length ? h('div', { key: 'a', style: { background: ALT, borderRadius: 6, padding: 12, display: 'flex', flexDirection: 'column', gap: 6 } }, h('b', { style: { fontSize: 12.5 } }, 'Artwork'), pr.job.artworks.map((a, i) => a.id ? h('span', { key: i }, link('📄 ' + a.name, () => this.openOrderFile(a.orderId, a))) : h('span', { key: i, style: { color: MUT } }, '📄 ' + a.name))) : null]));
    const issues = (j.delays || []).map(x => ({ title: 'Delay — ' + x.dept, text: x.reason + (x.newEta ? ' · new ETA ' + x.newEta : ''), by: x.by, at: x.at })).concat((j.incidents || []).map(x => ({ title: x.type === 'machine_down' ? 'Machine down' : 'Error — ' + x.dept, text: x.note, by: x.by, at: x.at }))).sort((a, b) => String(b.at).localeCompare(String(a.at)));
    const aside = [
      this.acC('Activities', this.acStatusList(pr.activities || [])),
      deptOf(this) === 'prepress' ? null : this.acC('Documents', h('ol', { style: { margin: 0, paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 8 } },
        (pr.documents || []).map(x => h('li', { key: x.id }, link(x.label, () => this.openJobDoc(id, x.id)))).concat(j.label ? [h('li', { key: 'l' }, link('Parcel label', () => this.printLabel(j.label)))] : []))),
      issues.length || isManager(this) ? this.acC('Delays & errors', [issues.length ? this.acStatusList(issues) : note('None recorded.'),
        isManager(this) ? h('div', { key: 'b' }, Btn('Log an error', () => this.pErrorModal(j))) : null]) : null,
    ];
    const typeTab = tabs.indexOf('Files') >= 0 ? 'Files' : tabs.indexOf('Queue') >= 0 ? 'Queue' : tabs[1];
    return this.acSingle({ home: tabs[0], type: typeTab, title: '#' + id, statusNode: this.pillDot(j.statusLabel || j.status, tone(j)) }, main, aside);
  };
  // the one card for the step the job is at — only the department that owns the step can act
  P.pStepCard = function (j, pr, acts) {
    const id = j.id, st = j.status, role = this.userRole();
    const act = (action, payload, ok) => this.jPost('/api/jobs/' + id + '/transition', { action, payload: payload || {} }, ok, () => this.setState({ acModal: null, acForm: {} }));
    const blocked = a => a && a.blockedBy && a.blockedBy.length ? box(a.blockedBy.join(' '), 'bad') : null;
    const delayBtn = dept => inDept(this, dept) ? Btn('Report a delay', () => this.pDelayModal(j)) : null;
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
            h('div', { key: 'b' }, Btn('Send to logistics', () => act('finish', { qc: true }, 'Sent to logistics.'), 'primary', !this.acF('qc')))] } }), 'primary') : null,
          Btn('Machine down — move to another machine', () => this.pMachineModal(j)),
          delayBtn('scheduler'))]);
    }
    if (st === 'outsourcing') return inDept(this, 'scheduler') ? this.acC('Printing — outsourced', [note('The printer uploads a draft; approve it before they print. They then deliver to ' + ((j.destination || {}).type === 'outlet' ? 'the outlet' : 'production (logistics receives it)') + '.'), h('div', { key: 'b' }, delayBtn('scheduler'))]) : this.acC('Printing', note('Outsourced to a printer.'));
    // Step 5 — logistics (§4.4 receiving, §4.5 packing + delivery)
    const cl = (group, keys) => { const prog = (j.progress && j.progress[group]) || {}; const can = inDept(this, 'logistics');
      return keys.map(k => { const v = prog[k[0]]; return h('label', { key: k[0], style: { display: 'flex', gap: 10, alignItems: 'center', fontSize: 13, cursor: can ? 'pointer' : 'default' } },
        h('input', { type: 'checkbox', checked: !!v, disabled: !can, onChange: e => this.opsStep(id, group, k[0], e.target.checked), style: { width: 17, height: 17 } }), h('span', { style: { flex: 1 } }, k[1]), v ? h('span', { style: { fontSize: 12, color: FAINT } }, v.by) : null); }); };
    if (st === 'inbound') {
      if (!inDept(this, 'logistics')) return this.acC('Logistics', note('On its way from the printer to production.'));
      const RC = [['matched', 'The outsourced order matches the physical item'], ['quantity', 'Quantity is correct'], ['quality', 'Finishing quality is good'], ['unlabelled', 'Printer labels removed for relabelling']];
      return this.acC('Receive outsourced job', [note('When the parcel arrives from ' + ((j.outsource && j.outsource.po) ? 'the printer (' + j.outsource.po + ')' : 'the printer') + ', verify it, then move it to packing.'), cl('receiving', RC), blocked(acts.receive),
        h('div', { key: 'b', style: { display: 'flex', flexDirection: 'column', gap: 8 } }, acts.receive ? Btn('Received — move to packing', () => act('receive', {}, 'Received — ready to pack.'), 'primary', !acts.receive.enabled) : null, delayBtn('logistics'))]);
    }
    if (st === 'logistics') {
      if (!inDept(this, 'logistics')) return this.acC('Logistics', note('Being packed for delivery.'));
      const PC = [['verified', 'Verified — order vs item, quantity and finishing quality'], ['packed', 'Packed — right materials, protected from damage, items grouped'], ['labelled', 'Labelled — label printed from this page (customer, order ID, destination, parcel count)']];
      return [this.acC('Pack & label', [note('Pack the order, print the label and stick it on every parcel.'), cl('logistics', PC), h('div', { key: 'b' }, Btn('Print label', () => this.printLabel(j.label)))]),
        this.pDispatchCard(j, pr, acts)];
    }
    if (st === 'dispatched') {
      const toCustomer = (j.destination || {}).type === 'customer';
      return [this.acC('In transit', [this.acDL([['Courier', j.courier], ['Tracking', j.tracking], ['To', (j.destination || {}).name]]),
        toCustomer ? note('Once the courier confirms delivery and the customer has been told, confirm it here.') : note('The outlet confirms when it receives the parcel.'),
        h('div', { key: 'b', style: { display: 'flex', flexDirection: 'column', gap: 8 } }, toCustomer && acts.deliver ? Btn('Delivery confirmed', () => act('deliver', {}, 'Delivery confirmed.'), 'primary') : null, delayBtn('logistics'))]),
        inDept(this, 'logistics') && pr.dispatchDelivery ? this.pDispatchCard(j, pr, acts) : null];
    }
    if (st === 'ready_collect') return this.acC('At the outlet', note('Ready for the customer to collect.'));
    if (st === 'completed') return this.acC('Completed', box('Delivered / collected.', 'ok'));
    return null;
  };
  // Delivery SOP (§4.5): courier from HQ's list, dispatch (time recorded), then confirmation
  P.pDispatchCard = function (j, pr, acts) {
    const cfg = this.state.opsConfig || { couriers: [] }; const dd = pr.dispatchDelivery || {}; const packing = j.status === 'logistics';
    const F = (k, def) => this.acF(k) !== '' ? this.acF(k) : def;
    const tracking = F('dTracking', (dd.tracking || []).join('\n')), courier = F('dCourier', dd.company || cfg.couriers[0] || '');
    const a = acts.dispatch;
    return this.acC('Delivery', [
      this.acDL([['Deliver to', ((j.destination || {}).name || '—') + ((j.destination || {}).address ? ', ' + j.destination.address : '')], ['Parcels', j.parcels || 1]]),
      FG('Courier', h('select', { value: courier, onChange: e => this.acSetF('dCourier', e.target.value), style: inp }, cfg.couriers.map(c => h('option', { key: c }, c))), 1, 'Only the delivery companies selected by HQ.'),
      FG('Tracking number', ta(tracking, v => this.acSetF('dTracking', v), 3), 1, 'One per line if there is more than one parcel.'),
      FG('Delivery order', h('div', { style: { display: 'flex', flexDirection: 'column', gap: 6 } }, dd.document ? link('📄 ' + dd.document.name, () => this.jDownload('/api/jobs/' + j.id + '/files/' + dd.document.id, dd.document.name)) : null, this.jPickFile('dDoc'))),
      packing && a && a.blockedBy && a.blockedBy.length ? box(a.blockedBy.join(' '), 'bad') : null,
      h('div', { key: 'b' }, Btn(packing ? 'Dispatch' : 'Save changes', () => this.jPost('/api/jobs/' + j.id + '/delivery', { tracking, company: courier, documentData: this.acF('dDocData') || undefined, documentName: this.acF('dDocName') || undefined }, packing ? 'Dispatched.' : 'Delivery details saved.', () => this.setState({ acForm: {} })), 'primary', !tracking.trim() || (packing && (!a || !a.enabled))))]);
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
      pr.draft && pr.draft.file ? h('div', { key: 'dr', style: { display: 'flex', flexDirection: 'column', gap: 8 } },
        pr.draft.approvedAt ? box('Draft approved by ' + pr.draft.approvedBy + '. The printer may print.', 'ok') : pr.draft.rejectedAt ? box('Draft rejected: ' + pr.draft.rejectReason + '. Waiting for a new draft.', 'bad') : box('The printer uploaded a draft. Check it and approve it before they print.'),
        link('📄 ' + pr.draft.file.name, () => this.jDownload('/api/jobs/' + id + '/files/' + pr.draft.file.id, pr.draft.file.name)),
        pr.canApproveDraft ? Row(Btn('Approve draft', () => this.jPost('/api/jobs/' + id + '/draft', { decision: 'approve' }, 'Draft approved.'), 'primary'), Btn('Reject draft', () => this.pModal('Reject draft', [['reason', 'What should the printer change?', '']], v => this.jPost('/api/jobs/' + id + '/draft', { decision: 'reject', reason: v.reason }, 'Draft rejected.', () => this.setState({ acModal: null }))))) : null) : null,
      o.awardedTo && !o.draft && j.status === 'outsourcing' ? note('Waiting for the printer to upload a draft.') : null,
      (isDirector(this) || /scheduler_manager/.test(this.userRole())) && pr.awarded && pr.status && ['shipped-to-hub', 'shipped'].indexOf(pr.status.id) >= 0 ? Btn('Printer paid', () => this.pModal('Printer paid', [['reference', 'Payment reference', 'e.g. IBG-7781']], v => this.jPost('/api/jobs/' + id + '/vendor-paid', v, 'Printer marked paid.', () => this.setState({ acModal: null })))) : null,
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
  P.pDelayModal = function (j) {
    this.setState({ acForm: {}, acModal: { title: 'Report a delay', body: () => [
      note('Your manager and the affected outlet are told straight away.'),
      FG('Cause of the delay', ta(this.acF('reason'), v => this.acSetF('reason', v), 3), 1),
      FG('New expected date', h('input', { type: 'date', value: this.acF('eta'), onChange: e => this.acSetF('eta', e.target.value), style: inp })),
      h('div', { key: 'b' }, Btn('Report delay', () => this.jPost('/api/jobs/' + j.id + '/delay', { reason: this.acF('reason'), newEta: this.acF('eta') || null }, 'Delay reported.', () => this.setState({ acModal: null, acForm: {} })), 'primary', !this.acF('reason')))] } });
  };
  P.pMachineModal = function (j) {
    const cfg = this.state.opsConfig || { machines: [] }; const others = cfg.machines.filter(m => m !== j.machine);
    this.setState({ acForm: {}, acModal: { title: 'Machine down', body: () => [
      note('Every job on ' + j.machine + ' moves to the machine you pick. Logistics and the affected outlets are told, and the incident is logged.'),
      FG('What is wrong with ' + j.machine + '?', ta(this.acF('reason'), v => this.acSetF('reason', v), 3), 1),
      FG('Move to', h('select', { value: this.acF('machine') || others[0] || '', onChange: e => this.acSetF('machine', e.target.value), style: inp }, others.map(m => h('option', { key: m }, m))), 1),
      h('div', { key: 'b' }, Btn('Move jobs', () => this.jPost('/api/jobs/' + j.id + '/machine-down', { reason: this.acF('reason'), machine: this.acF('machine') || others[0] }, 'Jobs moved.', () => this.setState({ acModal: null, acForm: {} })), 'primary', !this.acF('reason') || !others.length))] } });
  };
  P.pErrorModal = function (j) {
    const T = [['file_issue', 'File issue — Prepress'], ['late_job', 'Late job — Scheduler'], ['wrong_spec', 'Wrong spec — Scheduler'], ['quality', 'Quality — Scheduler'], ['wrong_item', 'Wrong item sent — Logistics'], ['damage', 'Damaged — Logistics']];
    this.setState({ acForm: {}, acModal: { title: 'Log an error', body: () => [
      FG('Error', h('select', { value: this.acF('type') || T[0][0], onChange: e => this.acSetF('type', e.target.value), style: inp }, T.map(t => h('option', { key: t[0], value: t[0] }, t[1]))), 1, 'The department responsible is set by the guidebook.'),
      FG('What happened', ta(this.acF('note'), v => this.acSetF('note', v), 3)),
      h('div', { key: 'b' }, Btn('Log error', () => this.jPost('/api/jobs/' + j.id + '/incident', { type: this.acF('type') || T[0][0], note: this.acF('note') }, 'Error logged.', () => this.setState({ acModal: null, acForm: {} })), 'primary'))] } });
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
        h('b', { key: 'd' }, 'Jobs delayed'), list(f.delayed, x => x.id + ' · ' + x.product + ' — ' + x.reason, 'No delays.'),
        h('b', { key: 'e' }, 'Errors'), list(f.errors, x => x.jobId + ' — ' + x.note, 'No errors.'),
        field('delays', 'Notes on delays'), field('errors', 'Notes on errors'), field('backlog', 'Notes for tomorrow'),
        h('div', { key: 'b' }, Btn('Submit to Production Director', () => this.jPost('/api/ops/daily-report', { dept, kind, delays: this.acF('delays'), errors: this.acF('errors'), backlog: this.acF('backlog') }, 'End-of-day report submitted.', () => { this.acDrop('drl_'); this.setState({ acForm: {} }); }), 'primary'))]),
      h('div', { key: 'p' }, this.dataCard(['Date', 'Report', 'By', 'Pending', 'Completed', 'Delayed', 'Errors'], past.map(r => [r.date, r.kind === 'morning' ? 'Morning' : 'End of day', r.by, String(r.figures.pending), r.kind === 'evening' ? String(r.figures.completed) : '—', r.kind === 'evening' ? String(r.figures.delayed.length) : '—', r.kind === 'evening' ? String(r.figures.errors.length) : '—']), { minWidth: 640, empty: 'No reports submitted yet.' }))];
  };
  P.pReports = function () {
    const rs = (this.acGet('drl_all', '/api/ops/reports') || {}).reports || [];
    const today = new Date().toISOString().slice(0, 10);
    const has = (d, k) => rs.some(r => r.dept === d && r.kind === k && r.date === today);
    return [h('h1', { key: 't', style: { fontSize: 34, fontWeight: 600, margin: '6px 0 0' } }, 'Daily reports'),
      this.dataCard(['Department', 'Morning report', 'End-of-day report'], ['prepress', 'scheduler', 'logistics'].map(d => [d[0].toUpperCase() + d.slice(1), this.pillDot(has(d, 'morning') ? 'Submitted' : 'Not yet', has(d, 'morning') ? 'ok' : 'warn'), this.pillDot(has(d, 'evening') ? 'Submitted' : 'Not yet', has(d, 'evening') ? 'ok' : 'warn')]), { minWidth: 480 }),
      h('div', { key: 'l', style: { display: 'flex', flexDirection: 'column', gap: 12 } }, rs.map(r => this.acC(r.date + ' · ' + r.dept[0].toUpperCase() + r.dept.slice(1) + ' · ' + (r.kind === 'morning' ? 'Morning' : 'End of day') + ' · ' + r.by, [
        this.acDL([['Pending', String(r.figures.pending)], ['Urgent', r.figures.urgent.map(x => x.id).join(', ') || '—'], r.kind === 'evening' ? ['Completed', String(r.figures.completed)] : null, r.kind === 'evening' ? ['Delayed', r.figures.delayed.map(x => x.id + ' (' + x.reason + ')').join('; ') || '—'] : null, r.kind === 'evening' ? ['Errors', r.figures.errors.map(x => x.jobId).join(', ') || '—'] : null,
          r.notes.status ? ['Machine / manpower', r.notes.status] : null, r.notes.delays ? ['Notes on delays', r.notes.delays] : null, r.notes.errors ? ['Notes on errors', r.notes.errors] : null, r.notes.backlog ? ['Notes for tomorrow', r.notes.backlog] : null])])))];
  };

  // ---------------------------------------------------------------- settings
  P.pMachines = function () {
    const cfg = this.state.opsConfig; if (!cfg) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    const jobs = this.opsJobs();
    const text = this.acF('machines') !== '' ? this.acF('machines') : cfg.machines.join('\n');
    return [h('h1', { key: 't', style: { fontSize: 34, fontWeight: 600, margin: '6px 0 0' } }, 'Machines'),
      this.dataCard(['Machine', { label: 'Printing now', right: true }], cfg.machines.map(m => [m, String(jobs.filter(j => j.status === 'printing' && j.machine === m).length)]), { minWidth: 420 }),
      this.acC('Edit machines', [FG('One machine per line', ta(text, v => this.acSetF('machines', v), 8)),
        h('div', { key: 'b' }, Btn('Save', () => this.opsFetch('/api/ops/config', { machines: text.split('\n').map(s => s.trim()).filter(Boolean) }).then(d => { if (this.acDone(d, 'Machines saved.')) this.setState({ opsConfig: d.config, acForm: {} }); }), 'primary'))])];
  };
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

  // ---------------------------------------------------------------- custom quotes (HQ prices the outlets' quote requests)
  P.pQuotes = function () {
    const qs = (this.acGet('p_quotes', '/api/quotes') || {}).quotes;
    if (!qs) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    const label = q => ({ requested: 'To price', amendment: 'To price', issued: 'Quoted', reviewed: 'Quoted', accepted: 'Accepted', rejected: 'Rejected', declined: 'Rejected' })[q.status] || q.status;
    return this.acList({ key: 'cq', title: 'Custom quotes', cols: ['Quote', 'Product', 'Customer', 'Outlet', { label: 'Price', right: true }, 'Status'],
      rows: qs.slice().sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt))).map(q => ({ date: q.createdAt, status: label(q), search: [q.id, q.customer && q.customer.name, q.requirement && q.requirement.product],
        cells: [link(q.id, () => this.acOpen({ kind: 'quote', id: q.id })), (q.requirement && q.requirement.product) || '—', (q.customer && q.customer.name) || '—', q.outlet || 'Online', q.price != null ? this.rm(q.price) : '—', this.pillDot(label(q), label(q) === 'To price' ? 'warn' : label(q) === 'Accepted' ? 'ok' : 'teal')] })) });
  };
  P.pQuote = function (qid, tabs) {
    const qs = (this.acGet('p_quotes', '/api/quotes') || {}).quotes; if (!qs) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    const q = qs.find(x => x.id === qid); if (!q) return [h('div', { key: 'e' }, 'Quote not found.')];
    const r = q.requirement || {}; const open = ['requested', 'amendment', 'issued', 'reviewed'].indexOf(q.status) >= 0;
    const pq = (q.printerQuotes || {}).printers || [];
    const main = [
      this.acC('Specifications', [h('b', { key: 'p' }, r.product || 'Custom job'), h('div', { key: 's', style: { whiteSpace: 'pre-wrap', lineHeight: 1.7 } }, r.quoteData || [r.size, r.material, r.finishing, r.qty && 'Qty ' + r.qty, r.remarks].filter(Boolean).join('\n'))]),
      this.acC('Printer quotes', [pq.length ? this.dataCard(['Printer', 'Weight (kg)', { label: 'Amount', right: true }, 'Document'], pq.map(p => [p.vendorName, p.weight || '—', p.amount != null ? this.rm(p.amount) : 'waiting', p.document ? link(p.document.name, () => this.jDownload('/api/quotes/' + q.id + '/printer-quotes/' + p.vendorId + '/document', p.document.name)) : '—']), { minWidth: 480 }) : note('No printer has been asked yet.'),
        open ? h('div', { key: 'rq', style: { display: 'flex', flexDirection: 'column', gap: 8 } }, h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(200px,1fr))', gap: 8 } }, ((this.acGet('vendors', '/api/vendors') || {}).vendors || []).filter(v => !pq.some(p => p.vendorId === v.id)).map(v => { const picked = this.acF('qv') || []; return h('label', { key: v.id, style: { display: 'flex', gap: 8, fontSize: 13, cursor: 'pointer' } }, h('input', { type: 'checkbox', checked: picked.indexOf(v.id) >= 0, onChange: () => this.acSetF('qv', picked.indexOf(v.id) >= 0 ? picked.filter(x => x !== v.id) : picked.concat([v.id])) }), v.name); })),
          h('div', null, Btn('Ask printers to quote', () => this.aFetchJ('/api/quotes/' + q.id + '/printer-quotes', { vendorIds: this.acF('qv') || [] }).then(d => { if (this.acDone(d, 'Printers asked to quote.')) { this.acDrop('p_quotes'); this.setState({ acForm: {} }); } }), null, !(this.acF('qv') || []).length))) : null]),
      open ? this.acC(q.price != null ? 'Quote issued — change price' : 'Price this quote', [
        h('div', { key: 'f', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 12 } },
          FG('Price (RM)', h('input', { type: 'number', value: this.acF('price') !== '' ? this.acF('price') : (q.price != null ? q.price : ''), onChange: e => this.acSetF('price', e.target.value), style: inp }), 1),
          FG('Lead time (days)', h('input', { type: 'number', value: this.acF('lead') !== '' ? this.acF('lead') : (q.leadDays || ''), onChange: e => this.acSetF('lead', e.target.value), style: inp }))),
        h('div', { key: 'b' }, Btn('Issue quote to customer', () => this.aFetchJ('/api/quotes/' + q.id + '/price', { price: this.acF('price') || q.price, leadDays: this.acF('lead') || q.leadDays }).then(d => { if (this.acDone(d, 'Quote issued to the customer.')) { this.acDrop('p_quotes'); this.setState({ acForm: {} }); } }), 'primary', !(this.acF('price') || q.price)))]) : null,
    ];
    const aside = [this.acC('Customer', this.acDL([['Name', q.customer && q.customer.name], ['Email', q.customer && q.customer.email], ['Phone', q.customer && q.customer.phone], ['Outlet', q.outlet || 'Online']])),
      this.acC('History', this.acStatusList((q.history || []).slice().reverse().map(e => ({ title: String(e.action || '').replace(/^./, c => c.toUpperCase()), text: e.note || (e.price ? 'RM ' + e.price : ''), by: e.actor, at: e.ts }))))];
    return this.acSingle({ home: tabs[0], type: 'Custom quotes', title: q.id, status: q.status }, main, aside);
  };
})();
