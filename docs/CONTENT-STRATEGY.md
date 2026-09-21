# Printoka Content Strategy

A content plan for the whole project: what each page type must rank for, how to keep every page unique, where the gaps are, and the order to fill them.

---

## 1. Business and audience

**Business:** Printoka is an online printing marketplace for Malaysia, Singapore and Brunei (with AU/NZ landing pages). 93 priced products across 8 categories, instant online pricing, membership discounts, nationwide delivery.

**Primary buyers**
- **SME owners and marketers** ordering business cards, flyers, stickers, packaging. Buying intent, price-sensitive, want it fast.
- **Event and retail** buyers ordering banners, buntings, packaging, apparel.
- **Designers and print buyers** who need artwork specs before they commit.

**Search intent split:** ~60% transactional/commercial ("business card printing", "sticker printing Penang"), ~40% informational ("what is spot UV", "flyer size guide").

---

## 2. Per-page SEO objective and uniqueness rule (the core of this plan)

Every page type has ONE objective and ONE rule to stay unique. This is where duplicate content is created or avoided.

| Page type | Count | Objective (rank for) | Uniqueness rule |
|---|---|---|---|
| **Home** | 1 | Brand + "online printing Malaysia/Singapore/Brunei" | One-off; already unique. |
| **Category** | 8 | Head terms: "sticker printing", "business card printing", "packaging boxes" | Unique 2-3 paragraph intro per category (done); list the real products; no boilerplate reuse. |
| **Product** | 93 | Product + spec: "PVC card printing", "roll label printing" | **RISK: templated `productSeo` is near-duplicate.** Fix: each product needs its own use-cases, spec notes, and 3 product-specific FAQs (not name-swapped boilerplate). |
| **City landing** | 479 | Local: "sticker printing Ipoh" | **HIGHEST RISK: shared template, city swapped = doorway pages.** Fix below (§4). |
| **Blog / Learning Hub** | 29 | Informational + commercial guides | Each targets one keyword; already unique. Keep it that way. |

**Rule of thumb:** if two pages differ only by a swapped noun, Google treats them as one. Product and city pages are where this happens.

---

## 3. Topical authority map

```
PILLAR: Online printing (home + /products)
├── CLUSTER: Business cards & essentials (14 products)
│   ├── Product pages: Business Card, PVC Card, Name Card Holder, Letterhead…
│   ├── Guide: Business Card Printing in Malaysia (LIVE)
│   ├── Guide: Folded, PVC and die-cut card types (GAP)
│   └── Guide: What to put on a business card (GAP)
├── CLUSTER: Stickers & labels (8 products)
│   ├── Product pages: Label Sticker, Roll Label, Car Sticker, UV DTF…
│   ├── Guide: Custom Sticker & Label Printing (LIVE)
│   └── Guide: Which sticker material for your use case (GAP)
├── CLUSTER: Flyers & leaflets (5 products)
│   ├── Guide: Flyer & Brochure Printing (LIVE)
│   └── Guide: Flyer distribution that works (GAP)
├── CLUSTER: Packaging & boxes (11 products)
│   ├── Guide: Custom Packaging Boxes (LIVE)
│   └── Guide: Box style picker by product type (GAP)
├── CLUSTER: Books & stationery (11 products)  → Booklet/notebook guides (GAP)
├── CLUSTER: Cards & invitations (10 products)  → Wedding/greeting card guides (GAP)
├── CLUSTER: Large format (13 products)  → Banner/bunting/roll-up guides (GAP)
├── CLUSTER: Apparel & gifts (21 products)  → T-shirt/tote/mug printing guides (GAP)
└── SUPPORTING: Artwork & finishing (22 existing guides) → already strong
    └── Cross-links into every product/configurator
```

---

## 4. Content gap analysis (prioritised)

**A. Fix the duplicate-content risk first (protects everything else)**
1. **City landing pages (479).** They are the biggest liability. Options, best first:
   - **Prune + specialise:** keep one landing page per service per *major* city (KL, PJ, Penang, JB, Ipoh, Kuching, Miri, Singapore, plus one national page per country). Give each a genuinely local intro (delivery time to that city, local pickup, a local use-case). `noindex` the long-tail small-town duplicates or 301 them to the national page.
   - If you keep all 479, they must each get a unique local paragraph; otherwise Google may treat them as doorway pages and discount the lot.
2. **Product pages (93).** Replace the name-swapped `productSeo` template with per-product content: 2 lines on what it is and who buys it, its real spec highlights, and 3 product-specific FAQs. The specs already differ per product, so lean on those.

