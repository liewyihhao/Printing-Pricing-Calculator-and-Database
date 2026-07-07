# Printoka Calculator — Product Status Checklist

_Generated 2026-07-04. 93 products._

## ✅ EXACT — cent-accurate (73)
- [x] `104` Notepad — Litho
- [x] `107` Folder — Litho
- [x] `108` L-Shape Plastic Folder — Digital
- [x] `118` Wall Calendar — Litho
- [x] `119` Arch File — Digital
- [x] `120` Desk Calendar — Hard Stand (Litho)
- [x] `121` Desk Calendar — Soft Stand (Litho)
- [x] `122` Wire-O Wall Calendar — Litho
- [x] `123` Banner — Litho
- [x] `124` Bunting — Litho
- [x] `125` Roll-Up Stand — Litho
- [x] `126` Wobbler — Digital
- [x] `127` Paper Bag — Litho
- [x] `128` Canvas Tote Bag — Litho
- [x] `129` Mug — Litho
- [x] `130` Papan Kopi / Sachet Board — Litho
- [x] `132` Button Badge — Digital
- [x] `133` Hand Fan — Digital
- [x] `134` Hanger — Digital
- [x] `136` Hard Cover Menu — Digital
- [x] `137` Standing Pouch — Litho
- [x] `138` Money Packet — Litho
- [x] `139` Non-Woven Bag — Litho
- [x] `140` Tent Card — Litho
- [x] `141` Stamp Chop
- [x] `143` Sublimation Shirt
- [x] `144` Cooler Bag — Litho
- [x] `145` DTF Tote Bag With Zip — Litho
- [x] `146` Heat Transfer Tote Bag — Litho
- [x] `147` Laminated Non-Woven Bag — Litho
- [x] `148` RPET Non-Woven Bag — Litho
- [x] `149` Toast Bag — Litho
- [x] `150` 3-Side Seal Packaging — Litho
- [x] `151` Kraft Standing Pouch — Litho
- [x] `152` Standing Pouch with Spout — Litho
- [x] `153` Vacuum Bag Packaging — Litho
- [x] `154` Foamboard — Digital
- [x] `155` Foamboard with Magnet — Digital
- [x] `156` Foldable POP Display — Digital
- [x] `157` POP Display — Digital
- [x] `158` Wind Flag — Digital
- [x] `159` Economy Roll-Up Stand — Digital
- [x] `160` Bunting — Gear X Stand
- [x] `161` Bunting — Round Base Stand
- [x] `162` Bunting — Tripod Stand
- [x] `163` Exclusive Leather Cover Wire-O Notebook — Litho
- [x] `164` Hard Cover Perfect Bind Notebook — Litho
- [x] `165` Creative Cut Card — Digital
- [x] `166` Greeting Card — Litho
- [x] `167` Premium Money Packet — Litho
- [x] `168` Hot Stamping Money Packet — Litho
- [x] `169` Envelope Money Packet — Litho
- [x] `174` Lanyard — Litho
- [x] `175` Premium Desk Calendar — Litho
- [x] `176` UV DTF Sticker — Digital
- [x] `177` Food Tray — Litho
- [x] `178` Kraft Paper Bag — Litho
- [x] `179` Kotak Cenderahati — Litho
- [x] `180` Corporate Shirt — Digital
- [x] `181` Jacket — Digital
- [x] `182` Muslimah Sublimation — Digital
- [x] `183` Sweatshirt & Hoodies — Digital
- [x] `185` Cap — DTF
- [x] `116` Static Cling Window Sticker — Digital
- [x] `117` Car Sticker — Digital (= Static Cling form)
- [x] `113` PVC Card — Digital
- [x] `106` Envelope — Litho
- [x] `109` Bookmark — Digital
- [x] `105` Letterhead — Litho
- [x] `21` Loose Sheet — Litho (Offset)
- [x] `101` Brochure (= Loose Sheet Litho)
- [x] `102` Flyer (= Loose Sheet Litho)
- [x] `103` Customprint (= Loose Sheet Litho)

## ✅ EXACT — completed this session (2026-07-06/07)
- [x] `24` Bill-Book — Litho (NCR) — EXACT via CheckPrice (2662 curves, workers=2 + repair)
- [x] `135` Magnet — Digital — EXACT via CheckPrice (Shape×Size; Custom Die-Cut=Rect, Round size-neutral)
- [x] `1`  Business Card — **corrected**: was ~58% underpriced (workers=30 corruption); re-sampled clean
- [x] `114` Kad Kahwin — **corrected**: re-sampled workers=1 + repair
- [x] `115` Kad Terima Kasih — **corrected**: re-enumerated workers=2, merged max-of-two-passes

> ⚠️ **CheckPrice concurrency bug (fixed):** devv2 /Product/CheckPrice keeps ONE order-session
> per account cookie, so concurrent calls underprice (~0.787×). All samplers lowered to
> workers≤2 + Theil-Sen repair. banner/paper-bag (pricelist-DataTable), the readymade
> shirts/cap (UI-driven), and wire-o-notebook (local price column) were verified NOT affected.

## 🟡 REFERENCE — calibrated formula (<5% for most); cent-exact currently BLOCKED
_v4 `/ordering` + `/price-list` pages return HTTP 500 (booklet, loose-sheet, magnet-pricelist)
or a JS error (computer-form); the legacy www `/spec` forms price server-side (no CheckPrice),
so the fast API is unavailable and a full exact www crawl is impractical (tens of thousands of
~1.5s ASP.NET postbacks). Direct-API `type`/spec could not be reverse-engineered blind. These
keep their calibrated formulas at the accuracy shown._
- [ ] `19` Booklet — Litho (Offset)  · formula ~0.5%
- [ ] `37` Booklet — Digital          · formula ~1.6%
- [ ] `50` Loose Sheet — Digital      · formula ~1.3%
- [ ] `111` Computer Form — Litho (NCR) · formula ~4.0%
- [ ] `131` Pillow — Litho             · formula (acc≈0)

## 🟡 FORMULA — continuous label size (imposition); cent-exact impractical by design
_Priced by arbitrary label W×H → imposition formula. Recalibrated on clean workers=2 CheckPrice
data; fit caps at the model's error (not the data's)._
- [ ] `60` Label Sticker — Digital     · imposition formula ~6% (median 4.2%)
- [ ] `61` Label Sticker — Letterpress · imposition formula ~10%

## 🔴 CONTACT — no online auto price
- [ ] `142` Mask Keeper — Litho        · no v4 price engine
- [ ] `170` ID Card — Digital          · needs a VDP template chosen to price
- [ ] `171` X-ccessories — Litho       · bulk multi-item builder (non-enumerable)
- [ ] `184` Roll Form Sticker — Litho  · v4 page works (type='Roll Form Sticker') but continuous size → would need a new imposition engine
