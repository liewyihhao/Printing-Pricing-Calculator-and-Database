/*
 * Printoka operations dashboards — mixed into the app component after app.js.
 *
 *   Qn 732  Hub system: Hub dashboard, Hub performance (total orders processed), Hub interactive
 *           progress form, Hub manager / staff action tracker
 *   Qn 750  Production (manager + staff): dashboards, sales data & details, in-house / outsource /
 *           custom-quote interactive progress forms, production sales performance, order listing,
 *           order details, custom quote details, staff KPI
 *           Prepress: dashboard, order listing, approve / reject pop-up, KPI
 *           Logistics: dashboard, order listing, status-update pop-up, KPI
 *   Qn 752  CF1 send an order to internal production with delivery instructions (Hub / Outlet /
 *           Customer; shipping label + assigned hub/outlet) · CF2 direct job award without a quote
 *
 * Every screen reads the SAME live jobs (/api/jobs, role derived from the signed-in account on the
 * server) and writes through the state machine, so one order stays in sync across departments,
 * the outlet and the customer's tracking page.
 */
(function () {
  const C = window.PKComponent; if (!C) return;
  const P = C.prototype;

  // ---------------------------------------------------------------- routes & access
  const prodScreen = SCREENS.find(s => s[0] === 'production');
  if (prodScreen) { prodScreen[1] = 'Production'; prodScreen[3] = 'Production floor + manager — in-house progress form, sales data, performance, staff KPI'; }
  SCREENS.push(['scheduler', 'Scheduler', 'E3', 'Scheduler — allocation queue, send to internal production, outsourcing & custom quotes']);
  SCREENS.push(['hub', 'Hub', 'E7', 'Hub system — inbound, interactive progress form, performance, action tracker']);

  // which ops screens each production login may open (first = home)
  const PROD_ROUTES = {
    prepress: ['prepress'], prepress_manager: ['prepress'],
    scheduler: ['scheduler'], scheduler_manager: ['scheduler', 'production'],
    production_staff: ['production'], production_manager: ['production', 'scheduler', 'prepress', 'logistics', 'hub'],
    logistics: ['logistics'], logistics_manager: ['logistics'],
  };
  const OPS_SCREENS = { outlet: 1, prepress: 1, production: 1, scheduler: 1, logistics: 1, hub: 1, director: 1 };
  const origAccess = P.access, origHomeFor = P.homeFor;
  P.access = function () {
    const type = this.userType(), role = this.userRole();
    if (type === 'admin') return origAccess.call(this).concat(['scheduler', 'hub']);
    if (type === 'hub') return ['hub', 'auth'];
    if (type === 'vendor') return ['vendor', 'auth'];
    if (type === 'production') return (PROD_ROUTES[role] || ['prepress']).concat(['artwork', 'auth']);
    return origAccess.call(this);
  };
  P.homeFor = function (u) {
    u = u || this.state.user || {};
    if (u.type === 'hub') return 'hub';
    if (u.type === 'production') return (PROD_ROUTES[u.role] || ['prepress'])[0];
    return origHomeFor.call(this, u);
  };
  P.opsRoleFor = function (route) { return OPS_SCREENS[route] ? 'session' : null; };
  P.opsActingRole = function () { return 'session'; };
  P.isOpsManager = function () { const r = this.userRole(); return this.userType() === 'admin' || /manager/.test(r); };

  // ---------------------------------------------------------------- login portals
  // Each sign-in page only admits its own kind of account (enforced on the server too).
  const PORTALS = {
    member: { title: 'Login', path: '/account/', bg: '#E52220', accent: '#E52220', head: 'Sign up for some member deals!', sub: 'Sign up for some member deals!' },
    printer: { title: 'Printer Login', path: '/account/printer-login/', bg: 'linear-gradient(90deg,#2fa4c5,#02cd9c)', accent: '#2fa4c5', head: 'Printer partner portal', sub: 'Quote on jobs, win purchase orders and ship with the Printoka label.',
      feats: [['Quote requests from the Printoka scheduler', 'edit-3'], ['Purchase orders on award', 'file'], ['Printoka shipping labels', 'box'], ['Company staff logins', 'user-plus']] },
    hub: { title: 'Hub Login', path: '/account/hub-login/', bg: 'linear-gradient(90deg,#F4732F,#FFB600)', accent: '#F4732F', head: 'Hub system', sub: 'Receive, check, relabel and forward every parcel on time.',
      feats: [['Inbound parcels from production & printers', 'truck'], ['Interactive progress form', 'check'], ['Hub performance', 'layers'], ['Manager / staff action tracker', 'clock']] },
    outlet: { title: 'Outlet Login', path: '/account/outlet-login/', bg: 'linear-gradient(90deg,#6a3de8,#b44bd6)', accent: '#6a3de8', head: 'Outlet counter', sub: 'Walk-in quotes, online orders and collections for your outlet.',
      feats: [['Walk-in quotes & follow-ups', 'edit-3'], ['Online orders for your outlet', 'file'], ['Collections & customer pickup', 'box'], ['Outlet sales performance', 'layers']] },
    production: { title: 'Production Login', path: '/account/production-login/', bg: 'linear-gradient(90deg,#1f3b73,#2e6bd9)', accent: '#2e6bd9', head: 'Production system', sub: 'Prepress, Scheduler and Logistics under the Production Director.',
      feats: [['Prepress file check', 'check'], ['Scheduling, printing & outsourcing', 'printer'], ['Receiving, packing & delivery', 'truck'], ['Daily reports to the Production Director', 'layers']] },
    admin: { title: 'Admin Login', path: '/account/admin-login/', bg: 'linear-gradient(90deg,#1b1b1f,#4a4a55)', accent: '#212121', head: 'Printoka admin', sub: 'Orders, products, customers, users & roles, content and settings.',
      feats: [['Orders & customers', 'file'], ['Products & pricing', 'layers'], ['Users & roles', 'user-plus'], ['Content & settings', 'edit-3']] },
  };
  P.authPortal = function (role) { return PORTALS[role] || PORTALS.member; };
  P.authPortals = function () { return PORTALS; };
  P.login = function () {
    this.setState({ authBusy: true, authErr: null });
    const portal = this.state.authRole || 'member';
    fetch('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: this.state.lgEmail, password: this.state.lgPass, portal }) })
      .then(r => r.json()).then(d => d.token ? this.authSetSession(d) : this.setState({ authErr: d.error || 'Could not sign in.', authErrPortal: d.portal || null, authBusy: false }))
      .catch(() => this.setState({ authErr: 'Network error.', authBusy: false }));
  };

  // ---------------------------------------------------------------- live data
  P.opsLoad = function () {
    if (typeof fetch !== 'function' || !this.authToken()) return;
    fetch('/api/jobs', { headers: this.authHeaders() }).then(r => r.ok ? r.json() : null)
      .then(d => { if (d) this.setState({ ops: { jobs: d.jobs || [], role: d.role, loaded: true } }); }).catch(() => {});
    this._od = {}; // invalidate cached KPI / sales / perf so the next render refetches
    if (!this._opsTimer && typeof window !== 'undefined') {
      // keep every department in sync without a manual refresh
      this._opsTimer = setInterval(() => { if (OPS_SCREENS[this.state.route] && this.authToken() && !this.state.opsModal) this.opsLoad(); }, 30000);
    }
    if (!this.state.opsConfig) this.opsFetch('/api/ops/config').then(d => d && this.setState({ opsConfig: d.config }));
  };
  P.opsFetch = function (url, body) {
    const opt = { headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()) };
    if (body !== undefined) { opt.method = 'POST'; opt.body = JSON.stringify(body || {}); }
    return fetch(url, opt).then(r => r.json().then(d => (r.ok ? d : Object.assign({ error: d.error || 'Request failed' }, d)))).catch(() => ({ error: 'Network error' }));
  };
  // cached GET for dashboards: returns the data (or null while loading) and fetches once
  P.od = function (key, url) {
    this._od = this._od || {};
    const c = this._od[key];
    if (c && c.data) return c.data;
    if (!c) { this._od[key] = { loading: true }; setTimeout(() => this.opsFetch(url).then(d => { this._od[key] = { data: d }; this.forceUpdate(); }), 0); }
    return null;
  };
  P.opsToastSet = function (bad, text) { const m = { bad, text, at: Date.now() }; this.setState({ opsMsg: m }); setTimeout(() => { if (this.state.opsMsg === m) this.setState({ opsMsg: null }); }, bad ? 10000 : 5000); };
  P.opsDone = function (d, okText) {
    if (!d || d.error) { this.opsToastSet(true, (d && d.error) || 'Something went wrong.'); return false; }
    if (okText) this.opsToastSet(false, okText);
    this.opsLoad();
    if (this.state.opsModal && this.state.opsModal.jobId) this.opsLoadJob(this.state.opsModal.jobId);
    return true;
  };
  P.opsTransition = function (jobId, action, payload, okText) {
    return this.opsFetch('/api/jobs/' + jobId + '/transition', { action, payload: payload || {} })
      .then(d => { const ok = this.opsDone(d, okText || (action.replace(/_/g, ' ') + ' ✓')); if (ok && this.state.opsModal && this.state.opsModal.closeOnDone) this.setState({ opsModal: null }); return ok; });
  };
  P.opsStep = function (jobId, group, key, done) { return this.opsFetch('/api/jobs/' + jobId + '/step', { group, key, done }).then(d => this.opsDone(d)); };
  P.opsLoadJob = function (jobId) { this.opsFetch('/api/jobs/' + jobId).then(d => { if (!d.error) this.setState({ opsJob: d }); }); };
  P.opsOpen = function (kind, j, extra) {
    this.setState({ opsModal: Object.assign({ kind, jobId: j ? j.id : null }, extra || {}), opsForm: {} });
    if (j && kind === 'job') { this.setState({ opsJob: null }); this.opsLoadJob(j.id); }
    if ((kind === 'outsource' || kind === 'award') && !this.state.vendors) this.loadVendors();
  };
  // what a job-card action button does: open the right pop-up, or transition straight away
  P.opsAction = function (j, a) {
    const byAction = { assign_inhouse: 'send', assign_outsource: 'outsource', dispatch: 'ship', forward: 'ship', vendor_ship: 'ship', resubmit: 'resubmit',
      approve: 'review', flag_minor: 'review', reject_major: 'review', escalate: 'review', finish: 'progress' };
    const k = byAction[a.action];
    if (k === 'review') return this.setState({ reviewJob: j.id });
    if (k === 'progress') return this.opsOpen('progress', j, { group: 'inhouse' });
    if (k) return this.opsOpen(k, j, { action: a.action });
    this.opsTransition(j.id, a.action, {});
  };

  // live pipeline strip across every department (incl. the production floor and the hub)
  P.opsPipeline = function (highlight) {
    const jobs = this.opsJobs();
    const stages = [['outlet', 'Outlet'], ['prepress', 'Prepress'], ['scheduler', 'Scheduler'], ['production', 'Production'], ['logistics', 'Logistics'], ['hub', 'Hub'], ['done', 'Done']];
    const n = q => jobs.filter(j => j.queue === q).length;
    return h('div', { key: 'pipe', style: { display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 6, border: '1px solid ' + HAIR, borderRadius: 12, padding: '12px 16px', background: '#fff' } },
      h('span', { style: { fontSize: 11, fontWeight: 600, letterSpacing: '.07em', textTransform: 'uppercase', color: FAINT, marginRight: 6 } }, 'Live pipeline'),
      stages.map((s, i) => { const on = s[0] === highlight, c = n(s[0]);
        return h('span', { key: s[0], style: { display: 'flex', alignItems: 'center', gap: 6 } },
          h('span', { style: { display: 'flex', alignItems: 'center', gap: 7, padding: '5px 11px', borderRadius: 999, background: on ? TEAL : (c ? '#fdf2f2' : ALT), color: on ? '#fff' : (c ? TEAL : MUT), fontSize: 12.5, fontWeight: 600 } },
            s[1], h('span', { style: { background: on ? 'rgba(255,255,255,.25)' : '#fff', color: on ? '#fff' : (c ? TEAL : FAINT), borderRadius: 999, padding: '0 7px', fontSize: 11.5 } }, c)),
          i < stages.length - 1 ? h('span', { style: { color: '#d5dae0', fontSize: 13 } }, '→') : null); }));
  };

  // daily bar chart (sparse date labels, values only on non-zero bars)
  P.oBars = function (series, hgt) {
    const H = hgt || 200, W = 1000, pad = 26, n = Math.max(1, series.length), max = Math.max(1, Math.max.apply(null, series.map(x => x.n)));
    const bw = (W - pad * 2) / n, step = Math.ceil(n / 8);
    return h('svg', { viewBox: '0 0 ' + W + ' ' + (H + 24), style: { width: '100%', height: 'auto', display: 'block' }, role: 'img', 'aria-label': 'Daily chart' },
      h('line', { x1: pad, y1: H, x2: W - pad, y2: H, stroke: HAIR }),
      series.map((x, i) => { const bh = x.n / max * (H - 30); const X = pad + i * bw;
        return h('g', { key: i },
          h('rect', { x: X + bw * .18, y: H - bh, width: bw * .64, height: Math.max(bh, x.n ? 2 : 0), rx: 3, fill: x.n ? TEAL : LINE }),
          x.n ? h('text', { x: X + bw / 2, y: H - bh - 6, textAnchor: 'middle', fontSize: 18, fontWeight: 600, fill: INK }, String(x.n)) : null,
          i % step === 0 || i === n - 1 ? h('text', { x: X + bw / 2, y: H + 20, textAnchor: 'middle', fontSize: 16, fill: FAINT }, x.day.slice(5)) : null); }));
  };
  // ---------------------------------------------------------------- small UI kit
  const box = (children, extra) => h('div', { style: Object.assign({ background: '#fff', borderRadius: 12, border: '1px solid ' + HAIR, padding: 18 }, extra || {}) }, children);
  const title = (t, sub) => h('div', { style: { marginBottom: 2 } }, h('h1', { style: { fontSize: 24, fontWeight: 700, letterSpacing: '-.02em', margin: '2px 0 4px' } }, t), sub ? h('p', { style: { margin: 0, fontSize: 13.5, color: MUT, maxWidth: '90ch', lineHeight: 1.6 } }, sub) : null);
  const sub2 = t => h('div', { style: { fontSize: 15, fontWeight: 600, margin: '4px 0 10px' } }, t);
  const mins = m => m == null ? '—' : m < 60 ? Math.round(m) + ' min' : m < 1440 ? (m / 60).toFixed(1) + ' h' : (m / 1440).toFixed(1) + ' d';
  const pct = v => v == null ? '—' : v + '%';
  const when = ts => { if (!ts) return '—'; const d = new Date(ts); return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }) + ' ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }); };
  const inp = { font: '400 13.5px Montserrat,sans-serif', padding: '9px 11px', border: '1px solid ' + HAIR, borderRadius: 8, width: '100%', background: '#fff' };
  const btnS = (kind) => ({ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6, font: '600 13px Montserrat,sans-serif', padding: '9px 15px', borderRadius: 8, cursor: 'pointer', border: '1px solid ' + (kind === 'primary' ? TEAL : kind === 'dark' ? INK : HAIR), background: kind === 'primary' ? TEAL : kind === 'dark' ? INK : '#fff', color: kind === 'primary' || kind === 'dark' ? '#fff' : INK, whiteSpace: 'nowrap' });
  const B = (label, onClick, kind, disabled, title) => h('button', { type: 'button', title: title || undefined, disabled: !!disabled, onClick: disabled ? undefined : onClick, style: Object.assign(btnS(kind), disabled ? { opacity: .45, cursor: 'not-allowed' } : {}) }, label);
  const field = (label, control, hint) => h('label', { style: { display: 'flex', flexDirection: 'column', gap: 5, fontSize: 12.5, fontWeight: 600, color: INK } }, label, control, hint ? h('span', { style: { fontSize: 11.5, fontWeight: 400, color: FAINT, lineHeight: 1.5 } }, hint) : null);
  const kv = (rows) => h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(210px,1fr))', gap: '10px 18px' } },
    rows.filter(Boolean).map((r, i) => h('div', { key: i, style: { minWidth: 0 } }, h('div', { style: { fontSize: 11, fontWeight: 600, letterSpacing: '.05em', textTransform: 'uppercase', color: FAINT } }, r[0]), h('div', { style: { fontSize: 13.5, color: INK, marginTop: 2, wordBreak: 'break-word' } }, r[1] == null || r[1] === '' ? '—' : r[1]))));
  const DEST_ICON = { hub: '🏭', outlet: '🏬', customer: '🏠' };
  const destText = d => d ? (DEST_ICON[d.type] || '') + ' ' + (d.name || d.type) : '—';

  // stepper: steps = [[label, done(bool), sub]] — the "interactive progress form" header
  P.oStepper = function (steps) {
    const cur = steps.findIndex(s => !s[1]);
    return h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center' } },
      steps.map((s, i) => h('span', { key: i, style: { display: 'inline-flex', alignItems: 'center', gap: 6 } },
        h('span', { title: s[2] || '', style: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '5px 10px', borderRadius: 999, fontSize: 12, fontWeight: 600,
          background: s[1] ? '#e6f4ea' : i === cur ? '#fdf2f2' : ALT, color: s[1] ? '#3d8b40' : i === cur ? TEAL : FAINT, border: '1px solid ' + (s[1] ? '#cfe8d4' : i === cur ? '#f5c8c7' : HAIR) } },
          h('span', { style: { fontSize: 11, opacity: .85 } }, s[1] ? '✓' : String(i + 1)), h('span', null, s[0])),
        i < steps.length - 1 ? h('span', { style: { color: '#d5dae0' } }, '›') : null)));
  };
  P.oToast = function () {
    // same notification as the account screens (original toka_toast look)
    return this.pkToastView(this.state.opsMsg, () => this.setState({ opsMsg: null }), 'toast');
  };
  // department switcher for managers / admin who oversee several screens
  P.oDeptSwitch = function (active) {
    const LAB = { prepress: 'Prepress', scheduler: 'Scheduler', production: 'Production', logistics: 'Logistics', hub: 'Hub', outlet: 'Outlet', vendor: 'Printers', admin: 'Admin' };
    const list = ['admin', 'outlet', 'prepress', 'scheduler', 'production', 'logistics', 'hub', 'vendor'].filter(r => this.canAccess(r));
    if (list.length < 2) return null;
    return h('div', { key: 'dsw', style: { display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' } },
      h('span', { style: { fontSize: 11, fontWeight: 700, letterSpacing: '.07em', textTransform: 'uppercase', color: FAINT, marginRight: 4 } }, 'Departments'),
      list.map(r => h('span', { key: r, 'data-go': r, style: { fontSize: 12.5, fontWeight: 600, padding: '5px 12px', borderRadius: 999, cursor: 'pointer', background: r === active ? INK : '#fff', color: r === active ? '#fff' : MUT, border: '1px solid ' + (r === active ? INK : HAIR) } }, LAB[r] || r)));
  };
  P.oPage = function (route, tabs, tab, identity, content) {
    return this.staffPage(tabs, tab, identity, [this.oDeptSwitch(route)].concat(content, [this.opsModalView(), this.opsReviewDialog(), this.oToast()]));
  };
  P.oTab = function (tabs) { return tabs.indexOf(this.state.sTab) >= 0 ? this.state.sTab : tabs[0]; };
  P.oIdentity = function (dept) { const u = this.state.user || {}; return { title: dept, sub: (u.name || '') + (u.role ? ' · ' + u.role.replace(/_/g, ' ') : '') }; };

  // compact live job tile with the department's primary actions
  P.oTile = function (j, extra) {
    const acts = (j.actions || []).filter(a => a.permitted);
    const late = j.deadline && Date.parse(j.deadline) < Date.now() && j.status !== 'completed';
    return h('div', { key: j.id, style: { border: '1px solid ' + (late ? '#f5c8c7' : HAIR), borderRadius: 12, background: '#fff', padding: 14, display: 'flex', flexDirection: 'column', gap: 8 } },
      h('div', { style: { display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' } },
        h('span', { style: { font: '600 12px ui-monospace,Menlo,monospace', color: TEAL } }, j.id),
        this.chip(j.statusLabel || j.status, late ? 'bad' : 'teal'),
        late ? this.chip('Overdue', 'bad') : null,
        h('span', { style: { marginLeft: 'auto', fontSize: 12, color: FAINT } }, j.deadline ? 'Due ' + when(j.deadline) : '')),
      h('div', { style: { display: 'flex', gap: 12 } },
        h('div', { style: { flex: '0 0 64px' } }, this.art(j.product)),
        h('div', { style: { flex: 1, minWidth: 0 } },
          h('div', { style: { fontSize: 14, fontWeight: 600 } }, j.customer),
          h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.5 } }, j.product + ' · qty ' + (j.qty || 0).toLocaleString()),
          h('div', { style: { fontSize: 12, color: FAINT, lineHeight: 1.5, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, j.spec || ''),
          h('div', { style: { fontSize: 12, color: MUT, marginTop: 3 } }, 'To ' + destText(j.destination) + (j.hub ? ' · hub ' + j.hub.replace('HUB-', '') : '')))),
      extra || null,
      h('div', { style: { display: 'flex', gap: 7, flexWrap: 'wrap', borderTop: '1px solid ' + LINE, paddingTop: 9 } },
        B('Details', () => this.opsOpen('job', j), 'ghost'),
        acts.map(a => B(this.oActLabel(a.action), () => this.opsAction(j, a), a.enabled ? 'primary' : 'ghost', !a.enabled, a.enabled ? a.note : (a.blockedBy || []).join(' ')))));
  };
  P.oActLabel = function (a) {
    return ({ acknowledge: 'Acknowledge', approve: 'Review file', flag_minor: 'Review file', reject_major: 'Review file', escalate: 'Review file', resubmit: 'New file received', assign_inhouse: 'Send to internal production', assign_outsource: 'Outsource',
      finish: 'Progress form', vendor_ship: 'Mark shipped', dispatch: 'Dispatch', deliver: 'Mark delivered', receive_hub: 'Receive at hub', receive_outlet: 'Receive at outlet', forward: 'Forward', collect: 'Customer collected' })[a] || a.replace(/_/g, ' ');
  };
  // de-duplicate the four prepress review buttons into one
  const dedupe = acts => { const seen = {}; return acts.filter(a => { const l = P.oActLabel(a.action); if (seen[l]) return false; seen[l] = 1; return true; }); };
  const origTile = P.oTile;
  P.oTile = function (j, extra) { return origTile.call(this, Object.assign({}, j, { actions: dedupe(j.actions || []) }), extra); };
  P.oGrid = function (jobs, emptyText, extraFn) {
    if (!jobs.length) return h('div', { key: 'empty', style: { border: '1px dashed ' + HAIR, borderRadius: 12, padding: 34, textAlign: 'center', color: FAINT, fontSize: 13, background: '#fff' } }, this.state.ops && this.state.ops.loaded ? emptyText : 'Loading live jobs…');
    return h('div', { key: 'grid', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(320px,1fr))', gap: 14 } }, jobs.map(j => this.oTile(j, extraFn ? extraFn(j) : null)));
  };
  // order listing view (shared by every department): search + status filter + table → details
  P.oOrders = function (jobs, key) {
    const q = String(this.state['ol_q_' + key] || '').toLowerCase(), st = this.state['ol_s_' + key] || 'All';
    const statuses = ['All'].concat(Array.from(new Set(jobs.map(j => j.statusLabel || j.status))));
    const list = jobs.filter(j => (st === 'All' || (j.statusLabel || j.status) === st) && (!q || [j.id, j.orderId, j.customer, j.product].join(' ').toLowerCase().indexOf(q) >= 0));
    const rows = list.map(j => [
      h('span', { onClick: () => this.opsOpen('job', j), style: { font: '600 12px ui-monospace,Menlo,monospace', color: TEAL, cursor: 'pointer', whiteSpace: 'nowrap' } }, j.id),
      j.customer, j.product + ' × ' + (j.qty || 0).toLocaleString(), this.rm(j.price || 0),
      this.pillDot(j.statusLabel || j.status, j.status === 'completed' ? 'ok' : j.status === 'rejected' ? 'bad' : 'teal'),
      j.route === 'inhouse' ? 'In-house' : j.route === 'outsource' ? 'Outsourced' : '—',
      destText(j.destination), j.deadline ? when(j.deadline) : '—',
      h('span', { onClick: () => this.opsOpen('job', j), style: { color: TEAL, fontWeight: 600, cursor: 'pointer' } }, 'View')]);
    return [
      h('div', { key: 'f', style: { display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' } },
        h('input', { placeholder: 'Search job, order, customer, product', value: this.state['ol_q_' + key] || '', onChange: e => this.setField('ol_q_' + key, e.target.value), style: Object.assign({}, inp, { maxWidth: 340 }) }),
        h('select', { value: st, onChange: e => this.setField('ol_s_' + key, e.target.value), style: Object.assign({}, inp, { maxWidth: 260 }) }, statuses.map(s => h('option', { key: s, value: s }, s))),
        h('span', { style: { fontSize: 12.5, color: FAINT, marginLeft: 'auto' } }, list.length + ' of ' + jobs.length + ' jobs')),
      h('div', { key: 't' }, this.dataCard([{ label: 'Job' }, { label: 'Customer' }, { label: 'Product' }, { label: 'Value', right: true }, { label: 'Status' }, { label: 'Route' }, { label: 'Destination' }, { label: 'Due', nowrap: true }, { label: '' }], rows, { minWidth: 980, empty: 'No jobs match.' })),
    ];
  };
  // KPI table + daily chart for one department (computed on the server from the audit log)
  P.oKpi = function (dept, label) {
    const days = Number(this.state['kpiDays_' + dept] || 30);
    const k = (this.od('kpi_' + dept + '_' + days, '/api/ops/kpi?dept=' + dept + '&days=' + days) || {}).kpi;
    const me = (this.state.user || {}).name;
    const pick = h('select', { value: String(days), onChange: e => this.setField('kpiDays_' + dept, e.target.value), style: Object.assign({}, inp, { maxWidth: 150 }) }, [7, 30, 90, 365].map(d => h('option', { key: d, value: String(d) }, 'Last ' + d + ' days')));
    if (!k) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading KPI…')];
    const cols = { prepress: ['Files checked', 'Avg check time', 'Within SLA (30 min / 10 urgent)', 'Rejections'], scheduler: ['Jobs allocated', 'Avg time to allocate', 'On-time', '—'], production: ['Floor actions', 'Avg floor time', 'On-time', '—'], logistics: ['Actions', 'Avg ready → dispatch', 'On-time delivery', '—'], hub: ['Actions', 'Avg hub dwell', 'On-time', '—'] }[dept];
    const rows = (k.staff || []).map(s => [h('span', { style: { fontWeight: s.actor === me ? 700 : 500 } }, s.actor + (s.actor === me ? ' (you)' : '')), String(s.count), mins(s.avgMins), dept === 'prepress' ? pct(s.slaPct) : pct(s.onTimePct), dept === 'prepress' ? (s.rejects + ' (' + pct(s.rejectPct) + ')') : '']);
    return [
      h('div', { key: 'h', style: { display: 'flex', alignItems: 'flex-end', gap: 12, flexWrap: 'wrap' } }, title((label || 'KPI'), 'Computed from every recorded action — the first person to handle a job owns it. Nothing here is typed in by hand.'), h('span', { style: { marginLeft: 'auto' } }, pick)),
      this.opsStatGrid([
        [cols[0], k.actions, 'check', 'teal', 'last ' + days + ' days'],
        [cols[1], mins(k.avgMins), 'clock', 'orange', 'average'],
        [dept === 'prepress' ? 'Within SLA' : 'On-time', dept === 'prepress' ? pct(k.slaPct) : pct(k.onTimePct), 'layers', 'teal', dept === 'prepress' ? '≤30 min standard · ≤10 urgent' : 'before customer deadline'],
        ['In queue now', k.inQueue, 'box', k.overdue ? 'red' : 'teal', k.overdue ? k.overdue + ' overdue' : 'none overdue', null, k.overdue > 0],
      ]),
      box([h('div', { key: 'a', style: { fontSize: 13, fontWeight: 600, color: MUT, marginBottom: 8 } }, 'Daily ' + cols[0].toLowerCase()), h('div', { key: 'b' }, this.oBars(k.series || []))]),
      h('div', { key: 'tb' }, sub2('By staff member'), this.dataCard([{ label: 'Staff' }, { label: cols[0], right: true }, { label: cols[1], right: true }, { label: cols[2], right: true }, { label: cols[3] }], rows, { minWidth: 640, empty: 'No actions recorded in this period yet.' })),
    ];
  };

  // ---------------------------------------------------------------- modals (pop-ups)
  P.opsModalView = function () {
    const m = this.state.opsModal; if (!m) return null;
    const j = m.jobId ? (this.opsJobs().find(x => x.id === m.jobId) || (this.state.opsJob && this.state.opsJob.job)) : null;
    const close = () => this.setState({ opsModal: null, opsForm: {} });
    const F = this.state.opsForm || {}; const setF = (k, v) => this.setState(st => ({ opsForm: Object.assign({}, st.opsForm, { [k]: v }) }));
    const cfg = this.state.opsConfig || { hubs: [], outlets: [], machines: [], couriers: [] };
    const frame = (heading, body, footer, wide) => h('div', { key: 'opsm', onClick: close, style: { position: 'fixed', inset: 0, zIndex: 95, background: 'rgba(15,20,25,.5)', display: 'grid', placeItems: 'center', padding: 14, overflow: 'auto' } },
      h('div', { onClick: e => e.stopPropagation(), role: 'dialog', 'aria-label': heading, style: { background: '#fff', borderRadius: 14, width: '100%', maxWidth: wide ? 960 : 620, maxHeight: '92vh', overflow: 'auto', boxShadow: '0 24px 60px rgba(33,33,33,.3)' } },
        h('div', { style: { padding: '15px 20px', borderBottom: '1px solid ' + HAIR, display: 'flex', alignItems: 'center', gap: 10, position: 'sticky', top: 0, background: '#fff', zIndex: 1 } },
          j ? h('span', { style: { font: '600 12px ui-monospace,Menlo,monospace', color: TEAL } }, j.id) : null,
          h('span', { style: { fontSize: 15.5, fontWeight: 600 } }, heading),
          h('span', { onClick: close, role: 'button', 'aria-label': 'Close', style: { marginLeft: 'auto', color: FAINT, fontSize: 22, cursor: 'pointer' } }, '×')),
        h('div', { style: { padding: 20, display: 'flex', flexDirection: 'column', gap: 16 } }, body),
        footer ? h('div', { style: { padding: '13px 20px', borderTop: '1px solid ' + HAIR, display: 'flex', gap: 9, flexWrap: 'wrap', justifyContent: 'flex-end', position: 'sticky', bottom: 0, background: '#fff' } }, footer) : null));
    const destPicker = (defType) => {
      const t = F.destType || defType || 'customer';
      return [
        field('Deliver to', h('div', { style: { display: 'flex', gap: 8, flexWrap: 'wrap' } }, ['hub', 'outlet', 'customer'].map(x => h('span', { key: x, onClick: () => setF('destType', x), style: Object.assign(btnS(t === x ? 'dark' : 'ghost'), { fontWeight: 600 }) }, DEST_ICON[x] + ' ' + x[0].toUpperCase() + x.slice(1))))),
        t === 'hub' ? field('Hub', h('select', { value: F.destId || (j && j.hub) || '', onChange: e => setF('destId', e.target.value), style: inp }, cfg.hubs.map(x => h('option', { key: x.id, value: x.id }, x.name)))) : null,
        t === 'outlet' ? field('Outlet', h('select', { value: F.destId || (j && j.finalDestination && j.finalDestination.type === 'outlet' ? j.finalDestination.id : (cfg.outlets[0] || {}).id) || '', onChange: e => setF('destId', e.target.value), style: inp }, cfg.outlets.map(x => h('option', { key: x.id, value: x.id }, x.name)))) : null,
        t === 'customer' ? h('div', { style: { fontSize: 12.5, color: MUT, background: ALT, borderRadius: 8, padding: '9px 12px' } }, 'Customer address: ', h('b', null, (j && j.finalDestination && j.finalDestination.type === 'customer' ? (j.finalDestination.address || 'on the order') : 'the order’s delivery address'))) : null,
      ];
    };
    const destPayload = (defType) => { const t = F.destType || defType || 'customer'; return { destType: t, destId: F.destId || (t === 'hub' ? (j && j.hub) : t === 'outlet' ? (j && j.finalDestination && j.finalDestination.type === 'outlet' ? j.finalDestination.id : (cfg.outlets[0] || {}).id) : null) }; };

    // ---- Order details (Qn 750 "Order Details") ----
    if (m.kind === 'job') {
      const d = this.state.opsJob; const jj = (d && d.job) || j;
      if (!jj) return frame('Order details', [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')]);
      const o = d && d.order; const L = jj.label || {};
      const acts = dedupe((jj.actions || []).filter(a => a.permitted));
      const ship = (jj.shipments || []).map((s, i) => h('div', { key: i, style: { fontSize: 12.5, color: MUT, padding: '6px 0', borderTop: i ? '1px solid ' + LINE : 'none' } }, 'Leg ' + s.leg + ': ' + (s.from || '') + ' → ' + destText(s.to) + ' · ' + (s.courier || 'courier') + (s.tracking ? ' · ' + s.tracking : '') + ' · ' + when(s.at) + (s.receivedAt ? ' · received ' + when(s.receivedAt) : ' · in transit')));
      const audit = ((d && d.audit) || []).slice().reverse();
      return frame('Order details', [
        h('div', { key: 's', style: { display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' } }, this.chip(jj.statusLabel || jj.status, 'teal'), jj.route ? this.chip(jj.route === 'inhouse' ? 'In-house' : 'Outsourced', 'neutral') : null, o && o.progressLabel ? this.chip('Customer sees: ' + o.progressLabel, 'amber') : null,
          (jj.orderId && /^PO-/.test(jj.orderId)) ? h('span', { 'data-go': 'vieworder:' + jj.orderId, style: { marginLeft: 'auto', fontSize: 12.5, fontWeight: 600, color: TEAL, cursor: 'pointer' } }, 'Full order ' + jj.orderId + ' →') : null),
        kv([['Customer', jj.customer], ['Order', jj.orderId], ['Product', jj.product], ['Quantity', (jj.qty || 0).toLocaleString()], ['Value', this.rm(jj.price || 0)], ['Payment', jj.paymentValidated ? 'Confirmed' : jj.creditTerms ? 'Credit terms' : 'Pending'],
          ['Deadline', jj.deadline ? when(jj.deadline) : '—'], ['Artwork', jj.artwork && jj.artwork.file], ['Machine', jj.machine], ['Printer', jj.printer || (jj.outsource && jj.outsource.awardedTo ? (jj.outsource.vendors.find(v => v.vendorId === jj.outsource.awardedTo) || {}).vendorName : null)],
          ['Current destination', destText(jj.destination)], ['Final destination', destText(jj.finalDestination)], ['Assigned hub', jj.hub], ['Owner', jj.owner && Object.keys(jj.owner).map(k => k + ': ' + jj.owner[k]).join(' · ')]]),
        jj.spec ? h('div', { key: 'sp', style: { fontSize: 12.5, color: MUT, lineHeight: 1.6, background: ALT, borderRadius: 8, padding: '10px 12px' } }, jj.spec) : null,
        jj.instructions ? h('div', { key: 'in', style: { fontSize: 12.5, color: INK, background: '#fff8e6', border: '1px solid #f3e2b8', borderRadius: 8, padding: '10px 12px' } }, h('b', null, 'Delivery instructions: '), jj.instructions) : null,
        this.oLabel(L),
        ship.length ? h('div', { key: 'sh' }, sub2('Shipments'), ship) : null,
        h('div', { key: 'tl' }, sub2('Timeline'), audit.length ? audit.map((e, i) => h('div', { key: i, style: { display: 'grid', gridTemplateColumns: '120px minmax(0,1fr)', gap: 10, fontSize: 12.5, padding: '6px 0', borderTop: i ? '1px solid ' + LINE : 'none' } },
          h('span', { style: { color: FAINT } }, when(e.ts)), h('span', { style: { color: MUT } }, h('b', { style: { color: INK } }, e.actor), ' · ' + e.action.replace(/_/g, ' ') + (e.to ? ' → ' + e.to : '') + (e.note ? ' — ' + e.note : '')))) : h('div', { style: { fontSize: 12.5, color: FAINT } }, 'No actions yet.')),
      ], acts.map(a => B(this.oActLabel(a.action), () => this.opsAction(jj, a), a.enabled ? 'primary' : 'ghost', !a.enabled, a.enabled ? a.note : (a.blockedBy || []).join(' '))), true);
    }

    // ---- Qn 752 CF1: send to internal production with delivery instructions ----
    if (m.kind === 'send' && j) {
      const def = (j.finalDestination && j.finalDestination.type) || 'customer';
      const machine = F.machine || cfg.machines[0] || '';
      const go = () => this.opsFetch('/api/jobs/' + j.id + '/send-internal', Object.assign({ machine, instructions: F.instructions || '', parcels: F.parcels || 1 }, destPayload(def)))
        .then(d => { if (this.opsDone(d, j.id + ' sent to internal production — label ' + (d.job && d.job.label ? d.job.label.id : '') + ' ready.')) close(); });
      return frame('Send to internal production', [
        h('div', { key: 'i', style: { fontSize: 13, color: MUT, lineHeight: 1.6 } }, j.product + ' · qty ' + (j.qty || 0).toLocaleString() + ' for ' + j.customer + '. The order goes to the Printoka production floor with these delivery instructions; a shipping label and the assigned hub/outlet travel with it.'),
        field('Machine / production line', h('select', { value: machine, onChange: e => setF('machine', e.target.value), style: inp }, cfg.machines.map(x => h('option', { key: x, value: x }, x)))),
        destPicker(def),
        field('Parcels', h('input', { type: 'number', min: 1, value: F.parcels || 1, onChange: e => setF('parcels', e.target.value), style: Object.assign({}, inp, { maxWidth: 120 }) })),
        field('Delivery instructions', h('textarea', { rows: 3, value: F.instructions || '', onChange: e => setF('instructions', e.target.value), placeholder: 'e.g. Pack in 2 boxes, fragile, deliver before 5pm', style: Object.assign({}, inp, { resize: 'vertical' }) })),
      ], [B('Cancel', close, 'ghost'), B('Send to production', go, 'primary', !machine)]);
    }

    // ---- outsource progress form: request quotes → compare → award (incl. Qn 752 CF2) ----
    if (m.kind === 'outsource' && j) {
      const o = j.outsource; const vendors = this.state.vendors || [];
      const picked = F.vids || vendors.filter(v => !v.internal).map(v => v.id);
      const toggle = id => setF('vids', picked.indexOf(id) >= 0 ? picked.filter(x => x !== id) : picked.concat([id]));
      const best = o && o.vendors.filter(v => v.submittedAt).sort((a, b) => a.price - b.price)[0];
      const steps = [['Quotes requested', !!o], ['Quotes in', !!(o && o.vendors.some(v => v.submittedAt))], ['Awarded', !!(o && o.awardedTo)], ['Printer shipped', ['dispatched', 'at_hub', 'ready_collect', 'completed'].indexOf(j.status) >= 0], ['Received', ['at_hub', 'ready_collect', 'completed'].indexOf(j.status) >= 0]];
      const canDirect = /scheduler_manager|production_manager/.test(this.userRole()) || this.userType() === 'admin';
      return frame('Outsource order processing', [
        this.oStepper(steps),
        !o ? h('div', { key: 'rq' }, sub2('1 · Request quotes'),
          h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(220px,1fr))', gap: 8 } }, vendors.map(v => h('label', { key: v.id, style: { display: 'flex', gap: 8, alignItems: 'center', border: '1px solid ' + HAIR, borderRadius: 8, padding: '9px 11px', fontSize: 13, cursor: 'pointer' } }, h('input', { type: 'checkbox', checked: picked.indexOf(v.id) >= 0, onChange: () => toggle(v.id) }), v.name, v.internal ? this.chip('Internal', 'neutral') : null))),
          h('div', { style: { marginTop: 10 } }, B('Send quote request to ' + picked.length + ' printer' + (picked.length === 1 ? '' : 's'), () => this.opsFetch('/api/jobs/' + j.id + '/request-quotes', { vendorIds: picked }).then(d => this.opsDone(d, 'Quote requests sent.')), 'primary', !picked.length))) : null,
        o && !o.awardedTo ? h('div', { key: 'cmp' }, sub2('2 · Compare & award'),
          this.dataCard([{ label: 'Printer' }, { label: 'Price', right: true }, { label: 'Lead time' }, { label: '' }], o.vendors.map(v => [
            h('span', null, v.vendorName, best && v.vendorId === best.vendorId ? h('b', { style: { color: '#3d8b40', fontSize: 11, marginLeft: 6 } }, 'BEST') : null),
            v.submittedAt ? this.rm(v.price) : h('span', { style: { color: FAINT } }, 'no quote yet'), v.submittedAt ? v.leadDays + ' days' : '—',
            v.submittedAt || canDirect ? h('span', { onClick: () => this.opsOpen('award', j, { vendorId: v.vendorId, vendorName: v.vendorName, quoted: !!v.submittedAt, price: v.price }), style: { color: TEAL, fontWeight: 600, cursor: 'pointer' } }, 'Award') : '']), { minWidth: 520 })) : null,
        o && o.awardedTo ? h('div', { key: 'aw', style: { fontSize: 13, color: INK, background: '#e6f4ea', borderRadius: 8, padding: '10px 12px' } }, 'Awarded to ', h('b', null, (o.vendors.find(v => v.vendorId === o.awardedTo) || {}).vendorName), ' · ', o.po, o.direct ? ' · direct award (no quote)' : '', ' · ships to ', destText(j.destination)) : null,
        canDirect && !(o && o.awardedTo) ? h('div', { key: 'dir', style: { borderTop: '1px solid ' + LINE, paddingTop: 12 } }, sub2('Award directly (no quote)'),
          h('div', { style: { fontSize: 12.5, color: MUT, marginBottom: 8 } }, 'For internal production or an agreed printer: award the job even though no quote was submitted.'),
          h('div', { style: { display: 'flex', gap: 8, flexWrap: 'wrap' } }, h('select', { value: F.dv || '', onChange: e => setF('dv', e.target.value), style: Object.assign({}, inp, { maxWidth: 320 }) }, [h('option', { key: '', value: '' }, 'Choose a printer…')].concat(vendors.map(v => h('option', { key: v.id, value: v.id }, v.name + (v.internal ? ' (internal)' : ''))))),
            B('Award…', () => { const v = vendors.find(x => x.id === F.dv); if (v) this.opsOpen('award', j, { vendorId: v.id, vendorName: v.name, quoted: false }); }, 'dark', !F.dv))) : null,
      ], [B('Close', close, 'ghost')], true);
    }

    // ---- "Confirm Job Award" pop-up (Qn 752 CF2 checkbox when no quote) ----
    if (m.kind === 'award' && j) {
      const need = !m.quoted;
      const go = () => this.opsFetch('/api/jobs/' + j.id + '/award', Object.assign({ vendorId: m.vendorId, confirmNoQuote: !!F.confirm, price: F.price, leadDays: F.lead, instructions: F.instructions }, destPayload('hub')))
        .then(d => { if (this.opsDone(d, 'Job awarded to ' + m.vendorName + (d.job && d.job.outsource ? ' · ' + d.job.outsource.po : '') + '.')) close(); });
      return frame('Confirm Job Award', [
        h('div', { key: 'w', style: { fontSize: 13.5, color: INK } }, 'Award ', h('b', null, j.id + ' · ' + j.product), ' to ', h('b', null, m.vendorName), m.quoted ? ' at ' + this.rm(m.price) : ''),
        need ? h('div', { key: 'pl', style: { display: 'flex', gap: 10, flexWrap: 'wrap' } },
          field('Agreed price (RM, optional)', h('input', { type: 'number', value: F.price || '', onChange: e => setF('price', e.target.value), style: Object.assign({}, inp, { maxWidth: 170 }) })),
          field('Lead days (optional)', h('input', { type: 'number', value: F.lead || '', onChange: e => setF('lead', e.target.value), style: Object.assign({}, inp, { maxWidth: 140 }) }))) : null,
        destPicker('hub'),
        field('Instructions for the printer (optional)', h('textarea', { rows: 2, value: F.instructions || '', onChange: e => setF('instructions', e.target.value), style: Object.assign({}, inp, { resize: 'vertical' }) })),
        need ? h('label', { key: 'cb', style: { display: 'flex', gap: 10, alignItems: 'flex-start', fontSize: 13, color: '#8a4b00', background: '#fff8e6', border: '1px solid #f3e2b8', borderRadius: 8, padding: '11px 12px', cursor: 'pointer', lineHeight: 1.5 } },
          h('input', { type: 'checkbox', checked: !!F.confirm, onChange: e => setF('confirm', e.target.checked), style: { marginTop: 3 } }), 'This printer didn’t submit a quote yet. Please make sure it is internal production.') : null,
      ], [B('Cancel', close, 'ghost'), B('Confirm award', go, 'primary', need && !F.confirm)]);
    }

    // ---- interactive progress forms: in-house production · hub · logistics packing ----
    if (m.kind === 'progress' && j) {
      const G = {
        inhouse: { head: 'In-house order processing', steps: [['setup', 'Set-up / plate / RIP'], ['printing', 'Printing'], ['finishing', 'Finishing (cut, laminate, bind…)'], ['qc', 'Quality check']], done: 'finish', doneLabel: 'Send to logistics' },
        hub: { head: 'Hub interactive progress form', steps: [['checked', 'Parcel checked against the order'], ['qc', 'Quality check passed'], ['relabelled', 'Relabelled / repacked']], done: 'forward', doneLabel: 'Forward…' },
        logistics: { head: 'Logistics status update', steps: [['picked', 'Picked from production'], ['packed', 'Packed'], ['labelled', 'Shipping label attached']], done: 'dispatch', doneLabel: 'Dispatch…' },
      }[m.group];
      const prog = (j.progress && j.progress[m.group]) || {};
      const all = G.steps.every(s => prog[s[0]]);
      const ALLOW = { inhouse: ['production_staff', 'production_manager'], hub: ['hub_staff', 'hub_manager', 'hub'], logistics: ['logistics', 'logistics_manager'] }[m.group];
      const canTick = this.userType() === 'admin' || ALLOW.indexOf(this.userRole()) >= 0;
      const act = (j.actions || []).find(a => a.action === G.done);
      const next = () => G.done === 'finish' ? this.opsTransition(j.id, 'finish', {}, j.id + ' sent to logistics.').then(ok => ok && close()) : this.opsOpen('ship', j, { action: G.done });
      return frame(G.head, [
        this.oStepper(G.steps.map(s => [s[1], !!prog[s[0]]])),
        canTick ? null : h('div', { key: 'ro', style: { fontSize: 12.5, color: MUT, background: ALT, borderRadius: 8, padding: '9px 12px' } }, 'View only — this form is updated by the ' + ({ inhouse: 'production floor', hub: 'hub team', logistics: 'logistics team' })[m.group] + '.'),
        h('div', { key: 'st', style: { display: 'flex', flexDirection: 'column', gap: 8 } }, G.steps.map(s => { const v = prog[s[0]];
          return h('label', { key: s[0], style: { display: 'flex', gap: 12, alignItems: 'center', border: '1px solid ' + (v ? '#cfe8d4' : HAIR), background: v ? '#f3faf5' : '#fff', borderRadius: 10, padding: '12px 14px', cursor: canTick ? 'pointer' : 'default' } },
            h('input', { type: 'checkbox', checked: !!v, disabled: !canTick, onChange: e => this.opsStep(j.id, m.group, s[0], e.target.checked), style: { width: 18, height: 18 } }),
            h('span', { style: { flex: 1, fontSize: 13.5, fontWeight: 600 } }, s[1]),
            v ? h('span', { style: { fontSize: 11.5, color: FAINT } }, v.by + ' · ' + when(v.at)) : null); })),
        this.oLabel(j.label),
      ], [B('Close', close, 'ghost'), m.group !== 'inhouse' ? B('Print label', () => this.printLabel(j.label), 'ghost') : null, act ? B(G.doneLabel, next, 'primary', !all || !act.enabled, !all ? 'Tick every step first' : (act.blockedBy || []).join(' ')) : null]);
    }

    // ---- ship / dispatch / forward (courier + tracking; forward = relabel to final destination) ----
    if (m.kind === 'ship' && j) {
      const a = m.action; const couriers = cfg.couriers || [];
      const courier = F.courier || couriers[0] || '';
      const fwdDef = (j.finalDestination && j.finalDestination.type) || 'customer';
      const go = () => this.opsTransition(j.id, a, Object.assign({ courier, tracking: F.tracking || '' }, a === 'forward' ? destPayload(fwdDef) : {}), a === 'forward' ? 'Forwarded and relabelled.' : 'Dispatched.').then(ok => ok && close());
      return frame(a === 'forward' ? 'Forward from hub' : a === 'vendor_ship' ? 'Printer shipped' : 'Dispatch parcel', [
        h('div', { key: 'i', style: { fontSize: 13, color: MUT } }, j.product + ' · qty ' + (j.qty || 0).toLocaleString() + ' → ' + (a === 'forward' ? 'final destination' : destText(j.destination))),
        a === 'forward' ? destPicker(fwdDef) : null,
        field('Courier', couriers.length ? h('select', { value: courier, onChange: e => setF('courier', e.target.value), style: inp }, couriers.map(x => h('option', { key: x, value: x }, x))) : h('input', { value: F.courier || '', onChange: e => setF('courier', e.target.value), style: inp })),
        field('Tracking / AWB number', h('input', { value: F.tracking || '', onChange: e => setF('tracking', e.target.value), placeholder: 'optional for own van', style: inp })),
        a !== 'forward' ? this.oLabel(j.label) : null,
      ], [B('Cancel', close, 'ghost'), a !== 'forward' ? B('Print label', () => this.printLabel(j.label), 'ghost') : null, B(a === 'forward' ? 'Forward & relabel' : 'Confirm dispatch', go, 'primary', !courier)]);
    }

    // ---- rejected artwork: a corrected file came in ----
    if (m.kind === 'resubmit' && j) {
      const go = () => this.opsTransition(j.id, 'resubmit', { file: F.file }, 'Back in the prepress queue.').then(ok => ok && close());
      return frame('New artwork received', [
        h('div', { key: 'i', style: { fontSize: 13, color: MUT, lineHeight: 1.6 } }, 'Rejected for: ' + (j.reason || 'artwork issue') + '. Record the corrected file the customer sent — the job goes back to prepress for a fresh check.'),
        field('Corrected file name', h('input', { value: F.file || '', onChange: e => setF('file', e.target.value), placeholder: 'e.g. bizcard-final-v4.pdf', style: inp })),
      ], [B('Cancel', close, 'ghost'), B('Send back to prepress', go, 'primary', !F.file)]);
    }

    // ---- custom quote details + progress (Qn 750) ----
    if (m.kind === 'quote') {
      const q = (this.state.quotesList || []).find(x => x.id === m.quoteId); if (!q) return frame('Custom quote', [h('div', { key: 'x' }, 'Quote not found.')], [B('Close', close, 'ghost')]);
      const r = q.requirement || {};
      return frame('Custom quote details', [
        this.oStepper(this.oQuoteSteps(q)),
        kv([['Quote', q.id], ['Customer', q.customer && q.customer.name], ['Email', q.customer && q.customer.email], ['Phone', q.customer && q.customer.phone], ['Outlet', q.outlet], ['Product', r.product], ['Quantity', r.qty], ['Size', r.size], ['Material', r.material], ['Finishing', r.finishing], ['Price', q.price != null ? this.rm(q.price) : null], ['Lead time', q.leadDays ? q.leadDays + ' days' : null], ['Order', q.orderId]]),
        r.remarks || r.quoteData ? h('div', { key: 'rm', style: { whiteSpace: 'pre-wrap', fontSize: 12.5, color: MUT, background: ALT, borderRadius: 8, padding: '10px 12px' } }, r.quoteData || r.remarks) : null,
        h('div', { key: 'hi' }, sub2('History'), (q.history || []).slice().reverse().map((e, i) => h('div', { key: i, style: { fontSize: 12.5, color: MUT, padding: '5px 0', borderTop: i ? '1px solid ' + LINE : 'none' } }, when(e.ts) + ' · ' + (e.actor || '') + ' · ' + (e.action || '') + (e.price ? ' · ' + this.rm(e.price) : '') + (e.note ? ' — ' + e.note : '')))),
        this.oPrinterQuotes && ['admin', 'production'].indexOf(this.userType()) >= 0 && ['accepted', 'rejected', 'declined'].indexOf(q.status) < 0 ? this.oPrinterQuotes(q) : null,
      ], [B('Open quote PDF', () => this.openDoc(q.id, 'quote'), 'ghost'), B('Close', close, 'primary')], true);
    }
    return null;
  };
  // the shipping label that travels with every job
  P.oLabel = function (L) {
    if (!L || !L.id) return null;
    return h('div', { key: 'lbl', style: { border: '2px solid ' + INK, borderRadius: 10, overflow: 'hidden', maxWidth: 420 } },
      h('div', { style: { background: INK, color: '#fff', padding: '7px 12px', display: 'flex', justifyContent: 'space-between', fontSize: 11.5, fontWeight: 600 } }, h('span', null, 'SHIPPING LABEL'), h('span', { style: { fontFamily: 'ui-monospace,Menlo,monospace' } }, L.id)),
      h('div', { style: { padding: 12, display: 'flex', flexDirection: 'column', gap: 4, fontSize: 12.5 } },
        h('div', { style: { fontSize: 11, color: FAINT } }, 'FROM ' + (L.from || '')),
        h('div', { style: { fontSize: 15, fontWeight: 700 } }, (DEST_ICON[L.toType] || '') + ' ' + (L.toName || '')),
        L.toAddress ? h('div', { style: { color: MUT } }, L.toAddress) : null,
        h('div', { style: { color: MUT } }, 'Attn: ' + (L.attn || '') + (L.toPhone ? ' · ' + L.toPhone : '')),
        h('div', { style: { color: MUT } }, (L.product || '') + ' · qty ' + (L.qty || '') + ' · ' + (L.parcels || 1) + ' parcel(s)'),
        L.instructions ? h('div', { style: { color: '#8a4b00' } }, '⚠ ' + L.instructions) : null,
        h('div', { style: { display: 'flex', justifyContent: 'space-between', fontSize: 11, color: FAINT, borderTop: '1px dashed ' + HAIR, paddingTop: 6, marginTop: 4 } }, h('span', null, 'Order ' + (L.orderId || '')), h('span', null, L.hub ? 'Hub: ' + L.hub : '')),
        h('div', { style: { height: 30, background: 'repeating-linear-gradient(90deg,#111 0 2px,#fff 2px 4px,#111 4px 5px,#fff 5px 9px)' } })));
  };
  P.printLabel = function (L) {
    if (!L || typeof window === 'undefined') return;
    const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
    const w = window.open('', '_blank', 'width=480,height=640'); if (!w) return this.opsToastSet(true, 'Allow pop-ups to print the label.');
    w.document.write('<html><head><title>' + esc(L.id) + '</title><style>body{font:14px Montserrat,Arial,sans-serif;margin:18px}.l{border:3px solid #111;border-radius:8px;overflow:hidden;max-width:420px}.h{background:#111;color:#fff;padding:8px 12px;display:flex;justify-content:space-between;font-weight:700}.b{padding:14px;line-height:1.6}.to{font-size:20px;font-weight:800}.bar{height:40px;margin-top:10px;background:repeating-linear-gradient(90deg,#111 0 2px,#fff 2px 4px,#111 4px 5px,#fff 5px 9px)}</style></head><body><div class="l"><div class="h"><span>PRINTOKA SHIPPING LABEL</span><span>' + esc(L.id) + '</span></div><div class="b"><div>FROM ' + esc(L.from) + '</div><div class="to">' + esc(L.toName) + '</div><div>' + esc(L.toAddress) + '</div><div>Attn: ' + esc(L.attn) + ' ' + esc(L.toPhone) + '</div><div>' + esc(L.product) + ' · qty ' + esc(L.qty) + ' · ' + esc(L.parcels || 1) + ' parcel(s)</div>' + (L.instructions ? '<div><b>Instructions:</b> ' + esc(L.instructions) + '</div>' : '') + '<div>Order ' + esc(L.orderId) + ' · Job ' + esc(L.jobId) + (L.hub ? ' · Hub ' + esc(L.hub) : '') + '</div><div class="bar"></div></div></div><script>window.onload=function(){window.print()}<\/script></body></html>');
    w.document.close();
  };
  P.oQuoteSteps = function (q) {
    const S = q.status; const order = ['requested', 'amendment', 'priced', 'issued', 'reviewed', 'accepted'];
    const at = s => order.indexOf(S) >= order.indexOf(s) || S === 'accepted';
    return [['Requested', true], ['Priced & issued', at('issued') || !!q.price], ['Customer viewed', at('reviewed')], ['Accepted', S === 'accepted'], ['Order created', !!q.orderId]];
  };

  // ---------------------------------------------------------------- custom quotes board (progress form)
  P.oQuotes = function (canPrice) {
    const qs = this.state.quotesList || [];
    const rows = qs.slice().sort((a, b) => String(b.createdAt || '').localeCompare(String(a.createdAt || ''))).map(q => [
      h('span', { onClick: () => this.setState({ opsModal: { kind: 'quote', quoteId: q.id } }), style: { font: '600 12px ui-monospace,Menlo,monospace', color: TEAL, cursor: 'pointer', whiteSpace: 'nowrap' } }, q.id),
      (q.customer && q.customer.name) || '—', (q.requirement && q.requirement.product) || 'Custom job',
      h('div', { style: { minWidth: 380 } }, this.oStepper(this.oQuoteSteps(q))),
      q.price != null ? this.rm(q.price) : '—',
      h('span', { onClick: () => this.setState({ opsModal: { kind: 'quote', quoteId: q.id } }), style: { color: TEAL, fontWeight: 600, cursor: 'pointer' } }, 'Details')]);
    return [
      title('Custom quotes', 'Every custom quote from request to order — who priced it, whether the customer has seen it, and whether it became an order.'),
      canPrice ? this.schedulerQuotePanel() : null,
      h('div', { key: 'qb' }, sub2('Custom quote progress'), this.dataCard([{ label: 'Quote' }, { label: 'Customer' }, { label: 'Product' }, { label: 'Progress' }, { label: 'Price', right: true }, { label: '' }], rows, { minWidth: 980, empty: 'No custom quotes yet.' })),
    ];
  };

  // ---------------------------------------------------------------- sales & performance (manager)
  P.oSales = function () {
    const days = Number(this.state.salesDays || 30);
    const s = (this.od('sales_' + days, '/api/ops/sales?days=' + days) || {}).sales;
    const pick = h('select', { value: String(days), onChange: e => this.setField('salesDays', e.target.value), style: Object.assign({}, inp, { maxWidth: 150 }) }, [7, 30, 90, 365].map(d => h('option', { key: d, value: String(d) }, 'Last ' + d + ' days')));
    if (!s) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading sales…')];
    return [
      h('div', { key: 'h', style: { display: 'flex', alignItems: 'flex-end', gap: 12, flexWrap: 'wrap' } }, title('Sales data & details', 'Paid orders only (bank transfers count once validated). Totals include SST and delivery.'), h('span', { style: { marginLeft: 'auto' } }, pick)),
      this.opsStatGrid([
        ['Revenue', this.rm(s.revenue), 'dollar-sign', 'teal', 'last ' + days + ' days'],
        ['Orders', s.orders, 'file', 'orange', 'avg ' + this.rm(s.aov)],
        ['Today', this.rm(s.today.revenue), 'clock', 'teal', s.today.orders + ' orders'],
        ['Awaiting payment', this.rm(s.pendingPayment.value), 'layers', s.pendingPayment.orders ? 'red' : 'teal', s.pendingPayment.orders + ' orders to validate', null, s.pendingPayment.orders > 0],
      ]),
      box([h('div', { key: 'a', style: { fontSize: 13, fontWeight: 600, color: MUT } }, 'Revenue by month'), h('div', { key: 'b' }, this.lineChart(s.months.map(m => m.month), s.months.map(m => m.revenue), { h: 240 }))]),
      h('div', { key: 'bp' }, sub2('By product'), this.dataCard([{ label: 'Product' }, { label: 'Order lines', right: true }, { label: 'Quantity', right: true }, { label: 'Revenue', right: true }], s.byProduct.map(p => [p.product, String(p.lines), p.qty.toLocaleString(), this.rm(p.revenue)]), { minWidth: 560, empty: 'No paid orders in this period.' })),
      h('div', { key: 'bc' }, sub2('By channel'), this.dataCard([{ label: 'Channel' }, { label: 'Orders', right: true }, { label: 'Revenue', right: true }], s.byChannel.map(c => [c.channel, String(c.orders), this.rm(c.revenue)]), { minWidth: 420 })),
    ];
  };
  P.oPerformance = function () {
    const days = Number(this.state.salesDays || 30);
    const s = (this.od('sales_' + days, '/api/ops/sales?days=' + days) || {}).sales;
    if (!s) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading performance…')];
    const R = s.route; const tot = ['inhouse', 'outsource', 'unallocated'].reduce((a, k) => a + R[k].revenue, 0) || 1;
    return [
      title('Production sales performance', 'Job value by production route — in-house on our own floor vs outsourced to partner printers — with printer cost and margin (last ' + days + ' days).'),
      this.dataCard([{ label: 'Route' }, { label: 'Jobs', right: true }, { label: 'Job value', right: true }, { label: 'Share', right: true }, { label: 'Printer cost', right: true }, { label: 'Margin', right: true }],
        [['In-house', R.inhouse], ['Outsourced', R.outsource], ['Not yet allocated', R.unallocated]].map(r => [r[0], String(r[1].jobs), this.rm(r[1].revenue), Math.round(r[1].revenue / tot * 100) + '%', r[0] === 'Outsourced' ? this.rm(r[1].cost) : '—', r[0] === 'Outsourced' ? this.rm(r[1].margin) : '—']), { minWidth: 640 }),
      h('div', { key: 'k2', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(320px,1fr))', gap: 16 } },
        box(this.oKpiMini('scheduler', 'Scheduler — allocation')), box(this.oKpiMini('production', 'Production floor'))),
    ];
  };
  P.oKpiMini = function (dept, label) {
    const k = (this.od('kpi_' + dept + '_30', '/api/ops/kpi?dept=' + dept + '&days=30') || {}).kpi;
    if (!k) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    return [h('div', { key: 't', style: { fontSize: 14, fontWeight: 600, marginBottom: 8 } }, label),
      kv([['Actions (30 days)', String(k.actions)], ['Average time', mins(k.avgMins)], ['On-time', pct(k.onTimePct)], ['In queue now', String(k.inQueue)], ['Overdue', String(k.overdue)]])];
  };
  // ops settings (CMS): hubs, outlets, machines, couriers
  P.oSettings = function () {
    const c = this.state.opsConfig; if (!c) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading settings…')];
    const D = this.state.opsCfgDraft || { machines: c.machines.join('\n'), couriers: c.couriers.join('\n'), hubs: JSON.stringify(c.hubs.map(x => ({ id: x.id, name: x.name, address: x.address, phone: x.phone || '', states: x.states, countries: x.countries || [] })), null, 1), outlets: JSON.stringify(c.outlets, null, 1) };
    const setD = (k, v) => this.setState({ opsCfgDraft: Object.assign({}, D, { [k]: v }) });
    const save = () => { let hubs, outlets; try { hubs = JSON.parse(D.hubs); outlets = JSON.parse(D.outlets); } catch (e) { return this.opsToastSet(true, 'Hubs / outlets must be valid JSON.'); }
      this.opsFetch('/api/ops/config', { machines: D.machines.split('\n').map(x => x.trim()).filter(Boolean), couriers: D.couriers.split('\n').map(x => x.trim()).filter(Boolean), hubs, outlets })
        .then(d => { if (d.error) return this.opsToastSet(true, d.error); this.setState({ opsConfig: d.config, opsCfgDraft: null }); this.opsToastSet(false, 'Settings saved.'); }); };
    const ta = (k, rows) => h('textarea', { rows, value: D[k], onChange: e => setD(k, e.target.value), style: Object.assign({}, inp, { fontFamily: k === 'hubs' || k === 'outlets' ? 'ui-monospace,Menlo,monospace' : undefined, fontSize: 12.5, resize: 'vertical' }) });
    return [title('Operations settings', 'The lists every department picks from. Hubs decide which parcels route where (by state); outlets appear at checkout for self-pickup.'),
      h('div', { key: 'g', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 16 } },
        box([field('Machines / production lines (one per line)', ta('machines', 7))]), box([field('Couriers (one per line)', ta('couriers', 7))])),
      box([field('Hubs (id, name, address, phone, states and countries served)', ta('hubs', 12))]), box([field('Outlets (id, name, address, hub, pickup)', ta('outlets', 12))]),
      h('div', { key: 'b' }, B('Save settings', save, 'primary'))];
  };

  // ================================================================== PRODUCTION (floor + manager)
  P.s_production = function () {
    const mgr = this.userType() === 'admin' || /production_manager|scheduler_manager/.test(this.userRole());
    const tabs = mgr ? ['Dashboard', 'Floor', 'Orders', 'Sales', 'Performance', 'Custom quotes', 'Staff KPI', 'Settings'] : ['Dashboard', 'Floor', 'Orders', 'My KPI'];
    const tab = this.oTab(tabs), jobs = this.opsJobs();
    const floor = jobs.filter(j => j.status === 'printing');
    const ready = floor.filter(j => { const p = (j.progress && j.progress.inhouse) || {}; return ['setup', 'printing', 'finishing', 'qc'].every(k => p[k]); });
    const overdue = jobs.filter(j => j.deadline && Date.parse(j.deadline) < Date.now() && ['scheduling', 'printing', 'outsourcing'].indexOf(j.status) >= 0);
    const bar = j => { const p = (j.progress && j.progress.inhouse) || {}; const n = ['setup', 'printing', 'finishing', 'qc'].filter(k => p[k]).length;
      return h('div', { style: { display: 'flex', alignItems: 'center', gap: 8 } }, h('div', { style: { flex: 1, height: 6, borderRadius: 3, background: LINE, overflow: 'hidden' } }, h('div', { style: { width: (n / 4 * 100) + '%', height: '100%', background: n === 4 ? '#63AA02' : TEAL } })), h('span', { style: { fontSize: 11.5, color: FAINT } }, n + '/4'),
        B('Progress form', () => this.opsOpen('progress', j, { group: 'inhouse' }), 'ghost')); };
    let content;
    if (tab === 'Dashboard' && mgr) {
      const s = (this.od('sales_30', '/api/ops/sales?days=30') || {}).sales;
      content = [
        title('Production manager dashboard', 'Live across scheduling, the in-house floor and outsourced printers. Every figure comes from real orders and recorded actions.'),
        this.opsStatGrid([
          ['Revenue (30 days)', s ? this.rm(s.revenue) : '…', 'dollar-sign', 'teal', s ? s.orders + ' paid orders' : ''],
          ['Awaiting allocation', jobs.filter(j => j.status === 'scheduling').length, 'layers', 'orange', 'in the scheduler queue', null, false],
          ['On the floor', floor.length, 'printer', 'teal', ready.length + ' ready for logistics'],
          ['Outsourced', jobs.filter(j => j.status === 'outsourcing').length, 'truck', 'teal', 'with partner printers'],
          ['Overdue', overdue.length, 'clock', overdue.length ? 'red' : 'teal', 'past customer deadline', null, overdue.length > 0],
        ]),
        this.opsPipeline('scheduler'),
        s ? box([h('div', { key: 'a', style: { fontSize: 13, fontWeight: 600, color: MUT } }, 'Revenue by month'), h('div', { key: 'b' }, this.lineChart(s.months.map(m => m.month), s.months.map(m => m.revenue), { h: 220 }))]) : null,
        h('div', { key: 'od' }, sub2('Needs attention — overdue'), this.oGrid(overdue, 'Nothing overdue. 🎉')),
      ];
    } else if (tab === 'Dashboard') {
      content = [
        title('Production floor', 'Jobs sent to our own presses. Tick each step in the progress form as it happens; when all four are done, hand the job to logistics.'),
        this.opsStatGrid([['On the floor', floor.length, 'printer', 'teal', 'in production now'], ['Ready for logistics', ready.length, 'check', 'orange', 'all steps done'], ['Overdue', floor.filter(j => j.deadline && Date.parse(j.deadline) < Date.now()).length, 'clock', 'red', 'past deadline']]),
        this.oGrid(floor, 'Nothing on the floor right now.', bar),
        this.notifPanel(),
      ];
    } else if (tab === 'Floor') content = [title('In-house order processing', 'Interactive progress form per job: set-up → printing → finishing → quality check → send to logistics.'), this.oGrid(floor, 'Nothing on the floor right now.', bar)];
    else if (tab === 'Orders') content = [title('Order listing', 'Every job in the system. Open one for full order details, its shipping label and timeline.')].concat(this.oOrders(jobs, 'prod'));
    else if (tab === 'Sales') content = this.oSales();
    else if (tab === 'Performance') content = this.oPerformance();
    else if (tab === 'Custom quotes') content = this.oQuotes(false);
    else if (tab === 'Staff KPI') content = this.oKpi('production', 'Production staff KPI').concat(this.oKpi('scheduler', 'Scheduler staff KPI'));
    else if (tab === 'My KPI') content = this.oKpi('production', 'My KPI');
    else content = this.oSettings();
    return this.oPage('production', tabs, tab, this.oIdentity('Production'), content);
  };

  // ================================================================== SCHEDULER
  P.s_scheduler = function () {
    const mgr = this.userType() === 'admin' || /manager/.test(this.userRole());
    const tabs = ['Dashboard', 'Allocation queue', 'Outsourcing', 'Custom quotes', 'Orders'].concat(mgr ? ['KPI'] : ['My KPI']);
    const tab = this.oTab(tabs), jobs = this.opsJobs();
    const q = jobs.filter(j => j.status === 'scheduling');
    const outs = jobs.filter(j => j.outsource || j.status === 'outsourcing');
    const reqs = (this.state.quotesList || []).filter(x => x.status === 'requested' || x.status === 'amendment');
    const outExtra = j => { const o = j.outsource || {}; return this.oStepper([['Requested', !!j.outsource], ['Quotes in', (o.vendors || []).some(v => v.submittedAt)], ['Awarded', !!o.awardedTo], ['Shipped', ['dispatched', 'at_hub', 'ready_collect', 'completed'].indexOf(j.status) >= 0]]); };
    let content;
    if (tab === 'Dashboard') content = [
      title('Scheduler', 'Priority is set only by the customer’s deadline, then payment time. Send each job to our own floor or to the best-quoted printer.'),
      this.opsStatGrid([['Awaiting allocation', q.length, 'layers', 'teal', 'priority-sorted'], ['Outsourcing in progress', jobs.filter(j => j.status === 'outsourcing').length, 'truck', 'orange', 'with printers'], ['Quote requests', outs.filter(j => j.outsource && !j.outsource.awardedTo).length, 'edit-3', 'teal', 'awaiting printer prices'], ['Custom quotes to price', reqs.length, 'file', reqs.length ? 'red' : 'teal', 'from outlets', reqs.length ? 'New' : null, reqs.length > 0]]),
      this.opsPipeline('scheduler'), this.oGrid(q.slice(0, 6), 'Queue is clear.'), this.notifPanel()];
    else if (tab === 'Allocation queue') content = [title('Allocation queue', 'Send to internal production (with delivery instructions, label and assigned hub/outlet), or outsource.'), this.oGrid(q, 'Queue is clear.')];
    else if (tab === 'Outsourcing') content = [title('Outsource order processing', 'Request quotes → compare → award a PO → the printer ships with the Printoka label → hub/outlet receives.'), this.oGrid(outs, 'No outsourced jobs.', outExtra)];
    else if (tab === 'Custom quotes') content = this.oQuotes(true);
    else if (tab === 'Orders') content = [title('Order listing')].concat(this.oOrders(jobs, 'sch'));
    else content = this.oKpi('scheduler', tab === 'KPI' ? 'Scheduler KPI' : 'My KPI');
    return this.oPage('scheduler', tabs, tab, this.oIdentity('Scheduler'), content);
  };

  // ================================================================== PREPRESS
  P.s_prepress = function () {
    const tabs = ['Dashboard', 'Queue', 'Orders', 'KPI'];
    const tab = this.oTab(tabs), jobs = this.opsJobs();
    const q = jobs.filter(j => j.queue === 'prepress');
    const blocked = q.filter(j => (j.actions || []).some(a => a.action === 'approve' && !a.enabled)).length;
    const k = (this.od('kpi_prepress_30', '/api/ops/kpi?dept=prepress&days=30') || {}).kpi;
    let content;
    if (tab === 'Dashboard') content = [
      title('Prepress', 'Check every file (Basic → Technical → Content) within 30 minutes — 10 for urgent jobs. Approve, fix minor issues, reject with proof, or escalate.'),
      this.opsStatGrid([['In queue', q.length, 'layers', 'teal', 'oldest first'], ['Blocked', blocked, 'file', blocked ? 'red' : 'teal', 'artwork ≠ order', null, blocked > 0], ['Avg check time', k ? mins(k.avgMins) : '…', 'clock', 'orange', 'last 30 days'], ['Within SLA', k ? pct(k.slaPct) : '…', 'check', 'teal', '≤30 min / ≤10 urgent']]),
      this.opsPipeline('prepress'), this.oGrid(q, 'No files waiting.'), this.notifPanel()];
    else if (tab === 'Queue') content = [title('Prepress queue', 'Open a file to run the check and approve or reject it.'), this.oGrid(q, 'No files waiting.')];
    else if (tab === 'Orders') content = [title('Order listing', 'Jobs that have passed through prepress.')].concat(this.oOrders(jobs.filter(j => j.statusAt && (j.statusAt.prepress || j.statusAt.scheduling || j.statusAt.rejected) || j.queue === 'prepress'), 'pre'));
    else content = this.oKpi('prepress', 'Prepress KPI');
    return this.oPage('prepress', tabs, tab, this.oIdentity('Prepress'), content);
  };

  // ================================================================== LOGISTICS
  P.s_logistics = function () {
    const tabs = ['Dashboard', 'Ready to ship', 'In transit', 'Orders', 'KPI'];
    const tab = this.oTab(tabs), jobs = this.opsJobs();
    const ready = jobs.filter(j => j.status === 'logistics'), transit = jobs.filter(j => j.status === 'dispatched');
    const packBar = j => { const p = (j.progress && j.progress.logistics) || {}; const n = ['picked', 'packed', 'labelled'].filter(k => p[k]).length;
      return h('div', { style: { display: 'flex', gap: 8, alignItems: 'center' } }, h('span', { style: { fontSize: 12, color: MUT, flex: 1 } }, n + '/3 packing steps'), B('Update status', () => this.opsOpen('progress', j, { group: 'logistics' }), 'dark'), B('Label', () => this.printLabel(j.label), 'ghost')); };
    let content;
    if (tab === 'Dashboard') content = [
      title('Logistics', 'Pick, pack and label finished jobs, dispatch them to the customer, an outlet or a hub, and confirm delivery.'),
      this.opsStatGrid([['Ready to ship', ready.length, 'box', 'teal', 'from production'], ['In transit', transit.length, 'truck', 'orange', 'with couriers'], ['To customers', transit.filter(j => (j.destination || {}).type === 'customer').length, 'check', 'teal', 'awaiting delivery'], ['Inbound from printers', jobs.filter(j => j.status === 'outsourcing').length, 'layers', 'teal', 'outsourced jobs']]),
      this.opsPipeline('logistics'), this.oGrid(ready, 'Nothing waiting to ship.', packBar), this.notifPanel()];
    else if (tab === 'Ready to ship') content = [title('Logistics status update', 'Tick picked → packed → labelled, then dispatch with the courier and tracking number.'), this.oGrid(ready, 'Nothing waiting to ship.', packBar)];
    else if (tab === 'In transit') content = [title('In transit', 'Parcels on the road. Confirm delivery for customer parcels; hubs and outlets confirm their own receipts.'), this.oGrid(transit, 'Nothing in transit.', j => h('div', { style: { fontSize: 12, color: MUT } }, (j.courier || '') + (j.tracking ? ' · ' + j.tracking : '')))];
    else if (tab === 'Orders') content = [title('Order listing')].concat(this.oOrders(jobs.filter(j => j.statusAt && (j.statusAt.logistics || j.statusAt.dispatched)) , 'log'));
    else content = this.oKpi('logistics', 'Logistics KPI');
    return this.oPage('logistics', tabs, tab, this.oIdentity('Logistics'), content);
  };

  // ================================================================== HUB (Qn 732)
  P.s_hub = function () {
    const mgr = this.userType() === 'admin' || /hub_manager|production_manager/.test(this.userRole());
    const tabs = ['Dashboard', 'Inbound', 'At hub', 'Performance', 'Action tracker', 'Orders'];
    const tab = this.oTab(tabs), jobs = this.opsJobs();
    const myHub = (this.state.user || {}).hub || null;
    const hubName = myHub ? ((this.state.opsConfig && this.state.opsConfig.hubs.find(x => x.id === myHub)) || {}).name || myHub : 'All hubs';
    const inbound = jobs.filter(j => j.status === 'dispatched' && (j.destination || {}).type === 'hub');
    const at = jobs.filter(j => j.status === 'at_hub');
    const perf = (this.od('hubperf', '/api/ops/hub-performance?days=30') || {}).performance;
    const hubBar = j => { const p = (j.progress && j.progress.hub) || {}; const n = ['checked', 'qc', 'relabelled'].filter(k => p[k]).length;
      return h('div', { style: { display: 'flex', gap: 8, alignItems: 'center' } }, h('span', { style: { fontSize: 12, color: MUT, flex: 1 } }, n + '/3 steps · next: ' + destText(j.finalDestination)), B('Progress form', () => this.opsOpen('progress', j, { group: 'hub' }), 'dark')); };
    let content;
    if (tab === 'Dashboard') content = [
      title('Hub dashboard · ' + hubName, 'Receive parcels from our production floor and partner printers, check and relabel them, and forward each one to its outlet or customer.'),
      this.opsStatGrid([['Inbound', inbound.length, 'truck', 'orange', 'on the way to the hub'], ['At the hub', at.length, 'box', 'teal', 'to check & forward'], ['Processed today', perf ? perf.processed.today : '…', 'check', 'teal', perf ? perf.processed.month + ' this month' : ''], ['Avg time at hub', perf ? mins(perf.avgDwellMins) : '…', 'clock', 'teal', perf && perf.overdue ? perf.overdue + ' overdue' : 'receive → forward', null, !!(perf && perf.overdue)]]),
      h('div', { key: 'two', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(340px,1fr))', gap: 16, alignItems: 'start' } },
        h('div', null, sub2('Inbound'), this.oGrid(inbound, 'Nothing inbound.')), h('div', null, sub2('At the hub'), this.oGrid(at, 'Hub is clear.', hubBar))),
      this.notifPanel()];
    else if (tab === 'Inbound') content = [title('Inbound parcels', 'Receive a parcel when it arrives — it moves into the hub’s progress form.'), this.oGrid(inbound, 'Nothing inbound.', j => h('div', { style: { fontSize: 12, color: MUT } }, 'From ' + ((j.label && j.label.from) || '') + (j.courier ? ' · ' + j.courier : '') + (j.tracking ? ' · ' + j.tracking : '')))];
    else if (tab === 'At hub') content = [title('Hub interactive progress form', 'Checked → quality check → relabelled / repacked → forward to the outlet or customer.'), this.oGrid(at, 'Hub is clear.', hubBar)];
    else if (tab === 'Performance') {
      content = !perf ? [h('div', { key: 'l', style: { color: FAINT } }, 'Loading performance…')] : [
        title('Hub performance — total orders processed', 'Processed = forwarded on to the outlet or customer after the hub’s checks.'),
        this.opsStatGrid([['Today', perf.processed.today, 'check', 'teal', perf.received.today + ' received'], ['This week', perf.processed.week, 'layers', 'teal', perf.received.week + ' received'], ['This month', perf.processed.month, 'layers', 'orange', perf.received.month + ' received'], ['All time', perf.processed.all, 'box', 'teal', perf.received.all + ' received']]),
        box([h('div', { key: 'a', style: { fontSize: 13, fontWeight: 600, color: MUT } }, 'Orders processed per day (30 days)'), h('div', { key: 'b' }, this.oBars(perf.series))]),
      ].concat(this.oKpi('hub', 'Hub staff KPI'));
    } else if (tab === 'Action tracker') {
      const who = this.state.hubWho || '';
      const acts = (this.od('hubacts', '/api/ops/actions?dept=hub') || {}).actions || [];
      const people = Array.from(new Set(acts.map(a => a.actor)));
      const list = acts.filter(a => !who || a.actor === who);
      content = [title(mgr ? 'Hub manager / staff action tracker' : 'My actions', mgr ? 'Every receive, check and forward, by whom and when.' : 'Everything you’ve done at the hub.'),
        mgr ? h('select', { key: 'w', value: who, onChange: e => this.setField('hubWho', e.target.value), style: Object.assign({}, inp, { maxWidth: 260 }) }, [h('option', { key: '', value: '' }, 'All staff')].concat(people.map(p => h('option', { key: p, value: p }, p)))) : null,
        this.dataCard([{ label: 'When', nowrap: true }, { label: 'Staff' }, { label: 'Action' }, { label: 'Job' }, { label: 'Customer' }, { label: 'Detail' }],
          list.map(a => [when(a.ts), a.actor, a.action.replace(/_/g, ' '), h('span', { onClick: () => this.opsOpen('job', { id: a.jobId }), style: { font: '600 12px ui-monospace,Menlo,monospace', color: TEAL, cursor: 'pointer', whiteSpace: 'nowrap' } }, a.jobId), a.customer || '', a.note || '']), { minWidth: 820, empty: 'No hub actions yet.' })];
    } else content = [title('Order listing')].concat(this.oOrders(jobs.filter(j => (j.destination || {}).type === 'hub' || j.status === 'at_hub' || (j.shipments || []).some(s => s.to && s.to.type === 'hub')), 'hub'));
    return this.oPage('hub', tabs, tab, this.oIdentity('Hub'), content);
  };

  // ================================================================== OUTLET collections tab
  P.outletCollections = function () {
    const jobs = this.opsJobs();
    const inbound = jobs.filter(j => j.status === 'dispatched' && (j.destination || {}).type === 'outlet');
    const ready = jobs.filter(j => j.status === 'ready_collect'), rejected = jobs.filter(j => j.status === 'rejected');
    return [title('Collections & artwork fixes', 'Parcels coming to this outlet, orders waiting for the customer to collect, and rejected artwork waiting for a corrected file.'),
      h('div', { key: 'a' }, sub2('Ready for collection (' + ready.length + ')'), this.oGrid(ready, 'Nothing waiting for pickup.')),
      h('div', { key: 'b' }, sub2('On the way to this outlet (' + inbound.length + ')'), this.oGrid(inbound, 'Nothing inbound.')),
      h('div', { key: 'c' }, sub2('Artwork rejected — contact the customer (' + rejected.length + ')'), this.oGrid(rejected, 'No rejected artwork.', j => h('div', { style: { fontSize: 12, color: '#8c1c13' } }, 'Reason: ' + (j.reason || '—')))),
      this.opsModalView(), this.oToast()];
  };

  // ================================================================== PRINTER portal (staff / manager)
  P.s_vendor = function () {
    const u = this.state.user || {};
    const isStaff = u.role === 'printer_staff';
    const co = u.vendorId || u.id;
    const jobs = this.state.vendorJobs || [];
    const mine = j => (j.outsource && j.outsource.vendors.find(v => v.vendorId === co)) || {};
    const requests = jobs.filter(j => j.outsource && !j.outsource.awardedTo);
    const awarded = jobs.filter(j => j.outsource && j.outsource.awardedTo === co);
    const toShip = awarded.filter(j => j.status === 'outsourcing'), shipped = awarded.filter(j => j.status !== 'outsourcing');
    const tabs = ['Dashboard', 'Quote requests', 'Awarded jobs', 'Shipped'];
    const tab = this.oTab(tabs);
    const pending = requests.filter(j => !mine(j).submittedAt).length;
    const ship = j => this.opsFetch('/api/vendor/jobs/' + j.id + '/ship', { courier: this.state['vs_c_' + j.id] || '', tracking: this.state['vs_t_' + j.id] || '' })
      .then(d => { if (d.error) return this.opsToastSet(true, d.error); this.opsToastSet(false, j.id + ' marked shipped.'); this.loadVendorRequests(); });
    const reqCard = j => { const me = mine(j); const sent = !!me.submittedAt;
      return h('div', { key: j.id, style: { border: '1px solid ' + HAIR, borderRadius: 12, padding: 16, background: '#fff', display: 'flex', flexDirection: 'column', gap: 9 } },
        h('div', { style: { display: 'flex', justifyContent: 'space-between' } }, h('span', { style: { font: '600 12px ui-monospace,Menlo,monospace', color: TEAL } }, j.id), this.chip(sent ? 'Quote submitted' : 'Awaiting quote', sent ? 'ok' : 'warn')),
        h('div', { style: { fontSize: 14.5, fontWeight: 600 } }, j.product), h('div', { style: { fontSize: 12.5, color: MUT } }, (j.spec || '') + ' · qty ' + (j.qty || 0).toLocaleString()),
        sent ? h('div', { style: { fontSize: 13, background: ALT, borderRadius: 8, padding: '9px 11px' } }, 'Your quote: ', h('b', null, this.rm(me.price)), ' · ' + me.leadDays + ' days')
          : isStaff ? h('div', { style: { fontSize: 12.5, color: FAINT } }, 'Your printer manager submits the price for this job.')
          : h('div', { style: { display: 'flex', flexDirection: 'column', gap: 7 } },
            h('div', { style: { display: 'flex', gap: 7 } }, h('input', { type: 'number', placeholder: 'Price (RM)', value: this.state['vq_' + j.id + '_price'] || '', onChange: e => this.setField('vq_' + j.id + '_price', e.target.value), style: inp }), h('input', { type: 'number', placeholder: 'Lead days', value: this.state['vq_' + j.id + '_lead'] || '', onChange: e => this.setField('vq_' + j.id + '_lead', e.target.value), style: inp })),
            h('input', { placeholder: 'Note (optional)', value: this.state['vq_' + j.id + '_note'] || '', onChange: e => this.setField('vq_' + j.id + '_note', e.target.value), style: inp }),
            B('Submit quote', () => this.vendorSubmitQuote(j.id), 'primary'))); };
    const awCard = j => h('div', { key: j.id, style: { display: 'flex', flexDirection: 'column', gap: 10 } },
      this.oLabel(j.label || (j.outsource && j.outsource.label)),
      h('div', { style: { fontSize: 12.5, color: MUT } }, 'PO ' + (j.outsource.po || '') + ' · ' + j.product + ' · qty ' + (j.qty || 0).toLocaleString()),
      j.status === 'outsourcing' ? h('div', { style: { display: 'flex', gap: 7, flexWrap: 'wrap' } },
        h('input', { placeholder: 'Courier', value: this.state['vs_c_' + j.id] || '', onChange: e => this.setField('vs_c_' + j.id, e.target.value), style: Object.assign({}, inp, { flex: '1 1 130px' }) }),
        h('input', { placeholder: 'Tracking no.', value: this.state['vs_t_' + j.id] || '', onChange: e => this.setField('vs_t_' + j.id, e.target.value), style: Object.assign({}, inp, { flex: '1 1 130px' }) }),
        B('Print label', () => this.printLabel(j.label), 'ghost'), B('Mark shipped', () => ship(j), 'primary', !this.state['vs_c_' + j.id]))
        : this.chip('Shipped' + (j.tracking ? ' · ' + j.tracking : ''), 'ok'));
    const grid = (list, fn, empty) => list.length ? h('div', { key: 'g', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(320px,1fr))', gap: 16 } }, list.map(fn)) : h('div', { key: 'e', style: { border: '1px dashed ' + HAIR, borderRadius: 12, padding: 30, textAlign: 'center', color: FAINT, background: '#fff' } }, empty);
    let content;
    if (tab === 'Dashboard') content = [title(u.name || 'Printer', isStaff ? 'Print staff — ship awarded jobs with the Printoka label.' : 'Printer manager — quote on jobs, win POs and ship with the Printoka label.'),
      this.opsStatGrid([['Quote requests', pending, 'edit-3', 'teal', 'awaiting your price', pending ? 'New' : null, pending > 0], ['To print & ship', toShip.length, 'box', 'orange', 'awarded to you'], ['Shipped', shipped.length, 'truck', 'teal', 'on the way / delivered']]), this.notifPanel()];
    else if (tab === 'Quote requests') content = [title('Quote requests'), grid(requests, reqCard, 'No open quote requests.')];
    else if (tab === 'Awarded jobs') content = [title('Awarded jobs', 'Print the Printoka shipping label, stick it on the parcel and mark it shipped with the courier and tracking number.'), grid(toShip, awCard, 'No jobs to ship right now.')];
    else content = [title('Shipped'), grid(shipped, awCard, 'Nothing shipped yet.')];
    return this.staffPage(tabs, tab, { title: u.name || 'Printer', sub: isStaff ? 'Printer staff' : 'Printer manager' }, content.concat([this.oToast()]));
  };
})();
