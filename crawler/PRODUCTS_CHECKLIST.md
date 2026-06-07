# Excard Product Catalog & Crawl Checklist

_Generated 2026-06-04 16:24 UTC · 78 products_

Legend: [x] done · [~] in progress · [→] queued next · [ ] not started

**Progress: 0/78 products complete**

## How Excard separates products (organizing principle)

Excard splits its catalog on **print method**, not just product name. The same product
under a different method is a **separate product with its own ID and price list**, reached
via `/spec/<Method>/<slug>` (e.g. `Litho` = Offset, `Digital`). Products that exist under
multiple methods in our list:

| Product | Offset/Litho ID | Digital ID |
|---|---|---|
| Loose Sheet | 21 (`/spec/Litho/Loose_Sheet`, confirmed) | 50 (`/spec/Digital/Loose_Sheet`, confirmed) |
| Booklet | 19 | 37 |
| Business Card | 1 | 27 |

Excard also tags products with soft use-case categories (Business Essentials, Marketing
Materials, Label Sticker & Packaging, Seasonal Products) — most products carry 3–4 of these,
so they are filters, not a strict hierarchy. The hard separators are **method** + product type.

> The full per-product (method + category) map will be captured directly from Excard's own
> menu during the discovery pass, so the catalog and the calculator's product picker mirror
> Excard exactly (choose product → choose method).

## Apparel (7)
| | ID | Product | Structure | Status |
|---|---|---|---|---|
| [ ] | 140 | Corporate Shirt | custom | not_started |
| [ ] | 127 | DTF Shirt | custom | not_started |
| [ ] | 141 | Jacket | custom | not_started |
| [ ] | 119 | Muslimah | custom | not_started |
| [ ] | 84 | Shirt | custom | not_started |
| [ ] | 126 | Silkscreen Shirt | custom | not_started |
| [ ] | 124 | Sweatshirt Hoodies | custom | not_started |

## Bags (4)
| | ID | Product | Structure | Status |
|---|---|---|---|---|
| [ ] | 111 | Canvas Tote Bag | custom | not_started |
| [ ] | 70 | Non-Woven Bag | custom | not_started |
| [ ] | 8 | Paper Bag | custom | not_started |
| [ ] | 133 | rPET Non-Woven Bag | custom | not_started |

## Calendars (6)
| | ID | Product | Structure | Status |
|---|---|---|---|---|
| [ ] | 61 | Desk Calendar (Hard Stand) | custom | not_started |
| [ ] | 60 | Desk Calendar (Soft Stand) | custom | not_started |
| [ ] | 115 | Premium Desk Calendar | custom | not_started |
| [ ] | 106 | Tong Seng Calendar | custom | not_started |
| [ ] | 62 | Wall Calendar | custom | not_started |
| [ ] | 66 | Wire-O Wall Calendar | custom | not_started |

## Drinkware (1)
| | ID | Product | Structure | Status |
|---|---|---|---|---|
| [ ] | 78 | Mug | custom | not_started |

## Large Format (9)
| | ID | Product | Structure | Status |
|---|---|---|---|---|
| [ ] | 112 | Banner | custom | not_started |
| [ ] | 113 | Bunting | custom | not_started |
| [ ] | 121 | Bunting (Gear X Stand) | custom | not_started |
| [ ] | 122 | Bunting (Round Base Stand) | custom | not_started |
| [ ] | 123 | Bunting (Tripod Stand) | custom | not_started |
| [ ] | 132 | Foamboard | custom | not_started |
| [ ] | 131 | POP Display | custom | not_started |
| [ ] | 114 | Roll Up Stand | custom | not_started |
| [ ] | 120 | Wind Flag | custom | not_started |

