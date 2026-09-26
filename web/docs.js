/*
 * Formal order documents — Printoka Invoice and Order Slip, rebuilt from the original WordPress
 * theme (TCPDF over assets/images/{invoice,order}/…-template.svg, A4, positions in mm) — plus the
 * admin "Download order" bundle and the order view (addresses/payment/price first, artworks and
 * payment proof as real files).
 *
 * PDFs are drawn in the browser with jsPDF: the original SVG letterhead is the page (vector via
 * svg2pdf, raster fallback), the text is laid over it at the original template coordinates.
 */
(function () {
  const C = window.PKComponent; if (!C) return;
  const P = C.prototype;
  const LIBS = [
    ['jspdf', 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js'],
    ['svg2pdf', 'https://cdn.jsdelivr.net/npm/svg2pdf.js@2.2.3/dist/svg2pdf.umd.min.js'],
    ['JSZip', 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js'],
  ];
  let libsP = null;
  const loadScript = src => new Promise((res, rej) => { const s = document.createElement('script'); s.src = src; s.async = true; s.onload = res; s.onerror = () => rej(new Error('Could not load ' + src)); document.head.appendChild(s); });
  const loadLibs = () => libsP || (libsP = LIBS.reduce((p, l) => p.then(() => window[l[0]] ? null : loadScript(l[1])), Promise.resolve()));

  // ---------------------------------------------------------------- template backgrounds
  const TPL = { invoice: 'assets/docs/invoice-template.svg', slip: 'assets/docs/order-slip-template.svg',
    // original printoka-3rd-party-supplier templates (A4 portrait · A5 landscape · A6 landscape)
    'purchase-order': 'assets/docs/purchase-order-template.svg', 'shipping-label': 'assets/docs/shipping-label-template.svg', 'hub-label': 'assets/docs/hub-label-template.svg' };
  const PAGE = { invoice: [210, 297], slip: [210, 297], 'purchase-order': [210, 297], 'shipping-label': [210, 148], 'hub-label': [148, 105] };
  const tplCache = {};
  function templateSvg(kind) {
    if (tplCache[kind]) return tplCache[kind];
    return (tplCache[kind] = fetch('/' + TPL[kind]).then(r => r.text()).then(txt => {
      const svg = new DOMParser().parseFromString(txt, 'image/svg+xml').documentElement;
      return { svg, txt };
    }));
  }
  function rasterize(txt, W, H) { // fallback: 300 dpi JPEG of the letterhead
    return new Promise((res, rej) => {
      const img = new Image(); const url = URL.createObjectURL(new Blob([txt], { type: 'image/svg+xml' }));
      img.onload = () => { const c = document.createElement('canvas'); c.width = Math.round(W / 25.4 * 300); c.height = Math.round(H / 25.4 * 300); const x = c.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, c.width, c.height); x.drawImage(img, 0, 0, c.width, c.height); URL.revokeObjectURL(url); res(c.toDataURL('image/jpeg', 0.92)); };
      img.onerror = rej; img.src = url;
    });
  }
  async function drawTemplate(doc, kind) {
    const t = await templateSvg(kind); const W = PAGE[kind][0], H = PAGE[kind][1];
    if (!t.jpeg && typeof doc.svg === 'function' && !t.svgFailed) {
      try { await doc.svg(t.svg.cloneNode(true), { x: 0, y: 0, width: W, height: H }); return; } catch (e) { t.svgFailed = true; }
    }
    if (!t.jpeg) t.jpeg = await rasterize(t.txt, W, H);
    doc.addImage(t.jpeg, 'JPEG', 0, 0, W, H, kind + '-tpl', 'FAST');
  }

  // ---------------------------------------------------------------- helpers
  const RM = n => 'RM' + Number(n || 0).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  const dmy = ts => { const d = ts ? new Date(ts) : new Date(); return String(d.getDate()).padStart(2, '0') + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + d.getFullYear(); };
  const PT = 0.3528; // mm per point
  // Printoka brand font (Montserrat, same as the templates and the site) embedded in every PDF;
  // falls back to Helvetica only if the font files can't be loaded
  const FONT_FILES = [['Montserrat_400Regular.ttf', 'normal'], ['Montserrat_600SemiBold.ttf', 'bold']];
  let fontsP = null;
  const toB64 = buf => { const u = new Uint8Array(buf); let s = ''; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000)); return btoa(s); };
  const loadFonts = () => fontsP || (fontsP = Promise.all(FONT_FILES.map(f => fetch('/assets/fonts/' + f[0]).then(r => { if (!r.ok) throw new Error('font'); return r.arrayBuffer(); }).then(b => [f[0], f[1], toB64(b)])))
    .catch(() => { fontsP = null; return null; }));
  const applyFonts = (doc, fonts) => { if (!fonts) return 'helvetica'; fonts.forEach(f => { doc.addFileToVFS(f[0], f[2]); doc.addFont(f[0], 'Montserrat', f[1]); }); return 'Montserrat'; };
  const addrLines = a => { if (!a) return []; if (typeof a === 'string') return a.split(/\n|,\s*(?=\d{5})/).map(s => s.trim()).filter(Boolean);
    return [a.name, a.company, a.phone, a.line1, a.line2, [a.postcode, a.city].filter(Boolean).join(', '), a.state, ({ MY: 'Malaysia', SG: 'Singapore', BN: 'Brunei' })[a.country] || a.country].filter(Boolean); };
  const orderNo = o => String(o.id || '').replace(/^PO-/, '');
  const specLines = it => {
    if (Array.isArray(it.specLines) && it.specLines.length) return it.specLines.map(l => Array.isArray(l) ? l[0] + ': ' + l[1] : String(l));
    return String(it.spec || '').split(/\s·\s|\n/).map(s => s.trim()).filter(Boolean);
  };

  // ---------------------------------------------------------------- one Printoka document (invoice | slip)
  P.buildOrderPdf = async function (o, kind) {
    await loadLibs();
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ unit: 'mm', format: 'a4', compress: true });
    const FONT = applyFonts(doc, await loadFonts());
    const no = orderNo(o);
    const cust = o.customer || {};
    const pickup = o.fulfillment && o.fulfillment.method === 'pickup';
    const docNo = kind === 'invoice' ? 'INV-' + no : '#' + no;
    doc.setProperties({ title: (kind === 'invoice' ? 'Invoice ' : 'Order Slip ') + docNo, subject: 'Printoka order ' + o.id, author: 'Yushan Corporation Sdn Bhd (Printoka)', creator: 'Printoka' });
    const tierPct = o.memberDiscount && o.subtotal ? Math.round(o.memberDiscount / o.subtotal * 100) : 0;
    const pcr = [o.tier && tierPct ? o.tier + ' member (' + tierPct + '%)' : (o.tier && o.tier !== 'Standard' ? o.tier + ' member' : ''), o.coupon ? 'Code ' + o.coupon : ''].filter(Boolean).join(' · ') || '—';
    const billing = addrLines(o.billing || cust);
    const shipping = pickup ? ['Self-pickup at ' + ((o.fulfillment && o.fulfillment.outletName) || (o.fulfillment && o.fulfillment.outlet) || 'outlet'), cust.name, cust.phone].filter(Boolean) : addrLines(o.shipTo || o.billing || cust);

    // ---- item rows (original: name in bold, spec lines, shipping method + artwork names on the slip)
    const rows = (o.items || []).map((it, i) => {
      const lines = specLines(it);
      if (kind === 'slip') {
        if (!lines.some(l => /^shipping method/i.test(l))) lines.push('Shipping Method: ' + (pickup ? 'Self-pickup' : (o.fulfillment && o.fulfillment.method === 'direct' ? 'Direct to customer' : 'Courier delivery')));
        (it.artworks || []).filter(a => !/^pending-upload/.test(a)).forEach(a => lines.push('Artwork: ' + a));
      } else {
        const jid = (o.jobIds || [])[i]; if (jid) lines.push('Job ID: ' + jid);
      }
      return { name: it.product, lines, qty: it.qty || 1, unit: it.qty ? it.lineTotal / it.qty : it.lineTotal, total: it.lineTotal };
    });
    if (o.tax) rows.push({ name: 'Sales & Service Tax (SST ' + Math.round(o.tax / Math.max(0.01, (o.subtotal - (o.memberDiscount || 0) - (o.couponDiscount || 0))) * 100) + '%)', lines: [], qty: 1, unit: o.tax, total: o.tax, uom: '' });
    if (o.creditApplied) rows.push({ name: 'Printoka wallet credit applied', lines: [], qty: 1, unit: -o.creditApplied, total: -o.creditApplied, uom: '' });

    const FS = 7, LH = FS * PT * 1.4; // font size + line height like the original (7pt, ratio 1.4)
    const TOP = 107, BOTTOM = 252;
    doc.setFont(FONT, 'normal'); doc.setFontSize(FS);
    // pre-wrap descriptions to the 102 mm column (minus padding)
    rows.forEach(r => {
      doc.setFont(FONT, 'bold'); r.nameLines = doc.splitTextToSize(String(r.name || ''), 96);
      doc.setFont(FONT, 'normal'); r.wrapped = r.lines.reduce((a, l) => a.concat(doc.splitTextToSize(String(l), 96)), []);
      r.height = (r.nameLines.length + r.wrapped.length) * LH + 4;
    });
    // paginate
    const pages = [[]]; let y = TOP;
    rows.forEach(r => { if (y + r.height > BOTTOM && pages[pages.length - 1].length) { pages.push([]); y = TOP; } pages[pages.length - 1].push(Object.assign(r, { y })); y += r.height; });

    let idx = 1;
    for (let p = 0; p < pages.length; p++) {
      if (p) doc.addPage();
      await drawTemplate(doc, kind);
      // header (original coordinates: TCPDF writeHTMLCell top-left → baseline ≈ top + 0.8·size)
      doc.setFont(FONT, 'normal'); doc.setFontSize(6); doc.setTextColor(223, 8, 8);
      doc.textWithLink('print@printoka.com', 61.9, 37.2, { url: 'mailto:print@printoka.com' });
      doc.setTextColor(33, 33, 33); doc.setFontSize(8);
      doc.setFont(FONT, 'bold'); doc.text(docNo, kind === 'invoice' ? 164.8 : 162.2, 30.3);
      doc.setFont(FONT, 'normal'); doc.setFontSize(7.5); doc.text('Date: ' + dmy(o.createdAt), 196.5, 37.4, { align: 'right' });
      // customer box
      doc.setFontSize(FS);
      doc.text((o.userId || 'Guest') + (cust.name ? '  ·  ' + cust.name : ''), 34.2, 51.0);
      doc.text(pcr, 57.6, 55.4);
      if (o.payment && o.payment.status === 'validated' && kind === 'invoice') { doc.setFont(FONT, 'bold'); doc.setTextColor(61, 139, 64); doc.text('PAID', 196.5, 51.0, { align: 'right' }); doc.setTextColor(33, 33, 33); doc.setFont(FONT, 'normal'); }
      billing.slice(0, 7).forEach((l, i) => doc.text(doc.splitTextToSize(l, 80)[0], 16.6, 66.9 + i * LH));
      shipping.slice(0, 7).forEach((l, i) => doc.text(doc.splitTextToSize(l, 80)[0], 101.8, 66.9 + i * LH));
      // item rows
      pages[p].forEach(r => {
        let ty = r.y + 3.4;
        doc.setFont(FONT, 'normal'); doc.text(String(idx++), 14, ty);
        doc.setFont(FONT, 'bold'); r.nameLines.forEach((l, i) => doc.text(l, 24, ty + i * LH));
        doc.setFont(FONT, 'normal'); r.wrapped.forEach((l, i) => doc.text(l, 24, ty + (r.nameLines.length + i) * LH));
        doc.text(Number(r.qty).toLocaleString('en-US'), 126, ty);
        doc.text(r.uom != null ? r.uom : 'pcs', 138, ty);
        doc.text(RM(r.unit), 171, ty, { align: 'right' });
        doc.text(RM(r.total), 196, ty, { align: 'right' });
      });
      // totals (last page) — shipping · coupon discount · member discount · total
      doc.setFontSize(FS);
      if (p === pages.length - 1) {
        const Y = [257.5, 262.2, 266.7, 271.5].map(v => v + 3.9);
        doc.text(RM(o.shipping || 0), 194.5, Y[0], { align: 'right' });
        doc.text(o.couponDiscount ? '-' + RM(o.couponDiscount) : '-', 194.5, Y[1], { align: 'right' });
        doc.text(o.memberDiscount ? '-' + RM(o.memberDiscount) : '-', 194.5, Y[2], { align: 'right' });
        doc.setFont(FONT, 'bold'); doc.setFontSize(8); doc.text(RM(o.total), 194.5, Y[3], { align: 'right' }); doc.setFont(FONT, 'normal');
      } else { doc.setFontSize(6.5); doc.setTextColor(120, 120, 120); doc.text('Continued on next page', 194.5, 275.4, { align: 'right' }); doc.setTextColor(33, 33, 33); }
      doc.setFontSize(6.5); doc.setTextColor(120, 120, 120);
      doc.text('Page ' + (p + 1) + ' of ' + pages.length, 196, 289, { align: 'right' });
      doc.setTextColor(33, 33, 33);
    }
    return doc;
  };

  // ---------------------------------------------------------------- printing-job documents (original supplier plugin)
  // TCPDF writeHTMLCell(x, y) places the top of the first line at y; jsPDF draws on the baseline.
  const cellText = (doc, lines, x, y, size, ratio, width) => {
    const lh = size * PT * ratio; let n = 0;
    lines.filter(l => l != null && l !== '').forEach(l => (width ? doc.splitTextToSize(String(l), width) : [String(l)]).forEach(s => { doc.text(s, x, y + size * PT + n * lh); n++; }));
    return n;
  };
  const jobLines = j => [j.product ? j.product : null].concat(String(j.spec || '').split(/\s·\s|\n/).map(s => s.trim()).filter(Boolean), [j.qty ? 'Quantity: ' + Number(j.qty).toLocaleString('en-US') : null, j.instructions ? 'Instructions: ' + j.instructions : null]);
  P.buildJobDoc = async function (d) {
    await loadLibs();
    const { jsPDF } = window.jspdf; const kind = d.kind, S = PAGE[kind];
    const doc = new jsPDF({ unit: 'mm', format: [S[0], S[1]], orientation: S[0] > S[1] ? 'landscape' : 'portrait', compress: true });
    const FONT = applyFonts(doc, await loadFonts());
    await drawTemplate(doc, kind);
    doc.setTextColor(33, 33, 33); doc.setFont(FONT, 'normal');
    const J = d.job || {};
    if (kind === 'purchase-order') {
      doc.setFontSize(6); doc.setTextColor(223, 8, 8); doc.textWithLink('print@printoka.com', 60.866, 35.4 + 6 * PT, { url: 'mailto:print@printoka.com' }); doc.setTextColor(33, 33, 33);
      doc.setFontSize(7);
      cellText(doc, [String(d.poNumber || '')], 145, 27.5, 7, 1.4);
      cellText(doc, [d.vendor && d.vendor.name].concat(String((d.vendor && d.vendor.address) || '').split(/\n|,\s*(?=\d{5})/)), 15, 53, 7, 1.4, 60);
      const sh = d.shipping || {}; cellText(doc, [sh.name].concat(String(sh.address || '').split(/\n/), [sh.phone]), 100, 53, 7, 1.4, 60);
      doc.setFont(FONT, 'bold'); cellText(doc, [J.product], 25, 110, 7, 1.4, 90); doc.setFont(FONT, 'normal');
      cellText(doc, jobLines(J).slice(1), 25, 110 + 7 * PT * 1.4, 7, 1.4, 90);
      const amt = d.amount != null ? Number(d.amount).toFixed(2) : '';
      cellText(doc, ['1'], 126, 110, 7, 1.4); cellText(doc, [amt], 148, 110, 7, 1.4); cellText(doc, [amt], 173, 110, 7, 1.4); cellText(doc, [amt], 173, 272.5, 7, 1.4);
    } else if (kind === 'shipping-label') {
      const o = d.order || {};
      doc.setFontSize(9);
      cellText(doc, ['Printoka'], 25, 30, 9, 1.4);
      cellText(doc, ['Lot 1565, Piasau Industrial Estate,', '98000 Miri, Sarawak,', 'Malaysia'], 25, 40, 9, 1.4);
      cellText(doc, ['014-969 0799'], 25, 70, 9, 1.4);
      cellText(doc, [o.name], 25, 90, 9, 1.4, 105);
      cellText(doc, String(o.address || '').split(/,\s*/).reduce((a, p) => { const last = a[a.length - 1]; if (last && (last + ', ' + p).length < 42) a[a.length - 1] = last + ', ' + p; else a.push(p); return a; }, []), 25, 100, 9, 1.4, 105);
      cellText(doc, [o.phone], 25, 130, 9, 1.4);
      doc.setFont(FONT, 'bold'); doc.setFontSize(16); cellText(doc, [o.postcode], 85, 130, 16, 1.4);
      doc.setFontSize(12); cellText(doc, [o.orderNumber], 165, 11, 12, 1.4);
      doc.setFont(FONT, 'normal'); doc.setFontSize(8); cellText(doc, jobLines(J), 140, 30, 8, 1.75, 60);
    } else if (kind === 'hub-label') {
      const hb = d.hub || {};
      doc.setFontSize(7.5);
      cellText(doc, [hb.name], 25, 30.5, 7.5, 1.5, 70);
      cellText(doc, String(hb.address || '').split(/\n|,\s*(?=\d{5})/), 25, 40.5, 7.5, 1.5, 70);
      cellText(doc, [hb.phone], 25, 90.5, 7.5, 1.5);
      doc.setFont(FONT, 'bold'); doc.setFontSize(10); cellText(doc, [String(d.poNumber || '')], 112, 10, 10, 1.4);
      doc.setFont(FONT, 'normal'); doc.setFontSize(7); cellText(doc, jobLines(J), 100, 30, 7, 1.4, 40);
    }
    doc.setProperties({ title: ({ 'purchase-order': 'Purchase Order ', 'shipping-label': 'Shipping Label ', 'hub-label': 'Hub Label ' })[kind] + (d.poNumber || d.jobId), author: 'Printoka', creator: 'Printoka' });
    return doc;
  };
  P.openJobDoc = function (jobId, kind) {
    const title = ({ 'purchase-order': 'Purchase Order', 'shipping-label': 'Shipping Label', 'hub-label': 'Delivery Label' })[kind] || 'Document';
    const v = pdfViewer(title);
    fetch('/api/jobs/' + encodeURIComponent(jobId) + '/doc/' + kind, { headers: this.authHeaders() }).then(r => r.json())
      .then(d => { if (d.error) throw new Error(d.error); return this.buildJobDoc(d).then(doc => [doc, d]); })
      .then(([doc, d]) => v.show(doc.output('blob'), title + ' ' + (d.poNumber || jobId) + '.pdf'))
      .catch(e => v.fail(e.message));
  };
  // ---------------------------------------------------------------- on-page PDF viewer (every page drawn with pdf.js + a download button)
  const PDFJS = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
  let pdfjsP = null;
  const loadPdfjs = () => pdfjsP || (pdfjsP = (window.pdfjsLib ? Promise.resolve() : loadScript(PDFJS)).then(() => { window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS.replace('pdf.min.js', 'pdf.worker.min.js'); return window.pdfjsLib; }));

  // ---------------------------------------------------------------- artwork watermark for printers' quotes
  // the prepress-approved artwork goes to printers as a PDF with "PRINTOKA" across every page (PDF pages or an image);
  // the original file is only released to the printer that is awarded the job
  const stamp = cv => {
    const x = cv.getContext('2d'), size = Math.max(28, Math.round(cv.width / 8));
    x.save(); x.globalAlpha = 0.22; x.fillStyle = '#E52220'; x.font = '700 ' + size + 'px Montserrat, Arial, sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
    x.translate(cv.width / 2, cv.height / 2); x.rotate(-Math.PI / 6);
    const stepX = size * 6, stepY = size * 2.6, span = Math.hypot(cv.width, cv.height);
    for (let yy = -span; yy <= span; yy += stepY) for (let xx = -span; xx <= span; xx += stepX) x.fillText('PRINTOKA', xx + ((yy / stepY) % 2 ? stepX / 2 : 0), yy);
    x.restore();
  };
  P.watermarkArtwork = function (blob, name) {
    const base = String(name || 'artwork').replace(/\.[^.]+$/, '');
    const isPdf = /pdf/i.test(blob.type) || /\.pdf$/i.test(name || ''), isImg = /^image\/(png|jpe?g|webp)/i.test(blob.type) || /\.(png|jpe?g|webp)$/i.test(name || '');
    if (!isPdf && !isImg) return Promise.resolve(null); // AI / PSD / ZIP … cannot be previewed — the printer sees the file name only
    const pages = [];
    const toPage = cv => { stamp(cv); pages.push({ img: cv.toDataURL('image/jpeg', 0.85), w: cv.width * 0.75, h: cv.height * 0.75 }); };
    const build = () => loadLibs().then(() => {
      const { jsPDF } = window.jspdf; let doc = null;
      pages.forEach((p, i) => { const o = p.w > p.h ? 'l' : 'p'; if (!i) doc = new jsPDF({ unit: 'pt', format: [p.w, p.h], orientation: o }); else doc.addPage([p.w, p.h], o); doc.addImage(p.img, 'JPEG', 0, 0, p.w, p.h); });
      return doc ? { name: base + '-PRINTOKA.pdf', data: doc.output('datauristring') } : null;
    });
    if (isImg) return new Promise((res, rej) => { const img = new Image(), url = URL.createObjectURL(blob);
      img.onload = () => { const k = Math.min(1, 2400 / Math.max(img.naturalWidth, img.naturalHeight)); const cv = document.createElement('canvas'); cv.width = Math.round(img.naturalWidth * k); cv.height = Math.round(img.naturalHeight * k);
        const x = cv.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, cv.width, cv.height); x.drawImage(img, 0, 0, cv.width, cv.height); URL.revokeObjectURL(url); toPage(cv); res(); };
      img.onerror = () => { URL.revokeObjectURL(url); rej(new Error('Could not read the artwork image.')); }; img.src = url; }).then(build);
    return blob.arrayBuffer().then(buf => loadPdfjs().then(lib => lib.getDocument({ data: buf }).promise)).then(pdf => {
      const n = Math.min(pdf.numPages, 20); let chain = Promise.resolve();
      for (let i = 1; i <= n; i++) chain = chain.then(() => pdf.getPage(i)).then(pg => { const vp1 = pg.getViewport({ scale: 1 }), k = Math.min(3, 1400 / vp1.width), vp = pg.getViewport({ scale: k });
        const cv = document.createElement('canvas'); cv.width = Math.round(vp.width); cv.height = Math.round(vp.height);
        return pg.render({ canvasContext: cv.getContext('2d'), viewport: vp }).promise.then(() => { stamp(cv); pages.push({ img: cv.toDataURL('image/jpeg', 0.85), w: vp1.width, h: vp1.height }); }); });
      return chain;
    }).then(build);
  };
  function pdfViewer(title) {
    const ov = document.createElement('div');
    ov.setAttribute('role', 'dialog'); ov.setAttribute('aria-label', title);
    ov.style.cssText = 'position:fixed;inset:0;z-index:200;background:rgba(15,20,25,.6);display:flex;flex-direction:column;font:14px Montserrat,sans-serif';
    ov.innerHTML = '<div style="display:flex;align-items:center;gap:10px;padding:12px 18px;background:#fff;border-bottom:1px solid #eaeaea"><b style="font-size:16px" data-t></b><span style="flex:1"></span>' +
      '<button data-dl disabled style="font:600 13.5px Montserrat,sans-serif;padding:9px 16px;border-radius:8px;border:1px solid #E52220;background:#E52220;color:#fff;cursor:pointer">Download PDF</button>' +
      '<button data-x style="font:600 13.5px Montserrat,sans-serif;padding:9px 16px;border-radius:8px;border:1px solid #d9d9d9;background:#fff;cursor:pointer">Close</button></div>' +
      '<div data-body style="flex:1;overflow:auto;padding:20px;display:flex;flex-direction:column;align-items:center;gap:16px"><p style="color:#fff">Preparing the PDF…</p></div>';
    ov.querySelector('[data-t]').textContent = title;
    const close = () => ov.remove();
    ov.querySelector('[data-x]').onclick = close;
    ov.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
    document.body.appendChild(ov);
    const body = ov.querySelector('[data-body]');
    return {
      show: async (blob, name) => {
        const dl = ov.querySelector('[data-dl]'); dl.disabled = false;
        dl.onclick = () => { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 4000); };
        try {
          const lib = await loadPdfjs(); const pdf = await lib.getDocument({ data: await blob.arrayBuffer() }).promise;
          body.innerHTML = '';
          const width = Math.min(900, body.clientWidth - 40);
          for (let i = 1; i <= pdf.numPages; i++) {
            const page = await pdf.getPage(i); const base = page.getViewport({ scale: 1 });
            const scale = width / base.width, ratio = window.devicePixelRatio || 1;
            const vp = page.getViewport({ scale: scale * ratio });
            const c = document.createElement('canvas'); c.width = vp.width; c.height = vp.height;
            c.style.cssText = 'width:' + (vp.width / ratio) + 'px;height:' + (vp.height / ratio) + 'px;background:#fff;box-shadow:0 8px 30px rgba(0,0,0,.35);max-width:100%';
            body.appendChild(c); await page.render({ canvasContext: c.getContext('2d'), viewport: vp }).promise;
          }
        } catch (e) { body.innerHTML = '<p style="color:#fff">Could not display the PDF here — use Download PDF.</p>'; }
      },
      fail: msg => { body.innerHTML = ''; const p = document.createElement('p'); p.style.color = '#fff'; p.textContent = 'Could not open the document: ' + msg; body.appendChild(p); },
    };
  }
  P.showPdf = function (blob, title, name) { pdfViewer(title).show(blob, name || title + '.pdf'); };

  // ---------------------------------------------------------------- open / download
  P.fetchOrderFull = function (oid) { return fetch('/api/orders/' + encodeURIComponent(oid), { headers: this.authHeaders() }).then(r => r.json()).then(d => d.order || null); };
  P.saveBlob = function (blob, name) { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 4000); };
  const origOpenDoc = P.openDoc;
  P.openDoc = function (id, kind) {
    if (!(kind === 'invoice' || kind === 'slip') || !/^PO-/.test(String(id))) return origOpenDoc.call(this, id, kind);
    const title = (kind === 'invoice' ? 'Invoice INV-' : 'Order Slip ') + String(id).replace(/^PO-/, '');
    const v = pdfViewer(title);
    this.fetchOrderFull(id).then(o => { if (!o) throw new Error('Order not found'); return this.buildOrderPdf(o, kind); })
      .then(doc => v.show(doc.output('blob'), title + '.pdf'))
      .catch(e => v.fail(e.message));
  };
  // the full order bundle: invoice + order slip + every artwork + payment proof, zipped
  P.downloadOrder = async function (oid) {
    this.setState({ dlBusy: oid, dlMsg: null });
    try {
      const o = await this.fetchOrderFull(oid); if (!o) throw new Error('Order not found');
      await loadLibs();
      const no = orderNo(o), zip = new window.JSZip(), root = zip.folder('Order ' + no);
      root.file('Invoice INV-' + no + '.pdf', (await this.buildOrderPdf(o, 'invoice')).output('arraybuffer'));
      root.file('Order Slip ' + no + '.pdf', (await this.buildOrderPdf(o, 'slip')).output('arraybuffer'));
      const files = o.files || [], missing = [];
      for (const f of files) {
        const r = await fetch('/api/orders/' + encodeURIComponent(o.id) + '/files/' + f.id, { headers: this.authHeaders() });
        if (!r.ok) { missing.push(f.name + ' (could not be read)'); continue; }
        const blob = await r.blob();
        if (f.kind === 'proof') root.file('Payment Proof/' + f.name, blob);
        else { const it = (o.items || [])[f.line - 1] || {}; root.file('Artworks/Line ' + f.line + ' - ' + String(it.product || 'item').replace(/[\\/:*?"<>|]+/g, '-') + '/' + f.name, blob); }
      }
      (o.items || []).forEach((it, i) => (it.artworks || []).forEach(a => { if (!files.some(f => f.kind === 'artwork' && f.line === i + 1 && f.name === a) && !/^pending-upload/.test(a)) missing.push('Line ' + (i + 1) + ': ' + a + ' — listed on the order but the file was not uploaded to the system'); }));
      const pay = o.payment || {};
      if (!files.some(f => f.kind === 'proof')) {
        root.file('Payment Proof/Payment record.txt', ['PRINTOKA — PAYMENT RECORD', '', 'Order: ' + o.id, 'Customer: ' + ((o.customer && o.customer.name) || ''), 'Method: ' + (pay.gateway || pay.method || ''), 'Status: ' + (pay.status === 'validated' ? 'Paid / validated' : 'Pending'), 'Reference: ' + (pay.reference || '—'), 'Paid at: ' + (pay.paidAt ? pay.paidAt.replace('T', ' ').slice(0, 16) : '—'), 'Amount: ' + RM(o.total), pay.proof ? 'Proof on file (name only, not uploaded): ' + pay.proof : ''].join('\r\n'));
      }
      if (missing.length) root.file('Artworks/MISSING FILES.txt', ['These artworks are named on the order but no file is stored for them:', ''].concat(missing).join('\r\n'));
      const blob = await zip.generateAsync({ type: 'blob', compression: 'DEFLATE' });
      this.saveBlob(blob, 'Printoka Order ' + no + '.zip');
      this.setState({ dlBusy: null, dlMsg: { ok: true, text: 'Downloaded Printoka Order ' + no + '.zip — invoice, order slip, ' + files.filter(f => f.kind === 'artwork').length + ' artwork file(s)' + (files.some(f => f.kind === 'proof') ? ' and the payment proof.' : ' and the payment record.') } });
    } catch (e) { this.setState({ dlBusy: null, dlMsg: { ok: false, text: 'Could not build the download: ' + e.message } }); }
  };
  P.uploadOrderFile = function (oid, kind, line, file) {
    if (!file) return;
    this.setState({ upBusy: kind + line, dlMsg: null });
    const rd = new FileReader();
    rd.onload = () => fetch('/api/orders/' + encodeURIComponent(oid) + '/files', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify({ kind, line, name: file.name, data: rd.result }) })
      .then(r => r.json()).then(d => { if (d.error) return this.setState({ upBusy: null, dlMsg: { ok: false, text: d.error } }); this.setState({ upBusy: null, ordView: d.order, dlMsg: { ok: true, text: file.name + ' uploaded.' } }); })
      .catch(() => this.setState({ upBusy: null, dlMsg: { ok: false, text: 'Upload failed — check your connection.' } }));
    rd.readAsDataURL(file);
  };
  P.openOrderFile = function (oid, f) {
    fetch('/api/orders/' + encodeURIComponent(oid) + '/files/' + f.id, { headers: this.authHeaders() }).then(r => { if (!r.ok) throw new Error('not allowed'); return r.blob(); })
      .then(b => this.saveBlob(b, f.name)).catch(() => this.setState({ dlMsg: { ok: false, text: 'Could not open ' + f.name } }));
  };

  // ---------------------------------------------------------------- the order view (addresses, payment & price first)
  P.orderDialog = function () {
    if (!this.state.ordViewId) return null;
    const o = this.state.ordView;
    const close = () => this.setState({ ordViewId: null, ordView: null, dlMsg: null });
    const paid = o && o.payment && o.payment.status === 'validated';
    const staff = this.userType() !== 'customer' && this.userType() !== 'guest';
    const sect = (t, node, extra) => h('div', { key: t, style: Object.assign({ marginBottom: 16 }, extra || {}) }, h('div', { style: { fontSize: 11, fontWeight: 700, letterSpacing: '.07em', textTransform: 'uppercase', color: FAINT, marginBottom: 8 } }, t), node);
    const hist = (o && o.customerHistory) || { totalOrders: 0, totalRevenue: 0, avgOrderValue: 0 };
    const btn = (label, on, primary, busy) => h('span', { onClick: busy ? undefined : on, style: { fontSize: 12.5, fontWeight: 600, color: primary ? '#fff' : TEAL, background: primary ? TEAL : '#fff', border: '1px solid ' + (primary ? TEAL : HAIR), borderRadius: 7, padding: '7px 12px', cursor: busy ? 'wait' : 'pointer', whiteSpace: 'nowrap' } }, busy ? 'Preparing…' : label);
    const files = (o && o.files) || [];
    const fileChip = f => h('span', { key: f.id, onClick: () => this.openOrderFile(o.id, f), title: 'Download ' + f.name, style: { display: 'inline-flex', alignItems: 'center', gap: 5, background: CHIP, color: TEAL, fontSize: 11.5, fontWeight: 600, borderRadius: 6, padding: '4px 8px', cursor: 'pointer' } }, '⬇ ' + f.name + ' · ' + Math.max(1, Math.round(f.size / 1024)) + ' KB');
    const upload = (kind, line, label) => h('label', { style: { display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 11.5, fontWeight: 600, color: MUT, border: '1px dashed ' + HAIR, borderRadius: 6, padding: '4px 9px', cursor: 'pointer' } },
      this.state.upBusy === kind + line ? 'Uploading…' : label, h('input', { type: 'file', accept: kind === 'proof' ? 'image/*,application/pdf' : '.pdf,.ai,.eps,.psd,.tif,.tiff,.jpg,.jpeg,.png,.svg,.cdr,.indd,.zip', style: { display: 'none' }, onChange: e => { this.uploadOrderFile(o.id, kind, line, e.target.files[0]); e.target.value = ''; } }));
    const priceRows = o ? [['Subtotal', this.rm(o.subtotal)], o.memberDiscount ? ['Member discount', '− ' + this.rm(o.memberDiscount)] : null, o.couponDiscount ? ['Discount code ' + (o.coupon || ''), '− ' + this.rm(o.couponDiscount)] : null, o.creditApplied ? ['Credit applied', '− ' + this.rm(o.creditApplied)] : null, [this.taxLabel ? 'SST' : 'Tax', this.rm(o.tax)], ['Delivery', this.rm(o.shipping)]].filter(Boolean) : [];
    return h('div', { key: 'ord', onClick: close, style: { position: 'fixed', inset: 0, zIndex: 92, background: 'rgba(15,20,25,.5)', display: 'grid', placeItems: 'start center', padding: 16, overflow: 'auto' } },
      h('div', { onClick: e => e.stopPropagation(), role: 'dialog', 'aria-label': 'Order ' + this.state.ordViewId, style: { background: '#fff', borderRadius: 14, maxWidth: 960, width: '100%', margin: '10px 0', boxShadow: '0 24px 60px rgba(33,33,33,.3)' } },
        h('div', { style: { padding: '14px 22px', borderBottom: '1px solid ' + HAIR, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', position: 'sticky', top: 0, background: '#fff', borderRadius: '14px 14px 0 0', zIndex: 1 } },
          h('span', { style: { font: '600 13px ui-monospace,Menlo,monospace', color: TEAL } }, this.state.ordViewId),
          o ? this.chip(paid ? 'Paid' : 'Payment pending', paid ? 'ok' : 'warn') : null,
          o && o.progressLabel ? this.chip(o.progressLabel, 'neutral') : null,
          o ? h('span', { style: { fontSize: 12.5, color: MUT } }, (o.channel || 'online') + ' · ' + (o.createdAt || '').slice(0, 10)) : null,
          h('span', { style: { marginLeft: 'auto', display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' } },
            o ? btn('Invoice PDF', () => this.openDoc(o.id, 'invoice')) : null,
            o ? btn('Order slip PDF', () => this.openDoc(o.id, 'slip')) : null,
            o && staff ? btn('⬇ Download order', () => this.downloadOrder(o.id), true, this.state.dlBusy === o.id) : null,
            (o && !paid && staff) ? btn('Validate payment', () => this.validateOrder(o.id), true) : null,
            h('span', { onClick: close, style: { color: FAINT, fontSize: 22, cursor: 'pointer', lineHeight: 1 } }, '×'))),
        this.state.dlMsg ? h('div', { style: { margin: '12px 22px 0', fontSize: 12.5, borderRadius: 8, padding: '9px 12px', background: this.state.dlMsg.ok ? '#e6f4ea' : '#fdecec', color: this.state.dlMsg.ok ? '#1f5e2a' : '#8c1c13' } }, this.state.dlMsg.text) : null,
        !o ? h('div', { style: { padding: 50, textAlign: 'center', color: FAINT } }, o === false ? 'Could not load the order.' : 'Loading…') :
        h('div', { style: { padding: 22 } },
          // 1 · billing · shipping · payment proof · price — first
          h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 18, borderBottom: '1px solid ' + LINE, paddingBottom: 6, marginBottom: 18 } },
            sect('Billing address', h('div', { style: { fontSize: 12.5 } }, this.docAddr(o.billing || o.customer))),
            sect('Shipping address', h('div', { style: { fontSize: 12.5 } }, o.fulfillment && o.fulfillment.method === 'pickup' ? h('div', null, h('b', null, 'Self-pickup'), h('div', null, o.fulfillment.outletName || o.fulfillment.outlet || 'Outlet')) : this.docAddr(o.shipTo || o.billing || o.customer))),
            sect('Payment proof', h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.7 } },
              h('div', null, h('b', { style: { color: INK } }, o.payment && (o.payment.gateway || o.payment.method))),
              h('div', null, 'Status: ', this.chip(paid ? 'Validated' : 'Pending', paid ? 'ok' : 'warn')),
              (o.payment && o.payment.reference) ? h('div', { style: { fontFamily: 'ui-monospace,Menlo,monospace', fontSize: 11.5, marginTop: 4 } }, 'Ref: ' + o.payment.reference) : null,
              (o.payment && o.payment.paidAt) ? h('div', null, 'Paid: ' + o.payment.paidAt.slice(0, 16).replace('T', ' ')) : null,
              h('div', { style: { display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 6 } }, files.filter(f => f.kind === 'proof').map(fileChip),
                !files.some(f => f.kind === 'proof') && o.payment && o.payment.proof ? h('span', { style: { fontSize: 11.5, color: FAINT } }, 'Named: ' + o.payment.proof + ' (file not uploaded)') : null,
                !paid ? upload('proof', 0, '＋ Upload payment proof') : null))),
            sect('Price', h('div', null,
              priceRows.map((r, i) => h('div', { key: i, style: { display: 'flex', justifyContent: 'space-between', fontSize: 12.5, color: MUT, padding: '3px 0' } }, h('span', null, r[0]), h('span', null, r[1]))),
              h('div', { style: { display: 'flex', justifyContent: 'space-between', fontSize: 15, fontWeight: 600, borderTop: '1px solid ' + HAIR, marginTop: 6, paddingTop: 8 } }, h('span', null, paid ? 'Total paid' : 'Total due'), h('span', null, this.rm(o.total))),
              (o.refundedTotal ? h('div', { style: { display: 'flex', justifyContent: 'space-between', fontSize: 12.5, color: '#c71917', marginTop: 4 } }, h('span', null, 'Refunded'), h('span', null, '− ' + this.rm(o.refundedTotal))) : null)))),
          // 2 · customer history
          sect('Customer · order history', h('div', { style: { display: 'flex', gap: 22, flexWrap: 'wrap', alignItems: 'center' } },
            h('div', { style: { fontSize: 14, fontWeight: 600 } }, (o.customer && o.customer.name) || '—', h('span', { style: { fontWeight: 400, color: MUT, marginLeft: 8, fontSize: 12.5 } }, [(o.customer && o.customer.email), (o.customer && o.customer.phone)].filter(Boolean).join(' · '))),
            h('span', { style: { flex: 1 } }),
            [['Total orders', String(hist.totalOrders)], ['Total revenue', this.rm(hist.totalRevenue)], ['Avg order value', this.rm(hist.avgOrderValue)]].map((k, i) =>
              h('div', { key: i, style: { textAlign: 'right' } }, h('div', { style: { fontSize: 10.5, color: FAINT, textTransform: 'uppercase', letterSpacing: '.05em' } }, k[0]), h('div', { style: { fontSize: 15, fontWeight: 600 } }, k[1]))))),
          // 3 · order lines + artworks (real files)
          sect('Order details & artworks', h('div', { style: { display: 'flex', flexDirection: 'column', gap: 10 } },
            (o.items || []).map((it, i) => { const af = files.filter(f => f.kind === 'artwork' && f.line === i + 1); const named = (it.artworks || []).filter(a => !/^pending-upload/.test(a) && !af.some(f => f.name === a));
              return h('div', { key: i, style: { border: '1px solid ' + HAIR, borderRadius: 10, padding: 13, display: 'flex', gap: 12 } },
                h('div', { style: { flex: '0 0 60px' } }, this.art(it.product)),
                h('div', { style: { flex: 1, minWidth: 0 } },
                  h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' } },
                    h('span', { style: { fontSize: 13.5, fontWeight: 600 } }, (i + 1) + '. ' + it.product),
                    h('span', { style: { fontSize: 13, fontWeight: 600 } }, this.rm(it.lineTotal))),
                  h('div', { style: { fontSize: 12, color: MUT, lineHeight: 1.6, marginTop: 4 } }, this.specView(it)),
                  h('div', { style: { fontSize: 12, color: FAINT, marginTop: 4 } }, 'Qty ' + (it.qty || 0).toLocaleString() + ' · unit ' + this.rm(it.unitPrice) + ((o.jobIds || [])[i] ? ' · job ' + o.jobIds[i] : '')),
                  h('div', { style: { display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8, alignItems: 'center' } },
                    af.map(fileChip),
                    named.map((a, k) => h('span', { key: 'n' + k, title: 'Named on the order — file not uploaded', style: { fontSize: 11.5, color: FAINT, border: '1px solid ' + LINE, borderRadius: 6, padding: '4px 8px' } }, '📎 ' + a)),
                    !af.length && !named.length ? h('span', { style: { fontSize: 11.5, color: '#a1660a' } }, 'No artwork yet') : null,
                    upload('artwork', i + 1, '＋ Upload artwork')))); }))))));
  };
})();
