/*
 * Admin backoffice sections that replace the WordPress / WooCommerce admin — mixed into the app
 * after app.js. Each section is live on the server (server/admin.js) and audit-logged.
 *
 *   Store    Analytics · Orders (status, notes, refunds, address, resend) · Customers (edit, tier,
 *            wallet, login-as-user) · Coupons · Users & roles (all staff types)
 *   General  Posts · FAQs · Media library (upload / delete)
 *   Setting  Membership tiers · Tax & currency (Country) · Payments · Shipping · Couriers & outlets ·
 *            Wallet top-ups · Pricing (engine)
 * Plus the storefront commerce helpers (tier discount, tax, shipping, currency) now read the same
 * settings the server re-checks at checkout.
 */
(function () {
  const C = window.PKComponent; if (!C) return;
  const P = C.prototype;

  // ---------------------------------------------------------------- storefront commerce from settings
  const S = self => (self.state.settings || {});
  P.tier = function () { return (this.state.user && this.state.user.type === 'customer' && this.state.user.tier) || 'Standard'; };
  P.tierPct = function () { const tiers = (S(this).membership && S(this).membership.tiers) || [{ name: 'Standard', pct: 0 }, { name: 'Bronze', pct: 5 }, { name: 'Silver', pct: 8 }, { name: 'Gold', pct: 10 }, { name: 'Platinum', pct: 15 }]; const t = tiers.find(x => x.name === this.tier()); return t ? Number(t.pct) || 0 : 0; };
  P.taxRate = function () { const t = (S(this).tax || {})[this.cc()]; return t ? (Number(t.rate) || 0) / 100 : ({ MY: 0.08, SG: 0.09, BN: 0 })[this.cc()] || 0; };
  P.taxLabel = function () { const t = (S(this).tax || {})[this.cc()]; if (!t) return ({ MY: 'SST 8%', SG: 'GST 9%', BN: 'No sales tax' })[this.cc()]; return Number(t.rate) ? t.label + ' ' + t.rate + '%' : 'No sales tax'; };
  P.shipFee = function (sub) { const sh = S(this).shipping || { flat: 12 }; const free = Number(sh.freeOver) || 0; return free && sub >= free ? 0 : (Number(sh.flat) || 0); };
  P.fx = function () { const c = S(this).currency || {}; return Number(c[this.cc()]) || ({ MY: 1, SG: 0.31, BN: 0.31 })[this.cc()] || 1; };

  // ---------------------------------------------------------------- login-as-user banner (WP "Login as User")
  const origRender = P.renderScreen;
  P.renderScreen = function () {
    const el = origRender.call(this);
    let back = null; try { back = localStorage.getItem('pk_admin_return'); } catch (e) {}
    if (!back || !this.state.user) return el;
    const ret = () => { try { localStorage.setItem('pk_token', back); localStorage.removeItem('pk_admin_return'); } catch (e) {} window.location.href = '/'; };
    return h('div', null, h('div', { style: { background: '#fff8e6', borderBottom: '1px solid #f3e2b8', color: '#8a4b00', fontSize: 13, padding: '8px 16px', display: 'flex', gap: 12, alignItems: 'center', justifyContent: 'center', flexWrap: 'wrap' } },
      'You are viewing the site as ', h('b', null, this.state.user.name + ' (' + this.state.user.email + ')'), h('span', { onClick: ret, style: { fontWeight: 700, textDecoration: 'underline', cursor: 'pointer' } }, 'Return to admin')), el);
  };

  // ---------------------------------------------------------------- helpers
  const inp = { font: '400 13.5px Montserrat,sans-serif', padding: '9px 11px', border: '1px solid ' + HAIR, borderRadius: 8, width: '100%', background: '#fff' };
  const B = (label, onClick, kind, disabled) => h('button', { type: 'button', disabled: !!disabled, onClick: disabled ? undefined : onClick, style: { font: '600 13px Montserrat,sans-serif', padding: '9px 15px', borderRadius: 8, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? .5 : 1, border: '1px solid ' + (kind === 'primary' ? TEAL : kind === 'danger' ? '#f5c8c7' : HAIR), background: kind === 'primary' ? TEAL : '#fff', color: kind === 'primary' ? '#fff' : kind === 'danger' ? '#c71917' : INK, whiteSpace: 'nowrap' } }, label);
  const F = (label, control, hint) => h('label', { style: { display: 'flex', flexDirection: 'column', gap: 5, fontSize: 12.5, fontWeight: 600, color: INK, minWidth: 0 } }, label, control, hint ? h('span', { style: { fontSize: 11.5, fontWeight: 400, color: FAINT } }, hint) : null);
  const grid = (children, min) => h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(' + (min || 200) + 'px,1fr))', gap: 12 } }, children);
  const box = (children, extra) => h('div', { style: Object.assign({ background: '#fff', border: '1px solid ' + HAIR, borderRadius: 12, padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }, extra || {}) }, children);
  const para = t => h('p', { style: { fontSize: 13.5, color: MUT, lineHeight: 1.7, margin: 0, maxWidth: '86ch' } }, t);
  const when = ts => ts ? String(ts).slice(0, 16).replace('T', ' ') : '—';
  P.aFetch = function (url, body) {
    const opt = { headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()) };
    if (body !== undefined) { opt.method = 'POST'; opt.body = JSON.stringify(body || {}); }
    return fetch(url, opt).then(r => r.json().then(d => (r.ok ? d : Object.assign({ error: d.error || 'Request failed' }, d)))).catch(() => ({ error: 'Network error' }));
  };
  P.aMsg = function (d, ok) { if (!d || d.error) { this.setState({ aMsg: { bad: true, text: (d && d.error) || 'Something went wrong.' } }); return false; } if (ok) this.setState({ aMsg: { bad: false, text: ok } }); return true; };
  P.aToast = function () { const m = this.state.aMsg; if (!m) return null; return h('div', { key: 'am', role: 'status', style: { fontSize: 13, borderRadius: 8, padding: '10px 12px', background: m.bad ? '#fdecec' : '#e6f4ea', color: m.bad ? '#8c1c13' : '#1f5e2a', border: '1px solid ' + (m.bad ? '#f5c8c7' : '#cfe8d4'), display: 'flex', gap: 10 } }, h('span', { style: { flex: 1 } }, m.text), h('span', { onClick: () => this.setState({ aMsg: null }), style: { cursor: 'pointer', fontWeight: 700 } }, '×')); };
  P.aGet = function (key, url) { this._ad = this._ad || {}; const c = this._ad[key]; if (c && c.data) return c.data; if (!c) { this._ad[key] = { loading: true }; setTimeout(() => this.aFetch(url).then(d => { this._ad[key] = { data: d }; this.forceUpdate(); }), 0); } return null; };
  P.aDrop = function (key) { if (this._ad) delete this._ad[key]; };
  P.aSettingsSave = function (patch, msg) { return this.aFetch('/api/settings', patch).then(d => { if (this.aMsg(d, msg || 'Saved.')) this.setState({ settings: d.settings }); }); };

  // ---------------------------------------------------------------- section router (called by s_admin)
  P.adminSection = function (tab) {
    const f = { analytics: this.aAnalytics, orders: this.aOrders, customers: this.aCustomers, users: this.aUsers, vouchers: this.aCoupons, membership: this.aMembership, tax: this.aTax, gateways: this.aPayments,
      couriers: this.aOps, outlets: this.aOps, posts: this.aPosts, faqs: this.aFaqs, media: this.aMedia, wallet: this.aWallet, pricing: this.aPricing, printing: this.aPrinting }[tab];
    if (!f) return null;
    try { return [this.aToast()].concat(f.call(this) || []); } catch (e) { return [h('div', { key: 'err', style: { color: '#c0392b' } }, 'This section failed to render: ' + e.message)]; }
  };

  // ---------------------------------------------------------------- Analytics (WooCommerce Reports)
  P.aAnalytics = function () {
    const days = Number(this.state.anDays || 30);
    const a = (this.aGet('an_' + days, '/api/admin/analytics?days=' + days) || {}).analytics;
    if (!a) return [para('Loading live figures…')];
    const delta = (c, p) => p ? ((c - p) / p * 100 >= 0 ? '+' : '') + Math.round((c - p) / p * 100) + '% vs previous ' + days + ' days' : 'no previous data';
    const maxT = Math.max(1, Math.max.apply(null, a.tiers.map(t => t.count)));
    return [
      h('div', { key: 'r', style: { display: 'flex', justifyContent: 'flex-end' } }, h('select', { value: String(days), onChange: e => this.setField('anDays', e.target.value), style: Object.assign({}, inp, { maxWidth: 170 }) }, [7, 30, 90, 365].map(d => h('option', { key: d, value: String(d) }, 'Last ' + d + ' days')))),
      h('div', { key: 'k', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 14 } },
        this.kpi('Revenue', this.rm(a.revenue), delta(a.revenue, a.revenuePrev), TEAL), this.kpi('Paid orders', String(a.orders), delta(a.orders, a.ordersPrev)),
        this.kpi('Avg. order value', this.rm(a.aov), 'paid orders only'), this.kpi('New customers', String(a.newCustomers), a.customers + ' in total'),
        this.kpi('Awaiting payment', this.rm(a.pendingPayments.value), a.pendingPayments.count + ' orders to validate'), this.kpi('Wallet credit owed', this.rm(a.walletLiability), 'outstanding customer credit'),
        this.kpi('Open custom quotes', String(a.quotes.open), a.quotes.accepted + ' accepted in period'), this.kpi('Refunds', this.rm(a.refunds), 'in period')),
      h('div', { key: 'g', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 16 } },
        box([h('div', { key: 't', style: { fontSize: 13.5, fontWeight: 600 } }, 'Customers by membership tier')].concat(a.tiers.map(t => h('div', { key: t.name, style: { display: 'flex', alignItems: 'center', gap: 10 } },
          h('span', { style: { width: 72, fontSize: 12.5, color: MUT } }, t.name), h('span', { style: { flex: 1, height: 8, background: LINE, borderRadius: 999, overflow: 'hidden' } }, h('span', { style: { display: 'block', height: '100%', width: (t.count / maxT * 100) + '%', background: TEAL } })), h('span', { style: { width: 30, textAlign: 'right', fontSize: 12, fontWeight: 600 } }, String(t.count)))))),
        box([h('div', { key: 't', style: { fontSize: 13.5, fontWeight: 600 } }, 'Top products')].concat(a.topProducts.length ? a.topProducts.map((p, i) => h('div', { key: i, style: { display: 'flex', justifyContent: 'space-between', fontSize: 13, borderTop: i ? '1px solid ' + LINE : 'none', paddingTop: i ? 8 : 0 } }, h('span', null, p.product), h('b', null, this.rm(p.revenue)))) : [h('div', { key: 'e', style: { fontSize: 13, color: FAINT } }, 'No paid orders in this period.')])),
        box([h('div', { key: 't', style: { fontSize: 13.5, fontWeight: 600 } }, 'By channel')].concat(a.channels.length ? a.channels.map((c, i) => h('div', { key: i, style: { display: 'flex', justifyContent: 'space-between', fontSize: 13 } }, h('span', null, c.channel + ' · ' + c.orders + ' orders'), h('b', null, this.rm(c.revenue)))) : [h('div', { key: 'e', style: { fontSize: 13, color: FAINT } }, 'No orders.')]))),
    ];
  };

  // ---------------------------------------------------------------- Orders (WooCommerce order screen)
  P.aOrders = function () {
    const all = this.state.admOrders || [];
    const q = String(this.state.aoQ || '').toLowerCase(), st = this.state.aoS || 'all';
    const stOf = o => o.status === 'cancelled' ? 'cancelled' : o.status === 'refunded' ? 'refunded' : (o.payment && o.payment.status !== 'validated') ? 'pending_payment' : (o.progress || 'received');
    const LAB = { all: 'All', pending_payment: 'Pending payment', artwork_check: 'Artwork check', action_required: 'Action needed', in_production: 'In production', shipped: 'Shipped', ready_for_collection: 'Ready for collection', completed: 'Completed', cancelled: 'Cancelled', refunded: 'Refunded', received: 'Received' };
    const list = all.filter(o => (st === 'all' || stOf(o) === st) && (!q || [o.id, o.customer && o.customer.name, o.customer && o.customer.email].join(' ').toLowerCase().indexOf(q) >= 0));
    const sel = this.state.aoSel ? all.find(o => o.id === this.state.aoSel) : null;
    const counts = {}; all.forEach(o => { const k = stOf(o); counts[k] = (counts[k] || 0) + 1; });
    return [
      h('div', { key: 'st', style: { display: 'flex', gap: 6, flexWrap: 'wrap' } }, ['all'].concat(Object.keys(counts)).map(k => h('span', { key: k, onClick: () => this.setState({ aoS: k }), style: { fontSize: 12.5, fontWeight: 600, padding: '6px 12px', borderRadius: 999, cursor: 'pointer', border: '1px solid ' + (st === k ? INK : HAIR), background: st === k ? INK : '#fff', color: st === k ? '#fff' : MUT } }, (LAB[k] || k) + ' (' + (k === 'all' ? all.length : counts[k]) + ')'))),
      h('input', { key: 'q', placeholder: 'Search order number, customer name or email', value: this.state.aoQ || '', onChange: e => this.setField('aoQ', e.target.value), style: Object.assign({}, inp, { maxWidth: 380 }) }),
      sel ? this.aOrderPanel(sel) : null,
      this.table(['Order', 'Date', 'Customer', 'Total', 'Payment', 'Status', ''],
        list.length ? list.slice(0, 100).map(o => [
          h('span', { onClick: () => this.setState({ aoSel: o.id, aMsg: null }), style: { color: TEAL, fontWeight: 600, cursor: 'pointer', fontFamily: 'ui-monospace,Menlo,monospace', fontSize: 12 } }, o.id),
          (o.createdAt || '').slice(0, 10), (o.customer && o.customer.name) || '—', this.rm(o.total),
          this.chip(o.payment && o.payment.status === 'validated' ? 'Paid' : 'Pending', o.payment && o.payment.status === 'validated' ? 'ok' : 'warn'),
          this.chip(LAB[stOf(o)] || stOf(o), stOf(o) === 'cancelled' || stOf(o) === 'action_required' ? 'bad' : stOf(o) === 'completed' ? 'ok' : 'neutral'),
          h('span', { onClick: () => this.setState({ aoSel: o.id, aMsg: null }), style: { color: TEAL, fontWeight: 600, cursor: 'pointer' } }, 'Manage')]) : [['—', 'No orders match', '', '', '', '', '']],
        ['150px', '100px', null, '110px', '90px', '150px', '80px']),
    ];
  };
  P.aOrderPanel = function (o) {
    const act = (path, body, ok) => this.aFetch('/api/admin/orders/' + o.id + '/' + path, body).then(d => { if (this.aMsg(d, ok)) this.loadAdmin(); });
    const refunded = (o.refunds || []).reduce((s, x) => s + x.amount, 0);
    const paid = o.payment && o.payment.status === 'validated';
    const addr = a => !a ? '—' : typeof a === 'string' ? a : [a.name, a.line1, a.line2, a.postcode + ' ' + a.city, a.state, a.country].filter(Boolean).join(', ');
    return box([
      h('div', { key: 'h', style: { display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' } }, h('b', { style: { fontSize: 16 } }, 'Order ' + o.id), this.chip(paid ? 'Paid' : 'Pending payment', paid ? 'ok' : 'warn'), o.progressLabel ? this.chip(o.progressLabel, 'neutral') : null, o.status === 'cancelled' ? this.chip('Cancelled', 'bad') : null,
        h('span', { style: { marginLeft: 'auto', display: 'flex', gap: 8, flexWrap: 'wrap' } }, h('span', { 'data-go': 'vieworder:' + o.id, style: { fontSize: 13, fontWeight: 600, color: TEAL, cursor: 'pointer' } }, 'Full order view →'), h('span', { onClick: () => this.setState({ aoSel: null }), style: { fontSize: 18, cursor: 'pointer', color: FAINT } }, '×'))),
      grid([
        box([h('b', { key: 't', style: { fontSize: 13 } }, 'Customer'), h('div', { key: 'c', style: { fontSize: 13, color: MUT, lineHeight: 1.6 } }, ((o.customer && o.customer.name) || '—') + ' · ' + ((o.customer && o.customer.email) || '') + ' · ' + ((o.customer && o.customer.phone) || '')), h('div', { key: 'b', style: { fontSize: 12.5, color: MUT } }, h('b', null, 'Billing: '), addr(o.billing)), h('div', { key: 's', style: { fontSize: 12.5, color: MUT } }, h('b', null, 'Ship to: '), o.fulfillment && o.fulfillment.method === 'pickup' ? 'Self-pickup · ' + (o.fulfillment.outlet || '') : addr(o.shipTo))]),
        box([h('b', { key: 't', style: { fontSize: 13 } }, 'Totals'), h('div', { key: 'x', style: { fontSize: 13, color: MUT, lineHeight: 1.8 } }, 'Subtotal ' + this.rm(o.subtotal), h('br'), 'Member discount −' + this.rm(o.memberDiscount || 0), o.couponDiscount ? [h('br', { key: 'b1' }), 'Code ' + o.coupon + ' −' + this.rm(o.couponDiscount)] : null, h('br'), 'Tax ' + this.rm(o.tax || 0) + ' · Delivery ' + this.rm(o.shipping || 0), h('br'), h('b', { style: { color: INK } }, 'Total ' + this.rm(o.total)), refunded ? [h('br', { key: 'b2' }), h('span', { key: 'rf', style: { color: '#c71917' } }, 'Refunded ' + this.rm(refunded))] : null)]),
      ], 260),
      grid([
        box([h('b', { key: 't', style: { fontSize: 13 } }, 'Add note'), h('textarea', { key: 'n', rows: 3, value: this.state.aoNote || '', onChange: e => this.setField('aoNote', e.target.value), placeholder: 'Private note, or a note to the customer', style: Object.assign({}, inp, { resize: 'vertical' }) }),
          h('label', { key: 'c', style: { display: 'flex', gap: 8, fontSize: 12.5, color: MUT } }, h('input', { type: 'checkbox', checked: !!this.state.aoNoteCust, onChange: e => this.setField('aoNoteCust', e.target.checked) }), 'Send to the customer (in-app + email)'),
          h('div', { key: 'b' }, B('Add note', () => act('note', { text: this.state.aoNote, toCustomer: !!this.state.aoNoteCust }, 'Note added.').then(() => this.setState({ aoNote: '' })), 'primary', !this.state.aoNote))]),
        box([h('b', { key: 't', style: { fontSize: 13 } }, 'Refund'), grid([F('Amount (RM)', h('input', { type: 'number', value: this.state.aoRef || '', onChange: e => this.setField('aoRef', e.target.value), style: inp })), F('Refund to', h('select', { value: this.state.aoRefM || 'wallet', onChange: e => this.setField('aoRefM', e.target.value), style: inp }, [h('option', { key: 'w', value: 'wallet' }, 'Customer wallet (credit)'), h('option', { key: 'm', value: 'manual' }, 'Manual (bank / card)')]))], 140),
          h('input', { key: 'r', placeholder: 'Reason', value: this.state.aoRefR || '', onChange: e => this.setField('aoRefR', e.target.value), style: inp }),
          h('div', { key: 'b' }, B('Refund', () => act('refund', { amount: this.state.aoRef, method: this.state.aoRefM || 'wallet', reason: this.state.aoRefR }, 'Refund recorded.').then(() => this.setState({ aoRef: '', aoRefR: '' })), 'primary', !this.state.aoRef))]),
      ], 260),
      (o.notes || []).length ? box([h('b', { key: 't', style: { fontSize: 13 } }, 'Order notes')].concat(o.notes.map(n => h('div', { key: n.id, style: { fontSize: 12.5, color: MUT, borderTop: '1px solid ' + LINE, paddingTop: 6 } }, when(n.ts) + ' · ' + n.by + (n.toCustomer ? ' · to customer' : ' · private') + ' — ' + n.text)))) : null,
      h('div', { key: 'acts', style: { display: 'flex', gap: 8, flexWrap: 'wrap' } },
        !paid ? B('Mark payment received', () => this.aFetch('/api/orders/' + o.id + '/pay', {}).then(d => { if (this.aMsg(d, 'Payment validated.')) this.loadAdmin(); }), 'primary') : null,
        B('Resend confirmation email', () => act('resend', {}, 'Confirmation re-sent.')),
        B('Invoice', () => this.openDoc && this.openDoc(o.id, 'invoice')),
        o.status !== 'cancelled' ? B('Cancel order', () => { const r = window.prompt('Reason for cancelling ' + o.id + '?', ''); if (r !== null) act('cancel', { reason: r }, 'Order cancelled.'); }, 'danger') : null),
    ], { borderColor: TEAL });
  };

  // ---------------------------------------------------------------- Customers (WP users + TeraWallet + login-as)
  P.aCustomers = function () {
    const all = this.state.admCustomers || [];
    const q = String(this.state.acQ || '').toLowerCase();
    const list = all.filter(c => !q || [c.name, c.email, c.phone, c.company].join(' ').toLowerCase().indexOf(q) >= 0);
    const sel = this.state.acSel ? all.find(c => c.id === this.state.acSel) : null;
    return [
      h('input', { key: 'q', placeholder: 'Search name, email, phone, company', value: this.state.acQ || '', onChange: e => this.setField('acQ', e.target.value), style: Object.assign({}, inp, { maxWidth: 380 }) }),
      sel ? this.aCustomerPanel(sel) : null,
      this.table(['Name', 'Email', 'Tier', 'Wallet', 'Joined', ''],
        list.length ? list.slice(0, 150).map(c => [h('span', { style: { fontWeight: 600 } }, c.name + (c.disabled ? ' (disabled)' : '')), c.email, this.chip(c.tier + (c.tierPinned ? ' · pinned' : ''), 'neutral'), this.rm(c.creditBalance || 0), (c.createdAt || '').slice(0, 10),
          h('span', { onClick: () => this.setState({ acSel: c.id, acEdit: null, aMsg: null }), style: { color: TEAL, fontWeight: 600, cursor: 'pointer' } }, 'Edit')]) : [['No customers match', '', '', '', '', '']],
        ['20%', null, '140px', '100px', '100px', '60px'])];
  };
  P.aCustomerPanel = function (c) {
    const tiers = ((this.state.settings || {}).membership || {}).tiers || [];
    const E = this.state.acEdit || { name: c.name, email: c.email, phone: c.phone || '', company: c.company || '', tier: c.tier || 'Standard', creditTerms: !!c.creditTerms };
    const setE = (k, v) => this.setState({ acEdit: Object.assign({}, E, { [k]: v }) });
    const save = body => this.aFetch('/api/admin/customers/' + c.id, body).then(d => { if (this.aMsg(d, 'Customer saved.')) { this.setState({ acEdit: null }); this.loadAdmin(); } });
    const loginAs = () => this.aFetch('/api/admin/customers/' + c.id + '/login-as', {}).then(d => { if (!this.aMsg(d)) return; try { localStorage.setItem('pk_admin_return', this.authToken()); localStorage.setItem('pk_token', d.token); } catch (e) {} window.location.href = '/'; });
    return box([
      h('div', { key: 'h', style: { display: 'flex', gap: 10, alignItems: 'center' } }, h('b', { style: { fontSize: 16 } }, c.name), this.chip(c.tier, 'neutral'), h('span', { style: { marginLeft: 'auto', fontSize: 18, cursor: 'pointer', color: FAINT }, onClick: () => this.setState({ acSel: null }) }, '×')),
      grid([F('Name', h('input', { value: E.name, onChange: e => setE('name', e.target.value), style: inp })), F('Email', h('input', { value: E.email, onChange: e => setE('email', e.target.value), style: inp })), F('Phone', h('input', { value: E.phone, onChange: e => setE('phone', e.target.value), style: inp })), F('Company', h('input', { value: E.company, onChange: e => setE('company', e.target.value), style: inp })),
        F('Membership tier', h('select', { value: E.tier, onChange: e => setE('tier', e.target.value), style: inp }, tiers.map(t => h('option', { key: t.name, value: t.name }, t.name + ' (' + t.pct + '%)'))), 'Changing it pins the tier (audit-logged).'),
        F('Credit terms', h('select', { value: E.creditTerms ? 'yes' : 'no', onChange: e => setE('creditTerms', e.target.value === 'yes'), style: inp }, [h('option', { key: 'n', value: 'no' }, 'No — pay before production'), h('option', { key: 'y', value: 'yes' }, 'Yes — approved corporate account')]))], 200),
      h('div', { key: 'sv', style: { display: 'flex', gap: 8, flexWrap: 'wrap' } }, B('Save customer', () => save(Object.assign({}, E, { tier: E.tier !== c.tier ? E.tier : undefined })), 'primary'), B(c.disabled ? 'Enable account' : 'Disable account', () => save({ disabled: !c.disabled }), c.disabled ? 'ghost' : 'danger'), B('Login as this customer', loginAs)),
      box([h('b', { key: 't', style: { fontSize: 13 } }, 'Wallet (TeraWallet) — balance ' + this.rm(c.creditBalance || 0)),
        grid([F('Amount (RM, negative to debit)', h('input', { type: 'number', value: this.state.acWal || '', onChange: e => this.setField('acWal', e.target.value), style: inp })), F('Note', h('input', { value: this.state.acWalN || '', onChange: e => this.setField('acWalN', e.target.value), style: inp }))], 200),
        h('div', { key: 'b' }, B('Apply to wallet', () => this.aFetch('/api/admin/customers/' + c.id + '/wallet', { amount: this.state.acWal, note: this.state.acWalN }).then(d => { if (this.aMsg(d, 'Wallet updated — new balance ' + this.rm(d.balance))) { this.setState({ acWal: '', acWalN: '' }); this.loadAdmin(); } }), 'primary', !this.state.acWal))]),
    ], { borderColor: TEAL });
  };

  // ---------------------------------------------------------------- Users & roles (every staff type)
  const TYPES = { outlet: 'Outlet', production: 'Production', vendor: 'Printer', hub: 'Hub', admin: 'Admin' };
  const ROLE_LABEL = { outlet_staff: 'Outlet staff', outlet_manager: 'Outlet manager', production_director: 'Production Director', prepress: 'Prepress staff', prepress_manager: 'Prepress manager', production_staff: 'Scheduler staff', production_manager: 'Production Director', scheduler: 'Scheduler staff', scheduler_manager: 'Scheduler manager', logistics: 'Logistics staff', logistics_manager: 'Logistics manager', printer_staff: 'Printer staff', printer_manager: 'Printer manager', hub_staff: 'Hub staff', hub_manager: 'Hub manager', admin: 'Administrator', vendor: 'Printer manager', hub: 'Hub staff' };
  P.aUsers = function () {
    const staff = this.state.admStaff || [];
    const SR = (this.state.admStaffRoles) || (this.aGet('roles', '/api/admin/roles') || {}).staffRoles || {};
    const cfg = this.state.opsConfig || (this.aGet('opscfg', '/api/ops/config') || {}).config || { outlets: [], hubs: [] };
    const companies = staff.filter(s => s.type === 'vendor' && !s.vendorId);
    const t = this.state.auType || 'all';
    const list = staff.filter(s => t === 'all' || s.type === t);
    const N = this.state.auNew || { type: 'production', role: 'prepress' };
    const setN = (k, v) => this.setState({ auNew: Object.assign({}, N, { [k]: v }, k === 'type' ? { role: (SR[v] || [])[0] } : {}) });
    const create = () => this.aFetch('/api/admin/staff', N).then(d => { if (this.aMsg(d, d.message)) { this.setState({ auNew: null, auOpen: false }); this.loadAdmin(); } });
    const upd = (s, body, msg) => this.aFetch('/api/admin/staff/' + s.id, body).then(d => { if (this.aMsg(d, msg || 'Saved.')) this.loadAdmin(); });
    // printer company: the products it prints and the finishing it can do (original "Printing Categories");
    // the scheduler only sees printers that can make a job's product and every finishing it needs
    const FIN = ((this.aGet('roles', '/api/admin/roles') || {}).finishes) || [];
    const clean = n => String(n || '').replace(/\s*\(=.*?\)/g, '').replace(/\s+—.*$/, '').replace(/\s+-\s+(Litho|Digital|Offset|Large Format).*$/i, '').trim();
    const PRODUCTS = Array.from(new Set((this.pkProducts() || []).map(p => clean(this.catName ? this.catName(p.id) : p.name)).filter(Boolean))).sort();
    const capText = s => { const c = s.capabilities || {}; const p = c.products || [], f = c.finishes || [];
      return (p.indexOf('*') >= 0 ? 'All products' : p.length ? p.length + ' product' + (p.length === 1 ? '' : 's') : 'No products set') + ' · ' + (f.indexOf('*') >= 0 ? 'all finishing' : f.length ? f.join(', ') : 'no finishing'); };
    const capFor = companies.find(s => s.id === this.state.auCap);
    const capEditor = () => {
      const s = capFor, c = this.state.auCapDraft || { products: (s.capabilities || {}).products || [], finishes: (s.capabilities || {}).finishes || [] };
      const set = (k, v) => this.setState({ auCapDraft: Object.assign({}, c, { [k]: v }) });
      const toggle = (k, x) => set(k, c[k].indexOf(x) >= 0 ? c[k].filter(y => y !== x) : c[k].filter(y => y !== '*').concat([x]));
      const allP = c.products.indexOf('*') >= 0, allF = c.finishes.indexOf('*') >= 0;
      const chk = (on, label, fn) => h('label', { key: label, style: { display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, cursor: 'pointer' } }, h('input', { type: 'checkbox', checked: on, onChange: fn }), label);
      return box([h('b', { key: 't' }, 'Products & finishing — ' + s.name),
        para('The Scheduler can only ask this printer for quotes on jobs it can make: the product, and every finishing the job needs.'),
        h('b', { key: 'ph', style: { fontSize: 13 } }, 'Products'),
        chk(allP, 'All products', () => set('products', allP ? [] : ['*'])),
        !allP ? (PRODUCTS.length ? h('div', { key: 'pl', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(210px,1fr))', gap: 6 } }, PRODUCTS.map(p => chk(c.products.indexOf(p) >= 0, p, () => toggle('products', p)))) : para('Loading products…')) : null,
        h('b', { key: 'fh', style: { fontSize: 13 } }, 'Finishing'),
        chk(allF, 'All finishing', () => set('finishes', allF ? [] : ['*'])),
        !allF ? h('div', { key: 'fl', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(160px,1fr))', gap: 6 } }, FIN.map(f => chk(c.finishes.indexOf(f) >= 0, f, () => toggle('finishes', f)))) : null,
        h('div', { key: 'b', style: { display: 'flex', gap: 8 } }, B('Save', () => this.aFetch('/api/admin/staff/' + s.id, { capabilities: c }).then(d => { if (this.aMsg(d, 'Saved — ' + s.name + ' will be offered matching jobs only.')) { this.setState({ auCap: null, auCapDraft: null }); this.loadAdmin(); } }), 'primary'), B('Cancel', () => this.setState({ auCap: null, auCapDraft: null }), 'ghost'))]);
    };
    return [
      para('Every staff login and its role — Admin, Outlet (staff / manager), Production (Prepress, Scheduler, Production, Logistics — staff / manager), Printer (staff / manager) and Hub (staff / manager). Each role signs in on its own login page and only sees its own screens.'),
      h('div', { key: 'f', style: { display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' } }, ['all'].concat(Object.keys(TYPES)).map(k => h('span', { key: k, onClick: () => this.setState({ auType: k }), style: { fontSize: 12.5, fontWeight: 600, padding: '6px 12px', borderRadius: 999, cursor: 'pointer', border: '1px solid ' + (t === k ? INK : HAIR), background: t === k ? INK : '#fff', color: t === k ? '#fff' : MUT } }, (k === 'all' ? 'All' : TYPES[k]) + ' (' + (k === 'all' ? staff.length : staff.filter(s => s.type === k).length) + ')')),
        h('span', { style: { marginLeft: 'auto' } }, B(this.state.auOpen ? 'Cancel' : '＋ Add new user', () => this.setState({ auOpen: !this.state.auOpen }), this.state.auOpen ? 'ghost' : 'primary'))),
      this.state.auOpen ? box([h('b', { key: 't' }, 'Add new staff user'),
        grid([F('Name', h('input', { value: N.name || '', onChange: e => setN('name', e.target.value), style: inp })), F('Email', h('input', { value: N.email || '', onChange: e => setN('email', e.target.value), style: inp })),
          F('Account type', h('select', { value: N.type, onChange: e => setN('type', e.target.value), style: inp }, Object.keys(TYPES).map(k => h('option', { key: k, value: k }, TYPES[k])))),
          F('Role', h('select', { value: N.role, onChange: e => setN('role', e.target.value), style: inp }, (SR[N.type] || []).map(r => h('option', { key: r, value: r }, ROLE_LABEL[r] || r)))),
          N.type === 'outlet' ? F('Outlet', h('select', { value: N.outlet || '', onChange: e => setN('outlet', e.target.value), style: inp }, [h('option', { key: '', value: '' }, 'Choose…')].concat(cfg.outlets.map(o => h('option', { key: o.id, value: o.id }, o.name))))) : null,
          N.type === 'hub' ? F('Hub', h('select', { value: N.hub || '', onChange: e => setN('hub', e.target.value), style: inp }, [h('option', { key: '', value: '' }, 'All hubs (manager)')].concat(cfg.hubs.map(o => h('option', { key: o.id, value: o.id }, o.name))))) : null,
          N.type === 'vendor' && N.role === 'printer_staff' ? F('Printer company', h('select', { value: N.vendorId || '', onChange: e => setN('vendorId', e.target.value), style: inp }, [h('option', { key: '', value: '' }, 'Choose…')].concat(companies.map(o => h('option', { key: o.id, value: o.id }, o.name))))) : null,
          F('Password (optional)', h('input', { type: 'text', value: N.password || '', onChange: e => setN('password', e.target.value), placeholder: 'leave blank to generate', style: inp }))], 200),
        h('div', { key: 'b' }, B('Create account', create, 'primary', !N.email))]) : null,
      capFor ? capEditor() : null,
      this.table(['Name', 'Email', 'Type', 'Role', 'Scope', 'Status', 'Actions'],
        list.map(s => [h('span', { style: { fontWeight: 600 } }, s.name), s.email, this.chip(TYPES[s.type] || s.type, 'teal'),
          (SR[s.type] || []).length > 1 ? h('select', { value: s.role, onChange: e => upd(s, { role: e.target.value }, 'Role changed.'), style: Object.assign({}, inp, { padding: '5px 7px', fontSize: 12.5 }) }, SR[s.type].map(r => h('option', { key: r, value: r }, ROLE_LABEL[r] || r))) : (ROLE_LABEL[s.role] || s.role),
          s.type === 'vendor' && !s.vendorId ? h('span', { style: { fontSize: 12.5, color: MUT } }, capText(s)) : s.outlet || (s.hub ? s.hub.replace('HUB-', 'Hub ') : '') || (s.vendorId ? ((staff.find(x => x.id === s.vendorId) || {}).name || '') : '') || '—',
          this.chip(s.disabled ? 'Disabled' : 'Active', s.disabled ? 'bad' : 'ok'),
          h('span', { style: { display: 'flex', gap: 10, flexWrap: 'wrap' } },
            s.type === 'vendor' && !s.vendorId ? h('span', { onClick: () => { this.setState({ auCap: s.id, auCapDraft: null }); if (typeof window !== 'undefined') window.scrollTo(0, 0); }, style: { color: TEAL, fontWeight: 600, cursor: 'pointer', fontSize: 12.5 } }, 'Products & finishing') : null,
            h('span', { onClick: () => upd(s, { disabled: !s.disabled }, s.disabled ? 'Account enabled.' : 'Account disabled — signed out everywhere.'), style: { color: s.disabled ? TEAL : '#c71917', fontWeight: 600, cursor: 'pointer', fontSize: 12.5 } }, s.disabled ? 'Enable' : 'Disable'),
            h('span', { onClick: () => this.aFetch('/api/admin/staff/' + s.id, { resetPassword: true }).then(d => this.aMsg(d, d.message)), style: { color: TEAL, fontWeight: 600, cursor: 'pointer', fontSize: 12.5 } }, 'Reset password'))]),
        ['16%', null, '100px', '170px', '130px', '90px', '170px']),
    ];
  };

  // ---------------------------------------------------------------- Coupons (WooCommerce coupons)
  P.aCoupons = function () {
    const list = (this.aGet('coupons', '/api/admin/coupons') || {}).coupons;
    const N = this.state.cpNew;
    const setN = (k, v) => this.setState({ cpNew: Object.assign({}, N, { [k]: v }) });
    const save = () => this.aFetch('/api/admin/coupons', N).then(d => { if (this.aMsg(d, 'Coupon ' + (d.coupon && d.coupon.code) + ' saved.')) { this.aDrop('coupons'); this.setState({ cpNew: null }); } });
    const edit = c => this.setState({ cpNew: Object.assign({}, c, { allowedEmails: (c.allowedEmails || []).join(', ') }) });
    const toggle = c => this.aFetch('/api/admin/coupons', Object.assign({}, c, { allowedEmails: (c.allowedEmails || []).join(','), status: c.status === 'active' ? 'disabled' : 'active' })).then(d => { if (this.aMsg(d, 'Coupon updated.')) this.aDrop('coupons'); });
    const del = c => { if (window.confirm('Delete coupon ' + c.code + '?')) this.aFetch('/api/admin/coupons/' + c.id + '/delete', {}).then(d => { if (this.aMsg(d, 'Coupon deleted.')) this.aDrop('coupons'); }); };
    return [
      para('Store-wide discount codes, like WooCommerce coupons. Customers enter them in the cart; the server re-checks every rule when the order is placed. Personal sign-up codes (RM30 and 15%) are issued automatically and are not listed here.'),
      h('div', { key: 'a' }, N ? null : B('＋ Add coupon', () => this.setState({ cpNew: { type: 'percent', status: 'active' } }), 'primary')),
      N ? box([h('b', { key: 't' }, N.id ? 'Edit coupon' : 'New coupon'),
        grid([F('Code', h('input', { value: N.code || '', onChange: e => setN('code', e.target.value.toUpperCase()), placeholder: 'e.g. RAYA26', style: inp })),
          F('Discount type', h('select', { value: N.type, onChange: e => setN('type', e.target.value), style: inp }, [h('option', { key: 'p', value: 'percent' }, 'Percentage discount'), h('option', { key: 'f', value: 'fixed' }, 'Fixed cart discount (RM)')])),
          F('Amount', h('input', { type: 'number', value: N.amount || '', onChange: e => setN('amount', e.target.value), style: inp })),
          F('Minimum spend (RM)', h('input', { type: 'number', value: N.minSpend || '', onChange: e => setN('minSpend', e.target.value), style: inp })),
          F('Expiry date', h('input', { type: 'date', value: N.expires || '', onChange: e => setN('expires', e.target.value), style: inp })),
          F('Usage limit (total)', h('input', { type: 'number', value: N.usageLimit || '', onChange: e => setN('usageLimit', e.target.value), placeholder: 'unlimited', style: inp })),
          F('Limit per customer', h('input', { type: 'number', value: N.perCustomer || '', onChange: e => setN('perCustomer', e.target.value), placeholder: 'unlimited', style: inp })),
          F('Status', h('select', { value: N.status, onChange: e => setN('status', e.target.value), style: inp }, [h('option', { key: 'a', value: 'active' }, 'Active'), h('option', { key: 'd', value: 'disabled' }, 'Disabled')]))], 180),
        F('Allowed emails (optional)', h('input', { value: N.allowedEmails || '', onChange: e => setN('allowedEmails', e.target.value), placeholder: 'comma-separated — leave blank for everyone', style: inp })),
        F('Description (internal)', h('input', { value: N.description || '', onChange: e => setN('description', e.target.value), style: inp })),
        h('div', { key: 'b', style: { display: 'flex', gap: 8 } }, B('Save coupon', save, 'primary', !N.code || !N.amount), B('Cancel', () => this.setState({ cpNew: null })))]) : null,
      !list ? para('Loading…') : this.table(['Code', 'Discount', 'Min spend', 'Expires', 'Used / limit', 'Status', ''],
        list.length ? list.map(c => [h('span', { style: { fontFamily: 'ui-monospace,Menlo,monospace', fontWeight: 700 } }, c.code), c.type === 'percent' ? c.amount + '% off' : 'RM ' + c.amount + ' off', c.minSpend ? this.rm(c.minSpend) : '—', c.expires || 'Never', (c.usedCount || 0) + ' / ' + (c.usageLimit || '∞'),
          this.chip(c.status === 'active' ? 'Active' : 'Disabled', c.status === 'active' ? 'ok' : 'neutral'),
          h('span', { style: { display: 'flex', gap: 10 } }, h('span', { onClick: () => edit(c), style: { color: TEAL, fontWeight: 600, cursor: 'pointer' } }, 'Edit'), h('span', { onClick: () => toggle(c), style: { color: MUT, fontWeight: 600, cursor: 'pointer' } }, c.status === 'active' ? 'Disable' : 'Enable'), h('span', { onClick: () => del(c), style: { color: '#c71917', fontWeight: 600, cursor: 'pointer' } }, 'Delete'))]) : [['No coupons yet', '', '', '', '', '', '']],
        ['130px', '120px', '100px', '100px', '110px', '90px', null])];
  };

  // ---------------------------------------------------------------- Settings: membership, country (tax + currency), payments, shipping
  P.aMembership = function () {
    const m = (this.state.settings || {}).membership; if (!m) return [para('Loading…')];
    const T = this.state.amTiers || m.tiers.map(t => Object.assign({}, t));
    const setT = (i, k, v) => { const n = T.map(x => Object.assign({}, x)); n[i][k] = k === 'name' ? v : Number(v); this.setState({ amTiers: n }); };
    return [para('Membership tiers (Printoka Settings → Membership). The discount applies automatically to the member’s cart and is re-checked by the server on every order. Pin a customer’s tier from Customers.'),
      this.table(['Tier', 'Spend threshold (RM, trailing 12 months)', 'Discount %'], T.map((t, i) => [h('input', { value: t.name, onChange: e => setT(i, 'name', e.target.value), style: inp }), h('input', { type: 'number', value: t.threshold, onChange: e => setT(i, 'threshold', e.target.value), style: inp }), h('input', { type: 'number', value: t.pct, onChange: e => setT(i, 'pct', e.target.value), style: inp })]), [null, null, '140px']),
      h('div', { key: 'b' }, B('Save tiers', () => this.aSettingsSave({ membership: Object.assign({}, m, { tiers: T }) }, 'Membership tiers saved.').then(() => this.setState({ amTiers: null })), 'primary'))];
  };
  P.aTax = function () {
    const s = this.state.settings || {}; if (!s.tax) return [para('Loading…')];
    const tx = this.state.atTax || JSON.parse(JSON.stringify(s.tax)), cur = this.state.atCur || Object.assign({}, s.currency), sh = this.state.atShip || Object.assign({}, s.shipping);
    const NAMES = { MY: 'Malaysia', SG: 'Singapore', BN: 'Brunei' };
    return [para('Country settings — tax per country, the display currency rate from RM, and the delivery fee. Checkout totals are recalculated from these on the server.'),
      this.table(['Country', 'Tax label', 'Tax rate %', 'Currency rate (1 RM =)'], Object.keys(tx).map(k => [NAMES[k] || k,
        h('input', { value: tx[k].label, onChange: e => { const n = JSON.parse(JSON.stringify(tx)); n[k].label = e.target.value; this.setState({ atTax: n }); }, style: inp }),
        h('input', { type: 'number', value: tx[k].rate, onChange: e => { const n = JSON.parse(JSON.stringify(tx)); n[k].rate = Number(e.target.value); this.setState({ atTax: n }); }, style: inp }),
        h('input', { type: 'number', step: '0.01', value: cur[k] != null ? cur[k] : '', onChange: e => this.setState({ atCur: Object.assign({}, cur, { [k]: Number(e.target.value) }) }), style: inp })]), [null, null, '130px', '190px']),
      box([h('b', { key: 't' }, 'Shipping'), grid([F('Flat delivery fee (RM)', h('input', { type: 'number', value: sh.flat, onChange: e => this.setState({ atShip: Object.assign({}, sh, { flat: Number(e.target.value) }) }), style: inp })), F('Free delivery over (RM, 0 = never)', h('input', { type: 'number', value: sh.freeOver || 0, onChange: e => this.setState({ atShip: Object.assign({}, sh, { freeOver: Number(e.target.value) }) }), style: inp }))], 200)]),
      h('div', { key: 'b' }, B('Save country & shipping settings', () => this.aSettingsSave({ tax: tx, currency: cur, shipping: sh }, 'Country & shipping settings saved.').then(() => this.setState({ atTax: null, atCur: null, atShip: null })), 'primary'))];
  };
  P.aPayments = function () {
    const p = (this.state.settings || {}).payments; if (!p) return [para('Loading…')];
    const D = this.state.apPay || JSON.parse(JSON.stringify(p));
    const setM = (k, f, v) => { const n = JSON.parse(JSON.stringify(D)); n.methods[k][f] = v; this.setState({ apPay: n }); };
    return [para('Payment methods offered at checkout (WooCommerce → Payments). Gateway API keys belong in the server environment, never in this screen. While test mode is on, card / e-wallet payments confirm instantly and wallet top-ups are credited immediately — switch it off before going live.'),
      h('label', { key: 'tm', style: { display: 'flex', gap: 10, alignItems: 'center', fontSize: 13.5, fontWeight: 600, color: D.testMode ? '#8a4b00' : '#1f5e2a', background: D.testMode ? '#fff8e6' : '#e6f4ea', borderRadius: 8, padding: '10px 12px' } }, h('input', { type: 'checkbox', checked: !!D.testMode, onChange: e => this.setState({ apPay: Object.assign({}, D, { testMode: e.target.checked }) }) }), D.testMode ? 'Test mode is ON — payments are simulated' : 'Live mode — real payments only'),
      this.table(['Method', 'Label at checkout', 'Enabled'], Object.keys(D.methods).map(k => [k.replace(/_/g, ' '), h('input', { value: D.methods[k].label, onChange: e => setM(k, 'label', e.target.value), style: inp }), h('input', { type: 'checkbox', checked: D.methods[k].enabled !== false, onChange: e => setM(k, 'enabled', e.target.checked) })]), ['150px', null, '90px']),
      D.methods.bank_transfer ? box([h('b', { key: 't' }, 'Bank transfer details (shown to the customer)'), grid([F('Bank', h('input', { value: D.methods.bank_transfer.bankName || '', onChange: e => setM('bank_transfer', 'bankName', e.target.value), style: inp })), F('Account name', h('input', { value: D.methods.bank_transfer.accountName || '', onChange: e => setM('bank_transfer', 'accountName', e.target.value), style: inp })), F('Account number', h('input', { value: D.methods.bank_transfer.accountNo || '', onChange: e => setM('bank_transfer', 'accountNo', e.target.value), style: inp }))], 180)]) : null,
      h('div', { key: 'b' }, B('Save payment settings', () => this.aSettingsSave({ payments: D }, 'Payment settings saved.').then(() => this.setState({ apPay: null })), 'primary'))];
  };
  // couriers, outlets and hubs live in the ops settings (the same lists every department uses)
  P.aOps = function () { if (!this.state.opsConfig) this.aFetch('/api/ops/config').then(d => d.config && this.setState({ opsConfig: d.config })); return this.oSettings ? this.oSettings() : [para('Loading…')]; };
  P.aWallet = function () {
    const custs = (this.state.admCustomers || []).filter(c => (c.creditBalance || 0) !== 0);
    const tu = (this.aGet('topups', '/api/admin/topups') || {}).topups || [];
    const approve = t => this.aFetch('/api/admin/topups/' + t.id + '/approve', {}).then(d => { if (this.aMsg(d, 'Top-up approved and credited.')) { this.aDrop('topups'); this.loadAdmin(); } });
    return [para('Customer wallet credit (TeraWallet). Credit or debit a wallet from Customers → Edit. Top-ups wait here until their payment is confirmed (test mode credits them instantly).'),
      h('div', { key: 'tu' }, h('b', null, 'Top-up requests'), this.table(['When', 'Customer', 'Amount', 'Status', ''], tu.length ? tu.map(t => [when(t.createdAt), t.name + ' · ' + t.email, this.rm(t.amount), this.chip(t.status, t.status === 'pending' ? 'warn' : 'ok'), t.status === 'pending' ? h('span', { onClick: () => approve(t), style: { color: TEAL, fontWeight: 600, cursor: 'pointer' } }, 'Payment received → credit') : (t.approvedBy || '')]) : [['No top-up requests', '', '', '', '']], ['140px', null, '100px', '100px', '200px'])),
      h('div', { key: 'bal' }, h('b', null, 'Balances'), this.table(['Customer', 'Email', 'Balance', ''], custs.length ? custs.map(c => [c.name, c.email, this.rm(c.creditBalance), h('span', { onClick: () => this.setState({ atab: 'customers', acSel: c.id }), style: { color: TEAL, fontWeight: 600, cursor: 'pointer' } }, 'Adjust')]) : [['No wallet balances', '', '', '']], ['24%', null, '120px', '80px']))];
  };
  P.aPricing = function () {
    const n = this.pkProducts().length;
    return [para('Prices come from the Printoka pricing engine (' + n + ' products), which replaced the WordPress “API Settings” tables — impression runs, material lists, stationery and computer-form settings. Product names, categories and visibility are edited under Products; membership discounts under Membership; tax, currency and delivery under Tax & invoicing.'),
      h('div', { key: 'b', style: { display: 'flex', gap: 8, flexWrap: 'wrap' } }, h('span', { 'data-go': 'set:atab:catalogue' }, B('Products & categories')), h('span', { 'data-go': 'set:atab:membership' }, B('Membership tiers')), h('span', { 'data-go': 'set:atab:tax' }, B('Tax, currency & delivery')))];
  };
  P.aPrinting = function () {
    const jobs = (this.state.admJobs || []).filter(j => j.outsource || j.route);
    return [para('Printing jobs (the WordPress “Printing Job” post type): every job routed to our own floor or a partner printer, with its PO and shipping label. Manage them in the Scheduler.'),
      h('div', { key: 'b' }, h('span', { 'data-go': 'scheduler' }, B('Open Scheduler →', null, 'primary'))),
      this.table(['Job', 'Customer', 'Product', 'Route', 'Printer / machine', 'PO', 'Status'], jobs.length ? jobs.map(j => [j.id, j.customer, j.product, j.route === 'inhouse' ? 'In-house' : 'Outsourced', j.machine || j.printer || '—', (j.outsource && j.outsource.po) || '—', this.chip(j.statusLabel || j.status, 'neutral')]) : [['No routed jobs yet', '', '', '', '', '', '']], ['120px', null, null, '100px', '160px', '120px', '170px'])];
  };

  // ---------------------------------------------------------------- Content: posts, FAQs, media
  P.aPosts = function () {
    const posts = this.state.blog || [];
    const E = this.state.apEdit;
    const setE = (k, v) => this.setState({ apEdit: Object.assign({}, E, { [k]: v }) });
    const open = p => { if (!p) return this.setState({ apEdit: { title: '', tag: 'Guides', excerpt: '', body: '', status: 'published' } }); fetch('/api/content/blog/' + p.slug).then(r => r.json()).then(d => { const x = d.post || p; this.setState({ apEdit: { originalSlug: x.slug, slug: x.slug, title: x.title, tag: x.tag, excerpt: x.excerpt || '', body: x.body || '', status: x.status || 'published' } }); }); };
    const save = () => this.aFetch('/api/admin/posts', E).then(d => { if (this.aMsg(d, 'Post saved.')) { this.setState({ apEdit: null }); this.blogLoad && this.blogLoad(true); fetch('/api/content/blog').then(r => r.json()).then(x => this.setState({ blog: x.posts || [] })); } });
    const del = slug => { if (window.confirm('Delete this post?')) this.aFetch('/api/admin/posts/' + encodeURIComponent(slug) + '/delete', {}).then(d => { if (this.aMsg(d, 'Post deleted.')) fetch('/api/content/blog').then(r => r.json()).then(x => this.setState({ blog: x.posts || [] })); }); };
    return [
      h('div', { key: 'a', style: { display: 'flex', gap: 8 } }, B('＋ Add new post', () => open(null), 'primary'), h('span', { 'data-go': 'learn' }, B('View Learning Hub'))),
      E ? box([h('b', { key: 't' }, E.originalSlug ? 'Edit post' : 'New post'),
        grid([F('Title', h('input', { value: E.title, onChange: e => setE('title', e.target.value), style: inp })), F('URL slug', h('input', { value: E.slug || '', onChange: e => setE('slug', e.target.value), placeholder: 'auto from title', style: inp }), '/blog/<slug>/'), F('Category', h('input', { value: E.tag || '', onChange: e => setE('tag', e.target.value), style: inp })), F('Status', h('select', { value: E.status, onChange: e => setE('status', e.target.value), style: inp }, [h('option', { key: 'p', value: 'published' }, 'Published'), h('option', { key: 'd', value: 'draft' }, 'Draft')]))], 200),
        F('Excerpt (meta description)', h('textarea', { rows: 2, value: E.excerpt, onChange: e => setE('excerpt', e.target.value), style: Object.assign({}, inp, { resize: 'vertical' }) })),
        F('Body (HTML)', h('textarea', { rows: 14, value: E.body, onChange: e => setE('body', e.target.value), style: Object.assign({}, inp, { resize: 'vertical', fontFamily: 'ui-monospace,Menlo,monospace', fontSize: 12.5 }) })),
        h('div', { key: 'b', style: { display: 'flex', gap: 8 } }, B('Save post', save, 'primary', !E.title), B('Cancel', () => this.setState({ apEdit: null })))]) : null,
      this.table(['Title', 'Category', 'Date', 'Status', ''], posts.map(pp => [h('span', { style: { fontWeight: 600 } }, pp.title), pp.tag, pp.date, this.chip(pp.bodyReady ? 'Published' : 'Draft', pp.bodyReady ? 'ok' : 'warn'),
        h('span', { style: { display: 'flex', gap: 10 } }, h('span', { onClick: () => open(pp), style: { color: TEAL, fontWeight: 600, cursor: 'pointer' } }, 'Edit'), h('span', { onClick: () => del(pp.slug), style: { color: '#c71917', fontWeight: 600, cursor: 'pointer' } }, 'Delete'))]), [null, '140px', '110px', '100px', '110px'])];
  };
  P.aFaqs = function () {
    const faqs = this.state.faq || [];
    const E = this.state.afEdit; const setE = (k, v) => this.setState({ afEdit: Object.assign({}, E, { [k]: v }) });
    const reload = d => { if (d && d.faq) this.setState({ faq: d.faq, afEdit: null }); };
    const del = (c, i) => { if (window.confirm('Delete this question?')) this.aFetch('/api/admin/faq/delete', { catId: c.id, index: i }).then(d => { if (this.aMsg(d, 'Question deleted.')) reload(d); }); };
    const row = (c, qa, i) => {
      if (E && E.catId === c.id && E.index === i) return h('div', { key: 'e' + i }, this.aFaqForm(E, setE, reload));
      return h('div', { key: i, style: { borderTop: '1px solid ' + LINE, paddingTop: 8, display: 'flex', gap: 12 } },
        h('div', { style: { flex: 1, minWidth: 0 } }, h('div', { style: { fontSize: 13, fontWeight: 600 } }, qa.q), h('div', { style: { fontSize: 12.5, color: MUT, whiteSpace: 'pre-wrap', lineHeight: 1.6 } }, qa.a)),
        h('span', { style: { display: 'flex', gap: 10, flex: 'none' } },
          h('span', { onClick: () => this.setState({ afEdit: { catId: c.id, index: i, q: qa.q, a: qa.a } }), style: { color: TEAL, fontWeight: 600, cursor: 'pointer', fontSize: 12.5 } }, 'Edit'),
          h('span', { onClick: () => del(c, i), style: { color: '#c71917', fontWeight: 600, cursor: 'pointer', fontSize: 12.5 } }, 'Delete')));
    };
    const topic = c => h('div', { key: c.id }, box([
      h('div', { key: 'h', style: { display: 'flex', alignItems: 'center', gap: 10 } }, h('b', null, c.title), h('span', { style: { color: FAINT, fontSize: 12.5 } }, c.questions.length + ' questions'), h('span', { style: { marginLeft: 'auto' } }, B('＋ Add question', () => this.setState({ afEdit: { catId: c.id, q: '', a: '' } })))),
      E && E.catId === c.id && E.index == null ? this.aFaqForm(E, setE, reload) : null,
    ].concat(c.questions.map((qa, i) => row(c, qa, i)))));
    return [para('Support FAQs, shown on the Support page and the homepage. Add, edit or delete questions within each topic.'),
      h('div', { key: 'l', style: { display: 'flex', flexDirection: 'column', gap: 14 } }, faqs.map(topic))];
  };
  P.aFaqForm = function (E, setE, reload) {
    return h('div', { key: 'faqf', style: { display: 'flex', flexDirection: 'column', gap: 8, background: ALT, borderRadius: 8, padding: 12 } },
      h('input', { placeholder: 'Question', value: E.q, onChange: e => setE('q', e.target.value), style: inp }),
      h('textarea', { rows: 4, placeholder: 'Answer', value: E.a, onChange: e => setE('a', e.target.value), style: Object.assign({}, inp, { resize: 'vertical' }) }),
      h('div', { style: { display: 'flex', gap: 8 } }, B('Save', () => this.aFetch('/api/admin/faq', E).then(d => { if (this.aMsg(d, 'FAQ saved.')) reload(d); }), 'primary', !E.q || !E.a), B('Cancel', () => this.setState({ afEdit: null }))));
  };
  P.aMedia = function () {
    const media = this.state.media || [];
    const kind = this.state.amKind || 'Uploaded';
    const kinds = Array.from(new Set(media.map(m => m.kind)));
    const list = media.filter(m => m.kind === kind);
    const reload = () => fetch('/api/content/media').then(r => r.json()).then(d => this.setState({ media: d.media || [] }));
    const upload = e => { const files = Array.from(e.target.files || []); files.forEach(f => { const rd = new FileReader(); rd.onload = () => this.aFetch('/api/admin/media', { name: f.name, data: rd.result }).then(d => { if (this.aMsg(d, 'Uploaded ' + (d.name || f.name) + '.')) reload(); }); rd.readAsDataURL(f); }); e.target.value = ''; };
    return [para('Media library. Upload images or PDFs (up to 8 MB each) for posts, banners and pages; copy the path to use it. Original site images and product photos are listed too.'),
      h('label', { key: 'u', style: { display: 'inline-flex', alignItems: 'center', gap: 8, font: '600 13px Montserrat,sans-serif', padding: '10px 16px', borderRadius: 8, background: TEAL, color: '#fff', cursor: 'pointer', alignSelf: 'flex-start' } }, 'Upload files', h('input', { type: 'file', multiple: true, accept: 'image/*,application/pdf', onChange: upload, style: { display: 'none' } })),
      h('div', { key: 'k', style: { display: 'flex', gap: 6, flexWrap: 'wrap' } }, kinds.map(k => h('span', { key: k, onClick: () => this.setState({ amKind: k }), style: { fontSize: 12.5, fontWeight: 600, padding: '6px 12px', borderRadius: 999, cursor: 'pointer', border: '1px solid ' + (kind === k ? INK : HAIR), background: kind === k ? INK : '#fff', color: kind === k ? '#fff' : MUT } }, k + ' (' + media.filter(m => m.kind === k).length + ')'))),
      list.length ? h('div', { key: 'g', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(140px,1fr))', gap: 12 } }, list.slice(0, 200).map((m, i) => h('div', { key: i, style: { border: '1px solid ' + HAIR, borderRadius: 10, overflow: 'hidden', background: '#fff' } },
        h('div', { style: { height: 96, background: ALT, display: 'grid', placeItems: 'center', overflow: 'hidden' } }, /\.pdf$/i.test(m.file) ? h('span', { style: { fontWeight: 700, color: MUT } }, 'PDF') : h('img', { src: window.__asset(m.file), alt: '', loading: 'lazy', style: { maxHeight: '100%', maxWidth: '100%', objectFit: 'contain' } })),
        h('div', { style: { padding: '7px 9px', display: 'flex', flexDirection: 'column', gap: 4 } }, h('span', { title: m.file, style: { fontSize: 11, color: MUT, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' } }, m.name),
          h('span', { style: { display: 'flex', gap: 10, fontSize: 11.5 } }, h('span', { onClick: () => { try { navigator.clipboard.writeText('/' + m.file); } catch (e) {} this.setState({ aMsg: { bad: false, text: 'Copied /' + m.file } }); }, style: { color: TEAL, fontWeight: 600, cursor: 'pointer' } }, 'Copy path'),
            m.kind === 'Uploaded' ? h('span', { onClick: () => { if (window.confirm('Delete ' + m.name + '?')) this.aFetch('/api/admin/media/delete', { file: m.file }).then(d => { if (this.aMsg(d, 'Deleted.')) reload(); }); }, style: { color: '#c71917', fontWeight: 600, cursor: 'pointer' } }, 'Delete') : null))))) : h('div', { key: 'e', style: { color: FAINT, fontSize: 13 } }, kind === 'Uploaded' ? 'Nothing uploaded yet.' : 'Loading media…')];
  };
})();
