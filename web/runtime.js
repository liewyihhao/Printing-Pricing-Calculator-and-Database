/*
 * Printoka custom-stack runtime — provides DCLogic, the React.Component base
 * the design's `class Component extends DCLogic` expects.
 *
 * The design (app.js) builds every screen via renderScreen(); DCLogic.render()
 * paints the shared shell (header, announcement, pages row, spec annotation,
 * footer, chat) from the values renderVals() returns. This replaces the Claude
 * Design {{ }}/sc-if/sc-for templating runtime with plain React — no WordPress,
 * no external design服务, everything served from local /assets.
 */
(function () {
  var h = function (t, p) {
    var args = [t, p];
    for (var i = 2; i < arguments.length; i++) args.push(arguments[i]);
    return React.createElement.apply(React, args);
  };
  var A = function (p) { return (window.__asset ? window.__asset(p) : p); };

  var TEAL = '#E52220', INK = '#212121', MUT = '#616161', HAIR = '#eaeaea', AMBER = '#FF9A2E';

  function img(src, style) { return h('img', { src: A(src), alt: '', style: style }); }

  function header(v) {
    if (v.bareStaff) return null;
    if (v.staff) return h('header', { style: { position: 'sticky', top: 0, zIndex: 60, background: '#fff', borderBottom: '1px solid ' + HAIR } },
      h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '12px 20px', display: 'flex', alignItems: 'center', gap: 12 } },
        h('a', { 'data-go': 'home', style: { display: 'flex', alignItems: 'center', gap: 9, fontWeight: 500, fontSize: 18, letterSpacing: '.16em', color: '#231f20', textDecoration: 'none', cursor: 'pointer' } },
          img('assets/icons/logomark.svg', { height: 24, width: 'auto', display: 'block' }), 'printoka'),
        h('span', { style: { fontSize: 12, color: MUT, borderLeft: '1px solid ' + HAIR, paddingLeft: 12 } }, 'Staff console')));
    return h('div', { style: { position: 'sticky', top: 0, zIndex: 60, display: 'flex', flexDirection: 'column' } },
      h('header', { style: { background: 'rgba(255,255,255,.96)', backdropFilter: 'blur(8px)', borderBottom: '1px solid ' + HAIR } },
        h('div', { role: 'navigation', 'aria-label': 'Primary', style: { maxWidth: 1180, margin: '0 auto', padding: '10px 20px', minHeight: 64, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '10px 18px' } },
          // logo
          h('a', { 'data-go': 'home', href: '#', onClick: function (e) { e.preventDefault(); }, style: { display: 'flex', alignItems: 'center', gap: 9, fontWeight: 500, fontSize: 18, letterSpacing: '.16em', color: '#231f20', whiteSpace: 'nowrap', textDecoration: 'none' } },
            img('assets/icons/logomark.svg', { height: 26, width: 'auto', display: 'block', flex: 'none' }), 'printoka'),
          // Products mega button
          h('span', { 'data-go': '_mega', style: { display: 'flex', alignItems: 'center', gap: 6, background: TEAL, color: '#fff', fontWeight: 600, fontSize: 13.5, borderRadius: 3, padding: '9px 15px', whiteSpace: 'nowrap', cursor: 'pointer' } },
            v.tProducts, img('assets/icons/dropdown.svg', { height: 7, width: 'auto', display: 'block', filter: 'brightness(0) invert(1)' })),
          // search
          h('div', { style: { display: 'flex', alignItems: 'center', flex: '1 1 260px', minWidth: 120, border: '1px solid ' + HAIR, borderRadius: 3, overflow: 'hidden', color: MUT, fontSize: 13 } },
            h('span', { style: { flex: 1, padding: '0 12px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, v.tSearch),
            h('span', { style: { background: TEAL, padding: '11px 15px', display: 'flex', alignItems: 'center' } },
              img('assets/icons/search.svg', { height: 13, width: 'auto', display: 'block', filter: 'brightness(0) invert(1)' }))),
          // right cluster
          h('div', { style: { display: 'flex', alignItems: 'center', gap: 14, fontSize: 13, color: '#231f20', whiteSpace: 'nowrap' } },
            h('span', { 'data-go': '_locale', style: { display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' } },
              v.localeLabel, img('assets/icons/dropdown.svg', { height: 6, width: 'auto', display: 'block', opacity: .55 })),
            h('span', { style: { width: 1, height: 16, background: HAIR } }),
            v.signedIn
              ? h('span', { 'data-go': 'dash', style: { display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer' } },
                  h('span', { style: { height: 26, width: 26, borderRadius: '50%', background: '#f3f4f6', color: TEAL, display: 'grid', placeItems: 'center', fontSize: 11, fontWeight: 600 } }, (v.userName || '?').slice(0, 2).toUpperCase()),
                  h('span', { style: { fontSize: 10.5, fontWeight: 600, letterSpacing: '.06em', background: 'linear-gradient(90deg,#FF9A2E,#E52220)', color: '#fff', borderRadius: 3, padding: '2px 6px' } }, v.tierLabel))
              : h('span', { 'data-go': 'auth', style: { display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer', fontSize: 13.5, color: '#231f20' } },
                  img('assets/icons/user.svg', { height: 18, width: 'auto', display: 'block' }), 'Login/ Signup'),
            h('span', { 'data-go': 'cart', style: { position: 'relative', display: 'flex', cursor: 'pointer' } },
              img('assets/icons/cart.svg', { height: 19, width: 'auto', display: 'block' }),
              h('span', { style: { position: 'absolute', top: -6, right: -9, background: TEAL, color: '#fff', fontSize: 10, fontWeight: 700, borderRadius: 9, padding: '1px 5px' } }, v.cartCount)),
            h('span', { 'data-go': '_country', style: { display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' } },
              img(v.isSG ? 'assets/icons/flag-sg.jpg' : v.isBN ? 'assets/icons/flag-bn.jpg' : 'assets/icons/flag-my.jpg',
                { height: 15, width: 22, objectFit: 'cover', display: 'block' }), v.countryLabel),
            h('span', { 'data-go': '_mega', style: { display: 'flex', alignItems: 'center', gap: 7, cursor: 'pointer' } },
              v.tMenu, img('assets/icons/menu.svg', { height: 15, width: 'auto', display: 'block' })))),
        // mega panel — categories (each a clickable header) + their products (open the configurator)
        v.megaOpen ? h('div', { style: { borderTop: '1px solid ' + HAIR, background: '#fff', boxShadow: '0 18px 34px rgba(33,33,33,.10)' } },
          h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '24px 20px 28px', display: 'grid', gridTemplateColumns: '150px 1fr', gap: 28 } },
            // left rail: the "Printing" heading + a jump-to-category list (side-bar form)
            h('div', { style: { borderRight: '1px solid ' + HAIR, paddingRight: 20, display: 'flex', flexDirection: 'column', gap: 4 } },
              h('div', { style: { fontSize: 13, fontWeight: 700, color: INK, marginBottom: 6 } }, 'Printing'),
              v.megaCols.map(function (col, ci) {
                return h(col.href ? 'a' : 'span', { key: ci, href: col.href || undefined, 'data-go': col.go, style: { fontSize: 13, color: MUT, padding: '5px 0', cursor: 'pointer', textDecoration: 'none' } }, col.title);
              }),
              h('a', { href: '/products', 'data-go': 'catopen:all', style: { fontSize: 13, fontWeight: 600, color: TEAL, padding: '8px 0 0', cursor: 'pointer', textDecoration: 'none' } }, 'View all products →')),
            // product columns
            h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: '18px 24px' } },
              v.megaCols.map(function (col, ci) {
                return h('div', { key: ci, style: { display: 'flex', flexDirection: 'column', gap: 8 } },
                  h(col.href ? 'a' : 'div', { href: col.href || undefined, 'data-go': col.go, style: { fontSize: 11, fontWeight: 600, letterSpacing: '.08em', textTransform: 'uppercase', color: TEAL, cursor: 'pointer', textDecoration: 'none' } }, col.title),
                  col.items.map(function (it, ii) {
                    return h(it.href ? 'a' : 'div', { key: ii, href: it.href || undefined, 'data-go': it.go, style: { fontSize: 13, color: MUT, cursor: 'pointer', lineHeight: 1.35, textDecoration: 'none' } }, it.n);
                  }));
              })))) : null));
  }

  function announcement(v) {
    var a = (v && v.announcement) || {};
    if (a.hidden) return null;
    return h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '14px 20px 0' } },
      h('div', { style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '10px 20px', padding: '12px 16px', borderRadius: 2, color: '#fff', fontSize: 14, backgroundImage: 'linear-gradient(90deg,#FF9A2E,#F02B29)', boxShadow: '0 1px 3px rgba(33,33,33,.12)' } },
        img('assets/icons/logomark.svg', { height: 34, width: 'auto', display: 'block', filter: 'brightness(0) invert(1)' }),
        h('div', { style: { flex: '1 1 auto', minWidth: 0, lineHeight: 1.35 } }, a.text || 'Members save up to 15% on every order — sign in to see your price. Free delivery on orders over RM 300.'),
        h('a', { 'data-go': a.link || 'membership', style: { display: 'flex', alignItems: 'center', gap: 6, color: '#fff', fontWeight: 500, textDecoration: 'none', whiteSpace: 'nowrap', cursor: 'pointer' } },
          a.cta || 'Find out more', img('assets/icons/arrow-right.svg', { height: 13, width: 'auto', display: 'block', filter: 'brightness(0) invert(1)' }))));
  }

  function pagesRow(v) {
    return h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '14px 20px 0', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' } },
      h('span', { style: { fontSize: 10.5, fontWeight: 600, letterSpacing: '.09em', textTransform: 'uppercase', color: MUT, marginRight: 4 } }, 'Pages'),
      v.screens.map(function (s) {
        var on = s.id === v.activeRoute;
        return h('span', { key: s.id, 'data-go': s.id, style: { font: '500 11.5px Montserrat,sans-serif', fontWeight: on ? 600 : 500, border: '1px solid ' + (on ? TEAL : HAIR), borderRadius: 999, padding: '4px 10px', color: on ? '#fff' : MUT, background: on ? TEAL : '#fff', whiteSpace: 'nowrap', cursor: 'pointer' } }, s.label);
      }));
  }

  function spec(v) {
    if (!v.showSpec) return null;
    return h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '16px 20px 6px', display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' } },
      h('span', { style: { font: '600 11px ui-monospace,Menlo,monospace', background: INK, color: '#fff', borderRadius: 4, padding: '3px 8px' } }, v.specId),
      h('span', { style: { fontSize: 13, color: MUT } }, v.specNote));
  }

  function footer(v) {
    var social = ['FB', 'IG', 'in', 'YT'];
    var flags = [['flag-my.jpg', 'Malaysia'], ['flag-sg.jpg', 'Singapore'], ['flag-bn.jpg', 'Brunei'], ['flag-au.jpg', 'Australia'], ['flag-nz.jpg', 'New Zealand']];
    return h('div', null,
      h('section', { style: { marginTop: 56, background: TEAL, color: '#fff' } },
        h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '30px 20px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(230px,1fr))', gap: 26, alignItems: 'start' } },
          h('div', { style: { display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'center', textAlign: 'center' } },
            h('div', { style: { fontSize: 17, fontWeight: 600 } }, 'Follow us'),
            h('div', { style: { display: 'flex', gap: 10 } }, social.map(function (s, i) {
              return h('a', { key: i, href: '#', onClick: function (e) { e.preventDefault(); }, style: { height: 34, width: 34, borderRadius: '50%', background: 'rgba(255,255,255,.16)', color: '#fff', display: 'grid', placeItems: 'center', fontSize: 12, fontWeight: 600, textDecoration: 'none' } }, s);
            }))),
          h('div', { style: { display: 'flex', flexDirection: 'column', gap: 12, textAlign: 'center' } },
            h('div', { style: { fontSize: 17, fontWeight: 600 } }, 'Subscribe for latest promotion and updates'),
            h('div', { style: { display: 'flex', background: '#fff', borderRadius: 2, overflow: 'hidden' } },
              h('span', { style: { flex: 1, padding: '11px 13px', fontSize: 13, color: MUT, minWidth: 0, textAlign: 'left' } }, 'Your email address'),
              h('span', { style: { padding: '11px 20px', fontSize: 13.5, fontWeight: 600, color: TEAL, whiteSpace: 'nowrap', borderLeft: '1px solid ' + HAIR } }, 'Subscribe'))),
          h('div', { style: { display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'center', textAlign: 'center' } },
            h('div', { style: { fontSize: 17, fontWeight: 600, whiteSpace: 'nowrap' } }, 'Be a Printoka printer'),
            h('a', { 'data-go': 'vendor', href: '#', onClick: function (e) { e.preventDefault(); }, style: { background: '#fff', color: TEAL, fontWeight: 600, fontSize: 13.5, borderRadius: 2, padding: '11px 22px', textDecoration: 'none', whiteSpace: 'nowrap', cursor: 'pointer' } }, 'Join our network')))),
      h('footer', { style: { borderTop: '1px solid #e9ecef', background: '#fff' } },
        h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '40px 20px 30px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(190px,1fr))', gap: 30 } },
          v.footerCols.map(function (col, ci) {
            return h('div', { key: ci, style: { display: 'flex', flexDirection: 'column', gap: 9 } },
              h('div', { style: { fontSize: 11, fontWeight: 600, letterSpacing: '.08em', textTransform: 'uppercase', color: INK } }, col.title),
              col.items.map(function (it, ii) {
                var label = Array.isArray(it) ? it[0] : it, go = Array.isArray(it) ? it[1] : null;
                return h('a', { key: ii, 'data-go': go || undefined, href: '#', onClick: function (e) { e.preventDefault(); }, style: { fontSize: 12.5, color: MUT, textDecoration: 'none', cursor: go ? 'pointer' : 'default' } }, label);
              }));
          }),
          h('div', { style: { display: 'flex', flexDirection: 'column', gap: 12 } },
            h('div', { style: { display: 'flex', alignItems: 'center', gap: 9, fontWeight: 500, fontSize: 17, letterSpacing: '.16em' } },
              img('assets/icons/logomark.svg', { height: 24, width: 'auto', display: 'block', flex: 'none' }), 'printoka'),
            h('div', { style: { fontSize: 11, fontWeight: 600, letterSpacing: '.08em', textTransform: 'uppercase', color: INK } }, 'Contact us'),
            h('div', { style: { display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' } }, flags.map(function (fl, i) {
              return h('img', { key: i, src: A('assets/icons/' + fl[0]), alt: fl[1], style: { height: 16, width: 24, objectFit: 'cover', display: 'block' } });
            })),
            h('a', { href: 'mailto:hello@printoka.com', style: { fontSize: 14, fontWeight: 500, color: TEAL, textDecoration: 'none' } }, 'hello@printoka.com'),
            h('div', { style: { display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, fontWeight: 500, color: INK } },
              img('assets/icons/whatsapp.png', { height: 20, width: 20, display: 'block' }), '+60 3-1234 5678'),
            h('p', { style: { margin: 0, fontSize: 12, color: MUT, lineHeight: 1.7 } },
              h('b', { style: { color: INK } }, 'Working Hours'), h('br'), 'Monday to Friday: 8.30am to 6.00pm', h('br'), 'Weekend and Public Holidays: Closed'))),
        h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '20px 20px 34px', borderTop: '1px solid ' + HAIR, display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 16, alignItems: 'center' } },
          h('div', { style: { display: 'flex', flexDirection: 'column', gap: 8 } },
            h('span', { style: { fontSize: 12, color: MUT, lineHeight: 1.7 } }, 'All rights reserved © 2013–2022 Printoka.com | This website is managed and operated by Yushan Corporation Sdn Bhd (561674-X) | Registered address: Lot 1565, Piasau Industrial Estate, 98000 Miri, Sarawak, Malaysia'),
            h('div', { style: { display: 'flex', gap: 16, flexWrap: 'wrap' } },
              ['Privacy & PDPA Policy', 'Terms & Conditions', 'SST disclosure (MY)', 'GST disclosure (SG)'].map(function (t, i) {
                return h('a', { key: i, href: '#', onClick: function (e) { e.preventDefault(); }, style: { fontSize: 12, color: MUT, textDecoration: 'none' } }, t);
              }))),
          h('div', { style: { display: 'flex', gap: 7, flexWrap: 'wrap', justifyContent: 'flex-end' } },
            v.payments.map(function (p, i) {
              return h('span', { key: i, style: { font: '600 10.5px Montserrat,sans-serif', border: '1px solid ' + HAIR, background: '#fff', borderRadius: 3, padding: '5px 9px', color: MUT, whiteSpace: 'nowrap' } }, p);
            })))));
  }

  function chat() {
    return h('a', { href: '#', onClick: function (e) { e.preventDefault(); }, style: { position: 'fixed', right: 0, bottom: 0, zIndex: 70, display: 'flex', alignItems: 'center', gap: 8, background: '#fff', color: TEAL, border: '1px solid ' + HAIR, borderBottom: 'none', borderRadius: '6px 6px 0 0', padding: '8px 20px', boxShadow: '0 -2px 14px rgba(33,33,33,.10)', fontSize: 14, fontWeight: 600, textDecoration: 'none' } },
      img('assets/icons/phone.svg', { height: 15, width: 'auto', display: 'block' }), 'Chat');
  }

  window.DCLogic = class extends React.Component {
    render() {
      var v = this.renderVals();
      return h('div', { onClick: v.onNav, style: { minHeight: '100vh', background: '#fff' } },
        h('a', { href: '#pk-main', className: 'pk-skip' }, 'Skip to content'),
        header(v),
        h('main', { id: 'pk-main', tabIndex: -1, style: { outline: 'none' } }, v.screen),
        v.staff ? null : footer(v),
        v.staff ? null : chat());
    }
  };
})();