## Offset Print (24)
| | ID | Product | Structure | Status |
|---|---|---|---|---|
| [ ] | 72 | Arch File | matrix-likely | not_started |
| [ ] | 3 | Bill-Book | matrix-likely | not_started |
| [ ] | 19 | Booklet (Offset) | matrix-likely | not_started |
| [ ] | 37 | Booklet (Digital) | matrix-likely | not_started |
| [ ] | 30 | Bookmark | matrix-likely | not_started |
| [ ] | 1 | Business Card (Offset) | matrix-likely | not_started |
| [ ] | 27 | Business Card (Digital) | matrix-likely | not_started |
| [ ] | 48 | Computer Form | matrix-likely | not_started |
| [ ] | 10 | Envelope | matrix-likely | not_started |
| [ ] | 6 | Folder | matrix-likely | not_started |
| [ ] | 125 | Greeting Card | matrix-likely | not_started |
| [ ] | 94 | Hard Cover Menu | matrix-likely | not_started |
| [ ] | 40 | Kad Kahwin | matrix-likely | not_started |
| [ ] | 44 | Kad Terima Kasih | matrix-likely | not_started |
| [ ] | 65 | L Shape Plastic Folder | matrix-likely | not_started |
| [ ] | 11 | Letterhead | matrix-likely | not_started |
| [~] | 21 | Loose Sheet (Litho/Offset) — `/spec/Litho/Loose_Sheet` | matrix-likely | in_progress (Normal done; ganging 2-5in1 crawling) |
| [→] | 50 | Loose Sheet (Digital) — `/spec/Digital/Loose_Sheet` | matrix-likely | QUEUED NEXT (after ganging) |
| [ ] | 15 | Money Packet | matrix-likely | not_started |
| [ ] | 14 | Notepad | matrix-likely | not_started |
| [ ] | 117 | Perfect Bind Notebook | matrix-likely | not_started |
| [ ] | 26 | Tent Card | matrix-likely | not_started |
| [ ] | 46 | Voucher | matrix-likely | not_started |
| [ ] | 67 | Wire-O Notebook | matrix-likely | not_started |

## Other (1)
| | ID | Product | Structure | Status |
|---|---|---|---|---|
| [ ] | 41 | Kotak Cenderahati | unknown | not_started |

## Packaging (6)
| | ID | Product | Structure | Status |
|---|---|---|---|---|
| [ ] | 128 | 3 Side Seal Packaging | custom | not_started |
| [ ] | 118 | Short Run Packaging | custom | not_started |
| [ ] | 109 | Standing Pouch | custom | not_started |
| [ ] | 130 | Standing Pouch with Spout | custom | not_started |
| [ ] | 91 | Tissue Box | custom | not_started |
| [ ] | 129 | Vacuum Bag Packaging | custom | not_started |

## Plastic Cards (2)
| | ID | Product | Structure | Status |
|---|---|---|---|---|
| [ ] | 134 | ID Card | custom | not_started |
| [ ] | 102 | PVC Card | custom | not_started |

## Promotional (11)
| | ID | Product | Structure | Status |
|---|---|---|---|---|
| [ ] | 68 | Button Badge | custom | not_started |
| [ ] | 63 | Hand Fan | custom | not_started |
| [ ] | 77 | Hanger | custom | not_started |
| [ ] | 83 | Lanyard | custom | not_started |
| [ ] | 95 | Mask Keeper | custom | not_started |
| [ ] | 89 | Memo Box | custom | not_started |
| [ ] | 96 | Papan Kopi | custom | not_started |
| [ ] | 105 | Pillow | custom | not_started |
| [ ] | 76 | Stamp Chop | custom | not_started |
| [ ] | 74 | Wobbler | custom | not_started |
| [ ] | 17 | X-ccessories | custom | not_started |

## Stickers & Labels (7)
| | ID | Product | Structure | Status |
|---|---|---|---|---|
| [ ] | 52 | Label Sticker | custom | not_started |
| [ ] | 110 | Label Sticker with Hot Stamping | custom | not_started |
| [ ] | 82 | Magnet | custom | not_started |
| [ ] | 71 | Multipurpose-Sticker | custom | not_started |
| [ ] | 73 | Roll Form Sticker | custom | not_started |
| [ ] | 64 | Static Cling Window Sticker | custom | not_started |
| [ ] | 116 | UV DTF Sticker | custom | not_started |
