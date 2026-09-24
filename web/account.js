/*
 * Staff account pattern — copied from the original printoka.com OUTLET account
 * (themes/printoka-child/views/templates/account/outlet/* + partials/mixin/dashboard.pug):
 *
 *   header: logo · nav tabs (or, on a single page, the record's progress bar) · user menu
 *   dashboard: quick-link tiles (with the live "ping" dot) + a metric chart + actions
 *   list pages: search · date · status filters + a card table
 *   single pages: "Dashboard / Type" crumbs, title + status pill, main column of collapsible
 *                 cards (status actions, details, forms) and a 300px aside (address, statuses
 *                 log with notes, PDFs, general)
 *   performance: range select (3 / 6 / 12 months), metric change pill, charts, product table
 *
 * This file holds the kit and the outlet screens. Production, hub and printer screens reuse the kit.
 */
(function () {
  const C = window.PKComponent; if (!C) return;
  const P = C.prototype;

  // ---------------------------------------------------------------- kit
  const inp = { font: '400 13.5px Montserrat,sans-serif', padding: '9px 12px', border: '1px solid ' + HAIR, borderRadius: 8, width: '100%', background: '#fff' };
  const pillInp = Object.assign({}, inp, { borderRadius: 999, maxWidth: 220 });
  const Btn = (label, onClick, kind, disabled) => h('button', { type: 'button', disabled: !!disabled, onClick: disabled ? undefined : onClick,
    style: { font: '600 13px Montserrat,sans-serif', padding: kind === 'block' ? '14px 16px' : '9px 16px', borderRadius: 8, width: kind === 'block' ? '100%' : undefined, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? .5 : 1,
      border: '1px solid ' + (kind === 'primary' ? TEAL : '#d9d9d9'), background: kind === 'primary' ? TEAL : '#fff', color: kind === 'primary' ? '#fff' : INK } }, label);
  const FG = (label, control, req, hint) => h('label', { style: { display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13, fontWeight: 600, color: INK } }, h('span', null, label, req ? h('span', { style: { color: TEAL } }, ' *') : null), hint ? h('span', { style: { fontSize: 12, fontWeight: 400, color: FAINT } }, hint) : null, control);
  const when = ts => { if (!ts) return '—'; const d = new Date(ts); return d.toLocaleDateString('en-GB').replace(/\//g, '-') + ' ' + d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }).toLowerCase(); };
  const dmy = ts => { if (!ts) return '—'; const d = new Date(ts); return String(d.getDate()).padStart(2, '0') + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + d.getFullYear(); };
  const ago = ts => { const s = Math.max(1, (Date.now() - Date.parse(ts)) / 1000); const u = [[31536e3, 'year'], [2592e3, 'month'], [86400, 'day'], [3600, 'hour'], [60, 'min']].find(x => s >= x[0]); return u ? Math.floor(s / u[0]) + ' ' + u[1] + (Math.floor(s / u[0]) > 1 ? 's' : '') : 'just now'; };
  const BADGE = s => /pending|not followed|issues|failed|refunded|cancelled|rejected|unable/i.test(s) ? 'bad' : /collect|completed|accepted|paid|shipped|quoted/i.test(s) ? 'ok' : 'teal';
  P.aFetchJ = function (url, body) {
    const opt = { headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()) };
    if (body !== undefined) { opt.method = 'POST'; opt.body = JSON.stringify(body || {}); }
    return fetch(url, opt).then(r => r.json().then(d => (r.ok ? d : Object.assign({ error: d.error || 'Request failed' }, d)))).catch(() => ({ error: 'Network error' }));
  };
  // cached GET, refetched when invalidated
  P.acGet = function (key, url) { this._ac = this._ac || {}; const c = this._ac[key]; if (c && c.data) return c.data; if (!c) { this._ac[key] = { loading: true }; setTimeout(() => this.aFetchJ(url).then(d => { this._ac[key] = { data: d }; this.forceUpdate(); }), 0); } return null; };
  P.acDrop = function (prefix) { if (!this._ac) return; Object.keys(this._ac).forEach(k => { if (!prefix || k.indexOf(prefix) === 0) delete this._ac[k]; }); this.forceUpdate(); };
  P.acMsg = function () { const m = this.state.acMsg; if (!m) return null; return h('div', { key: 'acm', role: 'status', style: { position: 'fixed', right: 16, bottom: 16, zIndex: 130, maxWidth: 420, fontSize: 13, borderRadius: 10, padding: '12px 16px', background: m.bad ? '#fdecec' : '#e6f4ea', color: m.bad ? '#8c1c13' : '#1f5e2a', border: '1px solid ' + (m.bad ? '#f5c8c7' : '#cfe8d4'), boxShadow: '0 10px 30px rgba(0,0,0,.12)', display: 'flex', gap: 10 } }, h('span', { style: { flex: 1 } }, m.text), h('span', { onClick: () => this.setState({ acMsg: null }), style: { cursor: 'pointer', fontWeight: 700 } }, '×')); };
  P.acDone = function (d, ok) { if (!d || d.error) { this.setState({ acMsg: { bad: true, text: (d && d.error) || 'Something went wrong. Please try again.' } }); return false; } if (ok) this.setState({ acMsg: { bad: false, text: ok } }); return true; };
  P.acOpen = function (view) { this.setState({ acView: view, acModal: null, acForm: {} }); if (typeof window !== 'undefined') window.scrollTo(0, 0); };

  // header — logo · nav tabs (or progress bar on single pages) · user menu (original outlet header.pug)
  P.acHeader = function (o) {
    const u = this.state.user || {};
    const nav = o.progress
      ? h('div', { style: { flex: '1 1 320px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, padding: '10px 0', maxWidth: 560, margin: '0 auto' } },
          h('div', { style: { fontSize: 13, fontWeight: 600 } }, o.progress.text),
          h('div', { style: { width: '100%', height: 6, borderRadius: 999, background: '#e4e4e4', overflow: 'hidden' } }, h('div', { style: { width: o.progress.width + '%', height: '100%', borderRadius: 999, background: TEAL, transition: 'width .6s ease' } })))
      : h('nav', { className: 'pk-staffnav', style: { display: 'flex', gap: 4, overflowX: 'auto', flex: '1 1 320px', minWidth: 0 } },
          o.tabs.map(t => { const on = t === o.active; return h('span', { key: t, onClick: () => { this.setState({ sTab: t, acView: null }); }, style: { whiteSpace: 'nowrap', fontSize: 14, fontWeight: on ? 700 : 500, color: on ? INK : MUT, padding: '20px 12px 17px', cursor: 'pointer', borderBottom: '3px solid ' + (on ? TEAL : 'transparent') } }, t); }));
    const open = this.state.acUserMenu;
    return h('header', { style: { background: '#fff', borderBottom: '1px solid ' + HAIR } },
      h('div', { style: { maxWidth: 1280, margin: '0 auto', padding: '0 16px', display: 'flex', alignItems: 'center', gap: '0 18px', flexWrap: 'wrap', minHeight: 64 } },
        h('span', { onClick: () => this.setState({ sTab: o.tabs[0], acView: null }), style: { cursor: 'pointer', width: 180, flex: 'none' } }, this.brandLogo()),
        nav,
        h('div', { style: { position: 'relative', width: 220, display: 'flex', justifyContent: 'flex-end', flex: 'none' } },
          h('span', { onClick: () => this.setState({ acUserMenu: !open }), style: { display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', padding: '10px 0' } },
            h('span', { style: { height: 36, width: 36, borderRadius: '50%', background: o.accent || 'linear-gradient(180deg,#2BA6DE,#12CD8E)', display: 'grid', placeItems: 'center' } }, this.dashIcon(o.icon || 'printer', '#fff', 18)),
            h('span', { style: { lineHeight: 1.2 } }, h('b', { style: { fontSize: 13.5, display: 'block' } }, u.name || ''), h('span', { style: { fontSize: 12, color: FAINT } }, o.sub || String(u.id || '').replace(/\D/g, '').padStart(5, '0')))),
          open ? h('div', { onClick: e => e.stopPropagation(), style: { position: 'absolute', top: '100%', right: 0, zIndex: 60, background: '#fff', border: '1px solid ' + HAIR, borderRadius: 10, boxShadow: '0 12px 30px rgba(0,0,0,.12)', padding: 14, display: 'flex', flexDirection: 'column', gap: 12, minWidth: 210 } },
            (o.menu || []).concat([['Logout', () => this.logout()]]).map(m => h('span', { key: m[0], onClick: () => { this.setState({ acUserMenu: false }); m[1](); }, style: { fontSize: 13.5, fontWeight: 600, color: m[0] === 'Logout' ? TEAL : INK, cursor: 'pointer' } }, m[0]))) : null)));
  };
  P.acPage = function (o, content) {
    return h('div', { style: { background: '#f4f5f6', minHeight: '100vh', display: 'flex', flexDirection: 'column' } },
      this.acHeader(o),
      h('div', { style: { maxWidth: 1280, width: '100%', margin: '0 auto', padding: '22px 16px 20px', display: 'flex', flexDirection: 'column', gap: 20, flex: 1 } }, content),
      h('div', { style: { maxWidth: 1280, width: '100%', margin: '0 auto', padding: '40px 16px 20px', display: 'flex', gap: 12, alignItems: 'center', fontSize: 13, color: FAINT } }, '© ' + new Date().getFullYear() + ' Printoka.com', h('span', { style: { width: 1, height: 16, background: HAIR } }), h('a', { href: 'mailto:print@printoka.com?subject=Staff%20dashboard%20feedback', style: { color: MUT } }, 'Feedback')),
      this.acModalView(), this.acMsg());
  };
  // dashboard quick-link tile with the live dot
  P.acQuick = function (items) {
    return h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(170px,1fr))', background: '#fff', overflow: 'hidden' } }, items.map(it => {
      const A = this.accent(it.color || 'teal');
      return h('div', { key: it.label, onClick: it.onClick, style: { background: '#fff', padding: 20, position: 'relative', cursor: it.onClick ? 'pointer' : 'default', minHeight: 110, boxShadow: '1px 1px 0 ' + HAIR } },
        h('div', { style: { fontWeight: 700, fontSize: 14 } }, it.label),
        h('div', { style: { fontSize: 34, fontWeight: 600, marginTop: 10, display: 'flex', alignItems: 'center', gap: 14 } }, String(it.value),
          Number(it.value) ? h('span', { className: 'pk-ping', style: { width: 9, height: 9, borderRadius: '50%', background: TEAL, display: 'inline-block' } }) : null),
        h('span', { style: { position: 'absolute', right: 22, bottom: 22, height: 46, width: 46, borderRadius: '50%', background: A[1], display: 'grid', placeItems: 'center' } }, this.dashIcon(it.icon, A[0], 22)));
    }));
  };
  P.acCard = function (children, extra) { return h('div', { style: Object.assign({ background: '#fff', border: '1px solid ' + HAIR, borderRadius: 12, overflow: 'hidden' }, extra || {}) }, children); };
  // collapsible card (details/summary) with optional edit / add action
  P.acC = function (title, children, action) {
    return h('details', { key: title, open: true, className: 'pk-acc', style: { background: '#fff', border: '1px solid ' + HAIR, borderRadius: 12, padding: '0 18px' } },
      h('summary', { style: { padding: '13px 0', fontWeight: 600, fontSize: 14, display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', listStyle: 'none' } }, title,
        action ? h('span', { title: action.label, onClick: e => { e.preventDefault(); e.stopPropagation(); action.onClick(); }, style: { marginLeft: 'auto', padding: 6, borderRadius: 6, cursor: 'pointer', fontSize: 15, color: MUT } }, action.icon === 'add' ? '＋' : '✎') : null,
        h('span', { className: 'pk-acc-chev', style: { marginLeft: action ? 0 : 'auto', color: FAINT, fontSize: 11 } }, '▼')),
      h('div', { style: { padding: '16px 0 18px', borderTop: '1px solid ' + HAIR, display: 'flex', flexDirection: 'column', gap: 14, fontSize: 13 } }, children));
  };
  P.acDL = function (rows) { return h('dl', { style: { display: 'grid', gridTemplateColumns: 'minmax(110px,40%) 1fr', gap: '8px 12px', margin: 0 } }, rows.filter(Boolean).map((r, i) => [h('dt', { key: 't' + i, style: { color: FAINT } }, r[0]), h('dd', { key: 'd' + i, style: { margin: 0, color: INK, wordBreak: 'break-word' } }, r[1] == null || r[1] === '' ? '—' : r[1])])); };
  // item specification: "Label: value" lines as a definition list, free text as-is
  P.acSpec = function (spec) {
    const lines = String(spec || '').split(/\s·\s|\n/).map(s => s.trim()).filter(Boolean);
    const pairs = lines.map(l => { const i = l.indexOf(': '); return i > 0 ? [l.slice(0, i), l.slice(i + 2)] : null; });
    if (lines.length && pairs.every(Boolean)) return this.acDL(pairs);
    return h('div', { style: { whiteSpace: 'pre-wrap', lineHeight: 1.7, color: MUT } }, lines.join('\n') || '—');
  };
  P.acStatusList = function (items) {
    if (!items || !items.length) return h('div', { style: { color: FAINT } }, 'Nothing yet.');
    return h('div', { style: { display: 'flex', flexDirection: 'column' } }, items.map((s, i) => h('div', { key: i, style: { display: 'flex', gap: 12, alignItems: 'center', padding: i === 0 ? '0 0 8px' : i === items.length - 1 ? '8px 0 0' : '8px 0', position: 'relative' } },
      i ? h('span', { style: { position: 'absolute', left: 3, top: 0, height: '50%', width: 2, background: '#d8d8d8' } }) : null,
      h('span', { style: { width: 8, height: 8, borderRadius: '50%', background: i === 0 ? TEAL : '#c9c9c9', flex: 'none', zIndex: 1 } }),
      h('div', { style: { display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 } }, h('b', null, s.title), h('span', { title: when(s.at), style: { fontSize: 12, color: FAINT } }, ago(s.at) + ' ago' + (s.by && s.by !== 'system' ? ' by ' + s.by : '')), s.text ? h('span', { style: { fontSize: 12, color: MUT } }, s.text) : null),
      i < items.length - 1 ? h('span', { style: { position: 'absolute', left: 3, bottom: 0, height: '50%', width: 2, background: '#d8d8d8' } }) : null)));
  };
  // single page: crumbs · title + pill · main + aside
  P.acSingle = function (o, main, aside) {
    return [
      h('div', { key: 'hd', style: { display: 'flex', flexDirection: 'column', gap: 4 } },
        h('p', { style: { margin: 0, fontSize: 13, fontWeight: 600, display: 'flex', gap: 8 } },
          h('span', { onClick: () => this.setState({ acView: null, sTab: o.home }), style: { color: TEAL, cursor: 'pointer' } }, 'Dashboard'), h('span', { style: { color: FAINT } }, '/'),
          h('span', { onClick: () => this.setState({ acView: null, sTab: o.type }), style: { color: TEAL, cursor: 'pointer' } }, o.type)),
        h('div', { style: { display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' } }, h('h1', { style: { fontSize: 34, fontWeight: 600, margin: 0, letterSpacing: '-.02em' } }, o.title), o.status ? this.pillDot(o.status, BADGE(o.status)) : null)),
      h('div', { key: 'bd', className: 'pk-acsingle', style: { display: 'flex', gap: 20, alignItems: 'flex-start', flexWrap: 'wrap' } },
        h('div', { style: { flex: '1 1 520px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 20 } }, main),
        h('div', { style: { flex: '1 1 300px', maxWidth: 360, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 20 } }, aside)),
    ];
  };
  // list page: title · filter bar (search · date · status · reset · extra) · card table
  P.acList = function (o) {
    const k = o.key, q = String(this.state[k + '_q'] || '').toLowerCase(), dsel = this.state[k + '_d'] || 'All dates', ssel = this.state[k + '_s'] || 'All status';
    const DAYS = { 'Last month': 31, 'Last 3 months': 92, 'Last 12 months': 366 };
    const rows = (o.rows || []).filter(r => (!q || JSON.stringify(r.search || '').toLowerCase().indexOf(q) >= 0) && (ssel === 'All status' || r.status === ssel) && (!DAYS[dsel] || Date.now() - Date.parse(r.date) <= DAYS[dsel] * 864e5));
    const statuses = Array.from(new Set((o.rows || []).map(r => r.status).filter(Boolean)));
    return [
      h('h1', { key: 't', style: { fontSize: 34, fontWeight: 600, margin: '6px 0 0', letterSpacing: '-.02em' } }, o.title),
      h('div', { key: 'f', style: { display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' } },
        h('input', { placeholder: 'Search', value: this.state[k + '_q'] || '', onChange: e => this.setField(k + '_q', e.target.value), style: pillInp }),
        h('select', { value: dsel, onChange: e => this.setField(k + '_d', e.target.value), style: pillInp }, ['All dates', 'Last month', 'Last 3 months', 'Last 12 months'].map(x => h('option', { key: x }, x))),
        h('select', { value: ssel, onChange: e => this.setField(k + '_s', e.target.value), style: pillInp }, ['All status'].concat(statuses).map(x => h('option', { key: x }, x))),
        h('span', { onClick: () => this.setState({ [k + '_q']: '', [k + '_d']: 'All dates', [k + '_s']: 'All status' }), style: { fontSize: 13, fontWeight: 600, cursor: 'pointer', color: INK, padding: '0 8px' } }, '↺ Reset'),
        o.action ? h('span', { style: { marginLeft: 'auto' } }, o.action) : null),
      h('div', { key: 'tb' }, this.dataCard(o.cols.map(c => typeof c === 'string' ? { label: c } : c), rows.map(r => r.cells), { minWidth: 900, empty: o.empty || 'No data available in table' })),
    ];
  };
  // period metric: current range total vs the range before it
  P.acMetric = function (series, keys, months, type) {
    const cur = keys.slice(-months), prev = keys.slice(-months * 2, -months);
    const vals = ks => ks.map(k => series[k]).filter(v => v != null);
    const agg = ks => { const v = vals(ks); if (!v.length) return null; const s = v.reduce((a, b) => a + b, 0); return type === 'percent' ? Math.round(s / v.length) : s; };
    const c = agg(cur), p = agg(prev);
    const change = p ? Math.round((c - p) / Math.abs(p) * 100) : null;
    return { value: c, change, text: change == null ? 'N/A' : (change >= 0 ? '+' : '') + change + '%', up: change == null ? null : change >= 0 };
  };
  P.acMetricHead = function (label, m, type) {
    const fmt = v => v == null ? '—' : type === 'currency' ? this.rm(v) : type === 'percent' ? v + '%' : String(v);
    return h('div', { style: { display: 'flex', flexDirection: 'column', gap: 4 } }, h('div', { style: { fontSize: 13, fontWeight: 600, color: MUT } }, label),
      h('div', { style: { display: 'flex', alignItems: 'center', gap: 8 } }, h('span', { style: { fontSize: 30, fontWeight: 600 } }, fmt(m.value)),
        h('span', { style: { fontSize: 12, fontWeight: 700, borderRadius: 999, padding: '2px 8px', background: m.up == null ? '#f1f3f5' : m.up ? '#e6f4ea' : '#fdecec', color: m.up == null ? MUT : m.up ? '#3d8b40' : '#c71917' } }, m.text)));
  };
  P.acRange = function (key) { const v = Number(this.state[key] || 6); return h('select', { value: String(v), onChange: e => this.setField(key, e.target.value), style: pillInp }, [[3, 'Last 3 months'], [6, 'Last 6 months'], [12, 'Last 12 months']].map(o => h('option', { key: o[0], value: String(o[0]) }, o[1]))); };
  P.acChart = function (series, keys, labels, months) { const ks = keys.slice(-months); return this.lineChart(ks.map(k => (labels[k] || k).slice(0, 3).toUpperCase()), ks.map(k => series[k] || 0), { h: 300 }); };

  // modal (original mmodal)
  P.acModalView = function () {
    const m = this.state.acModal; if (!m) return null;
    const close = () => this.setState({ acModal: null });
    return h('div', { key: 'acmd', onClick: close, style: { position: 'fixed', inset: 0, zIndex: 120, background: 'rgba(15,20,25,.45)', display: 'grid', placeItems: 'center', padding: 16, overflow: 'auto' } },
      h('div', { onClick: e => e.stopPropagation(), role: 'dialog', 'aria-label': m.title, style: { background: '#fff', borderRadius: 14, width: '100%', maxWidth: m.wide ? 720 : 520, maxHeight: '92vh', overflow: 'auto', boxShadow: '0 24px 60px rgba(0,0,0,.3)' } },
        h('div', { style: { display: 'flex', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid ' + HAIR } }, h('h2', { style: { fontSize: 18, margin: 0, fontWeight: 600 } }, m.title), h('span', { onClick: close, style: { marginLeft: 'auto', fontSize: 22, cursor: 'pointer', color: FAINT } }, '×')),
        h('div', { style: { padding: 20, display: 'flex', flexDirection: 'column', gap: 16 } }, typeof m.body === 'function' ? m.body() : m.body)));
  };
  P.acF = function (k) { return (this.state.acForm || {})[k] || ''; };
  P.acSetF = function (k, v) { this.setState(st => ({ acForm: Object.assign({}, st.acForm, { [k]: v }) })); };
  P.acReadFile = function (file) { return new Promise(res => { if (!file) return res(null); const r = new FileReader(); r.onload = () => res({ name: file.name, data: r.result }); r.readAsDataURL(file); }); };

  // ================================================================== OUTLET (original account/outlet/*)
  const OUT_TABS = ['Dashboard', 'Sales performance', 'Orders', 'Custom quotes'];
  P.s_outlet = function () {
    const u = this.state.user || {};
    const v = this.state.acView;
    const tab = OUT_TABS.indexOf(this.state.sTab) >= 0 ? this.state.sTab : 'Dashboard';
    const shell = { tabs: OUT_TABS, active: v && v.kind === 'individual' ? 'Sales performance' : tab, icon: 'printer', accent: 'linear-gradient(180deg,#2BA6DE,#12CD8E)',
      menu: [['Dashboard', () => this.setState({ acView: null, sTab: 'Dashboard' })], ['Individual report', () => this.acOpen({ kind: 'individual' })]] };
    let content;
    if (v && v.kind === 'order') { const d = this.acGet('ord_' + v.id, '/api/outlet/orders/' + encodeURIComponent(v.id)); shell.progress = d && d.order && d.order.progress; content = this.outOrder(d); }
    else if (v && (v.kind === 'quote' || v.kind === 'newquote')) { const d = v.kind === 'quote' ? this.acGet('q_' + v.id, '/api/outlet/quotes/' + encodeURIComponent(v.id)) : { quote: null }; shell.progress = v.kind === 'newquote' ? { text: 'Quote Details - Step 1 of 4', width: 25 } : d && d.quote && d.quote.progress; content = this.outQuote(d, v); }
    else if (v && v.kind === 'individual') content = this.outIndividual();
    else if (tab === 'Sales performance') content = this.outSales();
    else if (tab === 'Orders') content = this.outOrders();
    else if (tab === 'Custom quotes') content = this.outQuotes();
    else content = this.outDashboard();
    return this.acPage(shell, content);
  };
  P.outDashboard = function () {
    const d = this.acGet('out_dash', '/api/outlet/dashboard') || {};
    const perf = (this.acGet('out_perf', '/api/outlet/performance') || {}).performance;
    const months = Number(this.state.outRange || 6);
    const keys = perf ? perf.months.map(m => m.key) : [], labels = {}; if (perf) perf.months.forEach(m => { labels[m.key] = m.label; });
    const m = perf ? this.acMetric(perf.sales, keys, months) : { value: null, text: 'N/A', up: null };
    return [this.acCard([
      this.acQuick([
        { label: 'Quote to follow up', value: d.followUp || 0, icon: 'edit-3', color: 'teal', onClick: () => this.setState({ sTab: 'Custom quotes', oq_s: 'Not followed up' }) },
        { label: 'Orders', value: d.orders || 0, icon: 'file', color: 'red', onClick: () => this.setState({ sTab: 'Orders' }) },
        { label: 'Incoming', value: d.incoming || 0, icon: 'check', color: 'teal', onClick: () => this.setState({ sTab: 'Orders', oo_s: 'Shipped to Outlet' }) },
        { label: 'Delivery', value: d.delivery || 0, icon: 'truck', color: 'orange', onClick: () => this.setState({ sTab: 'Orders', oo_s: 'Ready for Collect' }) }]),
      h('div', { key: 'ch', style: { padding: 20, borderTop: '1px solid ' + HAIR } },
        h('div', { style: { display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 14, alignItems: 'flex-start' } }, this.acMetricHead('Sales amount', m, 'currency'),
          h('span', { style: { display: 'flex', gap: 10, alignItems: 'center' } }, this.acRange('outRange'), h('span', { onClick: () => this.setState({ sTab: 'Sales performance' }), style: { fontWeight: 700, color: TEAL, cursor: 'pointer', fontSize: 13.5 } }, 'Sales performance ›'))),
        h('div', { style: { marginTop: 24 } }, perf ? this.acChart(perf.sales, keys, labels, months) : h('div', { style: { color: FAINT } }, 'Loading…'))),
      h('div', { key: 'nu', style: { padding: 20, borderTop: '1px solid ' + HAIR, display: 'flex', justifyContent: 'flex-end' } }, Btn('＋ Create new user', () => this.outNewUser(), 'primary')),
    ]), this.notifPanel()];
  };
  P.outNewUser = function () {
    const f = k => this.acF(k), set = (k, v) => this.acSetF(k, v);
    const body = () => [
      h('div', { key: 'g', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 12 } },
        FG('First name', h('input', { value: f('firstName'), onChange: e => set('firstName', e.target.value), style: inp }), 1), FG('Last name', h('input', { value: f('lastName'), onChange: e => set('lastName', e.target.value), style: inp })),
        FG('Email', h('input', { type: 'email', value: f('email'), onChange: e => set('email', e.target.value), style: inp }), 1), FG('Phone', h('input', { value: f('phone'), onChange: e => set('phone', e.target.value), style: inp }), 1),
        FG('Company', h('input', { value: f('company'), onChange: e => set('company', e.target.value), style: inp })), FG('Street address', h('input', { value: f('address'), onChange: e => set('address', e.target.value), style: inp })),
        FG('Town / City', h('input', { value: f('city'), onChange: e => set('city', e.target.value), style: inp })), FG('Postcode', h('input', { value: f('postcode'), onChange: e => set('postcode', e.target.value), style: inp })),
        FG('State', h('input', { value: f('state'), onChange: e => set('state', e.target.value), style: inp })), FG('Country', h('select', { value: f('country') || 'MY', onChange: e => set('country', e.target.value), style: inp }, [['MY', 'Malaysia'], ['SG', 'Singapore'], ['BN', 'Brunei']].map(c => h('option', { key: c[0], value: c[0] }, c[1]))))),
      h('label', { key: 'p', style: { display: 'flex', gap: 8, fontSize: 13, color: MUT } }, h('input', { type: 'checkbox', checked: !!f('promo'), onChange: e => set('promo', e.target.checked) }), 'Receive exclusive offers and promotions from Printoka.'),
      h('div', { key: 'b' }, Btn('Create user', () => this.aFetchJ('/api/customers', Object.assign({ country: 'MY' }, this.state.acForm)).then(d => { if (this.acDone(d, 'Account created for ' + (d.customer && d.customer.email) + '. Temporary password: ' + d.tempPassword + ' (also emailed).')) this.setState({ acModal: null, acForm: {} }); }), 'primary', !f('email') || !f('firstName'))),
    ];
    this.setState({ acModal: { title: 'Create new user', body, wide: true }, acForm: {} });
  };
  P.outOrders = function () {
    const list = (this.acGet('out_orders', '/api/outlet/orders') || {}).orders;
    if (!list) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    return this.acList({ key: 'oo', title: 'Orders', cols: ['Date', 'Order', 'Status', 'Customer', { label: 'Amount', right: true }],
      rows: list.map(o => ({ date: o.date, status: o.status, search: [o.id, o.customer, o.fromQuote], cells: [dmy(o.date), h('span', { onClick: () => this.acOpen({ kind: 'order', id: o.id }), style: { color: TEAL, fontWeight: 600, cursor: 'pointer' } }, '#' + o.id.replace(/^PO-/, '')), this.pillDot(o.status, BADGE(o.status)), o.customer, this.rm(o.total)] })) });
  };
  P.outQuotes = function () {
    const list = (this.acGet('out_quotes', '/api/outlet/quotes') || {}).quotes;
    if (!list) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    return this.acList({ key: 'oq', title: 'Custom quotes', cols: ['Date', 'Quote', 'Status', 'Product', { label: 'Amount', right: true }], action: Btn('＋ New Quote', () => this.acOpen({ kind: 'newquote' }), 'primary'),
      rows: list.map(q => ({ date: q.date, status: q.status, search: [q.id, q.product, q.customerName], cells: [dmy(q.date), h('span', { onClick: () => this.acOpen({ kind: 'quote', id: q.id }), style: { color: TEAL, fontWeight: 600, cursor: 'pointer' } }, q.id), this.pillDot(q.status, BADGE(q.status)), q.product, q.price != null ? this.rm(q.price) : ''] })) });
  };
  // ---- order single (orders-single.pug)
  P.outOrder = function (d) {
    if (!d) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    if (d.error) return [h('div', { key: 'e', style: { color: '#c0392b' } }, d.error)];
    const o = d.order, id = o.id;
    const refresh = r => { if (this.acDone(r, 'Updated.')) { this.acDrop('ord_' + id); this.acDrop('out_'); } };
    const act = key => this.aFetchJ('/api/outlet/orders/' + encodeURIComponent(id) + '/status', { status: key }).then(r => refresh(r));
    const files = o.files || [];
    const main = [
      o.nextActions && o.nextActions.length ? this.acC('Status', h('div', { style: { display: 'flex', flexDirection: 'column', gap: 8 } }, o.nextActions.map(a => Btn(a.label, () => act(a.key), 'block')))) : null,
      o.issues && o.issues.length ? this.acC('Issues', o.issues.map((t, i) => h('p', { key: i, style: { margin: 0 } }, t))) : null,
      o.delivery ? this.acC('Delivery Details', this.acDL(o.delivery.map((x, i) => ['Tracking Number' + (o.delivery.length > 1 ? ' ' + (i + 1) : ''), (x.tracking || '—') + (x.courier ? ' · ' + x.courier : '') + (x.to ? ' → ' + x.to : '')]))) : null,
      this.acC('Items', (o.items || []).map((it, i) => h('div', { key: i, style: { display: 'flex', flexDirection: 'column', gap: 10, borderTop: i ? '1px solid #d9d9d9' : 'none', paddingTop: i ? 16 : 0 } },
        h('b', null, it.product),
        this.acSpec(it.spec),
        h('hr', { style: { border: 0, borderTop: '1px solid ' + HAIR, margin: 0 } }),
        this.acDL([['Quantity', (it.qty || 0).toLocaleString()], ['Price', this.rm(it.unitPrice)], ['Total', h('b', null, this.rm(it.lineTotal))]]),
        (files.filter(f => f.kind === 'artwork' && f.line === i + 1).length || (it.artworks || []).length) ? h('div', { style: { background: ALT, borderRadius: 6, padding: 12, display: 'flex', flexDirection: 'column', gap: 8 } },
          files.filter(f => f.kind === 'artwork' && f.line === i + 1).map(f => h('span', { key: f.id, onClick: () => this.openOrderFile(id, f), style: { color: TEAL, fontWeight: 700, cursor: 'pointer' } }, '📄 ' + f.name)),
          (it.artworks || []).filter(a => !files.some(f => f.name === a)).map((a, k) => h('span', { key: 'n' + k, style: { color: MUT } }, '📄 ' + a + ' (not uploaded)'))) : null))),
    ];
    const addr = o.shipTo || o.billing || o.customer || {};
    const aside = [
      this.acC('Address', [h('b', { key: 'n' }, (addr.name || (o.customer && o.customer.name) || '')),
        (o.customer && o.customer.phone) ? h('a', { key: 'p', href: 'https://wa.me/' + String(o.customer.phone).replace(/\D/g, '').replace(/^0/, '60'), target: '_blank', rel: 'noopener', style: { color: TEAL, fontWeight: 600 } }, o.customer.phone) : null,
        h('p', { key: 'a', style: { margin: 0, color: MUT, lineHeight: 1.6 } }, o.fulfillment && o.fulfillment.method === 'pickup' ? 'Self-pickup at ' + (o.fulfillment.outlet || 'outlet') : (typeof addr === 'string' ? addr : [addr.line1, addr.line2, [addr.postcode, addr.city].filter(Boolean).join(' '), addr.state].filter(Boolean).join(', '))),
        (o.customer && o.customer.email) ? h('a', { key: 'e', href: 'mailto:' + o.customer.email, style: { color: TEAL, fontWeight: 600 } }, o.customer.email) : null], { icon: 'edit', label: 'Edit address', onClick: () => this.outEditAddress(o) }),
      this.acC('Statuses', this.acStatusList(o.statusLog), { icon: 'add', label: 'Add note', onClick: () => this.outAddNote(o) }),
      this.acC('PDF', [h('span', { key: 's', onClick: () => this.openDoc(id, 'slip'), style: { color: TEAL, fontWeight: 700, cursor: 'pointer' } }, '📄 Order slip'), o.canInvoice ? h('span', { key: 'i', onClick: () => this.openDoc(id, 'invoice'), style: { color: TEAL, fontWeight: 700, cursor: 'pointer' } }, '📄 Invoice') : null]),
      this.acC('General', this.acDL([['Date created', when(o.createdAt)], o.payment && o.payment.paidAt ? ['Paid on', h('span', null, when(o.payment.paidAt), h('br'), h('span', { style: { fontSize: 12, color: FAINT } }, 'via ' + String(o.payment.gateway || o.payment.method || '').toLowerCase()))] : null, o.fromQuote ? ['Quote', o.fromQuote] : null])),
    ];
    return this.acSingle({ home: 'Dashboard', type: 'Orders', title: '#' + id.replace(/^PO-/, ''), status: o.outletStatus }, main, aside);
  };
  P.outAddNote = function (o) {
    this.setState({ acForm: {}, acModal: { title: 'Add note', body: () => [
      FG('Note', h('textarea', { rows: 8, value: this.acF('note'), onChange: e => this.acSetF('note', e.target.value), style: Object.assign({}, inp, { resize: 'vertical' }) }), 1),
      h('p', { key: 'h', style: { margin: '-8px 0 0', fontSize: 12.5, color: FAINT } }, 'Only you and other staff can see note'),
      h('div', { key: 'b' }, Btn('Add note', () => this.aFetchJ('/api/outlet/orders/' + encodeURIComponent(o.id) + '/note', { note: this.acF('note') }).then(r => { if (this.acDone(r, 'Note added.')) { this.setState({ acModal: null }); this.acDrop('ord_' + o.id); } }), 'primary', !this.acF('note')))] } });
  };
  P.outEditAddress = function (o) {
    const a = (o.shipTo && typeof o.shipTo === 'object') ? o.shipTo : {};
    this.setState({ acForm: { name: a.name || (o.customer && o.customer.name) || '', phone: a.phone || '', line1: a.line1 || '', line2: a.line2 || '', postcode: a.postcode || '', city: a.city || '', state: a.state || '', country: a.country || 'MY' }, acModal: { title: 'Edit address', wide: true, body: () => [
      h('div', { key: 'g', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 12 } },
        ['name:Full name', 'phone:Phone', 'line1:Street address', 'line2:Apartment, suite, unit', 'postcode:Postcode', 'city:Town / City', 'state:State'].map(x => { const p = x.split(':'); return h('div', { key: p[0] }, FG(p[1], h('input', { value: this.acF(p[0]), onChange: e => this.acSetF(p[0], e.target.value), style: inp }), p[0] !== 'line2')); })),
      h('div', { key: 'b' }, Btn('Submit', () => this.aFetchJ('/api/outlet/orders/' + encodeURIComponent(o.id) + '/address', this.state.acForm).then(r => { if (this.acDone(r, 'Address updated.')) { this.setState({ acModal: null }); this.acDrop('ord_' + o.id); } }), 'primary'))] } });
  };
  // ---- quote single + new quote (custom-quotes-single.pug)
  P.outQuote = function (d, v) {
    if (!d) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    if (d.error) return [h('div', { key: 'e', style: { color: '#c0392b' } }, d.error)];
    const q = d.quote, isNew = v.kind === 'newquote';
    const mode = isNew ? 'edit-spec' : (this.state.acEdit || (q && q.state));
    const done = (r, msg, reopen) => { if (!this.acDone(r, msg)) return; this.setState({ acEdit: null, acModal: null }); this.acDrop('out_'); if (r.quote) { this._ac['q_' + r.quote.id] = { data: { quote: r.quote } }; if (reopen) this.acOpen({ kind: 'quote', id: r.quote.id }); else this.forceUpdate(); } };
    const main = [];
    if (q && q.state === 'rejected') main.push(this.acC('Rejected reason', h('p', { style: { margin: 0, whiteSpace: 'pre-wrap' } }, q.rejectReason)));
    if (q && (q.lastFollowUp || q.state === 'follow-up')) main.push(this.acC('Follow-Up', [
      q.state === 'follow-up' ? h('div', { key: 'b', style: { display: 'flex', gap: 8 } }, Btn('Followed up', () => this.aFetchJ('/api/outlet/quotes/' + q.id + '/follow-up', {}).then(r => done(r, 'Quote followed up successfully')), 'primary'), Btn('Rejected', () => this.outRejectQuote(q, done))) : null,
      h('p', { key: 't', style: { margin: 0 } }, q.lastFollowUp ? ['Last follow up at ', h('b', { key: 'a', title: when(q.lastFollowUp.at) }, ago(q.lastFollowUp.at)), ' ago by ', h('b', { key: 'b' }, q.lastFollowUp.by)] : 'Not follow up yet.')]));
    if (q && mode === 'waiting-quote') main.push(this.acC('Quote', h('div', null, this.pillDot('Awaiting HQ quote', 'bad'))));
    if (q && mode === 'edit-quote') {
      const F = k => this.acF(k) !== '' ? this.acF(k) : (k === 'price' ? (q.price || '') : k === 'weight' ? (q.weight || '') : k === 'currency' ? (q.currency || 'MYR') : '');
      main.push(this.acC('Quote', [
        FG('Weight', h('input', { value: F('weight'), onChange: e => this.acSetF('weight', e.target.value), style: inp }), 1),
        FG('Price', h('div', { style: { display: 'flex' } }, h('select', { value: F('currency'), onChange: e => this.acSetF('currency', e.target.value), style: Object.assign({}, inp, { width: 100, borderRadius: '8px 0 0 8px', borderRight: 0 }) }, ['MYR', 'SGD', 'BND'].map(c => h('option', { key: c }, c))), h('input', { value: F('price'), onChange: e => this.acSetF('price', e.target.value), style: Object.assign({}, inp, { borderRadius: '0 8px 8px 0' }) })), 1),
        h('div', { key: 'b', style: { display: 'flex', gap: 8 } }, Btn('Submit', () => this.aFetchJ('/api/outlet/quotes/' + q.id + '/price', { weight: F('weight'), price: F('price'), currency: F('currency') }).then(r => done(r, 'Quote submited successfully')), 'primary'), Btn('Cancel', () => this.setState({ acEdit: null })))]));
    }
    if (mode === 'edit-spec') {
      const F = k => this.acF(k) !== '' ? this.acF(k) : (q ? ({ product: q.product, specifications: q.spec, requesterId: q.requester && q.requester.id })[k] || '' : '');
      const cust = (this.acGet('cust_' + (this.state.acCustQ || ''), '/api/outlet/customers?q=' + encodeURIComponent(this.state.acCustQ || '')) || {}).customers || [];
      const reqLabel = F('requesterId') ? ((cust.find(c => c.value === F('requesterId')) || {}).label || (q && q.requester ? q.requester.name + ' (' + q.requester.email + ')' : F('requesterId'))) : '';
      main.push(this.acC('Specifications', [
        FG('Product', h('input', { value: F('product'), onChange: e => this.acSetF('product', e.target.value), style: inp }), 1),
        FG('Specifications', h('textarea', { rows: 8, value: F('specifications'), onChange: e => this.acSetF('specifications', e.target.value), style: Object.assign({}, inp, { resize: 'vertical' }) }), 1),
        FG('Requester', h('div', { style: { display: 'flex', flexDirection: 'column', gap: 6 } },
          reqLabel ? h('div', { style: { fontSize: 13, background: ALT, borderRadius: 8, padding: '8px 12px' } }, reqLabel) : null,
          h('input', { placeholder: 'Search customer name or email…', value: this.state.acCustQ || '', onChange: e => this.setState({ acCustQ: e.target.value }), style: inp }),
          h('div', { style: { maxHeight: 160, overflow: 'auto', border: '1px solid ' + LINE, borderRadius: 8 } }, cust.map(c => h('div', { key: c.value, onClick: () => this.acSetF('requesterId', c.value), style: { padding: '8px 12px', fontSize: 13, cursor: 'pointer', background: F('requesterId') === c.value ? '#fdf2f2' : '#fff', borderTop: '1px solid ' + LINE } }, c.label)))), 1),
        h('div', { key: 'aw', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 12 } },
          FG('Artwork name', h('input', { value: this.acF('artworkName'), onChange: e => this.acSetF('artworkName', e.target.value), style: inp })),
          FG('Artwork file', h('input', { type: 'file', onChange: e => this.acReadFile(e.target.files[0]).then(f => { if (f) { this.acSetF('artworkData', f.data); this.acSetF('artworkFileName', f.name); } }), style: inp }))),
        h('div', { key: 'b', style: { display: 'flex', gap: 8 } }, Btn(isNew ? 'Next' : 'Save', () => this.aFetchJ(isNew ? '/api/outlet/quotes' : '/api/outlet/quotes/' + q.id + '/spec', { product: F('product'), specifications: F('specifications'), requesterId: F('requesterId'), artworkName: this.acF('artworkName'), artworkData: this.acF('artworkData'), artworkFileName: this.acF('artworkFileName') }).then(r => done(r, 'Specifications updated successfully', isNew)), 'primary'), !isNew ? Btn('Cancel', () => this.setState({ acEdit: null })) : null)]));
    } else if (q) {
      main.push(this.acC('Specifications', [h('b', { key: 'p' }, q.product), h('div', { key: 's', style: { whiteSpace: 'pre-wrap', lineHeight: 1.7 } }, q.spec),
        q.artwork ? h('div', { key: 'a', style: { background: ALT, borderRadius: 6, padding: 12 } }, h('a', { href: '#', onClick: e => { e.preventDefault(); fetch('/api/outlet/quotes/' + q.id + '/artwork', { headers: this.authHeaders() }).then(r => r.ok ? r.blob() : null).then(b => b && this.saveBlob(b, q.artwork.file || q.artwork.name)); }, style: { color: TEAL, fontWeight: 700 } }, '📄 ' + (q.artwork.name || 'File'))) : null],
        q.canEdit ? { icon: 'edit', label: 'Edit specifications', onClick: () => this.setState({ acEdit: 'edit-spec', acForm: {} }) } : null));
    }
    const aside = q ? [
      mode !== 'edit-quote' && q.price != null ? this.acC('Quote', this.acDL([['Weight', q.weight], ['Price', this.rm(q.price)], ['Issued by', q.issuedBy]]), q.canEdit ? { icon: 'edit', label: 'Edit quote', onClick: () => this.setState({ acEdit: 'edit-quote', acForm: {} }) } : null) : null,
      q.statuses && q.statuses.length ? this.acC('Statuses', this.acStatusList(q.statuses.map(s => ({ title: s.status, at: s.at, by: s.by, text: s.note })))) : null,
      q.requester && mode !== 'edit-spec' ? this.acC('Requester', [h('b', { key: 'n' }, q.requester.name), q.requester.phone ? h('a', { key: 'p', href: 'https://wa.me/' + String(q.requester.phone).replace(/\D/g, '').replace(/^0/, '60'), target: '_blank', rel: 'noopener', style: { color: TEAL, fontWeight: 600 } }, q.requester.phone) : null, q.requester.address ? h('p', { key: 'a', style: { margin: 0, color: MUT } }, q.requester.address) : null, h('a', { key: 'e', href: 'mailto:' + q.requester.email, style: { color: TEAL, fontWeight: 600 } }, q.requester.email)], q.canEdit ? { icon: 'edit', label: 'Change requester', onClick: () => this.setState({ acEdit: 'edit-spec', acForm: {} }) } : null) : null] : [];
    return this.acSingle({ home: 'Dashboard', type: 'Custom quotes', title: isNew ? 'New quote' : q.id, status: q ? q.status : null }, main, aside);
  };
  P.outRejectQuote = function (q, done) {
    this.setState({ acForm: {}, acModal: { title: 'Reject reasons', body: () => [FG('Reject reasons', h('textarea', { rows: 8, value: this.acF('reasons'), onChange: e => this.acSetF('reasons', e.target.value), style: Object.assign({}, inp, { resize: 'vertical' }) }), 1),
      h('div', { key: 'b' }, Btn('Submit', () => this.aFetchJ('/api/outlet/quotes/' + q.id + '/reject', { reasons: this.acF('reasons') }).then(r => done(r, 'Quote rejected.')), 'primary', !this.acF('reasons')))] } });
  };
  // ---- sales performance (sales-performance.pug) + individual report (individual-performance.pug)
  P.outSales = function () {
    const perf = (this.acGet('out_perf', '/api/outlet/performance') || {}).performance;
    if (!perf) return [h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')];
    const months = Number(this.state.outRange || 6), keys = perf.months.map(m => m.key), labels = {}; perf.months.forEach(m => { labels[m.key] = m.label; });
    const k12 = keys.slice(-12), m = this.acMetric(perf.sales, keys, months);
    const prods = Object.keys(perf.byProduct);
    return [h('h1', { key: 't', style: { fontSize: 34, fontWeight: 600, margin: '6px 0 0' } }, 'Sales performance report'),
      h('div', { key: 'f', style: { display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' } }, this.acRange('outRange')),
      this.acCard(h('div', { style: { padding: 20 } },
        h('div', { style: { display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: 12 } }, h('div', null, h('div', { style: { fontWeight: 600 } }, 'Outlet sales performance'), h('div', { style: { fontSize: 22, marginTop: 4 } }, labels[keys[keys.length - months]] + ' - ' + labels[keys[keys.length - 1]])),
          h('span', { onClick: () => this.acOpen({ kind: 'individual' }), style: { fontWeight: 700, color: TEAL, cursor: 'pointer', fontSize: 13.5 } }, 'Individual performance report ›')),
        h('div', { style: { margin: '16px 0 0' } }, this.acMetricHead('Sales amount', m, 'currency')),
        h('div', { style: { marginTop: 20 } }, this.acChart(perf.sales, keys, labels, months)))),
      this.acCard([h('p', { key: 't', style: { fontWeight: 700, padding: '14px 18px', margin: 0 } }, 'Product sales details'),
        h('div', { key: 'tb', style: { overflowX: 'auto' } }, h('table', { style: { width: '100%', minWidth: 1000, borderCollapse: 'collapse', fontSize: 13 } },
          h('thead', null, h('tr', null, h('th', { style: { textAlign: 'left', padding: '10px 14px', borderBottom: '1px solid ' + HAIR, width: 240 } }, 'Product'), k12.map(k => h('th', { key: k, style: { textAlign: 'right', padding: '10px 14px', borderBottom: '1px solid ' + HAIR } }, labels[k].replace(' 20', ' '))))),
          h('tbody', null, prods.length ? prods.map(p => h('tr', { key: p }, h('td', { style: { padding: '10px 14px', borderTop: '1px solid ' + LINE } }, p), k12.map(k => h('td', { key: k, style: { textAlign: 'right', padding: '10px 14px', borderTop: '1px solid ' + LINE } }, this.rm(perf.byProduct[p][k] || 0))))) : h('tr', null, h('td', { colSpan: 13, style: { padding: 18, color: FAINT } }, 'No paid orders yet.'))),
          h('tfoot', null, h('tr', null, h('td', { style: { padding: '10px 14px', fontWeight: 700, borderTop: '1px solid ' + HAIR } }, 'Total'), k12.map(k => h('td', { key: k, style: { textAlign: 'right', padding: '10px 14px', fontWeight: 700, borderTop: '1px solid ' + HAIR } }, this.rm(perf.sales[k] || 0)))))))])];
  };
  P.outIndividual = function () {
    const staff = (this.acGet('out_staff', '/api/outlet/staff') || {}).staff || [];
    const sid = this.state.outStaff || '';
    const pd = this.acGet('out_ind_' + sid, '/api/outlet/performance?individual=1' + (sid ? '&staff=' + encodeURIComponent(sid) : ''));
    const perf = pd && (pd.error ? { error: pd.error } : pd.performance);
    const months = Number(this.state.outRange || 6);
    const head = [h('h1', { key: 't', style: { fontSize: 34, fontWeight: 600, margin: '6px 0 0' } }, 'Individual performance report'),
      h('div', { key: 'f', style: { display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' } },
        staff.length ? h('select', { value: sid, onChange: e => this.setField('outStaff', e.target.value), style: pillInp }, [h('option', { key: '', value: '' }, 'Me')].concat(staff.map(s => h('option', { key: s.id, value: s.id }, s.name)))) : null,
        this.acRange('outRange'), h('span', { onClick: () => this.setState({ acView: null, sTab: 'Sales performance' }), style: { marginLeft: 'auto', fontWeight: 700, color: TEAL, cursor: 'pointer', fontSize: 13.5 } }, 'Outlet performance report ›'))];
    if (!perf) return head.concat([h('div', { key: 'l', style: { color: FAINT } }, 'Loading…')]);
    if (perf.error) return head.concat([h('div', { key: 'e', style: { color: '#c0392b' } }, perf.error)]);
    const keys = perf.months.map(m => m.key), labels = {}; perf.months.forEach(m => { labels[m.key] = m.label; });
    const METRICS = [['Sales amount', perf.sales, 'currency', 'dollar-sign', 'red'], ['Orders', perf.orders, 'number', 'file', 'red'], ['New accounts', perf.newAccounts, 'number', 'user-plus', 'orange'], ['Quotes issued', perf.quotesIssued, 'number', 'edit-3', 'teal'], ['Quotes followed up', perf.quotesFollowedUp, 'number', 'phone', 'teal'], ['Sales conversion', perf.conversion, 'percent', 'check', 'teal']];
    return head.concat([
      this.acCard([h('div', { key: 'h', style: { padding: 20 } }, h('p', { style: { fontWeight: 700, margin: 0 } }, 'Key metrics' + (perf.staff ? ' — ' + perf.staff : '')), h('div', { style: { fontSize: 22, marginTop: 4 } }, labels[keys[keys.length - months]] + ' - ' + labels[keys[keys.length - 1]])),
        h('div', { key: 'g', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 1, background: HAIR, borderTop: '1px solid ' + HAIR } }, METRICS.map(mm => { const A = this.accent(mm[4]); return h('div', { key: mm[0], style: { background: '#fff', padding: 20, position: 'relative' } }, this.acMetricHead(mm[0], this.acMetric(mm[1], keys, months, mm[2]), mm[2]), h('span', { style: { position: 'absolute', right: 20, bottom: 20, height: 44, width: 44, borderRadius: '50%', background: A[1], display: 'grid', placeItems: 'center' } }, this.dashIcon(mm[3], A[0], 20))); }))]),
    ].concat(METRICS.map(mm => this.acCard(h('div', { style: { padding: 20 } }, this.acMetricHead(mm[0], this.acMetric(mm[1], keys, months, mm[2]), mm[2]), h('div', { style: { marginTop: 20 } }, this.acChart(Object.fromEntries(Object.entries(mm[1]).map(e => [e[0], e[1] == null ? 0 : e[1]])), keys, labels, months)))))));
  };
})();
