# Printoka vs Excard — price comparison (purchaser audit)

_Generated 2026-06-25. Ground truth = Excard's authoritative v4 price-list CSV exports
(`output/v4_pricelists/*.csv`), which are Excard's live online "WM Price". Our calculator
prices via `app/pricelist_engine.cash_price` on the baked params — the exact code path the
standalone UI and the API both use._

Reproduce: `.venv\Scripts\python.exe -m app.compare_excard`

## How the comparison is framed

For **exact (price-list lookup) products**, our **Cash price *is* Excard's online price** — we model
Excard's WM Price directly, so there is no discrepancy at any listed configuration/quantity. The
Printoka value-add is the **membership tier discount** below that list price (Silver −4 %, Gold −8 %,
Platinum −14 %). The redesigned UI now shows this explicitly: an "Excard online price" line plus
"You save (Platinum)".

For **formula products** (still calibrated from the old `/spec` sampling), the Cash price is an
*estimate* of Excard's, carried with a published `±% vs Excard` accuracy badge.

## Result — exact products (walked every row of each price-list)

| Product | Excard rows checked | Exact-to-the-cent | Median \|err\| | Max \|err\| |
|---|--:|--:|--:|--:|
| Letterhead (105) | 466 | **100.0 %** | 0.0000 % | 0.0000 % |
| PVC Card (113) | 528 | **100.0 %** | 0.0000 % | 0.0000 % |
| Money Packet (138, Standard) | 495 | **100.0 %** | 0.0000 % | 0.0000 % |
| Folder (107) | 9 264 | 87.0 % | 0.0000 % | 8.83 % |

### Worked purchaser examples (our price vs Excard online)

| Product | Spec | Qty | Excard | Ours | Match |
|---|---|--:|--:|--:|:--:|
| Letterhead | Simili 80gsm · 1C Front · Loose | 1 000 | RM 123.40 | RM 123.40 | ✅ exact |
| PVC Card | 4C Front · no punch · no VDP | 500 | RM 416.00 | RM 416.00 | ✅ exact |
| PVC Card | 4C Both · Hole Punch · VDP Both | 1 000 | RM 1 096.00 | RM 1 096.00 | ✅ exact |
| Folder (Presentation) | FPF 001 · GAC 300 1S · 4C Front · Gloss Lam | 500 | RM 1 007.10 | RM 1 007.10 | ✅ exact |
| Letterhead | Conqueror White Wove · 4C Both · Pad | 1 000 | RM 418.65 | RM 418.65 | ✅ exact |

At every quantity Excard actually lists, we match **to the cent**. Between listed quantities we
log-log interpolate Excard's own breakpoints.

## Specs / customization parity (what the old sampling got wrong)

The rebuild fixed silently-mispriced options that the old `/spec` sampler had recorded as
"no price change / quoted separately":

- **Letterhead** — **Packing (Pad, 100 pcs/pad)** is a real priced axis (was missing entirely).
- **PVC Card** — **Hole Punching** and **Variable Data Printing** are both **priced** (were modelled
  as free / separate). Orientation & size confirmed genuinely price-neutral.
- **Folder** — all mould groups, every lamination incl. Spot UV, and the back colour-protective
  layer are now priced exactly.

## Known gap

- **Folder → CD Jacket category (13 % of folder rows):** Excard's exported CSV contains rows with
  byte-identical visible specs but two different prices (e.g. RM 868.00 vs RM 937.65 for the same
  spec). There is a **hidden option dimension Excard did not export as a column** (median spread
  +2.4 %, up to +8.8 %). Presentation / Document / Key folder categories are exact. Resolving CD
  Jacket needs the v4 generate-form to reveal the hidden option — pending the Chrome extension.

## Not yet re-verified against v4 (still on old `/spec` calibration)

Business Card hot-stamping, Bill-Book Normal Paper + numbering, Wire-O / Kad Kahwin / Kad Terima
laminations, Voucher / Computer-Form numbering, and the simple qty products. These still carry their
`±% vs Excard` estimate badge and are the queue for the next CSV-export pass.
