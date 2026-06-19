# In-Depth Parity Audit — Our Simulation vs Excard (all products)

_Live Excard order-page controls captured via `app/parity_formdump.py`
(`output/parity_<product>.json`), 2026-06. Compares options, sub-options, and prices.
Gaps + fix status below. Pricing tiers everywhere: Cash → Silver −4 → Gold −8 → Platinum −14._

## Summary of gaps found
| Product | Options match? | Gaps to fix |
|---|---|---|
| Business Card (1) | ✅ full | none (lam/SpotUV/round corner/hole punch/hot stamp/emboss/custom/package all present) |
| Loose Litho (21) | ◑ | **Envelope** option (7 sizes). No lamination/finishing on Excard (confirmed). |
| Loose Digital (50) | ◑ | **Envelope** option. (hot stamp/fold/punch already present.) |
| Booklet Litho (19) | ◑ | **Cover Lamination** (10), **Cover Embossing + size** (7), **Hot-stamp size+foil**, **Compulsory Finishing display**, **Jawi** |
| Booklet Digital (37) | ◑ | same as 19 |
| Label Sticker Digital (60) | ◑ | **Hot Stamping** ("HOT STAMPING NEW") — lamination + all 7 cut cats + 13 materials + CD + package already present |
| Label Sticker Letterpress (61) | ✅ full | none (Standard/Round + Gold/Silver hot-stamp = our colour) |
| Packaging Box (all 67) | ✅ full | none (material/colour/coating + stacked add-ons + size + 3D + dieline) |

## Detailed Excard option lists (captured)
### Booklet (19 & 37)
- Orientation (Portrait/Landscape), Size (A4/A5/B5/A6/B5+), Cover type (Soft/Hard), Binding
  (Saddle Stitching+Folding / Perfect Binding), Pages, Cover paper, **Cover Lamination**:
  `Matte Lam (Front/Both)`, `Matte Lam (Front/Both) + Spot UV (Front)`, `Gloss Lam
  (Front/Both)`, `UV Varnish (Front/Both)`, `Gloss Waterbase Varnish (Front/Both)`.
- **Cover Embossing** = Emboss SIZE: `90×30, 90×70, 95×206, 101×144, 144×206, 194×206,
  206×294 mm` (or Not Required). **Cover Hot Stamping** = `1C (Front)` / `2C (Front)` →
  reveals H/S size + foil colour (Gold/Silver/…) per the order page.
- Content paper, Content print colour (1C/4C Both), Outer/Inner (OO/OI), **Jawi content**
  (Yes/No), Quantity, Delivery. **Compulsory Finishing** shown as read-only text
  (Saddle → "Creasing, Saddle Stitching + Folding"; Perfect → its own).
### Loose Sheet (21 & 50)
- Size, Paper, Print colour/side, Package (Nin1), Quantity, **Envelope** (Not Required +
  `108×159 Pink A6, 110×220 White DL, 133×102 Cream A7, 162×114 White A6, 162×229 Pink A5,
  162×229 White A5, 215×114 Pink DL`). Digital(50) also: Hot Stamping, Folding, Hole Punch.
  Litho(21) has NO lamination/hot-stamp/fold/punch (confirmed — only Envelope add-on).
### Sticker Digital (60)
- rdType Sticker/CD, 7 cut categories (incl Multiple Dieline), 13 materials, 4C/1C,
  H×W, Package, Lamination/Finishing, **Hot Stamping ("HOT STAMPING NEW")** ← gap.
### Sticker Letterpress (61)
- Standard Shape/Round, H×W, Hot Stamping colour (Gold/Silver), Quantity. ✅ matches.

## Pricing of added finishing (update)
- **Loose Envelope (21+50): PRICED.** Sampled deltas (`finishing_envelope.json`): Digital is
  linear ~RM0.044/pc; Litho is band-priced (q500 ≈ RM0.029/pc → q1000 ≈ RM0.049/pc). Modelled
  as a per-piece estimate (Pink A6 0.043, White DL 0.049, default 0.046) × qty × package, added
  to the quote + finishing_cost; labelled an estimate (Litho low-qty bands differ). JS==Python.
- **Booklet Cover Lamination (19+37): still 'quoted separately'.** The delta sample
  (`finishing_booklet_lam.json`) was UNUSABLE — the booklet form's cover-print-colour cascade
  is hidden in headless config, so the with-lamination price reads a stale RM130 placeholder.
  Option remains selectable + visible with a separate-quote note; needs a booklet-form config
  fix (set cover colour via the OuterInner radio / JS) before its delta can be sampled.

## Fix plan / status
1. **Loose Envelope** (21+50) — add `envelope` option field; price = additive delta
   (sample) or block note. _(in progress)_
2. **Booklet finishing** (19+37) — add `cover_lamination`, `cover_embossing` (size),
   `jawi`; keep hot-stamp colour-count (size+foil = block "quoted separately"); add
   **Compulsory Finishing** display line driven by binding. Cover lamination has real price
   impact → sample deltas; embossing/hot-stamp = block charge (note), as bizcard does.
3. **Sticker Hot Stamping** (60) — add `hot_stamping` field; price delta sample or block.
4. Update FIELD_SCHEMAS + engines + ui/calculator.html + _standalone_template.html +
   rebuild standalone; verify JS==Python; commit.
