const PAGE_FILES = {"home":"Printoka Home.dc.html","category":"Printoka Catalogue.dc.html","product":"Printoka Product.dc.html","artwork":"Printoka Artwork-Checker.dc.html","cart":"Printoka Cart.dc.html","checkout":"Printoka Checkout.dc.html","learn":"Printoka Learning-Hub.dc.html","membership":"Printoka Membership.dc.html","contact":"Printoka Custom-Quote.dc.html","search":"Printoka Search.dc.html","about":"Printoka About.dc.html","auth":"Printoka Auth.dc.html","confirm":"Printoka Order-Confirmation.dc.html","invoices":"Printoka Invoices.dc.html","dash":"Printoka Customer-Dashboard.dc.html","track":"Printoka Order-Tracking.dc.html","outlet":"Printoka Outlet-Dashboard.dc.html","prepress":"Printoka Prepress-Queue.dc.html","production":"Printoka Production-Queue.dc.html","logistics":"Printoka Logistics-Queue.dc.html","director":"Printoka Production-Director.dc.html","crm":"Printoka Inquiry-CRM.dc.html","admin":"Printoka Admin-Backoffice.dc.html","vendor":"Printoka Vendor-Hub-Portal.dc.html"};

const R = React;
const h = (t, p, ...c) => R.createElement(t, p, ...c);

const INK='#212121', MUT='#616161', FAINT='#616161', HAIR='#eaeaea', LINE='#eef1f4',
      TEAL='#E52220', TEALD='#c71917', AMBER='#FF9A2E', ALT='#FAFAFA', CHIP='#FAFAFA';

const SCREENS = [
  ['home','Home','A2','Homepage — hero, category grid, mini price simulator, trust bar, tier teaser, Learning Hub cards'],
  ['category','Category','A4','Category listing — filter panel, sort, product cards with "from RM", pagination, SEO block'],
  ['product','Product','A5','Product detail & configurator — option selectors, validity enforcement, quantity break table, live price panel'],
  ['artwork','Artwork','C1–C3','Artwork upload, automated validation checklist and the visual bleed/template overlay checker (Phase 3)'],
  ['cart','Cart','A12','Cart — jobs within one order, membership discount, coupon, credit balance toggle'],
  ['checkout','Checkout','A13','Checkout — customer info, fulfilment, artwork gate, payment, confirmation'],
  ['learn','Learning Hub','A7','Learning Hub — templated trilingual guides authored with {{product_name}} placeholders'],
  ['membership','Membership','A9 / B5','Membership ladder — five tiers on trailing-12-month spend, inactivity downgrade, referral'],
  ['contact','Custom Quote','A11 / A5.8','Contact + Request Custom Quote — routes into the Chat & Inquiry CRM as a ticket'],
  ['search','Search','A6','Search results — unified products, categories and Learning Hub tabs, filters, no-results state'],
  ['packaging','Packaging','A5+','Packaging & boxes — box-style library, 6-step DIY box builder, lanes & die-line archive'],
  ['about','About','A8','About Us — company story, vendor-network stats, timeline, Key Account Manager introduction'],
  ['corporate','Corporate','F','B2B corporate accounts — dedicated account manager, credit terms, bulk & recurring print'],
  ['partners','Partners','F','Partner & affiliate programme — join the vendor network or earn referral commission'],
  ['support','Support','F','Support hub — help topics, FAQ, artwork guides, contact channels, order tracking'],
  ['downloads','Downloads','F','Template downloads — print-ready AI/PSD/PDF templates per product size (migrated from printoka.com)'],
  ['terms','Terms','F','Terms of service, privacy (PDPA) and refund policy'],
  ['auth','Sign in','A15','Authentication — log in, register with OTP and PDPA consent, business-account application'],
  ['confirm','Confirmation','A14','Order confirmation — order number, summary, what-happens-next timeline, referral CTA, cross-sell'],
  ['dash','Customer','B1','Customer dashboard — quick stats, recent orders, tier mission, credit ledger'],
  ['track','Tracking','B2','Order detail — job breakdown, real status timeline, courier tracking, invoice vs order slip'],
  ['invoices','Invoices','B7','Invoices & order-slip archive — searchable, filterable, resend-to-email, bulk export for business accounts'],
  ['outlet','Outlet','D4','Outlet quote board — status bars, action-needed vs informational, per-quote action dropdown'],
  ['prepress','Prepress','E2','Prepress queue — SLA-sorted job cards, approve/reject popup with reason codes'],
  ['production','Scheduler','E3','Scheduler queue — job prioritization (deadline, then payment time), machine allocation, outsourcing to printer by best quote'],
  ['logistics','Logistics','E4','Logistics queue — courier suggestion from computed weight, AWB, shipment popup'],
  ['crm','Chat CRM','G1','Chat & Inquiry CRM — unified inbox, live customer sidebar, linked order, SLA timer'],
  ['admin','Admin','F1–F4','Admin backoffice — analytics, pricing & margin control, membership rules engine'],
  ['vendor','Vendor / Hub','E6','Outsource vendor & Hub portal — nine-status printing-job lifecycle, PO, hub tracking'],
];

const PAPERS = ['Gloss Art Card 250gsm','Gloss Art Card 310gsm','Gloss Art Card 360gsm','Matte Art Card 250gsm','Linen 240gsm','Metal Ice 250gsm','Synthetic Paper 180micron','Super White 250gsm','Suwen 240gsm'];
const PAPER_F = {'Gloss Art Card 250gsm':1,'Gloss Art Card 310gsm':1.12,'Gloss Art Card 360gsm':1.24,'Matte Art Card 250gsm':1.05,'Linen 240gsm':1.42,'Metal Ice 250gsm':1.58,'Synthetic Paper 180micron':1.9,'Super White 250gsm':1.08,'Suwen 240gsm':1.16};
const SIZES = ['54mm x 89mm','52mm x 86mm','50mm x 89mm','54mm x 86mm'];
const LAMS = [['Gloss Lamination (Both)',0],['Matte Lamination (Both)',6],['Gloss Water Based Varnish (Both)',-4],['Soft Touch Lamination (Both)',28]];
const SPOTUV = [['No Required',0],['Silkscreen Spot UV (Front)',45],['Silkscreen Spot UV (Both)',78]];
const QTYS = [100,300,500,1000,2000,3000,5000];

// Per-product configurator corrections layered over the crawled engine, keyed by the
// engine product name. Built product-by-product from a live Excard comparison so the
// Printoka configurator matches the source order form exactly. DISPLAY-ONLY — pricing
// still uses the engine's own option values, so nothing here can change a price.
//   hide:      field keys Excard does not show (removed from the configurator)
//   label:     { fieldKey: 'display label' }         — rename a question
//   optLabel:  { fieldKey: { engineValue: 'shown label' } } — rename option text (value kept)
//   placeholder: [fieldKeys] that start unselected showing "-- Please select --"
//   remark:    { fieldKey: 'helper text under the field' }
// Captured Excard live CASH price tables, loaded at runtime from /pricing/*.json (see
// loadExcardPrices in componentDidMount). Keyed by engine product name → { qtys, standard,
// fold, addons }. priceBase reads these so the configurator quotes Excard's live price to
// the cent (pricing policy: follow Excard, not the frozen crawl engine).
let EXCARD_PRICES = {};
// package (N-in-1) design multipliers for Business Card
const BC_PKG_N = { 'Normal': 1, '2in1': 2, '3in1': 3, '4in1': 4, '5in1': 5, '6in1': 6, '7in1': 7, '8in1': 8, '9in1': 9, '10in1': 10 };
// Business Card price from the captured Excard table, for every card category. Price is
// size-independent (standard sizes, custom size, fold open size and die-cut size all price
// the same within a category); folds ignore creasing type. All applicable finishing is
// price-neutral on Excard now (lamination/embossing/round-corner/hot-stamping/silkscreen)
// EXCEPT hole punching (standard cards only). Package (N designs) = base × N.
function bcSegTable(T, cat) {
  if (cat === 'Standard') return T.standard;
  if (cat === 'Thin Fold') return T.fold && T.fold.thin_fold;
  if (cat === 'Fat Fold') return T.fold && T.fold.fat_fold;
  if (cat === 'Custom Die Cut') return T.die_cut;
  if (cat === 'Plastic Card') return T.plastic;
  return null;
}
function bcPriceBase(cfg, qty) {
  const T = EXCARD_PRICES['Business Card']; if (!T) return null;
  const table = bcSegTable(T, cfg.category); if (!table) return null;
  const branch = table[cfg.paper]; if (!branch) return null;
  const arr = branch[cfg.printcolour]; if (!arr) return null;
  const qi = T.qtys.indexOf(qty); if (qi < 0) return null;
  let base = arr[qi]; if (base == null) return null;
  const A = T.addons || {};
  // hole punching is a Standard-card-only add-on on Excard (qty curve, paper/diameter-independent)
  let hp = 0;
  if (cfg.category === 'Standard' && cfg.holepunching && !/^no/i.test(cfg.holepunching) && Array.isArray(A.holepunch) && A.holepunch[qi] != null) hp = A.holepunch[qi];
  const N = BC_PKG_N[cfg.package] || 1;                    // N designs, same spec → ×N
  return Math.round((base + hp) * N * 100) / 100;
}

const CFG_OVERRIDES = {
  'Business Card': {
    priceBase: bcPriceBase,
    // Excard's Business Card has no area inputs; the foil colour is a swatch picker (hs_colours widget)
    hide: ['hot_stamping_w', 'hot_stamping_h', 'embossing_w', 'embossing_h', 'hot_stamping_colour'],
    label: { lamination: 'Paper Lamination' },
    // hot stamping is price-neutral online (block quoted separately) — safe to match Excard's list exactly
    optionsOverride: {
      hot_stamping: ['No Hot Stamping', '1C (Front)', '1C (Back)', '1C (Front) + 1C (Back)', '1C (Front) + 2C (Back)', '2C (Front)', '2C (Back)', '2C (Front) + 1C (Back)', '2C (Front) + 2C (Back)'],
      hot_stamping_colour: ['Gold', 'Silver', 'Green', 'Blue', 'Black', 'Red'],
      // Paper list per Excard per card type: Custom Die-Cut drops Gloss Art Card 360gsm;
      // Plastic Card is frosted plastic only. Other categories keep the engine's paper list.
      paper: (cfg, options) => {
        if (cfg.category === 'Plastic Card') return ['Frosted Plastic 0.4mm'];
        if (cfg.category === 'Custom Die Cut') return (options || []).filter(p => p !== 'Gloss Art Card 360gsm');
        return options;
      },
      // Plastic Card prints 4C or 4C + White; every other card type is 4C (Both) / 4C (Front).
      printcolour: (cfg, options) => cfg.category === 'Plastic Card' ? ['4C', '4C & White'] : options,
      // fold cards have their own preset open sizes; Plastic Card is a single fixed size;
      // Standard + Custom Die-Cut keep the engine's standard size list.
      size: (cfg, options) => {
        if (cfg.category === 'Thin Fold') return ['54mm × 178mm (Open Size)', '52mm × 172mm (Open Size)', '50mm × 172mm (Open Size)', '52mm × 156mm (Open Size)', 'Other (Custom Size)'];
        if (cfg.category === 'Fat Fold') return ['89mm × 108mm (Open Size)', '86mm × 104mm (Open Size)', '86mm × 100mm (Open Size)', '86mm × 88mm (Open Size)', 'Other (Custom Size)'];
        if (cfg.category === 'Plastic Card') return ['54mm x 89mm'];
        return options;
      },
    },
    // per-card-type field visibility, mirroring Excard's finishing rules exactly:
    //   hole punch → Standard only · round corner → Standard + Plastic · hot stamp / embossing /
    //   silkscreen → Standard + folds · lamination → coated papers only (not fine/plastic).
    hideWhen: {
      holepunching: cfg => cfg.category !== 'Standard',
      round_corner: cfg => !(cfg.category === 'Standard' || cfg.category === 'Plastic Card'),
      round_corner_position: cfg => !(cfg.category === 'Standard' || cfg.category === 'Plastic Card'),
      hot_stamping: cfg => ['Standard', 'Thin Fold', 'Fat Fold'].indexOf(cfg.category) < 0,
      embossing: cfg => ['Standard', 'Thin Fold', 'Fat Fold'].indexOf(cfg.category) < 0,
      silkscreen_spot_uv: cfg => ['Standard', 'Thin Fold', 'Fat Fold'].indexOf(cfg.category) < 0,
      lamination: cfg => ['Gloss Art Card 250gsm', 'Gloss Art Card 310gsm', 'Gloss Art Card 360gsm', 'Matte Art Card 250gsm'].indexOf(cfg.paper) < 0,
    },
    // fields rendered as an image picker (base path; image = base + optionValue + '.jpg')
    optImages: { round_corner_position: 'assets/options/businesscard-roundcorner/' },
    // custom size prices exactly as the standard 54x89 card (dimension-independent, verified on Excard)
    priceSub: { size: { 'Other (Custom Size)': '54mm x 89mm' } },
    // NOTE: Silkscreen Spot UV, embossing, round corner & hot stamping are all price-neutral
    // on Excard now (captured 2026-09-21) — no priceAddon. Hole punching is priced inside
    // bcPriceBase. Base pricing comes entirely from the captured Excard table via priceBase.
    // Custom Size inputs appear only when Size = "Other (Custom Size)"; the ranges depend on the
    // card category (Standard / Thin Fold / Fat Fold). Creasing shows for fold cards.
    addFields: [
      { key: 'custom_h', label: 'Custom height (mm)', type: 'number', min: 40, max: 54, section: 'General', neutral: true, after: 'size', placeholder: 'e.g. 50', showWhen: { all: [{ field: 'category', value: 'Standard' }, { field: 'size', value: 'Other (Custom Size)' }] } },
      { key: 'custom_w', label: 'Custom width (mm)', type: 'number', min: 40, max: 89, section: 'General', neutral: true, after: 'size', placeholder: 'e.g. 85', note: 'Width must be greater than height', showWhen: { all: [{ field: 'category', value: 'Standard' }, { field: 'size', value: 'Other (Custom Size)' }] } },
      // Thin Fold custom — open card 110–178 mm wide, folds down the middle (H 52–54 mm)
      { key: 'fold_h_thin', label: 'Open Height (mm)', type: 'number', min: 52, max: 54, section: 'General', neutral: true, after: 'size', placeholder: 'e.g. 54', showWhen: { all: [{ field: 'category', value: 'Thin Fold' }, { field: 'size', value: 'Other (Custom Size)' }] } },
      { key: 'fold_w_thin', label: 'Open Width (mm)', type: 'number', min: 110, max: 178, section: 'General', neutral: true, after: 'size', placeholder: 'e.g. 178', note: 'folds to half width', showWhen: { all: [{ field: 'category', value: 'Thin Fold' }, { field: 'size', value: 'Other (Custom Size)' }] } },
      // Fat Fold custom — open card 60–108 mm wide (H 70–89 mm)
      { key: 'fold_h_fat', label: 'Open Height (mm)', type: 'number', min: 70, max: 89, section: 'General', neutral: true, after: 'size', placeholder: 'e.g. 89', showWhen: { all: [{ field: 'category', value: 'Fat Fold' }, { field: 'size', value: 'Other (Custom Size)' }] } },
      { key: 'fold_w_fat', label: 'Open Width (mm)', type: 'number', min: 60, max: 108, section: 'General', neutral: true, after: 'size', placeholder: 'e.g. 108', note: 'folds to half width', showWhen: { all: [{ field: 'category', value: 'Fat Fold' }, { field: 'size', value: 'Other (Custom Size)' }] } },
      { key: 'creasing', label: 'Creasing', options: ['Standard Creasing', 'Customised Creasing'], section: 'General', neutral: true, after: 'size', showWhen: { field: 'category', values: ['Thin Fold', 'Fat Fold'] } },
      // Customised Creasing: distance of the crease from the left edge (min 10 mm)
      { key: 'crease_add', label: 'Crease position (mm)', type: 'number', min: 10, section: 'General', neutral: true, after: 'size', placeholder: 'e.g. 78', note: 'Distance of the crease from the left edge (minimum 10 mm).', showWhen: { field: 'creasing', value: 'Customised Creasing' } },
      // Hot Stamping foil colours: one 6-colour swatch picker per colour in the option + block
      { key: 'hs_colours', widget: 'foilColours', section: 'Optional Finishing', neutral: true, after: 'hot_stamping', showWhen: { field: 'hot_stamping', notValues: ['No Hot Stamping'] } },
    ],
    optLabel: {
      category: { 'Standard': 'Standard Card', 'Custom Die Cut': 'Custom Die-Cut' },
      paper: { 'Gloss Art Card 250gsm': 'Gloss Art Card 250gsm (2 side coated)', 'Gloss Art Card 310gsm': 'Gloss Art Card 310gsm (2 side coated)', 'Gloss Art Card 360gsm': 'Gloss Art Card 360gsm (2 side coated)', 'Synthetic Paper 180micron': 'Synthetic Paper 180micron (0.18mm)' },
      lamination: { 'Gloss Water Based Varnish (Both)': 'Gloss Water Based Varnish (Both) (Free)' },
      package: { 'Normal': 'Normal (1 Design)', '2in1': '2 In 1 (2 Designs)', '3in1': '3 In 1 (3 Designs)', '4in1': '4 In 1 (4 Designs)', '5in1': '5 In 1 (5 Designs)', '6in1': '6 In 1 (6 Designs)', '7in1': '7 In 1 (7 Designs)', '8in1': '8 In 1 (8 Designs)', '9in1': '9 In 1 (9 Designs)', '10in1': '10 In 1 (10 Designs)' },
      round_corner: { 'No': 'No Round Corner', 'Required': 'Required Round Corner' },
      holepunching: { '3mm': 'Hole Punching - Diameter 3mm', '5mm': 'Hole Punching - Diameter 5mm' },
    },
    placeholder: ['size', 'paper', 'lamination', 'quantity'],
    bestSellerQty: [300, 500, 1000],
    // Silkscreen Spot UV is only offered with Matte Lamination (Both) on Gloss Art Card
    // 250/310gsm at qty >= 300 (Excard rule); otherwise only "No Required".
    optGate: {
      silkscreen_spot_uv: (cfg, qty) => cfg.lamination === 'Matte Lamination (Both)' && ['Gloss Art Card 250gsm', 'Gloss Art Card 310gsm'].indexOf(cfg.paper) >= 0 && (qty || 0) >= 300,
    },
    remark: {
      silkscreen_spot_uv: 'Available with Matte Lamination (Both Sides) only. Gloss Art Card 250gsm & 310gsm only. Qty: 300, 500, 1,000 – 10,000.',
      quantity: 'For Silkscreen Spot UV: available qty 300, 500, 1,000 – 10,000 only.',
      package: 'This is an easy-order function for you to order multiple business card sets which are the same spec. (same size, paper, quantity and spot UV finishing for all) but contain different designs.',
      hot_stamping: '6 colours: Gold, Silver, Green, Blue, Black & Red. Options with Back side require Gloss Art Card.',
      holepunching: '1 hole at fixed position on the shorter side.',
      embossing: 'Embossing adds 1 production day. Not compatible with Silkscreen Spot UV.',
      round_corner: 'This is the actual round corner position (Front), for either portrait or landscape. No rotation required.',
    },
    // suppress the engine's stale category note (every card type is now priced online)
    noteOverride: { category: null },
    processDays: 1, // Excard base process day for a plain Business Card (finishing may extend it)
  },
  // Flyer / Brochure (Litho Offset Loose Sheet) — Excard "lo-loose-sheet".
  // Base pricing verified: A4 / Gloss Art Paper 128gsm / 4C Both / 1,000 = RM168.55 (=Excard cash).
  'Flyer (= Loose Sheet Litho)': {
    label: { colour: 'Print Colour', package: 'Package', hole_punch_position: 'Hole Punching Side' },
    hide: ['hs_size', 'hs_colour'], // Excard's flyer hot stamping is a plain select (no size/foil sub-fields)
    placeholder: ['size', 'paper', 'colour', 'quantity'],
    optLabel: {
      size: { 'A1 (594mm x 840mm)': 'A1 (594mm × 840mm)', 'A2 (420mm x 594mm)': 'A2 (420mm × 594mm)', 'A3 (297mm x 420mm)': 'A3 (297mm × 420mm)', 'A4 (210mm x 297mm)': 'A4 (210mm × 297mm)', 'A5 (148mm x 210mm)': 'A5 (148mm × 210mm)', 'A6 (148mm x 105mm)': 'A6 (105mm × 148mm)', '3xA4 (297mm x 630mm)': '3 × A4 (297mm × 630mm)', '4xA4 (297mm x 840mm)': '4 × A4 (297mm × 840mm)', '4xA5 (210mm x 594mm)': '4 × A5 (210mm × 594mm)', 'Other (Custom Size)': 'Custom Size' },
      package: { 'Normal': 'Normal', '2in1': '2 in 1', '3in1': '3 in 1', '4in1': '4 in 1', '5in1': '5 in 1', '6in1': '6 in 1', '7in1': '7 in 1', '8in1': '8 in 1', '9in1': '9 in 1', '10in1': '10 in 1' },
      hot_stamping: { 'Not Required': 'Not Required', '1C (Front)': '1C (Front)', '1C (Back)': '1C (Back)', '2C (Front)': '2C (Front)', '2C (Back)': '2C (Back)' },
    },
    remark: {
      colour: '1C only for Simili 80gsm / 100gsm. 3 × A4, 4 × A4 and 4 × A5 are 2-sides printing only.',
      hot_stamping: '1 side only (Front OR Back). Max 2 colours.',
      hole_punching: '1 hole at centre of selected edge. Size: H 70–420mm × W 40–800mm. Not available for A1 / 4 × A4, and not with Folding / Creasing / Perforation.',
      perforation: '1–6 lines, minimum 45mm gap. A3 perforation is landscape only. A6 available in Standard spec only. Not with Folding / Creasing / Hole Punching.',
      fold: 'Open Size — Height 90–420mm, Width 120–630mm. After fold, width ≥ 25mm.',
      creasing: 'Min 4mm gap between 2 creasing lines. Available area: H 148–325mm × W 210–695mm.',
      envelope: 'Envelope quantity follows order quantity.',
    },
  },
};

const CATS = [
  ['Cards',8,'card'],['Books & Stationery',19,'book'],['Stickers & Labels',7,'sticker'],
  ['Large Format',13,'banner'],['Packaging & Boxes',18,'box'],['Calendars & Diary',5,'cal'],
  ['Apparel & Gifts',17,'mug'],['Money Packet',4,'flyer'],['Misc',2,'flyer'],
];

const CAT_PRODUCTS = [
  ['Business Card','Cards','card',38.00,'Exact price','3 working days'],
  ['Creative Cut Card — Digital','Cards','card',72.00,'Exact price','4 working days'],
  ['Kad Kahwin — Digital','Cards','card',129.00,'Exact price','5 working days'],
  ['Greeting Card — Litho','Cards','card',96.00,'Exact price','5 working days'],
  ['PVC Card — Digital','Cards','card',188.00,'On request','7 working days'],
  ['ID Card — Digital','Cards','card',142.00,'Exact price','5 working days'],
  ['Tent Card — Litho','Cards','card',210.00,'Exact price','6 working days'],
  ['Voucher — Litho','Cards','card',165.00,'Exact price','6 working days'],
];

const BEST = [
  ['Business Card','card','from RM 38'],['Label Sticker — Digital','sticker','from RM 45'],
  ['Flyer','flyer','from RM 88'],['Booklet — Litho (Offset)','book','from RM 420'],
  ['Banner — Litho','banner','from RM 78'],['Kad Kahwin — Digital','card','from RM 129'],
  ['Mug — Litho','mug','from RM 24'],['Paper Bag — Litho','box','from RM 310'],
];

const TIERS = [
  ['Standard','Automatic','—','Full platform access, tracking, credit balance'],
  ['Bronze','RM 1,000+','5% off','Catalogue discount on every job'],
  ['Silver','RM 3,000+','8% off','Discount + early access to campaigns'],
  ['Gold','RM 5,000+','10% off','Priority production-queue placement'],
  ['Platinum','RM 10,000+','up to 15%','Key Account Manager + negotiated credit terms'],
];

class Component extends DCLogic {
  state = {
    route: 'admin', megaOpen: false, banner: true, cartCount: 2, tab: 'spec',
    paper: 'Gloss Art Card 250gsm', size: '54mm x 89mm', lam: 'Gloss Lamination (Both)',
    spotuv: 'No Required', qty: 1000, corner: 'No', checkoutStep: 4, dialog: null,
    useCredit: true, catSort: 'Popularity', outletTab: 'all', vendorRow: 3, crmThread: 0,
  };

  go = (id) => { if (!this.canAccess(id)) id = this.homeFor(); this.setState({ route: id, megaOpen: false }); if (typeof window !== 'undefined') window.scrollTo(0, 0); const r = this.opsRoleFor(id); if (r) this.opsLoad(this.opsActingRole()); if (id === 'learn') this.blogLoad(); if (id === 'support') this.loadFaq(); if (id === 'downloads') this.loadDownloads(); if (id === 'track' && this.state.order && !this.state.trackOrder) this.trackLookup(this.state.order.id); if (id === 'dash' && this.state.user) { this.loadUserOrders(); this.loadAccount(); this.loadQuotes(); this.loadCustomInvoices(); } if (id === 'invoices' && this.state.user) { this.loadUserOrders(); this.loadCustomInvoices(); } if (id === 'checkout' && this.state.user) this.loadAccount(); if (id === 'production') this.loadVendors(); if (id === 'vendor') this.loadVendorRequests(); if (id === 'admin') this.loadAdmin(); if (['outlet', 'prepress', 'production', 'logistics'].indexOf(id) >= 0) { this.loadNotifications(); this.loadQuotes(); } if (id === 'outlet') this.loadStaffOrders(); };

  onNav = (e) => {
    // any click that bubbles here (custom-dropdown clicks stopPropagation) closes an open dropdown
    if (this.state.ddOpen != null) this.setState({ ddOpen: null });
    const el = e.target.closest && e.target.closest('[data-go]');
    if (!el) return;
    const v = el.getAttribute('data-go');
    // Product links point to the server-rendered SEO page (/<slug>-printing). Let a plain
    // left-click do a FULL navigation so everyone lands on that static SEO page, not the SPA
    // configurator — the SEO page's "Check Price Now" then loads the configurator (/configure/).
    if (el.tagName === 'A' && v && v.indexOf('open:') === 0 && el.getAttribute('href') && (e.button == null || e.button === 0) && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey) return;
    // other real <a href> cards (categories, blog): let modified/middle clicks open a new tab,
    // but intercept a plain left-click so it routes in-app instead of a full page reload.
    if (el.tagName === 'A' && el.getAttribute('href') && (e.button == null || e.button === 0) && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey) e.preventDefault();
    if (v === '_mega') return this.setState(s => ({ megaOpen: !s.megaOpen }));
    if (v === '_dismiss') return this.setState({ banner: false });
    if (v === '_locale') { const L = ['EN', 'ZH', 'MS']; return this.setState(s => ({ locale: L[(L.indexOf(s.locale || 'EN') + 1) % 3] })); }
    if (v === '_country') { const C = ['MY', 'SG', 'BN']; return this.setState(s => ({ country: C[(C.indexOf(s.country || this.props.defaultCountry || 'MY') + 1) % 3] })); }
    if (v.indexOf('opt:') === 0) {
      const [, k, val] = v.split(':');
      return this.setState({ [k]: k === 'qty' ? Number(val) : val });
    }
    if (v.indexOf('set:') === 0) {
      const [, k, val] = v.split(':');
      return this.setState({ [k]: isNaN(Number(val)) ? val : Number(val) });
    }
    if (v === '_closeDialog') return this.setState({ dialog: null });
    if (v.indexOf('dialog:') === 0) return this.setState({ dialog: v.slice(7) });
    // Real pricing engine: product switch + per-field config change (values may contain ':')
    if (v.indexOf('prod:') === 0) return this.setState({ prodId: Number(v.slice(5)), cfg: {}, qty: 1000, qtyChosen: false });
    if (v.indexOf('open:') === 0) { const pid = Number(v.slice(5)); if (typeof window !== 'undefined') window.scrollTo(0, 0); this.pushUrl(this.productPath(pid) || '/'); return this.setState({ prodId: pid, cfg: {}, qty: 1000, qtyChosen: false, route: 'product', megaOpen: false }); }
    if (v.indexOf('catopen:') === 0) { const cf = v.slice(8); if (typeof window !== 'undefined') window.scrollTo(0, 0); this.pushUrl(cf === 'all' ? '/products' : '/products/' + cf); return this.setState({ catFilter: cf, route: 'category', megaOpen: false }); }
    if (v.indexOf('blog:') === 0) return this.blogOpen(v.slice(5));
    if (v === 'addraddsave') return this.addressAdd();
    if (v.indexOf('addrdel:') === 0) return this.addressDelete(v.slice(8));
    if (v.indexOf('addrdefault:') === 0) return this.addressDefault(v.slice(12));
    if (v === 'dologin') return this.login();
    if (v === 'doregister') return this.register();
    if (v === 'dologout') return this.logout();
    if (v === 'addcart') return this.addToCart();
    if (v.indexOf('rmcart:') === 0) return this.removeFromCart(Number(v.slice(7)));
    if (v === 'placeorder') return this.placeOrder();
    if (v === 'doquote') return this.submitQuote();
    if (v.indexOf('doc:') === 0) { const rest = v.slice(4), i = rest.indexOf(':'); return this.openDoc(rest.slice(i + 1), rest.slice(0, i)); }
    if (v.indexOf('vieworder:') === 0) return this.openOrder(v.slice(10));
    if (v.indexOf('trackorder:') === 0) { const oid = v.slice(11); if (typeof window !== 'undefined') window.scrollTo(0, 0); this.setState({ route: 'track', trackInput: oid, megaOpen: false }); return this.trackLookup(oid); }
    if (v.indexOf('cfg:') === 0) {
      const rest = v.slice(4), i = rest.indexOf(':'), k = rest.slice(0, i), val = rest.slice(i + 1);
      return this.setState(s => ({ cfg: Object.assign({}, s.cfg, { [k]: val }) }));
    }
    // Custom-stack build: all screens live in this one app, so navigate in-app
    // instead of redirecting to per-page .dc.html files (PAGE_FILES).
    this.go(v);
  };

  tier() { return (this.state.user && this.state.user.tier) || this.props.memberTier || 'Gold'; }
  tierPct() { return ({ Standard: 0, Bronze: 5, Silver: 8, Gold: 10, Platinum: 15 })[this.tier()] || 0; }
  cc() { return this.state.country || this.props.defaultCountry || 'MY'; }
  loc() { return this.state.locale || 'EN'; }
  currency() { return ({ MY: 'RM', SG: 'SGD', BN: 'BND' })[this.cc()]; }
  fx() { return ({ MY: 1, SG: 0.31, BN: 0.31 })[this.cc()]; }
  taxLabel() { return ({ MY: 'SST 8%', SG: 'GST 9%', BN: 'No sales tax' })[this.cc()]; }
  couriers() { return ({ MY: ['J&T Express', 'Pos Laju', 'Self-pickup (Klang Valley, −5%)'], SG: ['Ninja Van', 'Qxpress', 'Self-pickup (CBD)'], BN: ['Pos Brunei', 'DHL cross-border'] })[this.cc()]; }
  t(key) {
    const D = {
      products: { EN: 'Products', ZH: '产品', MS: 'Produk' },
      search: { EN: 'Search', ZH: '搜索', MS: 'Cari' },
      menu: { EN: 'Menu', ZH: '菜单', MS: 'Menu' },
      heroTitle: { EN: 'Print. Create. Elevate.', ZH: '印刷。创作。提升。', MS: 'Cetak. Cipta. Tingkatkan.' },
      heroBody: { EN: 'Instant online pricing on more than 100 printing products, produced through a 30-vendor network across Malaysia, Singapore and Brunei.', ZH: '超过 100 种印刷产品即时在线报价，由马来西亚、新加坡和文莱的 30 家合作印刷厂生产。', MS: 'Harga dalam talian serta-merta untuk lebih 100 produk cetakan, dihasilkan melalui rangkaian 30 pembekal di Malaysia, Singapura dan Brunei.' },
      heroCta: { EN: 'Order online now', ZH: '立即在线下单', MS: 'Pesan dalam talian' },
      discover: { EN: 'Discover our printing products', ZH: '探索我们的印刷产品', MS: 'Terokai produk cetakan kami' },
      discoverSub: { EN: 'Every product is priced online with its full specification, artwork guide and print-ready template attached.', ZH: '每款产品均在线标价，并附完整规格、稿件指南与可印刷模板。', MS: 'Setiap produk berharga dalam talian dengan spesifikasi penuh, panduan artwork dan templat sedia cetak.' },
      viewAll: { EN: 'View all 100+ products', ZH: '查看全部 100+ 产品', MS: 'Lihat semua 100+ produk' },
      howEasy: { EN: 'How easy is it to order?', ZH: '下单有多简单？', MS: 'Semudah mana untuk memesan?' },
      shortRun: { EN: 'Short run printing, from one piece', ZH: '小批量印刷，一件起印', MS: 'Cetakan kuantiti kecil, dari satu keping' },
      morePaper: { EN: 'Printing more than just paper', ZH: '不只是纸张印刷', MS: 'Mencetak lebih daripada sekadar kertas' },
      checkPrice: { EN: 'Check Price Now', ZH: '立即查看价格', MS: 'Semak Harga' },
    };
    return (D[key] || {})[this.loc()] || (D[key] || {}).EN || key;
  }

  // ---------- real pricing engine adapter (window.PricingEngine, built from the calculator repo) ----------
  pkEngine() { return (typeof window !== 'undefined' && window.PricingEngine) || null; }
  pkProducts() { const E = this.pkEngine(); return E ? E.DATA.products : []; }
  pkProduct() {
    const E = this.pkEngine(); if (!E) return null;
    const id = this.state.prodId != null ? this.state.prodId : 1;
    return E.DATA.products.find(p => p.id === id) || E.DATA.products[0];
  }
  // resolve an engine product id from a name (exact, then loose match); null if unknown
  pkIdByName(name) {
    const list = this.pkProducts(); if (!list.length || !name) return null;
    let p = list.find(x => x.name === name);
    if (!p) { const n = name.toLowerCase(); p = list.find(x => x.name.toLowerCase() === n) || list.find(x => x.name.toLowerCase().indexOf(n) === 0) || list.find(x => x.name.toLowerCase().indexOf(n) !== -1); }
    return p ? p.id : null;
  }
  // a 'go' verb that opens a product by name, falling back to the catalogue if not priced
  goByName(name) { const id = this.pkIdByName(name); return id != null ? 'open:' + id : 'category'; }
  // ---------- crawlable product URLs: /<name>-printing ----------
  // Each product gets a real, shareable, indexable path derived from its display name, so
  // product pages have distinct URLs (canonical + sitemap) instead of living only in state.
  slugify(s) { return String(s || '').toLowerCase().replace(/&/g, ' and ').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, ''); }
  pkSlug(id) { const n = this.catName(id); return n ? this.slugify(n) + '-printing' : null; }
  pkIdBySlug(slug) {
    const s = String(slug || '').toLowerCase().replace(/\/+$/, '');
    const prods = this.pkProducts();
    for (const p of prods) if (this.pkSlug(p.id) === s) return p.id;
    return null;
  }
  productPath(id) { const sl = this.pkSlug(id); return sl ? '/' + sl : null; }
  // crawlable href for a nav token so product/category cards can be real <a> links (internal
  // link equity + anchor text). Returns null for tokens that are pure in-app state changes.
  navHref(go) {
    if (!go || typeof go !== 'string') return null;
    if (go.indexOf('open:') === 0) return this.productPath(Number(go.slice(5)));
    if (go.indexOf('catopen:') === 0) { const cf = go.slice(8); return cf === 'all' ? '/products' : '/products/' + cf; }
    if (go === 'packaging') return '/products/packaging-boxes';
    if (go.indexOf('blog:') === 0) return '/blog/' + go.slice(5) + '/';
    return null;
  }
  // props for a clickable card that navigates: a real <a href> when the token maps to a URL,
  // else the plain data-go span/div. Spread onto an h('a',…)/h('div',…) accordingly.
  cardGo(go) { const href = this.navHref(go); return href ? { tag: 'a', props: { href, 'data-go': go } } : { tag: 'div', props: { 'data-go': go } }; }
  // push a route's URL into the address bar so it is shareable/back-navigable (SPA history)
  pushUrl(path) { try { if (typeof history !== 'undefined' && path && location.pathname !== path) history.pushState({ pk: 1 }, '', path); } catch (e) {} }
  // per-product quantity model straight from the pricing engine (moq / options / chips)
  pkQtyObj(id) {
    const E = this.pkEngine(); if (!E) return null;
    const pid = id != null ? id : (this.state.prodId != null ? this.state.prodId : 1);
    const p = E.DATA.products.find(x => x.id === pid);
    return (p && p.quantity) ? p.quantity : null;
  }
  pkShown(f, cfg) {
    if (!f.showWhen) return true;
    const clauses = f.showWhen.all ? f.showWhen.all : [f.showWhen];
    return clauses.every(c => {
      const cur = cfg[c.field];
      if (c.values) return c.values.indexOf(cur) !== -1;
      if (c.notValues) return c.notValues.indexOf(cur) === -1;
      if (c.value != null) return cur === c.value;
      if (c.notValue != null) return cur !== c.notValue;
      return true;
    });
  }
  // per-product configurator override (display-only corrections vs the live source form)
  cfgOv() { const p = this.pkProduct(); return (p && CFG_OVERRIDES[p.name]) || {}; }
  pkHidden(key) { const ov = this.cfgOv(); return !!(ov.hide && ov.hide.indexOf(key) >= 0); }
  // are all "please select" fields chosen yet? (gates the live price, like the source form)
  pkReady() { const ov = this.cfgOv(); const ph = ov.placeholder || []; const sc = this.state.cfg || {}; const hw = ov.hideWhen || {}; const hidden = k => { try { return hw[k] ? !!hw[k](sc) : false; } catch (e) { return false; } }; return ph.every(k => hidden(k) ? true : (k === 'quantity' ? !!this.state.qtyChosen : (sc[k] != null && sc[k] !== ''))); }
  // live size simulator: a proportional diagram of the selected size (standard or custom),
  // with Width/Height dimension lines — so the customer can see exactly what they picked.
  sizeSim() {
    const cfg = this.pkV(), scfg = this.state.cfg || {}, ov = this.cfgOv();
    // folded cards (Thin/Fat Fold) draw the open card + a crease/fold line, like Excard.
    const cat = String(cfg.category || '');
    const fold = /^Thin Fold$/.test(cat) ? 'thin' : /^Fat Fold$/.test(cat) ? 'fat' : null;
    const sizePhTop = !!(ov.placeholder && ov.placeholder.indexOf('size') >= 0);
    if (fold) {
      const sizeSel = String((sizePhTop ? scfg.size : cfg.size) || '');
      if (!sizeSel) return { pendingSize: true };
      let W, H;
      if (/other|custom/i.test(sizeSel)) {
        const rng = fold === 'thin' ? { h: [52, 54], w: [110, 178] } : { h: [70, 89], w: [60, 108] };
        H = parseFloat(fold === 'thin' ? scfg.fold_h_thin : scfg.fold_h_fat);
        W = parseFloat(fold === 'thin' ? scfg.fold_w_thin : scfg.fold_w_fat);
        // only preview a size that is complete AND within range (no out-of-range flashes while typing)
        if (!(H >= rng.h[0] && H <= rng.h[1] && W >= rng.w[0] && W <= rng.w[1])) return { pendingSize: true, msg: 'Enter an open size within range — Height ' + rng.h[0] + '–' + rng.h[1] + ' mm, Width ' + rng.w[0] + '–' + rng.w[1] + ' mm.' };
      } else {
        // preset e.g. "54mm × 178mm (Open Size)" → height × open width
        const m = sizeSel.match(/(\d+(?:\.\d+)?)\s*mm\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm/i);
        if (!m) return { pendingSize: true };
        H = +m[1]; W = +m[2];
      }
      // crease position: middle for Standard, user-chosen (Add mm from left, min 10) for Customised
      let creaseAt = W / 2;
      if (/Customised/i.test(String(cfg.creasing || ''))) {
        const ca = parseFloat(scfg.crease_add);
        if (!(ca >= 10 && ca <= W - 10)) return { pendingSize: true, msg: 'Enter the crease position (Add) between 10 and ' + Math.round(W - 10) + ' mm.' };
        creaseAt = ca;
      }
      return this.foldDiagram(W, H, cfg.creasing, creaseAt);
    }
    // read the user's ACTUAL choice for a "please select" size (not the engine's auto-filled
    // default), so the preview stays empty until a size is picked and then clearly reacts.
    const sizePh = !!(ov.placeholder && ov.placeholder.indexOf('size') >= 0);
    const sv = String((sizePh ? scfg.size : cfg.size) || '');
    if (!sv) return { pendingSize: true };
    let a = null, b = null, custom = false;
    if (/other|custom/i.test(sv)) {
      const ch = parseFloat(scfg.custom_h), cw = parseFloat(scfg.custom_w);
      // only preview a complete, in-range custom size (Height 40–54, Width 40–89)
      if (!(ch >= 40 && ch <= 54 && cw >= 40 && cw <= 89)) return { pending: true, msg: 'Enter a custom size within range — Height 40–54 mm, Width 40–89 mm.' };
      b = ch; a = cw; custom = true; // width, height
    } else {
      const m = sv.match(/(\d+(?:\.\d+)?)\s*mm\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm/i);
      if (!m) return null;
      a = Math.max(+m[1], +m[2]); b = Math.min(+m[1], +m[2]);
    }
    const portrait = /portrait/i.test(String(cfg.orientation || ''));
    let W = custom ? a : a, H = custom ? b : b;
    if (portrait) { const t = W; W = H; H = t; }
    if (!(W > 0 && H > 0)) return null;
    const maxW = 210, maxH = 120, ar = W / H;
    let dw = maxW, dh = maxW / ar; if (dh > maxH) { dh = maxH; dw = maxH * ar; }
    const pad = 34, VW = dw + pad * 2, VH = dh + pad * 2, x0 = pad, y0 = pad;
    const dim = (x1, y1, x2, y2) => h('line', { x1, y1, x2, y2, stroke: MUT, strokeWidth: 1, markerStart: 'url(#pkArrow)', markerEnd: 'url(#pkArrow)' });
    return {
      svg: h('svg', { viewBox: '0 0 ' + VW + ' ' + VH, style: { width: '100%', maxWidth: 300, height: 'auto', display: 'block', margin: '0 auto' } },
        h('defs', null, h('marker', { id: 'pkArrow', markerWidth: 8, markerHeight: 8, refX: 4, refY: 4, orient: 'auto' }, h('path', { d: 'M1 4 L7 1 L7 7 Z', fill: MUT }))),
        h('rect', { x: x0, y: y0, width: dw, height: dh, fill: '#fdf2f2', stroke: TEAL, strokeWidth: 1.5, rx: 3 }),
        dim(x0, y0 + dh + 16, x0 + dw, y0 + dh + 16),
        h('text', { x: x0 + dw / 2, y: y0 + dh + 30, textAnchor: 'middle', fontSize: 12, fontWeight: 600, fill: INK }, 'Width ' + Math.round(W) + ' mm'),
        dim(x0 - 16, y0, x0 - 16, y0 + dh),
        h('text', { x: x0 - 22, y: y0 + dh / 2, textAnchor: 'middle', fontSize: 12, fontWeight: 600, fill: INK, transform: 'rotate(-90 ' + (x0 - 22) + ' ' + (y0 + dh / 2) + ')' }, 'Height ' + Math.round(H) + ' mm')),
      label: (custom ? 'Custom size · ' : '') + Math.round(W) + ' × ' + Math.round(H) + ' mm',
    };
  }
  // fold-card diagram: open card with a dashed crease line at the given position (default centre),
  // panel arrows and left/right panel-width labels, matching Excard.
  foldDiagram(W, H, creasing, creaseAt) {
    if (!(creaseAt > 0 && creaseAt < W)) creaseAt = W / 2;
    const leftW = creaseAt, rightW = W - creaseAt;
    const maxW = 224, maxH = 108, ar = W / H;
    let dw = maxW, dh = maxW / ar; if (dh > maxH) { dh = maxH; dw = maxH * ar; }
    const pad = 42, VW = dw + pad * 2, VH = dh + pad * 2, x0 = pad, y0 = pad, midy = y0 + dh / 2;
    const cx = x0 + (creaseAt / W) * dw; // crease x-position, proportional
    const arrow = (x1, y1, x2, y2) => h('line', { x1, y1, x2, y2, stroke: MUT, strokeWidth: 1, markerStart: 'url(#pkA2)', markerEnd: 'url(#pkA2)' });
    const seg = (x1, x2, val) => [arrow(x1 + 5, midy, x2 - 5, midy), h('text', { x: (x1 + x2) / 2, y: midy - 5, textAnchor: 'middle', fontSize: 11, fontWeight: 600, fill: INK }, Math.round(val))];
    return {
      svg: h('svg', { viewBox: '0 0 ' + VW + ' ' + VH, style: { width: '100%', maxWidth: 300, height: 'auto', display: 'block', margin: '0 auto' } },
        h('defs', null, h('marker', { id: 'pkA2', markerWidth: 8, markerHeight: 8, refX: 4, refY: 4, orient: 'auto' }, h('path', { d: 'M1 4 L7 1 L7 7 Z', fill: MUT }))),
        h('rect', { x: x0, y: y0, width: dw, height: dh, fill: '#fff', stroke: INK, strokeWidth: 1.5 }),
        // crease (fold) line at position
        h('line', { x1: cx, y1: y0 - 8, x2: cx, y2: y0 + dh + 8, stroke: TEAL, strokeWidth: 1.5, strokeDasharray: '5 4' }),
        h('text', { x: cx, y: y0 - 12, textAnchor: 'middle', fontSize: 10, fontWeight: 600, fill: TEAL }, 'Fold'),
        // left + right panel widths
        seg(x0, cx, leftW), seg(cx, x0 + dw, rightW),
        // total width dimension
        arrow(x0, y0 + dh + 18, x0 + dw, y0 + dh + 18),
        h('text', { x: x0 + dw / 2, y: y0 + dh + 32, textAnchor: 'middle', fontSize: 12, fontWeight: 600, fill: INK }, 'Width ' + Math.round(W) + ' mm'),
        // height dimension
        arrow(x0 - 18, y0, x0 - 18, y0 + dh),
        h('text', { x: x0 - 24, y: midy, textAnchor: 'middle', fontSize: 12, fontWeight: 600, fill: INK, transform: 'rotate(-90 ' + (x0 - 24) + ' ' + midy + ')' }, 'Height ' + Math.round(H) + ' mm')),
      label: 'Open ' + Math.round(W) + ' × ' + Math.round(H) + ' mm · crease at ' + Math.round(creaseAt) + ' mm (' + Math.round(leftW) + ' + ' + Math.round(rightW) + ')',
    };
  }
  // hot-stamping foil picker: one 6-colour swatch row per colour in the chosen option
  // (Front/Back × Colour 1/2), plus a Hot Stamping Block choice — matching Excard.
  foilColourPicker(def, cfg) {
    const COLOURS = [['Gold', '#E6C200'], ['Silver', '#C4C4C4'], ['Green', '#2E7D32'], ['Blue', '#1E88E5'], ['Black', '#1A1A1A'], ['Red', '#C62828']];
    const hs = String(cfg.hot_stamping || ''), pickers = [];
    hs.split('+').forEach(part => { const m = part.match(/(\d)\s*C\s*\((Front|Back)\)/i); if (m) { const n = +m[1], side = /front/i.test(m[2]) ? 'Front' : 'Back'; for (let i = 1; i <= n; i++) pickers.push({ key: 'hs_' + side.toLowerCase() + '_' + i, label: side + ' — Colour ' + i }); } });
    if (!pickers.length) return null;
    const pick = (k, v) => this.setState(st => ({ cfg: Object.assign({}, st.cfg, { [k]: v }) }));
    const swatch = (key, c) => { const on = cfg[key] === c[0]; return h('span', { key: c[0], onClick: e => { e.stopPropagation(); pick(key, c[0]); }, style: { display: 'inline-flex', alignItems: 'center', gap: 7, border: '1px solid ' + (on ? TEAL : HAIR), borderRadius: 999, padding: '5px 13px 5px 6px', cursor: 'pointer', background: on ? '#fdf2f2' : '#fff', fontSize: 12.5, fontWeight: on ? 600 : 500, color: on ? TEAL : INK } }, h('span', { style: { width: 15, height: 15, borderRadius: '50%', background: c[1], border: '1px solid rgba(0,0,0,.2)', flex: 'none' } }), c[0]); };
    const row = (label, children) => h('div', { key: label, style: { border: '1px solid ' + HAIR, borderRadius: 10, padding: 14, background: '#fff', display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' } }, h('div', { style: { fontSize: 13, fontWeight: 600, minWidth: 110 } }, label), h('div', { style: { display: 'flex', gap: 8, flexWrap: 'wrap' } }, children));
    const blockVal = cfg.hs_block || 'None';
    return h('div', { key: def.key, style: { padding: '6px 0 15px', borderTop: '1px solid ' + LINE } },
      h('div', { style: { display: 'flex', flexDirection: 'column', gap: 10 } },
        pickers.map(p => row(p.label, COLOURS.map(c => swatch(p.key, c)))),
        row('Hot Stamping Block', ['None', 'Same Block'].map(b => { const on = blockVal === b; return h('span', { key: b, onClick: e => { e.stopPropagation(); pick('hs_block', b); }, style: { display: 'inline-flex', alignItems: 'center', gap: 7, border: '1px solid ' + (on ? TEAL : HAIR), borderRadius: 999, padding: '6px 14px', cursor: 'pointer', background: on ? '#fdf2f2' : '#fff', fontSize: 12.5, fontWeight: on ? 600 : 500, color: on ? TEAL : INK } }, h('span', { style: { width: 13, height: 13, borderRadius: '50%', border: '2px solid ' + (on ? TEAL : '#bbb'), background: on ? TEAL : '#fff', boxShadow: on ? 'inset 0 0 0 2px #fff' : 'none', flex: 'none' } }), b); }))));
  }
  // physics-based shipment weight (kg) from size × paper gsm × qty × a packaging factor —
  // the engine's per-unit weight is unreliable for sheet goods (a 50g/card fallback), and
  // this matches Excard's stated weight (± their own 10% tolerance). Falls back to the engine.
  pkWeight(qtyOverride) {
    const cfg = this.pkV(), qty = qtyOverride || this.state.qty || 1;
    const sm = String(cfg.size || '').match(/(\d+(?:\.\d+)?)\s*mm\s*[x×]\s*(\d+(?:\.\d+)?)\s*mm/i);
    const gm = String(cfg.paper || cfg.material || '').match(/(\d{2,4})\s*(?:gsm|micron)/i);
    if (sm && gm) { const w = +sm[1], h = +sm[2], g = +gm[1]; if (w && h && g) return w * h / 1e6 * g / 1000 * qty * 1.35; }
    const q = this.pkQuote(qtyOverride);
    return (q && q.ok && q.weight != null) ? q.weight : null;
  }
  // visible option fields for the current product, each with its resolved (conditionally-valid) options
  pkFields() {
    const E = this.pkEngine(), prod = this.pkProduct(); if (!E || !prod) return [];
    // display cfg: like pkV but with UNSELECTED "please select" fields stripped, so fields
    // that depend on them (e.g. Paper Lamination depends on Paper) stay hidden until chosen.
    const cfg = Object.assign({}, this.pkV());
    const ov = this.cfgOv(), ph = ov.placeholder || [], sc = this.state.cfg || {};
    ph.forEach(k => { if (sc[k] == null || sc[k] === '') delete cfg[k]; });
    const gates = ov.optGate || {}, hideWhen = ov.hideWhen || {};
    const hidden = f => { if (this.pkHidden(f.key)) return true; if (hideWhen[f.key]) { try { return !!hideWhen[f.key](cfg); } catch (e) {} } return false; };
    const list = (prod.fields || []).filter(f => f.key && !hidden(f) && this.pkShown(f, cfg)).map(f => {
      let options = [];
      try { options = E.localOptions(prod, f.key, cfg) || []; } catch (e) { options = f.options || []; }
      // conditional validity: when a field's gate fails, offer only its first (safe) option
      if (gates[f.key] && options.length) { try { if (!gates[f.key](cfg, this.state.qty)) options = [options[0]]; } catch (e) {} }
      return { def: f, options };
    });
    // synthetic override fields (e.g. custom-size Height/Width shown when Size = "Other"),
    // inserted right after the engine field they depend on.
    (ov.addFields || []).forEach(af => {
      if (af.showWhen && !this.pkShown(af, cfg)) return;
      const node = { def: af, options: (af.options || null) };
      const depKey = af.after || (af.showWhen && (af.showWhen.field || (af.showWhen.all && af.showWhen.all[0] && af.showWhen.all[0].field)));
      let at = depKey ? list.findIndex(x => x.def.key === depKey) : -1;
      if (at >= 0) { let j = at + 1; while (j < list.length && list[j].def.__added) j++; list.splice(j, 0, Object.assign(node, { def: Object.assign({ __added: true }, af) })); }
      else list.push(Object.assign(node, { def: Object.assign({ __added: true }, af) }));
    });
    return list;
  }
  // option-value map the engine expects. Fields can be listed out of dependency order
  // (e.g. booklet 'ordertype' depends on 'orientation'+'size'), so resolve defaults with a
  // fixpoint loop, and re-validate any stale value that a changed upstream option invalidated.
  pkV() {
    const E = this.pkEngine(), prod = this.pkProduct();
    const cfg = Object.assign({}, this.state.cfg || {});
    if (!E || !prod) return cfg;
    const fields = (prod.fields || []).filter(f => f.key);
    const ovOpts = this.cfgOv().optionsOverride || {};
    for (let pass = 0; pass <= fields.length + 1; pass++) {
      let changed = false;
      for (const f of fields) {
        if (!this.pkShown(f, cfg)) continue;
        let opts = []; try { opts = E.localOptions(prod, f.key, cfg) || []; } catch (e) { opts = f.options || []; }
        // validate against the display option-override list where one exists, so an overridden
        // value (e.g. a fold-card preset size not in the engine's list) isn't reset.
        if (ovOpts[f.key]) { try { const a = typeof ovOpts[f.key] === 'function' ? ovOpts[f.key](cfg, opts) : ovOpts[f.key]; if (a && a.length) opts = a; } catch (e) {} }
        if (!opts.length) continue;
        if (cfg[f.key] == null || opts.indexOf(cfg[f.key]) < 0) { cfg[f.key] = opts[0]; changed = true; }
      }
      if (!changed) break;
    }
    // hidden fields must price as "not applied": set them to a none-like option so the engine's
    // axis lookup is correct (e.g. Lamination = "Not Required" for a paper that has no lamination,
    // instead of a blank that hits the wrong price curve).
    const NONE_RE = /^(not required|none|no required|no|not applicable|no hot stamping|no hole punching|no round corner|no fold(ing)?)$/i;
    for (const f of fields) {
      if (this.pkShown(f, cfg)) continue;
      let opts = []; try { opts = E.localOptions(prod, f.key, cfg) || f.options || []; } catch (e) { opts = f.options || []; }
      const none = opts.find(o => NONE_RE.test(String(Array.isArray(o) ? o[0] : o)));
      if (none != null) cfg[f.key] = Array.isArray(none) ? none[0] : none;
    }
    // enforce per-product conditional validity the crawl didn't bake into localOptions
    // (e.g. Business Card Silkscreen Spot UV only with Matte lamination + certain papers/qty):
    // when a field's gate fails, reset it to its first (safe) option.
    const ov = this.cfgOv();
    if (ov.optGate) for (const k in ov.optGate) {
      try { if (!ov.optGate[k](cfg, this.state.qty)) { const o = E.localOptions(prod, k, cfg) || []; if (o.length) cfg[k] = o[0]; } } catch (e) {}
    }
    return cfg;
  }
  pkQuote(qtyOverride) {
    const E = this.pkEngine(), prod = this.pkProduct(); if (!E || !prod) return null;
    const qty = qtyOverride || this.state.qty || 1;
    const ov = this.cfgOv();
    try {
      const cfg = this.pkV();
      // priceSub: substitute values for the engine call only (e.g. Business Card custom size
      // "Other (Custom Size)" is priced exactly as the standard 54x89 card — verified on Excard).
      let V = cfg;
      if (ov.priceSub) { V = Object.assign({}, cfg); for (const k in ov.priceSub) { const m = ov.priceSub[k]; if (m[V[k]] != null) V[k] = m[V[k]]; } }
      // priceBase: when a product's pricing is driven directly from captured Excard CASH
      // (the engine's own curve is stale / structurally different), priceBase(cfg,qty)
      // returns the Excard cash for the current config in RM and REPLACES the engine base.
      // Computed FIRST so it can price configs the engine refuses to quote (e.g. fold cards,
      // which the crawl engine returns "quote on request" for). Null → fall back to the engine.
      let baseOverride = null;
      if (ov.priceBase) { try { const b = ov.priceBase(cfg, qty); if (b != null && isFinite(b)) baseOverride = b; } catch (e) {} }
      // engine quote (price + weight/note). May throw for configs it won't quote — tolerate that
      // when priceBase covers the price; only its weight/note are then missing.
      let r = null;
      try { r = E.localQuote(prod, V, qty); } catch (e) { if (baseOverride == null) throw e; }
      let base = baseOverride != null ? baseOverride : r.printoka_cash;
      // priceAddon: cash deltas added on top of the base (engine or priceBase), verified
      // against Excard cash (e.g. Silkscreen Spot UV). Each returns a RM delta for cfg+qty.
      let addon = 0;
      if (ov.priceAddon) for (const k in ov.priceAddon) { try { const d = ov.priceAddon[k](cfg, qty); if (d) addon += d; } catch (e) {} }
      const gross = Math.round((base + addon) * 100) / 100;
      const pct = this.tierPct() / 100;
      const net = Math.round(gross * (1 - pct) * 100) / 100;
      const disc = Math.round((gross - net) * 100) / 100;
      return { ok: true, gross, disc, net, unit: net / qty,
        weight: r ? r.weight_kg : this.pkWeight(qty), note: r ? r.note : null, method: r ? r.method : 'excard', finishing: r ? r.finishing_cost : 0 };
    } catch (e) { return { ok: false, quoteOnly: true, message: e.message }; }
  }
  // legacy shim kept for any caller; routes through the real engine when present
  price() {
    const q = this.pkQuote();
    if (q && q.ok) return q;
    const qty = this.state.qty || 1, gross = 38 * Math.pow(qty / 100, 0.62), disc = gross * (this.tierPct() / 100);
    return { gross, disc, net: gross - disc, unit: (gross - disc) / qty, weight: qty * 0.31 / 1000 };
  }
  money(n) { return this.currency() + ' ' + (n * this.fx()).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }

  // ---------- storefront catalogue: display-name overrides + categories ----------
  // The pricing engine keeps its internal ids/names; the site shows these names.
  componentDidMount() {
    if (typeof fetch === 'function')
      fetch('/api/catalogue').then(r => r.json()).then(d => { if (d && d.overrides) this.setState({ catOverrides: d.overrides }); }).catch(() => {});
    // captured Excard live price tables → EXCARD_PRICES (drives priceBase). forceUpdate so any
    // already-rendered configurator re-prices once the table lands.
    if (typeof fetch === 'function')
      fetch('/pricing/excard_bc.json').then(r => r.json()).then(d => { if (d) { EXCARD_PRICES['Business Card'] = d; if (this.state.route === 'product') this.forceUpdate(); } }).catch(() => {});
    // the ~20MB pricing engine loads async (after first paint); re-render prices when it lands,
    // and re-resolve the URL (a product deep-link can't map its slug→id until products exist)
    if (typeof window !== 'undefined' && !window.PricingEngine)
      window.addEventListener('pk-engine-ready', () => { try { if (this._urlPending) this.resolveUrl(); this.forceUpdate(); this.applySEO(); } catch (e) {} }, { once: true });
    // browser back/forward → re-resolve the address bar to the matching in-app route
    if (typeof window !== 'undefined') window.addEventListener('popstate', () => { try { this.resolveUrl(); } catch (e) {} });
    const r = this.opsRoleFor(this.state.route); if (r) this.opsLoad(this.opsActingRole());
    if (this.state.route === 'learn') this.blogLoad();
    if (this.state.route === 'production') this.loadVendors();
    if (this.state.route === 'vendor') this.loadVendorRequests();
    if (this.state.route === 'admin') this.loadAdmin();
    this.resolveUrl();
    this.loadCart();
    this.loadSettings();
    this.authLoad();
    this.applySEO();
    // a11y: keyboard-activate data-go elements (Enter/Space), since they are not native buttons
    if (typeof document !== 'undefined') document.addEventListener('keydown', this.onNavKey);
    this.a11yEnhance();
  }
  componentDidUpdate(prevProps, prevState) {
    const s = this.state;
    if (!prevState || prevState.route !== s.route || prevState.prodId !== s.prodId || prevState.catFilter !== s.catFilter || prevState.seoPage !== s.seoPage || prevState.article !== s.article) this.applySEO();
    this.a11yEnhance();
  }
  componentWillUnmount() { if (typeof document !== 'undefined') document.removeEventListener('keydown', this.onNavKey); }
  // Enter / Space on a focused [data-go] element behaves like a click (native controls keep their own behaviour)
  onNavKey = (e) => {
    // Escape closes any open overlay (dropdown, mega menu, dialog, announcement)
    if (e.key === 'Escape') {
      const st = this.state;
      if (st.ddOpen != null || st.megaOpen || st.dialog != null || st.nu_open || st.annClosed !== (st.settings && st.settings.announcement && st.settings.announcement.text)) {
        const patch = {};
        if (st.ddOpen != null) patch.ddOpen = null;
        if (st.megaOpen) patch.megaOpen = false;
        if (st.dialog != null) patch.dialog = null;
        if (st.nu_open) patch.nu_open = false;
        const annTxt = st.settings && st.settings.announcement && st.settings.announcement.text;
        if (annTxt && st.annClosed !== annTxt) patch.annClosed = annTxt;
        if (Object.keys(patch).length) { this.setState(patch); }
      }
      return;
    }
    if (e.key !== 'Enter' && e.key !== ' ' && e.key !== 'Spacebar') return;
    const t = e.target; if (!t || !t.tagName) return;
    if (/^(INPUT|TEXTAREA|SELECT|BUTTON|A)$/.test(t.tagName)) return;
    const el = t.closest && t.closest('[data-go]'); if (!el) return;
    e.preventDefault();
    this.onNav(e);
  };
  // a11y: give every non-native [data-go] a button role + tab stop so it is reachable and
  // announced. React replaces nodes on re-render, so this re-runs after each update.
  a11yEnhance() {
    if (typeof document === 'undefined') return;
    const root = document.getElementById('root'); if (!root) return;
    root.querySelectorAll('[data-go]').forEach(el => {
      const tag = el.tagName;
      if (tag === 'A' || tag === 'BUTTON' || tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return;
      if (el.getAttribute('tabindex') == null) el.setAttribute('tabindex', '0');
      if (el.getAttribute('role') == null) el.setAttribute('role', 'button');
    });
  }
  // ---------- SEO: dynamic <title>, meta description, robots + JSON-LD per route ----------
  applySEO() {
    if (typeof document === 'undefined') return;
    let d; try { d = this.seoData(); } catch (e) { return; }
    if (!d) return;
    document.title = d.title;
    const setMeta = (name, content) => { let m = document.head.querySelector('meta[name="' + name + '"]'); if (!m) { m = document.createElement('meta'); m.setAttribute('name', name); document.head.appendChild(m); } m.setAttribute('content', content || ''); };
    // og:/article: meta use the property attribute, not name
    const setProp = (prop, content) => { let m = document.head.querySelector('meta[property="' + prop + '"]'); if (!m) { m = document.createElement('meta'); m.setAttribute('property', prop); document.head.appendChild(m); } m.setAttribute('content', content || ''); };
    setMeta('description', d.description || '');
    setMeta('robots', d.robots || 'index,follow');
    // canonical URL — strip query/hash so each route has one canonical address
    const origin = (typeof location !== 'undefined' ? location.origin : 'https://printoka.com');
    const canonical = origin + (d.canonical || (typeof location !== 'undefined' ? location.pathname : '/'));
    let can = document.head.querySelector('link[rel="canonical"]'); if (!can) { can = document.createElement('link'); can.setAttribute('rel', 'canonical'); document.head.appendChild(can); } can.setAttribute('href', canonical);
    // Open Graph + Twitter Card — social share previews
    const ogImg = d.image ? (/^https?:/.test(d.image) ? d.image : origin + d.image) : (origin + '/assets/products/business-card.jpg');
    setProp('og:type', d.ogType || 'website');
    setProp('og:site_name', 'Printoka');
    setProp('og:title', d.title || 'Printoka');
    setProp('og:description', d.description || '');
    setProp('og:url', canonical);
    setProp('og:image', ogImg);
    setMeta('twitter:card', 'summary_large_image');
    setMeta('twitter:title', d.title || 'Printoka');
    setMeta('twitter:description', d.description || '');
    setMeta('twitter:image', ogImg);
    let sc = document.getElementById('pk-jsonld'); if (!sc) { sc = document.createElement('script'); sc.id = 'pk-jsonld'; sc.type = 'application/ld+json'; document.head.appendChild(sc); }
    sc.textContent = d.jsonld ? JSON.stringify(d.jsonld) : '';
  }
  productFaqs(prod, name) {
    const fields = this.pkFields();
    const sizeF = fields.find(f => /size/i.test(f.def.key) && f.options && f.options.length);
    const sizes = sizeF ? sizeF.options.filter(o => !/other|custom/i.test(String(o))).slice(0, 6).join(', ') : '';
    // real material/finish options for THIS product, so the FAQ differs per product
    const matF = fields.find(f => /paper|material|stock/i.test(f.def.key) && f.options && f.options.length);
    const mats = matF ? matF.options.filter(o => !/other|custom|not required|^no/i.test(String(o))).slice(0, 5).join(', ') : '';
    const finF = fields.filter(f => /laminat|spot|stamp|emboss|foil|corner|coat|varnish/i.test(f.def.key) && f.options && f.options.length);
    const fins = finF.length ? finF.map(f => f.def.label.toLowerCase()).slice(0, 4).join(', ') : '';
    const qobj = prod ? this.pkQtyObj(prod.id) : null;
    const faqs = [];
    faqs.push(['What size options are available for ' + name + '?', sizes ? ('Available sizes include ' + sizes + '. You can also enter a custom size where supported.') : 'Choose from the size options in the configurator, or enter a custom size where supported.']);
    if (mats || fins) faqs.push(['What materials and finishes can I choose for ' + name + '?', (mats ? ('Materials include ' + mats + '. ') : '') + (fins ? ('Finishes include ' + fins + '.') : '')]);
    if (qobj) faqs.push(['What is the minimum order for ' + name + '?', 'The minimum order is ' + qobj.moq.toLocaleString() + ' pcs. Larger runs lower the price per piece.']);
    faqs.push(['How long does ' + name + ' printing take?', 'Standard turnaround is 3 working days after your artwork is approved by prepress.']);
    faqs.push(['Can I get ' + name + ' delivered or pick it up?', 'Both. Choose nationwide courier delivery, or free self-pickup at a Klang Valley outlet.']);
    return faqs.slice(0, 5);
  }
  seoData() {
    const route = this.state.route, C = 'Malaysia, Singapore & Brunei';
    const ctx = 'https://schema.org', origin = (typeof location !== 'undefined' ? location.origin : 'https://printoka.com');
    const org = { '@context': ctx, '@type': 'Organization', name: 'Printoka', url: origin, logo: origin + '/assets/icons/logomark.svg' };
    const IDX = 'index,follow', NOIDX = 'noindex,follow', money0 = n => this.money(n);
    if (route === 'product') {
      const prod = this.pkProduct(), name = prod ? this.catName(prod.id) : 'Business Card';
      const from = prod ? this.catFromPrice(prod.id) : null, cat = prod ? this.catCategoryLabel(this.catCategoryOf(prod.id)) : 'Products';
      const seo = this.productSeo(prod, name), faqs = this.productFaqs(prod, name);
      const jsonld = { '@context': ctx, '@graph': [
        Object.assign({ '@type': 'Product', name: name + ' Printing', category: cat, description: seo.paras[0].slice(0, 320), brand: { '@type': 'Brand', name: 'Printoka' } },
          from != null ? { offers: { '@type': 'Offer', priceCurrency: this.currency(), price: (from * this.fx()).toFixed(2), availability: 'https://schema.org/InStock', url: origin } } : {}),
        { '@type': 'BreadcrumbList', itemListElement: [{ '@type': 'ListItem', position: 1, name: 'Home', item: origin + '/' }, { '@type': 'ListItem', position: 2, name: cat }, { '@type': 'ListItem', position: 3, name: name }] },
        { '@type': 'FAQPage', mainEntity: faqs.map(f => ({ '@type': 'Question', name: f[0], acceptedAnswer: { '@type': 'Answer', text: f[1] } })) },
      ] };
      // configurator canonicalises to the static SEO page so the /configure/ route never competes
      return { title: name + ' Printing | ' + (from != null && from >= 0.001 ? 'From ' + money0(from) + '/pc | ' : '') + 'Printoka', description: 'Order ' + name + ' printing online in ' + C + ' — configure your options, get an instant price, and print with a free artwork check. Member discounts up to 15%.', robots: IDX, canonical: (prod ? this.productPath(prod.id) : null), jsonld };
    }
    if (route === 'category') {
      const active = this.state.catFilter || 'all', isAll = active === 'all';
      const label = isAll ? 'Online Printing' : this.catCategoryLabel(active);
      // "Online Printing" already contains "Printing", so don't append it again (avoids "… Printing Printing")
      const collName = isAll ? 'Online Printing' : label + ' Printing';
      const titleLead = isAll ? 'Online Printing' : label + ' Printing Online';
      const descLead = isAll ? 'Online printing' : 'Custom ' + label.toLowerCase() + ' printing';
      const items = this.catProducts(active), froms = items.map(p => this.catFromPrice(p.id)).filter(x => x != null), minFrom = froms.length ? Math.min.apply(null, froms) : null;
      const jsonld = { '@context': ctx, '@graph': [
        { '@type': 'CollectionPage', name: collName },
        { '@type': 'ItemList', itemListElement: items.slice(0, 20).map((p, i) => ({ '@type': 'ListItem', position: i + 1, name: p.name })) },
        { '@type': 'BreadcrumbList', itemListElement: [{ '@type': 'ListItem', position: 1, name: 'Home', item: origin + '/' }, { '@type': 'ListItem', position: 2, name: label }] },
      ] };
      const showFrom = minFrom != null && minFrom >= 0.01;
      return { title: titleLead + ' | ' + (showFrom ? 'From ' + money0(minFrom) + '/pc | ' : '') + 'Printoka', description: descLead + ' in ' + C + '. Configure size, material and finish, see the price instantly, and order online' + (showFrom ? ', from ' + money0(minFrom) + ' per piece.' : '.'), robots: IDX, jsonld };
    }
    if (route === 'home') return { title: 'Printoka — Online Printing in Malaysia, Singapore & Brunei | 100+ Products, Instant Pricing', description: 'Order business cards, flyers, stickers, packaging and more online. Instant pricing, member discounts up to 15%, and nationwide delivery across Malaysia, Singapore and Brunei.', robots: IDX, jsonld: { '@context': ctx, '@graph': [org, { '@type': 'WebSite', name: 'Printoka', url: origin, potentialAction: { '@type': 'SearchAction', target: origin + '/search?q={search_term_string}', 'query-input': 'required name=search_term_string' } }] } };
    if (route === 'packaging') return { title: 'Custom Packaging Boxes Printing | Design Your Own | Printoka', description: 'Design custom packaging boxes, sleeves and mailers online in ' + C + '. Choose your size, material and finishing, with a free die-line to design on.', robots: IDX, jsonld: org };
    if (route === 'membership') return { title: 'Printoka Membership — Save Up to 15% on Every Order', description: 'Earn Bronze, Silver, Gold or Platinum status as you print with Printoka. Automatic tier discounts, priority queue placement, and a dedicated account manager at Platinum.', robots: IDX, jsonld: { '@context': ctx, '@type': 'FAQPage', mainEntity: [{ '@type': 'Question', name: 'How do Printoka membership tiers work?', acceptedAnswer: { '@type': 'Answer', text: 'Your tier is set by trailing-12-month spend and applies automatically at checkout: Bronze 5%, Silver 8%, Gold 10% and Platinum 15%.' } }] } };
    if (route === 'about' || route === 'corporate') return { title: 'About Printoka | Malaysia’s Trusted Printing Marketplace', description: 'Printoka connects partner printers across ' + C + ' with instant online pricing for 100+ products.', robots: IDX, jsonld: org };
    if (route === 'support') return { title: 'Support & FAQ | Printoka', description: 'Artwork prep tips, FAQs and support for every Printoka product — free to read before you upload.', robots: IDX, jsonld: org };
    if (route === 'learn') return { title: 'Printing Guides & Artwork Tips | Printoka Learning Hub', description: 'Bleed and margin guides, paper stock explainers, and artwork prep tips for every Printoka product — free to read before you upload.', robots: IDX, jsonld: org };
    if (route === 'article') return { title: (this.state.article && this.state.article.title ? this.state.article.title : 'Article') + ' | Printoka Learning Hub', description: (this.state.article && this.state.article.excerpt) || 'A printing guide from the Printoka Learning Hub.', robots: IDX, jsonld: org };
    if (route === 'downloads') return { title: 'Free Print Templates & Downloads | Printoka', description: 'Download print-ready templates, die-lines and artwork guides for Printoka products.', robots: IDX, jsonld: org };
    if (route === 'contact') return { title: 'Contact Printoka | WhatsApp, Email & Support', description: 'Get in touch with Printoka support via WhatsApp, live chat or the contact form. We reply within 1 business day.', robots: IDX, jsonld: org };
    if (route === 'partners') return { title: 'Partner With Printoka | Become a Printer', description: 'Join Printoka’s partner printer network and receive jobs from customers across ' + C + '.', robots: IDX, jsonld: org };
    if (route === 'terms') return { title: 'Terms, Privacy & Policies | Printoka', description: 'Printoka terms of service, privacy and PDPA policy, and disclosures.', robots: IDX, jsonld: org };
    // programmatic city landing pages: index only major cities; noindex the long-tail so the
    // near-duplicate small-town variants are not treated as doorway pages (content-strategy §4).
    if (route === 'seo') {
      const p = this.state.seoPage;
      if (!p || typeof p !== 'object') return { title: 'Online Printing | Printoka', description: 'Order printing online across ' + C + '.', robots: NOIDX, jsonld: org };
      const slug = p.slug || '';
      const city = slug.replace(/^.*?-printing-/, '').replace(/^in-/, '');
      const KEEP = { 'kuala-lumpur': 1, 'petaling-jaya': 1, 'shah-alam': 1, 'klang': 1, 'klang-valley': 1, 'penang': 1, 'pulau-pinang': 1, 'georgetown': 1, 'george-town': 1, 'johor-bahru': 1, 'iskandar-puteri': 1, 'ipoh': 1, 'kuching': 1, 'miri': 1, 'kota-kinabalu': 1, 'seremban': 1, 'melaka': 1, 'malaysia': 1, 'singapore': 1, 'brunei': 1, 'bandar-seri-begawan': 1, 'australia': 1, 'new-zealand': 1, 'nz': 1, 'solutions': 1 };
      const keep = !!KEEP[city];
      const place = city.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      const desc = (p.title || 'Printing') + ' online with instant pricing and delivery to ' + place + '. Configure your job, see the exact price, and order from Printoka.';
      return { title: (p.title || 'Online Printing') + ' | Printoka', description: desc.slice(0, 300), robots: keep ? IDX : NOIDX, jsonld: org };
    }
    const T = { cart: 'Your Cart', checkout: 'Checkout', confirm: 'Order Confirmed', auth: 'Log In / Sign Up', dash: 'My Account', invoices: 'Invoices', track: 'Track Order', artwork: 'Upload & Check Artwork', search: 'Search Results' };
    if (T[route]) return { title: T[route] + ' | Printoka', description: '', robots: NOIDX, jsonld: null };
    return { title: 'Printoka — Online Printing', description: 'Order printing online across ' + C + '.', robots: IDX, jsonld: org };
  }

  // ---------- cart + checkout + orders (storefront commerce loop) ----------
  loadCart() {
    try { const c = JSON.parse(localStorage.getItem('pk_cart') || '[]'); if (Array.isArray(c) && c.length) this.setState({ cart: c }); } catch (e) {}
  }
  saveCart(cart) { try { localStorage.setItem('pk_cart', JSON.stringify(cart || [])); } catch (e) {} }
  // Full human-readable spec for the current configuration. Walks the *rendered* fields
  // (pkFields → includes the synthetic override fields: custom size, fold sizes, creasing)
  // and appends the Hot Stamping foil colours, so a placed order carries every choice —
  // not only the priced axes. Returns { short, lines:[[label,value],…] }.
  pkOrderSpec() {
    const ov = this.cfgOv(), cfg = this.pkV();
    let fields = []; try { fields = this.pkFields(); } catch (e) { fields = []; }
    const NONE_RE = /^(no|not required|no required|none|not applicable|no hot stamping|no hole punching|no round corner|no fold(ing)?)$/i;
    const dispLabel = def => (ov.label && ov.label[def.key]) || def.label || def.key;
    const dispVal = (def, val) => { const m = (ov.optLabel && ov.optLabel[def.key]) || {}; return m[val] || val; };
    // combine the custom H/W input pairs into one dimension line instead of two rows
    const PAIRS = { custom_w: ['custom_h', 'Custom Size'], fold_w_thin: ['fold_h_thin', 'Open Size'], fold_w_fat: ['fold_h_fat', 'Open Size'] };
    const SKIP_H = { custom_h: 1, fold_h_thin: 1, fold_h_fat: 1 };
    const lines = [], seen = {};
    for (const f of fields) {
      const def = f.def, k = def && def.key; if (!k || seen[k]) continue; seen[k] = 1;
      if (def.widget === 'foilColours') continue;      // colours handled below
      if (SKIP_H[k]) continue;                          // folded into its width partner
      if (PAIRS[k]) { const [hk, tag] = PAIRS[k]; if (cfg[hk] && cfg[k]) lines.push([tag, cfg[hk] + 'mm × ' + cfg[k] + 'mm']); continue; }
      let val = cfg[k]; if (val == null || val === '') continue;
      if (NONE_RE.test(String(val))) continue;   // drop "No/Not Required" selections (geometry fields are never none-like)
      if (/^\d+(\.\d+)?$/.test(String(val)) && /\(mm\)/i.test(def.label || '')) val = val + 'mm';
      lines.push([dispLabel(def), String(dispVal(def, val))]);
    }
    // Hot Stamping foil colours (same picker logic as foilColourPicker) + block
    const hs = String(cfg.hot_stamping || '');
    if (hs && !/^no /i.test(hs)) {
      hs.split('+').forEach(part => { const m = part.match(/(\d)\s*C\s*\((Front|Back)\)/i); if (m) { const n = +m[1], side = /front/i.test(m[2]) ? 'Front' : 'Back'; for (let i = 1; i <= n; i++) { const v = cfg['hs_' + side.toLowerCase() + '_' + i]; if (v) lines.push(['Foil — ' + side + ' Colour ' + i, v]); } } });
      if (cfg.hs_block && cfg.hs_block !== 'None') lines.push(['Hot Stamping Block', cfg.hs_block]);
    }
    // short line for the cart row: the meaningful choices, geometry/colour detail trimmed
    const short = lines.filter(l => !/^(creasing|crease|foil |hot stamping block|custom size|open size)/i.test(l[0])).slice(0, 5).map(l => l[1]).join(' · ');
    return { short: short || lines.slice(0, 5).map(l => l[1]).join(' · '), lines };
  }
  addToCart() {
    if (!this.pkReady()) { if (typeof window !== 'undefined') window.scrollTo(0, 0); return this.go('product'); }
    const prod = this.pkProduct(), q = this.pkQuote(); if (!prod || !q || !q.ok) return;
    const { short, lines } = this.pkOrderSpec();
    const item = { productId: prod.id, name: this.catName(prod.id), spec: short, specLines: lines, qty: this.state.qty || 1, unitPrice: q.gross / (this.state.qty || 1), lineTotal: q.gross };
    const cart = (this.state.cart || []).concat([item]);
    this.setState({ cart }); this.saveCart(cart); this.go('cart');
  }
  // render a cart/order item's spec: labelled lines when specLines is present (new fields
  // — fold sizes, creasing, custom size, foil colours — included), else the legacy string.
  specView(it) {
    if (it && it.specLines && it.specLines.length)
      return it.specLines.map((l, k) => h('div', { key: k }, h('span', { style: { color: FAINT } }, l[0] + ': '), l[1]));
    return ((it && it.spec) || '—').split(' · ').map((s, k) => h('div', { key: k }, s));
  }
  removeFromCart(i) { const cart = (this.state.cart || []).filter((_, idx) => idx !== i); this.setState({ cart }); this.saveCart(cart); }
  rmCart(i) { return this.removeFromCart(i); }
  dupCart(i) { const cart = (this.state.cart || []); const it = cart[i]; if (!it) return; const next = cart.slice(0, i + 1).concat([Object.assign({}, it)], cart.slice(i + 1)); this.setState({ cart: next }); this.saveCart(next); }
  applyCoupon() {
    const code = (this.state.cartCoupon || '').trim();
    if (!code) return this.setState({ couponMsg: 'Enter a discount or membership code.', couponOk: false });
    // codes are validated server-side at checkout; here we acknowledge and carry it forward
    this.setState({ couponMsg: 'Code “' + code + '” will be validated at checkout.', couponOk: true });
  }
  downloadQuotation() {
    // a cart-level quotation mirrors the price the configurator/checkout/invoice all read
    if (typeof window !== 'undefined') window.print();
  }
  cartTotals() {
    const cart = this.state.cart || [];
    const subtotal = cart.reduce((s, it) => s + (it.lineTotal || 0), 0);
    const memberDiscount = subtotal * (this.tierPct() / 100);
    const afterDisc = subtotal - memberDiscount;
    const taxRate = ({ MY: 0.08, SG: 0.09, BN: 0 })[this.cc()] || 0;
    const tax = afterDisc * taxRate;
    const shipping = cart.length ? 12 : 0;
    return { subtotal, memberDiscount, tax, shipping, total: afterDisc + tax + shipping, count: cart.length };
  }
  setField(k, v) { this.setState({ [k]: v }); }
  placeOrder() {
    const cart = this.state.cart || []; if (!cart.length) return;
    const t = this.cartTotals();
    const u = this.state.user || {};
    const picked = (this.state.addresses || []).find(a => a.id === this.state.coAddrId);
    const addrText = picked ? [picked.line1, picked.line2, picked.postcode + ' ' + picked.city, picked.state, picked.country].filter(Boolean).join(', ') : (this.state.coAddress || '');
    const creditAvail = (this.state.credit && this.state.credit.balance) || 0;
    const creditApplied = this.state.coCredit ? Math.min(creditAvail, t.total) : 0;
    const body = {
      customer: { name: this.state.coName || u.name || 'Guest customer', email: this.state.coEmail || u.email || '', phone: this.state.coPhone || u.phone || '', company: this.state.coCompany || u.company || '' },
      fulfillment: { method: this.state.coFulfil || 'delivery', address: addrText, addressId: this.state.coAddrId || null, outlet: this.state.coOutlet || '' },
      payment: { method: this.state.coPay || 'card_test' },
      items: cart.map(it => ({ productId: it.productId, product: it.name, spec: it.spec, specLines: it.specLines || null, qty: it.qty, unitPrice: it.unitPrice, lineTotal: it.lineTotal })),
      subtotal: t.subtotal, memberDiscount: t.memberDiscount, tax: t.tax, shipping: t.shipping, total: t.total, creditApplied, tier: this.tier(),
    };
    this.setState({ placing: true });
    fetch('/api/orders', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify(body) })
      .then(r => r.json()).then(d => {
        if (d && d.order) { this.setState({ order: d.order, placing: false, cart: [] }); this.saveCart([]); this.go('confirm'); }
        else this.setState({ placing: false });
      }).catch(() => this.setState({ placing: false }));
  }
  trackLookup(oid) {
    if (!oid) return;
    this.setState({ trackOrder: null, trackErr: false });
    fetch('/api/orders/' + oid.trim(), { headers: this.authHeaders() }).then(r => r.json()).then(d => this.setState({ trackOrder: d.order || false })).catch(() => this.setState({ trackOrder: false }));
  }

  // ---------- authentication (real accounts + sessions) ----------
  authToken() { try { return localStorage.getItem('pk_token') || ''; } catch (e) { return ''; } }
  authHeaders() { const t = this.authToken(); return t ? { 'x-token': t } : {}; }
  authLoad() {
    if (typeof fetch !== 'function' || !this.authToken()) return;
    fetch('/api/auth/me', { headers: this.authHeaders() }).then(r => r.ok ? r.json() : null).then(d => {
      if (!d || !d.customer) return;
      const c = d.customer; this.setState({ user: c }); this.loadAccount(); this.loadNotifications();
      // on a hard refresh the route is still 'home'; load the data the user's real home needs
      const home = this.homeFor(c);
      if (['production', 'prepress', 'logistics', 'admin', 'outlet', 'dash'].indexOf(home) >= 0) this.loadQuotes();
      if (home === 'dash') { this.loadUserOrders(); this.loadCustomInvoices(); }
      if (home === 'outlet') this.loadStaffOrders();
      if (home === 'admin') this.loadAdmin();
      if (home === 'vendor') this.loadVendorRequests();
      if (home === 'production') this.loadVendors();
      const r2 = this.opsRoleFor(home);
      if (r2 && typeof fetch === 'function') fetch('/api/jobs?role=' + this.opsRoleForUser(c), { headers: this.authHeaders() }).then(x => x.json()).then(j => this.setState({ ops: { jobs: j.jobs || [], role: this.opsRoleForUser(c), loaded: true } })).catch(() => {});
    }).catch(() => {});
  }
  // ---------- notifications ----------
  loadNotifications() { if (typeof fetch !== 'function' || !this.authToken()) return; fetch('/api/notifications', { headers: this.authHeaders() }).then(r => r.ok ? r.json() : null).then(d => { if (d) this.setState({ notifs: d.notifications || [] }); }).catch(() => {}); }
  loadStaffOrders() { if (typeof fetch !== 'function' || !this.authToken()) return; fetch('/api/orders', { headers: this.authHeaders() }).then(r => r.ok ? r.json() : null).then(d => { if (d) this.setState({ staffOrders: d.orders || [] }); }).catch(() => {}); }
  loadSettings() { if (typeof fetch !== 'function') return; fetch('/api/settings').then(r => r.json()).then(d => { if (d && d.settings) this.setState({ settings: d.settings }); }).catch(() => {}); }
  loadFaq() { if (typeof fetch !== 'function' || this.state.faq) return; fetch('/api/content/faq').then(r => r.json()).then(d => this.setState({ faq: d.faq || [] })).catch(() => {}); }
  loadDownloads() { if (typeof fetch !== 'function' || this.state.downloads) return; fetch('/api/content/downloads').then(r => r.json()).then(d => this.setState({ downloads: d.downloads || [] })).catch(() => {}); }
  loadMedia() { if (typeof fetch !== 'function' || this.state.media) return; fetch('/api/content/media').then(r => r.json()).then(d => this.setState({ media: d.media || [] })).catch(() => {}); }
  saveSettings(patch, tag) {
    this.setState({ setBusy: tag || true });
    fetch('/api/settings', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify(patch) })
      .then(r => r.json()).then(d => this.setState({ settings: d.settings || this.state.settings, setBusy: false, setMsg: 'Saved.' })).catch(() => this.setState({ setBusy: false, setMsg: 'Network error.' }));
  }
  // reusable admin settings form for a settings sub-object (theme/store/marketing/whatsapp)
  settingsForm(group, fields, desc) {
    const cur = (this.state.settings && this.state.settings[group]) || {};
    const val = k => { const s = this.state['sf_' + group + '_' + k]; return s != null ? s : (cur[k] != null ? cur[k] : ''); };
    const inp = { font: '400 13.5px Montserrat,sans-serif', padding: '10px 12px', border: '1px solid ' + HAIR, borderRadius: 8, width: '100%', background: '#fff' };
    const save = () => { const patch = {}; fields.forEach(f => { patch[f[0]] = val(f[0]); }); this.saveSettings({ [group]: patch }, group); };
    return [
      h('p', { key: 'd', style: { fontSize: 13.5, color: MUT, lineHeight: 1.7, margin: '0 0 14px', maxWidth: '82ch' } }, desc),
      h('div', { key: 'f', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 14, maxWidth: 760 } },
        fields.map(f => h('div', { key: f[0], style: f[2] === 'textarea' ? { gridColumn: '1 / -1' } : {} },
          h('div', { style: { fontSize: 12.5, fontWeight: 600, marginBottom: 6 } }, f[1]),
          f[2] === 'textarea'
            ? h('textarea', { value: val(f[0]), onChange: e => this.setField('sf_' + group + '_' + f[0], e.target.value), style: Object.assign({}, inp, { minHeight: 72, resize: 'vertical', fontFamily: 'inherit' }) })
            : h('input', { type: f[2] === 'number' ? 'number' : 'text', value: val(f[0]), onChange: e => this.setField('sf_' + group + '_' + f[0], e.target.value), style: inp })))),
      h('div', { key: 's', style: { marginTop: 14, display: 'flex', gap: 12, alignItems: 'center' } },
        h('span', { onClick: save, style: { background: TEAL, color: '#fff', fontWeight: 600, fontSize: 14, padding: '11px 24px', borderRadius: 8, cursor: this.state.setBusy === group ? 'wait' : 'pointer' } }, this.state.setBusy === group ? 'Saving…' : 'Save changes'),
        (this.state.setMsg && this.state.setBusy !== group) ? h('span', { style: { fontSize: 12.5, color: '#3d8b40' } }, this.state.setMsg) : null),
    ];
  }
  markNotif(nid) { fetch('/api/notifications/' + nid + '/read', { method: 'POST', headers: this.authHeaders() }).then(r => r.json()).then(d => this.setState({ notifs: d.notifications || [] })).catch(() => {}); }
  notifPanel() {
    const list = this.state.notifs || [];
    const unread = list.filter(n => !n.read);
    if (!list.length) return null;
    const ICON = { order_placed: '📦', quote_request: '📝', quote_issued: '💬', quote_reviewed: '👀', quote_converted: '✅', quote_amend: '✏️', quote_declined: '🚫' };
    return h('div', { key: 'notif', style: { border: '1px solid ' + HAIR, borderRadius: 12, background: '#fff', overflow: 'hidden', marginBottom: 4 } },
      h('div', { style: { display: 'flex', alignItems: 'center', gap: 8, padding: '11px 15px', borderBottom: list.length ? '1px solid ' + LINE : 'none', background: ALT } },
        h('span', { style: { fontSize: 13, fontWeight: 700 } }, 'Notifications'),
        unread.length ? h('span', { style: { background: TEAL, color: '#fff', fontSize: 11, fontWeight: 700, borderRadius: 999, padding: '1px 8px' } }, unread.length + ' new') : h('span', { style: { fontSize: 12, color: FAINT } }, 'all caught up'),
        unread.length ? h('span', { onClick: () => this.markNotif('all'), style: { marginLeft: 'auto', fontSize: 12, fontWeight: 600, color: TEAL, cursor: 'pointer' } }, 'Mark all read') : null),
      list.slice(0, 6).map((n, i) => {
        const isCust = this.userType() === 'customer';
        const canAct = (isCust && n.quoteId) || (!isCust && n.orderId);
        const act = () => {
          if (!n.read) this.markNotif(n.id);
          if (isCust) { if (n.quoteId) { this.quoteView(n.quoteId); this.openDoc(n.quoteId, 'quote'); } }
          else if (n.orderId) this.openOrder(n.orderId);
        };
        return h('div', { key: n.id, onClick: act, style: { display: 'flex', gap: 10, padding: '11px 15px', borderTop: i ? '1px solid ' + LINE : 'none', background: n.read ? '#fff' : '#fdf7f7', cursor: canAct ? 'pointer' : 'default' } },
          h('span', { style: { fontSize: 16, flex: 'none' } }, ICON[n.kind] || '🔔'),
          h('div', { style: { minWidth: 0, flex: 1 } },
            h('div', { style: { fontSize: 13, fontWeight: n.read ? 500 : 600 } }, n.title),
            h('div', { style: { fontSize: 12, color: MUT, lineHeight: 1.55 } }, n.body),
            h('div', { style: { display: 'flex', gap: 10, alignItems: 'center', marginTop: 4 } },
              (n.cta && canAct) ? h('span', { style: { fontSize: 12, fontWeight: 600, color: TEAL } }, n.cta) : null,
              h('span', { style: { fontSize: 11, color: FAINT } }, this.timeAgo(n.ts)))),
          !n.read ? h('span', { style: { flex: 'none', height: 8, width: 8, borderRadius: '50%', background: TEAL, marginTop: 6 } }) : null);
      }));
  }
  // ---------- walk-in quote (outlet) ----------
  submitWalkinQuote() {
    const s = this.state;
    const body = { walkin: true, customer: { name: s.wk_name, email: s.wk_email, phone: s.wk_phone }, product: s.wk_product, qty: s.wk_qty, size: s.wk_size, material: s.wk_material, finishing: s.wk_finishing, remarks: s.wk_remarks };
    if (!body.customer.name) { this.setState({ wk_err: 'Enter the customer name.' }); return; }
    if (!body.product) { this.setState({ wk_err: 'Enter what they want printed.' }); return; }
    this.setState({ wk_busy: true, wk_err: null });
    fetch('/api/quotes', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify(body) })
      .then(r => r.json()).then(d => { if (d.error) { this.setState({ wk_busy: false, wk_err: d.error }); return; } this.setState({ wk_busy: false, wk_done: d, wk_name: '', wk_email: '', wk_phone: '', wk_product: '', wk_qty: '', wk_size: '', wk_material: '', wk_finishing: '', wk_remarks: '' }); this.loadQuotes(); this.loadNotifications(); }).catch(() => this.setState({ wk_busy: false, wk_err: 'Network error.' }));
  }
  quoteView(qid) { fetch('/api/quotes/' + qid + '/view', { method: 'POST', headers: this.authHeaders() }).then(r => r.json()).then(() => { this.loadQuotes(); this.loadNotifications(); }).catch(() => {}); }
  quoteDecision(qid, decision, remark) {
    fetch('/api/quotes/' + qid + '/decision', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify({ decision, remark }) })
      .then(r => r.json()).then(() => { this.loadQuotes(); this.loadNotifications(); this.setState({ ['dec_' + qid]: null }); }).catch(() => {});
  }
  // ---------- outlet: create new user ----------
  submitNewUser() {
    const s = this.state;
    const body = { firstName: s.nu_first, lastName: s.nu_last, company: s.nu_company, address: s.nu_addr, city: s.nu_city, country: s.nu_country, phone: s.nu_phone, email: s.nu_email, promo: !!s.nu_promo };
    if (!body.firstName || !body.lastName) { this.setState({ nu_err: 'First and last name are required.' }); return; }
    if (!body.email) { this.setState({ nu_err: 'An email address is required.' }); return; }
    this.setState({ nu_busy: true, nu_err: null });
    fetch('/api/customers', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify(body) })
      .then(r => r.json()).then(d => { if (d.error) { this.setState({ nu_busy: false, nu_err: d.error }); return; } this.setState({ nu_busy: false, nu_done: d }); })
      .catch(() => this.setState({ nu_busy: false, nu_err: 'Network error.' }));
  }
  // Announcement popup (admin-set): shows once per announcement, closable, never permanent.
  announcementPopup() {
    const a = (this.state.settings && this.state.settings.announcement) || null;
    if (!a || a.hidden || !a.text) return null;
    const t = this.userType();
    if (t !== 'guest' && t !== 'customer') return null; // storefront visitors only
    let dismissed = ''; try { dismissed = localStorage.getItem('pk_ann') || ''; } catch (e) {}
    if (this.state.annClosed === a.text || dismissed === a.text) return null;
    const close = () => { try { localStorage.setItem('pk_ann', a.text); } catch (e) {} this.setState({ annClosed: a.text }); };
    const goCta = () => { close(); this.go(a.link || 'membership'); };
    return h('div', { key: 'annpop', onClick: close, style: { position: 'fixed', inset: 0, zIndex: 97, background: 'rgba(20,20,25,.4)', display: 'grid', placeItems: 'center', padding: 20 } },
      h('div', { onClick: e => e.stopPropagation(), role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Announcement', style: { position: 'relative', maxWidth: 460, width: '100%', borderRadius: 16, overflow: 'hidden', boxShadow: '0 24px 60px rgba(33,33,33,.35)', background: 'linear-gradient(135deg,#FF9A2E,#F02B29)', color: '#fff' } },
        h('span', { onClick: close, role: 'button', tabIndex: 0, 'aria-label': 'Close announcement', onKeyDown: e => { if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') { e.preventDefault(); close(); } }, style: { position: 'absolute', top: 12, right: 14, fontSize: 22, lineHeight: 1, cursor: 'pointer', color: 'rgba(255,255,255,.9)' } }, '×'),
        h('div', { style: { padding: '30px 28px 26px', textAlign: 'center' } },
          h('img', { src: window.__asset('assets/icons/logomark.svg'), alt: '', style: { height: 40, width: 'auto', filter: 'brightness(0) invert(1)', marginBottom: 14 } }),
          h('div', { style: { fontSize: 12, fontWeight: 700, letterSpacing: '.12em', textTransform: 'uppercase', opacity: .85, marginBottom: 10 } }, 'Announcement'),
          h('div', { style: { fontSize: 17, fontWeight: 600, lineHeight: 1.5, marginBottom: 20 } }, a.text),
          h('span', { onClick: goCta, style: { display: 'inline-block', background: '#fff', color: '#E52220', fontWeight: 700, fontSize: 14.5, padding: '11px 26px', borderRadius: 999, cursor: 'pointer' } }, (a.cta || 'Find out more') + ' →'),
          h('div', { onClick: close, style: { marginTop: 14, fontSize: 12.5, opacity: .85, cursor: 'pointer' } }, 'No thanks, maybe later'))));
  }
  newUserModal() {
    if (!this.state.nu_open) return null;
    const close = () => this.setState({ nu_open: false, nu_done: null, nu_err: null, nu_first: '', nu_last: '', nu_company: '', nu_addr: '', nu_city: '', nu_country: '', nu_phone: '', nu_email: '', nu_promo: false });
    const done = this.state.nu_done;
    const inp = { font: '400 14px Montserrat,sans-serif', padding: '10px 12px', border: '1px solid ' + HAIR, borderRadius: 8, width: '100%', background: '#fff' };
    const lbl = (t, req) => h('div', { style: { fontSize: 13, fontWeight: 600, marginBottom: 6 } }, t, req ? h('span', { style: { color: '#E52220' } }, ' *') : null);
    const field = (label, key, req, ph) => h('div', null, lbl(label, req), h('input', { placeholder: ph || '', value: this.state[key] || '', onChange: e => this.setField(key, e.target.value), style: inp }));
    return h('div', { key: 'nu', onClick: close, style: { position: 'fixed', inset: 0, zIndex: 96, background: 'rgba(20,25,30,.45)', display: 'grid', placeItems: 'start center', padding: 20, overflow: 'auto' } },
      h('div', { onClick: e => e.stopPropagation(), style: { background: '#fff', borderRadius: 14, maxWidth: 620, width: '100%', margin: '24px 0', boxShadow: '0 24px 60px rgba(33,33,33,.3)', overflow: 'hidden' } },
        h('div', { style: { height: 4, background: '#E52220' } }),
        h('div', { style: { padding: '20px 26px 26px' } },
          h('div', { style: { display: 'flex', alignItems: 'center', marginBottom: 18 } }, h('span', { style: { fontSize: 20, fontWeight: 600 } }, 'Create new user'), h('span', { onClick: close, style: { marginLeft: 'auto', color: FAINT, fontSize: 22, cursor: 'pointer' } }, '×')),
          done ? h('div', null,
            h('div', { style: { background: '#f2fbf4', border: '1px solid #12B3A6', borderRadius: 12, padding: 18 } },
              h('div', { style: { fontSize: 15, fontWeight: 600, marginBottom: 6 } }, '✅ Account created for ' + (done.customer && done.customer.name)),
              h('div', { style: { fontSize: 13, color: MUT, lineHeight: 1.7 } }, 'Email ', h('b', null, done.customer && done.customer.email), h('br'), 'Temporary password ', h('b', { style: { fontFamily: 'ui-monospace,Menlo,monospace' } }, done.tempPassword), h('div', { style: { fontSize: 12, color: FAINT, marginTop: 4 } }, 'Share this so they can sign in. They can reset it anytime.'))),
            h('div', { style: { marginTop: 16, display: 'flex', gap: 10 } },
              h('span', { onClick: () => this.setState({ nu_done: null, nu_first: '', nu_last: '', nu_company: '', nu_addr: '', nu_city: '', nu_country: '', nu_phone: '', nu_email: '', nu_promo: false }), style: { background: '#E52220', color: '#fff', fontWeight: 600, fontSize: 14, padding: '10px 20px', borderRadius: 999, cursor: 'pointer' } }, 'Add another'),
              h('span', { onClick: close, style: { border: '1px solid ' + HAIR, color: MUT, fontWeight: 600, fontSize: 14, padding: '10px 20px', borderRadius: 999, cursor: 'pointer' } }, 'Done'))) :
          h('div', { style: { display: 'flex', flexDirection: 'column', gap: 14 } },
            h('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 } }, field('First name', 'nu_first', true), field('Last name', 'nu_last', true)),
            h('div', null, lbl('Company name', false), h('span', { style: { fontSize: 12, color: '#E52220', marginLeft: -4 } }, ''), h('input', { placeholder: '', value: this.state.nu_company || '', onChange: e => this.setField('nu_company', e.target.value), style: inp })),
            field('Street address', 'nu_addr', true, 'House number and street name'),
            h('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 } },
              field('Town / City', 'nu_city', true),
              h('div', null, lbl('Country', true), h('select', { value: this.state.nu_country || '', onChange: e => this.setField('nu_country', e.target.value), style: inp }, h('option', { value: '' }, 'Select a country / region…'), [['MY', 'Malaysia'], ['SG', 'Singapore'], ['BN', 'Brunei']].map(c => h('option', { key: c[0], value: c[0] }, c[1]))))),
            h('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 } }, field('Phone', 'nu_phone', true), field('Email address', 'nu_email', true)),
            h('label', { style: { display: 'flex', gap: 9, alignItems: 'center', fontSize: 13, color: MUT, cursor: 'pointer' } },
              h('input', { type: 'checkbox', checked: !!this.state.nu_promo, onChange: e => this.setField('nu_promo', e.target.checked) }), 'Receive exclusive offers and promotions from Printoka.'),
            this.state.nu_err ? h('div', { style: { fontSize: 12.5, color: '#c0392b' } }, this.state.nu_err) : null,
            h('span', { onClick: () => this.submitNewUser(), style: { alignSelf: 'flex-start', background: '#E52220', color: '#fff', fontWeight: 600, fontSize: 14, padding: '11px 26px', borderRadius: 999, cursor: this.state.nu_busy ? 'wait' : 'pointer' } }, this.state.nu_busy ? 'Creating…' : 'Create user')))));
  }
  authSetSession(d) {
    try { localStorage.setItem('pk_token', d.token); } catch (e) {}
    const home = this.homeFor(d.customer);
    // set user + route together so access checks see the new identity synchronously
    this.setState({ user: d.customer, route: home, authErr: null, authBusy: false, megaOpen: false, ops: null });
    this.loadUserOrders();
    this.loadAccount();
    this.loadNotifications();
    if (['production', 'prepress', 'logistics', 'admin', 'outlet', 'dash'].indexOf(home) >= 0) this.loadQuotes();
    if (home === 'outlet') this.loadStaffOrders();
    const r = this.opsRoleFor(home);
    if (r) fetch('/api/jobs?role=' + this.opsRoleForUser(d.customer)).then(x => x.json()).then(j => this.setState({ ops: { jobs: j.jobs || [], role: this.opsRoleForUser(d.customer), loaded: true } })).catch(() => {});
    if (home === 'production') this.loadVendors();
    if (home === 'vendor') this.loadVendorRequests();
    if (home === 'admin') this.loadAdmin();
  }
  opsRoleForUser(u) {
    const map = { admin: 'production_director', production_manager: 'production_director', prepress: 'prepress_staff', scheduler: 'scheduler_staff', logistics: 'logistics_staff', outlet_staff: 'store_manager', outlet_manager: 'store_manager', vendor: 'printer', hub: 'hub' };
    return map[u && u.role] || 'production_director';
  }
  // ---------- outsource / vendor quotation flow ----------
  loadVendors() { if (this.state.vendors) return; fetch('/api/vendors').then(r => r.json()).then(d => this.setState({ vendors: d.vendors || [] })).catch(() => {}); }
  opsRequestQuotes(jobId, vendorIds) {
    fetch('/api/jobs/' + jobId + '/request-quotes', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify({ vendorIds }) })
      .then(r => r.json()).then(() => { this.setState({ quoteDialog: null }); this.opsLoad(this.opsActingRole()); }).catch(() => {});
  }
  opsAward(jobId, vendorId) {
    fetch('/api/jobs/' + jobId + '/award', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify({ vendorId }) })
      .then(r => r.json()).then(() => this.opsLoad(this.opsActingRole())).catch(() => {});
  }
  loadVendorRequests() {
    if (!this.authToken()) return;
    fetch('/api/vendor/requests', { headers: this.authHeaders() }).then(r => r.json()).then(d => this.setState({ vendorJobs: d.jobs || [] })).catch(() => {});
  }
  // ---------- admin backoffice data ----------
  loadAdmin() {
    if (!this.authToken()) return;
    const hd = this.authHeaders();
    fetch('/api/orders', { headers: hd }).then(r => r.json()).then(d => this.setState({ admOrders: d.orders || [] })).catch(() => {});
    fetch('/api/admin/customers', { headers: hd }).then(r => r.json()).then(d => this.setState({ admCustomers: d.customers || [] })).catch(() => {});
    fetch('/api/admin/staff', { headers: hd }).then(r => r.json()).then(d => this.setState({ admStaff: d.staff || [] })).catch(() => {});
    fetch('/api/admin/roles', { headers: hd }).then(r => r.json()).then(d => this.setState({ admRoles: d.roles || {} })).catch(() => {});
    fetch('/api/jobs?role=production_director', { headers: hd }).then(r => r.json()).then(d => this.setState({ admJobs: d.jobs || [] })).catch(() => {});
    fetch('/api/audit', { headers: hd }).then(r => r.json()).then(d => this.setState({ admAudit: d.audit || [] })).catch(() => {});
    this.loadQuotes();
    this.loadCustomInvoices();
    this.loadFaq();
    this.loadDownloads();
    this.loadMedia();
    this.loadEmails();
    this.loadSettings();
    this.blogLoad();
  }
  loadEmails() { if (!this.authToken()) return; fetch('/api/admin/emails', { headers: this.authHeaders() }).then(r => r.ok ? r.json() : null).then(d => { if (d) this.setState({ emailTpls: d.templates || [], emailOutbox: d.outbox || [] }); }).catch(() => {}); }
  toggleEmail(id, active) { fetch('/api/admin/emails/' + id, { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify({ active }) }).then(r => r.json()).then(d => this.setState({ emailTpls: d.templates || this.state.emailTpls })).catch(() => {}); }
  loadCustomInvoices() { if (typeof fetch !== 'function') return; fetch('/api/custom-invoices', { headers: this.authHeaders() }).then(r => r.json()).then(d => this.setState({ custInvoices: d.invoices || [] })).catch(() => {}); }
  submitCustomInvoice() {
    const s = this.state;
    const body = { number: s.ci_number, date: s.ci_date, status: s.ci_status || 'unpaid', userId: s.ci_userId || null, userName: s.ci_userName, currency: 'MYR', price: s.ci_price, orderId: s.ci_orderId, description: s.ci_desc };
    if (!body.userName && !body.userId) { this.setState({ ci_err: 'Pick or name the customer.' }); return; }
    if (!body.description) { this.setState({ ci_err: 'Add an invoice description.' }); return; }
    this.setState({ ci_busy: true, ci_err: null });
    fetch('/api/custom-invoices', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify(body) })
      .then(r => r.json()).then(() => { this.setState({ ci_busy: false, ci_new: false, ci_number: '', ci_date: '', ci_userName: '', ci_userId: '', ci_price: '', ci_orderId: '', ci_desc: '', ci_status: 'unpaid' }); this.loadCustomInvoices(); }).catch(() => this.setState({ ci_busy: false, ci_err: 'Network error.' }));
  }
  setCustomInvoiceStatus(cid, status) {
    fetch('/api/custom-invoices/' + cid, { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify({ status }) })
      .then(r => r.json()).then(() => this.loadCustomInvoices()).catch(() => {});
  }
  submitManualQuote() {
    const s = this.state;
    const body = { manual: true, product: s.mq_product, qty: s.mq_qty, weight: s.mq_weight, price: s.mq_price, leadDays: s.mq_lead, quoteData: s.mq_data, remarks: s.mq_remarks,
      userId: s.mq_userId || null, customer: { name: s.mq_custName, email: s.mq_custEmail } };
    if (!body.product) { this.setState({ mq_err: 'Enter the product.' }); return; }
    if (!body.customer.name && !body.userId) { this.setState({ mq_err: 'Pick or name the customer.' }); return; }
    this.setState({ mq_busy: true, mq_err: null });
    fetch('/api/quotes', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify(body) })
      .then(r => r.json()).then(() => { this.setState({ mq_busy: false, mq_new: false, mq_product: '', mq_qty: '', mq_weight: '', mq_price: '', mq_lead: '', mq_data: '', mq_remarks: '', mq_custName: '', mq_custEmail: '', mq_userId: '' }); this.loadQuotes(); }).catch(() => this.setState({ mq_busy: false, mq_err: 'Network error.' }));
  }
  // ---------- custom quotes ----------
  loadQuotes() { if (typeof fetch !== 'function') return; fetch('/api/quotes', { headers: this.authHeaders() }).then(r => r.json()).then(d => this.setState({ quotesList: d.quotes || [] })).catch(() => {}); }
  submitQuote() {
    const u = this.state.user || {};
    const body = {
      customer: { name: this.state.qfName || u.name || '', email: this.state.qfEmail || u.email || '', phone: this.state.qfPhone || u.phone || '', company: this.state.qfCompany || u.company || '' },
      product: this.state.qfProduct, size: this.state.qfSize, material: this.state.qfMaterial, finishing: this.state.qfFinishing, qty: this.state.qfQty, remarks: this.state.qfRemarks,
    };
    if (!body.product) { this.setState({ quoteErr: 'Please tell us what you want printed.' }); return; }
    this.setState({ quoteBusy: true, quoteErr: null });
    fetch('/api/quotes', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify(body) })
      .then(r => r.json()).then(d => this.setState({ quoteSent: d.quote, quoteBusy: false, qfProduct: '', qfSize: '', qfMaterial: '', qfFinishing: '', qfQty: '', qfRemarks: '' }))
      .catch(() => this.setState({ quoteBusy: false, quoteErr: 'Network error.' }));
  }
  quotePrice(qid) {
    const body = { price: this.state['qp_' + qid + '_price'], leadDays: this.state['qp_' + qid + '_lead'], note: this.state['qp_' + qid + '_note'] };
    fetch('/api/quotes/' + qid + '/price', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify(body) })
      .then(r => r.json()).then(() => this.loadQuotes()).catch(() => {});
  }
  quoteAccept(qid) {
    fetch('/api/quotes/' + qid + '/accept', { method: 'POST', headers: this.authHeaders() })
      .then(r => r.json()).then(d => { if (d.order) { this.setState({ order: d.order }); this.loadUserOrders(); this.loadQuotes(); this.go('confirm'); } }).catch(() => {});
  }
  quoteReject(qid) { fetch('/api/quotes/' + qid + '/reject', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify({ reason: 'Customer requested changes' }) }).then(r => r.json()).then(() => this.loadQuotes()).catch(() => {}); }
  // ---------- printable documents: invoice / order slip / custom invoice / custom quote ----------
  rm(n) { return 'RM' + Number(n || 0).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
  // friendly relative time for notifications ("just now", "2 hours ago", "yesterday")
  timeAgo(ts) {
    const t = Date.parse(ts); if (isNaN(t)) return '';
    const s = Math.max(0, (Date.now() - t) / 1000);
    if (s < 60) return 'just now';
    const m = Math.floor(s / 60); if (m < 60) return m + (m === 1 ? ' minute ago' : ' minutes ago');
    const hh = Math.floor(m / 60); if (hh < 24) return hh + (hh === 1 ? ' hour ago' : ' hours ago');
    const d = Math.floor(hh / 24); if (d === 1) return 'yesterday';
    if (d < 7) return d + ' days ago';
    const w = Math.floor(d / 7); if (w < 5) return w + (w === 1 ? ' week ago' : ' weeks ago');
    const mo = Math.floor(d / 30); return mo + (mo === 1 ? ' month ago' : ' months ago');
  }
  openDoc(id, type) {
    this.setState({ docType: type, docOrder: null, docRec: null });
    if (type === 'custominvoice') return fetch('/api/custom-invoices/' + id, { headers: this.authHeaders() }).then(r => r.json()).then(d => this.setState({ docRec: d.invoice || false })).catch(() => this.setState({ docRec: false }));
    if (type === 'quote') return fetch('/api/quotes/' + id, { headers: this.authHeaders() }).then(r => r.json()).then(d => this.setState({ docRec: d.quote || false })).catch(() => this.setState({ docRec: false }));
    fetch('/api/orders/' + id, { headers: this.authHeaders() }).then(r => r.json()).then(d => this.setState({ docOrder: d.order || false })).catch(() => this.setState({ docOrder: false }));
  }
  // shared address block (billing / shipping) for documents
  docAddr(a) {
    if (!a) return h('div', { style: { color: FAINT } }, '—');
    return h('div', { style: { color: MUT, lineHeight: 1.6 } }, a.name || '', a.phone ? h('div', null, a.phone) : null,
      [a.line1, a.line2].filter(Boolean).map((l, i) => h('div', { key: i }, l)),
      h('div', null, [a.postcode, a.city].filter(Boolean).join(', ')), a.state ? h('div', null, a.state) : null,
      h('div', null, ({ MY: 'Malaysia', SG: 'Singapore', BN: 'Brunei' })[a.country] || a.country || ''));
  }
  docHeader(title, ref, date, statusChip) {
    return h('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20, borderBottom: '2px solid ' + INK, paddingBottom: 14 } },
      h('div', null, h('div', { style: { fontSize: 20, fontWeight: 700, letterSpacing: '.14em' } }, 'printoka'), h('div', { style: { fontSize: 11.5, color: MUT, marginTop: 3 } }, 'Printoka Sdn Bhd · Miri, Sarawak · print@printoka.com')),
      h('div', { style: { textAlign: 'right' } }, h('div', { style: { fontSize: 15, fontWeight: 700, textTransform: 'uppercase' } }, title), h('div', { style: { fontSize: 12.5, color: MUT, marginTop: 3 } }, ref), h('div', { style: { fontSize: 11.5, color: FAINT } }, (date || '').slice(0, 10)), statusChip ? h('div', { style: { marginTop: 5 } }, statusChip) : null));
  }
  docDialog() {
    const type = this.state.docType; if (!type) return null;
    const close = () => this.setState({ docType: null, docOrder: null, docRec: null });
    const isSlip = type === 'slip', isOrder = type === 'invoice' || type === 'slip';
    const rec = isOrder ? this.state.docOrder : this.state.docRec;
    const title = { invoice: 'Invoice', slip: 'Order slip', custominvoice: 'Custom invoice', quote: 'Custom quote' }[type];
    const row = (l, r, bold) => h('div', { key: l, style: { display: 'flex', justifyContent: 'space-between', gap: 14, padding: '5px 0', fontSize: 13, fontWeight: bold ? 600 : 400, color: bold ? INK : MUT } }, h('span', null, l), h('span', { style: { color: INK } }, r));
    let body = null;
    if (rec) {
      if (isOrder) {
        const o = rec, paid = o.payment && o.payment.status === 'validated';
        body = [
          this.docHeader(isSlip ? 'Order Slip' : 'Tax Invoice', (isSlip ? '#' : 'INV-') + o.id.replace('PO-', ''), o.createdAt, this.chip(paid ? 'Paid' : 'Pending', paid ? 'ok' : 'warn')),
          h('div', { key: 'ad', style: { display: 'flex', justifyContent: 'space-between', gap: 20, marginBottom: 18, fontSize: 12.5 } },
            h('div', null, h('div', { style: { fontWeight: 600, marginBottom: 3 } }, 'Billing'), this.docAddr(o.billing || o.shipTo || o.customer)),
            h('div', { style: { textAlign: 'right' } }, h('div', { style: { fontWeight: 600, marginBottom: 3 } }, 'Shipping'), this.docAddr(o.shipTo || o.billing || o.customer))),
          h('table', { key: 'tb', style: { width: '100%', borderCollapse: 'collapse', fontSize: 12.5, marginBottom: 16 } },
            h('thead', null, h('tr', { style: { borderBottom: '1px solid ' + INK } }, ['#', 'Item' + (isSlip ? ' / spec / artwork' : ''), 'Qty', 'Unit', 'Amount'].map((c, i) => h('th', { key: i, style: { textAlign: i > 1 ? 'right' : 'left', padding: '7px 4px', fontSize: 11, textTransform: 'uppercase', letterSpacing: '.05em', color: FAINT } }, c)))),
            h('tbody', null, (o.items || []).map((it, i) => h('tr', { key: i, style: { borderBottom: '1px solid ' + LINE, verticalAlign: 'top' } },
              h('td', { style: { padding: '9px 4px', color: MUT } }, it.lineNo || i + 1),
              h('td', { style: { padding: '9px 4px' } }, h('div', { style: { fontWeight: 600 } }, it.product),
                isSlip ? h('div', { style: { color: MUT, fontSize: 11.5, lineHeight: 1.6, marginTop: 3 } }, this.specView(it)) : null,
                isSlip && (it.artworks || []).length ? h('div', { style: { color: TEAL, fontSize: 11.5, marginTop: 4 } }, (it.artworks || []).map((a, k) => h('div', { key: k }, 'Artwork: ' + a))) : null),
              h('td', { style: { padding: '9px 4px', textAlign: 'right', color: MUT } }, (it.qty || 0).toLocaleString()),
              h('td', { style: { padding: '9px 4px', textAlign: 'right', color: MUT } }, this.rm(it.unitPrice)),
              h('td', { style: { padding: '9px 4px', textAlign: 'right', fontWeight: 500 } }, this.rm(it.lineTotal)))))),
          h('div', { key: 'tot', style: { marginLeft: 'auto', maxWidth: 260 } },
            row('Subtotal', this.rm(o.subtotal)),
            o.memberDiscount ? row('Member discount', '− ' + this.rm(o.memberDiscount)) : null,
            o.creditApplied ? row('Credit applied', '− ' + this.rm(o.creditApplied)) : null,
            row('SST 8%', this.rm(o.tax)),
            row('Delivery', this.rm(o.shipping)),
            h('div', { style: { borderTop: '2px solid ' + INK, marginTop: 6 } }, row(paid ? 'Total paid' : 'Total due', this.rm(o.total), true))),
          isSlip ? h('div', { key: 'n', style: { marginTop: 14, fontSize: 11.5, color: FAINT, lineHeight: 1.7 } }, 'Order slip carries full production detail incl. artwork filenames — for production and your own finance/claims use.') : null,
        ];
      } else if (type === 'custominvoice') {
        const inv = rec, paid = inv.status === 'paid';
        body = [
          this.docHeader('Invoice', inv.number || inv.id, inv.date, this.chip(paid ? 'Paid' : inv.status === 'cancelled' ? 'Cancelled' : 'Unpaid', paid ? 'ok' : inv.status === 'cancelled' ? 'neutral' : 'warn')),
          h('div', { key: 'bt', style: { marginBottom: 16, fontSize: 12.5 } }, h('div', { style: { fontWeight: 600, marginBottom: 3 } }, 'Bill to'), h('div', { style: { color: MUT } }, inv.userName || '—')),
          h('div', { key: 'ds', style: { whiteSpace: 'pre-wrap', fontSize: 12.5, color: INK, lineHeight: 1.7, border: '1px solid ' + LINE, borderRadius: 8, padding: '14px 16px', marginBottom: 16 } }, inv.description || '—'),
          h('div', { key: 'tot', style: { marginLeft: 'auto', maxWidth: 260 } }, h('div', { style: { borderTop: '2px solid ' + INK } }, row('Total', this.rm(inv.price), true))),
        ];
      } else if (type === 'quote') {
        const q = rec;
        body = [
          this.docHeader('Quotation', q.id, q.createdAt, null),
          h('div', { key: 'to', style: { display: 'flex', justifyContent: 'space-between', gap: 20, marginBottom: 16, fontSize: 12.5 } },
            h('div', null, h('div', { style: { fontWeight: 600, marginBottom: 3 } }, 'To'), h('div', { style: { color: MUT, lineHeight: 1.6 } }, (q.customer && q.customer.name) || '—', (q.customer && q.customer.company) ? h('div', null, q.customer.company) : null, (q.customer && q.customer.email) ? h('div', null, q.customer.email) : null)),
            h('div', { style: { textAlign: 'right', color: MUT } }, h('div', { style: { fontWeight: 600, color: INK } }, q.requirement && q.requirement.product), q.requirement && q.requirement.qty ? h('div', null, 'Qty ' + q.requirement.qty) : null, q.leadDays ? h('div', null, 'Lead time: ' + q.leadDays + ' days') : null)),
          (q.requirement && q.requirement.quoteData) ? h('div', { key: 'qd', style: { whiteSpace: 'pre-wrap', fontSize: 12.5, color: INK, lineHeight: 1.7, border: '1px solid ' + LINE, borderRadius: 8, padding: '14px 16px', marginBottom: 16 } }, q.requirement.quoteData) : null,
          h('div', { key: 'tot', style: { marginLeft: 'auto', maxWidth: 260 } }, h('div', { style: { borderTop: '2px solid ' + INK } }, row('Total price', this.rm(q.price), true))),
        ];
      }
    }
    return h('div', { key: 'doc', onClick: close, style: { position: 'fixed', inset: 0, zIndex: 95, background: 'rgba(15,20,25,.5)', display: 'grid', placeItems: 'center', padding: 20, overflow: 'auto' } },
      h('div', { onClick: e => e.stopPropagation(), style: { background: '#fff', borderRadius: 12, maxWidth: 660, width: '100%', maxHeight: '92vh', overflow: 'auto', boxShadow: '0 24px 60px rgba(33,33,33,.3)' } },
        h('div', { style: { padding: '14px 22px', borderBottom: '1px solid ' + HAIR, display: 'flex', alignItems: 'center', gap: 10 } },
          h('span', { style: { fontSize: 14, fontWeight: 600 } }, title),
          h('span', { onClick: () => { if (typeof window !== 'undefined') window.print(); }, style: { marginLeft: 'auto', fontSize: 12.5, fontWeight: 600, color: '#fff', background: TEAL, borderRadius: 7, padding: '7px 14px', cursor: 'pointer' } }, 'Print / Save PDF'),
          h('span', { onClick: close, style: { color: FAINT, fontSize: 20, cursor: 'pointer' } }, '×')),
        !rec ? h('div', { style: { padding: 40, textAlign: 'center', color: FAINT } }, rec === false ? 'Could not load the document.' : 'Loading…') :
        h('div', { id: 'pk-doc', style: { padding: 28 } }, body,
          h('div', { style: { marginTop: 22, paddingTop: 12, borderTop: '1px solid ' + LINE, fontSize: 11, color: FAINT, textAlign: 'center' } }, 'Thank you for printing with Printoka. This is a computer-generated document.'))));
  }
  // ---------- management order detail view (admin / outlet / production) ----------
  openOrder(orderId) {
    this.setState({ ordView: null, ordViewId: orderId });
    fetch('/api/orders/' + orderId, { headers: this.authHeaders() }).then(r => r.json()).then(d => this.setState({ ordView: d.order || false })).catch(() => this.setState({ ordView: false }));
  }
  validateOrder(orderId) {
    fetch('/api/orders/' + orderId + '/pay', { method: 'POST', headers: this.authHeaders() }).then(r => r.json()).then(d => { if (d.order) this.setState({ ordView: d.order }); this.loadAdmin(); }).catch(() => {});
  }
  orderDialog() {
    if (!this.state.ordViewId) return null;
    const o = this.state.ordView;
    const close = () => this.setState({ ordViewId: null, ordView: null });
    const paid = o && o.payment && o.payment.status === 'validated';
    const sect = (t, node) => h('div', { key: t, style: { marginBottom: 16 } }, h('div', { style: { fontSize: 11, fontWeight: 700, letterSpacing: '.07em', textTransform: 'uppercase', color: FAINT, marginBottom: 8 } }, t), node);
    const hist = (o && o.customerHistory) || { totalOrders: 0, totalRevenue: 0, avgOrderValue: 0 };
    return h('div', { key: 'ord', onClick: close, style: { position: 'fixed', inset: 0, zIndex: 92, background: 'rgba(15,20,25,.5)', display: 'grid', placeItems: 'start center', padding: 20, overflow: 'auto' } },
      h('div', { onClick: e => e.stopPropagation(), style: { background: '#fff', borderRadius: 14, maxWidth: 900, width: '100%', margin: '10px 0', boxShadow: '0 24px 60px rgba(33,33,33,.3)' } },
        h('div', { style: { padding: '15px 22px', borderBottom: '1px solid ' + HAIR, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', position: 'sticky', top: 0, background: '#fff', borderRadius: '14px 14px 0 0', zIndex: 1 } },
          h('span', { style: { font: '600 13px ui-monospace,Menlo,monospace', color: TEAL } }, this.state.ordViewId),
          o ? this.chip(paid ? 'Paid' : 'Payment pending', paid ? 'ok' : 'warn') : null,
          o ? h('span', { style: { fontSize: 12.5, color: MUT } }, (o.channel || 'online') + ' · ' + (o.createdAt || '').slice(0, 10)) : null,
          h('span', { style: { marginLeft: 'auto', display: 'flex', gap: 8, flexWrap: 'wrap' } },
            o ? h('span', { onClick: () => this.openDoc(o.id, 'invoice'), style: { fontSize: 12.5, fontWeight: 600, color: TEAL, border: '1px solid ' + HAIR, borderRadius: 7, padding: '7px 12px', cursor: 'pointer' } }, 'Invoice PDF') : null,
            o ? h('span', { onClick: () => this.openDoc(o.id, 'slip'), style: { fontSize: 12.5, fontWeight: 600, color: TEAL, border: '1px solid ' + HAIR, borderRadius: 7, padding: '7px 12px', cursor: 'pointer' } }, 'Order slip') : null,
            (o && !paid) ? h('span', { onClick: () => this.validateOrder(o.id), style: { fontSize: 12.5, fontWeight: 600, color: '#fff', background: TEAL, borderRadius: 7, padding: '7px 12px', cursor: 'pointer' } }, 'Validate payment') : null,
            h('span', { onClick: close, style: { color: FAINT, fontSize: 22, cursor: 'pointer', lineHeight: 1 } }, '×'))),
        !o ? h('div', { style: { padding: 50, textAlign: 'center', color: FAINT } }, o === false ? 'Could not load the order.' : 'Loading…') :
        h('div', { style: { padding: 22 } },
          // customer history strip (WP "Customer history" panel)
          sect('Customer · order history', h('div', { style: { display: 'flex', gap: 22, flexWrap: 'wrap', alignItems: 'center' } },
            h('div', { style: { fontSize: 14, fontWeight: 600 } }, (o.customer && o.customer.name) || '—', h('span', { style: { fontWeight: 400, color: MUT, marginLeft: 8, fontSize: 12.5 } }, (o.customer && o.customer.email) || '')),
            h('span', { style: { flex: 1 } }),
            [['Total orders', String(hist.totalOrders)], ['Total revenue', this.rm(hist.totalRevenue)], ['Avg order value', this.rm(hist.avgOrderValue)]].map((k, i) =>
              h('div', { key: i, style: { textAlign: 'right' } }, h('div', { style: { fontSize: 10.5, color: FAINT, textTransform: 'uppercase', letterSpacing: '.05em' } }, k[0]), h('div', { style: { fontSize: 15, fontWeight: 600 } }, k[1]))))),
          // order details (line items + full spec + artworks)
          sect('Order details & artworks', h('div', { style: { display: 'flex', flexDirection: 'column', gap: 10 } },
            (o.items || []).map((it, i) => h('div', { key: i, style: { border: '1px solid ' + HAIR, borderRadius: 10, padding: 13, display: 'flex', gap: 12 } },
              h('div', { style: { flex: '0 0 60px' } }, this.art(it.product)),
              h('div', { style: { flex: 1, minWidth: 0 } },
                h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' } },
                  h('span', { style: { fontSize: 13.5, fontWeight: 600 } }, it.product),
                  h('span', { style: { fontSize: 13, fontWeight: 600 } }, this.rm(it.lineTotal))),
                h('div', { style: { fontSize: 12, color: MUT, lineHeight: 1.6, marginTop: 4 } }, this.specView(it)),
                h('div', { style: { fontSize: 12, color: FAINT, marginTop: 4 } }, 'Qty ' + (it.qty || 0).toLocaleString() + ' · unit ' + this.rm(it.unitPrice)),
                (it.artworks || []).length ? h('div', { style: { display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 } }, (it.artworks || []).map((a, k) =>
                  h('span', { key: k, style: { display: 'inline-flex', alignItems: 'center', gap: 5, background: CHIP, color: TEAL, fontSize: 11.5, fontWeight: 600, borderRadius: 6, padding: '4px 8px' } }, '📎 ' + a))) : h('div', { style: { fontSize: 11.5, color: FAINT, marginTop: 6 } }, 'No artwork uploaded yet')))))),
          // billing + shipping + payment
          h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 16 } },
            sect('Billing address', h('div', { style: { fontSize: 12.5 } }, this.docAddr(o.billing || o.customer))),
            sect('Shipping address', h('div', { style: { fontSize: 12.5 } }, this.docAddr(o.shipTo || o.billing || o.customer))),
            sect('Payment proof', h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.7 } },
              h('div', null, h('b', { style: { color: INK } }, o.payment && (o.payment.gateway || o.payment.method))),
              h('div', null, 'Status: ', this.chip(paid ? 'Validated' : 'Pending', paid ? 'ok' : 'warn')),
              (o.payment && o.payment.reference) ? h('div', { style: { fontFamily: 'ui-monospace,Menlo,monospace', fontSize: 11.5, marginTop: 4 } }, 'Ref: ' + o.payment.reference) : null,
              (o.payment && o.payment.paidAt) ? h('div', null, 'Paid: ' + o.payment.paidAt.slice(0, 16).replace('T', ' ')) : null,
              (o.payment && o.payment.proof) ? h('div', { style: { marginTop: 6 } }, h('span', { style: { display: 'inline-flex', alignItems: 'center', gap: 5, background: CHIP, color: TEAL, fontSize: 11.5, fontWeight: 600, borderRadius: 6, padding: '4px 8px' } }, '🧾 ' + o.payment.proof)) : null))),
          // price summary
          sect('Price', h('div', { style: { maxWidth: 300 } },
            [['Subtotal', this.rm(o.subtotal)], o.memberDiscount ? ['Member discount', '− ' + this.rm(o.memberDiscount)] : null, o.creditApplied ? ['Credit applied', '− ' + this.rm(o.creditApplied)] : null, ['SST 8%', this.rm(o.tax)], ['Delivery', this.rm(o.shipping)]].filter(Boolean).map((r, i) =>
              h('div', { key: i, style: { display: 'flex', justifyContent: 'space-between', fontSize: 12.5, color: MUT, padding: '4px 0' } }, h('span', null, r[0]), h('span', null, r[1]))),
            h('div', { style: { display: 'flex', justifyContent: 'space-between', fontSize: 15, fontWeight: 600, borderTop: '1px solid ' + HAIR, marginTop: 6, paddingTop: 8 } }, h('span', null, paid ? 'Total paid' : 'Total due'), h('span', null, this.rm(o.total)))),
          ))));
  }
  vendorSubmitQuote(jobId) {
    const body = { price: this.state['vq_' + jobId + '_price'], leadDays: this.state['vq_' + jobId + '_lead'], note: this.state['vq_' + jobId + '_note'] };
    fetch('/api/jobs/' + jobId + '/quote', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify(body) })
      .then(r => r.json()).then(() => this.loadVendorRequests()).catch(() => {});
  }
  register() {
    this.setState({ authBusy: true, authErr: null });
    const body = { name: this.state.rgName, email: this.state.rgEmail, phone: this.state.rgPhone, password: this.state.rgPass };
    fetch('/api/auth/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(r => r.json()).then(d => d.token ? this.authSetSession(d) : this.setState({ authErr: d.error || 'Could not register.', authBusy: false }))
      .catch(() => this.setState({ authErr: 'Network error.', authBusy: false }));
  }
  login() {
    this.setState({ authBusy: true, authErr: null });
    fetch('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: this.state.lgEmail, password: this.state.lgPass }) })
      .then(r => r.json()).then(d => d.token ? this.authSetSession(d) : this.setState({ authErr: d.error || 'Could not sign in.', authBusy: false }))
      .catch(() => this.setState({ authErr: 'Network error.', authBusy: false }));
  }
  logout() {
    fetch('/api/auth/logout', { method: 'POST', headers: this.authHeaders() }).catch(() => {});
    try { localStorage.removeItem('pk_token'); } catch (e) {}
    this.setState({ user: null, userOrders: null }); this.go('home');
  }
  loadUserOrders() {
    if (!this.authToken()) return;
    fetch('/api/orders', { headers: this.authHeaders() }).then(r => r.json()).then(d => this.setState({ userOrders: d.orders || [] })).catch(() => {});
  }
  // ---------- address book + credit ledger ----------
  loadAccount() {
    if (!this.authToken()) return;
    fetch('/api/account/addresses', { headers: this.authHeaders() }).then(r => r.json()).then(d => this.setState({ addresses: d.addresses || [] })).catch(() => {});
    fetch('/api/account/credit', { headers: this.authHeaders() }).then(r => r.json()).then(d => this.setState({ credit: d })).catch(() => {});
  }
  addressAdd() {
    const a = { label: this.state.adLabel || 'Address', line1: this.state.adLine1, line2: this.state.adLine2, city: this.state.adCity, postcode: this.state.adPostcode, state: this.state.adState, country: this.cc() };
    if (!a.line1) return;
    fetch('/api/account/addresses', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify(a) })
      .then(r => r.json()).then(d => this.setState({ addresses: d.addresses || [], adLabel: '', adLine1: '', adLine2: '', adCity: '', adPostcode: '', adState: '', addingAddr: false })).catch(() => {});
  }
  addressDelete(id) { fetch('/api/account/addresses/' + id, { method: 'DELETE', headers: this.authHeaders() }).then(r => r.json()).then(d => this.setState({ addresses: d.addresses || [] })).catch(() => {}); }
  addressDefault(id) { fetch('/api/account/addresses/default/' + id, { method: 'POST', headers: this.authHeaders() }).then(r => r.json()).then(d => this.setState({ addresses: d.addresses || [] })).catch(() => {}); }
  // ---------- customer: wallet top-up, profile, password ----------
  walletTopUp() {
    const amt = Number(this.state.tu_amount); if (!amt || amt <= 0) { this.setState({ tu_err: 'Enter an amount.' }); return; }
    this.setState({ tu_busy: true, tu_err: null });
    fetch('/api/account/credit', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify({ reason: 'TOPUP', amount: amt, actor: 'customer' }) })
      .then(r => r.json()).then(d => { this.setState({ tu_busy: false, tu_open: false, tu_amount: '', credit: d }); }).catch(() => this.setState({ tu_busy: false, tu_err: 'Network error.' }));
  }
  submitProfile() {
    const s = this.state, u = this.state.user || {};
    const body = { name: [s.pf_first != null ? s.pf_first : (u.name || '').split(' ')[0], s.pf_last != null ? s.pf_last : (u.name || '').split(' ').slice(1).join(' ')].filter(Boolean).join(' '), phone: s.pf_phone != null ? s.pf_phone : u.phone, newsletter: !!s.pf_news };
    this.setState({ pf_busy: true, pf_msg: null });
    fetch('/api/account/profile', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify(body) })
      .then(r => r.json()).then(d => this.setState({ pf_busy: false, pf_msg: 'Saved.', user: d.customer || this.state.user })).catch(() => this.setState({ pf_busy: false, pf_msg: 'Network error.' }));
  }
  submitPassword() {
    const s = this.state;
    if (!s.pw_next || s.pw_next !== s.pw_confirm) { this.setState({ pw_err: 'New passwords do not match.' }); return; }
    this.setState({ pw_busy: true, pw_err: null });
    fetch('/api/account/password', { method: 'POST', headers: Object.assign({ 'Content-Type': 'application/json' }, this.authHeaders()), body: JSON.stringify({ current: s.pw_current, next: s.pw_next }) })
      .then(r => r.json()).then(d => { if (d.error) { this.setState({ pw_busy: false, pw_err: d.error }); return; } this.setState({ pw_busy: false, pw_open: false, pw_current: '', pw_next: '', pw_confirm: '', pf_msg: 'Password changed.' }); }).catch(() => this.setState({ pw_busy: false, pw_err: 'Network error.' }));
  }

  // ---------- content: blog / Learning Hub (migrated from printoka.com) ----------
  blogLoad() {
    if (typeof fetch !== 'function' || (this.state.blog && this.state.blog.length)) return;
    fetch('/api/content/blog').then(r => r.json()).then(d => this.setState({ blog: d.posts || [] })).catch(() => {});
  }
  blogOpen(slug) {
    if (typeof window !== 'undefined') window.scrollTo(0, 0);
    this.setState({ route: 'article', articleSlug: slug, article: null });
    if (typeof fetch === 'function')
      fetch('/api/content/blog/' + slug).then(r => r.json()).then(d => this.setState({ article: d.post || false })).catch(() => this.setState({ article: false }));
  }
  // tiny, safe Markdown → React renderer (headings, lists, paragraphs, bold/italic)
  mdInline(text) {
    const parts = []; let s = String(text || ''); let key = 0;
    // bold / italic / code / [label](href) links
    const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g; let last = 0, m;
    while ((m = re.exec(s))) {
      if (m.index > last) parts.push(s.slice(last, m.index));
      const t = m[0];
      if (t.startsWith('**')) parts.push(h('b', { key: key++ }, t.slice(2, -2)));
      else if (t.startsWith('`')) parts.push(h('code', { key: key++, style: { background: '#f1f3f5', padding: '1px 5px', borderRadius: 4, fontSize: '.9em' } }, t.slice(1, -1)));
      else if (t.startsWith('[')) { const lm = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(t); if (lm) parts.push(h('a', { key: key++, href: lm[2], style: { color: TEAL, fontWeight: 500, textDecoration: 'underline' } }, lm[1])); else parts.push(t); }
      else parts.push(h('i', { key: key++ }, t.slice(1, -1)));
      last = m.index + t.length;
    }
    if (last < s.length) parts.push(s.slice(last));
    return parts;
  }
  mdToNodes(md) {
    const lines = String(md || '').split('\n'); const out = []; let list = null; let key = 0;
    const flush = () => { if (list) { out.push(h('ul', { key: key++, style: { margin: '0 0 16px', paddingLeft: 22, color: MUT, lineHeight: 1.75, fontSize: 15 } }, list)); list = null; } };
    for (const ln of lines) {
      const t = ln.trim();
      if (!t) { flush(); continue; }
      if (t.startsWith('### ')) { flush(); out.push(h('h3', { key: key++, style: { fontSize: 18, fontWeight: 600, margin: '22px 0 8px' } }, this.mdInline(t.slice(4)))); }
      else if (t.startsWith('## ')) { flush(); out.push(h('h2', { key: key++, style: { fontSize: 22, fontWeight: 600, margin: '28px 0 10px', letterSpacing: '-.01em' } }, this.mdInline(t.slice(3)))); }
      else if (/^[-*] /.test(t)) { if (!list) list = []; list.push(h('li', { key: key++ }, this.mdInline(t.slice(2)))); }
      else { flush(); out.push(h('p', { key: key++, style: { margin: '0 0 16px', color: MUT, lineHeight: 1.8, fontSize: 15.5 } }, this.mdInline(t))); }
    }
    flush();
    return out;
  }

  // ---------- programmatic SEO landing pages (per-city / per-service, migrated URLs) ----------
  // Resolve the real browser URL to a page so the migrated URLs (/blog/<slug>/, /<service>-printing-<city>/) render.
  resolveUrl() {
    if (typeof window === 'undefined') return;
    const segs = window.location.pathname.split('/').filter(Boolean);
    if (!segs.length) { if (this.state.route !== 'home') this.setState({ route: 'home' }); return; }
    if (segs[0] === 'blog' && segs[1]) return this.blogOpen(segs[1]);
    // named top-level routes (so the SSR header/footer links resolve in the SPA)
    const NAMED = { cart: 'cart', checkout: 'checkout', auth: 'auth', search: 'search', learn: 'learn', 'learning-hub': 'learn', membership: 'membership', contact: 'contact', about: 'about', 'about-us': 'about', support: 'support', downloads: 'downloads', partners: 'partners', terms: 'terms', track: 'track', packaging: 'packaging' };
    if (segs.length === 1 && NAMED[segs[0]]) return this.setState({ route: NAMED[segs[0]] });
    // category listing: /products or /products/<catId>
    if (segs[0] === 'products') return this.setState({ route: 'category', catFilter: segs[1] || 'all' });
    // product page: /<name>-printing (matched before the SEO city landing pages, which carry an
    // extra -<city> suffix and so won't match a bare product slug). The slug→id map needs the
    // pricing engine; until it loads, DEFER (set a flag; componentDidMount re-runs resolveUrl on
    // pk-engine-ready) rather than mis-routing a product slug to seoOpen.
    if (!this.pkProducts().length) { this._urlPending = true; return; }
    this._urlPending = false;
    const pid = this.pkIdBySlug(segs[0]);
    if (pid != null) { if (typeof window !== 'undefined') window.scrollTo(0, 0); return this.setState({ prodId: pid, cfg: {}, qty: 1000, qtyChosen: false, route: 'product' }); }
    const LOC = { au: 1, nz: 1, sg: 1, bn: 1 };
    let locale = 'my', rest = segs;
    if (LOC[segs[0]]) { locale = segs[0]; rest = segs.slice(1); }
    const slug = rest[0];
    if (slug && /(printing|solutions|packaging)/.test(slug)) return this.seoOpen(slug, locale);
  }
  seoOpen(slug, locale) {
    if (typeof window !== 'undefined') window.scrollTo(0, 0);
    this.setState({ route: 'seo', seoPage: null });
    if (typeof fetch === 'function')
      fetch('/api/content/seo/' + slug + (locale && locale !== 'my' ? '?locale=' + locale : ''))
        .then(r => r.json()).then(d => this.setState({ seoPage: d.page || false })).catch(() => this.setState({ seoPage: false }));
  }
  seoCategoryFor(slug) {
    const s = slug || '';
    if (/sticker|label/.test(s)) return 'labels-stickers';
    if (/brochure|flyer|leaflet/.test(s)) return 'flyers-leaflets';
    if (/packaging|box/.test(s)) return 'packaging-boxes';
    if (/booklet|book/.test(s)) return 'books-stationery';
    if (/banner|bunting|large/.test(s)) return 'large-format';
    return 'business-essentials';
  }
  s_seo() {
    const p = this.state.seoPage;
    if (p === null) return h('div', { style: { maxWidth: 760, margin: '0 auto', padding: '40px 20px', color: FAINT, textAlign: 'center' } }, 'Loading…');
    if (p === false) return h('div', { style: { maxWidth: 760, margin: '0 auto', padding: '40px 20px' } }, h('p', { style: { color: MUT } }, 'Page not found.'), this.btn('Browse products', 'teal', 'category'));
    const place = (p.slug.replace(/.*-printing-/, '').replace(/.*-in-/, '').replace(/-/g, ' ') || '').replace(/\b\w/g, c => c.toUpperCase());
    const cat = this.seoCategoryFor(p.slug);
    const prods = this.catProducts(cat).slice(0, 8);
    const cc = { au: 'Australia', nz: 'New Zealand', sg: 'Singapore', bn: 'Brunei', my: 'Malaysia' }[p.locale];
    return h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '10px 20px 40px' } },
      h('div', { style: { fontSize: 12.5, color: FAINT, marginBottom: 12 } }, h('span', { 'data-go': 'home', style: { color: TEAL, cursor: 'pointer' } }, 'Home'), ' › ' + cc + ' › ' + p.title),
      h('section', { style: { background: 'linear-gradient(180deg,#fdf2f2,#fff)', borderRadius: 16, padding: '34px 28px', marginBottom: 26 } },
        h('div', { style: { fontSize: 11.5, fontWeight: 600, letterSpacing: '.08em', textTransform: 'uppercase', color: TEAL, marginBottom: 10 } }, 'Online printing · ' + cc),
        h('h1', { style: { margin: '0 0 12px', fontSize: 'clamp(28px,4vw,42px)', lineHeight: 1.1, letterSpacing: '-.02em', fontWeight: 600, maxWidth: '20ch' } }, p.title),
        h('p', { style: { margin: '0 0 18px', fontSize: 16, color: MUT, lineHeight: 1.65, maxWidth: '60ch' } },
          'Order ' + p.title.toLowerCase() + ' online with instant, factory-direct pricing — no waiting for a manual quote. Configure your specs, see the exact price with member-tier savings, upload artwork and we print and deliver' + (place ? ' to ' + place : '') + '.'),
        h('div', { style: { display: 'flex', gap: 11, flexWrap: 'wrap' } }, this.btn('Get an instant price →', 'teal', 'catopen:' + cat), this.btn('Browse all products', 'ghost', 'catopen:all'))),
      h('h2', { style: { fontSize: 22, fontWeight: 600, margin: '0 0 16px' } }, 'Popular products' + (place ? ' in ' + place : '')),
      h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(210px,1fr))', gap: 16 } },
        prods.map(pr => { const from = this.catFromPrice(pr.id);
          return h('a', { key: pr.id, href: this.productPath(pr.id) || undefined, 'data-go': 'open:' + pr.id, style: { border: '1px solid ' + HAIR, borderRadius: 12, background: '#fff', overflow: 'hidden', cursor: 'pointer', display: 'block', color: 'inherit', textDecoration: 'none' } },
            this.art(pr.engName),
            h('div', { style: { padding: '13px 14px' } },
              h('div', { style: { fontSize: 13.5, fontWeight: 500, minHeight: 34, lineHeight: 1.3 } }, pr.name),
              h('div', { style: { fontSize: 14, fontWeight: 600, color: TEAL, marginTop: 6 } }, from != null ? 'from ' + this.money(from) + '/pc' : 'Quote'))); })),
      h('div', { style: { marginTop: 28, border: '1px solid ' + HAIR, borderRadius: 12, padding: 22, background: '#fff' } },
        h('h2', { style: { fontSize: 20, fontWeight: 600, margin: '0 0 10px' } }, 'Why print with Printoka' + (place ? ' in ' + place : '') + '?'),
        h('p', { style: { fontSize: 14.5, color: MUT, lineHeight: 1.8, margin: 0, maxWidth: '80ch' } },
          'Printoka is an online printing marketplace aggregating 30+ vendors plus our own facility in Miri, Sarawak. We serve ' + cc + ' with more than 100 products, instant online pricing, a five-tier membership discount and delivery' + (place ? ' across ' + place + ' and nationwide' : ' nationwide') + '. Every price you see in the configurator is the price on your quotation, at checkout and on the invoice — one number, traceable to one engine.')),
      h('div', { style: { marginTop: 18, fontSize: 11.5, color: FAINT } }, 'SEO landing page · migrated URL ' + p.path + ' · in sitemap.xml'));
  }

  // ---------- live operations data layer (shared backend state machine) ----------
  // Each department dashboard reads the SAME /api/jobs; a transition moves a job's
  // status → its queue changes → it appears in the next department. One order, synced.
  opsRoleFor(route) {
    return ({ outlet: 'store_manager', prepress: 'prepress_staff', production: 'scheduler_staff', logistics: 'logistics_staff', director: 'production_director' })[route] || null;
  }
  opsLoad(role) {
    if (typeof fetch !== 'function') return;
    fetch('/api/jobs?role=' + role).then(r => r.json()).then(d => this.setState({ ops: { jobs: d.jobs || [], role: role, loaded: true } })).catch(() => {});
  }
  opsJobs() { return (this.state.ops && this.state.ops.jobs) || []; }
  opsTransition(jobId, action, payload) {
    const role = (this.state.ops && this.state.ops.role) || 'production_director';
    if (typeof fetch !== 'function') return;
    fetch('/api/jobs/' + jobId + '/transition', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ role, action, payload: payload || {} }) })
      .then(r => r.json()).then(() => this.opsLoad(role)).catch(() => {});
  }
  opsAction(j, a) {
    const def = { machine: 'Digital-01', printer: 'Best-Quote Printer', courier: 'J&T Express', tracking: 'TRK-' + j.id, reason: 'Off-bleed on right edge (see proof)', proof: 'proof-' + j.id + '.png' };
    const payload = {}; (a.requires || []).forEach(f => { payload[f] = def[f] || '—'; });
    this.opsTransition(j.id, a.action, payload);
  }
  opsCreateOrder() {
    if (typeof fetch !== 'function') return;
    const names = ['Cahaya Enterprise', 'Delima Cafe', 'Titan Auto', 'Seri Mutiara', 'BeautyGlow', 'Hikmah Academy'];
    const prods = [[1, 'Business Card', '54×89mm · 310gsm · 4C both · 1,000 pcs', 1000, 86.42], [102, 'Flyer', 'A5 · 128gsm · 4C both · 2,000 pcs', 2000, 268], [19, 'Booklet — Litho', 'A4 · Saddle · 8pp · 500 pcs', 500, 620]];
    const pr = prods[Math.floor(Math.random() * prods.length)];
    const body = { channel: 'online', customer: names[Math.floor(Math.random() * names.length)], product: pr[1], spec: pr[2], qty: pr[3], price: pr[4], paymentValidated: true, artworkMatches: true, deadline: new Date(Date.now() + 36 * 3600e3).toISOString() };
    fetch('/api/jobs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(r => r.json()).then(() => this.opsLoad((this.state.ops && this.state.ops.role) || 'store_manager')).catch(() => {});
  }
  // live pipeline strip — counts per department, so an order is visible moving across all of them
  opsPipeline(highlightQueue) {
    const jobs = this.opsJobs();
    const stages = [['outlet', 'Intake'], ['prepress', 'Prepress'], ['scheduler', 'Scheduler'], ['logistics', 'Logistics'], ['done', 'Done']];
    const n = q => jobs.filter(j => j.queue === q).length;
    return h('div', { key: 'pipe', style: { display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 6, border: '1px solid ' + HAIR, borderRadius: 12, padding: '12px 16px', margin: '4px 0 18px', background: '#fff' } },
      h('span', { style: { fontSize: 11, fontWeight: 600, letterSpacing: '.07em', textTransform: 'uppercase', color: FAINT, marginRight: 6 } }, 'Live pipeline'),
      stages.map((s, i) => {
        const on = s[0] === highlightQueue, c = n(s[0]);
        return h('span', { key: s[0], style: { display: 'flex', alignItems: 'center', gap: 6 } },
          h('span', { style: { display: 'flex', alignItems: 'center', gap: 7, padding: '5px 11px', borderRadius: 999, background: on ? TEAL : (c ? '#fdf2f2' : ALT), color: on ? '#fff' : (c ? TEAL : MUT), fontSize: 12.5, fontWeight: 600 } },
            s[1], h('span', { style: { background: on ? 'rgba(255,255,255,.25)' : '#fff', color: on ? '#fff' : (c ? TEAL : FAINT), borderRadius: 999, padding: '0 7px', fontSize: 11.5 } }, c)),
          i < stages.length - 1 ? h('span', { style: { color: '#d5dae0', fontSize: 13 } }, '→') : null);
      }));
  }
  // one shared job card used by every department dashboard
  opsJobCard(j, tone) {
    const chan = { online: ['Online', 'neutral'], outlet: ['Outlet', 'amber'], outsourced: ['Outsourced', 'mag'] }[j.channel] || ['Online', 'neutral'];
    const acts = (j.actions || []).filter(a => a.permitted);
    const owner = j.owner && Object.keys(j.owner).length ? Object.keys(j.owner).map(k => k + ':' + j.owner[k]).join(' · ') : null;
    return h('div', { key: j.id, style: { border: '1px solid ' + (tone === 'action' ? TEAL : HAIR), borderRadius: 12, background: '#fff', padding: 15, display: 'flex', flexDirection: 'column', gap: 9 } },
      h('div', { style: { display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' } },
        h('span', { style: { font: '600 12px ui-monospace,Menlo,monospace', color: TEAL } }, j.id),
        this.chip(chan[0], chan[1]),
        h('span', { style: { marginLeft: 'auto' } }, this.chip(j.statusLabel || j.status, tone === 'action' ? 'bad' : 'teal'))),
      h('div', { style: { display: 'flex', gap: 12 } },
        h('div', { style: { flex: '0 0 74px' } }, this.art(j.product)),
        h('div', { style: { flex: 1, minWidth: 0 } },
          h('div', { style: { fontSize: 14, fontWeight: 600 } }, j.customer),
          h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.5 } }, this.catName(j.product ? (this.pkProducts().find(p => p.name === j.product) || {}).id : null) || j.product),
          h('div', { style: { fontSize: 12, color: FAINT, lineHeight: 1.5 } }, j.spec),
          h('div', { style: { fontSize: 12, color: FAINT, marginTop: 3 } }, this.money(j.price || 0) + ' · qty ' + (j.qty || 0).toLocaleString() + (j.paymentValidated ? ' · paid' : ' · unpaid')),
          (j.orderId && j.orderId.indexOf('PO-') === 0) ? h('span', { 'data-go': 'vieworder:' + j.orderId, style: { fontSize: 11.5, fontWeight: 600, color: TEAL, cursor: 'pointer' } }, 'Open order ' + j.orderId + ' →') : null)),
      owner && h('div', { style: { fontSize: 11.5, color: FAINT } }, 'Owner ' + owner),
      acts.length ? h('div', { style: { display: 'flex', gap: 7, flexWrap: 'wrap', borderTop: '1px solid ' + LINE, paddingTop: 10 } },
        acts.some(a => a.action === 'approve' || a.action === 'flag_minor')
          ? h('span', { key: 'review', onClick: () => this.setState({ reviewJob: j.id }), style: { fontSize: 12, fontWeight: 600, borderRadius: 7, padding: '7px 14px', cursor: 'pointer', border: '1px solid ' + TEAL, background: TEAL, color: '#fff' } }, 'Review file →')
          : acts.map(a => h('span', { key: a.action, onClick: a.enabled ? (() => this.opsAction(j, a)) : undefined,
            title: a.enabled ? a.note : (a.blockedBy || []).join(' '),
            style: { fontSize: 12, fontWeight: 600, borderRadius: 7, padding: '7px 12px', cursor: a.enabled ? 'pointer' : 'not-allowed',
              border: '1px solid ' + (a.enabled ? (a.action.indexOf('reject') === 0 || a.action === 'escalate' ? '#eaeaea' : TEAL) : '#eaeaea'),
              background: a.enabled ? (a.action.indexOf('reject') === 0 || a.action === 'escalate' ? '#fff' : TEAL) : '#f6f7f8',
              color: a.enabled ? (a.action.indexOf('reject') === 0 || a.action === 'escalate' ? MUT : '#fff') : '#b9c4cb' },
          }, a.action.replace(/_/g, ' ')))) : null,
      (acts.some(a => !a.enabled && a.blockedBy && a.blockedBy.length)) ? h('div', { style: { fontSize: 11, color: '#c0392b', lineHeight: 1.5 } }, acts.filter(a => !a.enabled && a.blockedBy && a.blockedBy.length).map(a => '⚠ ' + a.blockedBy.join(' ')).join(' ')) : null);
  }
  // Prepress file-check review popup — the guidebook's 3-step SOP + 4-status classifier,
  // wired to the live state machine.
  opsReviewDialog() {
    const jid = this.state.reviewJob; if (!jid) return null;
    const j = this.opsJobs().find(x => x.id === jid); if (!j) return null;
    const approveA = (j.actions || []).find(a => a.action === 'approve');
    const canApprove = approveA && approveA.enabled;
    const close = () => this.setState({ reviewJob: null, rejReason: null });
    const act = (action, payload) => { this.opsTransition(j.id, action, payload || {}); close(); };
    const reason = this.state.rejReason || 'Off-bleed';
    const REASONS = ['Off-bleed', 'Wrong dimensions', 'Low resolution (< 300 dpi)', 'RGB where CMYK expected', 'Fonts not embedded', 'Content / spelling issue', 'Risky die-cut', 'Pantone present'];
    // Step 2 Technical checks — demo results until real preflight is wired
    const CHECKS = [
      ['Basic', [['Product type matches file', 'pass'], ['Quantity correct', 'pass'], ['Size matches specs', j.artworkMatches ? 'pass' : 'fail']]],
      ['Technical', [['Resolution ≥ 300 dpi', 'pass'], ['Colour mode CMYK', 'warn'], ['Bleed ≥ 3 mm', j.artworkMatches ? 'pass' : 'fail'], ['Safe margin respected', 'warn'], ['Fonts outlined / embedded', 'pass'], ['No RGB / Pantone / white line', 'pass']]],
      ['Content', [['Missing fonts', 'pass'], ['Alignment', 'pass'], ['Cropping', 'pass']]],
    ];
    const dot = s => h('span', { style: { height: 8, width: 8, borderRadius: '50%', flex: 'none', background: s === 'pass' ? '#63AA02' : s === 'warn' ? '#d99100' : '#c71917' } });
    return h('div', { key: 'review', onClick: close, style: { position: 'fixed', inset: 0, zIndex: 90, background: 'rgba(15,20,25,.5)', display: 'grid', placeItems: 'center', padding: 20 } },
      h('div', { onClick: e => e.stopPropagation(), style: { background: '#fff', borderRadius: 14, maxWidth: 920, width: '100%', maxHeight: '90vh', overflow: 'auto', boxShadow: '0 24px 60px rgba(33,33,33,.30)' } },
        h('div', { style: { padding: '16px 20px', borderBottom: '1px solid ' + HAIR, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' } },
          h('span', { style: { font: '600 12px ui-monospace,Menlo,monospace', color: TEAL } }, j.id),
          h('span', { style: { fontSize: 15, fontWeight: 600 } }, j.customer + ' · file check'),
          this.chip(j.artwork && j.artwork.file || 'artwork.pdf', 'neutral'),
          h('span', { onClick: close, style: { marginLeft: 'auto', color: FAINT, fontSize: 20, cursor: 'pointer' } }, '×')),
        h('div', { style: { display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 320px' } },
          // artwork preview with trim / bleed / safe overlay
          h('div', { style: { padding: 20, background: '#FAFAFA' } },
            h('div', { style: { position: 'relative', paddingTop: '58%', background: '#fff', border: '1px dashed ' + (j.artworkMatches ? INK : '#c71917'), borderRadius: 2 } },
              h('div', { style: { position: 'absolute', inset: '7%', border: '1px solid ' + INK } },
                h('div', { style: { position: 'absolute', inset: '8%', border: '1px dashed #d99100' } })),
              !j.artworkMatches ? h('div', { style: { position: 'absolute', left: 0, right: 0, bottom: 0, height: '7%', background: 'repeating-linear-gradient(45deg,#fdecec,#fdecec 6px,#fff 6px,#fff 12px)' } }) : null),
            h('div', { style: { display: 'flex', gap: 8, marginTop: 12, fontSize: 11.5, color: MUT, flexWrap: 'wrap' } },
              [j.spec || 'trim', 'bleed 3 mm', 'safe 3 mm'].map((t, i) => h('span', { key: i, style: { border: '1px solid ' + HAIR, borderRadius: 6, padding: '3px 8px', background: '#fff' } }, t)))),
          // checklist + status + reason
          h('div', { style: { padding: 20, display: 'flex', flexDirection: 'column', gap: 14 } },
            CHECKS.map((grp, gi) => h('div', { key: gi },
              h('div', { style: { fontSize: 11, fontWeight: 600, letterSpacing: '.06em', textTransform: 'uppercase', color: FAINT, marginBottom: 6 } }, grp[0]),
              grp[1].map((c, ci) => h('div', { key: ci, style: { display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5, padding: '3px 0', color: MUT } }, dot(c[1]), c[0])))),
            !canApprove ? h('div', { style: { fontSize: 11.5, color: '#c0392b', lineHeight: 1.5, background: '#fdecec', border: '1px solid #f5c8c7', borderRadius: 8, padding: '8px 10px' } }, '⚠ ' + ((approveA && approveA.blockedBy) || ['Approval blocked.']).join(' ')) : null,
            h('div', null,
              h('div', { style: { fontSize: 12, fontWeight: 600, marginBottom: 6 } }, 'Rejection reason'),
              h('select', { value: reason, onChange: e => this.setState({ rejReason: e.target.value }), style: { font: '400 13px Montserrat,sans-serif', padding: '8px 10px', border: '1px solid ' + HAIR, borderRadius: 7, width: '100%' } },
                REASONS.map(r => h('option', { key: r, value: r }, r))),
              h('div', { style: { fontSize: 11, color: FAINT, marginTop: 5, lineHeight: 1.5 } }, 'Reject attaches the reason + a visual-proof screenshot and returns the job to the outlet.')))),
        h('div', { style: { padding: '14px 20px', borderTop: '1px solid ' + HAIR, display: 'flex', gap: 9, flexWrap: 'wrap', justifyContent: 'flex-end' } },
          h('span', { onClick: () => act('escalate', { reason: 'Critical — manager review' }), style: { fontSize: 13, fontWeight: 600, padding: '10px 16px', borderRadius: 8, border: '1px solid ' + HAIR, color: MUT, cursor: 'pointer' } }, 'Escalate (critical)'),
          h('span', { onClick: () => act('reject_major', { reason: reason, proof: 'proof-' + j.id + '.png' }), style: { fontSize: 13, fontWeight: 600, padding: '10px 16px', borderRadius: 8, border: '1px solid #f5c8c7', color: '#c71917', background: '#fff', cursor: 'pointer' } }, 'Reject → outlet'),
          h('span', { onClick: canApprove ? (() => act('approve')) : undefined, style: { fontSize: 13, fontWeight: 600, padding: '10px 20px', borderRadius: 8, border: '1px solid ' + (canApprove ? TEAL : '#eaeaea'), background: canApprove ? TEAL : '#f6f7f8', color: canApprove ? '#fff' : '#b9c4cb', cursor: canApprove ? 'pointer' : 'not-allowed' } }, 'Approve → Scheduler'))));
  }
  // fault-tolerant wrapper — a single bad job can never blank the whole dashboard
  opsCard(j, tone) {
    try { return this.opsJobCard(j, tone); }
    catch (e) {
      if (typeof window !== 'undefined') { window.__cardErr = (e && e.stack) || String(e); }
      return h('div', { key: j.id, style: { border: '1px solid ' + HAIR, borderRadius: 12, padding: 15, fontSize: 12.5, color: MUT } },
        h('span', { style: { font: '600 12px ui-monospace,Menlo,monospace', color: TEAL } }, j.id), ' · ', (j.customer || ''), ' — ', (j.statusLabel || j.status));
    }
  }
  // generic live department board (shell + pipeline + this queue's jobs)
  opsBoard(shellLabel, nav, active, dept, title, sub, opts) {
    opts = opts || {};
    const jobs = this.opsJobs();
    const mine = opts.showAll ? jobs : jobs.filter(j => j.queue === dept);
    return this.shell(shellLabel, nav, active, [
      this.head(title, sub, opts.actions),
      opts.top || null,
      opts.kpis || null,
      this.opsPipeline(dept),
      mine.length
        ? h('div', { key: 'jobs', style: { display: 'grid', gridTemplateColumns: opts.showAll ? 'repeat(auto-fill,minmax(300px,1fr))' : 'repeat(auto-fill,minmax(320px,1fr))', gap: 14 } },
          mine.map(j => this.opsCard(j, opts.tone)))
        : h('div', { key: 'empty', style: { border: '1px dashed ' + HAIR, borderRadius: 12, padding: 40, textAlign: 'center', color: FAINT, fontSize: 13 } }, this.state.ops && this.state.ops.loaded ? 'No jobs in this queue right now.' : 'Loading live jobs…'),
      opts.footer || null,
      this.opsReviewDialog(),
    ]);
  }
  catDefaults() { return (typeof window !== 'undefined' && window.PrintokaCatalogueDefaults) || { categories: [], overrides: {} }; }
  catCategories() { return this.catDefaults().categories; }
  catOverride(id) {
    return Object.assign({}, this.catDefaults().overrides[String(id)] || {}, (this.state.catOverrides || {})[String(id)] || {});
  }
  catName(id) { const o = this.catOverride(id); if (o.displayName) return o.displayName; const p = this.pkProducts().find(x => x.id === id); return p ? p.name : ''; }
  catCategoryOf(id) { return this.catOverride(id).categoryId || 'business-essentials'; }
  catCategoryLabel(cid) { const c = this.catCategories().find(x => x.id === cid); return c ? c.label : cid; }
  catProducts(categoryId) {
    return this.pkProducts()
      .filter(p => !this.catOverride(p.id).hidden)
      .filter(p => !categoryId || categoryId === 'all' || this.catCategoryOf(p.id) === categoryId)
      .map(p => ({ id: p.id, name: this.catName(p.id), engName: p.name, engine: p.engine, cat: this.catCategoryOf(p.id) }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }
  // persist an admin catalogue edit and reflect it immediately
  catSave(id, patch) {
    this.setState(s => ({ catOverrides: Object.assign({}, s.catOverrides, { [String(id)]: Object.assign({}, (s.catOverrides || {})[String(id)], patch) }) }));
    if (typeof fetch === 'function')
      fetch('/api/catalogue/' + id, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(patch) }).catch(() => {});
  }
  // minimum order quantity (moq) for a product, from the engine's quantity model
  catMoq(id) { const q = this.pkQtyObj(id); return q ? q.moq : null; }
  // "from" price per piece — the cheapest per-unit across the product's REAL quantity
  // options (so it matches the pricing calculator exactly, never a qty below moq). guarded.
  catFromPrice(id) {
    const E = this.pkEngine(); if (!E) return null;
    const prod = E.DATA.products.find(p => p.id === id); if (!prod) return null;
    const q = prod.quantity;
    let samples = (q && q.options && q.options.length) ? q.options.slice() : [100, 500, 1000];
    // sample a spread (min, some middles, max) to find the lowest available per-piece price
    if (samples.length > 6) { const pick = [0, Math.floor(samples.length / 3), Math.floor(2 * samples.length / 3), samples.length - 1]; samples = pick.map(i => samples[i]); }
    const save = this.state.prodId, saveCfg = this.state.cfg, saveQty = this.state.qty;
    this.state.prodId = id; this.state.cfg = {};
    let best = null;
    // price via pkQuote so the "from" price follows the same source as the configurator
    // (captured Excard cash where a product has priceBase, e.g. Business Card), not the raw engine.
    try { for (const qn of samples) { try { this.state.qty = qn; const r = this.pkQuote(qn); if (r && r.ok && r.gross > 0 && (best == null || r.gross / qn < best)) best = r.gross / qn; } catch (e) {} } } catch (e) {}
    this.state.prodId = save; this.state.cfg = saveCfg; this.state.qty = saveQty;
    return best;
  }

  // ---------- shared bits ----------
  art(kind, w) {
    const BY_NAME = {
      'Business Card': 'business-card.jpg', 'Kad Kahwin — Digital': 'greeting-cards.png',
      'Greeting Card — Litho': 'greeting-cards.png', 'Creative Cut Card — Digital': 'die-cut-card.png',
      'PVC Card — Digital': 'digital-cards.png', 'ID Card — Digital': 'key-card-holder.jpg',
      'Tent Card — Litho': 'folded-business-card.png', 'Voucher — Litho': 'voucher-book.jpg',
      'Bill Book (NCR)': 'computer-form.png', 'Letterhead': 'letterhead.jpg',
      'Booklet — Litho': 'booklet.jpg', 'Booklet — Litho (Offset)': 'booklet.jpg',
      'Notepad': 'business-documents.jpg', 'Label Sticker — Digital': 'car-sticker-single.png',
      'Roll Label': 'cards.jpg', 'Car Sticker': 'car-stickers.jpg', 'UV DTF Sticker': 'car-stickers.jpg',
      'Flyer': 'flyers.jpg', 'Banner — Litho': 'hanging-banners.jpg', 'Roll-up Stand': 'brochures.jpg',
      'Bunting': 'hanging-banners.jpg', 'Foamboard': 'hardcover-booklet.png',
      'Folding Carton': 'gift-boxes.jpg', 'Folding Carton (67 styles)': 'gift-boxes.jpg',
      'Paper Bag — Litho': 'tote-bags.jpg', 'Standing Pouch': 'envelope.jpg', 'Food Tray': 'gift-boxes.jpg',
      'Mug — Litho': 'button-badge.png', 'Wall Calendar': 'table-calendar.jpg',
      'Desk Calendar': 'folded-menu.png', 'Money Packet': 'folded-cards.jpg',
    };
    const BY_KIND = { card: 'business-card.jpg', sticker: 'car-sticker-single.png', flyer: 'flyers.jpg',
      book: 'booklet.jpg', banner: 'hanging-banners.jpg', box: 'gift-boxes.jpg',
      cal: 'table-calendar.jpg', mug: 'tote-bags.jpg' };
    const file = BY_NAME[kind] || BY_KIND[kind] || 'cards.jpg';
    const alt = (typeof kind === 'string' && BY_NAME[kind]) ? (kind + ' printing') : 'Printoka custom printing product';
    return React.createElement('img', {
      src: window.__asset('assets/products/' + file), alt: alt, loading: 'lazy',
      style: { width: w || '100%', aspectRatio: '4 / 3', objectFit: 'contain', display: 'block', background: '#fff' },
    });
  }
  sec(kicker, title, sub, children, opts) {
    const o = opts || {};
    return h('section', { style: { background: o.alt ? ALT : '#fff', padding: '46px 0' } },
      h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '0 20px' } },
        kicker && h('div', { style: { fontSize: 11.5, fontWeight: 600, letterSpacing: '.09em', textTransform: 'uppercase', color: TEAL, marginBottom: 7 } }, kicker),
        title && h('h2', { style: { margin: '0 0 8px', fontSize: 28, fontWeight: 600, letterSpacing: '-.02em' } }, title),
        sub && h('p', { style: { margin: '0 0 26px', color: MUT, fontSize: 14.5, maxWidth: '68ch', lineHeight: 1.7 } }, sub),
        children));
  }

  btn(label, kind, go, extra) {
    const st = { display: 'inline-flex', alignItems: 'center', gap: 8, borderRadius: 8, padding: '11px 20px', fontSize: 14, fontWeight: 600, border: '1px solid transparent', cursor: 'pointer', fontFamily: 'Montserrat,sans-serif', whiteSpace: 'nowrap' };
    if (kind === 'amber') Object.assign(st, { background: AMBER, color: '#3a2c00' });
    else if (kind === 'teal') Object.assign(st, { background: TEAL, color: '#fff' });
    else Object.assign(st, { background: '#fff', color: TEAL, borderColor: '#eaeaea' });
    return h('span', { 'data-go': go || 'product', style: Object.assign(st, extra || {}) }, label);
  }

  chip(text, tone) {
    const MAP = {
      ok: ['#e6f4ea', '#63AA02'], warn: ['#fff5e2', '#a1660a'], bad: ['#fdecec', '#c71917'],
      teal: [CHIP, '#616161'], neutral: ['#f1f3f5', '#6c757d'], amber: ['#fff8e6', '#8a6d1f'],
      mag: ['#fdeaf3', '#a30052'],
    };
    // never let an unknown/non-string tone crash a whole screen — fall back to neutral
    const T = MAP[tone] || MAP.neutral;
    return h('span', { style: { background: T[0], color: T[1], fontSize: 11.5, fontWeight: 600, borderRadius: 5, padding: '3px 9px', whiteSpace: 'nowrap' } }, text);
  }

  card(children, extra) {
    return h('div', { style: Object.assign({ border: '1px solid ' + HAIR, borderRadius: 12, background: '#fff', padding: 18 }, extra || {}) }, children);
  }

  kpi(label, value, note, tone) {
    return this.card([
      h('div', { key: 'l', style: { fontSize: 11.5, fontWeight: 600, letterSpacing: '.06em', textTransform: 'uppercase', color: FAINT } }, label),
      h('div', { key: 'v', style: { fontSize: 'clamp(20px,2.2vw,30px)', fontWeight: 600, letterSpacing: '-.02em', margin: '6px 0 2px', color: tone || INK, whiteSpace: 'nowrap' } }, value),
      note && h('div', { key: 'n', style: { fontSize: 12.5, color: MUT } }, note),
    ]);
  }

  table(headers, rows, widths) {
    return h('div', { style: { border: '1px solid ' + HAIR, borderRadius: 12, overflow: 'hidden', background: '#fff' } },
      h('table', { style: { width: '100%', borderCollapse: 'collapse', fontSize: 13 } },
        h('thead', null, h('tr', { style: { background: ALT } }, headers.map((hd, i) =>
          h('th', { key: i, style: { textAlign: 'left', padding: '11px 14px', fontSize: 11, fontWeight: 600, letterSpacing: '.07em', textTransform: 'uppercase', color: FAINT, borderBottom: '1px solid ' + HAIR, width: widths && widths[i] } }, hd)))),
        h('tbody', null, rows.map((r, i) =>
          h('tr', { key: i, style: { borderBottom: i === rows.length - 1 ? 'none' : '1px solid ' + LINE } },
            r.map((c, j) => h('td', { key: j, style: { padding: '12px 14px', color: j === 0 ? INK : MUT, fontWeight: j === 0 ? 500 : 400, verticalAlign: 'middle' } }, c)))))));
  }

  mobileBar(label, price, cta, go) {
    return h('div', { className: 'pk-mobilebar', style: { position: 'fixed', left: 0, right: 0, bottom: 0, zIndex: 80, background: '#fff', borderTop: '1px solid ' + HAIR, boxShadow: '0 -2px 14px rgba(33,33,33,.10)', padding: '10px 16px', alignItems: 'center', gap: 12 } },
      h('div', { style: { minWidth: 0, flex: 1 } },
        h('div', { style: { fontSize: 11.5, color: FAINT, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' } }, label),
        h('div', { style: { fontSize: 17, fontWeight: 600, color: TEAL } }, price)),
      h('span', { 'data-go': go, style: { flex: 'none', background: TEAL, color: '#fff', fontSize: 14, fontWeight: 600, borderRadius: 2, padding: '11px 20px', cursor: 'pointer' } }, cta));
  }

  // ---------- app shell for role dashboards ----------
  shell(role, navItems, active, children) {
    return h('div', { 'data-shell': '1', style: { maxWidth: 1180, margin: '0 auto', padding: '10px 20px 0', display: 'grid', gridTemplateColumns: '218px minmax(0,1fr)', gap: 22, alignItems: 'start' } },
      h('aside', { style: { border: '1px solid ' + HAIR, borderRadius: 12, padding: 14, background: '#fff', position: 'sticky', top: 120 } },
        h('div', { style: { fontSize: 11, fontWeight: 600, letterSpacing: '.08em', textTransform: 'uppercase', color: FAINT, padding: '2px 6px 10px' } }, role),
        navItems.map((n, i) => {
          const label = Array.isArray(n) ? n[0] : n, on = label === active;
          if (Array.isArray(n) && n[2] === '__group') return h('div', { key: i, style: { fontSize: 10, fontWeight: 700, letterSpacing: '.09em', textTransform: 'uppercase', color: FAINT, padding: i ? '14px 6px 5px' : '2px 6px 5px', borderTop: i ? '1px solid ' + LINE : 'none', marginTop: i ? 4 : 0 } }, label);
          return h('div', { key: i, 'data-go': Array.isArray(n) && n[2] ? n[2] : undefined, style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, padding: '8px 10px', borderRadius: 8, fontSize: 13, fontWeight: on ? 600 : 400, color: on ? TEAL : MUT, background: on ? CHIP : 'transparent', cursor: Array.isArray(n) && n[2] ? 'pointer' : 'default' } },
            h('span', null, label), Array.isArray(n) && n[1] ? this.chip(n[1], 'bad') : null);
        })),
      h('div', { style: { minWidth: 0, display: 'flex', flexDirection: 'column', gap: 20 } }, children));
  }

  head(title, sub, actions) {
    return h('div', { style: { display: 'flex', alignItems: 'flex-end', gap: 16, flexWrap: 'wrap' } },
      h('div', { style: { flex: '1 1 320px', minWidth: 0 } },
        h('h1', { style: { margin: '0 0 5px', fontSize: 25, fontWeight: 600, letterSpacing: '-.02em' } }, title),
        h('p', { style: { margin: 0, fontSize: 13.5, color: MUT, maxWidth: '76ch', lineHeight: 1.65 } }, sub)),
      actions && h('div', { style: { display: 'flex', gap: 9, flexWrap: 'wrap' } }, actions));
  }

  // ============================================================================
  // Staff-console aesthetic (mirrors the original outlet dashboard):
  // top-nav + identity header, icon stat cards, SVG line charts, filter tables.
  // ============================================================================
  accent(name) {
    // [icon colour, soft circle background]
    return ({ teal: ['#12B3A6', '#e1f5f2'], red: ['#E52220', '#fde3e1'], orange: ['#F08B1D', '#ffedd6'], blue: ['#2f7fd1', '#e2eefb'] })[name] || ['#12B3A6', '#e1f5f2'];
  }
  dashIcon(name, hex, size) {
    const D = {
      'edit-3': ['M12 20h9', 'M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z'],
      file: ['M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z', 'M13 2v7h7'],
      check: ['M20 6 9 17l-5-5'],
      truck: ['M1 3h15v13H1z', 'M16 8h4l3 3v5h-7', 'M5.5 18.5a2.5 2.5 0 1 0 0-.01', 'M18.5 18.5a2.5 2.5 0 1 0 0-.01'],
      'dollar-sign': ['M12 1v22', 'M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6'],
      'user-plus': ['M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2', 'M8.5 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z', 'M20 8v6', 'M23 11h-6'],
      phone: ['M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z'],
      printer: ['M6 9V2h12v7', 'M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2', 'M6 14h12v8H6z'],
      box: ['M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z', 'M3.3 7 12 12l8.7-5', 'M12 22V12'],
      layers: ['M12 2 2 7l10 5 10-5z', 'M2 17l10 5 10-5', 'M2 12l10 5 10-5'],
      clock: ['M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z', 'M12 6v6l4 2'],
      sliders: ['M4 21v-7', 'M4 10V3', 'M12 21v-9', 'M12 8V3', 'M20 21v-5', 'M20 12V3', 'M1 14h6', 'M9 8h6', 'M17 16h6'],
      upload: ['M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4', 'M17 8l-5-5-5 5', 'M12 3v12'],
      'credit-card': ['M1 4h22v16H1z', 'M1 10h22'],
    };
    const paths = D[name] || D.check;
    const s = size || 22;
    return h('svg', { width: s, height: s, viewBox: '0 0 24 24', fill: 'none', stroke: hex, strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' }, paths.map((d, i) => h('path', { key: i, d })));
  }
  metricBadge(change) {
    if (change == null || change === '') return null;
    let bg = '#eef1f4', col = '#6c757d', txt = String(change);
    if (change === 'New') { bg = '#e6f4ea'; col = '#3d8b40'; }
    else if (change === 'N/A' || change === '—') { bg = '#eef1f4'; col = '#8a9199'; }
    else if (/^\+/.test(txt)) { bg = '#e6f4ea'; col = '#3d8b40'; }
    else if (/^-/.test(txt)) { bg = '#fde3e1'; col = '#c71917'; }
    return h('span', { style: { background: bg, color: col, fontSize: 11, fontWeight: 700, borderRadius: 6, padding: '2px 7px', whiteSpace: 'nowrap' } }, txt);
  }
  // dashboard stat / metric card with a soft-circle icon (opts: badge, note, icon, accent, go)
  statCard(label, value, o) {
    o = o || {};
    const A = this.accent(o.accent || 'teal');
    const inner = h('div', { style: { display: 'flex', alignItems: 'center', gap: 12, position: 'relative', minHeight: 44 } },
      h('div', { style: { flex: 1, minWidth: 0 } },
        h('div', { style: { fontSize: 13, fontWeight: 600, color: INK, marginBottom: 6 } }, label),
        h('div', { style: { display: 'flex', alignItems: 'center', gap: 8 } },
          h('span', { style: { fontSize: 27, fontWeight: 700, letterSpacing: '-.02em', lineHeight: 1 } }, value),
          o.dot ? h('span', { style: { height: 7, width: 7, borderRadius: '50%', background: '#E52220' } }) : null,
          this.metricBadge(o.badge)),
        o.note ? h('div', { style: { fontSize: 12, color: FAINT, marginTop: 6 } }, o.note) : null),
      o.icon ? h('div', { style: { flex: 'none', height: 44, width: 44, borderRadius: '50%', background: A[1], display: 'grid', placeItems: 'center' } }, this.dashIcon(o.icon, A[0], 20)) : null);
    return h('div', { key: label, 'data-go': o.go || undefined, style: { background: '#fff', padding: '18px 18px', cursor: o.go ? 'pointer' : 'default' } }, inner);
  }
  // SVG line chart matching the original (gridlines, month labels, value labels above points)
  lineChart(labels, values, o) {
    o = o || {}; const H = o.h || 300, W = 1000, padL = 42, padR = 20, padT = 26, padB = 28;
    const n = Math.max(1, values.length);
    const rawMax = Math.max.apply(null, values.concat([0]));
    const max = rawMax <= 0 ? 1 : Math.ceil(rawMax * 1.1);
    const X = i => padL + i * ((W - padL - padR) / Math.max(1, n - 1));
    const Y = v => padT + (1 - v / max) * (H - padT - padB);
    const steps = 10;
    const grid = []; for (let s = 0; s <= steps; s++) { const gv = (max / steps) * s, gy = Y(gv); grid.push(h('line', { key: 'g' + s, x1: padL, y1: gy, x2: W - padR, y2: gy, stroke: '#eef1f4', strokeWidth: 1 })); grid.push(h('text', { key: 'gl' + s, x: padL - 8, y: gy + 3, textAnchor: 'end', fontSize: 11, fill: '#9aa4ad' }, (Math.round(gv * 100) / 100).toString())); }
    const pts = values.map((v, i) => [X(i), Y(v)]);
    const dPath = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
    return h('div', { style: { width: '100%', overflowX: 'auto' } },
      h('svg', { viewBox: '0 0 ' + W + ' ' + H, width: '100%', height: H, preserveAspectRatio: 'none', style: { display: 'block', minWidth: 620 } },
        grid,
        h('path', { d: dPath, fill: 'none', stroke: 'url(#lc)', strokeWidth: 3, strokeLinecap: 'round', strokeLinejoin: 'round' }),
        h('defs', null, h('linearGradient', { id: 'lc', x1: '0', y1: '0', x2: '1', y2: '0' }, h('stop', { offset: '0', stopColor: '#12B3A6' }), h('stop', { offset: '1', stopColor: '#2f7fd1' }))),
        pts.map((p, i) => h('circle', { key: 'c' + i, cx: p[0], cy: p[1], r: 5, fill: '#2f7fd1' })),
        pts.map((p, i) => h('text', { key: 't' + i, x: p[0], y: p[1] - 12, textAnchor: 'middle', fontSize: 12, fontWeight: 600, fill: '#4a5560' }, (Math.round(values[i] * 100) / 100).toFixed(2))),
        labels.map((l, i) => h('text', { key: 'x' + i, x: X(i), y: H - 8, textAnchor: 'middle', fontSize: 12, fill: '#9aa4ad' }, l))));
  }
  // original-site brand mark + wordmark (same asset & weight as the storefront header) — standardised
  brandLogo() {
    return h('div', { style: { display: 'flex', alignItems: 'center', gap: 9 } },
      h('img', { src: window.__asset('assets/icons/logomark.svg'), alt: '', style: { height: 26, width: 'auto', display: 'block', flex: 'none' } }),
      h('span', { style: { fontSize: 18, fontWeight: 500, letterSpacing: '.16em', color: '#231f20' } }, 'printoka'));
  }
  // white top-nav shell for staff dashboards (logo · tabs · identity), then a light-grey page
  staffPage(tabs, active, identity, children) {
    const nav = h('header', { style: { background: '#fff', borderBottom: '1px solid ' + HAIR } },
      h('div', { style: { maxWidth: 1280, margin: '0 auto', padding: '0 24px', display: 'flex', alignItems: 'center', gap: 20, minHeight: 64 } },
        this.brandLogo(),
        h('nav', { style: { display: 'flex', gap: 4, marginLeft: 18, flexWrap: 'wrap', flex: 1 } },
          tabs.map(t => { const on = t === active; return h('span', { key: t, 'data-go': 'set:sTab:' + t, style: { position: 'relative', fontSize: 14, fontWeight: on ? 600 : 500, color: on ? INK : MUT, padding: '20px 10px', cursor: 'pointer', borderBottom: '3px solid ' + (on ? '#E52220' : 'transparent') } }, t); })),
        identity ? h('div', { style: { display: 'flex', alignItems: 'center', gap: 10 } },
          h('span', { style: { height: 34, width: 34, borderRadius: '50%', background: '#e1f5f2', display: 'grid', placeItems: 'center' } }, this.dashIcon('printer', '#12B3A6', 18)),
          h('div', { style: { lineHeight: 1.25 } }, h('div', { style: { fontSize: 13.5, fontWeight: 700 } }, identity.title), identity.sub ? h('div', { style: { fontSize: 12, color: FAINT } }, identity.sub) : null)) : null));
    return h('div', { style: { background: '#f4f5f6', minHeight: '100vh' } }, nav,
      h('div', { style: { maxWidth: 1280, margin: '0 auto', padding: '26px 24px 60px', display: 'flex', flexDirection: 'column', gap: 20 } }, children));
  }
  // customer console: a secondary tab-bar UNDER the storefront header (keeps site chrome)
  customerPage(tabs, active, children) {
    const bar = h('div', { style: { background: '#fff', borderBottom: '1px solid ' + HAIR } },
      h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '0 20px', display: 'flex', gap: 6, flexWrap: 'wrap' } },
        tabs.map(t => { const on = t === active; return h('span', { key: t, 'data-go': 'set:cTab:' + t, style: { fontSize: 14, fontWeight: on ? 600 : 500, color: on ? INK : MUT, padding: '18px 12px', cursor: 'pointer', borderBottom: '3px solid ' + (on ? '#E52220' : 'transparent') } }, t); })));
    return h('div', { style: { background: '#f4f5f6' } }, bar,
      h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '26px 20px 60px', display: 'flex', flexDirection: 'column', gap: 20 } }, children),
      this.walletModal(), this.passwordModal());
  }
  walletModal() {
    if (!this.state.tu_open) return null;
    const close = () => this.setState({ tu_open: false, tu_err: null });
    return h('div', { key: 'tu', onClick: close, style: { position: 'fixed', inset: 0, zIndex: 96, background: 'rgba(20,25,30,.45)', display: 'grid', placeItems: 'start center', padding: 20, overflow: 'auto' } },
      h('div', { onClick: e => e.stopPropagation(), style: { background: '#fff', borderRadius: 14, maxWidth: 520, width: '100%', margin: '40px 0', overflow: 'hidden', boxShadow: '0 24px 60px rgba(33,33,33,.3)' } },
        h('div', { style: { height: 4, background: '#E52220' } }),
        h('div', { style: { padding: '20px 26px 26px' } },
          h('div', { style: { display: 'flex', alignItems: 'center', marginBottom: 16 } }, h('span', { style: { fontSize: 20, fontWeight: 600 } }, 'Wallet top-up'), h('span', { onClick: close, style: { marginLeft: 'auto', color: FAINT, fontSize: 22, cursor: 'pointer' } }, '×')),
          h('div', { style: { fontSize: 13, fontWeight: 600, marginBottom: 6 } }, 'Top Up Amount ', h('span', { style: { color: '#E52220' } }, '*')),
          h('div', { style: { display: 'flex', border: '1px solid ' + HAIR, borderRadius: 8, overflow: 'hidden', marginBottom: 8 } },
            h('span', { style: { background: ALT, padding: '10px 12px', fontSize: 13, color: MUT, borderRight: '1px solid ' + HAIR } }, this.currency()),
            h('input', { type: 'number', value: this.state.tu_amount || '', onChange: e => this.setField('tu_amount', e.target.value), style: { border: 'none', outline: 'none', padding: '10px 12px', font: '400 14px Montserrat,sans-serif', flex: 1 } })),
          this.state.tu_err ? h('div', { style: { fontSize: 12.5, color: '#c0392b', marginBottom: 8 } }, this.state.tu_err) : null,
          h('span', { onClick: () => this.walletTopUp(), style: { display: 'block', textAlign: 'center', background: '#E52220', color: '#fff', fontWeight: 600, fontSize: 15, padding: '12px', borderRadius: 999, cursor: this.state.tu_busy ? 'wait' : 'pointer' } }, this.state.tu_busy ? 'Processing…' : 'Proceed'))));
  }
  passwordModal() {
    if (!this.state.pw_open) return null;
    const close = () => this.setState({ pw_open: false, pw_err: null });
    const fld = (label, key) => h('div', null, h('div', { style: { fontSize: 13, fontWeight: 600, marginBottom: 6 } }, label), h('input', { type: 'password', placeholder: label === 'Current Password' ? 'Please enter your current password' : '', value: this.state[key] || '', onChange: e => this.setField(key, e.target.value), style: { font: '400 14px Montserrat,sans-serif', padding: '10px 12px', border: '1px solid ' + HAIR, borderRadius: 8, width: '100%' } }));
    return h('div', { key: 'pw', onClick: close, style: { position: 'fixed', inset: 0, zIndex: 96, background: 'rgba(20,25,30,.45)', display: 'grid', placeItems: 'start center', padding: 20, overflow: 'auto' } },
      h('div', { onClick: e => e.stopPropagation(), style: { background: '#fff', borderRadius: 14, maxWidth: 640, width: '100%', margin: '40px 0', overflow: 'hidden', boxShadow: '0 24px 60px rgba(33,33,33,.3)' } },
        h('div', { style: { height: 4, background: '#E52220' } }),
        h('div', { style: { padding: '20px 26px 26px' } },
          h('div', { style: { display: 'flex', alignItems: 'center', marginBottom: 16 } }, h('span', { style: { fontSize: 20, fontWeight: 600 } }, 'Change Password'), h('span', { onClick: close, style: { marginLeft: 'auto', color: FAINT, fontSize: 22, cursor: 'pointer' } }, '×')),
          h('div', { style: { display: 'flex', flexDirection: 'column', gap: 14 } },
            fld('Current Password', 'pw_current'),
            h('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 } }, fld('New Password', 'pw_next'), fld('Confirm new password', 'pw_confirm')),
            this.state.pw_err ? h('div', { style: { fontSize: 12.5, color: '#c0392b' } }, this.state.pw_err) : null,
            h('span', { onClick: () => this.submitPassword(), style: { alignSelf: 'flex-start', background: '#E52220', color: '#fff', fontWeight: 600, fontSize: 14, padding: '11px 26px', borderRadius: 999, cursor: this.state.pw_busy ? 'wait' : 'pointer' } }, this.state.pw_busy ? 'Saving…' : 'Update password')))));
  }
  // filter row (search · date · status · reset) + optional trailing action, matching the original
  filterRow(o) {
    o = o || {}; const sel = { font: '400 13.5px Montserrat,sans-serif', padding: '9px 12px', border: '1px solid ' + HAIR, borderRadius: 999, background: '#fff', color: MUT, cursor: 'pointer' };
    return h('div', { style: { display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 4 } },
      h('div', { style: { display: 'flex', alignItems: 'center', gap: 8, border: '1px solid ' + HAIR, borderRadius: 999, padding: '8px 14px', background: '#fff', flex: '0 1 300px' } },
        h('span', { style: { color: FAINT, fontSize: 14 } }, '⌕'),
        h('input', { placeholder: 'Search', value: this.state[o.searchKey] || '', onChange: e => this.setField(o.searchKey, e.target.value), style: { border: 'none', outline: 'none', font: '400 13.5px Montserrat,sans-serif', width: '100%', background: 'transparent' } })),
      h('select', { value: this.state[o.dateKey] || 'All dates', onChange: e => this.setField(o.dateKey, e.target.value), style: sel }, ['All dates', 'Last 7 days', 'Last 30 days', 'Last 6 months'].map(x => h('option', { key: x }, x))),
      o.statuses ? h('select', { value: this.state[o.statusKey] || 'All status', onChange: e => this.setField(o.statusKey, e.target.value), style: sel }, ['All status'].concat(o.statuses).map(x => h('option', { key: x }, x))) : null,
      h('span', { onClick: () => this.setState({ [o.searchKey]: '', [o.dateKey]: 'All dates', [o.statusKey]: 'All status' }), style: { display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 13.5, fontWeight: 600, color: '#E52220', cursor: 'pointer' } }, '↺ Reset'),
      o.action ? h('span', { style: { marginLeft: 'auto' } }, o.action) : null);
  }
  // white card table with header, empty-state and "Rows a–b of n" footer
  dataCard(cols, rows, o) {
    o = o || {};
    return h('div', null,
      h('div', { style: { background: '#fff', borderRadius: 12, border: '1px solid ' + HAIR, overflow: 'hidden' } },
        h('div', { style: { overflowX: 'auto' } },
          h('table', { style: { width: '100%', borderCollapse: 'collapse', fontSize: 13.5, minWidth: o.minWidth || 640 } },
            h('thead', null, h('tr', null, cols.map((c, i) => { const isObj = c && typeof c === 'object'; return h('th', { key: i, style: { textAlign: (isObj && c.right) ? 'right' : 'left', padding: '14px 18px', fontSize: 12.5, fontWeight: 700, color: INK, borderBottom: '1px solid ' + HAIR, whiteSpace: 'nowrap' } }, isObj ? (c.label || '') : c); }))),
            h('tbody', null, rows.length ? rows.map((r, i) => h('tr', { key: i, style: { borderBottom: i === rows.length - 1 ? 'none' : '1px solid ' + LINE } },
              r.map((cell, j) => h('td', { key: j, style: { padding: '16px 18px', color: j === 0 ? INK : MUT, textAlign: (cols[j] && cols[j].right) ? 'right' : 'left', whiteSpace: (cols[j] && cols[j].nowrap) ? 'nowrap' : 'normal' } }, cell)))) :
              h('tr', null, h('td', { colSpan: cols.length, style: { padding: '22px 18px', color: FAINT, fontSize: 13.5 } }, o.empty || 'No data available in table'))))),
      ),
      h('div', { style: { display: 'flex', alignItems: 'center', marginTop: 12, fontSize: 12.5, color: FAINT } },
        h('span', null, rows.length ? 'Rows 1–' + rows.length + ' of ' + rows.length : 'Showing 0 to 0 of 0 entries'),
        h('span', { style: { marginLeft: 'auto', display: 'flex', gap: 4, alignItems: 'center' } },
          h('span', { style: { border: '1px solid ' + HAIR, borderRadius: 8, padding: '5px 9px', color: FAINT } }, '‹'),
          rows.length ? h('span', { style: { border: '1px solid #E52220', color: '#E52220', borderRadius: 8, padding: '5px 11px', fontWeight: 700 } }, '1') : null,
          h('span', { style: { border: '1px solid ' + HAIR, borderRadius: 8, padding: '5px 9px', color: FAINT } }, '›'))));
  }
  // pill with a leading status dot (original "+pill_dot")
  pillDot(text, tone) {
    const T = ({ ok: '#3d8b40', warn: '#d99100', bad: '#c71917', teal: '#12B3A6', neutral: '#8a9199' })[tone] || '#8a9199';
    return h('span', { style: { display: 'inline-flex', alignItems: 'center', gap: 7, background: '#f6f7f8', borderRadius: 999, padding: '5px 12px', fontSize: 12.5, fontWeight: 600, color: INK, whiteSpace: 'nowrap' } },
      h('span', { style: { height: 7, width: 7, borderRadius: '50%', background: T } }), text);
  }
  // shared production/vendor "Dashboard" tab: stat cards + throughput chart + notifications
  opsStatGrid(cards) {
    return h('div', { style: { background: '#fff', borderRadius: 12, border: '1px solid ' + HAIR, overflow: 'hidden' } },
      h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 1, background: HAIR } },
        cards.map(c => this.statCard(c[0], String(c[1]), { icon: c[2], accent: c[3], note: c[4], badge: c[5], dot: c[6] }))));
  }
  opsDashTab(cards, chartLabel) {
    const MONTHS = ['APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP'];
    return [
      this.opsStatGrid(cards),
      h('div', { key: 'ch', style: { background: '#fff', borderRadius: 12, border: '1px solid ' + HAIR, padding: 20 } },
        h('div', { style: { fontSize: 13, fontWeight: 600, color: MUT, marginBottom: 2 } }, chartLabel || 'Throughput'),
        h('div', { style: { display: 'flex', alignItems: 'center', gap: 8 } }, h('span', { style: { fontSize: 26, fontWeight: 700 } }, '0'), this.metricBadge('N/A')),
        h('div', { style: { marginTop: 14 } }, this.lineChart(MONTHS, [0, 0, 0, 0, 0, 0], { h: 280 }))),
      this.notifPanel(),
    ];
  }
  // shared "Queue" tab: pipeline + live job cards + the prepress review dialog
  opsQueueTab(dept, tone) {
    const jobs = this.opsJobs(), mine = jobs.filter(j => j.queue === dept);
    return [
      this.opsPipeline(dept),
      mine.length
        ? h('div', { key: 'jobs', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(320px,1fr))', gap: 14 } }, mine.map(j => this.opsCard(j, tone)))
        : h('div', { key: 'empty', style: { border: '1px dashed ' + HAIR, borderRadius: 12, padding: 40, textAlign: 'center', color: FAINT, fontSize: 13, background: '#fff' } }, this.state.ops && this.state.ops.loaded ? 'No jobs in this queue right now.' : 'Loading live jobs…'),
      this.opsReviewDialog(),
    ];
  }

  renderVals() {
    const s = this.state;
    const cur = SCREENS.find(x => x[0] === s.route) || SCREENS[0];
    return {
      onNav: this.onNav,
      tProducts: this.t('products'),
      tSearch: this.t('search'),
      tMenu: this.t('menu'),
      localeLabel: this.loc(),
      megaOpen: s.megaOpen,
      cartCount: s.cartCount,
      showSpec: false,
      staff: this.userType() !== 'guest' && this.userType() !== 'customer',
      // the 5 role dashboards render their own white top-nav (staffPage) — hide the storefront header.
      // use the EFFECTIVE route (same redirect renderScreen applies) so a not-yet-synced route still counts.
      bareStaff: ['outlet', 'prepress', 'production', 'logistics', 'vendor'].indexOf(this.canAccess(this.state.route) ? this.state.route : this.homeFor()) >= 0,
      signedIn: !!this.state.user,
      userName: this.state.user ? this.state.user.name : '',
      tierLabel: this.tier().toUpperCase(),
      countryLabel: this.cc(),
      isMY: this.cc() === 'MY',
      isSG: this.cc() === 'SG',
      isBN: this.cc() === 'BN',
      specId: cur[2] + ' · ' + cur[1],
      specNote: cur[3],
      screens: SCREENS.map(x => ({ id: x[0], label: x[1] })),
      payments: ['Stripe', 'iPay88', 'FPX', "Touch 'n Go", 'PayNow', 'GrabPay'],
      megaCols: this.catCategories().map(c => { const go = c.id === 'packaging-boxes' ? 'packaging' : 'catopen:' + c.id; return {
        title: c.label,
        go,
        href: this.navHref(go),
        items: this.catProducts(c.id).slice(0, 7).map(pr => ({ n: pr.name, go: 'open:' + pr.id, href: this.productPath(pr.id) })),
      }; }),
      footerCols: [
        { title: 'Products', items: [['Business cards', 'category'], ['Stickers & labels', 'category'], ['Flyers & brochures', 'category'], ['Booklets', 'category'], ['Packaging & boxes', 'packaging'], ['Apparel & gifts', 'category']] },
        { title: 'Company', items: [['About Printoka', 'about'], ['Corporate accounts', 'corporate'], ['Partners', 'partners'], ['Membership', 'membership'], ['Terms & policies', 'terms']] },
        { title: 'Support', items: [['Artwork guides', 'learn'], ['Template downloads', 'downloads'], ['Track an order', 'track'], ['Contact us', 'contact'], ['Support & FAQ', 'support'], ['Terms', 'terms']] },
      ],
      activeRoute: this.state.route,
      announcement: (this.state.settings && this.state.settings.announcement) || undefined,
      screen: this.renderScreen(),
    };
  }

  // ---------- role-based access: each role is a separate, independent area ----------
  userType() { return (this.state.user && this.state.user.type) || 'guest'; }
  userRole() { return (this.state.user && this.state.user.role) || 'guest'; }
  access() {
    const STORE = ['home', 'category', 'product', 'packaging', 'artwork', 'cart', 'checkout', 'learn', 'article', 'seo', 'membership', 'contact', 'search', 'about', 'auth', 'confirm', 'track', 'corporate', 'partners', 'support', 'downloads', 'terms'];
    const type = this.userType(), role = this.userRole();
    if (type === 'guest') return STORE;
    if (type === 'customer') return STORE.concat(['dash', 'invoices']);
    if (type === 'admin') return STORE.concat(['dash', 'invoices', 'admin', 'outlet', 'prepress', 'production', 'logistics', 'vendor', 'crm']);
    if (type === 'outlet') return ['outlet', 'product', 'packaging', 'category', 'search', 'cart', 'checkout', 'track', 'crm', 'artwork', 'confirm', 'auth'];
    if (type === 'vendor' || type === 'hub') return ['vendor', 'auth'];
    if (type === 'production') return ({
      prepress: ['prepress', 'artwork', 'auth'],
      scheduler: ['production', 'vendor', 'artwork', 'auth'],
      logistics: ['logistics', 'artwork', 'auth'],
      production_manager: ['prepress', 'production', 'logistics', 'vendor', 'artwork', 'auth'],
    }[role] || ['prepress', 'auth']);
    return STORE;
  }
  canAccess(route) { return this.access().indexOf(route) !== -1; }
  homeFor(u) {
    u = u || this.state.user || {};
    const type = u.type || 'guest', role = u.role;
    if (type === 'admin') return 'admin';
    if (type === 'outlet') return 'outlet';
    if (type === 'vendor' || type === 'hub') return 'vendor';
    if (type === 'production') return ({ prepress: 'prepress', scheduler: 'production', logistics: 'logistics', production_manager: 'prepress' }[role] || 'prepress');
    if (type === 'customer') return 'dash';
    return 'home';
  }
  // ops acting-role for the live state machine, derived from the logged-in user's role
  opsActingRole() {
    const map = { admin: 'production_director', production_manager: 'production_director', prepress: 'prepress_staff', scheduler: 'scheduler_staff', logistics: 'logistics_staff', outlet_staff: 'store_manager', outlet_manager: 'store_manager', vendor: 'printer', hub: 'hub' };
    return map[this.userRole()] || this.opsRoleFor(this.state.route) || 'production_director';
  }
  isManager() { return ['admin', 'production_manager', 'outlet_manager'].indexOf(this.userRole()) !== -1; }
  // scoped top nav for staff, replacing the removed dev "Pages" row
  staffBar(active) {
    const type = this.userType();
    // only the admin keeps the dark cross-console bar; outlet/production/vendor use the white
    // top-nav in staffPage() (matching the original outlet dashboard aesthetic).
    if (type !== 'admin') return null;
    const role = this.userRole();
    const LABEL = { admin: 'Admin', outlet: 'Outlet', prepress: 'Prepress', production: 'Scheduler', logistics: 'Logistics', vendor: 'Vendor / Hub', crm: 'Chat CRM', home: 'View site' };
    const links = type === 'admin' ? ['admin', 'outlet', 'prepress', 'production', 'logistics', 'vendor', 'crm', 'home']
      : type === 'outlet' ? ['outlet']
      : type === 'vendor' || type === 'hub' ? ['vendor']
      : ({ prepress: ['prepress'], scheduler: ['production', 'vendor'], logistics: ['logistics'], production_manager: ['prepress', 'production', 'logistics', 'vendor'] }[role] || ['prepress']);
    const u = this.state.user;
    return h('div', { style: { background: INK, color: '#fff' } },
      h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '9px 20px', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' } },
        h('span', { style: { fontSize: 11, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', opacity: .7, marginRight: 4 } }, (role || type).replace(/_/g, ' ')),
        links.map(r => { const on = r === active;
          return h('span', { key: r, 'data-go': r, style: { fontSize: 12.5, fontWeight: on ? 700 : 500, padding: '5px 11px', borderRadius: 999, background: on ? TEAL : 'rgba(255,255,255,.12)', color: '#fff', cursor: 'pointer' } }, LABEL[r] || r); }),
        h('span', { style: { marginLeft: 'auto', display: 'flex', gap: 12, alignItems: 'center', fontSize: 12.5 } },
          h('span', { style: { opacity: .85 } }, (u && u.name) || ''),
          h('span', { 'data-go': 'dologout', style: { fontWeight: 600, cursor: 'pointer', textDecoration: 'underline' } }, 'Log out'))));
  }
  renderScreen() {
    let route = this.state.route || 'home';
    if (!this.canAccess(route)) route = this.homeFor();
    const f = this['s_' + route];
    const screen = f ? f.call(this) : h('div', { style: { padding: 60, textAlign: 'center', color: MUT } }, 'Screen coming next.');
    const bar = this.staffBar(route);
    return h('div', null, bar, screen, this.orderDialog(), this.docDialog(), this.newUserModal(), this.announcementPopup());
  }

  // ===== HOME =====
  s_home() {
    const s = this.state;
    return h('div', null,
      h('section', { style: { background: 'linear-gradient(180deg,#fdf2f2,#fff)', padding: '46px 0 40px' } },
        h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '0 20px', display: 'flex', gap: 40, alignItems: 'center', flexWrap: 'wrap' } },
          h('div', { style: { flex: '1 1 420px', minWidth: 0 } },
            h('div', { style: { fontSize: 11.5, fontWeight: 600, letterSpacing: '.09em', textTransform: 'uppercase', color: TEALD, marginBottom: 10 } }, 'Custom printing · Malaysia · Singapore · Brunei'),
            h('h1', { style: { margin: '0 0 14px', fontSize: 'clamp(32px,4.4vw,50px)', lineHeight: 1.06, letterSpacing: '-.03em', fontWeight: 600 } }, 'Your exact print price, ', h('span', { style: { color: TEAL } }, 'in seconds.')),
            h('p', { style: { margin: '0 0 22px', fontSize: 16.5, color: MUT, maxWidth: '48ch', lineHeight: 1.65 } }, 'Configure your job and see the price to the cent. Order online when it looks right.'),
            h('div', { style: { display: 'flex', gap: 11, flexWrap: 'wrap' } }, this.btn('Get your price →', 'teal', 'product'), this.btn('Browse products', 'ghost', 'category')),
            h('div', { style: { marginTop: 20, display: 'flex', gap: 22, flexWrap: 'wrap', fontSize: 12.5, color: FAINT } },
              h('span', null, h('b', { style: { color: INK } }, '30+'), ' partner vendors'),
              h('span', null, h('b', { style: { color: INK } }, '100+'), ' products online'),
              h('span', null, h('b', { style: { color: INK } }, '4.8/5'), ' verified reviews'),
              h('span', null, h('b', { style: { color: INK } }, 'Since 2018')))),
          h('div', { style: { flex: '1 1 340px', minWidth: 280, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 } },
            h('div', { style: { filter: 'drop-shadow(0 14px 26px rgba(33,33,33,.14))' } }, this.art('card')),
            h('div', { style: { filter: 'drop-shadow(0 14px 26px rgba(33,33,33,.14))', marginTop: 26 } }, this.art('sticker')),
            h('div', { style: { filter: 'drop-shadow(0 14px 26px rgba(33,33,33,.14))', marginTop: -12 } }, this.art('box')),
            h('div', { style: { filter: 'drop-shadow(0 14px 26px rgba(33,33,33,.14))', marginTop: 12 } }, this.art('banner'))))),

      this.homeSteps(),

      this.sec('Instant quote', 'See your price right here', 'Pick a category and quantity to get a starting price.',
        h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 14, alignItems: 'end', border: '1px solid ' + HAIR, borderRadius: 14, padding: 20, background: '#fff' } },
          [['Category', 'Cards'], ['Product', 'Business Card'], ['Quantity', '1,000 pcs']].map((f, i) =>
            h('label', { key: i, style: { display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12, fontWeight: 600, color: MUT } }, f[0],
              h('div', { style: { border: '1px solid #eaeaea', borderRadius: 8, padding: '11px 13px', fontSize: 14, fontWeight: 400, color: INK, display: 'flex', justifyContent: 'space-between' } }, f[1], h('span', { style: { color: FAINT, fontSize: 10 } }, '▼')))),
          h('div', { style: { display: 'flex', flexDirection: 'column', gap: 4 } },
            h('span', { style: { fontSize: 12, color: FAINT } }, 'From'),
            h('span', { style: { fontSize: 27, fontWeight: 600, letterSpacing: '-.02em', color: TEAL } }, this.money(168))),
          this.btn('Open configurator →', 'amber', 'product', { justifyContent: 'center' })), { alt: true }),

      this.sec('Shop by category', 'Find your product by category', this.pkProducts().length + ' products, every one priced online with specs and artwork guides.',
        h('div', null,
          h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(210px,1fr))', gap: 16 } },
            this.catCategories().map(c => {
              const list = this.catProducts(c.id), cover = list[0] ? list[0].engName : 'card';
              return h('a', { key: c.id, href: this.navHref(c.id === 'packaging-boxes' ? 'packaging' : 'catopen:' + c.id) || undefined, 'data-go': c.id === 'packaging-boxes' ? 'packaging' : 'catopen:' + c.id, style: { border: '1px solid ' + HAIR, borderRadius: 13, overflow: 'hidden', background: '#fff', cursor: 'pointer', display: 'block', color: 'inherit', textDecoration: 'none' } },
                this.art(cover),
                h('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '13px 15px' } },
                  h('span', { style: { fontWeight: 500, fontSize: 14 } }, c.label),
                  h('span', { style: { fontSize: 12, color: FAINT } }, list.length + ' products')));
            })),
          h('div', { style: { display: 'flex', justifyContent: 'center', marginTop: 24 } },
            this.btn('Browse all ' + this.pkProducts().length + ' products →', 'teal', 'catopen:all', { justifyContent: 'center', padding: '13px 26px' })))),

      this.sec('Popular right now', 'What customers order most', 'Best sellers, priced to the cent.',
        h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(190px,1fr))', gap: 14 } },
          BEST.map((p, i) => { const bid = this.pkIdByName(p[0]); const label = bid != null ? this.catName(bid) : p[0];
            return h(bid != null ? 'a' : 'div', { key: i, href: bid != null ? (this.productPath(bid) || undefined) : undefined, 'data-go': bid != null ? 'open:' + bid : 'category', style: { border: '1px solid ' + HAIR, borderRadius: 12, overflow: 'hidden', background: '#fff', display: 'flex', flexDirection: 'column', cursor: 'pointer', color: 'inherit', textDecoration: 'none' } },
            this.art(p[0]),
            h('div', { style: { padding: '11px 13px', display: 'flex', flexDirection: 'column', gap: 5 } },
              h('span', { style: { fontSize: 13.5, fontWeight: 500 } }, label),
              h('span', { style: { fontSize: 12.5, color: TEAL, fontWeight: 600 } }, p[2]))); })), { alt: true }),

      this.sec('Membership', 'Save up to 15% on every order', 'Your discount grows with your yearly spend, and stacks with vouchers and referral credit.',
        h('div', null,
          h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 12 } },
            TIERS.map((t, i) => h('div', { key: i, style: { border: '1px solid ' + (i === 3 ? TEAL : HAIR), borderRadius: 12, padding: 16, background: i === 3 ? '#fdf2f2' : '#fff' } },
              h('div', { style: { fontSize: 14.5, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 } }, t[0], i === 3 ? this.chip('You', 'ok') : null),
              h('div', { style: { fontSize: 12.5, color: FAINT, margin: '4px 0 8px' } }, t[1]),
              h('div', { style: { fontSize: 22, fontWeight: 600, color: TEAL, letterSpacing: '-.02em' } }, t[2]),
              h('div', { style: { fontSize: 12, color: MUT, marginTop: 8, lineHeight: 1.55 } }, t[3])))),
          h('div', { style: { marginTop: 18, display: 'flex', gap: 11 } }, this.btn('See full comparison', 'ghost', 'membership'), this.btn('Register free', 'teal', 'dash')))),

      this.sec('Learning Hub', 'Get your artwork right first time', 'Free guides on bleed, paper and setup for every product.',
        h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 16 } },
          [['Artwork Guides', 'How to set up bleed, trim and safe area', '3 mm bleed on every side'],
           ['Paper & Finishes', 'Choosing between 250gsm and 360gsm art card', 'Stock weight guide'],
           ['Business Tips', 'What to print for a new retail outlet', 'Launch checklist']].map((a, i) =>
            h('div', { key: i, 'data-go': 'learn', style: { border: '1px solid ' + HAIR, borderRadius: 12, overflow: 'hidden', background: '#fff' } },
              h('div', { style: { height: 120, background: 'linear-gradient(120deg,#FAFAFA,#fdf2f2)' } }),
              h('div', { style: { padding: 16 } },
                h('div', { style: { fontSize: 11, fontWeight: 600, letterSpacing: '.07em', textTransform: 'uppercase', color: TEAL } }, a[0]),
                h('div', { style: { fontSize: 15, fontWeight: 500, margin: '7px 0 6px', lineHeight: 1.35 } }, a[1]),
                h('div', { style: { fontSize: 12.5, color: MUT } }, a[2]))))), { alt: true }),
    );
  }

  // "Fast and Easy Ways to Print Online" — the original homepage's 4-step how-it-works
  // band (step copy preserved verbatim from the live site; brand-styled step icons).
  homeSteps() {
    const STEPS = [
      ['sliders', 'Customise your print', 'Pick your product, size, material and quantity.'],
      ['upload', 'Upload your artwork', 'Drop in your print-ready files.'],
      ['credit-card', 'See the price and pay', 'Get the exact price, then check out online.'],
      ['truck', 'We print and ship', 'We produce your order and deliver to your door.'],
    ];
    return h('section', { style: { background: '#fff', padding: '48px 0' } },
      h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '0 20px' } },
        h('div', { style: { textAlign: 'center', marginBottom: 34 } },
          h('h2', { style: { margin: '0 0 8px', fontSize: 28, fontWeight: 600, letterSpacing: '-.02em' } }, 'Order your print in four steps'),
          h('p', { style: { margin: 0, fontSize: 14.5, color: MUT } }, 'Set it up online in minutes.')),
        h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 26 } },
          STEPS.map((st, i) => h('div', { key: i, style: { textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 } },
            h('div', { style: { position: 'relative', height: 76, width: 76, borderRadius: '50%', background: '#fdf2f2', display: 'grid', placeItems: 'center' } },
              this.dashIcon(st[0], TEAL, 30),
              h('span', { style: { position: 'absolute', top: -6, right: -6, height: 26, width: 26, borderRadius: '50%', background: TEAL, color: '#fff', fontSize: 13, fontWeight: 700, display: 'grid', placeItems: 'center' } }, i + 1)),
            h('div', { style: { fontSize: 15.5, fontWeight: 600, lineHeight: 1.3, maxWidth: 220 } }, st[1]),
            h('div', { style: { fontSize: 13, color: MUT, lineHeight: 1.65, maxWidth: 240 } }, st[2])))),
        h('div', { style: { display: 'flex', justifyContent: 'center', gap: 11, marginTop: 32 } },
          this.btn('Start your order →', 'amber', 'category', { justifyContent: 'center', padding: '13px 26px' }))));
  }

  // ===== SEARCH RESULTS =====
  s_search() {
    const tab = this.state.stab || 'products';
    const TABS = [['products', 'Products', 12], ['cats', 'Categories', 3], ['learn', 'Learning Hub', 5]];
    const RESULTS = [
      ['Business Card', 'Cards', 'from ' + this.money(38), 'digital-cards.png'],
      ['Creative Cut Card — Digital', 'Cards', 'from ' + this.money(72), 'die-cut-card.png'],
      ['Folded Business Card', 'Cards', 'from ' + this.money(88), 'folded-business-card.png'],
      ['PVC Card — Digital', 'Cards', 'from ' + this.money(188), 'digital-cards.png'],
      ['Name Card Holder', 'Apparel & Gifts', 'from ' + this.money(42), 'key-card-holder.jpg'],
      ['Voucher — Litho', 'Cards', 'from ' + this.money(165), 'voucher-book.jpg'],
    ];
    const CATS_R = [['Cards', '8 products'], ['Books & Stationery', '19 products'], ['Money Packet', '4 products']];
    const ARTS = [
      ['Artwork Guides', 'Business card bleed and safe area explained', '3 mm bleed, 3 mm safe margin'],
      ['Paper & Finishes', 'Choosing between 250gsm, 310gsm and 360gsm art card', 'Stock weight guide'],
      ['Artwork Guides', 'Why your business card came back as “issues found”', 'Top five prepress rejections'],
      ['Business Tips', 'What to print when you open a new outlet', 'Launch checklist'],
      ['Company News', 'Printoka now delivers to Brunei in 5 working days', 'Coverage update'],
    ];
    return h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '10px 20px 0' } },
      this.head('Results for “business card”', 'Products, categories and Learning Hub articles in one tabbed result view. Unmatched queries are logged for catalogue-gap analysis.'),
      h('div', { style: { display: 'flex', marginTop: 18, border: '1px solid ' + HAIR, borderRadius: 2, overflow: 'hidden', maxWidth: 620 } },
        h('span', { style: { flex: 1, padding: '12px 14px', fontSize: 14, color: INK, minWidth: 0 } }, 'business card'),
        h('span', { style: { background: TEAL, padding: '12px 18px', display: 'flex', alignItems: 'center' } },
          h('img', { src: window.__asset('assets/icons/search.svg'), alt: '', style: { height: 14, width: 'auto', display: 'block', filter: 'brightness(0) invert(1)' } }))),
      h('div', { style: { display: 'flex', gap: 26, borderBottom: '1px solid ' + HAIR, margin: '22px 0 20px' } },
        TABS.map(t => h('span', { key: t[0], 'data-go': 'set:stab:' + t[0], style: { display: 'flex', alignItems: 'center', gap: 7, padding: '0 0 12px', fontSize: 14, fontWeight: 600, color: tab === t[0] ? TEAL : MUT, borderBottom: '2px solid ' + (tab === t[0] ? TEAL : 'transparent'), marginBottom: -1, cursor: 'pointer' } },
          t[1], h('span', { style: { fontSize: 11.5, fontWeight: 600, color: FAINT } }, t[2])))),
      tab === 'products' && h('div', null,
        h('div', { style: { display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 18 } },
          ['Category: Cards', 'Turnaround: any', 'Price: any', 'Sort: Most relevant'].map((f, i) =>
            h('span', { key: i, style: { display: 'flex', alignItems: 'center', gap: 7, border: '1px solid ' + HAIR, borderRadius: 2, padding: '8px 13px', fontSize: 13, color: MUT } }, f,
              h('img', { src: window.__asset('assets/icons/dropdown.svg'), alt: '', style: { height: 6, width: 'auto', display: 'block', opacity: .55 } })))),
        h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 18 } },
          RESULTS.map((r, i) => h('div', { key: i, 'data-go': this.goByName(r[0]), style: { border: '1px solid ' + HAIR, background: '#fff', padding: 18, cursor: 'pointer' } },
            h('img', { src: window.__asset('assets/products/' + r[3]), alt: '', loading: 'lazy', style: { width: '100%', aspectRatio: '4 / 3', objectFit: 'contain', display: 'block' } }),
            h('div', { style: { fontSize: 15, fontWeight: 500, margin: '12px 0 3px' } }, r[0]),
            h('div', { style: { fontSize: 12.5, color: FAINT, marginBottom: 6 } }, r[1]),
            h('div', { style: { fontSize: 13.5, fontWeight: 600, color: TEAL } }, r[2]))))),
      tab === 'cats' && h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 16 } },
        CATS_R.map((c, i) => h('div', { key: i, 'data-go': 'category', style: { border: '1px solid ' + HAIR, padding: 20, cursor: 'pointer' } },
          h('div', { style: { fontSize: 16, fontWeight: 600 } }, c[0]),
          h('div', { style: { fontSize: 13, color: MUT, marginTop: 4 } }, c[1])))),
      tab === 'learn' && h('div', { style: { display: 'flex', flexDirection: 'column', gap: 12 } },
        ARTS.map((a, i) => h('div', { key: i, 'data-go': 'learn', style: { border: '1px solid ' + HAIR, padding: 18, cursor: 'pointer' } },
          h('div', { style: { fontSize: 11, fontWeight: 600, letterSpacing: '.07em', textTransform: 'uppercase', color: TEAL } }, a[0]),
          h('div', { style: { fontSize: 15.5, fontWeight: 500, margin: '6px 0 4px' } }, a[1]),
          h('div', { style: { fontSize: 13, color: MUT } }, a[2])))),
      h('div', { style: { marginTop: 26, border: '1px solid ' + HAIR, background: ALT, padding: 20, fontSize: 13, color: MUT, lineHeight: 1.7 } },
        h('b', { style: { color: INK } }, 'No-results state: '),
        'when nothing matches, this panel lists the nearest categories and the top searched terms instead of an empty page, and the query is written to the catalogue-gap log.'));
  }

  // ===== ABOUT US =====
  s_about() {
    const STATS = [['2018', 'Founded'], ['30+', 'Partner vendors'], ['100+', 'Products online'], ['3', 'Countries served']];
    const TIMELINE = [
      ['2018', 'Printoka opens', 'Founded as an online printing marketplace, aggregating vetted Malaysian printers under one instant-quote storefront.'],
      ['2020', 'Own facility in Miri', 'A Printoka-operated press in Miri, Sarawak joins the vendor network for short-run and rapid jobs.'],
      ['2022', 'Singapore and Brunei', 'Cross-border delivery opens, with per-country currency, tax treatment and courier lists.'],
      ['2024', 'Membership ladder', 'Five tiers on cumulative spend, from Bronze at ' + this.money(1000) + ' to Platinum with a Key Account Manager.'],
      ['2026', 'One platform, every role', 'Customer, outlet, prepress, production, logistics and vendor work move onto a single system.'],
    ];
    return h('div', null,
      h('section', { style: { background: ALT, borderBottom: '1px solid ' + HAIR } },
        h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '54px 20px' } },
          h('h1', { style: { margin: 0, maxWidth: '20ch', fontSize: 'clamp(26px,3.6vw,38px)', fontWeight: 600, lineHeight: 1.2, letterSpacing: '-.02em' } }, 'Printing matched to the right press'),
          h('p', { style: { margin: '16px 0 0', maxWidth: '60ch', fontSize: 16, color: MUT, lineHeight: 1.8 } }, 'Printoka sends your job to the printer that suits it best, from our own facility in Miri to thirty partner vendors. You get factory pricing without chasing a quote first.'))),
      h('section', { style: { maxWidth: 1180, margin: '0 auto', padding: '36px 20px 0', display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))', gap: 18 } },
        STATS.map((s, i) => h('div', { key: i, style: { border: '1px solid ' + HAIR, padding: '22px 24px' } },
          h('div', { style: { fontSize: 30, fontWeight: 600, color: TEAL, letterSpacing: '-.02em' } }, s[0]),
          h('div', { style: { fontSize: 13, color: MUT, marginTop: 4 } }, s[1])))),
      this.sec(null, 'How we got here', null,
        h('div', { style: { display: 'flex', flexDirection: 'column' } },
          TIMELINE.map((t, i) => h('div', { key: i, style: { display: 'grid', gridTemplateColumns: '86px minmax(0,1fr)', gap: 20, padding: '20px 0', borderTop: '1px solid ' + LINE } },
            h('div', { style: { fontSize: 15, fontWeight: 600, color: TEAL } }, t[0]),
            h('div', null,
              h('div', { style: { fontSize: 16, fontWeight: 600, marginBottom: 5 } }, t[1]),
              h('div', { style: { fontSize: 14, color: MUT, lineHeight: 1.75 } }, t[2])))))),
      this.sec('Key Account Management', 'Your own Key Account Manager', 'Platinum members and approved business accounts get a named manager who handles quoting, scheduling, credit terms and escalation directly.',
        h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 18 } },
          [['Quoting and re-quoting', 'Bulk and off-catalogue jobs priced against vendor rate cards, usually same day.'],
           ['Production scheduling', 'Priority queue placement and delivery dates committed before you order.'],
           ['Credit terms', 'Consolidated monthly invoicing for approved accounts, with PO references carried to the order slip.']]
            .map((c, i) => h('div', { key: i, style: { border: '1px solid ' + HAIR, padding: 22 } },
              h('div', { style: { fontSize: 15.5, fontWeight: 600, marginBottom: 7 } }, c[0]),
              h('div', { style: { fontSize: 13.5, color: MUT, lineHeight: 1.7 } }, c[1])))), { alt: true }),
      this.sec(null, 'Work with us', null,
        h('div', { style: { display: 'flex', gap: 12, flexWrap: 'wrap' } },
          this.btn('Talk to sales', 'teal', 'contact'), this.btn('Become a partner printer', 'ghost', 'vendor'))));
  }

  // ===== AUTHENTICATION =====
  s_auth() {
    if (this.state.user) return h('div', { style: { maxWidth: 560, margin: '0 auto', padding: '20px' } },
      this.card([
        h('div', { key: 'a', style: { fontSize: 18, fontWeight: 600, marginBottom: 6 } }, 'You are signed in'),
        h('div', { key: 'b', style: { fontSize: 14, color: MUT, marginBottom: 16 } }, this.state.user.name + ' · ' + this.state.user.email + ' · ' + this.state.user.tier + ' tier'),
        h('div', { key: 'c', style: { display: 'flex', gap: 10, flexWrap: 'wrap' } }, this.btn('My dashboard', 'teal', 'dash'), this.btn('Log out', 'ghost', 'dologout'))]));
    const mode = this.state.authTab || 'login';           // login | register
    const role = this.state.authRole || 'member';          // member | printer | hub
    const MEDIA = 'https://printoka.com/media/';
    const feats = [
      ['value__thumb-1.svg', 'Superior Quality'], ['icon__truck.svg', 'Configurable Delivery Options'],
      ['icon__credit.svg', 'Credit Terms for Corporate Members'], ['value__time.svg', 'Instant Price Quotation'],
      ['value__shield.svg', 'Professional Print Experts at your service'], ['value__store.svg', 'Membership Plans'],
    ];
    const roleCopy = { member: 'Login', printer: 'Printer / Vendor login', hub: 'Hub login' }[role];
    const inp = { border: '1px solid ' + HAIR, borderRadius: 8, padding: '12px 14px', fontSize: 14, font: '400 14px Montserrat,sans-serif', width: '100%', background: '#f4f6fb' };
    const lbl = (t, req) => h('div', { style: { fontSize: 13, fontWeight: 500, color: INK, marginBottom: 6 } }, t, req ? h('span', { style: { color: '#E52220' } }, ' *') : null);
    const err = this.state.authErr ? h('div', { key: 'e', style: { fontSize: 12.5, color: '#c0392b', background: '#fdecec', border: '1px solid #f5c8c7', borderRadius: 8, padding: '9px 11px' } }, this.state.authErr) : null;
    const google = h('div', { key: 'g', style: { textAlign: 'center' } },
      h('span', { title: 'Google sign-in plugs in here (OAuth)', style: { display: 'inline-grid', placeItems: 'center', height: 46, width: 46, borderRadius: '50%', border: '1px solid ' + HAIR, cursor: 'pointer', fontFamily: 'Georgia,serif', fontSize: 22, fontWeight: 700, color: '#4285F4' } }, 'G'),
      h('div', { style: { fontSize: 12.5, color: FAINT, marginTop: 10 } }, 'or ' + (mode === 'login' ? 'login' : 'register') + ' with email address'));
    const card = h('div', { style: { background: '#fff', borderRadius: '28px 28px 16px 16px', padding: '30px 34px 34px', boxShadow: '0 20px 50px rgba(0,0,0,.18)', width: '100%', maxWidth: 460 } },
      h('div', { style: { height: 4, width: 34, background: '#E52220', borderRadius: 2, margin: '0 auto 10px' } }),
      h('h2', { style: { textAlign: 'center', fontSize: 22, fontWeight: 600, margin: '0 0 18px' } }, mode === 'login' ? roleCopy : 'Register'),
      google,
      h('div', { style: { display: 'flex', flexDirection: 'column', gap: 14, marginTop: 18 } },
        err,
        mode === 'login' ? [
          h('div', { key: 'em' }, lbl('Email', true), h('input', { type: 'email', value: this.state.lgEmail || '', onChange: e => this.setField('lgEmail', e.target.value), style: inp })),
          h('div', { key: 'pw' }, lbl('Password'), h('div', { style: { position: 'relative' } },
            h('input', { type: this.state.lgShow ? 'text' : 'password', value: this.state.lgPass || '', onChange: e => this.setField('lgPass', e.target.value), style: inp }),
            h('span', { onClick: () => this.setField('lgShow', !this.state.lgShow), style: { position: 'absolute', right: 12, top: 12, cursor: 'pointer', color: FAINT, fontSize: 14 } }, this.state.lgShow ? '🙈' : '👁'))),
          h('div', { key: 'fp', style: { fontSize: 13 } }, h('span', { 'data-go': 'contact', style: { color: '#2f6fd0', cursor: 'pointer' } }, 'Forgot your password?')),
          h('label', { key: 'rm', style: { display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, color: MUT, cursor: 'pointer' } }, h('input', { type: 'checkbox', checked: !!this.state.lgRemember, onChange: e => this.setField('lgRemember', e.target.checked) }), 'Remember me?'),
          h('span', { key: 'b', 'data-go': 'dologin', style: { display: 'block', textAlign: 'center', background: '#E52220', color: '#fff', fontWeight: 600, fontSize: 15, padding: '13px', borderRadius: 8, cursor: 'pointer' } }, this.state.authBusy ? 'Signing in…' : 'Login'),
          h('div', { key: 'reg', style: { textAlign: 'center', fontSize: 13.5, color: MUT } }, 'New member? ', h('span', { 'data-go': 'set:authTab:register', style: { color: '#2f6fd0', fontWeight: 600, cursor: 'pointer', textDecoration: 'underline' } }, 'Register'), ' here'),
          h('div', { key: 'alt', style: { textAlign: 'center', fontSize: 13.5, display: 'flex', gap: 16, justifyContent: 'center' } },
            h('span', { onClick: () => this.setState({ authRole: role === 'printer' ? 'member' : 'printer', authErr: null }), style: { color: '#2f6fd0', fontWeight: 600, cursor: 'pointer', textDecoration: 'underline' } }, 'Printer Login'),
            h('span', { onClick: () => this.setState({ authRole: role === 'hub' ? 'member' : 'hub', authErr: null }), style: { color: '#2f6fd0', fontWeight: 600, cursor: 'pointer', textDecoration: 'underline' } }, 'Hub Login')),
          role !== 'member' ? h('div', { key: 'hint', style: { textAlign: 'center', fontSize: 12, color: FAINT } }, 'Sign in with your ' + (role === 'printer' ? 'printer / vendor' : 'hub') + ' account — you’ll land on your ' + (role === 'printer' ? 'vendor' : 'hub') + ' dashboard.') : null,
        ] : [
          h('div', { key: 'nm' }, lbl('Full name', true), h('input', { value: this.state.rgName || '', onChange: e => this.setField('rgName', e.target.value), style: inp })),
          h('div', { key: 'em' }, lbl('Email', true), h('input', { type: 'email', value: this.state.rgEmail || '', onChange: e => this.setField('rgEmail', e.target.value), style: inp })),
          h('div', { key: 'ph' }, lbl('Mobile number'), h('input', { type: 'tel', value: this.state.rgPhone || '', onChange: e => this.setField('rgPhone', e.target.value), style: inp })),
          h('div', { key: 'pw' }, lbl('Password', true), h('input', { type: 'password', value: this.state.rgPass || '', onChange: e => this.setField('rgPass', e.target.value), style: inp }), h('div', { style: { fontSize: 11.5, color: FAINT, marginTop: 4 } }, 'Minimum 6 characters')),
          h('label', { key: 'ag', style: { display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 12.5, color: MUT, cursor: 'pointer', lineHeight: 1.5 } }, h('input', { type: 'checkbox', checked: !!this.state.rgAgree, onChange: e => this.setField('rgAgree', e.target.checked), style: { marginTop: 3 } }), 'I agree to the Terms and consent to Printoka processing my data under the PDPA.'),
          h('span', { key: 'b', 'data-go': 'doregister', style: { display: 'block', textAlign: 'center', background: '#E52220', color: '#fff', fontWeight: 600, fontSize: 15, padding: '13px', borderRadius: 8, cursor: 'pointer' } }, this.state.authBusy ? 'Creating…' : 'Create my account'),
          h('div', { key: 'log', style: { textAlign: 'center', fontSize: 13.5, color: MUT } }, 'Already a member? ', h('span', { 'data-go': 'set:authTab:login', style: { color: '#2f6fd0', fontWeight: 600, cursor: 'pointer', textDecoration: 'underline' } }, 'Login'), ' here'),
        ]));
    return h('div', { style: { background: '#E52220', margin: '-10px -20px 0', minHeight: 560 } },
      h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '48px 24px 60px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 40, alignItems: 'center' } },
        h('div', { style: { color: '#fff', maxWidth: 440 } },
          h('h1', { style: { fontSize: 'clamp(26px,3vw,34px)', fontWeight: 700, letterSpacing: '-.01em', margin: '0 0 8px' } }, 'Sign up for some member deals!'),
          h('p', { style: { margin: '0 0 24px', fontSize: 15, opacity: .95 } }, 'Sign up for some member deals!'),
          h('div', { style: { display: 'flex', flexDirection: 'column', gap: 16 } },
            feats.map((f, i) => h('div', { key: i, style: { display: 'flex', alignItems: 'center', gap: 14 } },
              h('span', { style: { height: 40, width: 40, borderRadius: '50%', background: '#fff', display: 'grid', placeItems: 'center', flex: 'none' } }, h('img', { src: MEDIA + f[0], alt: '', style: { height: 18, width: 18, display: 'block' } })),
              h('span', { style: { fontSize: 15.5 } }, f[1]))))),
        h('div', { style: { display: 'flex', justifyContent: 'center' } }, card)));
  }

  // ===== ORDER CONFIRMATION =====
  s_confirm() {
    const o = this.state.order;
    if (!o) return h('div', { style: { maxWidth: 700, margin: '0 auto', padding: '10px 20px 0' } },
      this.head('Order confirmation', 'No recent order in this session.'),
      h('div', { style: { display: 'flex', gap: 10 } }, this.btn('Track an order →', 'teal', 'track'), this.btn('Browse products', 'ghost', 'category')));
    const paid = o.payment && o.payment.status === 'validated';
    const NEXT = [
      ['Order received', 'Order ' + o.id + ' created' + (paid ? ' and payment confirmed' : ' — awaiting payment confirmation') + '. ' + o.jobIds.length + ' job(s) queued.', 'now'],
      ['Prepress check', 'A prepress operator checks your artwork against the trim, bleed and safe area for each job.', 'within 4 working hours'],
      ['Production', 'Printing, finishing and QC — in-house or with the partner printer best suited to the job.', '2–4 working days'],
      ['Shipped', 'Courier assigned, AWB issued, live tracking appears in your dashboard.', 'day 4'],
    ];
    return h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '10px 20px 0' } },
      h('div', { style: { border: '1px solid ' + HAIR, borderTop: '3px solid ' + TEAL, padding: '30px 32px', display: 'flex', flexWrap: 'wrap', gap: 22, alignItems: 'center', justifyContent: 'space-between' } },
        h('div', { style: { flex: '1 1 380px', minWidth: 0 } },
          h('h1', { style: { margin: '0 0 10px', fontSize: 'clamp(21px,2.6vw,27px)', fontWeight: 600, letterSpacing: '-.01em' } }, 'Thank you — your order is in'),
          h('p', { style: { margin: 0, fontSize: 14.5, color: MUT, lineHeight: 1.7 } }, 'Order ', h('b', { style: { color: INK } }, o.id), ' · ' + o.jobIds.length + ' job(s) · ',
            this.chip(paid ? 'Paid' : 'Payment pending', paid ? 'ok' : 'warn'),
            (o.customer && o.customer.email) ? h('span', null, ' · confirmation sent to ' + o.customer.email) : '')),
        h('div', { style: { display: 'flex', gap: 10, flexWrap: 'wrap' } },
          this.btn('Upload your artwork', 'amber', 'artwork'),
          this.btn('Track this order', 'teal', 'track'),
          this.btn('Download invoice', 'ghost', 'doc:invoice:' + o.id),
          this.btn('Order slip', 'ghost', 'doc:slip:' + o.id))),
      h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 22, marginTop: 22, alignItems: 'start' } },
        h('div', null,
          h('div', { style: { fontSize: 17, fontWeight: 600, marginBottom: 14 } }, 'What happens next'),
          NEXT.map((n, i) => h('div', { key: i, style: { display: 'grid', gridTemplateColumns: '30px minmax(0,1fr)', gap: 14, padding: '14px 0', borderTop: i ? '1px solid ' + LINE : 'none' } },
            h('span', { style: { height: 26, width: 26, borderRadius: '50%', background: i === 0 ? TEAL : '#fff', border: '1px solid ' + (i === 0 ? TEAL : HAIR), color: i === 0 ? '#fff' : MUT, display: 'grid', placeItems: 'center', fontSize: 12, fontWeight: 600 } }, i + 1),
            h('div', null,
              h('div', { style: { display: 'flex', gap: 10, alignItems: 'baseline', flexWrap: 'wrap' } },
                h('span', { style: { fontSize: 14.5, fontWeight: 600 } }, n[0]),
                h('span', { style: { fontSize: 12, color: FAINT } }, n[2])),
              h('div', { style: { fontSize: 13, color: MUT, lineHeight: 1.7, marginTop: 4 } }, n[1]))))),
        h('div', { style: { border: '1px solid ' + HAIR, padding: 22 } },
          h('div', { style: { fontSize: 15, fontWeight: 600, marginBottom: 14 } }, 'Order summary'),
          (o.items || []).map((it, i) => h('div', { key: 'i' + i, style: { display: 'flex', justifyContent: 'space-between', gap: 14, padding: '8px 0', fontSize: 13, color: INK } },
            h('span', { style: { minWidth: 0 } }, it.product + ' · ' + it.qty.toLocaleString() + ' pcs'), h('span', { style: { whiteSpace: 'nowrap', fontWeight: 500 } }, this.money(it.lineTotal)))),
          [['Subtotal', this.money(o.subtotal)], [this.tier() + ' member discount', '− ' + this.money(o.memberDiscount)], [this.taxLabel(), this.money(o.tax)], ['Delivery', this.money(o.shipping)]]
            .map((r, i) => h('div', { key: 'r' + i, style: { display: 'flex', justifyContent: 'space-between', gap: 14, padding: '8px 0', fontSize: 13, color: MUT, borderTop: i === 0 ? '1px solid ' + LINE : 'none' } },
              h('span', null, r[0]), h('span', { style: { whiteSpace: 'nowrap' } }, r[1]))),
          h('div', { style: { display: 'flex', justifyContent: 'space-between', borderTop: '1px solid ' + HAIR, marginTop: 8, paddingTop: 12, fontSize: 16, fontWeight: 600 } },
            h('span', null, paid ? 'Total paid' : 'Total due'), h('span', null, this.money(o.total))))));
  }

  // ===== INVOICES & ORDER SLIPS ARCHIVE =====
  s_invoices() {
    const tab = this.state.invTab || 'invoices';
    const u = this.state.user;
    const nav = [['Overview', null, 'dash'], ['My Orders', null, 'dash'], ['My Quotes', null, 'dash'], ['Artwork gallery', null, 'artwork'], ['Membership & rewards', null, 'membership'], ['Credit balance', null, 'dash'], ['Invoices & slips', null, 'invoices'], ['Address book', null, 'dash'], ['Notifications', null, 'dash']];
    const orders = this.state.userOrders || [];
    const cinvs = this.state.custInvoices || [];
    // real invoices: one per storefront order + every custom invoice prepared for this customer
    const orderInv = orders.map(o => ({ kind: 'order', id: 'INV-' + o.id.replace('PO-', ''), order: o.id, date: (o.createdAt || '').slice(0, 10), amount: o.total, status: o.payment && o.payment.status === 'validated' ? 'Paid' : 'Unpaid', open: () => this.openDoc(o.id, 'invoice') }));
    const custInv = cinvs.map(inv => ({ kind: 'custom', id: inv.number || inv.id, order: inv.orderId || '—', date: (inv.date || '').slice(0, 10), amount: inv.price, status: inv.status === 'paid' ? 'Paid' : inv.status === 'cancelled' ? 'Cancelled' : 'Unpaid', open: () => this.openDoc(inv.id, 'custominvoice') }));
    const INV = orderInv.concat(custInv);
    const SLIPS = orders.map(o => ({ id: 'OS-' + o.id.replace('PO-', ''), order: o.id, items: (o.items || []).map(it => it.product + ' · ' + (it.qty || 0).toLocaleString()).join(', '), files: (o.items || []).reduce((a, it) => a.concat(it.artworks || []), []).join(', ') || '—', date: (o.createdAt || '').slice(0, 10), open: () => this.openDoc(o.id, 'slip') }));
    const act = (label, on) => h('span', { onClick: on, style: { fontSize: 12.5, fontWeight: 600, color: TEAL, cursor: 'pointer', whiteSpace: 'nowrap' } }, label);
    const empty = msg => h('div', { style: { border: '1px dashed ' + HAIR, borderRadius: 10, padding: 28, textAlign: 'center', color: FAINT, fontSize: 13 } }, msg);
    return this.shell('Customer · ' + ((u && u.name) || ''), nav, 'Invoices & slips', [
      this.head('Invoices & order slips', 'One invoice per order as a simplified summary, plus any custom invoice our team prepared for you; one order slip per order carrying the full production detail including artwork filenames.'),
      h('div', { key: 't', style: { display: 'flex', gap: 22, borderBottom: '1px solid ' + HAIR, margin: '18px 0' } },
        [['invoices', 'Invoices', INV.length], ['slips', 'Order slips', SLIPS.length]].map(t =>
          h('span', { key: t[0], 'data-go': 'set:invTab:' + t[0], style: { display: 'flex', gap: 7, alignItems: 'center', padding: '0 0 12px', fontSize: 14, fontWeight: 600, color: tab === t[0] ? TEAL : MUT, borderBottom: '2px solid ' + (tab === t[0] ? TEAL : 'transparent'), marginBottom: -1, cursor: 'pointer' } },
            t[1], h('span', { style: { fontSize: 11.5, color: FAINT } }, t[2])))),
      tab === 'invoices'
        ? (INV.length ? this.table(['Invoice', 'Order', 'Issued', 'Amount', 'Status', ''],
            INV.map(r => [h('span', { style: { fontFamily: 'ui-monospace,Menlo,monospace', fontSize: 12 } }, r.id), r.order, r.date, this.rm(r.amount), this.chip(r.status, r.status === 'Paid' ? 'ok' : r.status === 'Cancelled' ? 'neutral' : 'warn'),
              h('span', { style: { display: 'flex', gap: 14, justifyContent: 'flex-end' } }, act('View PDF', r.open))]),
            ['18%', '16%', '14%', '14%', '18%', '20%']) : empty(this.state.userOrders == null ? 'Loading…' : 'No invoices yet.'))
        : (SLIPS.length ? this.table(['Order slip', 'Order', 'Items', 'Artwork files', 'Issued', ''],
            SLIPS.map(r => [h('span', { style: { fontFamily: 'ui-monospace,Menlo,monospace', fontSize: 12 } }, r.id), r.order, r.items, h('span', { style: { fontFamily: 'ui-monospace,Menlo,monospace', fontSize: 11.5 } }, r.files), r.date,
              h('span', { style: { display: 'flex', gap: 14, justifyContent: 'flex-end' } }, act('View PDF', r.open))]),
            ['14%', '14%', '24%', '22%', '13%', '13%']) : empty(this.state.userOrders == null ? 'Loading…' : 'No order slips yet.')),
      h('div', { key: 'n', style: { marginTop: 18, border: '1px solid ' + HAIR, background: ALT, padding: 18, fontSize: 12.5, color: MUT, lineHeight: 1.75 } },
        h('b', { style: { color: INK } }, 'Business accounts: '),
        'select a date range and export every invoice and order slip in one archive, or schedule a monthly statement to your finance mailbox.'),
    ]);
  }

  // ===== CATEGORY LISTING =====
  dieline(kind, w, hh) {
    const W = w || 150, H = hh || 96;
    const L = { stroke: TEAL, strokeWidth: 1, fill: 'none' };
    const F = { stroke: '#9aa4ad', strokeWidth: 1, strokeDasharray: '4 3', fill: 'none' };
    const body = {
      divider: [h('rect', { key: 'a', x: 14, y: 26, width: 122, height: 44, ...L }),
        [0, 1, 2, 3].map(i => h('path', { key: 'n' + i, d: 'M' + (36 + i * 24) + ' 26 l4 8 v18 M' + (36 + i * 24) + ' 26 l-4 8 v18', ...L }))],
      basic: [h('rect', { key: 'a', x: 30, y: 20, width: 90, height: 56, ...L }),
        h('path', { key: 'b', d: 'M30 20 h-16 v56 h16 M120 20 h16 v56 h-16', ...L }),
        h('path', { key: 'c', d: 'M52 20 v56 M98 20 v56', ...F })],
      window: [h('rect', { key: 'a', x: 24, y: 20, width: 102, height: 56, ...L }),
        h('rect', { key: 'b', x: 46, y: 34, width: 56, height: 28, rx: 3, ...L }),
        h('path', { key: 'c', d: 'M70 20 v56', ...F })],
      hanging: [h('rect', { key: 'a', x: 30, y: 26, width: 90, height: 52, ...L }),
        h('path', { key: 'b', d: 'M62 26 v-12 a13 13 0 0 1 26 0 v12', ...L }),
        h('circle', { key: 'c', cx: 75, cy: 17, r: 4, ...L })],
      tray: [h('path', { key: 'a', d: 'M20 34 h110 v34 h-110 z', ...L }),
        h('path', { key: 'b', d: 'M20 34 l14 -14 h82 l14 14 M34 68 l-14 12 h110 l-14 -12', ...L })],
      sleeve: [h('rect', { key: 'a', x: 18, y: 28, width: 114, height: 40, ...L }),
        h('path', { key: 'b', d: 'M46 28 v40 M104 28 v40', ...F })],
      insert: [h('rect', { key: 'a', x: 20, y: 24, width: 110, height: 48, ...L }),
        [0, 1, 2].map(i => h('rect', { key: 'r' + i, x: 30 + i * 34, y: 34, width: 26, height: 28, rx: 2, ...F }))],
      carton: [h('path', { key: 'a', d: 'M28 24 h94 l14 14 v34 l-14 14 h-94 l-14 -14 v-34 z', ...L }),
        h('path', { key: 'b', d: 'M28 24 v62 M122 24 v62', ...F })],
    }[kind] || [];
    return h('svg', { viewBox: '0 0 150 96', width: '100%', height: H, role: 'img', style: { display: 'block' } }, body);
  }

  // Excard-style marketing landing for custom packaging, in Printoka's brand system —
  // leads into the die-line-first configurator below.
  packagingHero() {
    const TYPES = [
      ['box', 'Basic Boxes', 'A clean base you can size to your exact measurements. Tuck-end, auto-lock and tray styles.'],
      ['layers', 'Window Boxes', 'Put your product front-and-centre with a clear window patch.'],
      ['file', 'Sleeves', 'Add to the unboxing moment with a printed sleeve or belly band.'],
      ['box', 'E-Flute Mailers', 'Durable corrugated mailers and flip-lid boxes for shipping and gifting.'],
    ];
    const STOCKS = [['Boxboard Grey Back', 'Economical and rigid. Ideal for retail cartons.'], ['Gloss / Matte Art Card', '250 to 400 GSM coated stock for vivid print.'], ['Kraft', 'Natural brown board for an organic, eco look.'], ['E-Flute Corrugated', 'Cushioned board for mailers and shippers.']];
    const FINISH = [['Spot UV', 'A precise gloss over matte for a tactile, premium accent.'], ['Embossing', 'Raise logos and text off the surface for a physical finish.'], ['Hot Stamping', 'Metallic gold or silver foil for a touch of luxury.'], ['Window Patching', 'A clear film window so the product shows through.']];
    const STEPS = [
      ['sliders', 'Choose your box & dimensions', 'Pick a die-cut style and key in your exact length, width and depth.'],
      ['upload', 'Download the die-line & upload artwork', 'Design straight on our die-line, then upload your print-ready file.'],
      ['truck', 'We print, finish & ship', 'We die-cut, laminate, finish and deliver your boxes to your door.'],
    ];
    const WHY = [['Certified production', 'ISO-grade quality control on every run.'], ['Mockup in days', 'Request a physical sample before the full run.'], ['Design & structure check', 'We verify your die-line and artwork are press-ready.'], ['Colour consistency', 'Consistent colour across every reprint.']];
    return h('div', null,
      // hero
      h('section', { style: { background: 'linear-gradient(180deg,#fdf2f2,#fff)', borderRadius: 16, padding: '40px 34px', marginBottom: 26 } },
        h('div', { style: { display: 'flex', gap: 36, alignItems: 'center', flexWrap: 'wrap' } },
          h('div', { style: { flex: '1 1 360px', minWidth: 0 } },
            h('div', { style: { fontSize: 11.5, fontWeight: 600, letterSpacing: '.09em', textTransform: 'uppercase', color: TEALD, marginBottom: 10 } }, 'Custom packaging boxes'),
            h('h1', { style: { margin: '0 0 12px', fontSize: 'clamp(30px,4vw,46px)', lineHeight: 1.05, letterSpacing: '-.03em', fontWeight: 600 } }, 'Create your own ', h('span', { style: { color: TEAL } }, 'packaging.')),
            h('p', { style: { margin: '0 0 18px', fontSize: 16, color: MUT, maxWidth: '50ch', lineHeight: 1.65 } }, 'Design a box, sleeve or mailer to your exact size. Pick your material and finishing and see the price instantly. Every order comes with a free die-line to design on.'),
            h('div', { style: { display: 'flex', gap: 10, alignItems: 'center', marginBottom: 20, flexWrap: 'wrap' } },
              h('span', { style: { color: AMBER, fontSize: 18, letterSpacing: 2 } }, '★★★★★'),
              h('span', { style: { fontSize: 13, color: MUT } }, '4.8 / 5 from verified reviews')),
            h('div', { style: { display: 'flex', gap: 11, flexWrap: 'wrap' } },
              this.btn('Design your box →', 'amber', 'set:pkTab:configure', { padding: '13px 24px' }),
              this.btn('Get a custom quote', 'ghost', 'contact', { padding: '13px 24px' }))),
          h('div', { style: { flex: '0 1 320px', minWidth: 240, display: 'grid', placeItems: 'center' } },
            h('div', { style: { width: '100%', maxWidth: 300, transform: 'perspective(760px) rotateX(6deg) rotateY(-20deg)', filter: 'drop-shadow(0 16px 26px rgba(33,33,33,.18))' } }, this.dieline('carton', null, 220))))),
      // box types
      this.pkBand('Box styles', 'What would you like to make?', TYPES, (t) => h('div', { key: t[1], 'data-go': 'set:pkTab:library', style: { border: '1px solid ' + HAIR, borderRadius: 12, background: '#fff', padding: '20px 18px', cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 9 } },
        h('span', { style: { height: 44, width: 44, borderRadius: 10, background: '#fdf2f2', display: 'grid', placeItems: 'center' } }, this.dashIcon(t[0], TEAL, 22)),
        h('div', { style: { fontSize: 15.5, fontWeight: 600 } }, t[1]),
        h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.6 } }, t[2]),
        h('span', { style: { fontSize: 12.5, fontWeight: 600, color: TEAL, marginTop: 'auto' } }, 'Order now →'))),
      // order steps
      h('section', { style: { background: ALT, borderRadius: 14, padding: '30px 26px', marginBottom: 26 } },
        h('h2', { style: { margin: '0 0 4px', fontSize: 22, fontWeight: 600, textAlign: 'center', letterSpacing: '-.02em' } }, 'Order in three steps'),
        h('p', { style: { margin: '0 0 24px', fontSize: 13.5, color: MUT, textAlign: 'center' } }, 'New to packaging? Here’s how to make your very own box order.'),
        h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 22 } },
          STEPS.map((s, i) => h('div', { key: i, style: { textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 } },
            h('div', { style: { position: 'relative', height: 66, width: 66, borderRadius: '50%', background: '#fff', border: '1px solid ' + HAIR, display: 'grid', placeItems: 'center' } },
              this.dashIcon(s[0], TEAL, 26),
              h('span', { style: { position: 'absolute', top: -6, right: -6, height: 24, width: 24, borderRadius: '50%', background: TEAL, color: '#fff', fontSize: 12, fontWeight: 700, display: 'grid', placeItems: 'center' } }, i + 1)),
            h('div', { style: { fontSize: 14.5, fontWeight: 600, maxWidth: 220 } }, s[1]),
            h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.6, maxWidth: 240 } }, s[2]))))),
      // details matter + finishing
      h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 22, marginBottom: 26 } },
        this.pkList('Details matter', 'Choose the right board for your product.', STOCKS),
        this.pkList('Finishing', 'Elevate your box with a premium finish.', FINISH)),
      // why printoka
      h('section', { style: { border: '1px solid ' + HAIR, borderRadius: 14, padding: '26px 24px', marginBottom: 8 } },
        h('h2', { style: { margin: '0 0 18px', fontSize: 20, fontWeight: 600, textAlign: 'center', letterSpacing: '-.02em' } }, 'Why Printoka for packaging'),
        h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 18 } },
          WHY.map((w, i) => h('div', { key: i, style: { display: 'flex', gap: 11 } },
            h('img', { src: window.__asset('assets/icons/check-circle.svg'), alt: '', style: { height: 18, width: 18, flex: 'none', marginTop: 1 } }),
            h('div', null, h('div', { style: { fontSize: 13.5, fontWeight: 600 } }, w[0]), h('div', { style: { fontSize: 12.5, color: MUT, marginTop: 3, lineHeight: 1.6 } }, w[1])))))));
  }
  pkBand(kicker, title, items, render) {
    return h('section', { style: { marginBottom: 26 } },
      h('div', { style: { fontSize: 11.5, fontWeight: 600, letterSpacing: '.09em', textTransform: 'uppercase', color: TEAL, marginBottom: 6 } }, kicker),
      h('h2', { style: { margin: '0 0 18px', fontSize: 22, fontWeight: 600, letterSpacing: '-.02em' } }, title),
      h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 16 } }, items.map(render)));
  }
  pkList(title, sub, rows) {
    return h('section', { style: { border: '1px solid ' + HAIR, borderRadius: 14, padding: '22px 22px' } },
      h('h3', { style: { margin: '0 0 3px', fontSize: 17, fontWeight: 600 } }, title),
      h('p', { style: { margin: '0 0 14px', fontSize: 13, color: MUT } }, sub),
      h('div', { style: { display: 'flex', flexDirection: 'column', gap: 12 } },
        rows.map((r, i) => h('div', { key: i, style: { display: 'flex', gap: 11 } },
          h('span', { style: { height: 8, width: 8, borderRadius: '50%', background: TEAL, flex: 'none', marginTop: 6 } }),
          h('div', null, h('div', { style: { fontSize: 13.5, fontWeight: 600 } }, r[0]), h('div', { style: { fontSize: 12.5, color: MUT, marginTop: 2, lineHeight: 1.6 } }, r[1]))))));
  }

  s_packaging() {
    const st = this.state;
    const tab = st.pkTab || 'library';
    const TABS = [['library', 'Box style library'], ['configure', 'Configurator'], ['quote', 'Spec, finishing & price'], ['dielines', 'Die-lines & orders']];

    const FAMILIES = [['All boxes', 54], ['Most popular', 5], ['— Basic boxes', 13], ['— Window boxes', 11], ['— Gift & display boxes', 9], ['— Hanging boxes', 8], ['— Tray & telescope', 3], ['— Folder & envelope', 1], ['— Sleeve', 1], ['Divider boxes', 4], ['Inner holding boxes', 7]];
    const MODELS = [
      ['M015', 'Divider boxes', 'Partition', 'divider'],
      ['K003', 'Gift & display', 'Tongue lock', 'basic'],
      ['K006', 'Gift & display', 'Top with dust lock', 'carton'],
      ['K016X', 'Gift & display', 'Cable with handle', 'hanging'],
      ['K024', 'Gift & display', '5 mm auto bottom lock', 'carton'],
      ['L046', 'Gift & display', 'Triangular cover', 'tray'],
      ['L082', 'Gift & display', 'Pillow box', 'sleeve'],
      ['Z039A', 'Gift & display', 'Straight tuck end (STE)', 'basic'],
      ['C012', 'Folder & envelope', 'Gift card envelope', 'sleeve'],
      ['O030', 'Window boxes', 'Window patch front', 'window'],
      ['M061', 'Inner holding', 'Four-cavity insert', 'insert'],
      ['A001X', 'Basic boxes', 'Reverse tuck end (RTE)', 'basic'],
    ];
    const LANES = [
      ['Short Run Packaging', '100 – 1,000 pcs', ['Gloss art card only', 'Gloss, matte and soft-touch lamination', 'Spot UV, hot stamping, window patching'], '2 process days', '4.62 / 5 · 18 reviews'],
      ['Standard Packaging', '1,000 – 100,000 pcs', ['All paper weights, 250–400 GSM', 'All finishing processes available', 'Emboss, spot UV, hot stamping, window patching'], '6 process days', '5.00 / 5 · 5 reviews'],
    ];

    const P = {};

    P.library = [
      h('div', { key: 'lanes', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 16 } },
        LANES.map((l, i) => h('div', { key: i, style: { border: '1px solid ' + HAIR, borderTop: '3px solid ' + (i ? '#231f20' : TEAL), background: '#fff', padding: '20px 22px' } },
          h('div', { style: { display: 'flex', gap: 10, alignItems: 'baseline', flexWrap: 'wrap', marginBottom: 4 } },
            h('span', { style: { fontSize: 16.5, fontWeight: 600 } }, l[0]),
            h('span', { style: { fontSize: 12.5, fontWeight: 600, color: TEAL } }, l[1])),
          h('div', { style: { fontSize: 11.5, color: FAINT, marginBottom: 10 } }, l[3]),
          h('div', { style: { display: 'flex', flexDirection: 'column', gap: 7 } },
            l[2].map((b, bi) => h('div', { key: bi, style: { display: 'flex', gap: 9, fontSize: 13, color: MUT, lineHeight: 1.55 } },
              h('img', { src: window.__asset ? window.__asset('assets/icons/check-circle.svg') : 'assets/icons/check-circle.svg', alt: '', style: { height: 14, width: 14, display: 'block', flex: 'none', marginTop: 2 } }), b)))))),
      h('div', { key: 'body', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 20, marginTop: 20, alignItems: 'start' } },
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 260 } },
          h('div', { style: { border: '1px solid ' + HAIR, background: '#fff' } },
            h('div', { style: { padding: '11px 14px', borderBottom: '1px solid ' + HAIR, fontSize: 12, fontWeight: 600, letterSpacing: '.06em', textTransform: 'uppercase', color: FAINT } }, 'Box family'),
            FAMILIES.map((f, i) => h('div', { key: i, style: { display: 'flex', justifyContent: 'space-between', gap: 10, padding: '9px 14px', borderTop: i ? '1px solid ' + LINE : 'none', fontSize: 13, cursor: 'pointer', background: '#fff', borderLeft: '2px solid ' + (i === 0 ? TEAL : 'transparent'), color: i === 0 ? TEAL : f[0].indexOf('—') === 0 ? MUT : INK, fontWeight: f[0].indexOf('—') === 0 ? 400 : 600, paddingLeft: f[0].indexOf('—') === 0 ? 24 : 14 } },
              h('span', null, f[0].replace('— ', '')), h('span', { style: { color: FAINT, fontSize: 12 } }, f[1])))),
          h('div', { style: { background: TEAL, color: '#fff', padding: '22px 20px', textAlign: 'center' } },
            h('div', { style: { fontSize: 14.5, fontWeight: 600, lineHeight: 1.5, marginBottom: 12 } }, 'Can’t find the style you need?'),
            h('span', { 'data-go': 'contact', style: { display: 'inline-block', background: '#fff', color: TEAL, fontSize: 13.5, fontWeight: 600, padding: '10px 20px', borderRadius: 2, cursor: 'pointer' } }, 'Get a custom quote'),
            h('div', { style: { fontSize: 12, marginTop: 10, opacity: .9 } }, 'For fully bespoke packaging and die-lines'))),
        h('div', null,
          h('div', { style: { display: 'flex', gap: 22, borderBottom: '1px solid ' + HAIR, marginBottom: 16, flexWrap: 'wrap' } },
            ['Box model', 'Product spec', 'Artwork spec', 'Tutorial'].map((t, i) =>
              h('span', { key: i, style: { padding: '0 0 12px', fontSize: 13.5, fontWeight: 600, color: i ? MUT : TEAL, borderBottom: '2px solid ' + (i ? 'transparent' : TEAL), marginBottom: -1, cursor: 'pointer' } }, t))),
          h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', marginBottom: 14 } },
            h('span', { style: { fontSize: 13, color: MUT } }, 'All boxes · 54 styles'),
            h('span', { style: { fontSize: 13, color: MUT } }, 'Sort: Most popular')),
          h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(190px,1fr))', gap: 16 } },
            MODELS.map((m, i) => h('div', { key: i, 'data-go': 'set:pkTab:configure', style: { border: '1px solid ' + HAIR, background: '#fff', padding: '16px 16px 18px', cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 4 } },
              this.dieline(m[3]),
              h('div', { style: { fontSize: 14.5, fontWeight: 600, color: TEAL, marginTop: 8 } }, m[0]),
              h('div', { style: { fontSize: 12.5, fontWeight: 500 } }, m[1]),
              h('div', { style: { fontSize: 12, color: MUT, lineHeight: 1.5 } }, m[2])))))),
    ];

    const step = st.pkStep === undefined ? 0 : st.pkStep;
    const STEPS = ['Size', 'Material', 'Processes', 'Quantity', 'Price'];
    const opt = (label, on, go, note) => h('span', { key: label, 'data-go': go, style: { position: 'relative', display: 'inline-flex', flexDirection: 'column', gap: 2, border: '1px solid ' + (on ? TEAL : HAIR), background: '#fff', padding: '11px 18px', fontSize: 13.5, color: INK, cursor: 'pointer', flex: '0 1 auto', minWidth: 0, textAlign: 'center', alignItems: 'center' } },
      label, note && h('span', { style: { fontSize: 11, color: FAINT } }, note),
      on && h('span', { style: { position: 'absolute', right: 0, bottom: 0, width: 0, height: 0, borderLeft: '9px solid transparent', borderBottom: '9px solid ' + TEAL } }));
    const row = (label, hint, children) => h('div', { key: label, style: { display: 'grid', gridTemplateColumns: 'minmax(120px,150px) minmax(0,1fr)', gap: 18, padding: '18px 0', borderTop: '1px solid ' + LINE, alignItems: 'start' } },
      h('div', null,
        h('div', { style: { fontSize: 14, fontWeight: 600 } }, label),
        hint && h('div', { style: { fontSize: 11.5, color: FAINT, marginTop: 3, lineHeight: 1.5 } }, hint)),
      h('div', { style: { display: 'flex', gap: 10, flexWrap: 'wrap' } }, children));

    const dimField = (label, value, unit) => h('div', { key: label, style: { display: 'flex', border: '1px solid ' + HAIR, background: '#fff', flex: '1 1 220px', minWidth: 0, maxWidth: 320 } },
      h('span', { style: { flex: '1 1 auto', minWidth: 0, background: ALT, padding: '10px 13px', fontSize: 13, color: MUT } }, label),
      h('span', { style: { flex: '0 0 auto', width: 78, padding: '10px 13px', fontSize: 13.5, fontWeight: 600, textAlign: 'right' } }, value),
      h('span', { style: { padding: '10px 13px', fontSize: 12.5, color: MUT, fontStyle: 'italic', borderLeft: '1px solid ' + HAIR } }, unit));

    const FORMS = [
      [row('Box template ID', null, [h('span', { style: { fontSize: 14, fontWeight: 600, color: TEAL } }, 'M015')]),
       row('Type', 'How the flat sheet is cut', [opt('Die-Cut', true, 'set:pkStep:0')]),
       row('Size', 'Minimums come from the die-line record', [
         h('div', { key: 'f', style: { display: 'flex', flexDirection: 'column', gap: 10 } },
           dimField('Length L ≥ 50', '80', 'mm'), dimField('Width W ≥ 20', '150', 'mm'),
           h('div', { style: { fontSize: 11.5, color: FAINT, lineHeight: 1.6, maxWidth: '46ch' } }, 'Caliper is taken from the chosen material — 0.3 mm at 250 GSM. Open sheet size recalculates to 401.2 × 150 mm.'))])],
      [row('Paper type', null, [opt('Gloss Art Card 1 Side Coated', true, 'set:pkStep:1'), opt('Boxboard Grey Back', false, 'set:pkStep:1')]),
       row('Standard weight', 'Short Run supports gloss art card only', ['250 GSM', '300 GSM', '350 GSM', '400 GSM'].map((g, i) => opt(g, i === 0, 'set:pkStep:1')))],
      [row('Printing', null, [opt('4 Colour Printing', true, 'set:pkStep:2')]),
       row('Coating', 'One coating per side', [opt('Gloss Lamination (Front)', true, 'set:pkStep:2'), opt('Matte Lamination (Front)', false, 'set:pkStep:2'), opt('Soft Touch Lamination (Front)', false, 'set:pkStep:2', 'New'), opt('Gloss Water Based Varnish', false, 'set:pkStep:2'), opt('UV Varnish (Front)', false, 'set:pkStep:2')]),
       row('Partial surface', 'Adds a die or plate charge', [opt('Embossing', false, 'set:pkStep:2'), opt('Spot UV', false, 'set:pkStep:2'), opt('Hot Stamping', false, 'set:pkStep:2')]),
       row('Others', null, [opt('Die-Cut', true, 'set:pkStep:2')])],
      [row('Quantity', 'Fixed break points — pricing is per print run', [
         h('div', { key: 'q', style: { display: 'flex', border: '1px solid ' + HAIR } },
           h('span', { style: { padding: '10px 16px', borderRight: '1px solid ' + HAIR, cursor: 'pointer', color: MUT } }, '−'),
           h('span', { style: { padding: '10px 26px', fontSize: 14, fontWeight: 600 } }, '300'),
           h('span', { style: { padding: '10px 16px', borderLeft: '1px solid ' + HAIR, cursor: 'pointer', color: MUT } }, '+'))]),
       row('Job name', 'Shown on the order slip and in your dashboard', [h('span', { key: 'n', style: { border: '1px solid ' + HAIR, padding: '10px 13px', fontSize: 13, color: FAINT, flex: '1 1 auto', minWidth: 0, width: '100%' } }, 'e.g. Studio North candle carton')]),
       row('Note to prepress', null, [h('span', { key: 'n', style: { border: '1px solid ' + HAIR, padding: '10px 13px', fontSize: 13, color: FAINT, flex: '1 1 auto', minWidth: 0, width: '100%', minHeight: 68, display: 'block' } }, 'Anything the operator should know before die-cutting')])],
      [h('div', { key: 'sum', style: { border: '1px solid ' + HAIR } },
        [['Box template ID', 'M015'], ['Size mode', 'Die-Cut'], ['Dimensions', 'Length 80 mm · Width 150 mm · Caliper 0.3 mm'], ['Materials', 'Main paper · Gloss Art Card 1 Side Coated (250 GSM)'], ['Processes', '4 Colour Printing · Gloss Lamination (Front) · Die-Cut'], ['Note', '—'], ['Quantity', '300']]
          .map((r, i) => h('div', { key: i, style: { display: 'grid', gridTemplateColumns: 'minmax(110px,150px) minmax(0,1fr) 22px', gap: 14, padding: '13px 16px', borderTop: i ? '1px solid ' + LINE : 'none', background: i % 2 ? ALT : '#fff', alignItems: 'center' } },
            h('span', { style: { fontSize: 13, fontWeight: 600 } }, r[0]),
            h('span', { style: { fontSize: 13, color: MUT, lineHeight: 1.6 } }, r[1]),
            h('span', { 'data-go': 'set:pkStep:' + Math.min(i, 3), style: { fontSize: 13, color: TEAL, cursor: 'pointer', textAlign: 'right' } }, '›')))),
       h('div', { key: 'zone', style: { display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap', marginTop: 16 } },
         h('span', { style: { fontSize: 14, fontWeight: 600 } }, 'Delivery zone'),
         h('span', { style: { border: '1px solid ' + HAIR, padding: '9px 14px', fontSize: 13, color: INK } }, 'West Malaysia'),
         h('span', { style: { fontSize: 12, color: FAINT } }, 'Zone sets the courier list and free-shipping threshold'))],
    ];

    P.configure = [
      h('div', { key: 'w', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 0, border: '1px solid ' + HAIR, background: '#fff' } },
        h('div', { style: { borderRight: '1px solid ' + HAIR, display: 'flex', flexDirection: 'column' } },
          h('div', { style: { display: 'flex', alignItems: 'center', gap: 12, padding: '11px 14px', background: '#231f20', color: '#fff' } },
            h('span', { style: { fontSize: 11.5, fontWeight: 600, letterSpacing: '.06em' } }, 'JOB #1 · M015'),
            h('span', { style: { fontSize: 11.5, opacity: .72, marginLeft: 'auto' } }, 'Fold preview')),
          h('div', { style: { flex: 1, minHeight: 300, display: 'grid', placeItems: 'center', padding: 24, background: '#fff' } },
            h('div', { style: { width: '100%', maxWidth: 320, transform: 'perspective(700px) rotateX(8deg) rotateY(-22deg)', filter: 'drop-shadow(0 12px 18px rgba(33,33,33,.18))' } }, this.dieline('divider', null, 180))),
          h('div', { style: { display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', borderTop: '1px solid ' + HAIR, background: ALT, flexWrap: 'wrap' } },
            ['Orbit', 'Pause'].map((c, i) => h('span', { key: i, style: { border: '1px solid ' + HAIR, background: '#fff', padding: '5px 10px', fontSize: 11.5, fontWeight: 600, color: MUT, cursor: 'pointer' } }, c)),
            h('span', { style: { flex: 1, minWidth: 90, height: 4, borderRadius: 999, background: LINE, position: 'relative' } },
              h('span', { style: { position: 'absolute', inset: 0, width: '45%', background: TEAL, borderRadius: 999 } }),
              h('span', { style: { position: 'absolute', left: '45%', top: -6, height: 16, width: 16, marginLeft: -8, borderRadius: '50%', background: '#fff', border: '1px solid ' + HAIR, boxShadow: '0 1px 4px rgba(33,33,33,.2)' } })),
            h('span', { style: { fontSize: 11.5, color: FAINT } }, 'Fold progress'))),
        h('div', { style: { display: 'flex', flexDirection: 'column' } },
          h('div', { style: { padding: '12px 18px', background: '#231f20', color: '#fff', fontSize: 13, fontWeight: 600, letterSpacing: '.04em', textTransform: 'uppercase', textAlign: 'center' } }, (step + 1) + ' / 6 — ' + STEPS[step]),
          h('div', { style: { padding: '4px 18px 18px' } }, FORMS[step]),
          h('div', { style: { marginTop: 'auto' } },
            h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', background: ALT, borderTop: '1px solid ' + HAIR } },
              STEPS.map((s, i) => h('span', { key: i, 'data-go': 'set:pkStep:' + i, style: { padding: '14px 6px', textAlign: 'center', fontSize: 12, fontWeight: 600, color: i === step ? TEAL : MUT, borderBottom: '3px solid ' + (i === step ? TEAL : 'transparent'), cursor: 'pointer' } }, (i + 1) + '. ' + s))),
            h('div', { 'data-go': 'set:pkTab:quote', style: { background: TEAL, color: '#fff', padding: '15px 18px', textAlign: 'center', fontSize: 15, fontWeight: 600, cursor: 'pointer' } }, 'Continue to get offer price')))),
      h('div', { key: 'n', style: { marginTop: 14, border: '1px solid ' + HAIR, background: ALT, padding: 16, fontSize: 12.5, color: MUT, lineHeight: 1.75 } },
        h('b', { style: { color: INK } }, 'Artwork comes later: '), 'the die-line is generated from these dimensions, so the customer can download it, design against it and upload artwork after the order is placed — shipment and delivery dates firm up once artwork passes prepress.'),
    ];

    const RATES = [
      [300, 921.35, 3.07, 6, 413.65, 1.38, 2],
      [500, 1042.60, 2.09, 6, 486.20, 0.97, 2],
      [1000, 1318.40, 1.32, 6, 648.90, 0.65, 3],
      [2000, 1836.00, 0.92, 6, null, null, null],
      [5000, 3204.50, 0.64, 7, null, null, null],
      [10000, 4980.00, 0.50, 7, null, null, null],
      [30000, 9642.00, 0.32, 7, null, null, null],
      [70000, 14521.20, 0.21, 7, null, null, null],
    ];
    const qi = Math.min(st.pkQty || 0, RATES.length - 1), rate = RATES[qi];
    const shortRunOK = rate[4] !== null;
    const lane = !shortRunOK ? 'Standard' : (st.pkLane || 'Short Run');
    const laneTotal = lane === 'Standard' ? rate[1] : rate[4];
    const lanePer = lane === 'Standard' ? rate[2] : rate[5];
    const laneDays = lane === 'Standard' ? rate[3] : rate[6];
    const tierOff = this.tierPct() / 100;
    const nett = laneTotal * (1 - tierOff);
    const sst = this.cc() === 'MY' ? 0.08 : this.cc() === 'SG' ? 0.09 : 0;
    const QTY = RATES.map(r => r[0].toLocaleString('en-US'));
    const laneCard = (name, total, per, days, on) => h('div', { key: name, 'data-go': 'set:pkLane:' + name, style: { border: '1px solid ' + (on ? TEAL : HAIR), background: on ? '#fdf6f6' : '#fff', padding: '22px 20px', cursor: 'pointer', position: 'relative' } },
      h('div', { style: { display: 'flex', alignItems: 'center', gap: 9, justifyContent: 'center', marginBottom: 14 } },
        h('span', { style: { height: 18, width: 18, borderRadius: '50%', border: '2px solid ' + (on ? TEAL : HAIR), background: on ? TEAL : '#fff', display: 'grid', placeItems: 'center', color: '#fff', fontSize: 10, fontWeight: 700 } }, on ? '✓' : ''),
        h('span', { style: { fontSize: 15.5, fontWeight: 600 } }, name)),
      h('div', { style: { display: 'flex', gap: 18, justifyContent: 'center', alignItems: 'center', borderBottom: '1px solid ' + HAIR, paddingBottom: 14, marginBottom: 14 } },
        h('div', { style: { textAlign: 'center' } },
          h('div', { style: { fontSize: 11.5, color: FAINT } }, 'from'),
          h('div', { style: { fontSize: 21, fontWeight: 600, whiteSpace: 'nowrap' } }, this.money(total)),
          h('div', { style: { fontSize: 11.5, color: FAINT } }, per.toFixed(per < 1 ? 3 : 2) + '/pc')),
        h('div', { style: { textAlign: 'center', borderLeft: '1px solid ' + HAIR, paddingLeft: 18 } },
          h('div', { style: { fontSize: 21, fontWeight: 600 } }, days),
          h('div', { style: { fontSize: 11.5, color: FAINT } }, 'process days'))),
      h('div', { style: { display: 'flex', flexDirection: 'column', gap: 8 } },
        [['Standard price', 0, 'Cash'], ['Discount 4%', .04, 'Silver'], ['Discount 8%', .08, 'Gold'], ['Discount 14%', .14, 'Platinum']].map((d, i) =>
          h('div', { key: i, style: { display: 'flex', alignItems: 'center', gap: 11, border: '1px solid ' + HAIR, background: '#fff', padding: '9px 12px' } },
            h('span', { style: { flex: 'none', height: 26, width: 26, borderRadius: '50%', display: 'grid', placeItems: 'center', fontSize: 8, fontWeight: 700, color: '#fff', background: ['#9aa4ad', '#7f8992', AMBER, '#231f20'][i] } }, d[2].slice(0, 4).toUpperCase()),
            h('span', { style: { minWidth: 0 } },
              h('span', { style: { display: 'block', fontSize: 12.5, fontWeight: 600 } }, d[0]),
              h('span', { style: { display: 'block', fontSize: 12, color: MUT } }, this.money(total * (1 - d[1])) + ' · ' + (per * (1 - d[1])).toFixed(per < 1 ? 3 : 2) + '/pc'))))));

    P.quote = [
      h('div', { key: 'g', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 20, alignItems: 'start' } },
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: 18 } },
          h('div', { style: { border: '1px solid ' + HAIR } },
            h('div', { style: { background: ALT, color: INK, padding: '12px 15px', borderBottom: '1px solid ' + HAIR, fontSize: 11.5, fontWeight: 600, letterSpacing: '.07em', textTransform: 'uppercase' } }, 'Product spec'),
            [['Box model', 'M015 · Divider box, partition lock'], ['Open size (H × W)', '401.2 mm × 150 mm'], ['Dimension (L × W × D)', '80 mm × 150 mm × 0.3 mm'], ['Paper', 'Gloss Art Card 250 gsm (1 side coated)'], ['Run', QTY[qi] + ' pcs · ' + lane + ' lane · ' + laneDays + ' process days']]
              .map((r, i) => h('div', { key: i, style: { display: 'grid', gridTemplateColumns: 'minmax(120px,170px) minmax(0,1fr)', gap: 14, padding: '12px 14px', borderTop: i ? '1px solid ' + LINE : 'none' } },
                h('span', { style: { fontSize: 12.5, fontWeight: 600 } }, r[0]), h('span', { style: { fontSize: 12.5, color: MUT } }, r[1])))),
          h('div', { style: { border: '1px solid ' + HAIR } },
            h('div', { style: { background: ALT, color: INK, padding: '12px 15px', borderBottom: '1px solid ' + HAIR, fontSize: 11.5, fontWeight: 600, letterSpacing: '.07em', textTransform: 'uppercase' } }, 'Finishing'),
            h('div', { style: { padding: '12px 14px 2px', fontSize: 12, color: MUT, lineHeight: 1.6 } }, 'Change any finishing option here — the price recalculates immediately.'),
            h('div', { style: { padding: '0 14px 14px' } },
              row('Lamination', null, [opt('Gloss (Front)', true, 'set:pkTab:quote'), opt('Matte (Front)', false, 'set:pkTab:quote'), opt('Soft touch (Front)', false, 'set:pkTab:quote', 'New')]),
              row('Emboss', 'Adds an embossing die charge', [opt('Not required', false, 'set:pkTab:quote'), opt('Required', true, 'set:pkTab:quote'), dimField('Emboss size (H)', '40', 'mm'), dimField('Emboss size (W)', '25', 'mm')]),
              row('Spot UV', null, [opt('Not required', true, 'set:pkTab:quote'), opt('Required', false, 'set:pkTab:quote')]),
              row('Hot stamping', null, [opt('Not required', true, 'set:pkTab:quote'), opt('Required', false, 'set:pkTab:quote')]))),
          h('div', { style: { border: '1px solid ' + HAIR } },
            h('div', { style: { background: ALT, color: INK, padding: '12px 15px', borderBottom: '1px solid ' + HAIR, fontSize: 11.5, fontWeight: 600, letterSpacing: '.07em', textTransform: 'uppercase' } }, 'Ordering option & quantity'),
            h('div', { style: { padding: 14, display: 'flex', flexDirection: 'column', gap: 14 } },
              h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.7 } }, 'Request a sample for colour proofing and application testing before committing to the full run.'),
              h('div', { style: { display: 'flex', gap: 10, alignItems: 'center', fontSize: 13 } }, h('span', { style: { height: 15, width: 15, border: '1px solid ' + HAIR, display: 'inline-block' } }), 'Order mockup / sample'),
              h('div', null,
                h('div', { style: { fontSize: 13, fontWeight: 600, marginBottom: 8 } }, 'Quantity (mass production)'),
                h('div', { style: { display: 'flex', gap: 8, flexWrap: 'wrap' } },
                  QTY.map((q, i) => h('span', { key: i, 'data-go': 'set:pkQty:' + i, style: { border: '1px solid ' + ((st.pkQty || 0) === i ? TEAL : HAIR), background: (st.pkQty || 0) === i ? TEAL : '#fff', color: (st.pkQty || 0) === i ? '#fff' : INK, padding: '8px 14px', fontSize: 13, fontWeight: 600, cursor: 'pointer' } }, q)))),
              h('div', { style: { fontSize: 13, fontWeight: 600, marginTop: 4 } }, 'Choose your option according to the quantity chosen'),
              h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(230px,1fr))', gap: 14 } },
                laneCard('Standard', rate[1], rate[2], rate[3], lane === 'Standard'),
                shortRunOK
                  ? laneCard('Short Run', rate[4], rate[5], rate[6], lane === 'Short Run')
                  : h('div', { key: 'sr', style: { border: '1px dashed ' + HAIR, background: ALT, padding: '22px 20px', display: 'flex', flexDirection: 'column', gap: 8, justifyContent: 'center' } },
                      h('div', { style: { fontSize: 15.5, fontWeight: 600, color: MUT } }, 'Short Run'),
                      h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.7 } }, 'Not available at ' + QTY[qi] + ' pcs. Short Run covers 100 – 1,000 pcs on gloss art card only; above that the job runs on the Standard litho lane.'),
                      h('span', { 'data-go': 'set:pkQty:2', style: { alignSelf: 'flex-start', fontSize: 12.5, fontWeight: 600, color: TEAL, cursor: 'pointer' } }, 'Price 1,000 pcs instead'))))),
          h('div', { style: { border: '1px solid ' + HAIR } },
            h('div', { style: { background: ALT, color: INK, padding: '12px 15px', borderBottom: '1px solid ' + HAIR, fontSize: 11.5, fontWeight: 600, letterSpacing: '.07em', textTransform: 'uppercase' } }, 'Delivery'),
            h('div', { style: { padding: 14, display: 'flex', flexDirection: 'column', gap: 12 } },
              h('div', { style: { display: 'flex', gap: 20, flexWrap: 'wrap', fontSize: 12.5 } },
                h('span', null, h('b', null, 'Country: '), 'West Malaysia'),
                h('span', null, h('b', null, 'Courier: '), 'Appointed courier (free shipping)')),
              h('div', { style: { border: '1px solid ' + HAIR, background: ALT, padding: 13, fontSize: 12.5, color: MUT, lineHeight: 1.7 } },
                h('div', { style: { fontWeight: 600, color: TEAL, marginBottom: 3 } }, 'Studio North Sdn Bhd · Aiman Lim'),
                'Lot 8, Jalan Sungai Kayu Ara 32/38, Section 32, Berjaya Industrial Park, 40460 Shah Alam, Selangor'),
              h('div', { style: { display: 'flex', gap: 10, flexWrap: 'wrap' } }, this.btn('Add new address', 'ghost', 'packaging', { borderRadius: 2 }), this.btn('Change', 'ghost', 'packaging', { borderRadius: 2 })),
              h('div', { style: { fontSize: 13, fontWeight: 600, marginTop: 4 } }, 'Or self-pickup for an extra discount'),
              h('div', { style: { display: 'flex', flexDirection: 'column', gap: 7 } },
                [['KL Damansara', true], ['Miri (own facility)', false], ['Johor Bahru', false], ['Seri Kembangan', false], ['Bandar Puteri Klang', true]]
                  .map((o, i) => h('div', { key: i, style: { display: 'flex', gap: 9, alignItems: 'center', fontSize: 12.5 } },
                    h('span', { style: { height: 13, width: 13, borderRadius: '50%', border: '1px solid ' + HAIR, flex: 'none' } }),
                    h('span', null, 'Self-pickup · ' + o[0]),
                    h('span', { style: { fontSize: 11, fontWeight: 600, color: TEAL } }, 'Extra 5% off'),
                    o[1] && this.chip('New', 'ok'))))))),
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: 16, position: 'sticky', top: 84 } },
          h('div', { style: { border: '1px solid ' + HAIR, borderTop: '3px solid ' + TEAL, background: '#fff' } },
            h('div', { style: { background: TEAL, color: '#fff', padding: '12px 15px', fontSize: 11.5, fontWeight: 600, letterSpacing: '.07em', textTransform: 'uppercase', display: 'flex', justifyContent: 'space-between', gap: 10 } },
              h('span', null, 'Product · packaging'),
              h('span', { style: { cursor: 'pointer' } }, 'Slip ↓')),
            h('div', { style: { background: '#fff', padding: '14px 16px', borderBottom: '1px solid ' + HAIR } }, this.dieline('divider', null, 70)),
            h('div', { style: { padding: '12px 16px', background: '#fff' } },
              [['Open size (H × W)', '401.2 mm × 150 mm'], ['Dimension (L × W × D)', '80 × 150 × 0.3 mm'], ['Lock type', 'Partition']]
                .map((r, i) => h('div', { key: i, style: { display: 'flex', justifyContent: 'space-between', gap: 12, padding: '7px 0', borderTop: i ? '1px solid ' + LINE : 'none', fontSize: 12 } },
                  h('span', { style: { color: MUT } }, r[0]), h('span', { style: { fontWeight: 600, textAlign: 'right' } }, r[1])))),
            h('div', { style: { padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 10 } },
              h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'baseline' } },
                h('span', { style: { fontSize: 13, fontWeight: 600 } }, 'Nett price'),
                h('span', { style: { fontSize: 17, fontWeight: 600, color: TEAL, whiteSpace: 'nowrap' } }, this.money(nett))),
              h('div', { style: { fontSize: 11.5, color: MUT, lineHeight: 1.7 } }, lane + ' lane · ' + QTY[qi] + ' pcs · ' + laneDays + ' process days · ' + this.tier() + ' tier ' + this.tierPct() + '% off applied. Shipment and delivery dates become available once artwork is confirmed.'),
              h('div', { style: { display: 'flex', gap: 9, fontSize: 11.5, color: MUT, lineHeight: 1.6 } },
                h('span', { style: { height: 14, width: 14, border: '1px solid ' + HAIR, background: '#fff', flex: 'none', marginTop: 1 } }),
                'I confirm I have read and understood the Terms and Conditions.'),
              h('div', { 'data-go': 'checkout', style: { background: TEAL, color: '#fff', padding: '12px 16px', textAlign: 'center', fontSize: 14, fontWeight: 600, cursor: 'pointer' } }, 'Submit order'),
              h('div', { 'data-go': 'set:pkTab:dielines', style: { border: '1px solid ' + TEAL, background: '#fff', color: TEAL, padding: '11px 16px', textAlign: 'center', fontSize: 13.5, fontWeight: 600, cursor: 'pointer' } }, 'Free die-line (29 downloads left)'),
              h('div', { 'data-go': 'set:pkTab:configure', style: { border: '1px solid ' + HAIR, background: '#fff', padding: '11px 16px', textAlign: 'center', fontSize: 13.5, fontWeight: 600, color: MUT, cursor: 'pointer' } }, 'Back to configurator'))),
          h('div', { style: { border: '1px solid ' + HAIR, background: '#fff' } },
            h('div', { style: { background: ALT, color: INK, padding: '12px 15px', borderBottom: '1px solid ' + HAIR, fontSize: 11.5, fontWeight: 600, letterSpacing: '.07em', textTransform: 'uppercase' } }, 'Nett price for deal'),
            [['Price before discount', this.money(laneTotal)], ['Membership discount · ' + this.tier() + ' ' + this.tierPct() + '%', '− ' + this.money(laneTotal * tierOff)], [this.taxLabel(), this.money(nett * sst)], ['Delivery fee', this.money(0)]]
              .map((r, i) => h('div', { key: i, style: { display: 'flex', justifyContent: 'space-between', gap: 12, padding: '10px 14px', borderTop: i ? '1px solid ' + LINE : 'none', fontSize: 12.5, color: MUT } },
                h('span', null, r[0]), h('span', { style: { whiteSpace: 'nowrap', color: INK } }, r[1]))),
            h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: 12, padding: '12px 14px', borderTop: '1px solid ' + HAIR, background: ALT, fontSize: 14, fontWeight: 600 } },
              h('span', null, 'Total amount'), h('span', { style: { whiteSpace: 'nowrap' } }, this.money(nett * (1 + sst))))),
          h('div', { style: { backgroundImage: 'linear-gradient(90deg,#FF9A2E,#F02B29)', color: '#fff', padding: '16px 18px' } },
            h('div', { style: { fontSize: 13.5, fontWeight: 600, marginBottom: 8 } }, 'Reach the next tier and pay less on this order'),
            [['Silver', 8], ['Gold', 10], ['Platinum', 15]].map((t, i) =>
              h('div', { key: i, style: { display: 'flex', justifyContent: 'space-between', gap: 10, padding: '6px 0', borderTop: i ? '1px solid rgba(255,255,255,.28)' : 'none', fontSize: 12.5 } },
                h('span', null, t[0] + ' · ' + t[1] + '% off'), h('span', { style: { fontWeight: 600, whiteSpace: 'nowrap' } }, this.money(laneTotal * (1 - t[1] / 100))))),
            h('span', { 'data-go': 'membership', style: { display: 'inline-block', marginTop: 10, background: '#fff', color: TEAL, fontSize: 12.5, fontWeight: 600, padding: '9px 16px', cursor: 'pointer' } }, 'See how tiers work')))),
    ];

    const dtab = st.pkDtab || 'dieline';
    const DROWS = [
      ['2026-09-10 09:34', 'M015', '80 × 150 × 0.3 mm', 'Divider box · partition', '10-11-2026'],
      ['2026-09-02 15:12', 'K024', '120 × 80 × 40 mm', 'Auto bottom lock carton', '02-11-2026'],
      ['2026-08-21 11:48', 'O030', '90 × 90 × 30 mm', 'Window box, front patch', '21-10-2026'],
    ];
    P.dielines = [
      h('div', { key: 'top', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 16 } },
        h('div', { style: { backgroundImage: 'linear-gradient(90deg,#FF9A2E,#F02B29)', color: '#fff', padding: '28px 30px', display: 'flex', flexDirection: 'column', justifyContent: 'center' } },
          h('div', { style: { fontSize: 11.5, fontWeight: 600, letterSpacing: '.12em', textTransform: 'uppercase' } }, 'Every packaging repeat order'),
          h('div', { style: { fontSize: 'clamp(21px,2.6vw,27px)', fontWeight: 600, margin: '8px 0 6px', letterSpacing: '-.01em' } }, '5% off, or min ' + this.money(100)),
          h('div', { style: { fontSize: 13, lineHeight: 1.6 } }, 'Not applicable to Short Run packaging')),
        h('div', { style: { border: '1px solid ' + HAIR, background: '#fff', padding: '22px 26px', display: 'flex', gap: 22, alignItems: 'center', flexWrap: 'wrap' } },
          h('div', { style: { flex: 'none', height: 96, width: 96, borderRadius: '50%', background: 'conic-gradient(' + TEAL + ' 0 96.6%, ' + LINE + ' 0)', display: 'grid', placeItems: 'center' } },
            h('div', { style: { height: 74, width: 74, borderRadius: '50%', background: '#fff', display: 'grid', placeItems: 'center', textAlign: 'center' } },
              h('div', null,
                h('div', { style: { fontSize: 19, fontWeight: 600, color: TEAL } }, '29', h('span', { style: { fontSize: 12, color: FAINT } }, '/30')),
                h('div', { style: { fontSize: 9.5, color: FAINT } }, 'downloads')))),
          h('div', { style: { minWidth: 0 } },
            h('div', { style: { fontSize: 14.5, fontWeight: 600, marginBottom: 4 } }, 'Free die-line downloads'),
            h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.65, marginBottom: 10 } }, 'Your monthly balance by membership tier. Each download stays re-orderable until it expires.'),
            this.btn('Upgrade to get more', 'teal', 'membership', { borderRadius: 2 })))),
      h('div', { key: 'tabs', style: { display: 'flex', gap: 24, marginTop: 24, marginBottom: 18, flexWrap: 'wrap', borderBottom: '1px solid ' + HAIR } },
        [['mockup', 'Mockup orders', 1], ['complete', 'Complete orders', 6], ['dieline', 'Free die-lines', DROWS.length]].map(t =>
          h('span', { key: t[0], 'data-go': 'set:pkDtab:' + t[0], style: { display: 'flex', gap: 7, alignItems: 'center', padding: '0 0 12px', fontSize: 14, fontWeight: 600, cursor: 'pointer', color: dtab === t[0] ? TEAL : MUT, borderBottom: '2px solid ' + (dtab === t[0] ? TEAL : 'transparent'), marginBottom: -1 } },
            t[1], h('span', { style: { fontSize: 11.5, color: FAINT } }, t[2])))),
      h('div', { key: 'panel', style: { border: '1px solid ' + HAIR, background: '#fff', padding: 18 } },
        h('div', { style: { display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 16 } },
          h('span', { style: { border: '1px solid ' + HAIR, padding: '9px 14px', fontSize: 13, color: MUT } }, '10/03/2026 – 10/09/2026'),
          this.btn('Search', 'teal', 'packaging', { borderRadius: 2 }),
          h('span', { style: { marginLeft: 'auto', fontSize: 12.5, color: FAINT } }, 'Showing 1 to ' + DROWS.length + ' of ' + DROWS.length + ' jobs')),
        dtab === 'dieline'
          ? this.table(['Downloaded', 'Model', 'Dimension (L × W × D)', 'Style', 'Expires', ''],
              DROWS.map(r => [r[0], h('span', { style: { fontWeight: 600, color: TEAL } }, r[1]), r[2], r[3], r[4],
                h('span', { style: { display: 'flex', gap: 12, justifyContent: 'flex-end' } },
                  h('span', { style: { fontSize: 12.5, fontWeight: 600, color: TEAL, cursor: 'pointer', whiteSpace: 'nowrap' } }, 'Download die-line'),
                  h('span', { 'data-go': 'set:pkTab:quote', style: { fontSize: 12.5, fontWeight: 600, color: INK, cursor: 'pointer' } }, 'Re-order'))]),
              ['16%', '9%', '20%', '20%', '11%', '24%'])
          : dtab === 'mockup'
            ? this.table(['Job', 'Model', 'Requested', 'Status', ''],
                [['Studio North candle carton', 'M015', '08 Sep 2026', this.chip('Mockup in production', 'warn'), h('span', { style: { fontSize: 12.5, fontWeight: 600, color: TEAL, cursor: 'pointer', textAlign: 'right', display: 'block' } }, 'Track')]],
                ['32%', '12%', '18%', '22%', '16%'])
            : this.table(['Order', 'Model', 'Quantity', 'Shipped', 'Total', ''],
                [['PO-2026-04288', 'K024', '2,000', '30 Aug 2026', this.money(1204), h('span', { 'data-go': 'set:pkTab:quote', style: { fontSize: 12.5, fontWeight: 600, color: TEAL, cursor: 'pointer', textAlign: 'right', display: 'block' } }, 'Repeat · 5% off')],
                 ['PO-2026-03960', 'O030', '5,000', '25 Jul 2026', this.money(2880.15), h('span', { 'data-go': 'set:pkTab:quote', style: { fontSize: 12.5, fontWeight: 600, color: TEAL, cursor: 'pointer', textAlign: 'right', display: 'block' } }, 'Repeat · 5% off')]],
                ['22%', '11%', '13%', '17%', '15%', '22%']),
        h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', marginTop: 14, fontSize: 12.5, color: MUT } },
          h('span', null, 'Show 10 entries'),
          h('span', { style: { display: 'flex', gap: 12 } }, h('span', null, 'Previous'), h('span', { style: { fontWeight: 600, color: TEAL } }, '1'), h('span', null, 'Next')))),
      h('div', { key: 'note', style: { marginTop: 16, border: '1px solid ' + HAIR, background: ALT, padding: 16, fontSize: 12.5, color: MUT, lineHeight: 1.75 } },
        h('b', { style: { color: INK } }, 'What the die-line PDF contains: '), 'a single-page vector file of cut, crease and bleed lines only — no artwork — at the exact dimensions ordered, so the customer’s designer can work straight on top of it and prepress can verify against the same record.'),
    ];

    return h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '10px 20px 0' } },
      h('div', { style: { fontSize: 12.5, color: FAINT, marginBottom: 12 } },
        h('span', { 'data-go': 'home', style: { color: TEAL } }, 'Home'), ' › Products › Custom Packaging Boxes'),
      this.packagingHero(),
      h('div', { style: { fontSize: 11.5, fontWeight: 600, letterSpacing: '.09em', textTransform: 'uppercase', color: TEAL, margin: '10px 0 4px' } }, 'Start your order'),
      h('h2', { style: { margin: '0 0 6px', fontSize: 22, fontWeight: 600, letterSpacing: '-.02em' } }, 'Die-line-first box configurator'),
      h('p', { style: { margin: '0 0 6px', fontSize: 13.5, color: MUT, maxWidth: '68ch', lineHeight: 1.7 } }, 'Pick a box style, set its size, and choose your material and finishing. See the price at every tier before you submit. Add artwork once you download the die-line.'),
      h('div', { style: { display: 'flex', gap: 22, borderBottom: '1px solid ' + HAIR, margin: '20px 0 20px', flexWrap: 'wrap' } },
        TABS.map(t => h('span', { key: t[0], 'data-go': 'set:pkTab:' + t[0], style: { padding: '0 0 12px', fontSize: 14, fontWeight: 600, color: tab === t[0] ? TEAL : MUT, borderBottom: '2px solid ' + (tab === t[0] ? TEAL : 'transparent'), marginBottom: -1, cursor: 'pointer' } }, t[1]))),
      P[tab],
      tab === 'quote'
        ? this.mobileBar('M015 · ' + QTY[qi] + ' pcs · ' + lane, this.money(nett), 'Submit order', 'checkout')
        : null);
  }

  // ===== CATEGORY LISTING =====

  s_category() {
    const active = this.state.catFilter || 'all';
    const cats = [{ id: 'all', label: 'All products' }].concat(this.catCategories());
    const items = this.catProducts(active);
    // left sidebar: category menu (matches the original site's side-nav)
    const sidebar = h('aside', { key: 'side', style: { position: 'sticky', top: 122, alignSelf: 'start' } },
      h('div', { style: { fontSize: 11, fontWeight: 600, letterSpacing: '.08em', textTransform: 'uppercase', color: FAINT, padding: '0 4px 10px' } }, 'Categories'),
      h('div', { style: { border: '1px solid ' + HAIR, borderRadius: 12, overflow: 'hidden', background: '#fff' } },
        cats.map((c, i) => {
          const on = c.id === active, n = c.id === 'all' ? this.pkProducts().length : this.catProducts(c.id).length;
          return h('div', { key: c.id, 'data-go': 'set:catFilter:' + c.id, style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, padding: '11px 14px', borderTop: i ? '1px solid ' + LINE : 'none', borderLeft: '3px solid ' + (on ? TEAL : 'transparent'), background: on ? '#fdf2f2' : '#fff', color: on ? TEAL : INK, fontSize: 13.5, fontWeight: on ? 600 : 500, cursor: 'pointer' } },
            h('span', null, c.label), h('span', { style: { fontSize: 11.5, color: on ? TEAL : FAINT } }, n));
        })),
      h('div', { 'data-go': 'packaging', style: { marginTop: 10, border: '1px solid ' + HAIR, borderRadius: 12, padding: '13px 14px', background: ALT, cursor: 'pointer' } },
        h('div', { style: { fontSize: 13.5, fontWeight: 600, marginBottom: 3 } }, 'Custom Packaging Boxes →'),
        h('div', { style: { fontSize: 12, color: MUT, lineHeight: 1.55 } }, 'Design your own box, sleeve or E-flute mailer.')));
    const seo = this.categorySeo(active);
    return h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '10px 20px 0' } },
      h('div', { style: { fontSize: 12.5, color: FAINT, marginBottom: 12 } },
        h('span', { 'data-go': 'home', style: { color: TEAL } }, 'Home'), ' › Products', active !== 'all' ? ' › ' + this.catCategoryLabel(active) : ''),
      this.head(active === 'all' ? 'Online Printing' : this.catCategoryLabel(active) + ' Printing',
        active === 'all'
          ? 'Browse every product Printoka prints. ' + this.pkProducts().length + ' products across ' + this.catCategories().length + ' categories, each priced online in seconds.'
          : seo.lead),
      h('div', { style: { display: 'grid', gridTemplateColumns: '232px minmax(0,1fr)', gap: 26, alignItems: 'start', marginTop: 18 } },
        sidebar,
        h('div', null,
          h('div', { key: 'count', style: { fontSize: 13, color: MUT, marginBottom: 14 } }, items.length + ' products' + (active === 'all' ? '' : ' in ' + this.catCategoryLabel(active))),
          h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(210px,1fr))', gap: 16 } },
            items.map(p => {
              const from = this.catFromPrice(p.id), moq = this.catMoq(p.id);
              return h('a', { key: p.id, href: this.productPath(p.id) || undefined, 'data-go': 'open:' + p.id, style: { border: '1px solid ' + HAIR, borderRadius: 12, background: '#fff', overflow: 'hidden', display: 'flex', flexDirection: 'column', cursor: 'pointer', color: 'inherit', textDecoration: 'none' } },
                this.art(p.engName),
                h('div', { style: { padding: '13px 14px', display: 'flex', flexDirection: 'column', gap: 6, flex: 1 } },
                  h('span', { style: { fontSize: 13.5, fontWeight: 500, lineHeight: 1.3, minHeight: 34 } }, p.name),
                  h('span', { style: { fontSize: 11, color: FAINT } }, moq != null ? ('Min. order ' + moq.toLocaleString() + ' pcs') : this.catCategoryLabel(p.cat)),
                  h('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginTop: 'auto', paddingTop: 4 } },
                    h('span', { style: { fontSize: 14.5, fontWeight: 600, color: TEAL } }, from != null ? ('from ' + this.money(from) + '/pc') : 'Quote'),
                    this.chip(from != null ? 'Instant' : 'On request', from != null ? 'ok' : 'warn'))));
            })))),
      // SEO content section above the footer
      h('section', { style: { borderTop: '1px solid ' + HAIR, marginTop: 46, paddingTop: 34, maxWidth: 900 } },
        h('h2', { style: { margin: '0 0 18px', fontSize: 23, fontWeight: 600, letterSpacing: '-.02em' } }, seo.heading),
        seo.whyHeading ? h('h3', { style: { margin: '0 0 10px', fontSize: 16.5, fontWeight: 600, color: INK } }, seo.whyHeading) : null,
        (seo.bullets && seo.bullets.length) ? h('ul', { style: { margin: '0 0 20px', padding: '0 0 0 22px' } },
          seo.bullets.map((b, i) => h('li', { key: i, style: { fontSize: 14, color: MUT, lineHeight: 1.95 } }, b))) : null,
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: 13 } },
          seo.paras.map((t, i) => h('p', { key: i, style: { margin: 0, fontSize: 14, color: MUT, lineHeight: 1.85 } }, t)))));
  }

  // per-category benefit bullets + an opening pitch (benefit-first, no filler). Shared by
  // the category page and every product page in that category so the "Why print" block is
  // consistent across the site. Falls back to platform-level benefits for 'all'/unknown.
  catWhy(catId) {
    const WHY = {
      'business-essentials': { bullets: ['Make a sharp first impression at every meeting', 'Put your contact details in every prospect’s hand', 'Look established from the first hello'], pitch: 'Your business card and stationery are the first thing a client touches. Print them well and you look ready for the deal before you say a word. Choose premium stocks and finishes that feel as good as they look.' },
      'flyers-leaflets': { bullets: ['Put your promotion straight into people’s hands', 'Drive walk-ins with an offer they can hold', 'Reach a whole neighbourhood on a small budget'], pitch: 'A flyer works because someone holds it. Hand out a launch, a menu or an offer and your message goes home with the customer. Pick your size and paper, and print as few or as many as you need.' },
      'labels-stickers': { bullets: ['Brand every product you sell', 'Seal your packaging with your own mark', 'Turn plain boxes into shelf appeal'], pitch: 'Labels and stickers put your brand on the product itself. They are low cost, hard-wearing and they travel wherever your product goes. Choose round, rectangular, oval or a custom die-cut shape to fit your packaging exactly.' },
      'books-stationery': { bullets: ['Keep your brand on a desk all year', 'Give clients something they use every day', 'Collect your story in one book'], pitch: 'Notebooks, booklets and company profiles carry more of your story than a single page. The right binding and paper make them feel premium and keep your brand in daily use.' },
      'cards-invitations': { bullets: ['Set the tone for the big day', 'Give guests something worth keeping', 'Add foil and texture people want to touch'], pitch: 'A wedding invitation or greeting card gets kept, not thrown away. The right paper and finishing make the moment feel special before it begins. Add hot foil, embossing or a die-cut shape to make it yours.' },
      'large-format': { bullets: ['Get seen from across the street', 'Own your storefront and events', 'Stand tall at every roadshow'], pitch: 'Banners, buntings and roll-ups put your message where a crowd can see it. Print on durable material that lasts the event and beyond, at the exact size you need.' },
      'packaging-boxes': { bullets: ['Protect your product in transit', 'Turn unboxing into your best advert', 'Own the shelf with custom print'], pitch: 'Custom boxes and mailers protect your product and sell it at the same time. A branded unboxing is the advert your customer photographs and shares. Design on a free die-line built for your exact size.' },
      'apparel-gifts': { bullets: ['Put your brand on your team', 'Turn events into walking billboards', 'Give gifts people actually use'], pitch: 'Printed shirts, totes and mugs earn daily use, which makes them some of the highest-exposure branding you can buy. Choose the print method that suits your run and your design.' },
    };
    return WHY[catId] || { bullets: ['Get an exact price before you order', 'Choose from 100+ products in one place', 'Print with a free artwork check'], pitch: 'Printoka is an online printing marketplace bringing 30+ vendors and our own facility into one place. Configure any product, see the exact price on screen, and order online.' };
  }
  // category SEO copy — a keyword heading, a "Why print X" benefit list, and descriptive
  // paragraphs. Benefit bullets are hand-written per category; the closing paragraph is
  // derived live from the catalogue (product count, representative names, from-price).
  categorySeo(catId) {
    const all = catId === 'all';
    const label = all ? 'Online printing' : this.catCategoryLabel(catId);
    const items = this.catProducts(catId);
    const names = items.slice(0, 6).map(p => p.name);
    const moqs = items.map(p => this.catMoq(p.id)).filter(x => x != null);
    const minMoq = moqs.length ? Math.min.apply(null, moqs) : null;
    const froms = items.map(p => this.catFromPrice(p.id)).filter(x => x != null);
    const minFrom = froms.length ? Math.min.apply(null, froms) : null;
    const showFrom = minFrom != null && minFrom >= 0.01;
    const why = this.catWhy(catId);
    const lead = all
      ? 'Every product Printoka prints, priced online in seconds.'
      : 'Order ' + label.toLowerCase() + ' online across Malaysia, Singapore and Brunei. ' + items.length + ' product' + (items.length === 1 ? '' : 's') + ', each priced online in seconds.';
    // closing paragraph from live catalogue data
    const catalogue = 'Printoka prints ' + items.length + ' ' + (all ? 'product' : label.toLowerCase() + ' product') + (items.length === 1 ? '' : 's') + (names.length ? ', including ' + names.slice(0, 5).join(', ') + (items.length > 5 ? ' and more' : '') : '') + '. Configure your spec, see the exact price as you choose'
      + (minMoq != null ? ', from as few as ' + minMoq.toLocaleString() + ' pc' + (minMoq === 1 ? '' : 's') : '')
      + (showFrom ? ' and ' + this.money(minFrom) + ' per piece' : '') + ', and order online. Members save up to 15% at checkout.';
    return {
      lead,
      heading: all ? 'Online Printing in Malaysia, Singapore & Brunei' : 'Print ' + label + ' Online in Malaysia',
      whyHeading: all ? 'Why Print with Printoka' : 'Why Print ' + label,
      bullets: why.bullets,
      paras: [why.pitch, catalogue],
    };
  }

  // ===== PRODUCT + CONFIGURATOR =====
  // Clean, single-product configurator (no cross-product picker) with word-only
  // dropdowns in the aesthetic of the original site. Product detail / SEO content
  // lives in a full-width section below the configurator (see productDetails()).
  s_product() {
    const s = this.state, p = this.price();
    const prod = this.pkProduct(), cfg = this.pkV(), fields = this.pkFields(), q = this.pkQuote();
    const quoteOnly = q && q.quoteOnly;
    const ready = this.pkReady();
    const NAME = prod ? this.catName(prod.id) : 'Business Card';
    const selStyle = { font: '400 14px Montserrat,sans-serif', color: INK, padding: '10px 12px', border: '1px solid ' + HAIR, borderRadius: 8, background: '#fff', width: '100%', appearance: 'auto' };
    // each option is a full-width ROW: label (left) + native <select> (right), divided by a
    // hairline — the aesthetic of the original order form's "Craft your specification".
    const rowStyle = { display: 'grid', gridTemplateColumns: 'minmax(150px,240px) minmax(0,1fr)', gap: 24, alignItems: 'center', padding: '15px 0', borderTop: '1px solid ' + LINE };
    const labelCell = (label, note) => h('div', null,
      h('div', { style: { fontSize: 13.5, fontWeight: 600 } }, label),
      note ? h('div', { style: { fontSize: 11, color: FAINT, marginTop: 3, lineHeight: 1.5 } }, note) : null);
    const ctrlWrap = ch => h('div', { style: { maxWidth: 420 } }, ch);
    const ov = this.cfgOv();
    const ddOpen = this.state.ddOpen;
    // Printoka-styled custom dropdown: closed shows the value / "Please Select"; opening reveals a
    // panel with the helper note above the options — both visible only when clicked.
    const pkDropdown = (key, curText, isPlaceholder, remark, items, fieldLabel) => {
      const open = ddOpen === key;
      const toggle = () => this.setState(st => ({ ddOpen: st.ddOpen === key ? null : key }));
      const close = () => this.setState({ ddOpen: null });
      const label = (fieldLabel || 'Option') + (isPlaceholder ? ' (not selected)' : ': ' + (typeof curText === 'string' ? curText : ''));
      return h('div', { style: { position: 'relative' } },
        h('div', { onClick: e => { e.stopPropagation(); toggle(); },
          tabIndex: 0, role: 'combobox', 'aria-haspopup': 'listbox', 'aria-expanded': open ? 'true' : 'false', 'aria-label': label,
          onKeyDown: e => {
            if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') { e.preventDefault(); e.stopPropagation(); toggle(); }
            else if (e.key === 'ArrowDown' && !open) { e.preventDefault(); e.stopPropagation(); this.setState({ ddOpen: key }); }
            else if (e.key === 'Escape' && open) { e.preventDefault(); e.stopPropagation(); close(); }
          },
          style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, font: '400 14px Montserrat,sans-serif', color: isPlaceholder ? FAINT : INK, padding: '10px 13px', border: '1px solid ' + (open ? TEAL : HAIR), borderRadius: 8, background: '#fff', cursor: 'pointer', boxShadow: open ? '0 0 0 3px rgba(229,34,32,.10)' : 'none' } },
          h('span', { style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, curText),
          h('span', { 'aria-hidden': 'true', style: { flex: 'none', transform: open ? 'rotate(180deg)' : 'none', transition: 'transform .12s', color: FAINT, fontSize: 10 } }, '▼')),
        open ? h('div', { onClick: e => e.stopPropagation(), role: 'listbox', 'aria-label': label, style: { position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0, zIndex: 50, background: '#fff', border: '1px solid ' + HAIR, borderRadius: 8, boxShadow: '0 12px 30px rgba(33,33,33,.18)', overflow: 'hidden' } },
          remark ? h('div', { style: { padding: '10px 13px', fontSize: 11.5, color: MUT, lineHeight: 1.55, background: ALT, borderBottom: '1px solid ' + LINE } }, remark) : null,
          h('div', { style: { maxHeight: 300, overflowY: 'auto' } },
            items.map((it, i) => h('div', { key: i, role: 'option', 'aria-selected': it.on ? 'true' : 'false', tabIndex: 0,
              onClick: e => { e.stopPropagation(); it.onPick(); close(); },
              onKeyDown: e => {
                if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') { e.preventDefault(); e.stopPropagation(); it.onPick(); close(); }
                else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(); }
                else if (e.key === 'ArrowDown') { e.preventDefault(); e.stopPropagation(); const n = e.currentTarget.nextElementSibling; if (n && n.focus) n.focus(); }
                else if (e.key === 'ArrowUp') { e.preventDefault(); e.stopPropagation(); const p = e.currentTarget.previousElementSibling; if (p && p.focus) p.focus(); }
              },
              style: { padding: '10px 13px', fontSize: 13.5, cursor: 'pointer', color: it.on ? TEAL : INK, fontWeight: it.on ? 600 : 400, background: it.on ? '#fdf2f2' : '#fff', borderTop: i ? '1px solid ' + LINE : 'none', outlineOffset: '-2px' } }, it.label)))) : null);
    };
    // card-tile option selector (the "Craft your specification" layout): a field header row
    // (label + current value) over a responsive grid of selectable cards. Each card shows a
    // radio dot, the option label and a Select / Not available subtext; the chosen card is
    // highlighted, and options that are invalid for the current spec are greyed and disabled.
    const cardGroup = (key, fieldLabel, curText, isPh0, note, remark, items) => {
      // collapsible: the field shows only its current value until clicked; clicking reveals the
      // option cards, and picking one collapses it again (the original site's dropdown behaviour).
      const open = this.state.ddOpen === key;
      const toggle = () => this.setState(st => ({ ddOpen: st.ddOpen === key ? null : key }));
      const close = () => this.setState({ ddOpen: null });
      const cards = open ? items.map((it, i) => {
        const on = it.on, avail = it.avail !== false || on;
        return h(avail ? 'button' : 'div', {
          key: it.val != null ? it.val : i, type: avail ? 'button' : undefined,
          onClick: avail ? (e => { e.preventDefault(); e.stopPropagation(); it.onPick(); close(); }) : undefined,
          role: 'radio', 'aria-checked': on ? 'true' : 'false', 'aria-disabled': avail ? undefined : 'true',
          tabIndex: avail ? 0 : -1, 'aria-label': fieldLabel + ': ' + it.label + (avail ? '' : ' (not available)'),
          onKeyDown: avail ? (e => { if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') { e.preventDefault(); e.stopPropagation(); it.onPick(); close(); } else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(); } }) : undefined,
          style: { display: 'flex', alignItems: 'center', gap: 11, textAlign: 'left', width: '100%', font: 'inherit',
            border: '1px solid ' + (on ? TEAL : HAIR), borderRadius: 12, background: on ? '#fdf2f2' : (avail ? '#fff' : ALT),
            padding: '13px 14px', cursor: avail ? 'pointer' : 'default', opacity: avail ? 1 : 0.75, outlineOffset: '2px' } },
          h('span', { 'aria-hidden': 'true', style: { flex: 'none', width: 18, height: 18, borderRadius: '50%', border: '2px solid ' + (on ? TEAL : '#cfcfcf'), background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' } },
            on ? h('span', { style: { width: 8, height: 8, borderRadius: '50%', background: TEAL } }) : null),
          h('span', { style: { display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 } },
            h('span', { style: { fontSize: 13.5, fontWeight: 500, lineHeight: 1.3, color: avail ? INK : FAINT, textDecoration: avail ? 'none' : 'line-through' } }, it.label),
            avail ? null : h('span', { style: { fontSize: 11.5, fontWeight: 400, color: '#bdbdbd' } }, 'Not available')));
      }) : [];
      return h('div', { key: key, style: { padding: '16px 0', borderTop: '1px solid ' + LINE } },
        h('div', { style: { fontSize: 13.5, fontWeight: 600, marginBottom: 8 } }, fieldLabel),
        note ? h('div', { style: { fontSize: 11.5, color: FAINT, lineHeight: 1.5, marginBottom: 8 } }, note) : null,
        // the collapsed control: current value + chevron; click to open the option list
        h('div', { onClick: e => { e.stopPropagation(); toggle(); }, tabIndex: 0, role: 'combobox', 'aria-haspopup': 'listbox', 'aria-expanded': open ? 'true' : 'false', 'aria-label': fieldLabel + (isPh0 ? ' (not selected)' : ': ' + curText),
          onKeyDown: e => { if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') { e.preventDefault(); e.stopPropagation(); toggle(); } else if (e.key === 'ArrowDown' && !open) { e.preventDefault(); e.stopPropagation(); this.setState({ ddOpen: key }); } else if (e.key === 'Escape' && open) { e.preventDefault(); e.stopPropagation(); close(); } },
          style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, cursor: 'pointer', padding: '11px 14px', border: '1px solid ' + (open ? TEAL : HAIR), borderRadius: 10, background: '#fff', boxShadow: open ? '0 0 0 3px rgba(229,34,32,.10)' : 'none' } },
          h('span', { style: { fontSize: 14, fontWeight: 500, color: isPh0 ? FAINT : INK, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, curText),
          h('span', { 'aria-hidden': 'true', style: { flex: 'none', color: FAINT, fontSize: 10, transform: open ? 'rotate(180deg)' : 'none', transition: 'transform .12s' } }, '▼')),
        open ? h('div', { style: { marginTop: 10 } },
          remark ? h('div', { style: { fontSize: 11.5, color: MUT, lineHeight: 1.55, background: ALT, borderRadius: 8, padding: '9px 12px', marginBottom: 12 } }, remark) : null,
          h('div', { role: 'radiogroup', 'aria-label': fieldLabel, style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(200px,1fr))', gap: 12 } }, cards)) : null);
    };
    const optCards = (def, options, sel) => {
      const label = (ov.label && ov.label[def.key]) || def.label;
      const remark = (ov.remark && ov.remark[def.key]) || null;
      const optLabel = (ov.optLabel && ov.optLabel[def.key]) || {};
      const isPh = !!(ov.placeholder && ov.placeholder.indexOf(def.key) >= 0);
      let dispOptions = ov.optionsOverride && ov.optionsOverride[def.key];
      dispOptions = (typeof dispOptions === 'function' ? (dispOptions(this.pkV(), options) || options) : (dispOptions || options));
      const chosen = isPh ? (this.state.cfg[def.key] != null ? this.state.cfg[def.key] : '') : (sel != null ? sel : (dispOptions[0] || ''));
      const isPh0 = isPh && (chosen === '' || chosen == null);
      const curText = isPh0 ? 'Please Select' : (optLabel[chosen] || chosen);
      const note = (ov.noteOverride && Object.prototype.hasOwnProperty.call(ov.noteOverride, def.key)) ? ov.noteOverride[def.key] : (def.neutral ? null : (def.note || null));
      // which of the displayed options are valid for the current spec (the engine's live set)
      const availSet = {}; const validVals = (options || []).map(o => Array.isArray(o) ? o[0] : o);
      validVals.forEach(v => { availSet[v] = 1; });
      // Only grey "Not available" when the engine's live set is a subset of the displayed menu —
      // i.e. the override is the full menu and the engine filters it (e.g. paper vs lamination).
      // When the displayed options are a display-only override the engine doesn't enumerate
      // (fold "Open Size" presets, plastic-card sets), the engine set is disjoint, so trust the
      // override and show every option as available (don't falsely grey them).
      const dispSet = {}; dispOptions.forEach(v => { dispSet[Array.isArray(v) ? v[0] : v] = 1; });
      const reliable = validVals.length > 0 && validVals.every(v => dispSet[v]);
      const items = dispOptions.map(v => { const val = Array.isArray(v) ? v[0] : v;
        return { val: val, label: optLabel[val] || val, on: chosen === val, avail: reliable ? !!availSet[val] : true,
          onPick: () => this.setState(st => ({ cfg: Object.assign({}, st.cfg, { [def.key]: val }) })) }; });
      return cardGroup(def.key, label, curText, isPh0, note, remark, items);
    };
    // quantity, straight from the engine's per-product model (moq / options)
    const qobj = this.pkQtyObj();
    let qopts = (qobj && qobj.options && qobj.options.length) ? qobj.options.slice() : QTYS.slice();
    if (qopts.indexOf(s.qty) < 0) qopts = [s.qty].concat(qopts).sort((a, b) => a - b);
    const qtyPh = !!(ov.placeholder && ov.placeholder.indexOf('quantity') >= 0);
    const qtyChosen = !qtyPh || this.state.qtyChosen;
    const bestSeller = ov.bestSellerQty || [];
    const qtyRemark = ov.remark && ov.remark.quantity;
    const qtyPh0 = qtyPh && !qtyChosen;
    const qtyCur = qtyPh0 ? 'Please Select' : (s.qty.toLocaleString() + ' pcs' + (bestSeller.indexOf(s.qty) >= 0 ? ' — Best Seller' : ''));
    const qtyItems = qopts.map(qn => ({ val: qn, label: qn.toLocaleString() + ' pcs' + (bestSeller.indexOf(qn) >= 0 ? ' · Best Seller' : ''), on: qtyChosen && s.qty === qn, avail: true, onPick: () => this.setState({ qty: qn, qtyChosen: true }) }));
    const qtyField = cardGroup('quantity', 'Quantity', qtyCur, qtyPh0, qobj ? 'min. order ' + qobj.moq.toLocaleString() + ' pcs' : null, qtyRemark, qtyItems);
    // image picker: a selectable grid of option thumbnails (e.g. Round Corner Position)
    const imgPicker = (def, options, sel, base) => {
      const label = (ov.label && ov.label[def.key]) || def.label;
      const optLabel = (ov.optLabel && ov.optLabel[def.key]) || {};
      return h('div', { key: def.key, style: { padding: '15px 0', borderTop: '1px solid ' + LINE } },
        h('div', { style: { fontSize: 13.5, fontWeight: 600, marginBottom: 10 } }, label),
        h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(92px,1fr))', gap: 10 } },
          options.map(v => { const val = Array.isArray(v) ? v[0] : v; const on = sel === val;
            const pick = () => this.setState(st => ({ cfg: Object.assign({}, st.cfg, { [def.key]: val }) }));
            return h('div', { key: val, onClick: pick, tabIndex: 0, role: 'button', 'aria-pressed': on ? 'true' : 'false', 'aria-label': label + ': ' + (optLabel[val] || val),
              onKeyDown: e => { if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') { e.preventDefault(); pick(); } },
              style: { border: '2px solid ' + (on ? TEAL : HAIR), borderRadius: 8, overflow: 'hidden', cursor: 'pointer', background: '#fff' } },
              h('img', { src: window.__asset(base + val + '.jpg'), alt: val, loading: 'lazy', style: { width: '100%', display: 'block', aspectRatio: '1 / 1', objectFit: 'contain', background: '#fff' } }),
              h('div', { style: { textAlign: 'center', fontSize: 11, color: on ? TEAL : MUT, fontWeight: on ? 600 : 400, padding: '3px 0', borderTop: '1px solid ' + LINE } }, optLabel[val] || val)); })));
    };
    // render one field (image picker, dropdown, or value input with range hint)
    const renderField = ({ def, options }) => {
      if (def.widget === 'foilColours') return this.foilColourPicker(def, cfg);
      const imgBase = ov.optImages && ov.optImages[def.key];
      if (imgBase && options && options.length) return imgPicker(def, options, cfg[def.key], imgBase);
      if (options && options.length) return optCards(def, options, cfg[def.key]);
      const isNum = def.type === 'number';
      const unit = /\(mm\)/i.test(def.label || '') ? ' mm' : '';
      const hints = [];
      if (def.min != null && def.max != null) hints.push('Between ' + def.min + unit + ' and ' + def.max + unit);
      else if (def.min != null) hints.push('Minimum ' + def.min + unit);
      else if (def.max != null) hints.push('Maximum ' + def.max + unit);
      if (def.note) hints.push(def.note);
      return h('div', { key: def.key, style: rowStyle },
        labelCell(def.label, null),
        ctrlWrap(h('div', { style: { display: 'flex', flexDirection: 'column', gap: 5 } },
          h('input', { type: isNum ? 'number' : 'text', min: def.min != null ? def.min : undefined, max: def.max != null ? def.max : undefined,
            value: cfg[def.key] || '', placeholder: def.placeholder || ('Enter ' + def.label.toLowerCase()), 'aria-label': def.label,
            onChange: e => { const val = e.target.value; this.setState(st => ({ cfg: Object.assign({}, st.cfg, { [def.key]: val }) })); },
            style: Object.assign({}, selStyle, { font: '400 14px Montserrat,sans-serif' }) }),
          hints.length ? h('div', { style: { fontSize: 11.5, color: FAINT, lineHeight: 1.5 } }, hints.join(' · ')) : null)));
    };
    // group fields by the engine's section order (General / Optional Finishing / …),
    // exactly as the source order form categorises them; quantity sits in its section
    // (before Package, matching the original).
    const secOrder = (prod && prod.sectionOrder && prod.sectionOrder.length) ? prod.sectionOrder.slice() : ['General'];
    const qtySec = (prod && prod.quantitySection) || 'General';
    if (secOrder.indexOf(qtySec) < 0) secOrder.push(qtySec);
    const usedKeys = {};
    const groups = secOrder.map(sec => {
      const secFields = fields.filter(f => (f.def.section || 'General') === sec);
      secFields.forEach(f => { usedKeys[f.def.key] = 1; });
      return { sec, nodes: secFields.map(renderField) };
    });
    const orphans = fields.filter(f => !usedKeys[f.def.key]);
    if (orphans.length) groups[0].nodes = groups[0].nodes.concat(orphans.map(renderField));
    // Quantity is always the LAST configuration option, after every other field/section.
    if (groups.length) groups[groups.length - 1].nodes = groups[groups.length - 1].nodes.concat([qtyField]);
    const sectionHeader = (sec) => h('div', { key: 'h_' + sec, style: { display: 'flex', alignItems: 'center', gap: 10, margin: '22px 0 4px' } },
      h('span', { style: { width: 4, height: 18, background: TEAL, borderRadius: 2, flex: 'none' } }),
      h('span', { style: { fontSize: 15, fontWeight: 700, letterSpacing: '.04em', textTransform: 'uppercase', color: INK } }, sec));
    return h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '10px 20px 0' } },
      h('div', { style: { fontSize: 12.5, color: FAINT, marginBottom: 14 } },
        h('span', { 'data-go': 'home', style: { color: TEAL } }, 'Home'), ' › ', h('span', { 'data-go': prod ? ('catopen:' + this.catCategoryOf(prod.id)) : 'category', style: { color: TEAL } }, prod ? this.catCategoryLabel(this.catCategoryOf(prod.id)) : 'Products'), ' › ', NAME),
      h('div', { style: { display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 352px', gap: 28, alignItems: 'start' } },
        h('div', null,
          h('div', { style: { display: 'flex', gap: 20, flexWrap: 'wrap', marginBottom: 26 } },
            h('div', { style: { flex: '0 0 300px', maxWidth: 340, filter: 'drop-shadow(0 12px 24px rgba(33,33,33,.12))' } }, this.art(prod ? prod.name : 'card')),
            h('div', { style: { flex: '1 1 300px', minWidth: 0 } },
              h('h1', { style: { margin: '0 0 10px', fontSize: 30, fontWeight: 600, letterSpacing: '-.02em' } }, NAME + ' Printing'),
              h('p', { style: { margin: '0 0 12px', fontSize: 14, color: MUT, lineHeight: 1.7 } }, (() => { try { const s = this.productSeo(prod, NAME); if (s && s.paras && s.paras[0]) return s.paras[0]; } catch (e) {} return 'Configure your job and see the exact price before you order.'; })()),
              h('div', { style: { display: 'flex', gap: 8, flexWrap: 'wrap' } }, this.chip('Price to the cent', 'ok'), this.chip('Ready in 3 working days', 'teal')))),
          h('div', { style: { display: 'flex', flexDirection: 'column', gap: 4, border: '1px solid ' + HAIR, borderRadius: 14, padding: 20 } },
            h('div', { style: { fontSize: 18, fontWeight: 600, letterSpacing: '-.01em', color: INK, borderBottom: '2px solid ' + TEAL, paddingBottom: 8, marginBottom: 4, display: 'inline-block' } }, 'Craft your specification'),
            groups.map(g => h('div', { key: g.sec, style: { display: 'flex', flexDirection: 'column' } }, sectionHeader(g.sec), g.nodes)))),
        h('div', { style: { position: 'sticky', top: 122, display: 'flex', flexDirection: 'column', gap: 14 } },
          this.card([
            h('div', { key: 'h', style: { fontSize: 18, fontWeight: 600, letterSpacing: '-.01em', color: INK, borderBottom: '2px solid ' + TEAL, paddingBottom: 8, marginBottom: 12, display: 'inline-block' } }, 'Summary'),
            // live spec summary, straight from the current configuration
            (() => { let lines = []; try { lines = (this.pkOrderSpec().lines || []); } catch (e) {} return lines.length
              ? h('div', { key: 'spec', style: { display: 'flex', flexDirection: 'column', gap: 8 } },
                  lines.map((l, i) => h('div', { key: i, style: { display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 14, fontSize: 12.5, lineHeight: 1.5 } },
                    h('span', { style: { color: FAINT, flex: '0 0 auto' } }, l[0]), h('span', { style: { color: INK, fontWeight: 500, textAlign: 'right' } }, l[1]))))
              : null; })(),
            // order quantity + production time
            h('div', { key: 'qp', style: { display: 'flex', flexDirection: 'column', gap: 8, borderTop: '1px solid ' + LINE, paddingTop: 12, marginTop: 12, fontSize: 12.5 } },
              [['Order Quantity', qtyChosen ? s.qty.toLocaleString() + ' pcs' : 'Please select'], ['Production time', ov.processDays != null ? (ov.processDays + (ov.processDays === 1 ? ' working day' : ' working days')) : '3 working days']]
                .map((r, i) => h('div', { key: i, style: { display: 'flex', justifyContent: 'space-between', gap: 12, lineHeight: 1.5 } }, h('span', { style: { color: FAINT } }, r[0]), h('span', { style: { color: INK, fontWeight: 500 } }, r[1])))),
            // price
            quoteOnly
              ? h('div', { key: 'pr', style: { borderTop: '1px solid ' + LINE, paddingTop: 14, marginTop: 12 } }, h('span', { style: { fontSize: 22, fontWeight: 600, color: TEAL } }, 'Price on request'))
              : (ready
                  ? h('div', { key: 'pr', style: { borderTop: '1px solid ' + LINE, paddingTop: 12, marginTop: 12, display: 'flex', flexDirection: 'column', gap: 7 } },
                      [['Subtotal', this.money(p.gross), MUT], [this.tier() + ' member −' + this.tierPct() + '%', '−' + this.money(p.disc), TEAL], ['Est. shipping (Selangor)', this.money(12), MUT]]
                        .map((r, i) => h('div', { key: i, style: { display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: 12.5, lineHeight: 1.5, color: r[2] } }, h('span', null, r[0]), h('span', { style: { fontWeight: 500, color: r[2] === TEAL ? TEAL : INK } }, r[1]))),
                      h('div', { style: { display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, borderTop: '1px solid ' + LINE, paddingTop: 11, marginTop: 4 } },
                        h('span', { style: { fontSize: 15, fontWeight: 600 } }, 'Total'),
                        h('span', { style: { fontSize: 30, fontWeight: 600, letterSpacing: '-.02em', color: TEAL } }, this.money(p.net))),
                      h('div', { style: { fontSize: 11.5, color: FAINT } }, this.currency() + ' ' + (p.unit * this.fx()).toFixed(3) + ' per piece · incl. ' + this.taxLabel()))
                  : h('div', { key: 'pr', style: { borderTop: '1px solid ' + LINE, paddingTop: 14, marginTop: 12, fontSize: 20, fontWeight: 600, color: MUT } }, 'Select your options')),
            // actions
            h('div', { key: 'e', style: { display: 'flex', flexDirection: 'column', gap: 9, marginTop: 16 } },
              (quoteOnly || ready)
                ? h('div', { style: { display: 'flex', flexDirection: 'column', gap: 9 } },
                    this.btn(quoteOnly ? 'Request a quote' : 'Add to cart', 'amber', quoteOnly ? 'contact' : 'addcart', { justifyContent: 'center' }),
                    this.btn('Buy now', 'teal', quoteOnly ? 'contact' : 'addcart', { justifyContent: 'center' }),
                    this.btn('Download quotation (PDF)', 'ghost', 'product', { justifyContent: 'center' }))
                : h('span', { style: { textAlign: 'center', background: '#f1f3f5', color: MUT, fontWeight: 600, fontSize: 13.5, padding: '12px', borderRadius: 8 } }, 'Select your options to continue')),
          ]),
          (() => { const sim = this.sizeSim(); return this.card([
            h('div', { key: 'a', style: { fontSize: 12.5, fontWeight: 600, marginBottom: 10 } }, 'Size preview & bleed'),
            sim && sim.svg ? h('div', { key: 's', style: { marginBottom: 10 } }, sim.svg,
              h('div', { style: { textAlign: 'center', fontSize: 12, fontWeight: 600, color: TEAL, marginTop: 4 } }, sim.label)) : null,
            sim && sim.pendingSize ? h('div', { key: 'ps', style: { fontSize: 12, color: FAINT, textAlign: 'center', padding: '18px 0', lineHeight: 1.5 } }, sim.msg || 'Choose a size above to preview it here.') : null,
            sim && sim.pending ? h('div', { key: 'p', style: { fontSize: 12, color: FAINT, textAlign: 'center', padding: '16px 0', lineHeight: 1.5 } }, sim.msg || 'Enter a custom height and width to preview the size.') : null,
            h('div', { key: 'b', style: { border: '1px dashed #eaeaea', borderRadius: 8, padding: 12, background: '#fdf2f2', fontSize: 12, color: MUT, lineHeight: 1.6 } }, 'Bleed 3 mm all round · keep text 3–5 mm inside the trim'),
            h('div', { key: 'c', style: { marginTop: 10 } }, this.btn('Upload & check artwork', 'ghost', 'artwork', { justifyContent: 'center', width: '100%' })),
          ]); })(),
          this.card([
            h('div', { key: 'a', style: { fontSize: 12.5, fontWeight: 600, marginBottom: 6 } }, 'Need something off-catalogue?'),
            h('div', { key: 'b', style: { fontSize: 12, color: MUT, lineHeight: 1.6, marginBottom: 10 } }, 'Custom sizes, special finishes or large volumes we don’t price online are quoted on request.'),
            this.btn('Request a custom quote', 'ghost', 'contact', { justifyContent: 'center', width: '100%' }),
          ]))),
      this.productDetails(prod, NAME));
  }

  // full-width product-detail / SEO section (below the configurator): intro copy for
  // search engines + the Product Spec / Artwork Spec / Templates / FAQ tabs.
  productDetails(prod, NAME) {
    const s = this.state;
    const tabs = [['spec', 'Product Spec'], ['artwork', 'Artwork Spec'], ['templates', 'Templates'], ['about', 'Description & FAQ']];
    const seo = this.productSeo(prod, NAME);
    return h('section', { style: { borderTop: '1px solid ' + HAIR, marginTop: 44, paddingTop: 34 } },
      h('div', { style: { maxWidth: 900 } },
        h('h2', { style: { margin: '0 0 18px', fontSize: 24, fontWeight: 600, letterSpacing: '-.02em' } }, seo.heading),
        seo.whyHeading ? h('h3', { style: { margin: '0 0 10px', fontSize: 16.5, fontWeight: 600, color: INK } }, seo.whyHeading) : null,
        (seo.bullets && seo.bullets.length) ? h('ul', { style: { margin: '0 0 20px', padding: '0 0 0 22px' } },
          seo.bullets.map((b, i) => h('li', { key: i, style: { fontSize: 14, color: MUT, lineHeight: 1.95 } }, b))) : null,
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: 13 } },
          seo.paras.map((t, i) => h('p', { key: i, style: { margin: 0, fontSize: 14, color: MUT, lineHeight: 1.85 } }, t)))),
      h('div', { style: { display: 'flex', gap: 24, borderBottom: '1px solid ' + HAIR, marginTop: 30, flexWrap: 'wrap' } },
        tabs.map(t => h('span', { key: t[0], 'data-go': 'set:tab:' + t[0], style: { padding: '13px 2px', fontSize: 14, fontWeight: 600, color: s.tab === t[0] ? TEAL : FAINT, borderBottom: '3px solid ' + (s.tab === t[0] ? AMBER : 'transparent'), marginBottom: -1, cursor: 'pointer' } }, t[1]))),
      h('div', { style: { paddingTop: 22 } }, this.productPanel()));
  }

  // SEO copy generator — real, product-specific sentences built from the live catalogue
  // (name, category, option axes) rather than generic keyword filler.
  productSeo(prod, NAME) {
    const catId = prod ? this.catCategoryOf(prod.id) : null;
    const qobj = prod ? this.pkQtyObj(prod.id) : null;
    const fields = this.pkFields();
    const axes = fields.filter(f => f.options && f.options.length && !/category/i.test(f.def.key)).map(f => f.def.label.toLowerCase());
    const axisPhrase = axes.length ? axes.slice(0, 4).join(', ') + (axes.length > 4 ? ' and more' : '') : 'a range of specifications';
    const from = prod ? this.catFromPrice(prod.id) : null;
    // shared per-category benefit bullets (same "Why print" list as the category page)
    const why = this.catWhy(catId);
    // pull THIS product's real option values (not just field labels) so two products in the
    // same category with the same axes still get genuinely different body copy (content-strategy §4.A.2)
    const valsOf = re => { const f = fields.find(x => re.test(x.def.key) && x.options && x.options.length); return f ? f.options.filter(o => !/other|custom|not required|^no\b|none/i.test(String(o))) : []; };
    const sizes = valsOf(/size/i).slice(0, 4), mats = valsOf(/paper|material|stock/i).slice(0, 3), fins = valsOf(/laminat|spot|stamp|emboss|foil|corner|coat|varnish/i).slice(0, 3);
    const specBits = [];
    if (sizes.length) specBits.push('sizes like ' + sizes.join(', '));
    if (mats.length) specBits.push('materials such as ' + mats.join(', '));
    if (fins.length) specBits.push('finishing including ' + fins.map(x => String(x).toLowerCase()).join(', '));
    const specLine = specBits.length ? ('For your ' + NAME + ' you can choose ' + specBits.join('; ') + '. Every option is priced live as you select it.') : '';
    const paras = [];
    paras.push('Order ' + NAME + ' online and see the exact price as you configure it. Set ' + axisPhrase + ', then order across Malaysia, Singapore and Brunei. You pay exactly what the configurator shows, at checkout and on your invoice.');
    if (specLine) paras.push(specLine);
    if (qobj) paras.push('Minimum order is ' + qobj.moq.toLocaleString() + ' pcs' + (from != null ? ', from ' + this.money(from) + ' per piece' : '') + '. Larger runs bring the price per piece down, and members save 5% to 15% automatically at checkout.');
    paras.push('Upload your artwork and our prepress team checks trim, bleed, resolution and colour before printing. Turnaround is 3 working days after approval, with nationwide delivery or free pickup in the Klang Valley.');
    return { heading: 'Print ' + NAME + ' Online in Malaysia', whyHeading: 'Why Print ' + NAME, bullets: why.bullets, paras };
  }

  productPanel() {
    const t = this.state.tab;
    const prod0 = this.pkProduct(), NAME0 = prod0 ? this.catName(prod0.id) : 'this product';
    const kv = rows => h('table', { style: { width: '100%', borderCollapse: 'collapse', fontSize: 13.5 } },
      h('tbody', null, rows.map((r, i) => h('tr', { key: i, style: { borderBottom: i === rows.length - 1 ? 'none' : '1px solid ' + LINE } },
        h('th', { style: { textAlign: 'left', verticalAlign: 'top', width: 200, padding: '13px 16px 13px 0', fontSize: 13, fontWeight: 600, color: TEAL } }, r[0]),
        h('td', { style: { padding: '13px 0', color: MUT, lineHeight: 1.65 } }, r[1])))));
    if (t === 'artwork') return h('div', null,
      h('h3', { style: { fontSize: 20, fontWeight: 600, margin: '0 0 6px' } }, 'Artwork Specification'),
      h('p', { style: { fontSize: 13.5, color: MUT, margin: '0 0 16px' } }, 'How to set up print-ready artwork for ' + NAME0 + ' so it prints exactly as you expect.'),
      kv([['File format', 'Print-ready PDF preferred. AI, EPS, or high-resolution PNG/TIFF also accepted.'], ['Resolution', '300 dpi at 100% size. Vector art stays sharp.'], ['Colour mode', 'CMYK for accurate print colour (RGB is converted and can shift).'], ['Bleed', '3 mm on every side. Extend your background into the bleed.'], ['Safe margin', 'Keep text and logos at least 3 to 5 mm inside the trim.'], ['Fonts', 'Outline or embed all fonts before exporting.'], ['Spot UV / foil', 'Supply a separate 100% black mask layer, named for the finishing process.']]));
    if (t === 'templates') {
      const prodT = this.pkProduct();
      const sizeField = this.pkFields().find(f => /size/i.test(f.def.key) && f.options && f.options.length);
      const sizes = sizeField ? sizeField.options.filter(s => !/other|custom/i.test(s)) : [];
      const slug = prodT ? (this.catOverride(prodT.id).slug || 'product') : 'product';
      return h('div', null,
        h('h3', { style: { fontSize: 20, fontWeight: 600, margin: '0 0 6px' } }, 'Templates & Downloads — ' + (prodT ? this.catName(prodT.id) : '')),
        h('p', { style: { fontSize: 13.5, color: MUT, margin: '0 0 16px' } }, 'Download a print-ready template for your size, set up your artwork on it, and remove the guides before submitting. Every template already has trim, +3 mm bleed and safe area marked.'),
        sizes.length ? h('div', { style: { border: '1px solid ' + HAIR, borderRadius: 12, overflow: 'hidden' } },
          h('div', { style: { display: 'grid', gridTemplateColumns: '1fr 110px 110px 90px', gap: 8, padding: '10px 14px', background: ALT, fontSize: 11, fontWeight: 600, letterSpacing: '.06em', textTransform: 'uppercase', color: FAINT } },
            h('span', null, 'Size'), h('span', { style: { textAlign: 'center' } }, 'Illustrator'), h('span', { style: { textAlign: 'center' } }, 'Photoshop'), h('span', { style: { textAlign: 'center' } }, 'PDF')),
          sizes.map((sz, i) => h('div', { key: i, style: { display: 'grid', gridTemplateColumns: '1fr 110px 110px 90px', gap: 8, padding: '10px 14px', borderTop: '1px solid ' + LINE, alignItems: 'center' } },
            h('span', { style: { fontSize: 13, fontWeight: 500 } }, sz, h('span', { style: { color: FAINT, fontWeight: 400 } }, ' · +3 mm bleed')),
            ['.ai', '.psd', '.pdf'].map((ext, j) => h('a', { key: j, href: 'templates/' + slug + '/' + sz.replace(/[^a-z0-9]+/gi, '-').toLowerCase() + ext, style: { textAlign: 'center', fontSize: 12, fontWeight: 600, color: TEAL, border: '1px solid ' + HAIR, borderRadius: 6, padding: '6px 0', textDecoration: 'none' } }, ['AI', 'PSD', 'PDF'][j]))))) : h('p', { style: { fontSize: 13, color: FAINT } }, 'Templates for this product are supplied on request.'),
        h('div', { style: { fontSize: 11.5, color: FAINT, marginTop: 12, lineHeight: 1.6 } }, 'Need a size that is not listed? Ask us and we will send you the template.'));
    }
    if (t === 'about') {
      const axes0 = this.pkFields().filter(f => f.options && f.options.length && !/category/i.test(f.def.key));
      const axisList = axes0.slice(0, 5).map(f => f.def.label.toLowerCase()).join(', ');
      const q0 = this.pkQtyObj(prod0 && prod0.id);
      return h('div', null,
        h('h3', { style: { fontSize: 20, fontWeight: 600, margin: '0 0 10px' } }, 'About ' + NAME0 + ' & ordering'),
        h('p', { style: { fontSize: 14, color: MUT, lineHeight: 1.85, maxWidth: '78ch' } }, 'Printoka prices ' + NAME0 + ' exactly from the same impression-run engine our production floor uses, so the number you see when you configure is the number on your quotation, at checkout and on the invoice.' + (axisList ? ' Set ' + axisList + ' and more — every option is priced live.' : '')),
        h('div', { style: { marginTop: 16, display: 'flex', flexDirection: 'column', gap: 10 } },
          [['How long does printing take?', 'Standard orders ship in 3 working days after your artwork is approved by prepress.'], ['What is the minimum order?', q0 ? ('The minimum order for ' + NAME0 + ' is ' + q0.moq.toLocaleString() + ' pcs; larger runs bring the per-piece price down.') : 'Minimum order varies by product and is shown in the configurator.'], ['Do members pay less?', 'Yes. Bronze saves 5%, Silver 8%, Gold 10% and Platinum 15%, applied automatically at checkout.']]
            .map((qq, i) => h('div', { key: i, style: { border: '1px solid ' + HAIR, borderRadius: 10, padding: '13px 15px' } },
              h('div', { style: { fontSize: 13.5, fontWeight: 500 } }, qq[0]),
              h('div', { style: { fontSize: 13, color: MUT, marginTop: 5, lineHeight: 1.6 } }, qq[1])))),
        h('div', { style: { fontSize: 11.5, color: FAINT, marginTop: 14 } }, 'FAQPage + Product + Offer structured data emitted server-side'));
    }
    const prod = this.pkProduct(), NAME = prod ? this.catName(prod.id) : 'Business Cards';
    const rows = this.pkFields().map(({ def, options }) =>
      [def.label, (options && options.length) ? options.join(' · ') : (this.state.cfg && this.state.cfg[def.key]) || '—']);
    return h('div', null,
      h('h3', { style: { fontSize: 20, fontWeight: 600, margin: '0 0 6px' } }, 'Configurable Options'),
      h('p', { style: { fontSize: 13.5, color: MUT, margin: '0 0 16px' } }, 'Every option you can set for ' + NAME + ' when you order.'),
      rows.length ? kv(rows) : h('p', { style: { fontSize: 13.5, color: FAINT } }, 'This product is quoted on request.'));
  }

  // ===== ARTWORK UPLOAD + BLEED CHECKER =====
  s_artwork() {
    const zoom = this.state.zoom || 100, page = this.state.apage || 1;
    const CHECKS = [
      ['C2.1', 'File format valid', 'pass', 'PDF/X-1a:2001 · 2 pages · 4.1 MB'],
      ['C2.2', 'Page count matches job', 'pass', '2 of 2 required pages present'],
      ['C2.3', 'Trim dimensions', 'pass', '54.0 × 89.0 mm · within 0.3 mm tolerance'],
      ['C2.4', 'Bleed present', 'fail', 'Page 1: background stops 1.2 mm short of the bleed line on the right edge'],
      ['C2.5', 'Safe area respected', 'warn', 'Page 2: phone number sits 1.8 mm inside the safe margin'],
      ['C2.6', 'Resolution floor (300 dpi)', 'pass', 'Lowest placed image 412 dpi'],
      ['C2.7', 'Colour mode', 'warn', 'Logo swatch is RGB — will be converted to CMYK, colour may shift'],
      ['C2.8', 'Fonts embedded / outlined', 'pass', '4 fonts embedded, none subset-missing'],
      ['C2.9', 'Overprint & transparency', 'pass', 'No live transparency on spot layers'],
      ['C2.10', 'Special-finish layer naming', 'pass', 'No foil or spot-UV layer required for this job'],
    ];
    const dot = s => h('span', { style: { flex: 'none', height: 10, width: 10, borderRadius: '50%', background: s === 'pass' ? '#63AA02' : s === 'warn' ? '#E8A317' : TEAL, marginTop: 5 } });
    const fails = CHECKS.filter(c => c[2] === 'fail').length, warns = CHECKS.filter(c => c[2] === 'warn').length;
    const VERSIONS = [
      ['v3', 'aiman-bizcard-v3.pdf', '12 Sep · 14:02', 'Current · 1 fail, 2 warnings'],
      ['v2', 'aiman-bizcard-v2.pdf', '11 Sep · 17:40', 'Rejected by prepress — wrong trim size'],
      ['v1', 'aiman-bizcard.pdf', '11 Sep · 09:15', 'Replaced by customer'],
    ];
    const scale = zoom / 100;
    const sheet = h('div', { style: { display: 'grid', placeItems: 'center', background: '#f3f4f6', padding: 26, overflow: 'hidden' } },
      h('div', { style: { position: 'relative', width: 300 * scale, height: 190 * scale, background: '#fff', boxShadow: '0 2px 14px rgba(33,33,33,.14)' } },
        h('div', { style: { position: 'absolute', inset: 0, background: 'linear-gradient(115deg,#231f20 0 62%,#fff 62% 100%)' } }),
        h('div', { style: { position: 'absolute', inset: 16 * scale + 'px', border: '1px dashed ' + TEAL } }),
        h('div', { style: { position: 'absolute', inset: 30 * scale + 'px', border: '1px dashed #2fa4c5' } }),
        h('div', { style: { position: 'absolute', top: 0, right: 0, bottom: 0, width: 14 * scale, background: 'rgba(229,34,32,.35)', borderLeft: '1px solid ' + TEAL } }),
        h('div', { style: { position: 'absolute', right: 6 * scale, bottom: 6 * scale, fontSize: 10, fontWeight: 600, color: TEAL, background: '#fff', padding: '2px 5px' } }, 'bleed short 1.2 mm')));
    return h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '10px 20px 0' } },
      this.head('Upload & check artwork' + (this.pkProduct() ? ' — ' + this.catName(this.pkProduct().id) : ''), 'Upload your print-ready file (JPG, PNG, EPS, AI, ID, PDF or ZIP — up to 1 GB). Every upload is scanned for malware, then checked against this product’s template. Each check reports pass, warning or fail on its own — never one opaque “invalid file” message. You can also upload later and we’ll email you a link.'),
      h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 22, marginTop: 20, alignItems: 'start' } },
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: 18 } },
          h('div', { style: { border: '1px dashed ' + HAIR, background: ALT, padding: 26, textAlign: 'center' } },
            h('img', { src: window.__asset('assets/icons/upload-artwork.svg'), alt: '', style: { height: 38, width: 'auto', display: 'block', margin: '0 auto 12px' } }),
            h('div', { style: { fontSize: 14.5, fontWeight: 600, marginBottom: 5 } }, 'Drag artwork here, or browse'),
            h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.7 } }, 'PDF preferred · AI, EPS, PNG and JPG accepted for this product · multi-file upload for multi-page jobs · every file is virus-scanned before it reaches prepress')),
          h('div', { style: { border: '1px solid ' + HAIR } },
            h('div', { style: { padding: '13px 16px', borderBottom: '1px solid ' + HAIR, fontSize: 13.5, fontWeight: 600 } }, 'Version history'),
            VERSIONS.map((v, i) => h('div', { key: i, style: { padding: '12px 16px', borderTop: i ? '1px solid ' + LINE : 'none', display: 'flex', gap: 12, alignItems: 'baseline' } },
              h('span', { style: { fontSize: 12, fontWeight: 600, color: i === 0 ? TEAL : FAINT, flex: 'none' } }, v[0]),
              h('span', { style: { flex: 1, minWidth: 0 } },
                h('span', { style: { display: 'block', fontFamily: 'ui-monospace,Menlo,monospace', fontSize: 12, color: INK } }, v[1]),
                h('span', { style: { display: 'block', fontSize: 12, color: MUT, marginTop: 3 } }, v[3])),
              h('span', { style: { fontSize: 11.5, color: FAINT, flex: 'none' } }, v[2])))),
          h('div', { style: { border: '1px solid ' + HAIR, padding: 18 } },
            h('div', { style: { fontSize: 13.5, fontWeight: 600, marginBottom: 9 } }, 'Guides & templates for this product'),
            [['Business card artwork guide', 'learn'], ['Download die-line — AI / PDF / PSD', 'learn'], ['Bleed and safe area explained', 'learn']].map((g, i) =>
              h('div', { key: i, 'data-go': g[1], style: { display: 'flex', gap: 8, alignItems: 'center', padding: '7px 0', fontSize: 13, color: TEAL, fontWeight: 600, cursor: 'pointer' } }, g[0],
                h('img', { src: window.__asset('assets/icons/arrow-right.svg'), alt: '', style: { height: 11, width: 'auto', display: 'block' } }))))),
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: 18 } },
          h('div', { style: { border: '1px solid ' + HAIR } },
            h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center', padding: '11px 14px', borderBottom: '1px solid ' + HAIR } },
              h('span', { style: { fontSize: 13, fontWeight: 600, marginRight: 'auto' } }, 'Overlay viewer'),
              [['set:apage:1', 'Page 1', page === 1], ['set:apage:2', 'Page 2', page === 2]].map((p, i) =>
                h('span', { key: i, 'data-go': p[0], style: { fontSize: 12, fontWeight: 600, padding: '5px 11px', borderRadius: 2, cursor: 'pointer', background: p[2] ? TEAL : '#fff', color: p[2] ? '#fff' : MUT, border: '1px solid ' + (p[2] ? TEAL : HAIR) } }, p[1])),
              [['set:zoom:75', '75%', 75], ['set:zoom:100', '100%', 100], ['set:zoom:150', '150%', 150]].map((z, i) =>
                h('span', { key: i, 'data-go': z[0], style: { fontSize: 12, fontWeight: 600, padding: '5px 10px', borderRadius: 2, cursor: 'pointer', color: zoom === z[2] ? TEAL : MUT, border: '1px solid ' + (zoom === z[2] ? TEAL : HAIR) } }, z[1]))),
            sheet,
            h('div', { style: { display: 'flex', gap: 18, flexWrap: 'wrap', padding: '11px 14px', borderTop: '1px solid ' + HAIR, fontSize: 12, color: MUT } },
              [['Trim', '#231f20'], ['Bleed 3 mm', TEAL], ['Safe area', '#2fa4c5']].map((l, i) =>
                h('span', { key: i, style: { display: 'flex', alignItems: 'center', gap: 7 } },
                  h('span', { style: { width: 18, height: 0, borderTop: '2px dashed ' + l[1] } }), l[0])))),
          h('div', { style: { border: '1px solid ' + HAIR } },
            h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center', padding: '13px 16px', borderBottom: '1px solid ' + HAIR } },
              h('span', { style: { fontSize: 13.5, fontWeight: 600, marginRight: 'auto' } }, 'Automated checks'),
              this.chip(fails + ' fail', 'bad'), this.chip(warns + ' warnings', 'warn'), this.chip((CHECKS.length - fails - warns) + ' pass', 'ok')),
            CHECKS.map((c, i) => h('div', { key: i, style: { display: 'flex', gap: 12, padding: '12px 16px', borderTop: i ? '1px solid ' + LINE : 'none', background: c[2] === 'fail' ? '#fdf6f6' : '#fff' } },
              dot(c[2]),
              h('div', { style: { minWidth: 0, flex: 1 } },
                h('div', { style: { display: 'flex', gap: 9, alignItems: 'baseline', flexWrap: 'wrap' } },
                  h('span', { style: { fontSize: 13.5, fontWeight: 600 } }, c[1])),
                h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.6, marginTop: 3 } }, c[3])),
              c[2] !== 'pass' && h('span', { 'data-go': 'learn', style: { fontSize: 12, fontWeight: 600, color: TEAL, cursor: 'pointer', whiteSpace: 'nowrap' } }, 'How to fix')))),
          h('div', { style: { border: '1px solid ' + HAIR, padding: 18, display: 'flex', flexDirection: 'column', gap: 12 } },
            h('div', { style: { fontSize: 13.5, fontWeight: 600 } }, 'Your decision'),
            h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.7 } }, 'One check failed. You can still continue — prepress will review it manually and may send it back — or fix the file now and re-upload as v4.'),
            h('div', { style: { display: 'flex', gap: 10, flexWrap: 'wrap' } },
              this.btn('Fix and re-upload', 'teal', 'artwork', { borderRadius: 2 }),
              this.btn('Looks good, continue', 'ghost', 'cart', { borderRadius: 2 }),
              this.btn('Download annotated PDF', 'ghost', 'artwork', { borderRadius: 2 }))))));
  }

  // ===== CART =====
  s_cart() {
    const cart = this.state.cart || [];
    const t = this.cartTotals();
    if (!cart.length) return h('div', { style: { maxWidth: 700, margin: '0 auto', padding: '10px 20px 0' } },
      this.head('Cart', 'Your cart is empty.'),
      h('div', { style: { border: '1px dashed ' + HAIR, borderRadius: 12, padding: 44, textAlign: 'center', marginTop: 20 } },
        h('div', { style: { fontSize: 15, color: MUT, marginBottom: 16 } }, 'Nothing here yet — configure a product to get an instant price and add it to your cart.'),
        this.btn('Browse products →', 'teal', 'category', { justifyContent: 'center' })));
    const addr = (this.state.addresses || []).find(a => a.isDefault) || (this.state.addresses || [])[0] || null;
    const u = this.state.user || {};
    const kvRow = (label, value, strong) => h('div', { key: label, style: { display: 'flex', justifyContent: 'space-between', gap: 12, padding: '7px 0', borderBottom: '1px solid ' + LINE, fontSize: 13 } },
      h('span', { style: { color: MUT } }, label), h('span', { style: { fontWeight: strong ? 600 : 500, color: INK, textAlign: 'right' } }, value));
    return h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '10px 20px 0' } },
      h('div', { style: { display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 340px', gap: 24, marginTop: 6, alignItems: 'start' } },
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: 16 } },
          h('h1', { style: { margin: '0 0 2px', fontSize: 28, fontWeight: 600, letterSpacing: '-.02em' } }, 'Cart'),
          // Shipped To block
          this.card([
            h('div', { key: 's', style: { fontSize: 11, fontWeight: 600, letterSpacing: '.07em', textTransform: 'uppercase', color: FAINT, marginBottom: 8 } }, 'Shipped to'),
            addr
              ? h('div', { key: 'a', style: { fontSize: 13.5, color: INK, lineHeight: 1.7 } },
                  h('div', { style: { fontWeight: 600 } }, addr.label || u.name || 'Delivery address'),
                  u.phone ? h('div', { style: { color: MUT } }, u.phone) : null,
                  h('div', { style: { color: MUT } }, [addr.line1, addr.line2, addr.postcode + ' ' + addr.city, addr.state, addr.country].filter(Boolean).join(', ')))
              : h('div', { key: 'a', style: { fontSize: 13.5, color: MUT } }, 'No delivery address yet — add one at checkout, or in your Address Book.'),
            h('div', { key: 'l', style: { display: 'flex', gap: 18, marginTop: 10 } },
              h('span', { 'data-go': this.state.user ? 'dash' : 'checkout', style: { fontSize: 12.5, fontWeight: 600, color: TEAL, cursor: 'pointer' } }, 'Add new address'),
              (this.state.addresses && this.state.addresses.length > 1) ? h('span', { 'data-go': 'checkout', style: { fontSize: 12.5, fontWeight: 600, color: TEAL, cursor: 'pointer' } }, 'Choose another address') : null),
          ]),
          // line items
          cart.map((it, i) => this.card([
            h('div', { key: 'top', style: { display: 'flex', gap: 16 } },
              h('div', { style: { flex: '0 0 120px' } }, this.art((this.pkProducts().find(p => p.id === it.productId) || {}).name || 'card')),
              h('div', { style: { flex: 1, minWidth: 0 } },
                h('div', { style: { display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 8 } },
                  h('span', { style: { fontSize: 16, fontWeight: 600 } }, it.name),
                  h('span', { 'data-go': 'open:' + it.productId, style: { fontSize: 12.5, color: TEAL, fontWeight: 600, cursor: 'pointer' } }, 'Edit'),
                  h('span', { onClick: () => this.rmCart(i), style: { marginLeft: 'auto', fontSize: 18, color: FAINT, cursor: 'pointer' } }, '🗑')),
                [['Quantity (pcs)', it.qty.toLocaleString()], ['Price per piece', this.currency() + ' ' + (it.unitPrice * this.fx()).toFixed(3)], ['Subtotal', this.money(it.lineTotal)], ['Urgency', it.urgency || 'Standard'], ['Total', this.money(it.lineTotal), true]].map(r => kvRow(r[0], r[1], r[2])))),
            (it.spec || (it.specLines && it.specLines.length)) ? h('div', { key: 'spec', style: { marginTop: 12 } },
              h('div', { style: { fontSize: 12.5, fontWeight: 600, marginBottom: 4 } }, 'Specification'),
              h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.7 } }, this.specView(it))) : null,
            h('div', { key: 'act', style: { display: 'flex', gap: 18, marginTop: 12 } },
              h('span', { 'data-go': 'open:' + it.productId, style: { fontSize: 12.5, fontWeight: 600, color: TEAL, cursor: 'pointer' } }, 'Edit'),
              h('span', { onClick: () => this.dupCart(i), style: { fontSize: 12.5, fontWeight: 600, color: TEAL, cursor: 'pointer' } }, 'Duplicate')),
            // artwork upload block (same flow used after quote-conversion)
            h('div', { key: 'art', style: { marginTop: 14, background: ALT, borderRadius: 10, padding: '13px 15px' } },
              h('div', { style: { fontSize: 12.5, fontWeight: 600, marginBottom: 3 } }, 'Artwork upload'),
              h('div', { style: { fontSize: 12, color: MUT, marginBottom: 10, lineHeight: 1.6 } }, 'Upload your print-ready file for this job. You can also upload later — we’ll email you a link.'),
              h('div', { style: { display: 'flex', gap: 10, flexWrap: 'wrap' } },
                this.btn('Upload artwork', 'ghost', 'artwork', { padding: '8px 16px', fontSize: 13 }),
                h('span', { 'data-go': 'artwork', style: { alignSelf: 'center', fontSize: 12.5, fontWeight: 600, color: TEAL, cursor: 'pointer' } }, 'Upload files later'))),
          ])),
          h('div', { style: { display: 'flex', gap: 10, marginTop: 2 } }, this.btn('+ Add another product', 'ghost', 'category'))),
        // summary
        h('div', { style: { position: 'sticky', top: 122, display: 'flex', flexDirection: 'column', gap: 14 } },
          this.card([
            h('div', { key: 'a', style: { fontSize: 13, fontWeight: 600, marginBottom: 10 } }, 'Summary'),
            h('div', { key: 'cpn', style: { marginBottom: 12 } },
              h('div', { style: { fontSize: 12, color: TEAL, marginBottom: 6 } }, 'Discount / PCR membership code'),
              h('div', { style: { display: 'flex', gap: 8 } },
                h('input', { placeholder: 'Discount code', value: this.state.cartCoupon || '', onChange: e => this.setField('cartCoupon', e.target.value), style: { flex: 1, minWidth: 0, font: '400 13.5px Montserrat,sans-serif', padding: '10px 12px', border: '1px solid ' + HAIR, borderRadius: 8 } }),
                h('span', { onClick: () => this.applyCoupon(), style: { background: TEAL, color: '#fff', fontWeight: 600, fontSize: 13.5, borderRadius: 8, padding: '10px 18px', cursor: 'pointer', whiteSpace: 'nowrap' } }, 'Apply'))),
            this.state.couponMsg ? h('div', { key: 'cm', style: { fontSize: 12, color: this.state.couponOk ? '#3d8b40' : '#c0392b', marginBottom: 10 } }, this.state.couponMsg) : null,
            h('div', { key: 'b', style: { display: 'flex', flexDirection: 'column', gap: 9, fontSize: 13, borderTop: '1px solid ' + LINE, paddingTop: 12 } },
              [['Subtotal', this.money(t.subtotal)], [this.tier() + ' member −' + this.tierPct() + '%', '−' + this.money(t.memberDiscount), TEAL], [this.taxLabel(), this.money(t.tax)], ['Estimated shipping', this.money(t.shipping)]]
                .map((r, i) => h('div', { key: i, style: { display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, lineHeight: 1.5, color: r[2] || MUT } }, h('span', { style: { flex: '1 1 auto', minWidth: 0 } }, r[0]), h('span', { style: { flex: 'none', fontWeight: 500, whiteSpace: 'nowrap', color: r[2] || INK } }, r[1])))),
            h('div', { key: 'e', style: { borderTop: '1px solid ' + HAIR, marginTop: 14, paddingTop: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' } },
              h('span', { style: { fontSize: 13, fontWeight: 600 } }, 'Total'),
              h('span', { style: { fontSize: 26, fontWeight: 600, color: TEAL, letterSpacing: '-.02em' } }, this.money(t.total))),
            h('div', { key: 'f', style: { marginTop: 14 } }, this.btn('Checkout', 'amber', 'checkout', { justifyContent: 'center', width: '100%' })),
            h('div', { key: 'g', style: { marginTop: 10, textAlign: 'center' } },
              h('span', { onClick: () => this.downloadQuotation(), style: { fontSize: 12.5, fontWeight: 600, color: TEAL, cursor: 'pointer' } }, 'Download Quotation')),
          ]))));
  }

  // ===== CHECKOUT =====
  s_checkout() {
    const cart = this.state.cart || [], t = this.cartTotals();
    if (!cart.length) return h('div', { style: { maxWidth: 700, margin: '0 auto', padding: '10px 20px 0' } },
      this.head('Checkout', 'Your cart is empty — add a product first.'), this.btn('Browse products →', 'teal', 'category'));
    const inp = { font: '400 14px Montserrat,sans-serif', padding: '11px 13px', border: '1px solid #eaeaea', borderRadius: 8, width: '100%', color: INK };
    const field = (label, key, ph, type) => h('label', { key: label, style: { display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12, fontWeight: 600, color: MUT } }, label,
      h('input', { type: type || 'text', placeholder: ph || '', value: this.state[key] || '', onChange: e => this.setField(key, e.target.value), style: inp }));
    const fulfil = this.state.coFulfil || 'delivery';
    const pay = this.state.coPay || 'card_test';
    const PAYS = [['card_test', 'Card (test mode)', 'Validates immediately'], ['fpx', 'FPX online banking', 'Validates immediately'], ['tng', "Touch 'n Go eWallet", 'Validates immediately'], ['ipay88', 'iPay88', 'Validates immediately'], ['bank_transfer', 'Bank transfer', 'Pending until verified'], ['credit_term', 'Credit terms', 'Approved accounts']];
    return h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '10px 20px 0' } },
      this.head('Checkout', 'Enter your details and place the order — it enters the production pipeline the moment payment is confirmed.'),
      h('div', { style: { display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 340px', gap: 24, alignItems: 'start', marginTop: 8 } },
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: 16 } },
          this.card([
            h('div', { key: 'h', style: { fontSize: 14, fontWeight: 600, marginBottom: 14 } }, '1 · Customer information'),
            h('div', { key: 'g', style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 } },
              field('Full name *', 'coName', 'Your name'), field('Email *', 'coEmail', 'you@email.com', 'email'),
              field('Phone', 'coPhone', '+60…'), field('Company (optional)', 'coCompany', 'Company Sdn Bhd')),
          ]),
          this.card([
            h('div', { key: 'h', style: { fontSize: 14, fontWeight: 600, marginBottom: 12 } }, '2 · Fulfilment'),
            h('div', { key: 'o', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 10 } },
              [['delivery', 'Courier delivery', 'To your address'], ['pickup', 'Self-pickup at outlet', 'Klang Valley · 5% off'], ['direct', 'Direct to customer', 'Unbranded packaging']]
                .map(o => h('div', { key: o[0], 'data-go': 'set:coFulfil:' + o[0], style: { border: '1px solid ' + (fulfil === o[0] ? TEAL : HAIR), background: fulfil === o[0] ? '#fdf2f2' : '#fff', borderRadius: 10, padding: 14, cursor: 'pointer' } },
                  h('div', { style: { fontSize: 13, fontWeight: 600, display: 'flex', gap: 8, alignItems: 'center' } },
                    h('span', { style: { height: 14, width: 14, borderRadius: '50%', border: '1px solid ' + (fulfil === o[0] ? TEAL : '#eaeaea'), background: fulfil === o[0] ? TEAL : '#fff', flex: 'none' } }), o[1]),
                  h('div', { style: { fontSize: 12, color: MUT, marginTop: 6 } }, o[2])))),
            fulfil === 'delivery' && h('div', { key: 'a', style: { marginTop: 12, display: 'flex', flexDirection: 'column', gap: 10 } },
              (this.state.addresses && this.state.addresses.length) ? h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 8 } },
                this.state.addresses.map(a => { const on = (this.state.coAddrId || (this.state.addresses.find(x => x.isDefault) || {}).id) === a.id;
                  return h('div', { key: a.id, 'data-go': 'set:coAddrId:' + a.id, style: { border: '1px solid ' + (on ? TEAL : HAIR), background: on ? '#fdf2f2' : '#fff', borderRadius: 8, padding: '10px 12px', fontSize: 12, color: MUT, cursor: 'pointer', lineHeight: 1.5 } },
                    h('div', { style: { fontWeight: 600, color: on ? TEAL : INK } }, a.label), [a.line1, a.postcode + ' ' + a.city].filter(Boolean).join(', ')); })) : null,
              h('input', { placeholder: this.state.addresses && this.state.addresses.length ? 'Or type a new delivery address' : 'Delivery address', value: this.state.coAddress || '', onChange: e => this.setField('coAddress', e.target.value), style: inp }),
              !this.state.user ? h('div', { style: { fontSize: 11.5, color: FAINT } }, h('span', { 'data-go': 'auth', style: { color: TEAL, fontWeight: 600, cursor: 'pointer' } }, 'Sign in'), ' to use your saved address book.') : null),
          ]),
          this.card([
            h('div', { key: 'h', style: { fontSize: 14, fontWeight: 600, marginBottom: 12 } }, '3 · Payment'),
            h('div', { key: 'g', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(155px,1fr))', gap: 10 } },
              PAYS.map(m => h('div', { key: m[0], 'data-go': 'set:coPay:' + m[0], style: { border: '1px solid ' + (pay === m[0] ? TEAL : HAIR), background: pay === m[0] ? '#fdf2f2' : '#fff', borderRadius: 10, padding: '12px 14px', cursor: 'pointer' } },
                h('div', { style: { fontSize: 12.5, fontWeight: pay === m[0] ? 600 : 500, color: pay === m[0] ? TEAL : INK } }, m[1]),
                h('div', { style: { fontSize: 11, color: FAINT, marginTop: 3 } }, m[2])))),
            h('div', { key: 'n', style: { fontSize: 11.5, color: FAINT, marginTop: 12, lineHeight: 1.6 } }, 'Real Stripe / iPay88 keys plug in here — card data is tokenized by the gateway and never stored on Printoka systems. Test mode simulates a confirmed payment; bank transfer stays pending until an admin validates it.'),
          ])),
        h('div', { style: { position: 'sticky', top: 122 } },
          this.card([
            h('div', { key: 'a', style: { fontSize: 12.5, fontWeight: 600, marginBottom: 12 } }, cart.length + ' job' + (cart.length > 1 ? 's' : '') + ' in this order'),
            h('div', { key: 'b', style: { display: 'flex', flexDirection: 'column', gap: 9, fontSize: 13 } },
              [['Subtotal', this.money(t.subtotal)], [this.tier() + ' member −' + this.tierPct() + '%', '−' + this.money(t.memberDiscount), TEAL], [this.taxLabel(), this.money(t.tax)], ['Shipping', this.money(t.shipping)]]
                .map((r, i) => h('div', { key: i, style: { display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, lineHeight: 1.5, color: r[2] || MUT } }, h('span', { style: { flex: '1 1 auto', minWidth: 0 } }, r[0]), h('span', { style: { flex: 'none', fontWeight: 500, whiteSpace: 'nowrap', color: r[2] || INK } }, r[1])))),
            (function () {
              const avail = (this.state.credit && this.state.credit.balance) || 0;
              const applied = this.state.coCredit ? Math.min(avail, t.total) : 0;
              const due = t.total - applied;
              return [
                avail > 0 ? h('label', { key: 'cr', 'data-go': 'set:coCredit:' + (!this.state.coCredit), style: { display: 'flex', alignItems: 'center', gap: 9, fontSize: 12.5, color: MUT, marginTop: 12, cursor: 'pointer' } },
                  h('span', { style: { height: 16, width: 28, borderRadius: 9, background: this.state.coCredit ? TEAL : '#eaeaea', position: 'relative', flex: 'none' } },
                    h('span', { style: { position: 'absolute', top: 2, left: this.state.coCredit ? 14 : 2, height: 12, width: 12, borderRadius: '50%', background: '#fff' } })),
                  'Use credit balance (' + this.money(avail) + ' available)') : null,
                applied > 0 ? h('div', { key: 'ca', style: { display: 'flex', justifyContent: 'space-between', fontSize: 13, color: TEAL, marginTop: 8 } }, h('span', null, 'Credit applied'), h('span', null, '−' + this.money(applied))) : null,
                h('div', { key: 'c', style: { borderTop: '1px solid ' + HAIR, marginTop: 13, paddingTop: 13, display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' } },
                  h('span', { style: { fontSize: 13, fontWeight: 600 } }, 'Total'),
                  h('span', { style: { fontSize: 25, fontWeight: 600, color: TEAL } }, this.money(due))),
                h('div', { key: 'd', style: { marginTop: 14, display: 'flex', flexDirection: 'column', gap: 9 } },
                  this.btn(this.state.placing ? 'Placing…' : 'Place order · ' + this.money(due), 'amber', 'placeorder', { justifyContent: 'center' }),
                  this.btn('Back to cart', 'ghost', 'cart', { justifyContent: 'center' })),
              ];
            }).call(this),
          ]))));
  }

  // ===== LEARNING HUB =====
  s_learn() {
    const posts = this.state.blog || [];
    const active = this.state.blogTag || 'All';
    const tags = ['All'].concat(Array.from(new Set(posts.map(p => p.tag))));
    const list = active === 'All' ? posts : posts.filter(p => p.tag === active);
    return h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '10px 20px 0' } },
      this.head('Learning Hub', 'Artwork guides, paper & finishing explainers and printing tips — migrated from printoka.com. The same help content the artwork checker links to, and the SEO content behind the catalogue.',
        [this.btn('Browse products', 'ghost', 'category')]),
      h('div', { style: { display: 'flex', gap: 7, margin: '20px 0', flexWrap: 'wrap' } },
        tags.map(t => { const on = t === active; const n = t === 'All' ? posts.length : posts.filter(p => p.tag === t).length;
          return h('span', { key: t, 'data-go': 'set:blogTag:' + t, style: { fontSize: 12.5, borderRadius: 999, padding: '6px 13px', border: '1px solid ' + (on ? TEAL : HAIR), background: on ? TEAL : '#fff', color: on ? '#fff' : MUT, fontWeight: 500, cursor: 'pointer' } }, t + ' · ' + n); })),
      posts.length === 0 ? h('div', { style: { padding: 40, textAlign: 'center', color: FAINT, fontSize: 14 } }, 'Loading articles…') :
      h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(280px,1fr))', gap: 18 } },
        list.map(p => h('div', { key: p.slug, 'data-go': 'blog:' + p.slug, style: { border: '1px solid ' + HAIR, borderRadius: 12, overflow: 'hidden', background: '#fff', display: 'flex', flexDirection: 'column', cursor: 'pointer' } },
          h('div', { style: { height: 120, background: 'linear-gradient(120deg,#fdf2f2,#FAFAFA)', display: 'grid', placeItems: 'center' } },
            h('div', { style: { width: '54%', border: '1px dashed #e3b7b4', borderRadius: 4, paddingTop: '32%', position: 'relative', background: '#fff' } },
              h('div', { style: { position: 'absolute', inset: '10%', border: '1px solid ' + TEAL } }))),
          h('div', { style: { padding: 16, display: 'flex', flexDirection: 'column', gap: 7, flex: 1 } },
            h('div', { style: { fontSize: 11, fontWeight: 600, letterSpacing: '.07em', textTransform: 'uppercase', color: TEAL } }, p.tag),
            h('div', { style: { fontSize: 15.5, fontWeight: 600, lineHeight: 1.35 } }, p.title),
            h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.6 } }, p.excerpt),
            h('div', { style: { marginTop: 'auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 10 } },
              h('span', { style: { fontSize: 11.5, color: FAINT } }, p.date),
              h('span', { style: { fontSize: 12.5, fontWeight: 600, color: TEAL } }, 'Read →')))))));
  }

  s_article() {
    const a = this.state.article;
    if (a === null) return h('div', { style: { maxWidth: 760, margin: '0 auto', padding: '40px 20px', color: FAINT, textAlign: 'center' } }, 'Loading article…');
    if (a === false) return h('div', { style: { maxWidth: 760, margin: '0 auto', padding: '40px 20px' } },
      h('p', { style: { color: MUT } }, 'Sorry, that article could not be loaded. '),
      this.btn('Back to Learning Hub', 'ghost', 'learn'));
    return h('div', { style: { maxWidth: 760, margin: '0 auto', padding: '10px 20px 40px' } },
      h('div', { style: { fontSize: 12.5, color: FAINT, marginBottom: 14 } },
        h('span', { 'data-go': 'home', style: { color: TEAL, cursor: 'pointer' } }, 'Home'), ' › ',
        h('span', { 'data-go': 'learn', style: { color: TEAL, cursor: 'pointer' } }, 'Learning Hub'), ' › ', a.tag),
      h('div', { style: { fontSize: 11, fontWeight: 600, letterSpacing: '.07em', textTransform: 'uppercase', color: TEAL, marginBottom: 8 } }, a.tag),
      h('h1', { style: { fontSize: 34, fontWeight: 600, lineHeight: 1.15, letterSpacing: '-.02em', margin: '0 0 10px' } }, a.title),
      h('div', { style: { fontSize: 12.5, color: FAINT, marginBottom: 22, borderBottom: '1px solid ' + HAIR, paddingBottom: 18 } }, a.date + ' · Printoka'),
      a.body ? h('div', null, this.mdToNodes(a.body))
        : h('div', { style: { border: '1px dashed ' + HAIR, borderRadius: 10, padding: 20, background: ALT, color: MUT, fontSize: 14, lineHeight: 1.7 } },
            h('p', { style: { margin: '0 0 8px' } }, a.excerpt),
            h('p', { style: { margin: 0, fontSize: 12.5, color: FAINT } }, 'The full text of this article is being migrated from printoka.com — run ', h('code', { style: { background: '#fff', padding: '1px 5px', borderRadius: 4 } }, 'node web/content/migrate-blog.mjs'), ' to import it.')),
      h('div', { style: { marginTop: 30, paddingTop: 20, borderTop: '1px solid ' + HAIR, display: 'flex', gap: 10, flexWrap: 'wrap' } },
        this.btn('← All articles', 'ghost', 'learn'),
        this.btn('Configure & price a product →', 'teal', 'category')));
  }

  // ===== MEMBERSHIP =====
  s_membership() {
    const u = this.state.user;
    const spend = (u && u.spend12mo) || 0, plat = 10000;
    const toPlat = Math.max(0, plat - spend), pct = Math.min(100, Math.round(spend / plat * 100));
    return h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '10px 20px 0' } },
      this.head('Save up to 15% on every order', 'Your tier is set by your spend over the last 12 months. Higher tiers save you more on every job.',
        [this.btn(u ? 'Go to dashboard' : 'Register free', 'amber', 'dash')]),
      h('div', { style: { marginTop: 22, border: '1px solid ' + TEAL, borderRadius: 14, padding: 20, background: '#fdf2f2' } },
        h('div', { style: { display: 'flex', gap: 18, flexWrap: 'wrap', alignItems: 'center' } },
          h('div', { style: { flex: '1 1 340px', minWidth: 0 } },
            h('div', { style: { fontSize: 11.5, fontWeight: 600, letterSpacing: '.08em', textTransform: 'uppercase', color: TEAL } }, 'Where you are'),
            h('div', { style: { fontSize: 22, fontWeight: 600, margin: '6px 0 12px' } }, this.tier() + ' · ' + this.tierPct() + '% off every job'),
            h('div', { style: { height: 9, borderRadius: 5, background: '#eaeaea', overflow: 'hidden' } },
              h('div', { style: { width: pct + '%', height: '100%', background: 'linear-gradient(90deg,' + TEAL + ',' + AMBER + ')' } })),
            h('div', { style: { display: 'flex', justifyContent: 'space-between', fontSize: 12.5, color: MUT, marginTop: 8 } },
              h('span', null, this.money(spend) + ' of ' + this.money(plat) + ' trailing spend'), h('span', null, this.tier() === 'Platinum' ? 'Top tier reached' : this.money(toPlat) + ' to Platinum'))),
          h('div', { style: { flex: '0 0 260px', display: 'flex', flexDirection: 'column', gap: 9, fontSize: 12.5 } },
            h('div', { style: { background: '#fff5e2', color: '#a1660a', borderRadius: 8, padding: '11px 13px', lineHeight: 1.55 } }, 'Inactivity watch: 41 days without an order. At 90 days you drop one tier. Re-upgrade is automatic.'),
            this.btn('Refer a friend · earn ' + this.money(150), 'ghost', 'membership', { justifyContent: 'center' })))),
      h('div', { style: { marginTop: 22 } },
        this.table(['Tier', 'Trailing 12-month spend', 'Discount', 'Benefits', 'Status'],
          (function (self) { const cur = TIERS.findIndex(t => t[0] === self.tier()); return TIERS.map((t, i) => [t[0], t[1], t[2], t[3], i === cur ? self.chip('Your tier', 'ok') : (i < cur ? self.chip('Unlocked', 'neutral') : self.chip('Next', 'warn'))]); })(this),
          ['140px', '190px', '110px', null, '110px'])),
      h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 16, marginTop: 22 } },
        [['Stacking', 'Membership discount, seasonal coupons and referral credit stack independently up to a cap, currently 30% per order.'],
         ['Credit balance, not a wallet', 'A ledger fed by refunds, goodwill adjustments and referral payouts. Every entry carries a reason code, actor and running balance.'],
         ['Downgrade & re-upgrade', 'No order for 3 consecutive months drops one tier. Crossing the threshold again re-upgrades instantly, no manual reinstatement.']]
          .map((c, i) => this.card([
            h('div', { key: 'a', style: { fontSize: 14, fontWeight: 600, marginBottom: 7 } }, c[0]),
            h('div', { key: 'b', style: { fontSize: 12.5, color: MUT, lineHeight: 1.7 } }, c[1]),
          ], { key: i }))));
  }

  // ===== PUBLIC PAGES: Corporate · Partners · Support · Terms =====
  pageWrap(children) { return h('div', { style: { maxWidth: 980, margin: '0 auto', padding: '10px 20px 0' } }, children); }
  featureGrid(items) {
    return h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 16, marginTop: 22 } },
      items.map((it, i) => this.card([
        h('div', { key: 'i', style: { height: 40, width: 40, borderRadius: '50%', background: '#e1f5f2', display: 'grid', placeItems: 'center', marginBottom: 12 } }, this.dashIcon(it[2] || 'check', '#12B3A6', 20)),
        h('div', { key: 'a', style: { fontSize: 15, fontWeight: 600, marginBottom: 6 } }, it[0]),
        h('div', { key: 'b', style: { fontSize: 13, color: MUT, lineHeight: 1.7 } }, it[1]),
      ], { key: i })));
  }
  s_corporate() {
    return this.pageWrap([
      this.head('Corporate accounts', 'For teams, agencies and franchises that print regularly. A dedicated account manager, negotiated rates, credit terms and one consolidated invoice — across Malaysia, Singapore and Brunei.',
        [this.btn('Apply for a corporate account', 'amber', 'contact'), this.btn('Talk to sales', 'ghost', 'contact')]),
      this.featureGrid([
        ['Dedicated Key Account Manager', 'One person who knows your brand, specs and deadlines — reachable on WhatsApp and email, not a ticket queue.', 'user-plus'],
        ['Credit terms & consolidated billing', 'Order now, settle monthly on agreed terms. One statement across every outlet, user and country.', 'dollar-sign'],
        ['Volume & contract pricing', 'Rates that improve with committed annual volume, stacked on top of your membership tier.', 'clock'],
        ['Brand asset library', 'We keep your die-lines, templates and approved artwork on file so reorders are one click.', 'layers'],
        ['Multi-user accounts', 'Add your team with roles and shared address book, artwork gallery and order history.', 'file'],
        ['Nationwide fulfilment', 'Produced through our 30-vendor network and delivered to every branch, or held for outlet pickup.', 'truck'],
      ]),
      h('div', { key: 't', style: { marginTop: 28 } },
        h('div', { style: { fontSize: 18, fontWeight: 600, marginBottom: 12 } }, 'How onboarding works'),
        this.table(['Step', 'What happens', 'Timeline'],
          [['1 · Apply', 'Send your company details and typical print needs.', 'Today'],
           ['2 · Review', 'We propose rates, credit limit and your account manager.', '1–2 working days'],
           ['3 · Activate', 'Your team is set up with corporate pricing and billing.', 'Same week'],
           ['4 · Print', 'Order online or through your manager — one invoice monthly.', 'Ongoing']],
          ['16%', null, '160px'])),
    ]);
  }
  s_partners() {
    return this.pageWrap([
      this.head('Partners', 'Two ways to grow with Printoka — join our production network as a print vendor, or earn commission by referring customers.',
        [this.btn('Become a printer', 'amber', 'vendor'), this.btn('Join the affiliate programme', 'ghost', 'contact')]),
      h('div', { key: 'g', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 18, marginTop: 22 } },
        this.card([
          h('div', { key: 'a', style: { fontSize: 17, fontWeight: 600, marginBottom: 8 } }, 'Print vendors & hubs'),
          h('p', { key: 'b', style: { fontSize: 13.5, color: MUT, lineHeight: 1.75, margin: '0 0 12px' } }, 'Receive quote requests from our scheduling team, quote your price and lead time, and win jobs on merit — cost, speed and logistics, never relationship. Winners print a shipping label and deliver to the destination outlet or customer.'),
          h('ul', { key: 'c', style: { margin: '0 0 14px', paddingLeft: 20, color: MUT, fontSize: 13, lineHeight: 1.9 } }, ['Steady, transparent job flow', 'Get paid per awarded PO', 'A scorecard that rewards quality & on-time delivery'].map((x, i) => h('li', { key: i }, x))),
          this.btn('Apply as a printer', 'teal', 'vendor'),
        ]),
        this.card([
          h('div', { key: 'a', style: { fontSize: 17, fontWeight: 600, marginBottom: 8 } }, 'Affiliates & referrers'),
          h('p', { key: 'b', style: { fontSize: 13.5, color: MUT, lineHeight: 1.75, margin: '0 0 12px' } }, 'Refer a business to Printoka and earn ' + this.money(150) + ' credit once their first order ships — plus recurring rewards as they keep printing. Perfect for designers, agencies and consultants.'),
          h('ul', { key: 'c', style: { margin: '0 0 14px', paddingLeft: 20, color: MUT, fontSize: 13, lineHeight: 1.9 } }, ['Unique referral link & dashboard', 'Credit paid to your wallet', 'No cap on referrals'].map((x, i) => h('li', { key: i }, x))),
          this.btn('Get your referral link', 'ghost', 'contact'),
        ])),
    ]);
  }
  s_support() {
    const topics = [
      ['Track an order', 'Live production and delivery status by order number.', 'truck', 'track'],
      ['Artwork & guides', 'Bleed, resolution, colour and file-prep guides per product.', 'layers', 'learn'],
      ['Request a quote', 'Non-standard job? Tell us the spec and we’ll price it.', 'edit-3', 'contact'],
      ['Membership & rewards', 'How tiers, discounts and credit work.', 'clock', 'membership'],
      ['Payments & invoices', 'Methods, tax invoices, statements and credit terms.', 'dollar-sign', 'contact'],
      ['Template downloads', 'Print-ready AI, PSD & PDF templates per product size.', 'file', 'downloads'],
    ];
    return this.pageWrap([
      this.head('Support', 'Pick a topic below, or reach us on WhatsApp, email or the contact form.',
        [this.btn('WhatsApp us', 'amber', 'contact'), this.btn('Contact form', 'ghost', 'contact')]),
      h('div', { key: 'g', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 16, marginTop: 22 } },
        topics.map((t, i) => h('div', { key: i, 'data-go': t[3], style: { cursor: 'pointer' } }, this.card([
          h('div', { key: 'i', style: { height: 40, width: 40, borderRadius: '50%', background: '#e1f5f2', display: 'grid', placeItems: 'center', marginBottom: 12 } }, this.dashIcon(t[2], '#12B3A6', 20)),
          h('div', { key: 'a', style: { fontSize: 15, fontWeight: 600, marginBottom: 6 } }, t[0]),
          h('div', { key: 'b', style: { fontSize: 13, color: MUT, lineHeight: 1.7 } }, t[1]),
          h('div', { key: 'c', style: { fontSize: 12.5, color: TEAL, fontWeight: 600, marginTop: 8 } }, 'Open →'),
        ])))),
      this.faqSection(),
      h('div', { key: 'c', style: { marginTop: 24, border: '1px solid ' + HAIR, borderRadius: 12, padding: 20, background: ALT, display: 'flex', flexWrap: 'wrap', gap: 20, justifyContent: 'space-between' } },
        [['WhatsApp', '+60 3-1234 5678'], ['Email', 'hello@printoka.com'], ['Hours', 'Mon–Fri 9am–6pm (MYT)']].map((r, i) =>
          h('div', { key: i }, h('div', { style: { fontSize: 11.5, fontWeight: 600, letterSpacing: '.06em', textTransform: 'uppercase', color: FAINT } }, r[0]), h('div', { style: { fontSize: 14, fontWeight: 600, marginTop: 4 } }, r[1])))),
    ]);
  }
  // FAQ accordions (migrated verbatim from printoka.com/support) — one open per category
  faqSection() {
    const faq = this.state.faq;
    if (!faq || !faq.length) return h('div', { key: 'faq', style: { marginTop: 26, color: FAINT, fontSize: 13 } }, faq == null ? 'Loading FAQ…' : null);
    return h('div', { key: 'faq', style: { marginTop: 30 } },
      h('h2', { style: { fontSize: 24, fontWeight: 700, letterSpacing: '-.02em', margin: '0 0 4px' } }, 'Frequently asked questions'),
      h('p', { style: { margin: '0 0 18px', fontSize: 13.5, color: MUT } }, faq.reduce((s, c) => s + c.questions.length, 0) + ' answers across ' + faq.length + ' topics.'),
      faq.map(c => {
        const open = this.state['faqOpen_' + c.id];
        return h('div', { key: c.id, style: { marginBottom: 22 } },
          h('div', { style: { fontSize: 16, fontWeight: 600, marginBottom: 10 } }, c.title),
          h('div', { style: { border: '1px solid ' + HAIR, borderRadius: 12, overflow: 'hidden', background: '#fff' } },
            c.questions.map((qa, i) => h('div', { key: i, style: { borderTop: i ? '1px solid ' + LINE : 'none' } },
              h('div', { onClick: () => this.setState({ ['faqOpen_' + c.id]: open === i ? null : i }), style: { display: 'flex', gap: 12, alignItems: 'flex-start', padding: '14px 16px', cursor: 'pointer', fontWeight: 600, fontSize: 14 } },
                h('span', { style: { flex: 1 } }, qa.q),
                h('span', { style: { color: '#E52220', fontSize: 18, lineHeight: 1, transform: open === i ? 'rotate(180deg)' : 'none', transition: 'transform .15s' } }, '⌄')),
              open === i ? h('div', { style: { padding: '0 16px 16px', fontSize: 13.5, color: MUT, lineHeight: 1.75, whiteSpace: 'pre-wrap' } }, qa.a) : null))));
      }));
  }
  // ===== TEMPLATE DOWNLOADS (migrated from printoka.com/download) =====
  s_downloads() {
    const dls = this.state.downloads;
    if (!dls) return this.pageWrap([this.head('Template downloads', 'Loading…')]);
    const active = dls.find(c => c.slug === this.state.dlCat) || dls[0];
    return this.pageWrap([
      this.head('Template downloads', 'Print-ready templates for standard-size products. Download, design to the guidelines, and remove the guide layer before you submit.'),
      h('div', { key: 'g', style: { display: 'grid', gridTemplateColumns: '220px minmax(0,1fr)', gap: 22, marginTop: 22, alignItems: 'start' } },
        h('aside', { style: { border: '1px solid ' + HAIR, borderRadius: 12, background: '#fff', padding: 8, position: 'sticky', top: 16, maxHeight: '80vh', overflow: 'auto' } },
          dls.map(c => { const on = active && c.slug === active.slug;
            return h('div', { key: c.slug, 'data-go': 'set:dlCat:' + c.slug, style: { padding: '9px 12px', borderRadius: 8, fontSize: 13, fontWeight: on ? 600 : 400, color: on ? '#E52220' : MUT, background: on ? '#fdeceb' : 'transparent', cursor: 'pointer' } }, c.title); })),
        active ? h('div', null,
          h('h2', { style: { fontSize: 22, fontWeight: 700, margin: '0 0 8px' } }, active.title),
          active.description ? h('p', { style: { margin: '0 0 12px', fontSize: 13.5, color: MUT, lineHeight: 1.7, whiteSpace: 'pre-wrap' } }, active.description) : null,
          active.notice ? h('div', { style: { display: 'flex', gap: 10, background: '#fff7e6', border: '1px solid #f0d9a0', borderRadius: 10, padding: '12px 14px', marginBottom: 16 } },
            h('span', { style: { flex: 'none', fontSize: 16 } }, '⚠'), h('div', null, h('div', { style: { fontSize: 11.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.05em', color: '#a1660a', marginBottom: 2 } }, active.notice.label), h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.6 } }, active.notice.body))) : null,
          active.folds.map((f, fi) => h('div', { key: fi, style: { marginBottom: 22 } },
            h('div', { style: { fontSize: 15, fontWeight: 600, marginBottom: 10 } }, f.name),
            f.rows.length ? h('div', { style: { border: '1px solid ' + HAIR, borderRadius: 12, overflow: 'hidden', background: '#fff' } },
              f.rows.map((r, ri) => h('div', { key: ri, style: { display: 'grid', gridTemplateColumns: 'minmax(120px,220px) 1fr', gap: 14, padding: '12px 16px', borderTop: ri ? '1px solid ' + LINE : 'none', alignItems: 'center' } },
                h('div', null, h('div', { style: { fontSize: 13.5, fontWeight: 500 } }, r.size || '—'), r.dims ? h('div', { style: { fontSize: 12, color: FAINT } }, r.dims) : null),
                h('div', { style: { display: 'flex', gap: 16, flexWrap: 'wrap' } }, r.files.length ? r.files.map((fl, li) =>
                  h('a', { key: li, href: fl.url, target: '_blank', rel: 'noopener', style: { display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13.5, fontWeight: 600, color: '#E52220', textDecoration: 'none' } }, this.dashIcon('file', '#E52220', 15), fl.label)) : h('span', { style: { fontSize: 12.5, color: FAINT } }, 'No file'))))) :
              h('div', { style: { border: '1px dashed ' + HAIR, borderRadius: 10, padding: 18, color: FAINT, fontSize: 13 } }, 'No downloadable templates for this variation yet.'))),
        ) : null),
    ]);
  }
  s_terms() {
    const S = [
      ['Terms of service', 'By placing an order you agree to these terms. Prices shown are for the specified specification and quantity; final artwork must match the order. Production begins only after payment is confirmed (or on approved credit terms) and artwork passes prepress checks.'],
      ['Artwork & proofing', 'You are responsible for the accuracy of supplied artwork — spelling, layout, colour intent and bleed. We check files against the order and flag issues, but we do not amend content without your authorisation. Colour may vary slightly between screen and print, and between print runs.'],
      ['Delivery & risk', 'Estimated lead times begin once artwork is approved and payment confirmed. Delivery dates are estimates; risk passes on dispatch. Import duties and taxes for cross-border shipments are borne by the recipient.'],
      ['Refunds & remakes', 'If a job is defective due to our error, we remake or refund it. Claims must be raised within 7 days of delivery with photos. We are not liable for errors present in approved artwork, or for delays caused by incorrect delivery details.'],
      ['Privacy (PDPA)', 'We collect only what we need to fulfil your orders and run your account, and we process it under Malaysia’s PDPA. We never sell your data. Artwork and order history are stored securely and visible only to you and the staff processing your job.'],
      ['Membership & credit', 'Membership tiers are based on trailing-12-month spend and evaluated continuously. Store credit is a ledger balance usable on any job; it is non-transferable and non-refundable to cash except where required by law.'],
    ];
    return this.pageWrap([
      this.head('Terms & policies', 'The essentials, in plain language. This summary is provided for the prototype and is not a substitute for the final legal agreement.'),
      h('div', { key: 'b', style: { display: 'flex', flexDirection: 'column', gap: 16, marginTop: 22 } },
        S.map((s, i) => h('div', { key: i, style: { border: '1px solid ' + HAIR, borderRadius: 12, padding: 20, background: '#fff' } },
          h('div', { style: { fontSize: 16, fontWeight: 600, marginBottom: 8 } }, s[0]),
          h('p', { style: { margin: 0, fontSize: 13.5, color: MUT, lineHeight: 1.8 } }, s[1])))),
      h('div', { key: 'f', style: { marginTop: 20, fontSize: 12.5, color: FAINT } }, 'Questions about these terms? ', h('span', { 'data-go': 'support', style: { color: TEAL, fontWeight: 600, cursor: 'pointer' } }, 'Contact support →')),
    ]);
  }

  // ===== CONTACT / CUSTOM QUOTE =====
  s_contact() {
    const inp = { border: '1px solid #eaeaea', borderRadius: 8, padding: '11px 13px', fontSize: 14, font: '400 14px Montserrat,sans-serif', width: '100%' };
    const field = (label, key, wide, ta) => h('label', { key: label, style: { gridColumn: wide ? '1 / -1' : 'auto', display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12, fontWeight: 600, color: MUT } }, label,
      ta ? h('textarea', { value: this.state[key] || '', onChange: e => this.setField(key, e.target.value), style: Object.assign({}, inp, { minHeight: 90, resize: 'vertical' }) })
        : h('input', { value: this.state[key] || '', onChange: e => this.setField(key, e.target.value), style: inp }));
    const sent = this.state.quoteSent;
    return h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '10px 20px 0' } },
      this.head('Request a custom quote', 'For off-catalogue, bulk or non-standard jobs. We reply with a price and lead time you can accept and pay online.'),
      h('div', { style: { display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 320px', gap: 24, marginTop: 22, alignItems: 'start' } },
        sent ? this.card([
          h('div', { key: 'a', style: { fontSize: 18, fontWeight: 600, marginBottom: 6 } }, 'Quote request received ✓'),
          h('div', { key: 'b', style: { fontSize: 14, color: MUT, lineHeight: 1.7, marginBottom: 14 } }, 'Your reference is ', h('b', { style: { color: TEAL } }, sent.id), '. Our team will price it and issue the quote to your account — you’ll be able to accept & pay it from ', h('b', null, 'My Quotes'), '.'),
          h('div', { key: 'c', style: { display: 'flex', gap: 10, flexWrap: 'wrap' } }, this.state.user ? this.btn('Go to My Quotes', 'teal', 'dash') : this.btn('Sign in to track it', 'teal', 'auth'), this.btn('Submit another', 'ghost', 'contact'))
        ]) : this.card([
          this.state.quoteErr ? h('div', { key: 'e', style: { fontSize: 12.5, color: '#c0392b', background: '#fdecec', border: '1px solid #f5c8c7', borderRadius: 6, padding: '9px 11px', marginBottom: 12 } }, this.state.quoteErr) : null,
          h('div', { key: 'g', style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 13 } },
            field('Name', 'qfName'), field('Company', 'qfCompany'),
            field('Email', 'qfEmail'), field('Phone / WhatsApp', 'qfPhone'),
            field('What do you want printed? *', 'qfProduct'), field('Quantity', 'qfQty'),
            field('Size', 'qfSize'), field('Material / stock', 'qfMaterial'),
            field('Finishing', 'qfFinishing'),
            field('Tell us about the job', 'qfRemarks', true, true)),
          h('div', { key: 'u', style: { marginTop: 14, border: '1px dashed #eaeaea', borderRadius: 10, padding: 18, textAlign: 'center', fontSize: 12.5, color: MUT, background: '#fdf2f2' } },
            'Attach artwork, a reference photo or a spec sheet · PDF, AI, EPS, PNG, JPG'),
          h('div', { key: 'b', style: { display: 'flex', gap: 10, marginTop: 16, alignItems: 'center', flexWrap: 'wrap' } },
            this.btn(this.state.quoteBusy ? 'Sending…' : 'Send request', 'amber', 'doquote'),
            h('span', { style: { fontSize: 11.5, color: FAINT } }, 'Typical first response: under 2 working hours')),
        ]),
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: 14 } },
          this.card([
            h('div', { key: 'a', style: { fontSize: 13, fontWeight: 600, marginBottom: 9 } }, 'Talk to us'),
            h('div', { key: 'b', style: { fontSize: 12.5, color: MUT, lineHeight: 1.8 } },
              h('div', null, 'Web chat · 9am–6pm MYT'), h('div', null, 'WhatsApp · +60 3-1234 5678'),
              h('div', null, 'hello@printoka.com'), h('div', null, 'Miri facility + 30 partner vendors')),
          ]),
          this.card([
            h('div', { key: 'a', style: { fontSize: 13, fontWeight: 600, marginBottom: 9 } }, 'Already have a quote?'),
            h('div', { key: 'b', style: { fontSize: 12.5, color: MUT, lineHeight: 1.7, marginBottom: 11 } }, 'Accept and pay, or request changes, from My Quotes.'),
            this.btn('Open My Quotes', 'ghost', 'dash', { justifyContent: 'center', width: '100%' }),
          ]))));
  }

  // ===== CUSTOMER DASHBOARD =====
  s_dash() {
    const u = this.state.user;
    if (!u) return h('div', { style: { maxWidth: 700, margin: '0 auto', padding: '40px 20px' } },
      this.head('Your dashboard', 'Sign in to see your orders, membership tier and credit balance.'),
      h('div', { key: 's', style: { display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 16 } }, this.btn('Log in', 'teal', 'auth'), this.btn('Create an account', 'ghost', 'auth')));
    const tabs = ['Dashboard', 'Orders', 'Invoices', 'Transactions', 'Sales Missions'];
    const tab = this.state.cTab || 'Dashboard';
    const navActive = tabs.indexOf(tab) >= 0 ? tab : 'Dashboard';
    const orders = this.state.userOrders || [];
    const quotes = this.state.quotesList || [];
    const cinvs = this.state.custInvoices || [];
    const credit = this.state.credit || { balance: 0, ledger: [] };
    const MONTHS = ['APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP'];
    const stitle = t => h('h1', { key: 'h', style: { fontSize: 30, fontWeight: 700, letterSpacing: '-.02em', margin: '2px 0 6px' } }, t);
    let content;

    if (tab === 'Dashboard') {
      const heroCard = (label, value, extra, grad, icon) => h('div', { style: { position: 'relative', overflow: 'hidden', borderRadius: 12, padding: '20px 22px', color: '#fff', background: grad, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', minHeight: 96 } },
        h('div', null, h('div', { style: { fontWeight: 700, fontSize: 14 } }, label), h('div', { style: { display: 'flex', alignItems: 'center', gap: 10, marginTop: 8 } }, h('span', { style: { fontSize: 32, fontWeight: 800, letterSpacing: '-.02em' } }, value), extra)),
        h('div', { style: { height: 52, width: 52, borderRadius: '50%', background: 'rgba(255,255,255,.18)', display: 'grid', placeItems: 'center', flex: 'none' } }, this.dashIcon(icon, '#fff', 24)));
      const links = [['My Orders', 'Orders', 'file'], ['My Quotations', 'Quotations', 'edit-3'], ['My Invoices', 'Invoices', 'file'], ['Sales Missions', 'Sales Missions', 'clock'], ['Transactions', 'Transactions', 'dollar-sign'], ['Artwork Gallery', 'Artwork', 'layers'], ['Coupons', 'Coupons', 'check']];
      // monthly sales from real orders
      const now = new Date(); const monthKeys = []; for (let i = 5; i >= 0; i--) { const d = new Date(now.getFullYear(), now.getMonth() - i, 1); monthKeys.push(d.getFullYear() + '-' + (d.getMonth() + 1)); }
      const sales = monthKeys.map(mk => orders.filter(o => { const d = new Date(o.createdAt || 0); return (d.getFullYear() + '-' + (d.getMonth() + 1)) === mk; }).reduce((s, o) => s + (o.total || 0), 0));
      const thisMonth = sales[sales.length - 1] || 0;
      content = [
        h('div', { key: 'top', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 16 } },
          h('div', { style: { background: '#fff', borderRadius: 12, border: '1px solid ' + HAIR, padding: 18, display: 'flex', gap: 14, alignItems: 'center' } },
            h('span', { style: { height: 52, width: 52, borderRadius: '50%', border: '1px solid ' + HAIR, display: 'grid', placeItems: 'center', flex: 'none', color: MUT, fontWeight: 700 } }, (u.name || '?').slice(0, 1)),
            h('div', null, h('div', { style: { fontWeight: 700 } }, u.name), h('div', { style: { fontSize: 12.5, color: MUT } }, u.email),
              h('div', { style: { display: 'flex', gap: 14, marginTop: 8 } }, h('span', { 'data-go': 'set:cTab:Account', style: { fontSize: 12.5, color: '#2f7fd1', fontWeight: 600, cursor: 'pointer' } }, 'Account information'), h('span', { 'data-go': 'set:cTab:Addresses', style: { fontSize: 12.5, color: '#2f7fd1', fontWeight: 600, cursor: 'pointer' } }, 'Address Book')))),
          h('span', { 'data-go': 'set:cTab:Sales Missions', style: { cursor: 'pointer' } }, heroCard('Sales Missions', this.tierPct() + '%', null, 'linear-gradient(120deg,#12B3A6,#1aa6c4)', 'clock')),
          heroCard('Balance (' + this.currency() + ')', this.money(credit.balance || 0).replace(this.currency() + ' ', ''), h('span', { onClick: () => this.setState({ tu_open: true }), style: { display: 'inline-flex', alignItems: 'center', gap: 5, background: '#fff', color: INK, fontWeight: 700, fontSize: 12.5, borderRadius: 999, padding: '5px 12px', cursor: 'pointer' } }, '+ Top up'), 'linear-gradient(120deg,#E52220,#F0662E)', 'dollar-sign')),
        h('div', { key: 'main', style: { display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 300px', gap: 16, alignItems: 'start' } },
          h('div', { style: { background: '#fff', borderRadius: 12, border: '1px solid ' + HAIR, overflow: 'hidden' } },
            h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 1, background: HAIR } },
              this.statCard('Orders', String(orders.filter(o => o.status !== 'completed').length), { icon: 'file', accent: 'red', dot: orders.length > 0, go: 'set:cTab:Orders' }),
              this.statCard('Quotes', String(quotes.filter(q => q.status === 'issued' || q.status === 'reviewed').length), { icon: 'edit-3', accent: 'teal', go: 'set:cTab:Quotations' }),
              this.statCard('Invoices', String(cinvs.length + orders.length), { icon: 'file', accent: 'orange', dot: cinvs.length > 0, go: 'set:cTab:Invoices' })),
            h('div', { style: { padding: 20, borderTop: '1px solid ' + HAIR } },
              h('div', { style: { display: 'flex', alignItems: 'center', gap: 10 } }, h('span', { style: { fontSize: 13, fontWeight: 600, color: MUT } }, 'Current Month Sales')),
              h('div', { style: { display: 'flex', alignItems: 'center', gap: 8, margin: '4px 0 2px' } }, h('span', { style: { fontSize: 26, fontWeight: 700 } }, this.money(thisMonth)), this.metricBadge('+17%'), h('span', { style: { fontSize: 12, color: FAINT } }, 'vs last month')),
              h('div', { style: { marginTop: 10 } }, this.lineChart(MONTHS, sales, { h: 300 })))),
          h('div', { style: { background: '#fff', borderRadius: 12, border: '1px solid ' + HAIR, padding: 16 } },
            h('div', { style: { fontSize: 13, fontWeight: 700, marginBottom: 10 } }, 'Links'),
            h('div', { style: { display: 'flex', flexDirection: 'column', gap: 4 } },
              links.map(l => h('span', { key: l[0], 'data-go': 'set:cTab:' + l[1], style: { display: 'flex', alignItems: 'center', gap: 10, padding: '7px 4px', cursor: 'pointer', fontSize: 13.5 } },
                h('span', { style: { height: 30, width: 30, borderRadius: '50%', background: '#eaf7f9', display: 'grid', placeItems: 'center', flex: 'none' } }, this.dashIcon(l[2], '#12B3A6', 15)), l[0]))))),
      ];
    } else if (tab === 'Orders') {
      const oq = (this.state.coSearch || '').toLowerCase();
      const rows = orders.filter(o => !oq || o.id.toLowerCase().indexOf(oq) >= 0).map(o => [
        (o.createdAt || '').slice(0, 10),
        h('span', { 'data-go': 'trackorder:' + o.id, style: { color: '#E52220', fontWeight: 600, cursor: 'pointer' } }, o.id.replace('PO-2026-', '')),
        this.pillDot(o.status === 'paid' ? 'Paid' : o.status === 'completed' ? 'Completed' : (o.status || '').replace(/_/g, ' '), o.status === 'completed' ? 'ok' : o.status === 'paid' ? 'teal' : 'warn'),
        h('div', { style: { display: 'flex', flexDirection: 'column', gap: 4 } }, (o.items || []).map((it, i) => h('span', { key: i, style: { fontSize: 12.5 } }, it.product))),
        this.money(o.total),
        h('span', { style: { display: 'flex', gap: 12 } },
          h('span', { onClick: () => this.openDoc(o.id, 'invoice'), title: 'Download invoice', style: { cursor: 'pointer', color: MUT } }, '⭳'),
          h('span', { 'data-go': 'trackorder:' + o.id, title: 'Track', style: { cursor: 'pointer', color: MUT } }, '⤳')),
      ]);
      content = [stitle('Orders'),
        this.filterRow({ searchKey: 'coSearch', dateKey: 'coDate', statusKey: 'coStatus', statuses: ['Paid', 'Completed', 'Pending payment'] }),
        this.dataCard([{ label: 'Date' }, { label: 'Order' }, { label: 'Status' }, { label: 'Items' }, { label: 'Amount', right: true }, { label: '', right: true }], rows, { empty: 'No orders yet.', minWidth: 760 })];
    } else if (tab === 'Invoices') {
      const orderInv = orders.map(o => ({ date: (o.createdAt || '').slice(0, 10), inv: 'INV-' + o.id.replace('PO-', ''), order: o.id, job: (o.items || []).map(it => it.product).join(', '), amount: o.total, open: () => this.openDoc(o.id, 'invoice') }));
      const custInv = cinvs.map(iv => ({ date: (iv.date || '').slice(0, 10), inv: iv.number || iv.id, order: iv.orderId || '—', job: (iv.description || '').split('\n')[0], amount: iv.price, open: () => this.openDoc(iv.id, 'custominvoice') }));
      const all = orderInv.concat(custInv);
      const iq = (this.state.ciSearch || '').toLowerCase();
      const rows = all.filter(r => !iq || r.inv.toLowerCase().indexOf(iq) >= 0).map(r => [
        r.date, h('span', { onClick: r.open, style: { color: '#E52220', fontWeight: 600, cursor: 'pointer' } }, r.inv),
        h('span', { style: { color: '#E52220', fontWeight: 600 } }, r.order), r.job, this.money(r.amount),
        h('span', { onClick: r.open, title: 'Download', style: { cursor: 'pointer', color: MUT } }, '⭳'),
      ]);
      content = [stitle('Invoices'),
        this.filterRow({ searchKey: 'ciSearch', dateKey: 'ciDate', statusKey: null }),
        this.dataCard([{ label: 'Date' }, { label: 'Invoice #' }, { label: 'Order' }, { label: 'Job Name' }, { label: 'Amount', right: true }, { label: '', right: true }], rows, { empty: 'No invoices yet.', minWidth: 820 })];
    } else if (tab === 'Transactions') {
      const rows = (credit.ledger || []).map(e => [
        (e.ts || '').slice(0, 10),
        e.orderId ? h('span', { style: { color: '#E52220', fontWeight: 600 } }, e.orderId.replace('PO-2026-', '')) : '',
        (e.reason === 'TOPUP' ? 'Reload' : e.reason === 'ORDER_OFFSET' ? 'Order' : e.reason) + (e.orderId ? ' #' + e.orderId.replace('PO-2026-', '') : ''),
        this.pillDot(e.amount < 0 ? 'DEBIT' : 'CREDIT', e.amount < 0 ? 'warn' : 'ok'),
        e.amount < 0 ? Math.abs(e.amount).toFixed(2) : '0.00',
        e.amount >= 0 ? e.amount.toFixed(2) : '0.00',
        (e.balanceAfter != null ? e.balanceAfter : 0).toFixed(2),
      ]);
      content = [
        h('div', { key: 'h', style: { display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' } }, stitle('Transactions'),
          h('span', { style: { marginLeft: 'auto', fontSize: 13.5, color: MUT } }, 'Balance: ', h('b', { style: { color: INK } }, this.money(credit.balance || 0))),
          h('span', { onClick: () => this.setState({ tu_open: true }), style: { display: 'inline-flex', alignItems: 'center', gap: 6, background: '#E52220', color: '#fff', fontWeight: 600, fontSize: 14, padding: '10px 20px', borderRadius: 999, cursor: 'pointer' } }, '+ Top up')),
        this.filterRow({ searchKey: 'trSearch', dateKey: 'trDate', statusKey: null, action: h('span', { onClick: () => { if (typeof window !== 'undefined') window.print(); }, style: { display: 'inline-flex', alignItems: 'center', gap: 6, color: '#fff', background: 'linear-gradient(120deg,#12B3A6,#1aa6c4)', fontWeight: 600, fontSize: 13.5, padding: '9px 18px', borderRadius: 999, cursor: 'pointer' } }, '⭳ Print Statement') }),
        this.dataCard([{ label: 'Date' }, { label: 'Reference #' }, { label: 'Description' }, { label: 'Type' }, { label: 'Debit (' + this.currency() + ')', right: true }, { label: 'Credit (' + this.currency() + ')', right: true }, { label: 'Balance (' + this.currency() + ')', right: true }], rows, { empty: 'No transactions yet.', minWidth: 900 })];
    } else if (tab === 'Sales Missions') {
      const TIERS = [['Bronze', 1000, 5], ['Silver', 3000, 8], ['Gold', 5000, 10], ['Platinum', 10000, 15]];
      const spend = u.spend12mo || 0; const maxT = 10000;
      const medal = c => h('span', { style: { height: 46, width: 46, borderRadius: '50%', border: '3px solid ' + c, display: 'grid', placeItems: 'center', flex: 'none', color: c, fontWeight: 700, fontSize: 12 } }, 'P');
      const bar = pct => h('div', { style: { flex: 1, height: 8, borderRadius: 999, background: '#eaeaea', overflow: 'hidden' } }, h('div', { style: { width: Math.min(100, pct) + '%', height: '100%', background: 'linear-gradient(90deg,#12B3A6,#2f7fd1)' } }));
      content = [stitle('Sales Missions'),
        h('div', { key: 'ov', style: { background: '#fff', borderRadius: 12, border: '1px solid ' + HAIR, padding: '20px 24px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 22, alignItems: 'center' } },
          h('div', { style: { display: 'flex', gap: 14, alignItems: 'center' } }, medal('#9aa4ad'), h('div', null, h('div', { style: { fontSize: 12.5, color: MUT } }, 'Current Tier'), h('div', { style: { fontSize: 22, fontWeight: 600 } }, u.tier))),
          h('div', null, h('div', { style: { fontSize: 12.5, color: MUT } }, 'Current Sales (' + this.currency() + ')'), h('div', { style: { fontSize: 22, fontWeight: 600 } }, spend.toLocaleString())),
          h('div', null, h('div', { style: { fontSize: 12.5, color: MUT } }, 'Current discount'), h('div', { style: { fontSize: 22, fontWeight: 600 } }, this.tierPct() + '%')),
          h('div', { style: { display: 'flex', flexDirection: 'column', gap: 8 } }, bar(Math.round(spend / maxT * 100)), h('span', { style: { fontSize: 12.5, color: INK } }, 'Target ' + TIERS.filter(t => spend >= t[1]).length + ' / ' + TIERS.length))),
        h('div', { key: 'tiers', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(320px,1fr))', gap: 16 } },
          TIERS.map(t => { const pct = Math.min(100, Math.round(spend / t[1] * 100)); return h('div', { key: t[0], style: { background: '#fff', borderRadius: 12, border: '1px solid ' + HAIR, padding: 20, display: 'flex', gap: 16 } },
            medal(t[0] === 'Bronze' ? '#c07b3a' : t[0] === 'Silver' ? '#9aa4ad' : t[0] === 'Gold' ? '#d4a017' : '#7a8391'),
            h('div', { style: { flex: 1 } }, h('div', { style: { fontWeight: 700, marginBottom: 8 } }, t[0]),
              h('div', { style: { display: 'flex', gap: 16, marginBottom: 10 } }, h('div', null, h('div', { style: { fontSize: 12, color: MUT } }, 'Target Sales'), h('div', { style: { fontSize: 18, fontWeight: 600 } }, t[1].toLocaleString())), h('div', null, h('div', { style: { fontSize: 12, color: MUT } }, 'Discounts'), h('div', { style: { fontSize: 18, fontWeight: 600 } }, t[2] + '%'))),
              h('div', { style: { display: 'flex', gap: 10, alignItems: 'center' } }, bar(pct), h('span', { style: { fontSize: 12.5 } }, pct + '%')))); })),
      ];
    } else if (tab === 'Quotations') {
      const rows = quotes.map(q => [
        (q.createdAt || '').slice(0, 10),
        h('span', { onClick: () => { this.quoteView(q.id); this.openDoc(q.id, 'quote'); }, style: { color: '#E52220', fontWeight: 600, cursor: 'pointer' } }, q.id),
        this.pillDot({ requested: 'Being priced', issued: 'Ready for you', reviewed: 'Awaiting you', accepted: 'Accepted', amendment: 'Updating', declined: 'Closed' }[q.status] || q.status, q.status === 'accepted' ? 'ok' : q.status === 'issued' ? 'warn' : 'teal'),
        (q.requirement && q.requirement.product) || 'Custom job',
        q.price != null ? this.rm(q.price) : '—',
        (q.status === 'issued' || q.status === 'reviewed') ? h('span', { onClick: () => this.quoteAccept(q.id), style: { color: '#E52220', fontWeight: 600, cursor: 'pointer', fontSize: 13 } }, 'Accept & pay') : (q.orderId ? h('span', { 'data-go': 'trackorder:' + q.orderId, style: { color: '#E52220', fontWeight: 600, cursor: 'pointer', fontSize: 13 } }, 'Track') : ''),
      ]);
      content = [stitle('My Quotations'),
        this.dataCard([{ label: 'Date' }, { label: 'Quote' }, { label: 'Status' }, { label: 'Product' }, { label: 'Amount', right: true }, { label: '', right: true }], rows, { empty: 'No quotations yet — request one from the Contact page.', minWidth: 760 })];
    } else if (tab === 'Artwork') {
      const arts = []; orders.forEach(o => (o.items || []).forEach(it => (it.artworks || []).forEach(a => arts.push({ name: a, order: o.id }))));
      content = [stitle('Artwork Gallery'),
        h('p', { key: 'p', style: { margin: '-4px 0 6px', color: MUT, fontSize: 13.5 } }, 'All artworks uploaded by me'),
        arts.length ? h('div', { key: 'g', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(240px,1fr))', gap: 16 } },
          arts.map((a, i) => h('div', { key: i, style: { background: '#fff', border: '1px solid ' + HAIR, borderRadius: 10, padding: 16, display: 'flex', gap: 12, alignItems: 'flex-start' } },
            h('span', { style: { fontSize: 10, fontWeight: 700, color: '#fff', background: /\.pdf$/i.test(a.name) ? '#E52220' : '#2f7fd1', borderRadius: 4, padding: '3px 5px', flex: 'none' } }, /\.pdf$/i.test(a.name) ? 'PDF' : 'IMG'),
            h('div', { style: { minWidth: 0 } }, h('div', { style: { fontSize: 13.5, fontWeight: 600, wordBreak: 'break-word' } }, a.name), h('div', { style: { fontSize: 11.5, color: FAINT, marginTop: 3 } }, 'Order ' + a.order))))) :
          h('div', { key: 'e', style: { background: '#fff', border: '1px dashed ' + HAIR, borderRadius: 12, padding: 34, textAlign: 'center', color: FAINT } }, 'No artworks yet — they appear here once you place an order with uploaded files.')];
    } else if (tab === 'Coupons') {
      content = [stitle('My Coupons'), h('p', { key: 'e', style: { color: MUT, fontSize: 14 } }, 'You have no coupons.')];
    } else if (tab === 'Account') {
      const first = this.state.pf_first != null ? this.state.pf_first : (u.name || '').split(' ')[0];
      const last = this.state.pf_last != null ? this.state.pf_last : (u.name || '').split(' ').slice(1).join(' ');
      const inp = { font: '400 14px Montserrat,sans-serif', padding: '11px 13px', border: '1px solid ' + HAIR, borderRadius: 8, width: '100%', background: '#fff' };
      const lbl = (t, req) => h('div', { style: { fontSize: 13, color: MUT, marginBottom: 6 } }, t, req ? h('span', { style: { color: '#E52220' } }, ' *') : null);
      content = [stitle('Account Information'),
        h('div', { key: 'f', style: { background: '#fff', border: '1px solid ' + HAIR, borderRadius: 12, padding: 24, maxWidth: 720 } },
          h('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 } },
            h('div', null, lbl('First Name', true), h('input', { value: first, onChange: e => this.setField('pf_first', e.target.value), style: inp })),
            h('div', null, lbl('Last Name', true), h('input', { value: last, onChange: e => this.setField('pf_last', e.target.value), style: inp }))),
          h('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 } },
            h('div', null, lbl('Mobile', true), h('input', { value: this.state.pf_phone != null ? this.state.pf_phone : (u.phone || ''), onChange: e => this.setField('pf_phone', e.target.value), style: inp })),
            h('div', null, lbl('Email Address', true), h('input', { value: u.email, disabled: true, style: Object.assign({}, inp, { background: ALT, color: MUT }) }))),
          h('div', { style: { marginBottom: 16 } }, lbl('Password'), h('span', { onClick: () => this.setState({ pw_open: true }), style: { display: 'inline-block', border: '1px solid ' + HAIR, borderRadius: 8, padding: '9px 16px', fontSize: 13.5, fontWeight: 600, cursor: 'pointer' } }, 'Change Password')),
          h('label', { style: { display: 'flex', gap: 9, alignItems: 'center', fontSize: 13, color: MUT, marginBottom: 16, cursor: 'pointer' } }, h('input', { type: 'checkbox', checked: !!this.state.pf_news, onChange: e => this.setField('pf_news', e.target.checked) }), 'Subscribe to our Newsletter'),
          this.state.pf_msg ? h('div', { style: { fontSize: 12.5, color: '#3d8b40', marginBottom: 10 } }, this.state.pf_msg) : null,
          h('span', { onClick: () => this.submitProfile(), style: { display: 'block', textAlign: 'center', background: '#E52220', color: '#fff', fontWeight: 600, fontSize: 15, padding: '13px', borderRadius: 8, cursor: this.state.pf_busy ? 'wait' : 'pointer' } }, this.state.pf_busy ? 'Saving…' : 'Submit'))];
    } else { // Addresses
      content = [stitle('Address Book'),
        h('div', { key: 'add', style: { marginBottom: 4 } }, h('span', { 'data-go': this.state.addingAddr ? 'set:addingAddr:' : 'set:addingAddr:1', style: { fontSize: 13.5, color: '#E52220', fontWeight: 600, cursor: 'pointer' } }, this.state.addingAddr ? 'Cancel' : '+ Add address')),
        this.state.addingAddr ? h('div', { key: 'form', style: { background: '#fff', border: '1px solid ' + HAIR, borderRadius: 12, padding: 16, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 } },
          [['adLabel', 'Label (Home/Office)'], ['adLine1', 'Address line 1'], ['adLine2', 'Address line 2'], ['adPostcode', 'Postcode'], ['adCity', 'City'], ['adState', 'State']].map(f => h('input', { key: f[0], placeholder: f[1], value: this.state[f[0]] || '', onChange: e => this.setField(f[0], e.target.value), style: { font: '400 13px Montserrat,sans-serif', padding: '9px 11px', border: '1px solid ' + HAIR, borderRadius: 7 } })),
          h('span', { 'data-go': 'addraddsave', style: { gridColumn: '1 / -1', background: '#E52220', color: '#fff', fontWeight: 600, fontSize: 13, padding: '10px', borderRadius: 8, textAlign: 'center', cursor: 'pointer' } }, 'Save address')) : null,
        (this.state.addresses || []).length ? h('div', { key: 'list', style: { background: '#fff', border: '1px solid ' + HAIR, borderRadius: 12, overflow: 'hidden' } },
          this.state.addresses.map((a, i) => h('div', { key: a.id, style: { display: 'grid', gridTemplateColumns: '1fr 1.4fr 1fr auto', gap: 14, padding: '16px 18px', borderTop: i ? '1px solid ' + LINE : 'none', alignItems: 'start', fontSize: 13.5 } },
            h('div', { style: { fontWeight: 600 } }, a.name || a.label, a.isDefault ? h('span', { style: { marginLeft: 6 } }, this.pillDot('Default', 'teal')) : null),
            h('div', { style: { color: MUT, lineHeight: 1.6 } }, [a.line1, a.line2, a.postcode + ' ' + a.city, a.state, ({ MY: 'Malaysia', SG: 'Singapore', BN: 'Brunei' })[a.country] || a.country].filter(Boolean).join(', ')),
            h('div', { style: { color: MUT } }, a.phone || u.phone || ''),
            h('div', { style: { display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-end' } },
              !a.isDefault ? h('span', { 'data-go': 'addrdefault:' + a.id, style: { color: '#2f7fd1', fontWeight: 600, cursor: 'pointer', fontSize: 12.5 } }, 'Set default') : null,
              h('span', { 'data-go': 'addrdel:' + a.id, style: { color: '#c0392b', fontWeight: 600, cursor: 'pointer', fontSize: 12.5 } }, 'Delete'))))) :
          h('div', { key: 'e', style: { background: '#fff', border: '1px dashed ' + HAIR, borderRadius: 12, padding: 30, textAlign: 'center', color: FAINT } }, 'No saved addresses yet.')];
    }
    return this.customerPage(tabs, navActive, content);
  }

  // ===== ORDER TRACKING =====
  trackStage(status) {
    const map = { intake: 0, prepress: 1, prepress_issue: 1, escalated: 1, rejected: 1, scheduling: 2, printing: 2, outsourcing: 2, logistics: 3, dispatched: 3, completed: 4 };
    return map[status] != null ? map[status] : 0;
  }
  s_track() {
    const o = this.state.trackOrder;
    const STAGES = ['Order received', 'Prepress check', 'In production', 'Shipped', 'Delivered'];
    const lookup = h('div', { key: 'lk', style: { display: 'flex', gap: 8, flexWrap: 'wrap', maxWidth: 460, marginBottom: 22 } },
      h('input', { placeholder: 'Order number (e.g. PO-2026-04417)', value: this.state.trackInput != null ? this.state.trackInput : (this.state.order ? this.state.order.id : ''),
        onChange: e => this.setField('trackInput', e.target.value), style: { flex: 1, minWidth: 200, font: '400 14px Montserrat,sans-serif', padding: '11px 13px', border: '1px solid #eaeaea', borderRadius: 8 } }),
      h('span', { onClick: () => this.trackLookup(this.state.trackInput != null ? this.state.trackInput : (this.state.order ? this.state.order.id : '')),
        style: { background: TEAL, color: '#fff', fontWeight: 600, fontSize: 14, padding: '11px 20px', borderRadius: 8, cursor: 'pointer' } }, 'Track'));
    if (!o) return h('div', { style: { maxWidth: 900, margin: '0 auto', padding: '10px 20px 0' } },
      this.head('Track your order', 'Enter your order number to see live production status — customer-friendly labels on top of the real pipeline the floor uses.'),
      lookup,
      o === false ? h('div', { style: { color: '#c0392b', fontSize: 13 } }, 'No order found with that number.') : null);
    const jobs = o.jobs || [];
    const cur = jobs.length ? Math.min.apply(null, jobs.map(j => this.trackStage(j.status))) : 0;
    const paid = o.payment && o.payment.status === 'validated';
    return h('div', { style: { maxWidth: 1000, margin: '0 auto', padding: '10px 20px 0' } },
      this.head('Order ' + o.id, (o.customer && o.customer.name ? o.customer.name + ' · ' : '') + jobs.length + ' job(s) · ' + (o.channel || 'online') + ' · ' + (paid ? 'paid' : 'payment pending'),
        [this.btn('Invoice', 'ghost', 'doc:invoice:' + o.id), this.btn('Order slip', 'ghost', 'doc:slip:' + o.id), this.btn('Contact support', 'teal', 'crm')]),
      lookup,
      h('div', { key: 't', style: { border: '1px solid ' + HAIR, borderRadius: 14, padding: 20, marginBottom: 20 } },
        h('div', { style: { fontSize: 12.5, fontWeight: 600, marginBottom: 16 } }, 'Status timeline'),
        h('div', { style: { display: 'flex', gap: 0, flexWrap: 'wrap' } },
          STAGES.map((s, i) => h('div', { key: i, style: { flex: '1 1 120px', display: 'flex', flexDirection: 'column', gap: 8 } },
            h('div', { style: { display: 'flex', alignItems: 'center' } },
              h('span', { style: { height: 14, width: 14, borderRadius: '50%', flex: 'none', background: i > cur ? '#eaeaea' : (i === cur ? AMBER : TEAL) } }),
              i < STAGES.length - 1 && h('span', { style: { flex: 1, height: 2, background: i < cur ? TEAL : '#eaeaea' } })),
            h('div', { style: { fontSize: 12.5, fontWeight: i === cur ? 600 : 500, color: i > cur ? FAINT : INK } }, s)))),
        !paid ? h('div', { style: { marginTop: 16, background: '#fff5e2', color: '#a1660a', borderRadius: 8, padding: '11px 13px', fontSize: 12.5, lineHeight: 1.6 } }, 'Payment is pending — production starts once payment is confirmed. Paid by bank transfer? Our team validates it shortly.') : null),
      h('div', { key: 'j', style: { display: 'flex', flexDirection: 'column', gap: 14 } },
        jobs.map((j, i) => h('div', { key: i, style: { border: '1px solid ' + HAIR, borderRadius: 12, padding: 16, display: 'flex', gap: 14, background: '#fff' } },
          h('div', { style: { flex: '0 0 96px' } }, this.art((this.pkProducts().find(p => p.name === j.product) || {}).name || j.product)),
          h('div', { style: { flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 7 } },
            h('div', { style: { display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' } },
              h('span', { style: { font: '600 12px ui-monospace,Menlo,monospace', color: TEAL } }, j.id),
              h('span', { style: { fontSize: 14.5, fontWeight: 600 } }, j.product),
              h('span', { style: { marginLeft: 'auto' } }, this.chip(j.statusLabel || j.status, j.status === 'completed' ? 'ok' : (j.status === 'rejected' || j.status === 'prepress_issue' ? 'bad' : 'teal')))),
            h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.6 } }, j.spec || '—'),
            h('div', { style: { fontSize: 12, color: FAINT } }, 'Qty ' + (j.qty || 0).toLocaleString() + ' · ' + this.money(j.price || 0) + ' · artwork: ' + ((j.artwork && j.artwork.file) || '—'))))),
        jobs.length === 0 ? h('div', { style: { color: FAINT, fontSize: 13 } }, 'No jobs on this order.') : null));
  }

  // ===== OUTLET QUOTE BOARD =====
  s_outlet() {
    const u = this.state.user || {};
    const jobs = this.opsJobs();
    const outletName = (u.outlet || 'KL-Damansara').replace(/-/g, ' ');
    const code = '0' + (Array.from(outletName).reduce((a, c) => a + c.charCodeAt(0), 0) % 90000 + 10000);
    const identity = { title: outletName + ' Outlet', sub: code };
    const tabs = ['Dashboard', 'Sales performance', 'Orders', 'Custom quotes', 'Follow-ups'];
    const tab = tabs.indexOf(this.state.sTab) >= 0 ? this.state.sTab : 'Dashboard';
    const quotes = this.state.quotesList || [];
    const orders = this.state.staffOrders || [];
    const MONTHS = ['APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP'], ZERO = [0, 0, 0, 0, 0, 0];
    const followUp = quotes.filter(qq => qq.status === 'reviewed' || qq.status === 'issued').length;
    const activeJobs = jobs.filter(j => ['prepress', 'scheduler'].indexOf(j.queue) >= 0).length;
    const incoming = jobs.filter(j => j.status === 'logistics').length;
    const delivery = jobs.filter(j => j.status === 'dispatched').length;
    const sectionTitle = t => h('h1', { style: { fontSize: 30, fontWeight: 700, letterSpacing: '-.02em', margin: '4px 0 6px' } }, t);
    const card = (children, extra) => h('div', { style: Object.assign({ background: '#fff', borderRadius: 12, border: '1px solid ' + HAIR }, extra || {}) }, children);
    const salesLink = h('span', { 'data-go': 'set:sTab:Sales performance', style: { fontSize: 14, fontWeight: 600, color: '#E52220', cursor: 'pointer' } }, 'Sales performance ›');

    let content;
    if (tab === 'Dashboard') {
      content = [
        card([
          h('div', { key: 'q', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 1, background: HAIR } },
            this.statCard('Quote to follow up', String(followUp), { icon: 'edit-3', accent: 'teal', dot: followUp > 0, go: 'set:sTab:Custom quotes' }),
            this.statCard('Orders', String(activeJobs), { icon: 'file', accent: 'red', go: 'set:sTab:Orders' }),
            this.statCard('Incoming', String(incoming), { icon: 'check', accent: 'teal', go: 'set:sTab:Orders' }),
            this.statCard('Delivery', String(delivery), { icon: 'truck', accent: 'orange', go: 'set:sTab:Orders' })),
          h('div', { key: 's', style: { padding: 20, borderTop: '1px solid ' + HAIR } },
            h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'flex-start' } },
              h('div', null, h('div', { style: { fontSize: 13, fontWeight: 600, color: MUT } }, 'Sales amount'), h('div', { style: { display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 } }, h('span', { style: { fontSize: 26, fontWeight: 700 } }, '0.00'), this.metricBadge('N/A'))),
              salesLink),
            h('div', { style: { marginTop: 14 } }, this.lineChart(MONTHS, ZERO, { h: 300 }))),
          h('div', { key: 'c', style: { padding: 20, borderTop: '1px solid ' + HAIR } },
            h('span', { onClick: () => this.setState({ nu_open: true, nu_done: null }), style: { display: 'inline-flex', alignItems: 'center', gap: 8, background: '#E52220', color: '#fff', fontWeight: 600, fontSize: 14, padding: '11px 22px', borderRadius: 999, cursor: 'pointer' } }, this.dashIcon('user-plus', '#fff', 16), 'Create new user')),
        ], { overflow: 'hidden' }),
        this.notifPanel(),
      ];
    } else if (tab === 'Sales performance') {
      const individual = this.state.spView === 'individual';
      const rangeSel = h('select', { value: this.state.spRange || 'Last 6 months', onChange: e => this.setField('spRange', e.target.value), style: { font: '400 13.5px Montserrat,sans-serif', padding: '9px 14px', border: '1px solid ' + HAIR, borderRadius: 999, background: '#fff' } }, ['Last 6 months', 'Last 3 months', 'Last 12 months'].map(x => h('option', { key: x }, x)));
      if (!individual) {
        content = [
          sectionTitle('Sales performance report'),
          h('div', { key: 'f', style: { display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' } }, rangeSel),
          card([h('div', { style: { padding: 20 } },
            h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' } },
              h('div', null, h('div', { style: { fontSize: 13.5, fontWeight: 600 } }, 'Outlet sales performance'), h('div', { style: { fontSize: 22, fontWeight: 700, marginTop: 3 } }, 'Apr 2026 – Sep 2026')),
              h('span', { 'data-go': 'set:spView:individual', style: { fontSize: 14, fontWeight: 600, color: '#E52220', cursor: 'pointer' } }, 'Individual performance report ›')),
            h('div', { style: { marginTop: 16 } }, this.lineChart(MONTHS, ZERO, { h: 300 })))]),
          card([
            h('div', { key: 't', style: { padding: 18, fontSize: 14, fontWeight: 700 } }, 'Product sales details'),
            h('div', { key: 'tb', style: { overflowX: 'auto', borderTop: '1px solid ' + HAIR } },
              h('table', { style: { width: '100%', borderCollapse: 'collapse', fontSize: 13.5, minWidth: 900 } },
                h('thead', null, h('tr', null, ['Product', 'Apr 26', 'May 26', 'Jun 26', 'Jul 26', 'Aug 26', 'Sep 26'].map((c, i) => h('th', { key: i, style: { textAlign: i ? 'right' : 'left', padding: '13px 18px', fontSize: 12.5, fontWeight: 700, whiteSpace: 'nowrap' } }, c)))),
                h('tbody', null, h('tr', null, h('td', { colSpan: 7, style: { padding: '20px 18px', color: FAINT } }, 'No data available in table'))),
                h('tfoot', null, h('tr', { style: { borderTop: '1px solid ' + HAIR } }, ['Total', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00'].map((c, i) => h('td', { key: i, style: { textAlign: i ? 'right' : 'left', padding: '14px 18px', fontWeight: 700 } }, c)))))),
          ]),
        ];
      } else {
        const issued = quotes.filter(qq => qq.status !== 'requested').length;
        const followed = quotes.filter(qq => qq.decision).length;
        const conv = quotes.length ? Math.round((quotes.filter(qq => qq.status === 'accepted').length / quotes.length) * 100) + '%' : '0%';
        const newAcc = 1;
        const metrics = [
          ['Sales amount', '0.00', 'N/A', 'dollar-sign', 'red'], ['Orders', '0', 'N/A', 'file', 'red'], ['New accounts', String(newAcc), 'New', 'user-plus', 'orange'],
          ['Quotes issued', String(issued), issued ? 'New' : 'N/A', 'edit-3', 'teal'], ['Quotes followed up', String(followed), followed ? 'New' : 'N/A', 'phone', 'teal'], ['Sales conversion', conv, 'N/A', 'check', 'teal'],
        ];
        content = [
          sectionTitle('Individual performance report'),
          h('div', { key: 'f', style: { display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' } },
            h('select', { value: outletName + ' Outlet', onChange: () => {}, style: { font: '400 13.5px Montserrat,sans-serif', padding: '9px 14px', border: '1px solid ' + HAIR, borderRadius: 999, background: '#fff' } }, h('option', null, outletName + ' Outlet')),
            rangeSel,
            h('span', { 'data-go': 'set:spView:outlet', style: { marginLeft: 'auto', fontSize: 14, fontWeight: 600, color: '#E52220', cursor: 'pointer' } }, 'Outlet performance report ›')),
          card([
            h('div', { key: 'h', style: { padding: 20 } }, h('div', { style: { fontSize: 14, fontWeight: 700 } }, 'Key metrics'), h('div', { style: { fontSize: 22, fontWeight: 700, marginTop: 2 } }, 'Apr 2026 – Sep 2026')),
            h('div', { key: 'g', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 1, background: HAIR, borderTop: '1px solid ' + HAIR } },
              metrics.map(m => this.statCard(m[0], m[1], { badge: m[2], icon: m[3], accent: m[4] }))),
          ], { overflow: 'hidden' }),
          card([h('div', { style: { padding: 20 } },
            h('div', null, h('div', { style: { fontSize: 13, fontWeight: 600, color: MUT } }, 'Sales amount'), h('div', { style: { display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 } }, h('span', { style: { fontSize: 26, fontWeight: 700 } }, '0.00'), this.metricBadge('N/A'))),
            h('div', { style: { marginTop: 14 } }, this.lineChart(MONTHS, ZERO, { h: 300 })))]),
        ];
      }
    } else if (tab === 'Orders') {
      const statusTone = s => /paid|complete|deliver/i.test(s) ? 'ok' : /pending|payment/i.test(s) ? 'warn' : 'teal';
      const oq = (this.state.ordSearch || '').toLowerCase();
      const rows = orders.filter(o => !oq || o.id.toLowerCase().indexOf(oq) >= 0 || ((o.customer && o.customer.name) || '').toLowerCase().indexOf(oq) >= 0)
        .map(o => [
          (o.createdAt || '').slice(0, 10),
          h('span', { 'data-go': 'vieworder:' + o.id, style: { color: '#E52220', fontWeight: 600, cursor: 'pointer' } }, o.id),
          this.pillDot(o.status === 'paid' ? 'Paid' : (o.status || '').replace(/_/g, ' '), statusTone(o.status || '')),
          (o.customer && o.customer.name) || '—',
          this.rm(o.total),
        ]);
      content = [sectionTitle('Orders'),
        this.filterRow({ searchKey: 'ordSearch', dateKey: 'ordDate', statusKey: 'ordStatus', statuses: ['Paid', 'Pending payment', 'Completed'] }),
        this.dataCard([{ label: 'Date' }, { label: 'Order' }, { label: 'Status' }, { label: 'Customer' }, { label: 'Amount', right: true }], rows, { empty: 'No data available in table', minWidth: 720 })];
    } else if (tab === 'Custom quotes') {
      const STAT = { requested: ['Awaiting Scheduler', 'warn'], issued: ['Not followed up', 'warn'], reviewed: ['Reviewed', 'teal'], amendment: ['Amendment', 'warn'], declined: ['Rejected', 'bad'], accepted: ['Accepted', 'ok'] };
      const qq2 = (this.state.cqSearch || '').toLowerCase();
      const rows = quotes.filter(qz => !qq2 || qz.id.toLowerCase().indexOf(qq2) >= 0 || ((qz.requirement && qz.requirement.product) || '').toLowerCase().indexOf(qq2) >= 0)
        .map(qz => { const st = STAT[qz.status] || [qz.status, 'neutral'];
          return [
            (qz.createdAt || '').slice(0, 10),
            h('span', { onClick: () => this.openDoc(qz.id, 'quote'), style: { color: '#E52220', fontWeight: 600, cursor: 'pointer' } }, qz.id),
            this.pillDot(st[0], st[1]),
            (qz.requirement && qz.requirement.product) || 'Custom job',
            qz.price != null ? this.rm(qz.price) : '—',
            (qz.status === 'issued' || qz.status === 'reviewed') ? h('span', { onClick: () => this.setState({ decQuote: this.state.decQuote === qz.id ? null : qz.id }), style: { color: '#E52220', fontWeight: 600, cursor: 'pointer', fontSize: 13 } }, 'Follow up') : '',
          ]; });
      const newQuoteBtn = h('span', { onClick: () => this.setState({ wk_open: !this.state.wk_open, wk_done: null }), style: { display: 'inline-flex', alignItems: 'center', gap: 7, background: '#E52220', color: '#fff', fontWeight: 600, fontSize: 14, padding: '10px 20px', borderRadius: 999, cursor: 'pointer' } }, this.dashIcon('user-plus', '#fff', 15), this.state.wk_open ? 'Close' : 'New Quote');
      content = [sectionTitle('Custom quotes'),
        this.filterRow({ searchKey: 'cqSearch', dateKey: 'cqDate', statusKey: 'cqStatus', statuses: ['Not followed up', 'Reviewed', 'Accepted', 'Rejected'], action: newQuoteBtn }),
        this.state.wk_open ? this.walkinBuilder() : null,
        this.decQuoteBar(),
        this.dataCard([{ label: 'Date' }, { label: 'Quote' }, { label: 'Status' }, { label: 'Product' }, { label: 'Amount', right: true }, { label: '', right: true }], rows, { empty: 'No custom quotes yet.', minWidth: 760 })];
    } else { // Follow-ups — quotes awaiting the customer's decision (reviewed >1 day = overdue)
      const now = Date.now();
      const due = quotes.filter(qz => qz.status === 'issued' || qz.status === 'reviewed');
      const overdue = q => q.status === 'reviewed' && q.viewedAt && (now - Date.parse(q.viewedAt) > 24 * 3600e3);
      const rows = due.sort((a, b) => (overdue(b) ? 1 : 0) - (overdue(a) ? 1 : 0)).map(qz => [
        (qz.createdAt || '').slice(0, 10),
        h('span', { onClick: () => this.openDoc(qz.id, 'quote'), style: { color: '#E52220', fontWeight: 600, cursor: 'pointer' } }, qz.id),
        (qz.customer && qz.customer.name) || 'Customer',
        this.pillDot(overdue(qz) ? 'Follow up due' : (qz.status === 'reviewed' ? 'Reviewed — waiting' : 'Sent — awaiting'), overdue(qz) ? 'warn' : qz.status === 'reviewed' ? 'teal' : 'neutral'),
        qz.price != null ? this.rm(qz.price) : '—',
        h('span', { onClick: () => this.setState({ decQuote: this.state.decQuote === qz.id ? null : qz.id }), style: { color: '#E52220', fontWeight: 600, cursor: 'pointer', fontSize: 13 } }, 'Record decision'),
      ]);
      content = [sectionTitle('Follow-ups'),
        h('p', { key: 'p', style: { margin: '-4px 0 8px', color: MUT, fontSize: 13.5, maxWidth: '80ch', lineHeight: 1.6 } }, 'Quotes waiting on the customer. Once a customer has reviewed a quote and taken no action for a day, it’s flagged ', h('b', null, 'Follow up due'), ' — call them, then record their decision (proceed converts it to an order; amendment goes back to the Scheduler).'),
        this.decQuoteBar(),
        this.dataCard([{ label: 'Date' }, { label: 'Quote' }, { label: 'Customer' }, { label: 'Status' }, { label: 'Amount', right: true }, { label: '', right: true }], rows, { empty: 'Nothing to follow up — you’re all caught up.', minWidth: 760 })];
    }
    return this.staffPage(tabs, tab, identity, content);
  }
  // inline decision bar for a quote the outlet is following up (proceed / amend / not proceed)
  decQuoteBar() {
    const qid = this.state.decQuote; if (!qid) return null;
    const q = (this.state.quotesList || []).find(x => x.id === qid); if (!q) return null;
    const inp = { font: '400 13px Montserrat,sans-serif', padding: '9px 11px', border: '1px solid ' + HAIR, borderRadius: 8, flex: 1, minWidth: 160 };
    return h('div', { style: { border: '1px solid #d99100', background: '#fffaf0', borderRadius: 12, padding: 16 } },
      h('div', { style: { fontSize: 13.5, fontWeight: 600, marginBottom: 4 } }, 'Record ' + ((q.customer && q.customer.name) || 'the customer') + '’s decision on ' + qid),
      h('div', { style: { fontSize: 12.5, color: MUT, marginBottom: 10 } }, (q.requirement && q.requirement.product) + (q.price != null ? ' · ' + this.rm(q.price) : '')),
      h('div', { style: { display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' } },
        h('span', { onClick: () => this.quoteDecision(qid, 'proceed'), style: { background: '#E52220', color: '#fff', fontWeight: 600, fontSize: 13, padding: '9px 16px', borderRadius: 999, cursor: 'pointer' } }, 'Proceed → order'),
        h('input', { placeholder: 'Amendment / notes for the Scheduler', value: this.state['decnote_' + qid] || '', onChange: e => this.setField('decnote_' + qid, e.target.value), style: inp }),
        h('span', { onClick: () => this.quoteDecision(qid, 'amend', this.state['decnote_' + qid]), style: { border: '1px solid #d99100', color: '#a1660a', fontWeight: 600, fontSize: 13, padding: '9px 16px', borderRadius: 999, cursor: 'pointer' } }, 'Amend → Scheduler'),
        h('span', { onClick: () => this.quoteDecision(qid, 'not_proceed', this.state['decnote_' + qid]), style: { border: '1px solid ' + HAIR, color: MUT, fontWeight: 600, fontSize: 13, padding: '9px 16px', borderRadius: 999, cursor: 'pointer' } }, 'Not proceeding'),
        h('span', { onClick: () => this.setState({ decQuote: null }), style: { color: FAINT, fontSize: 18, cursor: 'pointer', marginLeft: 'auto' } }, '×')));
  }
  // outlet: sign up a walk-in customer + file a quote request to the scheduler
  walkinBuilder() {
    if (!this.state.wk_open) return null;
    const inp = { font: '400 13px Montserrat,sans-serif', padding: '9px 11px', border: '1px solid ' + HAIR, borderRadius: 7, width: '100%' };
    const done = this.state.wk_done;
    if (done) return h('div', { key: 'wkd', style: { border: '1px solid ' + TEAL, borderRadius: 12, padding: 18, background: '#f2fbf4', marginTop: 20 } },
      h('div', { style: { fontSize: 14, fontWeight: 600, marginBottom: 8 } }, '✅ Quote request ' + done.quote.id + ' sent to the Scheduler'),
      h('div', { style: { fontSize: 13, color: MUT, lineHeight: 1.7 } },
        'Customer ', h('b', null, done.quote.customer.name), ' · ', done.quote.requirement.product, done.quote.requirement.qty ? ' × ' + done.quote.requirement.qty : '',
        done.createdAccount ? h('div', { style: { marginTop: 8, padding: '10px 12px', background: '#fff', border: '1px dashed ' + HAIR, borderRadius: 8 } },
          'New account created for the customer: ', h('b', null, done.customer.email), ' · temporary password ', h('b', { style: { fontFamily: 'ui-monospace,Menlo,monospace' } }, done.tempPassword), h('div', { style: { fontSize: 12, color: FAINT, marginTop: 3 } }, 'Share this so they can log in to view the quote once the Scheduler prices it. They can reset it anytime.'))
          : h('div', { style: { marginTop: 6, fontSize: 12.5, color: MUT } }, 'Linked to their existing account.')),
      h('div', { style: { marginTop: 12, display: 'flex', gap: 10 } },
        h('span', { onClick: () => this.setState({ wk_done: null }), style: { background: TEAL, color: '#fff', fontWeight: 600, fontSize: 13, padding: '9px 16px', borderRadius: 8, cursor: 'pointer' } }, 'New walk-in quote'),
        h('span', { onClick: () => this.setState({ wk_open: false, wk_done: null }), style: { border: '1px solid ' + HAIR, color: MUT, fontWeight: 600, fontSize: 13, padding: '9px 16px', borderRadius: 8, cursor: 'pointer' } }, 'Done')));
    return h('div', { key: 'wk', style: { border: '1px solid ' + TEAL, borderRadius: 12, padding: 18, background: '#fdf7f7', marginTop: 20 } },
      h('div', { style: { fontSize: 15, fontWeight: 600, marginBottom: 4 } }, 'New walk-in quote'),
      h('p', { style: { margin: '0 0 12px', fontSize: 12.5, color: MUT, lineHeight: 1.6 } }, 'Collect the customer’s details (this creates their account) and what they need. It’s filed to the Scheduler to price — the customer and this outlet are notified when the quote is ready.'),
      h('div', { style: { fontSize: 11, fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: FAINT, marginBottom: 7 } }, 'Customer'),
      h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))', gap: 8, marginBottom: 12 } },
        h('input', { placeholder: 'Full name', value: this.state.wk_name || '', onChange: e => this.setField('wk_name', e.target.value), style: inp }),
        h('input', { placeholder: 'Email', value: this.state.wk_email || '', onChange: e => this.setField('wk_email', e.target.value), style: inp }),
        h('input', { placeholder: 'Phone', value: this.state.wk_phone || '', onChange: e => this.setField('wk_phone', e.target.value), style: inp })),
      h('div', { style: { fontSize: 11, fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: FAINT, marginBottom: 7 } }, 'What they need'),
      h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))', gap: 8, marginBottom: 8 } },
        h('input', { placeholder: 'Product (e.g. Bunting)', value: this.state.wk_product || '', onChange: e => this.setField('wk_product', e.target.value), style: inp }),
        h('input', { placeholder: 'Quantity', value: this.state.wk_qty || '', onChange: e => this.setField('wk_qty', e.target.value), style: inp }),
        h('input', { placeholder: 'Size', value: this.state.wk_size || '', onChange: e => this.setField('wk_size', e.target.value), style: inp }),
        h('input', { placeholder: 'Material', value: this.state.wk_material || '', onChange: e => this.setField('wk_material', e.target.value), style: inp }),
        h('input', { placeholder: 'Finishing', value: this.state.wk_finishing || '', onChange: e => this.setField('wk_finishing', e.target.value), style: inp })),
      h('textarea', { placeholder: 'Remarks / deadline / notes', value: this.state.wk_remarks || '', onChange: e => this.setField('wk_remarks', e.target.value), style: Object.assign({}, inp, { minHeight: 70, resize: 'vertical', marginBottom: 8, fontFamily: 'inherit' }) }),
      this.state.wk_err ? h('div', { style: { fontSize: 12, color: '#c0392b', marginBottom: 8 } }, this.state.wk_err) : null,
      h('span', { onClick: () => this.submitWalkinQuote(), style: { display: 'inline-block', background: TEAL, color: '#fff', fontWeight: 600, fontSize: 13, padding: '10px 18px', borderRadius: 8, cursor: this.state.wk_busy ? 'wait' : 'pointer' } }, this.state.wk_busy ? 'Filing…' : 'Create account & send to Scheduler'));
  }
  // outlet: this outlet's quotes, with follow-up flags + record-decision controls
  outletQuoteBoard() {
    const qlist = this.state.quotesList || [];
    const now = Date.now();
    const followUp = q => q.status === 'reviewed' && q.viewedAt && (now - Date.parse(q.viewedAt) > 24 * 3600e3);
    const STAT = { requested: ['Awaiting Scheduler', 'warn'], issued: ['Sent — awaiting customer', 'teal'], reviewed: ['Reviewed by customer', 'amber'], amendment: ['Amendment → Scheduler', 'warn'], declined: ['Declined', 'neutral'], accepted: ['Converted to order', 'ok'] };
    const inp = { font: '400 13px Montserrat,sans-serif', padding: '8px 10px', border: '1px solid ' + HAIR, borderRadius: 7 };
    return h('div', { key: 'oqb', style: { marginTop: 26 } },
      h('div', { style: { fontSize: 17, fontWeight: 600, marginBottom: 6 } }, 'Walk-in quotes', qlist.filter(followUp).length ? h('span', { style: { marginLeft: 8, background: '#d99100', color: '#fff', fontSize: 12, fontWeight: 700, borderRadius: 999, padding: '1px 9px' } }, qlist.filter(followUp).length + ' follow-up') : null),
      h('p', { style: { margin: '0 0 14px', fontSize: 13.5, color: MUT, lineHeight: 1.7, maxWidth: '82ch' } }, 'Quotes you filed for walk-in customers. Once the customer has reviewed a quote and taken no action for a day, follow up and record their decision — proceed converts it to an order; amendment sends it back to the Scheduler.'),
      qlist.length === 0 ? h('div', { style: { border: '1px dashed ' + HAIR, borderRadius: 12, padding: 24, textAlign: 'center', color: FAINT, fontSize: 13 } }, 'No walk-in quotes yet.') :
      h('div', { style: { display: 'flex', flexDirection: 'column', gap: 12 } }, qlist.map(q => {
        const st = STAT[q.status] || [q.status, 'neutral']; const fu = followUp(q); const dec = this.state['dec_' + q.id];
        return h('div', { key: q.id, style: { border: '1px solid ' + (fu ? '#d99100' : HAIR), borderRadius: 12, padding: 14, background: '#fff' } },
          h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'baseline', flexWrap: 'wrap', marginBottom: 6 } },
            h('div', null, h('span', { style: { font: '600 12px ui-monospace,Menlo,monospace', color: TEAL, marginRight: 8 } }, q.id), h('span', { style: { fontSize: 14, fontWeight: 600 } }, (q.requirement && q.requirement.product) || 'Custom job'), h('span', { style: { fontSize: 12.5, color: MUT } }, ' · ' + ((q.customer && q.customer.name) || 'Customer'))),
            h('span', { style: { display: 'flex', gap: 6, alignItems: 'center' } }, fu ? this.chip('Follow up due', 'warn') : null, this.chip(st[0], st[1]))),
          h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.6, marginBottom: 8 } }, [q.requirement && q.requirement.qty && 'Qty ' + q.requirement.qty, q.price != null ? 'Quoted ' + this.rm(q.price) : null, q.leadDays ? q.leadDays + ' days' : null].filter(Boolean).join(' · ') + (q.orderId ? ' · order ' + q.orderId : '') + (q.remarks ? ' · remark: ' + q.remarks : '')),
          (q.status === 'issued' || q.status === 'reviewed') ? (dec ? h('div', { style: { display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', borderTop: '1px solid ' + LINE, paddingTop: 10 } },
              h('span', { style: { fontSize: 12.5, color: MUT } }, 'Record decision:'),
              h('span', { onClick: () => this.quoteDecision(q.id, 'proceed'), style: { background: TEAL, color: '#fff', fontWeight: 600, fontSize: 12.5, padding: '7px 12px', borderRadius: 7, cursor: 'pointer' } }, 'Proceed → order'),
              h('input', { placeholder: 'Amendment / notes', value: this.state['decnote_' + q.id] || '', onChange: e => this.setField('decnote_' + q.id, e.target.value), style: Object.assign({}, inp, { flex: 1, minWidth: 140 }) }),
              h('span', { onClick: () => this.quoteDecision(q.id, 'amend', this.state['decnote_' + q.id]), style: { border: '1px solid #d99100', color: '#a1660a', fontWeight: 600, fontSize: 12.5, padding: '7px 12px', borderRadius: 7, cursor: 'pointer' } }, 'Amend → Scheduler'),
              h('span', { onClick: () => this.quoteDecision(q.id, 'not_proceed', this.state['decnote_' + q.id]), style: { border: '1px solid ' + HAIR, color: MUT, fontWeight: 600, fontSize: 12.5, padding: '7px 12px', borderRadius: 7, cursor: 'pointer' } }, 'Not proceeding'),
              h('span', { onClick: () => this.setState({ ['dec_' + q.id]: null }), style: { color: FAINT, fontSize: 16, cursor: 'pointer', marginLeft: 'auto' } }, '×'))
            : h('div', { style: { display: 'flex', gap: 10, alignItems: 'center' } },
              h('span', { onClick: () => this.setState({ ['dec_' + q.id]: 1 }), style: { background: fu ? '#d99100' : '#fff', color: fu ? '#fff' : TEAL, border: '1px solid ' + (fu ? '#d99100' : HAIR), fontWeight: 600, fontSize: 12.5, padding: '8px 14px', borderRadius: 8, cursor: 'pointer' } }, fu ? 'Follow up now' : 'Record customer decision'),
              h('span', { onClick: () => this.openDoc(q.id, 'quote'), style: { fontSize: 12.5, fontWeight: 600, color: TEAL, cursor: 'pointer' } }, 'View quote PDF')))
            : h('div', { style: { fontSize: 12.5, color: MUT } }, q.status === 'accepted' ? '✅ Converted to order ' + q.orderId : q.status === 'amendment' ? 'Sent back to Scheduler for re-pricing.' : q.status === 'declined' ? 'Customer declined.' : 'Awaiting the Scheduler to price this.'));
      })));
  }

  dialog(title, rows, note) {
    return h('div', { key: 'dlg', 'data-go': '_closeDialog', style: { position: 'fixed', inset: 0, zIndex: 80, background: 'rgba(15,42,53,.42)', display: 'grid', placeItems: 'center', padding: 20 } },
      h('div', { style: { background: '#fff', borderRadius: 14, maxWidth: 520, width: '100%', boxShadow: '0 24px 60px rgba(33,33,33,.30)', overflow: 'hidden' } },
        h('div', { style: { padding: '18px 20px', borderBottom: '1px solid ' + HAIR, display: 'flex', alignItems: 'center', gap: 10 } },
          h('span', { style: { fontSize: 15, fontWeight: 600 } }, title),
          h('span', { style: { marginLeft: 'auto', color: FAINT, fontSize: 18 } }, '×')),
        h('div', { style: { padding: '8px 12px 12px' } },
          rows.map((r, i) => h('div', { key: i, style: { padding: '11px 10px', borderRadius: 8, display: 'flex', flexDirection: 'column', gap: 3 } },
            h('span', { style: { fontSize: 13.5, fontWeight: 500 } }, r[0]),
            h('span', { style: { fontSize: 12, color: MUT } }, r[1])))),
        note && h('div', { style: { padding: '12px 20px 18px', fontSize: 11.5, color: FAINT, borderTop: '1px solid ' + LINE } }, note)));
  }

  // ===== PREPRESS QUEUE =====
  s_prepress() {
    const u = this.state.user || {};
    const jobs = this.opsJobs(), q = jobs.filter(j => j.queue === 'prepress');
    const blocked = q.filter(j => (j.actions || []).some(a => a.action === 'approve' && !a.enabled)).length;
    const identity = { title: 'Prepress', sub: u.name || 'Station' };
    const tabs = ['Dashboard', 'Queue'];
    const tab = tabs.indexOf(this.state.sTab) >= 0 ? this.state.sTab : 'Dashboard';
    const cards = [
      ['In queue', q.length, 'layers', 'teal', 'live from the state machine', null, false],
      ['Blocked · artwork ≠ order', blocked, 'file', blocked ? 'red' : 'teal', 'need authorization', null, blocked > 0],
      ['Online', q.filter(j => j.channel === 'online').length, 'check', 'orange', 'web orders in for check'],
      ['Approved today', jobs.filter(j => ['scheduling', 'printing', 'outsourcing', 'logistics', 'dispatched', 'completed'].indexOf(j.status) >= 0).length, 'check', 'teal', 'released to Scheduler'],
    ];
    const content = tab === 'Dashboard' ? this.opsDashTab(cards, 'Files checked') : this.opsQueueTab('prepress', 'action');
    return this.staffPage(tabs, tab, identity, content);
  }

  // ===== SCHEDULER QUEUE =====
  s_production() {
    const u = this.state.user || {};
    const jobs = this.opsJobs(), q = jobs.filter(j => j.queue === 'scheduler');
    const reqs = (this.state.quotesList || []).filter(qz => qz.status === 'requested' || qz.status === 'amendment').length;
    const identity = { title: 'Scheduler', sub: u.name || 'Station' };
    const tabs = ['Dashboard', 'Queue', 'Outsourcing', 'Quote requests'];
    const tab = tabs.indexOf(this.state.sTab) >= 0 ? this.state.sTab : 'Dashboard';
    const cards = [
      ['In scheduler queue', q.length, 'layers', 'teal', 'awaiting allocation'],
      ['Printing (in-house)', jobs.filter(j => j.status === 'printing').length, 'clock', 'orange', 'on machines now'],
      ['Outsourced', jobs.filter(j => j.status === 'outsourcing').length, 'truck', 'red', 'awarded to printers'],
      ['Quote requests', reqs, 'edit-3', 'teal', 'walk-ins to price', reqs ? 'New' : null, reqs > 0],
    ];
    const content = tab === 'Dashboard' ? this.opsDashTab(cards, 'Jobs allocated')
      : tab === 'Queue' ? this.opsQueueTab('scheduler', null)
      : tab === 'Outsourcing' ? [this.schedulerOutsourcePanel(jobs)]
      : [this.schedulerQuotePanel()];
    return this.staffPage(tabs, tab, identity, content);
  }
  // Scheduler prices the walk-in quote requests that outlets file, and re-prices amendments
  schedulerQuotePanel() {
    const qlist = (this.state.quotesList || []).filter(q => q.status === 'requested' || q.status === 'amendment');
    const qinp = { font: '400 13px Montserrat,sans-serif', padding: '8px 10px', border: '1px solid ' + HAIR, borderRadius: 7, width: '100%' };
    return h('div', { key: 'sq', style: { marginTop: 26 } },
      h('div', { style: { fontSize: 17, fontWeight: 600, marginBottom: 6 } }, 'Walk-in quote requests', qlist.length ? h('span', { style: { marginLeft: 8, background: TEAL, color: '#fff', fontSize: 12, fontWeight: 700, borderRadius: 999, padding: '1px 9px' } }, qlist.length) : null),
      h('p', { style: { margin: '0 0 14px', fontSize: 13.5, color: MUT, lineHeight: 1.7, maxWidth: '82ch' } }, 'Requests filed by outlets on behalf of walk-in customers. Price each one and issue it — the quote is sent straight to the customer’s account, and the originating outlet is notified. Amendment requests reappear here for re-pricing.'),
      qlist.length === 0 ? h('div', { style: { border: '1px dashed ' + HAIR, borderRadius: 12, padding: 24, textAlign: 'center', color: FAINT, fontSize: 13 } }, 'No quote requests waiting.') :
      h('div', { style: { display: 'flex', flexDirection: 'column', gap: 12 } }, qlist.map(q => h('div', { key: q.id, style: { border: '1px solid ' + (q.status === 'amendment' ? '#d99100' : HAIR), borderRadius: 12, padding: 14, background: '#fff' } },
        h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'baseline', flexWrap: 'wrap', marginBottom: 6 } },
          h('div', null, h('span', { style: { font: '600 12px ui-monospace,Menlo,monospace', color: TEAL, marginRight: 8 } }, q.id), h('span', { style: { fontSize: 14, fontWeight: 600 } }, (q.requirement && q.requirement.product) || 'Custom job'), h('span', { style: { fontSize: 12.5, color: MUT } }, ' · ' + ((q.customer && q.customer.name) || 'Customer') + (q.outlet ? ' · ' + q.outlet : ''))),
          this.chip(q.status === 'amendment' ? 'Amendment' : 'New request', q.status === 'amendment' ? 'warn' : 'teal')),
        h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.6, marginBottom: 8 } }, [q.requirement && q.requirement.qty && 'Qty ' + q.requirement.qty, q.requirement && q.requirement.size, q.requirement && q.requirement.material, q.requirement && q.requirement.finishing].filter(Boolean).join(' · ') + ((q.requirement && q.requirement.remarks) ? ' — ' + q.requirement.remarks : '') + (q.remarks ? ' · outlet remark: ' + q.remarks : '')),
        h('div', { style: { display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' } },
          h('input', { type: 'number', placeholder: 'Price (RM)', value: this.state['qp_' + q.id + '_price'] || '', onChange: e => this.setField('qp_' + q.id + '_price', e.target.value), style: Object.assign({}, qinp, { maxWidth: 130 }) }),
          h('input', { type: 'number', placeholder: 'Lead days', value: this.state['qp_' + q.id + '_lead'] || '', onChange: e => this.setField('qp_' + q.id + '_lead', e.target.value), style: Object.assign({}, qinp, { maxWidth: 110 }) }),
          h('input', { placeholder: 'Note (optional)', value: this.state['qp_' + q.id + '_note'] || '', onChange: e => this.setField('qp_' + q.id + '_note', e.target.value), style: Object.assign({}, qinp, { flex: 1, minWidth: 140 }) }),
          h('span', { onClick: () => this.quotePrice(q.id), style: { background: TEAL, color: '#fff', fontWeight: 600, fontSize: 13, padding: '9px 16px', borderRadius: 8, cursor: 'pointer' } }, q.status === 'amendment' ? 'Re-issue' : 'Issue & send to customer'))))));
  }
  // Scheduler's outsourcing workflow: request quotes → compare → award a PO to the best vendor
  schedulerOutsourcePanel(jobs) {
    const relevant = jobs.filter(j => j.queue === 'scheduler' || j.outsource);
    const vendors = this.state.vendors || [];
    return h('div', { key: 'out', style: { marginTop: 26 } },
      h('div', { style: { fontSize: 17, fontWeight: 600, marginBottom: 6 } }, 'Outsourcing — request quotes & award a PO'),
      h('p', { style: { margin: '0 0 14px', fontSize: 13.5, color: MUT, lineHeight: 1.7, maxWidth: '82ch' } }, 'Send a job to vendors, compare their price and lead time, and award a Purchase Order to the best (never by relationship — by cost, time and logistics). The winning vendor prints a shipping label to deliver to the outlet or customer.'),
      relevant.length === 0 ? h('div', { style: { border: '1px dashed ' + HAIR, borderRadius: 12, padding: 28, textAlign: 'center', color: FAINT, fontSize: 13 } }, 'No jobs available to outsource right now.') :
      h('div', { style: { display: 'flex', flexDirection: 'column', gap: 12 } }, relevant.map(j => {
        const o = j.outsource;
        const best = o && o.vendors.filter(v => v.submittedAt).sort((a, b) => a.price - b.price)[0];
        return h('div', { key: j.id, style: { border: '1px solid ' + HAIR, borderRadius: 12, padding: 16, background: '#fff' } },
          h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'baseline', flexWrap: 'wrap', marginBottom: 8 } },
            h('div', null, h('span', { style: { font: '600 12px ui-monospace,Menlo,monospace', color: TEAL, marginRight: 8 } }, j.id), h('span', { style: { fontSize: 14, fontWeight: 600 } }, j.product), h('span', { style: { fontSize: 12.5, color: MUT } }, ' · qty ' + (j.qty || 0).toLocaleString() + ' · for ' + j.customer)),
            o ? this.chip(o.awardedTo ? 'Awarded' : (o.status === 'quotes_received' ? 'Quotes received' : o.status === 'partly_received' ? 'Partly received' : 'Requested'), o.awardedTo ? 'ok' : 'warn') : this.chip('In-house or outsource', 'neutral')),
          !o ? h('span', { onClick: () => this.opsRequestQuotes(j.id, vendors.map(v => v.id)), style: { display: 'inline-block', background: TEAL, color: '#fff', fontWeight: 600, fontSize: 13, padding: '9px 16px', borderRadius: 8, cursor: 'pointer' } }, 'Request vendor quotes' + (vendors.length ? ' (' + vendors.length + ')' : ''))
          : o.awardedTo ? h('div', { style: { fontSize: 13, color: INK } }, 'Awarded to ', h('b', null, (o.vendors.find(v => v.vendorId === o.awardedTo) || {}).vendorName), ' · PO ', h('b', null, o.po), ' · vendor is printing the shipping label.')
          : h('div', { style: { border: '1px solid ' + LINE, borderRadius: 8, overflow: 'hidden' } },
              h('div', { style: { display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr 90px', gap: 8, padding: '8px 12px', background: ALT, fontSize: 11, fontWeight: 600, letterSpacing: '.05em', textTransform: 'uppercase', color: FAINT } }, h('span', null, 'Vendor'), h('span', null, 'Price'), h('span', null, 'Lead time'), h('span', null, '')),
              o.vendors.map(v => h('div', { key: v.vendorId, style: { display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr 90px', gap: 8, padding: '9px 12px', borderTop: '1px solid ' + LINE, alignItems: 'center', background: best && v.vendorId === best.vendorId ? '#f2fbf4' : '#fff' } },
                h('span', { style: { fontSize: 13, fontWeight: 500 } }, v.vendorName, best && v.vendorId === best.vendorId ? h('span', { style: { fontSize: 10.5, color: '#63AA02', fontWeight: 700, marginLeft: 6 } }, 'BEST') : null),
                h('span', { style: { fontSize: 13 } }, v.submittedAt ? this.money(v.price) : h('span', { style: { color: FAINT } }, 'awaiting…')),
                h('span', { style: { fontSize: 13, color: MUT } }, v.submittedAt ? v.leadDays + ' days' : '—'),
                v.submittedAt ? h('span', { onClick: () => this.opsAward(j.id, v.vendorId), style: { fontSize: 12, fontWeight: 600, color: '#fff', background: TEAL, borderRadius: 7, padding: '6px 0', textAlign: 'center', cursor: 'pointer' } }, 'Award') : h('span', null)))));
      })));
  }

  // ===== LOGISTICS =====
  s_logistics() {
    const u = this.state.user || {};
    const jobs = this.opsJobs(), q = jobs.filter(j => j.queue === 'logistics');
    const identity = { title: 'Logistics', sub: u.name || 'Station' };
    const tabs = ['Dashboard', 'Queue'];
    const tab = tabs.indexOf(this.state.sTab) >= 0 ? this.state.sTab : 'Dashboard';
    const cards = [
      ['Ready / in transit', q.length, 'box', 'teal', 'pack, label, dispatch'],
      ['Dispatched', jobs.filter(j => j.status === 'dispatched').length, 'truck', 'orange', 'awaiting delivery'],
      ['Completed', jobs.filter(j => j.status === 'completed').length, 'check', 'teal', 'delivered / picked up'],
      ['Outsourced inbound', jobs.filter(j => j.status === 'outsourcing').length, 'layers', 'red', 'from vendors / hub'],
    ];
    const content = tab === 'Dashboard' ? this.opsDashTab(cards, 'Parcels dispatched') : this.opsQueueTab('logistics', null);
    return this.staffPage(tabs, tab, identity, content);
  }

  // ===== PRODUCTION DIRECTOR (cross-department, live) =====
  s_director() {
    const jobs = this.opsJobs();
    const n = qn => jobs.filter(j => j.queue === qn).length;
    const nav = [['Rollup'], ['Prepress', String(n('prepress'))], ['Scheduler', String(n('scheduler'))], ['Logistics', String(n('logistics'))], ['Done', String(n('done'))]];
    const tiles = [['Intake', 'outlet', 'outlet'], ['Prepress', 'prepress', 'prepress'], ['Scheduler', 'scheduler', 'production'], ['Logistics', 'logistics', 'logistics'], ['Done', 'done', null]];
    const kpis = h('div', { key: 'k', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(150px,1fr))', gap: 14, marginBottom: 4 } },
      tiles.map(d => h('div', { key: d[1], 'data-go': d[2] || undefined, style: { border: '1px solid ' + HAIR, borderRadius: 12, padding: 16, background: '#fff', cursor: d[2] ? 'pointer' : 'default' } },
        h('div', { style: { fontSize: 11.5, fontWeight: 600, letterSpacing: '.06em', textTransform: 'uppercase', color: FAINT } }, d[0]),
        h('div', { style: { fontSize: 30, fontWeight: 600, letterSpacing: '-.02em', margin: '6px 0 2px', color: INK } }, String(n(d[1]))),
        h('div', { style: { fontSize: 12.5, color: MUT } }, 'jobs'))));
    return this.opsBoard('Production Director · Ms. Tan', nav, 'Rollup', null,
      'Cross-department rollup',
      'The one role that sees and can act on every job in every department. Counts are live from the shared state machine; with director authority you can transition any job in any queue — each override is audit-logged. This is the single source every department reads from.',
      { kpis: kpis, showAll: true });
  }

  // ===== CHAT & INQUIRY CRM =====
  s_crm() {
    const chan = this.state.chan || 'all';
    const CHANNELS = [['all', 'All', 18], ['web', 'Web chat', 7], ['wa', 'WhatsApp', 6], ['email', 'Email', 3], ['form', 'Contact form', 2]];
    const THREADS = [
      ['Aiman Lim', 'Studio North', 'Web chat', 'Can you check if my bleed is right before I pay?', '2 m', 'Open', 'bad', true],
      ['Nurul Izzah', 'Borneo Dental', 'WhatsApp', 'Is the quote QT-8846 still valid this week?', '14 m', 'Open', 'warn', false],
      ['Kelvin Tan', 'Kopitiam 88', 'WhatsApp', 'Order PO-2026-04288 — can I change the delivery address?', '1 h', 'Pending', 'warn', false],
      ['Sharifah A.', 'Rimba Resort', 'Email', 'Requesting a proforma invoice for finance approval.', '3 h', 'Pending', 'neutral', false],
      ['Wong Li Ping', 'Astra Tuition', 'Contact form', 'Do you deliver to Brunei and how long does it take?', '5 h', 'Resolved', 'ok', false],
    ];
    const MSGS = [
      ['in', 'Aiman Lim', '14:02', 'Hi — I uploaded my business card artwork but it says one check failed. Can someone look before I pay?'],
      ['out', 'Suraya · CS', '14:04', 'Hi Aiman, I can see job J-04417-1. The background stops 1.2 mm short of the bleed on the right edge — everything else passes.'],
      ['note', 'Internal note · Suraya', '14:05', 'Customer is Gold tier, second job this month. If they can’t fix it, prepress said they can extend the background themselves — 10 min job.'],
      ['in', 'Aiman Lim', '14:09', 'Can you extend it for me? I don’t have the source file with me today.'],
    ];
    const MACROS = ['Bleed explainer + guide link', 'Quote validity', 'Delivery times MY/SG/BN', 'Artwork resubmission steps', 'Refund to credit balance'];
    const list = chan === 'all' ? THREADS : THREADS.filter(t => (chan === 'web' && t[2] === 'Web chat') || (chan === 'wa' && t[2] === 'WhatsApp') || (chan === 'email' && t[2] === 'Email') || (chan === 'form' && t[2] === 'Contact form'));
    return h('div', { style: { maxWidth: 1180, margin: '0 auto', padding: '10px 20px 0' } },
      this.head('Chat & Inquiry CRM', 'One inbox across web chat, WhatsApp, email and the contact form. Every conversation can be attached to an Order or Quote, so the agent reads live history instead of asking the customer to repeat it.'),
      h('div', { style: { display: 'grid', gridTemplateColumns: 'minmax(0,1fr)', gap: 16, marginTop: 18 } },
        h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 16, alignItems: 'start' } },
          h('div', { style: { border: '1px solid ' + HAIR, background: '#fff' } },
            h('div', { style: { display: 'flex', gap: 6, flexWrap: 'wrap', padding: 10, borderBottom: '1px solid ' + HAIR } },
              CHANNELS.map(c => h('span', { key: c[0], 'data-go': 'set:chan:' + c[0], style: { display: 'flex', gap: 6, alignItems: 'center', fontSize: 12, fontWeight: 600, padding: '6px 10px', borderRadius: 2, cursor: 'pointer', background: chan === c[0] ? TEAL : ALT, color: chan === c[0] ? '#fff' : MUT } }, c[1],
                h('span', { style: { fontSize: 11 } }, c[2])))),
            list.map((t, i) => h('div', { key: i, style: { padding: '13px 14px', borderTop: i ? '1px solid ' + LINE : 'none', background: t[7] ? '#fdf6f6' : '#fff', borderLeft: '3px solid ' + (t[7] ? TEAL : 'transparent'), cursor: 'pointer' } },
              h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'baseline' } },
                h('span', { style: { fontSize: 13.5, fontWeight: 600 } }, t[0]),
                h('span', { style: { fontSize: 11.5, color: FAINT } }, t[4])),
              h('div', { style: { fontSize: 11.5, color: FAINT, margin: '2px 0 5px' } }, t[1] + ' · ' + t[2]),
              h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.5, overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' } }, t[3]),
              h('div', { style: { marginTop: 7 } }, this.chip(t[5], t[6]))))),
          h('div', { style: { border: '1px solid ' + HAIR, background: '#fff', display: 'flex', flexDirection: 'column' } },
            h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center', padding: '12px 14px', borderBottom: '1px solid ' + HAIR } },
              h('span', { style: { fontSize: 14, fontWeight: 600, marginRight: 'auto' } }, 'Aiman Lim · Web chat'),
              this.chip('SLA 3 m left', 'warn'), this.chip('Open', 'bad')),
            h('div', { style: { padding: 14, display: 'flex', flexDirection: 'column', gap: 12, background: ALT } },
              MSGS.map((m, i) => h('div', { key: i, style: { alignSelf: m[0] === 'in' ? 'flex-start' : m[0] === 'out' ? 'flex-end' : 'stretch', maxWidth: m[0] === 'note' ? '100%' : '86%', background: m[0] === 'note' ? '#fff8e6' : m[0] === 'out' ? TEAL : '#fff', color: m[0] === 'out' ? '#fff' : INK, border: '1px solid ' + (m[0] === 'note' ? '#f0dfae' : m[0] === 'out' ? TEAL : HAIR), borderRadius: 6, padding: '10px 13px' } },
                h('div', { style: { fontSize: 11, fontWeight: 600, marginBottom: 4, color: m[0] === 'out' ? 'rgba(255,255,255,.9)' : FAINT } }, m[1] + ' · ' + m[2]),
                h('div', { style: { fontSize: 13, lineHeight: 1.6 } }, m[3])))),
            h('div', { style: { padding: 12, borderTop: '1px solid ' + HAIR, display: 'flex', flexDirection: 'column', gap: 10 } },
              h('div', { style: { display: 'flex', gap: 7, flexWrap: 'wrap' } },
                MACROS.map((m, i) => h('span', { key: i, style: { fontSize: 11.5, fontWeight: 600, border: '1px solid ' + HAIR, borderRadius: 999, padding: '5px 11px', color: MUT, cursor: 'pointer' } }, m))),
              h('div', { style: { border: '1px solid ' + HAIR, borderRadius: 2, padding: '11px 13px', fontSize: 13, color: FAINT, minHeight: 62 } }, 'Reply to Aiman — or switch to an internal note that the customer never sees'),
              h('div', { style: { display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' } },
                this.btn('Send reply', 'teal', 'crm', { borderRadius: 2 }),
                this.btn('Add internal note', 'ghost', 'crm', { borderRadius: 2 }),
                h('span', { style: { fontSize: 12, color: FAINT, marginLeft: 'auto' } }, 'Resolve · Reopen · Schedule follow-up')))),
          h('div', { style: { border: '1px solid ' + HAIR, background: '#fff', padding: 16, display: 'flex', flexDirection: 'column', gap: 14 } },
            h('div', { style: { fontSize: 13.5, fontWeight: 600 } }, 'Customer'),
            h('div', { style: { fontSize: 13, color: MUT, lineHeight: 1.8 } },
              h('div', { style: { fontSize: 15, fontWeight: 600, color: INK } }, 'Aiman Lim'),
              'Studio North Sdn Bhd', h('br'), 'aiman@studionorth.my', h('br'), '+6012 345 6789'),
            h('div', { style: { display: 'flex', gap: 8, flexWrap: 'wrap' } }, this.chip('Gold tier', 'amber'), this.chip('Credit ' + this.money(96), 'ok'), this.chip('MY', 'neutral')),
            h('div', null,
              h('div', { style: { fontSize: 12, fontWeight: 600, letterSpacing: '.06em', textTransform: 'uppercase', color: FAINT, marginBottom: 8 } }, 'Linked to this conversation'),
              h('div', { style: { border: '1px solid ' + HAIR, borderRadius: 2, padding: 12, fontSize: 12.5 } },
                h('div', { style: { fontWeight: 600 } }, 'Order PO-2026-04417'),
                h('div', { style: { color: MUT, marginTop: 3 } }, 'Job J-04417-1 · artwork issues found'),
                h('span', { 'data-go': 'track', style: { display: 'inline-block', marginTop: 8, fontSize: 12, fontWeight: 600, color: TEAL, cursor: 'pointer' } }, 'Open order'))),
            h('div', null,
              h('div', { style: { fontSize: 12, fontWeight: 600, letterSpacing: '.06em', textTransform: 'uppercase', color: FAINT, marginBottom: 8 } }, 'Recent history'),
              [['PO-2026-04288', '28 Aug · ' + this.money(1204) + ' · delivered'], ['QT-8830', '21 Aug · accepted · ' + this.money(4620)], ['PO-2026-04102', '09 Aug · ' + this.money(318.72) + ' · delivered']].map((r, i) =>
                h('div', { key: i, style: { display: 'flex', justifyContent: 'space-between', gap: 10, padding: '7px 0', borderTop: i ? '1px solid ' + LINE : 'none', fontSize: 12.5 } },
                  h('span', { style: { fontWeight: 600 } }, r[0]), h('span', { style: { color: MUT, textAlign: 'right' } }, r[1])))),
            h('div', { style: { border: '1px solid ' + HAIR, background: ALT, padding: 12, fontSize: 12, color: MUT, lineHeight: 1.7 } },
              h('b', { style: { color: INK } }, 'WhatsApp Business: '),
              'outbound template messages need Meta approval before use; order-status broadcasts run from the approved template list only.')))));
  }

  // ===== ADMIN BACKOFFICE =====
  s_admin() {
    const tab = this.state.atab || 'analytics';
    const nOrders = (this.state.admOrders || []).length, nPosts = (this.state.blog || []).length;
    const nOutsource = (this.state.admJobs || []).filter(j => j.outsource).length;
    // menu mirrors the WordPress admin — grouped Store / Content / Settings
    const nav = [
      ['Store', null, '__group'],
      ['Analytics', null, 'analytics'], ['Orders', nOrders ? String(nOrders) : null, 'orders'], ['Customers', null, 'customers'],
      ['Products', null, 'catalogue'], ['Coupons', null, 'vouchers'], ['Artworks', null, 'artworks'],
      ['Custom Quote', null, 'quotes'], ['Custom Invoice', null, 'custinvoice'], ['Printing Job', nOutsource ? String(nOutsource) : null, 'printing'], ['Users & roles', null, 'users'],
      ['Content', null, '__group'],
      ['Posts (Blog)', nPosts ? String(nPosts) : null, 'posts'], ['Pages', null, 'pages'], ['Media', null, 'media'], ['Downloads', null, 'downloads'], ['FAQs', null, 'faqs'], ['SEO · Rank Math', null, 'seo'],
      ['Settings', null, '__group'],
      ['Pricing & margin', null, 'pricing'], ['Membership', null, 'membership'], ['TeraWallet · Credit', null, 'wallet'],
      ['Payments', null, 'gateways'], ['Tax & invoicing', null, 'tax'], ['Couriers & vendors', null, 'couriers'], ['Outlets', null, 'outlets'],
      ['Follow-up emails', null, 'followup'], ['Scheduled emails', null, 'scheduled'], ['Mailing lists', null, 'mailing'],
      ['Notifications', null, 'notify'],
      ['Printoka settings', null, 'settings'], ['Theme settings', null, 'theme'], ['Store settings', null, 'storeset'], ['Audit log', null, 'audit'],
    ];
    const navItems = nav.map(n => [n[0], n[1], n[2] === '__group' ? '__group' : 'set:atab:' + n[2]]);
    const activeLabel = (nav.find(n => n[2] === tab) || nav[1])[0];
    const P = {};

    P.analytics = [
      h('div', { key: 'k', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 14 } },
        this.kpi('Revenue · 30 days', this.money(486240), '+18% vs previous', TEAL),
        this.kpi('Orders', '1,284', '412 outlet · 872 online'),
        this.kpi('Conversion', '3.8%', 'Sessions to paid order'),
        this.kpi('Avg. order value', this.money(378), '+' + this.money(22) + ' vs previous')),
      h('div', { key: 'g', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 16, marginTop: 16 } },
        this.card([
          h('div', { key: 't', style: { fontSize: 13.5, fontWeight: 600, marginBottom: 12 } }, 'Membership tier distribution'),
          [['Standard', 62], ['Bronze', 19], ['Silver', 11], ['Gold', 6], ['Platinum', 2]].map((r, i) =>
            h('div', { key: i, style: { display: 'flex', alignItems: 'center', gap: 10, padding: '5px 0' } },
              h('span', { style: { width: 68, fontSize: 12.5, color: MUT } }, r[0]),
              h('span', { style: { flex: 1, height: 8, background: LINE, borderRadius: 999, overflow: 'hidden' } },
                h('span', { style: { display: 'block', height: '100%', width: r[1] + '%', background: TEAL } })),
              h('span', { style: { width: 34, textAlign: 'right', fontSize: 12, fontWeight: 600 } }, r[1] + '%'))),
        ]),
        this.card([
          h('div', { key: 't', style: { fontSize: 13.5, fontWeight: 600, marginBottom: 12 } }, 'Top products · 30 days'),
          [['Business Card', this.money(96400)], ['Flyer', this.money(72180)], ['Booklet — Litho', this.money(61020)], ['Label Sticker', this.money(44900)], ['Folding Carton', this.money(38650)]].map((r, i) =>
            h('div', { key: i, style: { display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderTop: i ? '1px solid ' + LINE : 'none', fontSize: 13 } },
              h('span', null, r[0]), h('span', { style: { fontWeight: 600 } }, r[1]))),
        ])),
      h('div', { key: 'o', style: { marginTop: 16 } },
        this.table(['Outlet', 'Quotes', 'Conversion', 'Revenue', 'Throughput'],
          [['KL Damansara', '68', '58%', this.money(50440), '112 jobs'], ['Miri (own facility)', '41', '64%', this.money(38120), '208 jobs'], ['Johor Bahru', '35', '49%', this.money(21760), '74 jobs']],
          ['30%', '15%', '17%', '20%', '18%'])),
    ];

    const admQ = (this.state.admQ || '').toLowerCase();
    const clist = this.pkProducts()
      .filter(p => !admQ || this.catName(p.id).toLowerCase().indexOf(admQ) >= 0 || p.name.toLowerCase().indexOf(admQ) >= 0)
      .sort((a, b) => this.catName(a.id).localeCompare(this.catName(b.id)));
    const inp = { font: '400 13px Montserrat,sans-serif', padding: '7px 9px', border: '1px solid ' + HAIR, borderRadius: 6, background: '#fff', width: '100%' };
    P.catalogue = [
      h('p', { key: 'i', style: { fontSize: 13, color: MUT, lineHeight: 1.6, margin: '0 0 12px', maxWidth: '80ch' } },
        'Rename any product for the storefront and assign it a category. Names here are ', h('b', { style: { color: INK } }, 'display-only'), ' — the pricing calculator still resolves by the underlying product, so “Offset Printing Booklets” prices exactly as “Booklet — Litho”. Changes save instantly and show across the site.'),
      h('input', { key: 'q', placeholder: 'Search ' + this.pkProducts().length + ' products…', value: this.state.admQ || '',
        onChange: e => this.setState({ admQ: e.target.value }), style: Object.assign({}, inp, { maxWidth: 320, marginBottom: 14 }) }),
      h('div', { key: 'tbl', style: { border: '1px solid ' + HAIR, borderRadius: 12, overflow: 'hidden' } },
        h('div', { style: { display: 'grid', gridTemplateColumns: '1.3fr 1.3fr 1fr 70px', gap: 12, padding: '10px 14px', background: ALT, fontSize: 11, fontWeight: 600, letterSpacing: '.06em', textTransform: 'uppercase', color: FAINT } },
          h('span', null, 'Calculator product'), h('span', null, 'Display name (website)'), h('span', null, 'Category'), h('span', { style: { textAlign: 'center' } }, 'Hidden')),
        clist.map((p, i) => {
          const o = this.catOverride(p.id);
          return h('div', { key: p.id, style: { display: 'grid', gridTemplateColumns: '1.3fr 1.3fr 1fr 70px', gap: 12, padding: '9px 14px', borderTop: '1px solid ' + LINE, alignItems: 'center' } },
            h('span', { style: { fontSize: 12, color: MUT } }, p.name, h('span', { style: { color: '#c9ced3', marginLeft: 6 } }, '#' + p.id)),
            h('input', { value: o.displayName || p.name, onChange: e => this.catSave(p.id, { displayName: e.target.value }), style: Object.assign({}, inp, { fontWeight: 600, color: INK }) }),
            h('select', { value: this.catCategoryOf(p.id), onChange: e => this.catSave(p.id, { categoryId: e.target.value }), style: inp },
              this.catCategories().map(c => h('option', { key: c.id, value: c.id }, c.label))),
            h('span', { style: { textAlign: 'center' } },
              h('input', { type: 'checkbox', checked: !!o.hidden, onChange: e => this.catSave(p.id, { hidden: e.target.checked }) })));
        })),
    ];

    P.pricing = [
      h('div', { key: 'n', style: { border: '1px solid ' + HAIR, background: ALT, padding: 16, fontSize: 12.5, color: MUT, lineHeight: 1.75, marginBottom: 16 } },
        h('b', { style: { color: INK } }, 'Crawler refresh: '), 'last run 12 Sep 04:00 · 93 products sampled · 0 discrepancies against the reference. Price changes are staged and shown as a diff before publish; every publish writes to the price history log.'),
      this.table(['SKU / option', 'Cost basis', 'Margin', 'Sell price', 'Member-eligible', 'Staged change'],
        [['BC-001 · 1,000 · 310gsm', this.money(128.6), '38%', this.money(198.4), 'Yes', this.chip('none', 'neutral')],
         ['BC-001 · 1,000 · Linen', this.money(182.4), '38%', this.money(281.2), 'Yes', this.chip('+4% margin', 'warn')],
         ['FL-014 · 5,000', this.money(306), '32%', this.money(449), 'Yes', this.chip('none', 'neutral')],
         ['PK-067 · 1,000 style', this.money(1940), '26%', this.money(2621), 'No', this.chip('vendor rate ↑', 'bad')]],
        ['26%', '15%', '10%', '14%', '15%', '20%']),
      h('div', { key: 'a', style: { display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 14 } },
        this.btn('Preview price diff', 'teal', 'admin', { borderRadius: 2 }), this.btn('Bulk margin adjust', 'ghost', 'admin', { borderRadius: 2 }), this.btn('Price history log', 'ghost', 'admin', { borderRadius: 2 })),
    ];

    P.membership = [
      h('div', { key: 'n', style: { border: '1px solid ' + TEAL, background: '#fdf6f6', padding: 16, fontSize: 12.5, color: MUT, lineHeight: 1.75, marginBottom: 16 } },
        h('b', { style: { color: INK } }, 'Confirmed new work: '), 'no tier or loyalty logic exists anywhere in the current codebase despite the tiers being publicly advertised. Confirm with the team whether tiers are tracked manually today before scoping this as a full rules engine.'),
      this.table(['Tier', 'MY threshold', 'SG threshold', 'BN threshold', 'Discount', 'Extras'],
        [['Standard', '—', '—', '—', '0%', 'Full platform access'],
         ['Bronze', this.money(1000), 'SGD 310', 'BND 310', '5%', '—'],
         ['Silver', this.money(3000), 'SGD 930', 'BND 930', '8%', 'Early campaign access'],
         ['Gold', this.money(5000), 'SGD 1,550', 'BND 1,550', '10%', 'Priority production queue'],
         ['Platinum', this.money(10000), 'SGD 3,100', 'BND 3,100', '15%', 'Key Account Manager + credit terms']],
        ['14%', '17%', '17%', '17%', '12%', '23%']),
      h('div', { key: 'r', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 14, marginTop: 16 } },
        [['Evaluation window', 'Trailing 12 months, evaluated continuously — not per order'],
         ['Inactivity downgrade', 'One tier down after 3 consecutive months with no order'],
         ['Re-upgrade', 'Automatic the moment trailing spend crosses the threshold again'],
         ['Stacking cap', 'Tier + voucher + referral credit capped at 30% of order value'],
         ['Manual override', 'Admin can pin a tier; writes actor, reason and before/after to the audit log'],
         ['Referral payout', 'RM 20 credit once the referred customer’s first order ships']]
          .map((r, i) => this.card([
            h('div', { key: 'a', style: { fontSize: 13, fontWeight: 600, marginBottom: 5 } }, r[0]),
            h('div', { key: 'b', style: { fontSize: 12.5, color: MUT, lineHeight: 1.65 } }, r[1]),
          ], { key: i }))),
    ];

    P.vouchers = [
      this.table(['Code', 'Type', 'Scope', 'Window', 'Used / limit', 'Status'],
        [['RAYA26', '15% off', 'All catalogue', '01–30 Apr 2026', '842 / 1,000', this.chip('Expired', 'neutral')],
         ['FIRST50', 'RM 50 off', 'First order only', 'Always on', '2,104 / ∞', this.chip('Active', 'ok')],
         ['CARTON10', '10% off', 'Packaging category', '01 Sep – 31 Oct', '61 / 300', this.chip('Active', 'ok')]],
        ['14%', '14%', '22%', '20%', '16%', '14%']),
      h('div', { key: 'a', style: { display: 'flex', gap: 10, marginTop: 14 } }, this.btn('New campaign', 'teal', 'admin', { borderRadius: 2 }), this.btn('Performance report', 'ghost', 'admin', { borderRadius: 2 })),
    ];

    P.outlets = [
      this.table(['Outlet', 'Country', 'Staff', 'Self-pickup discount', 'Rapid SKUs', 'Hours'],
        [['KL Damansara', 'MY', '3', '5%', 'Business card, flyer', 'Mon–Sat 09:00–19:00'],
         ['Miri (own facility)', 'MY', '11', '5%', 'All digital SKUs', 'Mon–Fri 08:30–18:00'],
         ['Johor Bahru', 'MY', '2', '5%', 'Business card', 'Mon–Sat 10:00–18:00'],
         ['Singapore CBD', 'SG', '2', '—', 'Business card', 'Mon–Fri 09:00–18:00']],
        ['26%', '10%', '10%', '20%', '20%', '14%']),
    ];

    P.users = [
      this.table(['User', 'Role', 'Scope', 'Last login', 'Status'],
        [['Suraya binti Kamal', 'Prepress', 'Prepress queue', 'Today 08:12', this.chip('Active', 'ok')],
         ['Hafiz Rahman', 'Production', 'Production queue', 'Today 07:55', this.chip('Active', 'ok')],
         ['Chin Wei Kit', 'Logistics', 'Logistics queue', 'Yesterday 17:40', this.chip('Active', 'ok')],
         ['Nadia Rahman', 'Outlet counter', 'KL Damansara', 'Today 09:05', this.chip('Active', 'ok')],
         ['Lee Chong', 'Production Director', 'All departments', 'Today 08:00', this.chip('Active', 'ok')],
         ['Vendor · Percetakan Maju', 'Outsource printer', 'Own jobs only', '10 Sep 15:22', this.chip('Active', 'ok')]],
        ['26%', '18%', '22%', '18%', '16%']),
      h('div', { key: 'n', style: { marginTop: 14, border: '1px solid ' + HAIR, background: ALT, padding: 16, fontSize: 12.5, color: MUT, lineHeight: 1.75 } },
        'Every role in the map has an explicit permission set — no screen leaks data because it was never scoped. Prepress, Production and Logistics have no cross-visibility; the Production Director is the only override-capable role.'),
    ];

    P.cms = [
      this.table(['Content', 'Type', 'EN', 'ZH', 'MS', 'SEO'],
        [['Business card artwork guide', 'Guide template', this.chip('Live', 'ok'), this.chip('Live', 'ok'), this.chip('Missing', 'bad'), 'Indexed'],
         ['Paper & finishes explainer', 'Article', this.chip('Live', 'ok'), this.chip('Draft', 'warn'), this.chip('Missing', 'bad'), 'Noindex (draft)'],
         ['Homepage hero slides', 'Banner set', this.chip('Live', 'ok'), this.chip('Live', 'ok'), this.chip('Live', 'ok'), '—'],
         ['/kuala-lumpur/business-cards', 'City landing page', this.chip('Live', 'ok'), this.chip('n/a', 'neutral'), this.chip('Live', 'ok'), 'Indexed']],
        ['30%', '16%', '12%', '12%', '12%', '18%']),
      h('div', { key: 'n', style: { marginTop: 14, border: '1px solid ' + HAIR, background: ALT, padding: 16, fontSize: 12.5, color: MUT, lineHeight: 1.75 } },
        h('b', { style: { color: INK } }, 'Templating: '), 'guides are authored once with {{product_name}}-style placeholders so one template serves the whole catalogue, and the same content renders inside the configurator’s Size & Bleed tab. Sitemap regenerates whenever the pricing engine adds or retires a product.'),
    ];

    P.templates = [
      this.table(['SKU / option', 'Trim', 'Bleed', 'Safe area', 'Die-line files', 'Used by'],
        [['BC-001 · 54 × 89 mm', '54 × 89 mm', '3 mm', '3 mm', 'AI · PDF · PSD', 'Customer checker + prepress'],
         ['BC-001 · 50 × 90 mm', '50 × 90 mm', '3 mm', '3 mm', 'AI · PDF', 'Customer checker + prepress'],
         ['FL-014', '148 × 210 mm', '3 mm', '5 mm', 'AI · PDF', 'Customer checker + prepress'],
         ['PK-067 carton', 'die-specific', '5 mm', '6 mm', 'AI die-line', 'Prepress only']],
        ['24%', '16%', '10%', '12%', '18%', '20%']),
    ];

    P.couriers = [
      this.table(['Courier / vendor', 'Type', 'Zones', 'Weight bands', 'Effective from', 'Status'],
        [['J&T Express', 'Courier', 'MY peninsular + east', '0–1, 1–3, 3–5, 5–10 kg', '01 Jul 2026', this.chip('Active', 'ok')],
         ['Ninja Van SG', 'Courier', 'Singapore', '0–2, 2–5, 5–10 kg', '01 Aug 2026', this.chip('Active', 'ok')],
         ['Percetakan Maju', 'Outsource printer', 'Litho, large format', '—', '01 Jan 2026', this.chip('Scorecard 94%', 'ok')],
         ['Hub · Shah Alam', 'Consolidation hub', 'Klang Valley intake', '—', '01 Jan 2026', this.chip('Active', 'ok')]],
        ['24%', '16%', '20%', '18%', '12%', '10%']),
    ];

    P.tax = [
      this.table(['Country', 'Tax', 'Rate', 'Invoice prefix', 'Numbering', 'Template'],
        [['Malaysia', 'SST', '8% service', 'PIN-MY-', 'Sequential per year', 'Editable'],
         ['Singapore', 'GST', '9%', 'PIN-SG-', 'Sequential per year', 'Editable'],
         ['Brunei', 'None', '—', 'PIN-BN-', 'Sequential per year', 'Editable']],
        ['20%', '14%', '14%', '18%', '20%', '14%']),
      h('div', { key: 'n', style: { marginTop: 14, border: '1px solid ' + HAIR, background: ALT, padding: 16, fontSize: 12.5, color: MUT, lineHeight: 1.75 } },
        'Confirm exact tax treatment per country with a tax advisor before go-live. The invoice is one simplified summary per order; the order slip is one per job and carries artwork filenames for the customer’s own finance and claims use.'),
    ];

    P.gateways = [
      this.table(['Gateway', 'Countries', 'Methods', 'Transaction fee', 'Status'],
        [['Stripe', 'MY · SG · BN', 'Cards, Apple/Google Pay', '2.9% + RM 1.00', this.chip('Live', 'ok')],
         ['iPay88', 'MY', 'FPX, cards, Touch ’n Go', '1.8%', this.chip('Live', 'ok')],
         ['PayNow / GrabPay', 'SG', 'QR, wallet', '1.2%', this.chip('Planned P2', 'warn')],
         ['Brunei rails', 'BN', 'TBC', 'TBC', this.chip('Not configured', 'neutral')]],
        ['20%', '20%', '28%', '18%', '14%']),
      h('div', { key: 'n', style: { marginTop: 14, border: '1px solid ' + HAIR, background: ALT, padding: 16, fontSize: 12.5, color: MUT, lineHeight: 1.75 } },
        'API keys live in a secrets vault, never in the product record. Card data is tokenised by the gateway — Printoka’s own systems never store it. Transaction fees feed the margin calculation in Pricing.'),
    ];

    P.notify = [
      this.table(['Trigger', 'Recipient', 'Channels', 'Languages', 'Status'],
        [['Order status change', 'Customer', 'Email · in-app · WhatsApp', 'EN · ZH · MS', this.chip('Live', 'ok')],
         ['Artwork rejected', 'Customer', 'Email · in-app', 'EN · ZH', this.chip('Missing MS', 'warn')],
         ['Quote about to expire', 'Customer', 'Email · in-app', 'EN · ZH · MS', this.chip('Live', 'ok')],
         ['Membership tier changed', 'Customer', 'Email · in-app', 'EN', this.chip('Missing ZH · MS', 'bad')],
         ['SLA breach', 'Director / CS lead', 'In-app', 'EN', this.chip('Live', 'ok')],
         ['New chat message', 'Assigned agent', 'In-app · browser push', 'EN', this.chip('Live', 'ok')]],
        ['26%', '18%', '26%', '16%', '14%']),
      h('div', { key: 'a', style: { display: 'flex', gap: 10, marginTop: 14 } }, this.btn('Edit template', 'ghost', 'admin', { borderRadius: 2 }), this.btn('Send test', 'teal', 'admin', { borderRadius: 2 })),
    ];

    P.audit = [
      this.table(['When', 'Actor', 'Action', 'Before → after'],
        [['12 Sep 09:41', 'Admin · Lee Chong', 'Margin change · BC-001 Linen', '34% → 38%'],
         ['12 Sep 08:22', 'CS · Suraya', 'Manual credit adjustment · Aiman Lim', 'RM 76.00 → RM 96.00'],
         ['11 Sep 16:03', 'Admin · Lee Chong', 'Tier override · Rimba Resort', 'Silver → Gold'],
         ['11 Sep 11:50', 'Prepress · Nazri', 'Artwork approval override · J-04102-1', 'issues-found → processing'],
         ['10 Sep 15:14', 'Admin · Lee Chong', 'Role change · Chin Wei Kit', 'Production → Logistics']],
        ['16%', '20%', '34%', '30%']),
    ];

    // ===== WordPress-aligned sections (data-backed where the model exists) =====
    const M = n => this.money(n);
    const orders = this.state.admOrders || [], custs = this.state.admCustomers || [], staff = this.state.admStaff || [], posts = this.state.blog || [], ajobs = this.state.admJobs || [], alog = this.state.admAudit || [];
    const p = (txt) => h('p', { key: 'd', style: { fontSize: 13.5, color: MUT, lineHeight: 1.7, margin: '0 0 12px', maxWidth: '82ch' } }, txt);
    const stub = (desc, bullets) => [p(desc),
      bullets ? h('ul', { key: 'b', style: { margin: '0 0 12px', paddingLeft: 20, color: MUT, fontSize: 13, lineHeight: 1.9 } }, bullets.map((b, i) => h('li', { key: i }, b))) : null,
      h('div', { key: 's', style: { fontSize: 12, color: FAINT, border: '1px dashed ' + HAIR, borderRadius: 8, padding: '10px 12px', background: ALT } }, 'Scaffolded to match the WordPress feature — this section’s data layer is planned; the editor is on the build queue.')];
    P.orders = [p('Every order placed on the storefront, flowing into the production pipeline. Click an order to open it — artworks, billing & shipping, payment proof, customer history, invoice and order slip. ' + orders.length + ' order(s) on record.'),
      this.table(['Order', 'Customer', 'Items', 'Total', 'Payment', 'Status', ''],
        orders.length ? orders.slice(0, 40).map(o => [
          h('span', { 'data-go': 'vieworder:' + o.id, style: { color: TEAL, fontWeight: 600, cursor: 'pointer', fontFamily: 'ui-monospace,Menlo,monospace', fontSize: 12 } }, o.id),
          (o.customer && o.customer.name) || '—', (o.items || o.jobIds || []).length, M(o.total),
          this.chip(o.payment && o.payment.status === 'validated' ? 'Paid' : 'Pending', o.payment && o.payment.status === 'validated' ? 'ok' : 'warn'), o.status,
          h('span', { 'data-go': 'vieworder:' + o.id, style: { color: TEAL, fontWeight: 600, cursor: 'pointer' } }, 'Open →')]) : [['—', 'No orders yet', '', '', '', '', '']],
        ['150px', null, '55px', '100px', '90px', '110px', '70px'])];
    P.customers = [p('Registered customer accounts, their membership tier and credit balance.'),
      this.table(['Name', 'Email', 'Tier', 'Credit', 'Joined'],
        custs.length ? custs.slice(0, 40).map(c => [c.name, c.email, this.chip(c.tier, 'neutral'), M(c.creditBalance || 0), (c.createdAt || '').slice(0, 10)]) : [['No customers yet', '', '', '', '']],
        ['22%', null, '110px', '100px', '110px'])];
    P.users = [p('Every staff account and its role. Admin, Outlet (staff/manager), Production (Prepress/Scheduler/Logistics/Manager) and Vendor are separate logins with separate access.'),
      this.table(['Name', 'Email', 'Type', 'Role'],
        staff.length ? staff.map(s => [s.name, s.email, this.chip(s.type, 'teal'), (s.role || '').replace(/_/g, ' ')]) : [['—', '', '', '']],
        ['24%', null, '120px', '160px'])];
    P.printing = [p('Outsourced printing jobs — the Scheduler requests vendor quotes, awards a PO to the best, and the vendor prints a shipping label.'),
      this.table(['Job', 'Product', 'Status', 'Awarded / PO'],
        ajobs.filter(j => j.outsource).length ? ajobs.filter(j => j.outsource).map(j => [j.id, j.product, this.chip(j.outsource.awardedTo ? 'Awarded' : (j.outsource.status || '').replace(/_/g, ' '), j.outsource.awardedTo ? 'ok' : 'warn'), j.outsource.po || (j.outsource.vendors.filter(v => v.submittedAt).length + ' quote(s)')]) : [['—', 'No outsourced jobs right now', '', '']],
        ['110px', null, '150px', null])];
    P.posts = [h('div', { key: 'a', style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, flexWrap: 'wrap', gap: 10 } }, h('span', { style: { fontSize: 13, color: MUT } }, posts.length + ' articles migrated from printoka.com'), this.btn('View Learning Hub', 'ghost', 'learn')),
      this.table(['Title', 'Category', 'Date', 'Status'], posts.slice(0, 40).map(pp => [pp.title, pp.tag, pp.date, this.chip(pp.bodyReady ? 'Published' : 'Draft', pp.bodyReady ? 'ok' : 'warn')]), [null, '150px', '110px', '110px'])];
    P.wallet = [p('Customer credit balances — the TeraWallet replacement. Total outstanding credit liability: ' + M(custs.reduce((s, c) => s + (c.creditBalance || 0), 0)) + '.'),
      this.table(['Customer', 'Email', 'Credit balance'], custs.filter(c => (c.creditBalance || 0) > 0).length ? custs.filter(c => (c.creditBalance || 0) > 0).map(c => [c.name, c.email, M(c.creditBalance)]) : [['No credit issued yet', '', '']], ['26%', null, '140px'])];
    P.seo = [p('Programmatic SEO — ' + posts.length + ' blog articles plus 479 city/service landing pages, all in the sitemap with the original printoka.com URL structure preserved.'),
      h('div', { key: 'b', style: { display: 'flex', gap: 10, flexWrap: 'wrap' } }, h('a', { href: '/sitemap.xml', target: '_blank', style: { fontSize: 13, fontWeight: 600, color: TEAL, border: '1px solid ' + HAIR, borderRadius: 8, padding: '10px 16px', textDecoration: 'none' } }, 'Open sitemap.xml'), this.btn('View blog', 'ghost', 'learn'))];
    P.audit = [p('Every destructive or financial change is logged with actor, timestamp and detail.'),
      this.table(['When', 'Actor', 'Role', 'Action', 'Detail'],
        alog.length ? alog.slice().reverse().slice(0, 30).map(e => [(e.ts || '').slice(0, 16).replace('T', ' '), e.actor, (e.role || '').replace(/_/g, ' '), (e.action || '').replace(/_/g, ' '), e.note || '']) : [['—', 'No activity yet', '', '', '']],
        ['130px', '120px', '110px', '130px', null])];
    const arts = []; (orders || []).forEach(o => (o.items || []).forEach(it => (it.artworks || []).forEach(a => arts.push([a, (o.customer && o.customer.name) || '—', it.product, o.id, (o.createdAt || '').slice(0, 10)]))));
    P.artworks = [p('Every customer artwork file uploaded with an order, across the whole store — the prepress team checks each against the order before production. ' + arts.length + ' file(s) on record.'),
      arts.length ? this.table(['Artwork file', 'Customer', 'Product', 'Order', 'Uploaded'],
        arts.slice(0, 60).map(a => [h('span', { style: { fontFamily: 'ui-monospace,Menlo,monospace', fontSize: 12 } }, a[0]), a[1], a[2], h('span', { style: { color: TEAL, fontWeight: 600 } }, a[3]), a[4]]),
        [null, '160px', '160px', '150px', '110px'])
        : h('div', { key: 'e', style: { border: '1px dashed ' + HAIR, borderRadius: 10, padding: 26, textAlign: 'center', color: FAINT, fontSize: 13 } }, 'No artworks uploaded yet — they appear here as customers place orders with files.')];
    const qlist = this.state.quotesList || [];
    const qinp = { font: '400 13px Montserrat,sans-serif', padding: '8px 10px', border: '1px solid ' + HAIR, borderRadius: 7, width: '100%' };
    const linkAct = (label, on) => h('span', { onClick: on, style: { fontSize: 12.5, fontWeight: 600, color: TEAL, cursor: 'pointer' } }, label);
    P.quotes = [
      h('div', { key: 'h', style: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' } },
        p('Custom quotes — both customer requests (price & issue them) and quotes you prepare manually for a customer. An issued quote can be accepted & paid (creating an order) or sent back for changes.'),
        h('span', { onClick: () => this.setState({ mq_new: !this.state.mq_new }), style: { flex: 'none', background: this.state.mq_new ? '#fff' : TEAL, color: this.state.mq_new ? MUT : '#fff', border: '1px solid ' + (this.state.mq_new ? HAIR : TEAL), fontWeight: 600, fontSize: 13, padding: '9px 16px', borderRadius: 8, cursor: 'pointer' } }, this.state.mq_new ? 'Cancel' : '＋ New custom quote')),
      this.state.mq_new ? h('div', { key: 'form', style: { border: '1px solid ' + TEAL, borderRadius: 12, padding: 16, background: '#fdf7f7', marginBottom: 4 } },
        h('div', { style: { fontSize: 13.5, fontWeight: 600, marginBottom: 10 } }, 'Prepare a quote for a customer'),
        h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(150px,1fr))', gap: 8, marginBottom: 8 } },
          h('input', { placeholder: 'Customer name', value: this.state.mq_custName || '', onChange: e => this.setField('mq_custName', e.target.value), style: qinp }),
          h('input', { placeholder: 'Customer email (optional)', value: this.state.mq_custEmail || '', onChange: e => this.setField('mq_custEmail', e.target.value), style: qinp }),
          h('input', { placeholder: 'Product (e.g. Book Printing)', value: this.state.mq_product || '', onChange: e => this.setField('mq_product', e.target.value), style: qinp }),
          h('input', { placeholder: 'Quantity', value: this.state.mq_qty || '', onChange: e => this.setField('mq_qty', e.target.value), style: qinp }),
          h('input', { type: 'number', placeholder: 'Price (RM)', value: this.state.mq_price || '', onChange: e => this.setField('mq_price', e.target.value), style: qinp }),
          h('input', { type: 'number', placeholder: 'Lead time (days)', value: this.state.mq_lead || '', onChange: e => this.setField('mq_lead', e.target.value), style: qinp }),
          h('input', { type: 'number', placeholder: 'Weight (g, optional)', value: this.state.mq_weight || '', onChange: e => this.setField('mq_weight', e.target.value), style: qinp })),
        h('textarea', { placeholder: 'Quote data — full spec breakdown, itemised pricing, terms (appears on the quote PDF)', value: this.state.mq_data || '', onChange: e => this.setField('mq_data', e.target.value), style: Object.assign({}, qinp, { minHeight: 120, resize: 'vertical', marginBottom: 8, fontFamily: 'inherit' }) }),
        h('input', { placeholder: 'Internal remarks (staff only)', value: this.state.mq_remarks || '', onChange: e => this.setField('mq_remarks', e.target.value), style: Object.assign({}, qinp, { marginBottom: 8 }) }),
        this.state.mq_err ? h('div', { style: { fontSize: 12, color: '#c0392b', marginBottom: 8 } }, this.state.mq_err) : null,
        h('span', { onClick: () => this.submitManualQuote(), style: { display: 'inline-block', background: TEAL, color: '#fff', fontWeight: 600, fontSize: 13, padding: '10px 18px', borderRadius: 8, cursor: this.state.mq_busy ? 'wait' : 'pointer' } }, this.state.mq_busy ? 'Saving…' : 'Issue quote')) : null,
      qlist.length === 0 ? h('div', { key: 'e', style: { border: '1px dashed ' + HAIR, borderRadius: 10, padding: 28, textAlign: 'center', color: FAINT } }, 'No custom quotes yet.') :
      h('div', { key: 'l', style: { display: 'flex', flexDirection: 'column', gap: 12 } }, qlist.map(q => h('div', { key: q.id, style: { border: '1px solid ' + HAIR, borderRadius: 12, padding: 14, background: '#fff' } },
        h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'baseline', flexWrap: 'wrap', marginBottom: 6 } },
          h('div', null, h('span', { style: { font: '600 12px ui-monospace,Menlo,monospace', color: TEAL, marginRight: 8 } }, q.id), h('span', { style: { fontSize: 14, fontWeight: 600 } }, (q.requirement && q.requirement.product) || 'Custom job'), h('span', { style: { fontSize: 12.5, color: MUT } }, ' · ' + ((q.customer && q.customer.name) || 'Guest') + (q.manual ? ' · manual' : ''))),
          this.chip({ requested: 'Needs pricing', issued: 'Issued · RM ' + q.price, quoted: 'Quoted · RM ' + q.price, accepted: 'Accepted', rejected: 'Changes requested' }[q.status] || q.status, q.status === 'requested' ? 'warn' : q.status === 'accepted' ? 'ok' : 'neutral')),
        h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.6, marginBottom: 8 } }, [q.requirement && q.requirement.qty && 'Qty ' + q.requirement.qty, q.requirement && q.requirement.size, q.requirement && q.requirement.material, q.requirement && q.requirement.finishing].filter(Boolean).join(' · ') + ((q.staff && q.staff.name) ? ' · by ' + q.staff.name + (q.staff.outlet ? ' (' + q.staff.outlet + ')' : '') : '') + (q.remarks ? ' — remark: ' + q.remarks : '')),
        h('div', { style: { display: 'flex', gap: 14, flexWrap: 'wrap', alignItems: 'center' } },
          q.status === 'requested' ? h('div', { style: { display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', flex: 1 } },
            h('input', { type: 'number', placeholder: 'Price (RM)', value: this.state['qp_' + q.id + '_price'] || '', onChange: e => this.setField('qp_' + q.id + '_price', e.target.value), style: Object.assign({}, qinp, { maxWidth: 130 }) }),
            h('input', { type: 'number', placeholder: 'Lead days', value: this.state['qp_' + q.id + '_lead'] || '', onChange: e => this.setField('qp_' + q.id + '_lead', e.target.value), style: Object.assign({}, qinp, { maxWidth: 110 }) }),
            h('input', { placeholder: 'Note (optional)', value: this.state['qp_' + q.id + '_note'] || '', onChange: e => this.setField('qp_' + q.id + '_note', e.target.value), style: Object.assign({}, qinp, { flex: 1, minWidth: 140 }) }),
            h('span', { onClick: () => this.quotePrice(q.id), style: { background: TEAL, color: '#fff', fontWeight: 600, fontSize: 13, padding: '9px 16px', borderRadius: 8, cursor: 'pointer' } }, 'Issue quote'))
            : h('span', { style: { fontSize: 12.5, color: MUT, flex: 1 } }, q.status === 'issued' || q.status === 'quoted' ? 'Issued at RM ' + q.price + (q.leadDays ? ' · ' + q.leadDays + ' days' : '') + ' — awaiting the customer.' : q.orderId ? 'Accepted → order ' + q.orderId : 'Customer requested changes.'),
          linkAct('View PDF →', () => this.openDoc(q.id, 'quote')))))),
    ];
    // ----- Custom Invoice: manually prepared invoices to customers -----
    const cinvs = this.state.custInvoices || [];
    P.custinvoice = [
      h('div', { key: 'h', style: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' } },
        p('Invoices prepared manually by admin or outlet and issued to a customer (independent of the storefront order flow). Set the status, add a description and issue a printable PDF. ' + cinvs.length + ' invoice(s).'),
        h('span', { onClick: () => this.setState({ ci_new: !this.state.ci_new }), style: { flex: 'none', background: this.state.ci_new ? '#fff' : TEAL, color: this.state.ci_new ? MUT : '#fff', border: '1px solid ' + (this.state.ci_new ? HAIR : TEAL), fontWeight: 600, fontSize: 13, padding: '9px 16px', borderRadius: 8, cursor: 'pointer' } }, this.state.ci_new ? 'Cancel' : '＋ New custom invoice')),
      this.state.ci_new ? h('div', { key: 'form', style: { border: '1px solid ' + TEAL, borderRadius: 12, padding: 16, background: '#fdf7f7', marginBottom: 4 } },
        h('div', { style: { fontSize: 13.5, fontWeight: 600, marginBottom: 10 } }, 'Prepare an invoice for a customer'),
        h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(150px,1fr))', gap: 8, marginBottom: 8 } },
          h('input', { placeholder: 'Invoice number', value: this.state.ci_number || '', onChange: e => this.setField('ci_number', e.target.value), style: qinp }),
          h('input', { type: 'date', placeholder: 'Invoice date', value: this.state.ci_date || '', onChange: e => this.setField('ci_date', e.target.value), style: qinp }),
          h('select', { value: this.state.ci_status || 'unpaid', onChange: e => this.setField('ci_status', e.target.value), style: qinp }, ['unpaid', 'paid', 'cancelled'].map(s => h('option', { key: s, value: s }, s[0].toUpperCase() + s.slice(1)))),
          h('select', { value: this.state.ci_userId || '', onChange: e => { const c = custs.find(x => x.id === e.target.value); this.setState({ ci_userId: e.target.value, ci_userName: c ? c.name : this.state.ci_userName }); }, style: qinp },
            h('option', { value: '' }, 'Select customer…'), custs.map(c => h('option', { key: c.id, value: c.id }, c.name + ' (' + c.email + ')'))),
          h('input', { placeholder: 'or type customer name', value: this.state.ci_userName || '', onChange: e => this.setField('ci_userName', e.target.value), style: qinp }),
          h('input', { type: 'number', placeholder: 'Price (RM)', value: this.state.ci_price || '', onChange: e => this.setField('ci_price', e.target.value), style: qinp }),
          h('input', { placeholder: 'Order ID (optional)', value: this.state.ci_orderId || '', onChange: e => this.setField('ci_orderId', e.target.value), style: qinp })),
        h('textarea', { placeholder: 'Invoice description — full spec, quantity, price (appears on the invoice PDF)', value: this.state.ci_desc || '', onChange: e => this.setField('ci_desc', e.target.value), style: Object.assign({}, qinp, { minHeight: 110, resize: 'vertical', marginBottom: 8, fontFamily: 'inherit' }) }),
        this.state.ci_err ? h('div', { style: { fontSize: 12, color: '#c0392b', marginBottom: 8 } }, this.state.ci_err) : null,
        h('span', { onClick: () => this.submitCustomInvoice(), style: { display: 'inline-block', background: TEAL, color: '#fff', fontWeight: 600, fontSize: 13, padding: '10px 18px', borderRadius: 8, cursor: this.state.ci_busy ? 'wait' : 'pointer' } }, this.state.ci_busy ? 'Saving…' : 'Issue invoice')) : null,
      cinvs.length === 0 ? h('div', { key: 'e', style: { border: '1px dashed ' + HAIR, borderRadius: 10, padding: 28, textAlign: 'center', color: FAINT } }, 'No custom invoices yet.') :
      this.table(['Invoice', 'Customer', 'Status', 'Price', 'Prepared by', 'Date', ''],
        cinvs.map(inv => [
          h('span', { style: { fontFamily: 'ui-monospace,Menlo,monospace', fontSize: 12, fontWeight: 600 } }, inv.number || inv.id),
          inv.userName || '—',
          h('select', { value: inv.status, onChange: e => this.setCustomInvoiceStatus(inv.id, e.target.value), style: { font: '600 11.5px Montserrat,sans-serif', padding: '4px 6px', borderRadius: 6, border: '1px solid ' + HAIR, color: inv.status === 'paid' ? '#63AA02' : inv.status === 'cancelled' ? '#6c757d' : '#a1660a' } }, ['unpaid', 'paid', 'cancelled'].map(s => h('option', { key: s, value: s }, s[0].toUpperCase() + s.slice(1)))),
          this.rm(inv.price), (inv.createdBy && inv.createdBy.name) || '—', (inv.date || '').slice(0, 10),
          linkAct('View PDF →', () => this.openDoc(inv.id, 'custominvoice'))]),
        ['150px', null, '110px', '100px', '140px', '100px', '90px'])];
    const PAGES = [['Home', 'home', '/'], ['About', 'about', '/about'], ['Corporate accounts', 'corporate', '/corporate'], ['Partners', 'partners', '/partners'], ['Support & FAQ', 'support', '/support'], ['Template downloads', 'downloads', '/downloads'], ['Membership', 'membership', '/membership'], ['Learning Hub', 'learn', '/blog'], ['Terms & policies', 'terms', '/terms'], ['Contact / custom quote', 'contact', '/contact']];
    P.pages = [p('Every published storefront page. Content pages are live in the app; click to view.'),
      this.table(['Page', 'Path', 'Status', ''],
        PAGES.map(pg => [h('span', { style: { fontWeight: 600 } }, pg[0]), h('span', { style: { fontFamily: 'ui-monospace,Menlo,monospace', fontSize: 12, color: MUT } }, pg[2]), this.chip('Published', 'ok'),
          h('span', { 'data-go': pg[1], style: { color: TEAL, fontWeight: 600, cursor: 'pointer' } }, 'View →')]),
        [null, '200px', '110px', '80px'])];
    const media = this.state.media || [];
    P.media = [p('Media library — the image assets shipped with the storefront (product photos + brand/UI icons). ' + media.length + ' file(s). Product photos and the original site media are served from the same asset pipeline.'),
      media.length ? h('div', { key: 'g', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(130px,1fr))', gap: 12 } },
        media.slice(0, 60).map((m, i) => h('div', { key: i, style: { border: '1px solid ' + HAIR, borderRadius: 10, overflow: 'hidden', background: '#fff' } },
          h('div', { style: { height: 90, background: ALT, display: 'grid', placeItems: 'center', overflow: 'hidden' } }, h('img', { src: window.__asset(m.file), alt: '', style: { maxHeight: '100%', maxWidth: '100%', objectFit: 'contain' } })),
          h('div', { style: { padding: '7px 9px', fontSize: 11, color: MUT, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' } }, m.name))))
        : h('div', { key: 'e', style: { color: FAINT, fontSize: 13 } }, 'Loading media…')];
    const dls = this.state.downloads || [];
    const dlRows = dls.reduce((s, c) => s + c.folds.reduce((t, f) => t + f.rows.length, 0), 0);
    const dlFiles = dls.reduce((s, c) => s + c.folds.reduce((t, f) => t + f.rows.reduce((x, r) => x + r.files.length, 0), 0), 0);
    P.downloads = [p('Print-ready template downloads (AI / PSD / PDF) per product size — migrated verbatim from printoka.com. ' + dls.length + ' categories · ' + dlRows + ' size variants · ' + dlFiles + ' files. Live on the storefront Downloads page.'),
      h('div', { key: 'b', style: { marginBottom: 12 } }, this.btn('View on site →', 'ghost', 'downloads')),
      this.table(['Category', 'Variations', 'Size rows', 'Files'],
        dls.length ? dls.map(c => [c.title, c.folds.length, c.folds.reduce((s, f) => s + f.rows.length, 0), c.folds.reduce((s, f) => s + f.rows.reduce((x, r) => x + r.files.length, 0), 0)]) : [['Loading…', '', '', '']],
        [null, '110px', '110px', '90px'])];
    const faqs = this.state.faq || [];
    P.faqs = [p('Support FAQ — migrated verbatim from printoka.com/support. ' + faqs.length + ' topics · ' + faqs.reduce((s, c) => s + c.questions.length, 0) + ' questions. Shown on the storefront Support page.'),
      h('div', { key: 'b', style: { marginBottom: 12 } }, this.btn('View on site →', 'ghost', 'support')),
      h('div', { key: 'l', style: { display: 'flex', flexDirection: 'column', gap: 16 } }, faqs.map(c =>
        h('div', { key: c.id, style: { border: '1px solid ' + HAIR, borderRadius: 10, background: '#fff', overflow: 'hidden' } },
          h('div', { style: { padding: '10px 14px', background: ALT, fontSize: 13.5, fontWeight: 600, borderBottom: '1px solid ' + HAIR } }, c.title, h('span', { style: { color: FAINT, fontWeight: 400, marginLeft: 8 } }, c.questions.length + ' questions')),
          c.questions.map((qa, i) => h('div', { key: i, style: { padding: '10px 14px', borderTop: i ? '1px solid ' + LINE : 'none' } },
            h('div', { style: { fontSize: 13, fontWeight: 600, marginBottom: 3 } }, qa.q),
            h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.65, whiteSpace: 'pre-wrap' } }, qa.a)))))) ];
    const etpls = this.state.emailTpls || [], outbox = this.state.emailOutbox || [];
    P.followup = [p('Automated system emails, sent per trigger event (account, wallet, orders, quotes, vendor jobs). ' + etpls.filter(t => t.active).length + ' of ' + etpls.length + ' active · ' + outbox.length + ' sent recently. Deactivate any you don’t want the system to send.'),
      this.table(['Email', 'Trigger / delay', 'Type', 'Sent', 'Opens', 'Status'],
        etpls.length ? etpls.map(t => [
          h('span', { style: { fontWeight: 600 } }, t.name),
          h('span', { style: { fontSize: 12.5, color: MUT } }, t.delay),
          t.type,
          String(t.sent || 0),
          (t.sent ? Math.round((t.opens / t.sent) * 100) + '%' : '—'),
          h('span', { style: { display: 'flex', gap: 10, alignItems: 'center' } },
            this.chip(t.active ? 'Active' : 'Inactive', t.active ? 'ok' : 'neutral'),
            h('span', { onClick: () => this.toggleEmail(t.id, !t.active), style: { fontSize: 12.5, fontWeight: 600, color: TEAL, cursor: 'pointer' } }, t.active ? 'Deactivate' : 'Activate')),
        ]) : [['Loading…', '', '', '', '', '']],
        [null, '200px', '110px', '70px', '80px', '150px']),
      h('div', { key: 'ob', style: { marginTop: 20 } },
        h('div', { style: { fontSize: 14, fontWeight: 600, marginBottom: 10 } }, 'Recent outbox'),
        outbox.length ? this.table(['When', 'Email', 'To', 'Subject'],
          outbox.slice(0, 30).map(e => [(e.ts || '').slice(0, 16).replace('T', ' '), e.template, e.to, e.subject]),
          ['140px', '180px', '180px', null])
          : h('div', { style: { border: '1px dashed ' + HAIR, borderRadius: 10, padding: 22, textAlign: 'center', color: FAINT, fontSize: 13 } }, 'No emails sent yet — place an order, top up a wallet or issue a quote to see them here.'))];
    P.settings = (() => {
      const a = (this.state.settings && this.state.settings.announcement) || {};
      const val = (k, d) => { const s = this.state['ann_' + k]; return s != null ? s : (a[k] != null ? a[k] : d); };
      const inp = { font: '400 13.5px Montserrat,sans-serif', padding: '10px 12px', border: '1px solid ' + HAIR, borderRadius: 8, width: '100%' };
      const lbl = t => h('div', { style: { fontSize: 12.5, fontWeight: 600, marginBottom: 6 } }, t);
      const routes = ['membership', 'category', 'contact', 'learn', 'about'];
      return [p('The storefront announcement bar shown site-wide (above the header). Edit it here — changes are saved and go live for every visitor immediately.'),
        h('div', { key: 'prev', style: { marginBottom: 16 } },
          h('div', { style: { fontSize: 11, fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: FAINT, marginBottom: 6 } }, 'Live preview'),
          val('hidden', false) ? h('div', { style: { fontSize: 13, color: FAINT, fontStyle: 'italic', border: '1px dashed ' + HAIR, borderRadius: 8, padding: 14 } }, 'The announcement bar is currently hidden.') :
          h('div', { style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '10px 20px', padding: '12px 16px', borderRadius: 4, color: '#fff', fontSize: 14, backgroundImage: 'linear-gradient(90deg,#FF9A2E,#F02B29)' } },
            h('div', { style: { flex: '1 1 auto', minWidth: 0, lineHeight: 1.35 } }, val('text', '')),
            h('span', { style: { fontWeight: 600, whiteSpace: 'nowrap' } }, val('cta', 'Find out more') + ' →'))),
        h('div', { key: 'form', style: { display: 'flex', flexDirection: 'column', gap: 14, maxWidth: 640 } },
          h('div', null, lbl('Announcement text'), h('textarea', { value: val('text', ''), onChange: e => this.setField('ann_text', e.target.value), style: Object.assign({}, inp, { minHeight: 70, resize: 'vertical', fontFamily: 'inherit' }) })),
          h('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 } },
            h('div', null, lbl('Button label'), h('input', { value: val('cta', ''), onChange: e => this.setField('ann_cta', e.target.value), style: inp })),
            h('div', null, lbl('Button links to'), h('select', { value: val('link', 'membership'), onChange: e => this.setField('ann_link', e.target.value), style: inp }, routes.map(r => h('option', { key: r, value: r }, r))))),
          h('label', { style: { display: 'flex', gap: 9, alignItems: 'center', fontSize: 13, color: MUT, cursor: 'pointer' } },
            h('input', { type: 'checkbox', checked: !!val('hidden', false), onChange: e => this.setField('ann_hidden', e.target.checked) }), 'Hide the announcement bar'),
          this.state.setMsg ? h('div', { style: { fontSize: 12.5, color: '#3d8b40' } }, this.state.setMsg) : null,
          h('span', { onClick: () => this.saveSettings({ announcement: { text: val('text', ''), cta: val('cta', ''), link: val('link', 'membership'), hidden: !!val('hidden', false) } }), style: { alignSelf: 'flex-start', background: TEAL, color: '#fff', fontWeight: 600, fontSize: 14, padding: '11px 24px', borderRadius: 8, cursor: this.state.setBusy ? 'wait' : 'pointer' } }, this.state.setBusy ? 'Saving…' : 'Save & publish'))];
    })();
    P.theme = this.settingsForm('theme', [['primary', 'Brand primary colour'], ['heroTitle', 'Homepage hero title'], ['heroSub', 'Homepage hero subtitle', 'textarea']], 'Branding shown across the storefront — the primary colour, and the homepage hero copy.');
    P.storeset = this.settingsForm('store', [['name', 'Store name'], ['supportEmail', 'Support email'], ['supportPhone', 'Support phone / WhatsApp'], ['countries', 'Countries served'], ['currency', 'Base currency']], 'General store settings (WooCommerce “Settings” equivalent) — identity, contact and the markets you serve.');
    const ob = this.state.emailOutbox || [];
    P.scheduled = [p('Scheduled & sent emails — the live outbox for every automated Follow-Up email. ' + ob.length + ' in the recent queue.'),
      ob.length ? this.table(['When', 'Email', 'Recipient', 'Subject'], ob.slice(0, 40).map(e => [(e.ts || '').slice(0, 16).replace('T', ' '), e.template, e.to, e.subject]), ['150px', '180px', '190px', null])
        : h('div', { key: 'e', style: { border: '1px dashed ' + HAIR, borderRadius: 10, padding: 22, textAlign: 'center', color: FAINT, fontSize: 13 } }, 'Nothing scheduled yet — automated emails appear here as events fire.')];
    const byTier = {}; (custs || []).forEach(c => { byTier[c.tier || 'Standard'] = (byTier[c.tier || 'Standard'] || 0) + 1; });
    P.mailing = [p('Mailing lists — customer segments you can target with campaigns and broadcasts. ' + custs.length + ' subscriber(s) total.'),
      this.table(['List', 'Segment rule', 'Subscribers'],
        [['All customers', 'Every registered account', String(custs.length)],
         ['Members (Bronze+)', 'Tier above Standard', String(custs.filter(c => c.tier && c.tier !== 'Standard').length)],
         ['Gold & Platinum', 'Top tiers', String((byTier.Gold || 0) + (byTier.Platinum || 0))],
         ['With credit balance', 'Wallet balance > 0', String(custs.filter(c => (c.creditBalance || 0) > 0).length)],
         ['Newsletter opt-in', 'Agreed to marketing', String(custs.filter(c => c.newsletter || c.promoOptIn).length)]],
        [null, null, '130px'])];
    return this.shell('Admin', navItems, activeLabel, [
      this.head(activeLabel, 'Role-scoped backoffice. Every destructive or financial change writes actor, timestamp and before/after values to the audit log.'),
      h('div', { key: 'p', style: { marginTop: 18 } }, P[tab] || P.analytics),
    ]);
  }

  // ===== VENDOR / HUB PORTAL =====
  s_vendor() {
    const uid = (this.state.user && this.state.user.id) || '';
    const vname = (this.state.user && this.state.user.name) || 'Vendor';
    const jobs = this.state.vendorJobs || [];
    const mine = j => (j.outsource && j.outsource.vendors.find(v => v.vendorId === uid)) || {};
    const open = jobs.filter(j => j.outsource && (!j.outsource.awardedTo || j.outsource.awardedTo === uid));
    const requests = open.filter(j => j.outsource.awardedTo !== uid);
    const awarded = jobs.filter(j => j.outsource && j.outsource.awardedTo === uid);
    const pending = requests.filter(j => !mine(j).submittedAt).length;
    const identity = { title: vname, sub: 'Vendor / Hub' };
    const tabs = ['Dashboard', 'Quote requests', 'Awarded jobs'];
    const tab = tabs.indexOf(this.state.sTab) >= 0 ? this.state.sTab : 'Dashboard';
    const inp = { font: '400 13px Montserrat,sans-serif', padding: '9px 11px', border: '1px solid ' + HAIR, borderRadius: 7, width: '100%' };
    const cards = [
      ['Quote requests', pending, 'edit-3', 'teal', 'awaiting your price', pending ? 'New' : null, pending > 0],
      ['Quotes submitted', requests.filter(j => mine(j).submittedAt).length, 'check', 'orange', 'awaiting decision'],
      ['Awarded jobs', awarded.length, 'box', 'red', 'print & ship'],
    ];
    const sectionTitle = (t, s) => h('div', { key: 't', style: { marginBottom: 6 } }, h('h1', { style: { fontSize: 26, fontWeight: 700, letterSpacing: '-.02em', margin: '2px 0 4px' } }, t), s ? h('p', { style: { margin: 0, fontSize: 13.5, color: MUT, maxWidth: '82ch', lineHeight: 1.65 } }, s) : null);
    const requestsGrid = requests.length === 0 ? h('div', { key: 'e', style: { border: '1px dashed ' + HAIR, borderRadius: 12, padding: 34, textAlign: 'center', color: FAINT, background: '#fff' } }, 'No open quote requests right now.') :
      h('div', { key: 'r', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(320px,1fr))', gap: 16 } },
        requests.map(j => { const me = mine(j); const submitted = !!me.submittedAt;
          return h('div', { key: j.id, style: { border: '1px solid ' + HAIR, borderRadius: 12, padding: 16, background: '#fff', display: 'flex', flexDirection: 'column', gap: 10 } },
            h('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' } },
              h('span', { style: { font: '600 12px ui-monospace,Menlo,monospace', color: TEAL } }, j.id),
              this.chip(submitted ? 'Quote submitted' : 'Awaiting your quote', submitted ? 'ok' : 'warn')),
            h('div', { style: { fontSize: 14.5, fontWeight: 600 } }, j.product),
            h('div', { style: { fontSize: 12.5, color: MUT, lineHeight: 1.55 } }, j.spec + ' · qty ' + (j.qty || 0).toLocaleString()),
            h('div', { style: { fontSize: 12, color: FAINT } }, 'Deliver to: ' + (j.fulfillmentOutlet || 'KL Damansara Outlet') + ' · for ' + j.customer),
            submitted ? h('div', { style: { fontSize: 13, color: INK, background: ALT, borderRadius: 8, padding: '10px 12px' } }, 'Your quote: ', h('b', null, this.money(me.price)), ' · ' + me.leadDays + ' days lead time — locked, awaiting the Scheduler’s decision.')
              : h('div', { style: { display: 'flex', flexDirection: 'column', gap: 8 } },
                h('div', { style: { display: 'flex', gap: 8 } },
                  h('input', { type: 'number', placeholder: 'Price (RM)', value: this.state['vq_' + j.id + '_price'] || '', onChange: e => this.setField('vq_' + j.id + '_price', e.target.value), style: inp }),
                  h('input', { type: 'number', placeholder: 'Lead days', value: this.state['vq_' + j.id + '_lead'] || '', onChange: e => this.setField('vq_' + j.id + '_lead', e.target.value), style: inp })),
                h('input', { placeholder: 'Note (optional)', value: this.state['vq_' + j.id + '_note'] || '', onChange: e => this.setField('vq_' + j.id + '_note', e.target.value), style: inp }),
                h('span', { onClick: () => this.vendorSubmitQuote(j.id), style: { background: TEAL, color: '#fff', fontWeight: 600, fontSize: 13, padding: '10px', borderRadius: 8, textAlign: 'center', cursor: 'pointer' } }, 'Submit quote')));
        }));
    const awardedGrid = awarded.length === 0 ? h('div', { key: 'ae', style: { border: '1px dashed ' + HAIR, borderRadius: 12, padding: 34, textAlign: 'center', color: FAINT, background: '#fff' } }, 'No awarded jobs yet — win a quote and it appears here to print & ship.') :
      h('div', { key: 'awg', style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(320px,1fr))', gap: 16 } },
        awarded.map(j => { const L = j.outsource.label || {};
          return h('div', { key: j.id, style: { border: '2px solid ' + INK, borderRadius: 12, overflow: 'hidden', background: '#fff' } },
            h('div', { style: { background: INK, color: '#fff', padding: '10px 14px', display: 'flex', justifyContent: 'space-between', fontSize: 12 } }, h('span', null, 'SHIPPING LABEL'), h('span', { style: { fontFamily: 'ui-monospace,Menlo,monospace' } }, L.id || '')),
            h('div', { style: { padding: 16, display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13 } },
              h('div', { style: { fontSize: 16, fontWeight: 700 } }, L.dest || 'Destination outlet'),
              h('div', { style: { color: MUT } }, 'Attn: ' + (L.customer || j.customer)),
              h('div', { style: { color: MUT } }, L.product + ' · qty ' + (L.qty || j.qty)),
              h('div', { style: { marginTop: 6, paddingTop: 8, borderTop: '1px dashed ' + HAIR, display: 'flex', justifyContent: 'space-between', fontSize: 12, color: FAINT } }, h('span', null, 'PO ' + (L.po || j.outsource.po)), h('span', null, 'Order ' + j.orderId)),
              h('div', { style: { marginTop: 4, height: 34, background: 'repeating-linear-gradient(90deg,#111 0 2px,#fff 2px 4px,#111 4px 5px,#fff 5px 9px)' } }),
              h('span', { onClick: () => { if (typeof window !== 'undefined') window.print(); }, style: { marginTop: 8, background: TEAL, color: '#fff', fontWeight: 600, fontSize: 13, padding: '9px', borderRadius: 8, textAlign: 'center', cursor: 'pointer' } }, 'Print label')));
        }));
    const content = tab === 'Dashboard' ? this.opsDashTab(cards, 'Jobs won')
      : tab === 'Quote requests' ? [sectionTitle('Quote requests', 'The Scheduler sends you jobs to quote. Reply with your price and lead time to the destination — if you win, print the shipping label and stick it on the parcel.'), requestsGrid]
      : [sectionTitle('Awarded jobs', 'You won these jobs. Print the shipping label, stick it on the parcel and deliver to the destination.'), awardedGrid];
    return this.staffPage(tabs, tab, identity, content);
  }
}


// ---- mount (custom-stack entry; DCLogic provided by runtime.js) ----
window.PKComponent = Component;
window.PKProps = { showSpecAnnotations: true, memberTier: 'Gold', defaultCountry: 'MY' };