**B. Content gaps (new articles to build)**
- Missing **commercial guides** for: large format (banners/buntings/roll-ups), apparel (t-shirts/totes/mugs), booklets, wedding/greeting cards, calendars.
- Missing **landing-page services**: business card, banner, apparel, mug (city pages exist for stickers/flyers/booklets/packaging only).
- **Comparison/decision content** (high commercial value): "Digital vs offset printing", "Which paper weight for X", "Sticker vs label", "Matte vs gloss lamination".

**C. Strengths to keep**
- 22 artwork/finishing guides = strong informational authority. Keep them cross-linked into the configurator's artwork tab.

---

## 5. Search intent mapping

| Keyword example | Intent | Page that should win |
|---|---|---|
| "business card printing" | Commercial | Category / product page + guide |
| "business card printing kuala lumpur" | Local | Curated city landing page |
| "what is spot uv" | Informational | Blog guide (exists) |
| "digital vs offset printing" | Commercial/compare | New comparison guide |
| "buy pvc card" | Transactional | Product page |
| "flyer size guide" | Informational | Blog guide (exists) |

Match format to intent. Never point a transactional keyword at a blog post, or an informational keyword at a bare product page.

---

## 6. Priority content queue

| # | Title | Keyword | Intent | Priority | Words |
|---|---|---|---|---|---|
| 1 | Per-product content template (all 93) | product + spec | Commercial | **Big bet** (fixes dup risk) | 150-300 each |
| 2 | City-page specialise/prune plan | local | Local | **Big bet** | n/a (systems) |
| 3 | Banner & Bunting Printing Guide | banner printing | Commercial | Quick win | 900 |
| 4 | Custom T-Shirt & Apparel Printing | t-shirt printing | Commercial | Quick win | 900 |
| 5 | Digital vs Offset Printing | digital vs offset | Compare | Quick win | 1000 |
| 6 | Booklet & Catalogue Printing Guide | booklet printing | Commercial | Quick win | 900 |
| 7 | Wedding & Greeting Card Printing | wedding card printing | Commercial | Quick win | 900 |
| 8 | Matte vs Gloss Lamination | lamination types | Compare | Fill-in | 700 |
| 9 | Paper Weight (GSM) Guide | gsm paper guide | Info | Fill-in | 800 |
| 10 | Calendar Printing Guide | calendar printing | Commercial | Fill-in | 800 |

---

## 7. Content calendar (12 weeks)

**Month 1 — Fix the foundation (protect existing pages)**
- Week 1: Ship the per-product content template; rewrite the top 20 product pages.
- Week 2: City-page audit; pick the ~40 keeper cities, noindex/301 the rest.
- Week 3: Banner & Bunting guide + rewrite next 20 product pages.
- Week 4: Apparel guide + next 20 product pages.

**Month 2 — Expand commercial coverage**
- Week 5: Digital vs Offset comparison.
- Week 6: Booklet & Catalogue guide.
- Week 7: Wedding & Greeting Card guide.
- Week 8: Finish product-page rewrites (final 33).

**Month 3 — Depth and decision content**
- Week 9: Matte vs Gloss Lamination.
- Week 10: Paper Weight (GSM) guide.
- Week 11: Calendar Printing guide.
- Week 12: Add business-card and banner city landing pages for the keeper cities.

Cadence: 1-2 pieces/week is realistic; the product-page rewrites run in parallel as a batch.

---

## 8. Internal linking plan

- **Guides → products:** every commercial guide links to its category and 2-3 named products (the 5 live guides already do this).
- **Products → guides:** each product page links to its buying guide and the relevant artwork guide.
- **Category → guide + top products:** each category page links to its pillar guide and its best sellers.
- **City page → national service page → category:** keep local pages one hop from the category, never orphaned.
- **Artwork guides → configurator:** link every finishing guide to the product's artwork tab.
- Keep a flat depth: home → category → product ≤ 2 clicks; every published guide reachable from the Learning Hub and from at least one product.

---

## 9. Success metrics

- **Organic traffic:** +30% in 90 days, driven by the commercial guides and de-duplicated product pages.
- **Indexation health:** the share of indexed pages that are unique should rise; watch for "Crawled, not indexed" on the city pages (the doorway signal).
- **Rankings to track:** "business card printing", "sticker printing malaysia", "custom packaging boxes", "flyer printing", plus 5 local terms for keeper cities.
- **Production KPIs:** 93 product pages de-templated, ~40 city pages specialised, 8 new commercial guides shipped in 12 weeks.
- **Engagement:** guide → configurator click-through, and configured-price events from guide traffic.

---

## 10. What is already done (baseline)
- 8 category pages with unique intros; 93 product pages (templated, to de-dup); 479 city landing pages (to specialise/prune); 29 blog guides (22 artwork + 5 new commercial, all unique); per-route titles/meta/canonical/OG/JSON-LD; sitemap with product + category + blog URLs.
