/*
 * Production, hub and printer accounts on the original outlet account pattern (account.js kit),
 * running the original printoka-3rd-party-supplier printing-job flow:
 *
 *   printer: Printing Jobs · Custom Quotes — single job cards by status
 *            (Request Quote → Upload Draft + Quote → Job Status "Shipped to hub" + Quote), Job details;
 *            sidebar Activities · Job documents (Purchase Order, Hub Label) · Hub detail
 *   hub:     receive → progress form → Delivery Details (tracking numbers, delivery company,
 *            delivery order) → Shipped; sidebar Activities · Job documents (Shipping Label) · Customer detail
 *   production (prepress, scheduler, floor, logistics, managers): the same single job page with the
 *            department's next actions, draft approval, printer quotes, printer paid, documents
 *
 * Every screen keeps its Qn 732/750/752 tabs; jobs open as full pages instead of pop-ups.
 */
(function () {
  const C = window.PKComponent; if (!C) return;
  const P = C.prototype;

  const inp = { font: '400 13.5px Montserrat,sans-serif', padding: '9px 12px', border: '1px solid ' + HAIR, borderRadius: 8, width: '100%', background: '#fff' };
  const Btn = (label, onClick, kind, disabled, title) => h('button', { type: 'button', title: title || undefined, disabled: !!disabled, onClick: disabled ? undefined : onClick,
    style: { font: '600 13px Montserrat,sans-serif', padding: kind === 'block' ? '14px 16px' : '9px 16px', borderRadius: 8, width: kind === 'block' ? '100%' : undefined, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? .5 : 1,
      border: '1px solid ' + (kind === 'primary' ? TEAL : '#d9d9d9'), background: kind === 'primary' ? TEAL : '#fff', color: kind === 'primary' ? '#fff' : INK } }, label);
  const FG = (label, control, req, hint) => h('label', { style: { display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13, fontWeight: 600, color: INK } }, h('span', null, label, req ? h('span', { style: { color: TEAL } }, ' *') : null), hint ? h('span', { style: { fontSize: 12.5, fontWeight: 400, color: MUT } }, hint) : null, control);
  const when = ts => { if (!ts) return '—'; const d = new Date(ts); return d.toLocaleDateString('en-GB').replace(/\//g, '-') + ' ' + d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }).toLowerCase(); };
  const dmy = ts => { if (!ts) return '—'; const d = new Date(ts); return String(d.getDate()).padStart(2, '0') + '/' + String(d.getMonth() + 1).padStart(2, '0') + '/' + d.getFullYear(); };
  const alertBox = (text, tone) => h('div', { style: { display: 'flex', gap: 10, alignItems: 'flex-start', fontSize: 13, lineHeight: 1.55, borderRadius: 8, padding: '11px 13px', background: tone === 'ok' ? '#e6f4ea' : tone === 'bad' ? '#fdecec' : '#fff8e6', color: tone === 'ok' ? '#1f5e2a' : tone === 'bad' ? '#8c1c13' : '#8a4b00', border: '1px solid ' + (tone === 'ok' ? '#cfe8d4' : tone === 'bad' ? '#f5c8c7' : '#f3e2b8') } }, h('span', { style: { fontWeight: 700 } }, tone === 'ok' ? '✓' : '!'), h('span', null, text));
  const link = (text, onClick) => h('span', { onClick, style: { color: TEAL, fontWeight: 700, cursor: 'pointer' } }, text);
  const muted = t => h('p', { style: { margin: 0, fontSize: 13, color: MUT, lineHeight: 1.6 } }, t);
  // original +job_status pill: the status colour as a dot
  const jobPill = s => s ? h('span', { style: { display: 'inline-flex', alignItems: 'center', gap: 7, background: '#f6f7f8', borderRadius: 999, padding: '5px 12px', fontSize: 12.5, fontWeight: 600, color: INK, whiteSpace: 'nowrap' } }, h('span', { style: { height: 8, width: 8, borderRadius: '50%', background: s.color || '#8a9199' } }), s.label) : null;

  // ---------------------------------------------------------------- shared plumbing
  P.jDownload = function (url, name) {
    fetch(url, { headers: this.authHeaders() }).then(r => { if (!r.ok) throw new Error('not allowed'); return r.blob(); })
      .then(b => this.saveBlob(b, name)).catch(() => this.setState({ acMsg: { bad: true, text: 'Could not open ' + name + '.' } }));
  };
  P.jPost = function (url, body, okText, then) {
    return this.aFetchJ(url, body).then(d => {
      if (!this.acDone(d, okText || d.message)) return false;
      this.acDrop('job_'); this.acDrop('v'); if (this.state.ops) this.opsLoad();
      if (then) then(d); return true;
    });
  };
  P.jPickFile = function (key) {
    return h('input', { type: 'file', onChange: e => this.acReadFile(e.target.files[0]).then(f => { if (f) { this.acSetF(key + 'Data', f.data); this.acSetF(key + 'Name', f.name); } }), style: inp });
  };
  const origDone = P.opsDone;
  P.opsDone = function (d, okText) { const r = origDone.call(this, d, okText); if (r) this.acDrop('job_'); return r; };
  // jobs open as full pages (the original single-page pattern) instead of the details pop-up
  // the hub forwards and logistics dispatches through the Delivery Details card on the job page (original flow)
  const origAction = P.opsAction;
  P.opsAction = function (j, a) { if (a.action === 'forward' || a.action === 'dispatch') return this.acOpen({ kind: 'job', id: j.id }); return origAction.call(this, j, a); };
  const origOpen = P.opsOpen;
  P.opsOpen = function (kind, j, extra) {
    if (j && j.id && (kind === 'job' || (kind === 'ship' && extra && (extra.action === 'dispatch' || extra.action === 'forward')))) return this.acOpen({ kind: 'job', id: j.id });
    return origOpen.call(this, kind, j, extra);
  };

  // ---------------------------------------------------------------- production / hub shell
  const SHELL = { production: ['linear-gradient(180deg,#1f3b73,#2e6bd9)', 'printer'], scheduler: ['linear-gradient(180deg,#1f3b73,#2e6bd9)', 'layers'], prepress: ['linear-gradient(180deg,#1f3b73,#2e6bd9)', 'check'], logistics: ['linear-gradient(180deg,#1f3b73,#2e6bd9)', 'truck'], hub: ['linear-gradient(180deg,#F4732F,#FFB600)', 'truck'] };
  P.oPage = function (route, tabs, tab, identity, content) {
    const v = this.state.acView; const S = SHELL[route] || SHELL.production;
    const shell = { tabs, active: tab, accent: S[0], icon: S[1], sub: identity && identity.title, menu: [['Dashboard', () => this.setState({ acView: null, sTab: tabs[0] })]] };
    let body = content;
    if (v && v.kind === 'job') { const d = this.acGet('job_' + v.id, '/api/jobs/' + encodeURIComponent(v.id)); shell.progress = this.jProgress(d); body = this.jobSingle(d, route, tabs); }
    return this.acPage(shell, [this.oDeptSwitch(route)].concat(body, [this.opsModalView(), this.opsReviewDialog(), this.oToast()]));
  };
  // the job's place in the whole pipeline — header progress bar on the single page
  const STAGE = { intake: 1, prepress: 1, prepress_issue: 1, escalated: 1, rejected: 1, scheduling: 2, printing: 3, outsourcing: 3, logistics: 4, dispatched: 5, at_hub: 5, ready_collect: 6, completed: 7, cancelled: 7 };
  P.jProgress = function (d) {
    if (!d || !d.job) return null; const j = d.job; const n = STAGE[j.status] || 1;
    return { text: (j.statusLabel || j.status) + ' - Step ' + n + ' of 7', width: Math.round(n / 7 * 100) };
  };
  // order listing (every department): the original list page — search · date · status · table → single page
  P.oOrders = function (jobs, key) {
    return this.acList({ key: 'ol_' + key, title: 'Orders', cols: ['Job number', 'Product', 'Customer', { label: 'Total Amount', right: true }, 'Status', 'Order date'],
      rows: jobs.map(j => ({ date: j.createdAt, status: j.statusLabel || j.status, search: [j.id, j.orderId, j.customer, j.product],
        cells: [link(j.id, () => this.acOpen({ kind: 'job', id: j.id })), j.product + ' × ' + (j.qty || 0).toLocaleString(), j.customer, this.rm(j.price || 0), this.pillDot(j.statusLabel || j.status, j.status === 'completed' ? 'ok' : j.status === 'rejected' ? 'bad' : 'teal'), dmy(j.createdAt)] })) }).slice(1);
  };

  // ---------------------------------------------------------------- the single job page (staff + hub)
  const PROGRESS = {
    printing: ['inhouse', [['setup', 'Set-up / plate / RIP'], ['printing', 'Printing'], ['finishing', 'Finishing (cut, laminate, bind…)'], ['qc', 'Quality check']], ['production_staff', 'production_manager']],
    at_hub: ['hub', [['checked', 'Parcel checked against the order'], ['qc', 'Quality check passed'], ['relabelled', 'Relabelled / repacked']], ['hub_staff', 'hub_manager', 'hub']],
    logistics: ['logistics', [['picked', 'Picked from production'], ['packed', 'Packed'], ['labelled', 'Shipping label attached']], ['logistics', 'logistics_manager']],
  };
  P.jobSingle = function (d, route, tabs) {
    if (!d) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    if (d.error) return [h('div', { key: 'e', style: { color: '#c0392b' } }, d.error)];
    const j = d.job, pr = d.printing || {}, o = d.order, id = j.id;
    const type = this.userType(), role = this.userRole(), isHub = type === 'hub', admin = type === 'admin';
    const approver = admin || /^scheduler|production_manager/.test(role);
    const manager = admin || /scheduler_manager|production_manager/.test(role);
    // at the hub, "forward" is the Delivery Details card below (original flow), not a separate button
    // (actions for a different destination — e.g. "Receive at hub" on a parcel bound for an outlet — are not shown)
    const wrongDest = a => !a.enabled && (a.blockedBy || []).some(b => /not addressed|not the customer/.test(b));
    const isLog = /^logistics/.test(role);
    const viaCard = a => (a.action === 'forward' && (isHub || admin)) || (a.action === 'dispatch' && (isLog || admin));
    const seen = {}; const acts = (j.actions || []).filter(a => a.permitted && !wrongDest(a) && !viaCard(a)).filter(a => { const l = this.oActLabel(a.action); if (seen[l]) return false; seen[l] = 1; return true; });
    const main = [];
    // Status — the department's next actions (open the existing pop-up forms)
    if (acts.length || (j.outsource && j.status === 'scheduling' && approver)) main.push(this.acC('Status', [
      acts.map(a => h('div', { key: a.action, style: { display: 'flex', flexDirection: 'column', gap: 6 } }, Btn(this.oActLabel(a.action), () => this.opsAction(j, a), 'block', !a.enabled), !a.enabled && a.blockedBy && a.blockedBy.length ? h('span', { style: { fontSize: 12, color: '#8c1c13' } }, a.blockedBy.join(' ')) : null)),
      j.outsource && !j.outsource.awardedTo && j.status === 'scheduling' && approver ? Btn('Compare quotes & award', () => origOpen.call(this, 'outsource', j), 'block') : null]));
    // interactive progress form (floor · hub · logistics)
    const G = PROGRESS[j.status];
    if (G) {
      const prog = (j.progress && j.progress[G[0]]) || {}; const canTick = admin || G[2].indexOf(role) >= 0;
      main.push(this.acC(G[0] === 'inhouse' ? 'In-house progress form' : G[0] === 'hub' ? 'Hub progress form' : 'Logistics status update', [
        canTick ? null : muted('View only — updated by the ' + ({ inhouse: 'production floor', hub: 'hub team', logistics: 'logistics team' })[G[0]] + '.'),
        G[1].map(s => { const v = prog[s[0]]; return h('label', { key: s[0], style: { display: 'flex', gap: 12, alignItems: 'center', border: '1px solid ' + (v ? '#cfe8d4' : HAIR), background: v ? '#f3faf5' : '#fff', borderRadius: 10, padding: '11px 13px', cursor: canTick ? 'pointer' : 'default' } },
          h('input', { type: 'checkbox', checked: !!v, disabled: !canTick, onChange: e => this.opsStep(id, G[0], s[0], e.target.checked), style: { width: 18, height: 18 } }),
          h('span', { style: { flex: 1, fontWeight: 600 } }, s[1]), v ? h('span', { style: { fontSize: 12, color: FAINT } }, v.by + ' · ' + when(v.at)) : null); })]));
    }
    // printer draft (original: admin approves the draft before printing starts)
    if (!isHub && pr.draft && pr.draft.file) main.push(this.acC('Printer draft', [
      pr.draft.approvedAt ? alertBox('Draft approved by ' + pr.draft.approvedBy + ' on ' + when(pr.draft.approvedAt) + '. The printer may proceed with printing.', 'ok')
        : pr.draft.rejectedAt ? alertBox('Draft rejected: ' + pr.draft.rejectReason + ' — waiting for the printer to upload a new draft.', 'bad')
        : alertBox('Draft Pending Approval — uploaded ' + when(pr.draft.at) + ' by ' + pr.draft.by + '.'),
      h('div', { key: 'f', style: { background: ALT, borderRadius: 6, padding: 12 } }, link('📄 ' + pr.draft.file.name, () => this.jDownload('/api/jobs/' + id + '/files/' + pr.draft.file.id, pr.draft.file.name))),
      pr.canApproveDraft && approver ? h('div', { key: 'b', style: { display: 'flex', gap: 8 } },
        Btn('Approve draft', () => this.jPost('/api/jobs/' + id + '/draft', { decision: 'approve' }, 'Draft approved — the printer has been told to start printing.'), 'primary'),
        Btn('Reject', () => this.setState({ acForm: {}, acModal: { title: 'Reject draft', body: () => [FG('What should the printer change?', h('textarea', { rows: 6, value: this.acF('reason'), onChange: e => this.acSetF('reason', e.target.value), style: Object.assign({}, inp, { resize: 'vertical' }) }), 1),
          h('div', { key: 'b' }, Btn('Submit', () => this.jPost('/api/jobs/' + id + '/draft', { decision: 'reject', reason: this.acF('reason') }, 'Draft rejected — the printer will upload a new one.', () => this.setState({ acModal: null })), 'primary', !this.acF('reason')))] } }))) : null]));
    // printer quotes for an outsourced job
    if (!isHub && j.outsource && pr.quotes) main.push(this.acC('Printer quotes', [
      h('div', { key: 't', style: { overflowX: 'auto' } }, h('table', { style: { width: '100%', borderCollapse: 'collapse', fontSize: 13 } },
        h('thead', null, h('tr', null, ['Printer', 'Quote amount (RM)', 'Lead time', 'Quote document', ''].map(c => h('th', { key: c, style: { textAlign: 'left', padding: '8px 10px', borderBottom: '1px solid ' + HAIR, fontSize: 12 } }, c)))),
        h('tbody', null, pr.quotes.map(q => h('tr', { key: q.vendorId }, h('td', { style: { padding: '9px 10px', borderTop: '1px solid ' + LINE } }, q.vendorName),
          h('td', { style: { padding: '9px 10px', borderTop: '1px solid ' + LINE } }, q.amount != null ? Number(q.amount).toFixed(2) : h('span', { style: { color: FAINT } }, q.submittedAt ? '—' : 'no quote yet')),
          h('td', { style: { padding: '9px 10px', borderTop: '1px solid ' + LINE } }, q.leadDays ? q.leadDays + ' days' : '—'),
          h('td', { style: { padding: '9px 10px', borderTop: '1px solid ' + LINE } }, q.document ? link(q.document.name, () => this.jDownload('/api/jobs/' + id + '/files/' + q.document.id, q.document.name)) : '—'),
          h('td', { style: { padding: '9px 10px', borderTop: '1px solid ' + LINE } }, q.awarded ? this.pillDot('Assigned', 'ok') : '')))))),
      pr.po ? muted('Purchase order ' + pr.po + (pr.poNumber ? ' (No. ' + pr.poNumber + ')' : '')) : null]));
    // hub: Delivery Details (original card) — tracking numbers, delivery company, delivery order → Shipped
    // Delivery Details (original hub card; logistics dispatches through the same card)
    const dStage = deliveryStage(j, pr);
    if (dStage === 'hub' && (isHub || admin)) main.push(this.deliveryCard(j, pr, 'hub'));
    if (dStage === 'logistics' && (isLog || admin)) main.push(this.deliveryCard(j, pr, 'logistics'));
    // HQ pays the printer (original status "Paid")
    if (manager && pr.awarded && pr.status && ['shipped-to-hub', 'shipped'].indexOf(pr.status.id) >= 0) main.push(this.acC('Printer payment', [
      muted('Once the printer has been paid for ' + (pr.po || 'this job') + ', record it here — the printing job moves to “Paid”.'),
      FG('Payment reference', h('input', { value: this.acF('payref'), onChange: e => this.acSetF('payref', e.target.value), style: inp })),
      h('div', { key: 'b' }, Btn('Mark printer paid', () => this.jPost('/api/jobs/' + id + '/vendor-paid', { reference: this.acF('payref') }, 'Printer marked paid.'), 'primary'))]));
    // job details (original card)
    main.push(this.acC('Job details', [
      h('b', { key: 'p' }, j.product), this.acSpec((pr.job && pr.job.spec) || j.spec),
      this.acDL([['Quantity', (j.qty || 0).toLocaleString()], ['Deadline', j.deadline ? when(j.deadline) : '—'], ['Machine', j.machine], ['Deliver to', j.destination ? (j.destination.name || j.destination.type) : '—'], ['Final destination', j.finalDestination ? (j.finalDestination.name || j.finalDestination.type) : '—'], j.instructions ? ['Instructions', j.instructions] : null]),
      (pr.job && pr.job.artworks && pr.job.artworks.length) ? h('div', { key: 'a', style: { background: ALT, borderRadius: 6, padding: 12, display: 'flex', flexDirection: 'column', gap: 8 } }, h('b', { style: { fontSize: 12.5 } }, 'Artworks'),
        pr.job.artworks.map((a, i) => a.id && !isHub ? h('span', { key: i }, link('📄 ' + a.name, () => this.openOrderFile(a.orderId, a))) : h('span', { key: i, style: { color: MUT } }, '📄 ' + a.name))) : null]));
    if ((j.shipments || []).length) main.push(this.acC('Delivery', this.acDL(j.shipments.map(s => ['Leg ' + s.leg, (s.from || '') + ' → ' + ((s.to && (s.to.name || s.to.type)) || '') + ' · ' + (s.courier || 'courier') + (s.tracking ? ' · ' + s.tracking : '') + ' · ' + when(s.at) + (s.receivedAt ? ' · received' : ' · in transit')]))));
    // aside
    const aside = [
      this.acC('Activities', this.acStatusList(pr.activities || [])),
      this.acC('Job documents', h('ol', { style: { margin: 0, paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 8 } },
        (pr.documents || []).map(x => h('li', { key: x.id }, link(x.label, () => this.openJobDoc(id, x.id)))).concat(j.label ? [h('li', { key: 'lbl' }, link('Parcel label (' + (j.label.toName || '') + ')', () => this.printLabel(j.label)))] : []))),
      pr.customer ? this.acC('Customer detail', [h('b', { key: 'n' }, pr.customer.name), pr.customer.phone ? h('a', { key: 'p', href: 'https://wa.me/' + String(pr.customer.phone).replace(/\D/g, '').replace(/^0/, '60'), target: '_blank', rel: 'noopener', style: { color: TEAL, fontWeight: 600 } }, pr.customer.phone) : null, h('p', { key: 'a', style: { margin: 0, color: MUT, lineHeight: 1.6 } }, pr.customer.address), pr.customer.orderNumber ? muted('Order #' + pr.customer.orderNumber) : null]) : null,
      !isHub && pr.deliverTo && j.outsource ? this.acC('Printer delivers to', [h('b', { key: 'n' }, pr.deliverTo.name), h('p', { key: 'a', style: { margin: 0, color: MUT, whiteSpace: 'pre-wrap' } }, pr.deliverTo.address), pr.deliverTo.phone ? muted('Phone ' + pr.deliverTo.phone) : null]) : null,
      !isHub ? this.acC('General', this.acDL([['Order', o ? h('span', { 'data-go': 'vieworder:' + o.id, style: { color: TEAL, fontWeight: 600, cursor: 'pointer' } }, o.id) : j.orderId], ['Date created', when(j.createdAt)], ['Payment', j.paymentValidated ? 'Confirmed' : j.creditTerms ? 'Credit terms' : 'Pending'], ['Value', this.rm(j.price || 0)], ['Route', j.route === 'inhouse' ? 'In-house' : j.route === 'outsource' ? 'Outsourced' : '—'], pr.status ? ['Printing job', jobPill(pr.status)] : null])) : null,
    ];
    const home = tabs[0], typeTab = tabs.indexOf('Orders') >= 0 ? 'Orders' : tabs[1];
    return this.acSingle({ home, type: typeTab, title: '#' + id, statusNode: h('span', { style: { display: 'inline-flex', gap: 8, flexWrap: 'wrap' } }, this.pillDot(j.statusLabel || j.status, j.status === 'completed' ? 'ok' : j.status === 'rejected' ? 'bad' : 'teal'), pr.status ? jobPill(pr.status) : null) }, main, aside);
  };
  // which Delivery Details card a job has now: the hub's (at hub → forward) or logistics' (packed → dispatch)
  const deliveryStage = (j, pr) => j.status === 'at_hub' ? 'hub' : j.status === 'logistics' ? 'logistics' : pr.hubDelivery ? 'hub' : pr.dispatchDelivery ? 'logistics' : null;
  P.deliveryCard = function (j, pr, stage) {
    const cfg = this.state.opsConfig || { couriers: [], outlets: [] };
    const hd = (stage === 'hub' ? pr.hubDelivery : pr.dispatchDelivery) || {};
    const at = stage === 'hub' ? j.status === 'at_hub' : j.status === 'logistics';
    const F = (k, def) => this.acF(k) !== '' ? this.acF(k) : def;
    const tracking = F('hdTracking', (hd.tracking || []).join('\n')), company = F('hdCompany', hd.company || cfg.couriers[0] || '');
    const destType = F('hdDest', (j.finalDestination && j.finalDestination.type) || 'customer');
    const steps = stage === 'hub' ? ['checked', 'qc', 'relabelled'] : ['picked', 'packed', 'labelled'];
    const prog = (j.progress && j.progress[stage]) || {}; const ready = !at || steps.every(k => prog[k]);
    const dest = j.destination || {};
    return this.acC('Delivery Details', [
      stage === 'logistics' ? this.acDL([['Deliver to', (dest.name || dest.type || '—') + (dest.address ? ', ' + dest.address : '')], j.instructions ? ['Instructions', j.instructions] : null]) : null,
      FG('Delivery Order / Tracking Number', h('textarea', { rows: 6, value: tracking, onChange: e => this.acSetF('hdTracking', e.target.value), style: Object.assign({}, inp, { resize: 'vertical' }) }), 1, 'Enter a least 1 tracking number. Enter new line for additional tracking numbers.'),
      FG('Delivery Company', h('select', { value: company, onChange: e => this.acSetF('hdCompany', e.target.value), style: inp }, (cfg.couriers.length ? cfg.couriers : [company]).map(c => h('option', { key: c, value: c }, c))), 1),
      at && stage === 'hub' ? FG('Deliver to', h('select', { value: destType, onChange: e => this.acSetF('hdDest', e.target.value), style: inp }, [['customer', 'Customer — ' + ((j.finalDestination && j.finalDestination.type === 'customer' && j.finalDestination.address) || 'delivery address')], ['outlet', 'Outlet — ' + ((j.finalDestination && j.finalDestination.type === 'outlet' && j.finalDestination.name) || 'pickup outlet')]].map(o => h('option', { key: o[0], value: o[0] }, o[1])))) : null,
      FG('Delivery Order', h('div', { style: { display: 'flex', flexDirection: 'column', gap: 6 } }, hd.document ? link('📄 ' + hd.document.name, () => this.jDownload('/api/jobs/' + j.id + '/files/' + hd.document.id, hd.document.name)) : null, this.jPickFile('hdDoc'))),
      !ready ? muted(stage === 'hub' ? 'Tick every step of the hub progress form before shipping.' : 'Tick picked, packed and labelled in the logistics status update before dispatching.') : null,
      h('div', { key: 'b' }, Btn(at && stage === 'logistics' ? 'Dispatch' : 'Save Changes', () => this.jPost('/api/jobs/' + j.id + '/delivery', { tracking, company, destType: at && stage === 'hub' ? destType : undefined, destId: at && stage === 'hub' && j.finalDestination && j.finalDestination.type === destType ? j.finalDestination.id : undefined, documentData: this.acF('hdDocData') || undefined, documentName: this.acF('hdDocName') || undefined }, null, () => this.setState({ acForm: {} })), 'primary', !ready || !tracking.trim())),
    ]);
  };

  // ================================================================== PRINTER (original supplier account)
  const V_TABS = ['Dashboard', 'Printing Jobs', 'Custom Quotes'];
  P.s_vendor = function () {
    const u = this.state.user || {}; const v = this.state.acView;
    const tab = V_TABS.indexOf(this.state.sTab) >= 0 ? this.state.sTab : 'Dashboard';
    const shell = { tabs: V_TABS, active: tab, icon: 'printer', accent: 'linear-gradient(180deg,#2fa4c5,#02cd9c)', sub: u.role === 'printer_staff' ? 'Printer staff' : 'Printer manager', menu: [['Dashboard', () => this.setState({ acView: null, sTab: 'Dashboard' })]] };
    let content;
    if (v && v.kind === 'job') { const d = this.acGet('vjob_' + v.id, '/api/jobs/' + encodeURIComponent(v.id)); const s = d && d.printing && d.printing.status; if (s) shell.progress = { text: s.label + ' - Step ' + s.step + ' of ' + s.of, width: Math.round(s.step / s.of * 100) }; content = this.vJob(d); }
    else if (v && v.kind === 'cq') content = this.vCustomQuote(this.acGet('vcq_' + v.id, '/api/vendor/custom-quotes/' + encodeURIComponent(v.id)));
    else if (tab === 'Printing Jobs') content = this.vJobs();
    else if (tab === 'Custom Quotes') content = this.vCustomQuotes();
    else content = this.vDashboard();
    return this.acPage(shell, content);
  };
  P.vDashboard = function () {
    const jobs = (this.acGet('v_jobs', '/api/jobs') || {}).jobs || [];
    const cqs = (this.acGet('v_cqs', '/api/vendor/custom-quotes') || {}).quotes || [];
    const n = f => jobs.filter(j => j.printing && f(j.printing)).length;
    const go = (tab, key, val) => this.setState({ sTab: tab, [key]: val });
    return [this.acCard(this.acQuick([
      { label: 'Quote requests', value: n(p => /^quote/.test(p.statusId) && !p.submitted), icon: 'edit-3', color: 'teal', onClick: () => go('Printing Jobs', 'vj_s', 'Quote requested') },
      { label: 'Upload draft', value: n(p => p.statusId === 'printer-assigned'), icon: 'upload', color: 'red', onClick: () => go('Printing Jobs', 'vj_s', 'Printer assigned') },
      { label: 'Ready to print & ship', value: n(p => p.statusId === 'draft-approved'), icon: 'truck', color: 'orange', onClick: () => go('Printing Jobs', 'vj_s', 'Draft approved') },
      { label: 'Custom quotes', value: cqs.filter(q => q.status === 'Pending quote').length, icon: 'file', color: 'teal', onClick: () => go('Custom Quotes', 'vc_s', 'Pending quote') }])), this.notifPanel()];
  };
  P.vJobs = function () {
    const d = this.acGet('v_jobs', '/api/jobs'); if (!d) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    return this.acList({ key: 'vj', title: 'Printing Jobs', cols: ['Job number', 'Product', { label: 'Total Amount', right: true }, 'Status', 'Order date'],
      rows: (d.jobs || []).map(j => { const p = j.printing || {}; return { date: p.date, status: p.status, search: [j.id, j.product, p.po],
        cells: [link(j.id, () => this.acOpen({ kind: 'job', id: j.id })), j.product, p.amount != null ? 'RM' + Number(p.amount).toFixed(2) : '', jobPill({ label: p.status, color: p.color }), dmy(p.date)] }; }) });
  };
  P.vJob = function (d) {
    if (!d) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    if (d.error) return [h('div', { key: 'e', style: { color: '#c0392b' } }, d.error)];
    const j = d.job, p = d.printing || {}, s = p.status || {}, id = j.id, mq = p.myQuote || {};
    const staff = (this.state.user || {}).role === 'printer_staff';
    const fileLink = f => f ? link('📄 ' + f.name, () => this.jDownload('/api/jobs/' + id + '/files/' + f.id, f.name)) : null;
    const quoteCard = () => this.acC('Quote', this.acDL([['Quote amount (RM)', (mq.awardedAmount != null ? mq.awardedAmount : mq.amount) != null ? Number(mq.awardedAmount != null ? mq.awardedAmount : mq.amount).toFixed(2) : '—'], ['Quote document', mq.document ? fileLink(mq.document) : '—']]));
    const main = [];
    if (['quote-requested', 'quote-partly-received', 'quotes-received'].indexOf(s.id) >= 0) {
      const amt = this.acF('qAmount') !== '' ? this.acF('qAmount') : (mq.amount != null ? String(mq.amount) : '');
      const lead = this.acF('qLead') !== '' ? this.acF('qLead') : (mq.leadDays ? String(mq.leadDays) : '');
      main.push(this.acC('Request Quote', p.canQuote ? [
        FG('Quote amount (RM)', h('input', { type: 'text', value: amt, onChange: e => this.acSetF('qAmount', e.target.value), style: inp }), 1),
        FG('Lead time (days)', h('input', { type: 'number', value: lead, onChange: e => this.acSetF('qLead', e.target.value), style: inp })),
        FG('Quote document', h('div', { style: { display: 'flex', flexDirection: 'column', gap: 6 } }, mq.document ? fileLink(mq.document) : null, this.jPickFile('qDoc'))),
        h('div', { key: 'b' }, Btn('Submit quote', () => this.jPost('/api/jobs/' + id + '/vendor-quote', { amount: amt, leadDays: lead, documentData: this.acF('qDocData') || undefined, documentName: this.acF('qDocName') || undefined }, null, () => this.setState({ acForm: {} })), 'primary', !amt))]
        : [mq.submittedAt ? this.acDL([['Quote amount (RM)', Number(mq.amount).toFixed(2)], ['Quote document', mq.document ? fileLink(mq.document) : '—']]) : null, muted(staff ? 'Your printer manager submits the price for this job.' : 'Quoting is closed for this job.')]));
    }
    if (['printer-assigned', 'draft-pending-approval'].indexOf(s.id) >= 0) {
      const dr = p.draft || {};
      main.push(this.acC('Upload Draft', [
        dr.rejectedAt ? alertBox('The administrator asked for changes: ' + dr.rejectReason, 'bad') : null,
        alertBox(dr.file && !dr.rejectedAt ? 'Please wait for admin approve the draft before start printing.' : 'Please upload draft for approval before start printing.'),
        dr.file ? fileLink(dr.file) : null,
        this.jPickFile('draft'),
        h('div', { key: 'b' }, Btn('Save Changes', () => this.jPost('/api/jobs/' + id + '/draft', { data: this.acF('draftData'), name: this.acF('draftName') }, null, () => this.setState({ acForm: {} })), 'primary', !this.acF('draftData')))]));
      main.push(quoteCard());
    }
    if (s.id === 'draft-approved') {
      const cfg = this.state.opsConfig || { couriers: [] };
      const st = this.acF('jStatus') || 'draft-approved';
      main.push(this.acC('Job Status', [
        alertBox('The administrator has approved the draft. You may proceed with printing.', 'ok'),
        muted('After shipping the items to ' + (j.destination && j.destination.type === 'outlet' ? 'the outlet' : 'production') + ', update the status below, then click save changes.'),
        h('select', { key: 's', value: st, onChange: e => this.acSetF('jStatus', e.target.value), style: inp }, [['draft-approved', 'Draft approved'], ['shipped-to-hub', 'Shipped to ' + ((j.destination && j.destination.name) || 'production')]].map(o => h('option', { key: o[0], value: o[0] }, o[1]))),
        st === 'shipped-to-hub' ? h('div', { key: 'c', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 10 } },
          FG('Courier', h('input', { list: 'pk-couriers', value: this.acF('jCourier'), onChange: e => this.acSetF('jCourier', e.target.value), placeholder: 'e.g. J&T Express, own van', style: inp }), 0),
          FG('Tracking number', h('input', { value: this.acF('jTracking'), onChange: e => this.acSetF('jTracking', e.target.value), style: inp })),
          h('datalist', { id: 'pk-couriers' }, (cfg.couriers || []).map(c => h('option', { key: c, value: c })))) : null,
        h('div', { key: 'b' }, Btn('Save Changes', () => st !== 'shipped-to-hub' ? this.setState({ acMsg: { bad: true, text: 'No changes required.' } }) : this.jPost('/api/jobs/' + id + '/ship-to-hub', { status: st, courier: this.acF('jCourier'), tracking: this.acF('jTracking') }, null, () => this.setState({ acForm: {} })), 'primary'))]));
      main.push(quoteCard());
    }
    if (['shipped-to-hub', 'shipped', 'paid'].indexOf(s.id) >= 0) main.push(quoteCard());
    if (s.id === 'not-awarded') main.push(this.acC('Quote', [muted('This job was awarded to another printer. Thank you for quoting.'), mq.submittedAt ? this.acDL([['Your quote (RM)', Number(mq.amount).toFixed(2)]]) : null]));
    const J = p.job || {};
    main.push(this.acC('Job details', [
      h('b', { key: 'p' }, J.product || j.product), this.acSpec(J.spec || j.spec),
      this.acDL([['Quantity', (J.qty || j.qty || 0).toLocaleString()], ['Deadline', J.deadline ? when(J.deadline) : '—'], ['Deliver to', j.destination ? (j.destination.name || j.destination.type) + (j.destination.address ? ', ' + j.destination.address : '') : '—'], J.instructions ? ['Instructions', J.instructions] : null, p.po ? ['Purchase order', p.po] : null]),
      (J.artworks || []).length ? h('div', { key: 'a', style: { background: ALT, borderRadius: 6, padding: 12, display: 'flex', flexDirection: 'column', gap: 8 } }, h('b', { style: { fontSize: 12.5 } }, 'Artworks'),
        h('ol', { style: { margin: 0, paddingLeft: 18 } }, J.artworks.map((a, i) => h('li', { key: i, style: { marginBottom: 4 } }, a.id && p.awardedToMe ? link(a.name, () => this.openOrderFile(a.orderId, a)) : h('span', { style: { color: MUT } }, a.name))))) : null]));
    const aside = [
      this.acC('Activities', this.acStatusList(p.activities || [])),
      (p.documents || []).length ? this.acC('Job documents', h('ol', { style: { margin: 0, paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 8 } }, p.documents.map(x => h('li', { key: x.id }, link(x.label, () => this.openJobDoc(id, x.id)))))) : null,
      p.deliverTo ? this.acC('Deliver to', [h('b', { key: 'n' }, p.deliverTo.name), h('p', { key: 'a', style: { margin: 0, color: MUT, whiteSpace: 'pre-wrap' } }, p.deliverTo.address), p.deliverTo.phone ? [h('b', { key: 'pt' }, 'Phone'), h('p', { key: 'pv', style: { margin: 0, color: MUT } }, p.deliverTo.phone)] : null]) : null,
    ];
    return this.acSingle({ home: 'Dashboard', type: 'Printing Jobs', title: id, statusNode: jobPill(s) }, main, aside);
  };
  // ---- printer custom quotes (original printer-custom-quotes + single-printer-custom-quotes)
  P.vCustomQuotes = function () {
    const d = this.acGet('v_cqs', '/api/vendor/custom-quotes'); if (!d) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    return this.acList({ key: 'vc', title: 'Custom Quotes', cols: ['Quote', 'Product', { label: 'Total Amount', right: true }, 'Status', 'Date'],
      rows: (d.quotes || []).map(q => ({ date: q.date, status: q.status, search: [q.id, q.product], cells: [link(q.id, () => this.acOpen({ kind: 'cq', id: q.id })), q.product, q.amount != null ? 'RM' + Number(q.amount).toFixed(2) : '', this.pillDot(q.status, q.status === 'Quote submitted' ? 'ok' : 'warn'), dmy(q.date)] })) });
  };
  P.vCustomQuote = function (d) {
    if (!d) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    if (d.error) return [h('div', { key: 'e', style: { color: '#c0392b' } }, d.error)];
    const q = d.quote, m = q.mine || {};
    const main = [];
    if (m.submittedAt) main.push(this.acC('Submitted Quote', this.acDL([['Quote weight (kg)', m.weight], ['Quote amount (RM)', Number(m.amount).toFixed(2)], ['Quote document', m.document ? link('📄 ' + m.document.name, () => this.jDownload('/api/vendor/custom-quotes/' + q.id + '/document', m.document.name)) : '—']])));
    else main.push(this.acC('Request Quote', q.canSubmit ? [
      FG('Weight (kg)', h('input', { value: this.acF('cWeight'), onChange: e => this.acSetF('cWeight', e.target.value), style: inp }), 1),
      FG('Quote amount (RM)', h('input', { value: this.acF('cAmount'), onChange: e => this.acSetF('cAmount', e.target.value), style: inp }), 1),
      FG('Quote document', this.jPickFile('cDoc')),
      h('hr', { key: 'hr', style: { border: 0, borderTop: '1px solid ' + HAIR, margin: '6px 0' } }),
      h('div', { key: 'b', style: { display: 'flex', justifyContent: 'flex-end' } }, Btn('Submit quote', () => this.setState({ acModal: { title: 'One-Time Submission', body: () => [
        h('p', { key: 'a', style: { margin: 0, fontSize: 14 } }, 'You can submit the quote only once.'), h('p', { key: 'b', style: { margin: 0, fontSize: 14 } }, 'Please double-check all details for accuracy before submitting. Thank you.'),
        h('div', { key: 'c' }, Btn('Submit quote', () => this.jPost('/api/vendor/custom-quotes/' + q.id, { weight: this.acF('cWeight'), amount: this.acF('cAmount'), documentData: this.acF('cDocData') || undefined, documentName: this.acF('cDocName') || undefined }, null, () => this.setState({ acModal: null, acForm: {} })), 'primary'))] } }), 'primary', !this.acF('cWeight') || !this.acF('cAmount')))]
      : [muted('Your printer manager submits the price for this quote.')]));
    main.push(this.acC('Job details', [this.acDL([['Quantity', q.quantity || '—']]), h('b', { key: 's' }, 'Specification'), h('div', { key: 'v', style: { whiteSpace: 'pre-wrap', lineHeight: 1.7 } }, q.specification || '—')]));
    const aside = [this.acC('Activities', this.acStatusList(q.activities || [])), q.hub ? this.acC('Hub detail', [h('b', { key: 'n' }, q.hub.name), h('p', { key: 'a', style: { margin: 0, color: MUT, whiteSpace: 'pre-wrap' } }, q.hub.address)]) : null];
    return this.acSingle({ home: 'Dashboard', type: 'Custom Quotes', title: q.id, status: q.status }, main, aside);
  };

  // ================================================================== HQ: ask printers to price a custom quote
  P.oPrinterQuotes = function (q) {
    const vendors = this.state.vendors; if (!vendors) { this.loadVendors(); return null; }
    const pq = q.printerQuotes || { printers: [] }; const cfg = this.state.opsConfig || { hubs: [] };
    const F = this.state.opsForm || {}; const setF = (k, v) => this.setState(st => ({ opsForm: Object.assign({}, st.opsForm, { [k]: v }) }));
    const asked = pq.printers.map(p => p.vendorId); const picked = F.pqv || [];
    return h('div', { key: 'pq', style: { borderTop: '1px solid ' + LINE, paddingTop: 12, display: 'flex', flexDirection: 'column', gap: 10 } },
      h('div', { style: { fontSize: 15, fontWeight: 600 } }, 'Printer quotes'),
      pq.printers.length ? this.dataCard([{ label: 'Printer' }, { label: 'Weight (kg)' }, { label: 'Amount (RM)', right: true }, { label: 'Document' }, { label: 'Status' }], pq.printers.map(p => [p.vendorName, p.weight || '—', p.amount != null ? Number(p.amount).toFixed(2) : '—',
        p.document ? link(p.document.name, () => this.jDownload('/api/quotes/' + q.id + '/printer-quotes/' + p.vendorId + '/document', p.document.name)) : '—', this.pillDot(p.submittedAt ? 'Quote submitted' : 'Pending quote', p.submittedAt ? 'ok' : 'warn')]), { minWidth: 560 }) : null,
      h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(210px,1fr))', gap: 8 } }, vendors.filter(v => asked.indexOf(v.id) < 0).map(v => h('label', { key: v.id, style: { display: 'flex', gap: 8, alignItems: 'center', border: '1px solid ' + HAIR, borderRadius: 8, padding: '8px 10px', fontSize: 13, cursor: 'pointer' } },
        h('input', { type: 'checkbox', checked: picked.indexOf(v.id) >= 0, onChange: () => setF('pqv', picked.indexOf(v.id) >= 0 ? picked.filter(x => x !== v.id) : picked.concat([v.id])) }), v.name))),
      h('div', { style: { display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' } },
        h('select', { value: F.pqHub || pq.hub || '', onChange: e => setF('pqHub', e.target.value), style: Object.assign({}, inp, { maxWidth: 260 }) }, [h('option', { key: '', value: '' }, 'Deliver to hub…')].concat((cfg.hubs || []).map(x => h('option', { key: x.id, value: x.id }, x.name)))),
        Btn('Request printer quotes', () => this.opsFetch('/api/quotes/' + q.id + '/printer-quotes', { vendorIds: picked, hub: F.pqHub || pq.hub || null }).then(d => { if (this.opsDone(d, 'Printer quote requests sent.')) { setF('pqv', []); this.loadQuotes(); } }), 'primary', !picked.length)));
  };
})();
