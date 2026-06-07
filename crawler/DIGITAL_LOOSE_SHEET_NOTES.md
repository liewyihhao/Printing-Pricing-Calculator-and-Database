# Digital Loose Sheet (product 50) — gathered options + cost model

Source: live site `/spec/Digital/Loose_Sheet` (digital_options.json) + spec PDF
(pdf_flyer_digital.txt). Print method toggle on the page: **Litho / Digital**.

## Options (complete — exactly Excard)
**Sizes (8):** A3 (297×420), A4 (210×297), A5 (148×210), A6 (105×148), A7 (74×105),
DL (99×210), 2DL (198×210), 310×445.

**Papers (19):** Gloss Art Paper 100/128/150 · Matte Art Paper 100/130/150 ·
Gloss Art Card 230/250/310/360 (2-side coated) · Linen 240 · Synthetic Paper 180µm ·
Super White 240 · Suwen 240 · Vellum 220 (out of stock) · Simili 80/100/140 ·
Metal Ice 250.  *(Fine/specialty cards are digital-only.)*

**Print colour/side:** 1C+0, 1C+1C (≥250pcs), 4C+0, 4C+4C.  1C limited to Simili /
Gloss Art Paper / Gloss Art Card (not Matte/Fine Card per PDF).

**Quantity:** 10→500 (steps), 1000→20000 (steps), Other. **MOQ effectively low
(per-piece), max 20,000** — incremental 1pc. (Same-day ship 1–10,000.)

**Package (ganging):** Normal, 2in1 … 10in1.

**Finishing (same family as offset; "individual — mix not allowed"):**
- Lamination (Gloss/Matt) — ≥250pcs; needs heavier paper variants.
- Folding (1Fa…4Fb), Creasing (1–6 lines, ≥250pcs), Perforation (1–6 lines).
- Hole punching (3/6/8mm). Round corner (R6mm, ≤A4, not with fold/crease).
- Hot stamping (6 foils, max 2, 7 area sizes). Envelope (7 types).

## Cost model — DIGITAL (click-based, NOT plates)
Key difference from offset: **no plates; charged per "click" (impression) per side.**
So cost is ~linear in quantity (more formula-friendly than offset).

    sheets   = ceil(qty / ups[size])            # ups on a digital SRA3 (320×450) press sheet
    clicks   = sheets * sides                    # one click per side per sheet
    cash = margin * ( setup
                      + clicks * click_rate[colour]          # 4C click >> 1C click
                      + sheets * sra3_kg(gsm) * paper_RM[paper]
                      + finishing_addons )
    - ups[A3]=1, A4≈2, A5≈4, A6≈8, A7/DL more (fit/confirm via spot-test)
    - click_rate: 4C ≈ RM0.x per A4-equivalent side; 1C much lower
    - paper_RM per kg by category (Simili/Gloss/Matte/Card/FineCard)
Weight = piece_m2 * gsm * qty / 1000 * factor   (physics, same as offset)

## Calibration plan (no full crawl)
Spot-test via account: sample ~a few hundred Digital prices across size×paper×colour×qty
corners, fit {setup, click_rate[1C/4C], paper_RM[cat], ups[size], margin}, validate on
held-out sample to 3–5%. Digital's linearity should make this achievable.

## Open item
- Digital page has **no visible colour <select>** in the dump — colour mode likely a
  radio that appears after qty/paper, or encoded in another control. Confirm during
  spot-test (the colour values themselves are known from the PDF).
