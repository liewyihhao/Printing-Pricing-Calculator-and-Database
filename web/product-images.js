/*
 * Original printoka.com imagery, mapped onto this project (files in assets/original/).
 * Loaded before app.js (window.PK_IMAGES) and read by the server for the SSR product pages.
 *
 *  products : our product id → the original product photo (cut-out on white)
 *  option(fieldKey, value, productId) → original image for a configurator option, or null.
 *    Per-product rules are checked first, then the generic rules [fieldKeyRegex, valueRegex, file]
 *    (first match wins; field regex '' = any field).
 */
(function (root) {
  var P = {
    // Business Essentials
    1: 'Standard-Business-Card.png', 111: 'computer-form-multiply.png', 106: '4.5x9.5-White-Envelope-Window.png',
    136: 'Hardcover-Booklet.jpg', 105: 'Letterhead-Full-Color.png', 24: 'Carbonised-Form.png', 104: 'Stitched-Office-Document.jpg',
    107: 'Presentation-Folder-Cover-Image.jpg', 110: 'Book-Binded-Ticket-and-Voucher.jpg',
    // Flyers & Leaflets
    101: 'Folded-Brochure-8.png', 103: 'Non-Folded-Brochure-3.png', 50: 'Non-Folded-Brochure-1.png', 102: 'Flyers-Cropped.png', 21: 'Non-Folded-Brochure-2.png',
    // Labels & Stickers
    117: 'Car-Window-Sticker.png', 60: 'Round-Sticker-Cover.png', 61: 'Round-Corner-Sticker.png', 184: 'Round-Sticker.png',
    116: 'Car-Window-Sticker.png', 176: 'custom-die-cut-sticker.png',
    // Books & Stationery
    37: 'Booklet-Staple-Content.png', 164: 'Hardcover-Booklet.jpg', 163: 'leather-portrait.jpg', 19: 'Booklet-Perfect-Cover.png',
    121: 'soft-stand-table-calendar.png',
    // Cards & Invitations
    169: 'Money-Packet-Horizontal.png', 166: '6x8-Folded-Cards-1.png', 168: 'Money-Pack-Vertical-2.png', 138: 'Money-Pack-Vertical-3.png',
    167: 'Money-Pack-Vertical.png', 113: 'frosted-plastic-card.jpg', 115: 'A5-Size-Folded-Cards.png', 114: 'Non-folded-Invitation-Cards.png',
    165: 'A4-Size-Folded-Cards.png',
    // Large Format
    160: 'Stand-Banner.png', 161: 'Stand-Banner.png', 162: 'Stand-Banner.png', 124: 'Stand-Banner.png', 159: 'Roll-Up-Banner.png',
    125: 'Roll-Up-Banner.png', 123: 'Hanging-Banner.png',
    // Packaging & Boxes
    179: 'premium-packaging.jpg', 127: 'Paperbag-290x200x95-1.png', 178: 'Paperbag-cover.jpg',
    // Apparel & Gifts
    132: 'Button-Badge.png', 128: 'C20.png', 133: 'HFS001.png', 174: 'lanyard.png', 139: 'N31A.png', 147: 'NH03A.png', 148: 'N01A.png',
    146: 'C10.png',
  };

  // per-product rules: Business Card types use the original card photos; sticker products map cut shapes
  var STICKERS = { 60: 1, 61: 1, 184: 1, 176: 1 };
  var PR = {
    1: [['category', /^standard$/i, 'Standard-Business-Card.png'], ['category', /fold/i, 'Folded-Business-Card.png'],
        ['category', /die.?cut/i, 'Custom-Die-Cut-Business-Card.png'], ['category', /plastic/i, 'frosted-plastic-card.jpg']],
  };
  var STICKER_RULES = [['category', /^round$/i, 'Round-Sticker.png'], ['category', /oval/i, 'Oval-Sticker.png'],
    ['category', /rectangle|square|standard shape/i, 'Square-Sticker.png'], ['category', /custom|kiss cut|multiple dieline/i, 'custom-die-cut-sticker.png']];

  var R = [
    // ---- paper / board / sticker materials ----
    ['paper|material|cover|content|inc_paper|stock', /frosted plastic/i, 'frosted-plastic-card.jpg'],
    ['', /black plastic/i, 'black-plastic.jpg'],
    ['', /matte art card|matte art paper|matt art/i, 'matte-art-paper.jpg'],
    ['', /gloss art card|^art card|\bart card\b/i, 'gloss-art-card.jpg'],
    ['', /gloss art paper|^art paper|\bart paper\b/i, 'gloss-art-paper.jpg'],
    ['', /linen/i, 'linen.jpg'],
    ['', /metal ice/i, 'metal-ice.jpg'],
    ['', /synthetic/i, 'synthetic-paper.jpg'],
    ['', /super white/i, 'super-white.jpg'],
    ['', /suwen/i, 'suwen.jpg'],
    ['', /conqueror.*vellum|\bvellum\b/i, 'conqueror-vellum.jpg'],
    ['', /conqueror|brilliant white/i, 'brilliant-white.jpg'],
    ['', /mirror ?kote|mirrorkorte|mirrorkote/i, 'mirror-kote.jpg'],
    ['', /removable/i, 'removable-white-pp.jpg'],
    ['', /opp|transparent (pet|film)|^transparent$/i, 'opp-transparent.jpg'],
    ['', /white pp/i, 'white-pp.jpg'],
    ['', /matte silver/i, 'matte-silver.jpg'],
    ['', /bright silver|silver polyester|metalised|metallised/i, 'bright-silver.jpg'],
    ['', /silver foil board/i, 'silver-foil-board.jpg'],
    ['', /warranty/i, 'warranty.jpg'],
    ['', /grey back|box ?board/i, 'box-board-grey-back.jpg'],
    ['', /b-?flute.*(brown|kraft)/i, 'b-flute-brown.jpg'], ['', /b-?flute.*white/i, 'b-flute-white.jpg'], ['', /b-?flute/i, 'b-flute-corrugated.jpg'],
    ['', /e-?flute.*(brown|kraft)/i, 'e-flute-brown.jpg'], ['', /e-?flute.*white/i, 'e-flute-white.jpg'], ['', /e-?flute/i, 'e-flute-corrugated.jpg'],
    ['', /brown kraft|kraft|craft/i, 'brown-craft.jpg'],
    ['', /simili/i, 'simili-paper.jpg'],
    ['', /woodfree|printing paper|uncoated/i, 'printing-paper.jpg'],
    ['', /black canvas/i, 'black-canvas.jpg'],
    // ---- lamination / coating / finishing ----
    ['lamination|finishing|coating|cover_lamination|spot', /spot ?uv/i, 'matte-laminationspot-uv.jpg'],
    ['lamination|finishing|coating|cover_lamination', /gloss (lamination|laminate|laminating)|^gloss$/i, 'gloss-lamination.jpg'],
    ['lamination|finishing|coating|cover_lamination', /matte? (lamination|laminate|laminating)/i, 'matte-lamination.jpg'],
    ['lamination|finishing|coating|cover_lamination', /water ?based|waterbase/i, 'gloss-waterbased.jpg'],
    ['emboss', /front|back|required|both/i, 'emboss-finishing.jpg'],
    ['round_corner$', /^required$/i, 'round-corner.jpg'],
    ['glu', /required|glued/i, 'glued.jpg'],
    // ---- hot stamping foil colours ----
    ['hot_stamping_colour|hs_colour|foil|stamping_colour', /gold/i, 'hot-stamping-gold.jpg'],
    ['hot_stamping_colour|hs_colour|foil|stamping_colour', /silver/i, 'hot-stamping-silver.jpg'],
    ['hot_stamping_colour|hs_colour|foil|stamping_colour', /black/i, 'hot-stamping-black.jpg'],
    ['hot_stamping_colour|hs_colour|foil|stamping_colour', /blue/i, 'hot-stamping-blue.jpg'],
    ['hot_stamping_colour|hs_colour|foil|stamping_colour', /green/i, 'hot-stamping-green.jpg'],
    ['hot_stamping_colour|hs_colour|foil|stamping_colour', /red/i, 'hot-stamping-red.jpg'],
    // ---- folding (fold codes) ----
    ['fold', /^1fa$/i, 'F1-1Fa.jpg'], ['fold', /^2fa$/i, 'F7-2Fa.png'], ['fold', /^2fb$/i, 'F8-2Fb.png'], ['fold', /^2fc$/i, 'F2-2Fc.png'],
    ['fold', /^3fa$/i, 'F10-3Fa.png'], ['fold', /^3fb$/i, 'F13-3Fb.png'], ['fold', /^4fa$/i, 'F11-4Fa.png'],
    // ---- sticker shapes (the "shape" field only) ----
    ['^shape$', /^round$/i, 'Round-Sticker.png'],
    ['^shape$', /oval/i, 'Oval-Sticker.png'],
    ['^shape$', /rectangle|square/i, 'Square-Sticker.png'],
    ['^shape$', /custom.*(die.?cut|shape)|kiss cut/i, 'custom-die-cut-sticker.png'],
    // ---- bag / handle / rope colours (swatches) ----
    ['colour|color', /^black$/i, 'black.jpg'], ['colour|color', /^white$/i, 'white.jpg'], ['colour|color', /^beige$/i, 'beige.jpg'],
    ['colour|color', /^yellow$/i, 'yellow.jpg'], ['colour|color', /^dark orange$/i, 'dark-orange.jpg'], ['colour|color', /^orange$/i, 'orange.jpg'],
    ['colour|color', /^magenta$/i, 'magenta.jpg'], ['colour|color', /^maroon$/i, 'maroon.jpg'], ['colour|color', /^milo green$/i, 'milo-green.jpg'],
    ['colour|color', /^dark green$/i, 'dark-green.jpg'], ['colour|color', /^turquoise$/i, 'turquoise.jpg'], ['colour|color', /^cyan$/i, 'cyan.jpg'],
    ['colour|color', /^royal blue$/i, 'royal-blue.jpg'], ['colour|color', /^navy blue$/i, 'navy-blue.jpg'], ['colour|color', /^dark purple$/i, 'dark-purple.jpg'],
    ['colour|color', /^light brown$/i, 'light-brown.jpg'], ['colour|color', /^dark brown$/i, 'dark-brown.jpg'], ['colour|color', /^(grey|dark grey)$/i, 'dark-grey.jpg'],
    ['colour|color', /^light grey$/i, 'light-grey.jpg'],
    // ---- print colour ----
    ['printcolour|print_colour|colour', /^1c\b|black ?(and|&) ?white/i, 'black-white-printing.jpg'],
    ['printcolour|print_colour|colour', /^4c\b|full colou?r/i, 'colorful-printing.jpg'],
    ['side', /single|one side|1 side|front only/i, 'single-sided.jpg'], ['side', /double|two side|2 side|both/i, 'two-sided.jpg'],
    // ---- orientation, hole punching, numbering, perforation, copy change ----
    ['orientation', /portrait/i, 'portrait.jpg'], ['orientation', /landscape/i, 'landscape.jpg'],
    ['hole', /^no|not required/i, 'no-hole-punch.png'], ['hole', /mm|required|yes/i, 'with-hole-punch.png'],
    ['numbering', /required|yes|[1-9]/i, 'Numbering.jpg'],
    ['perforat', /[1-9]|line|required|yes/i, 'Perforating.jpg'],
    ['copy', /^no|not required/i, 'no-copy-change.png'], ['copy', /required|yes|change/i, 'copy-change.png'],
    // ---- lanyard parts ----
    ['', /lobster hook.*semi|semi.?d/i, 'lobster-hooksemi-D.jpg'], ['', /lobster/i, 'lobster-hook.jpg'],
    ['', /oval hook/i, 'oval-hook.jpg'], ['', /crocodile/i, 'crocodile-clip.jpg'], ['', /safety clip/i, 'safety-clip-small.jpg'],
    ['', /friction lock/i, 'friction-lock.jpg'], ['', /slit lock/i, 'slit-lock.jpg'], ['', /buckle/i, 'buckle.jpg'],
    // ---- paper sizes (named); finishing-area sizes (hot stamp, emboss, window) get no picture ----
    ['stamp|hs_|emboss|deboss|window', /./, null],
    ['size', /^a1\b/i, 'A1.jpg'], ['size', /^a2\b/i, 'A2.jpg'], ['size', /^a3\b/i, 'A3.jpg'], ['size', /^a4\b/i, 'A4.jpg'], ['size', /^a5\b/i, 'A5.jpg'],
    ['size', /^a6\b/i, 'A6.jpg'], ['size', /^a7\b/i, 'A7.jpg'], ['size', /^b5\b/i, 'B5.jpg'], ['size', /^dl\b/i, 'DL.jpg'],
    ['size', /^3\s*x\s*a4/i, '3xA4.jpg'], ['size', /^4\s*x\s*a4/i, '4xA4.jpg'], ['size', /^4\s*x\s*a5/i, '4xA5.jpg'], ['size', /^3\s*x\s*a5/i, '3xA5.jpg'],
    ['size', /^2\s*x\s*dl/i, '2xDL.jpg'],
  ];

  // dimension images named "<a>x<b>mm.jpg" (key = long side x short side)
  var DIMS = { '89x54': '89x54mm.jpg', '86x54': '86x54mm.jpg', '86x52': '86x52mm.jpg', '89x50': '89x50mm.jpg',
    '178x54': '54x178mm.jpg', '172x52': '52x172mm.jpg', '172x50': '50x172mm.jpg', '156x52': '52x156mm.jpg',
    '108x89': '89x108mm.jpg', '104x86': '86x104mm.jpg', '100x86': '86x100mm.jpg', '88x86': '86x88mm.jpg',
    '145x105': '105x145mm.jpg', '300x105': '105x300mm.jpg', '190x107': '107x190mm.jpg', '230x120': '120x230mm.jpg',
    '175x125': '125x175mm.jpg', '145x145': '145x145mm.jpg', '210x145': '145x210mm.jpg', '152x152': '152x152.jpg', '280x140': '280x140.jpg',
    '213x55': '55x213mm.jpg', '210x60': '60x210mm.jpg', '140x90': '90x140mm.jpg', '190x90': '90x190mm.jpg', '225x95': '95x225mm.jpg',
    // ISO paper sizes given in mm
    '841x594': 'A1.jpg', '840x594': 'A1.jpg', '594x420': 'A2.jpg', '420x297': 'A3.jpg', '297x210': 'A4.jpg', '210x148': 'A5.jpg',
    '148x105': 'A6.jpg', '105x74': 'A7.jpg', '250x176': 'B5.jpg', '210x99': 'DL.jpg', '220x110': 'DL.jpg',
    '630x297': '3xA4.jpg', '840x297': '4xA4.jpg', '594x210': '4xA5.jpg', '444x210': '3xA5.jpg', '420x210': '2xDL.jpg' };

  function norm(s) { return String(s == null ? '' : s).trim(); }
  function option(fieldKey, value, productId) {
    var k = norm(fieldKey).toLowerCase(), v = norm(value);
    if (!v) return null;
    var pr = (PR[productId] || []).concat(STICKERS[productId] ? STICKER_RULES : []);
    for (var j = 0; j < pr.length; j++) if (new RegExp(pr[j][0], 'i').test(k) && pr[j][1].test(v)) return pr[j][2];
    if (/^(-\s*)?(not required|no required|none|n\/a|no)(\s*-)?$/i.test(v) && !/hole|copy/.test(k)) return null;
    if (/size/.test(k) && !/stamp|hs_|emboss|deboss|window|header|content/.test(k)) {
      var nums = (v.match(/(\d+(?:\.\d+)?)\s*mm/g) || []).map(function (x) { return parseFloat(x); });
      if (nums.length >= 2) { var a = Math.max(nums[0], nums[1]), b = Math.min(nums[0], nums[1]); var d = DIMS[a + 'x' + b]; if (d) return d; }
    }
    for (var i = 0; i < R.length; i++) {
      var r = R[i];
      if (r[0] && !new RegExp(r[0], 'i').test(k)) continue;
      if (r[1].test(v)) return r[2] || null;
    }
    return null;
  }
  var api = { products: P, option: option, base: 'assets/original/' };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.PK_IMAGES = api;
})(typeof window !== 'undefined' ? window : null);
