# Packaging Box — P0 Recon Findings

_Recon done 2026-06-15 via `app/packaging_recon.py`, `packaging_recon2.py`,
`packaging_globals.py`. Raw dumps in `output/packaging_globals/*.json`,
`output/packaging_recon*.json`, `output/packaging_catalogue.json`._

## TL;DR — this is far more tractable than feared
Excard's packaging site (`packaging.excard.com.my`, the "packmage" engine) exposes
**clean JSON APIs** for pricing AND the 3D dieline geometry, with the **whole product model
in JS globals**. We do NOT have to hand-model 43 boxes or reverse-engineer pricing blind:
- **Pricing:** `POST /uc/GetPriceFactor2` returns exact total/unit price + weight. Public
  (HTTP 200 without login in recon). Callable directly + threaded — like the bizcard v4 API.
- **3D dieline:** `POST /uc/LinTest3D` returns the **parametric dieline** (`LineExp` = fold/
  cut line segments) + panel dims as a function of L/W/D/CAL. Feed into three.js to fold.
- **Catalogue + options + limits:** JS globals `BOXLIB`, `boxTree`, `boxPmsLimit`,
  `Mid4DiyAndOrder` — 67 box defs (43 enabled), 39 categories, per-box dim limits.
- **Delivery:** `POST /uc/GetTranFeeByAreaID` (weight × zone, WeightList/FeeList).
- **3D lib confirmed:** three.js (`window.THREE` present; `<canvas>` renderer).

## The product space
- **67 box definitions** (`BOXLIB.boxes`), 43 enabled on the public style page. Codes:
  `0930, A001, A001A, A001X, A002AX/BX/CX/FX/X, B037, B038, B040A, B042A, B044X, B048A,
  B052A, C001A/AA/AB/AC/AD/AE/AX/AY/B/BX/EX/IX/JX/M/N/NX/QX/RX, C017, D007A, D030, D040A,
  D052A, E005X/Y, E013X, E028A, E043A, E049, G012, J023A, K003, K006, K016/X, K024, L021,
  L044, L069/A, L082, M013/4/5/6, M061-064, T001, Z039A`.
- **39 categories** (`BOXLIB.cates` / `boxTree.cates`): Reverse Tuck, Variant Tuck, Lock
  Bottom Tuck, Trays & Top-Base, Lid Hinged Base w/ Extend Flap, Bag, Folder & Envelope,
  Variant Lock End, Case Box, FEFCO, Gift Box, Display Box, … (maps to the ~8–10 archetypes
  in the plan).
- **Per-box dimension limits** (`boxPmsLimit`): each box has min/range for L, W, D, G(lue
  flap). e.g. `A001X: L≥20, W≥20, D∈[50,300], G=15` (mm).

## Pricing API — `POST https://packaging.excard.com.my/uc/GetPriceFactor2`
Request (form-encoded `boxDiys` = JSON array):
```json
[{"BoxID":"A001X","IsJP":0,"diyIdx":1,
  "BoxPms":"CHOOSE=3,L=120,W=100,D=200,CAL=0.3",
  "Qtys":[300],
  "ProcessJson":"[{\"ID\":\"P001\",\"Pms\":[4,0,0,0,0],\"Materials\":[{\"MID\":\"M0024\",\"SerialNo\":1,\"Pms\":[]}]},{\"ID\":\"P021\"},{\"ID\":\"P051\"}, ...]"}]
```
- `BoxPms`: dimensions in mm — **L**ength, **W**idth, **D**epth, **CAL** = board caliper/
  thickness; `CHOOSE` = a variant selector.
- `ProcessJson`: ordered list of processes — `P001` = printing (`Pms[0]`=colour count, e.g.
  4 = 4C) with a **material** (`MID` e.g. `M0024`); `P021`, `P051`, … = finishing/processes
  (lamination, etc.). Material IDs map via `Mid4DiyAndOrder`.
- `Qtys`: array of order quantities (returns a price per qty).

Response:
```json
{"success":true,"Data":[{"BoxID":"A001X","UnitWeight":0.0522,"NetUnitWeight":0.0359,
  "LstResFee":[{"Qty":300,"TotalFee":1423.95,"UnitFee":4.75,
    "DicParams":{"qty":300,"netarea":1434.8,"area":2086.6,"color":4,"no":17,
                 "price":1.45,"ref":1423.95, ...}}],
  "ProfitRate":1.331}]}
```
⇒ Gives **TotalFee, UnitFee, UnitWeight** directly, plus the cost-driver breakdown
(`netarea`, `area`, `no`=ups, `color`, `price`/unit-area, `ProfitRate`). We can either
curve-fit per box or reconstruct the closed-form (area×price×ups×profit) — our own formula.

## 3D dieline API — `POST /uc/LinTest3D`
Request: `boxid=A001X&boxPms=CHOOSE=3,L=120,W=100,D=200,CAL=0.3&getBoxJson=true&getLineExp=true`
Response: `BoxJson` (OffsetX/Y, Width, Height, Area, NetArea, SolidLength, DashLength, P) +
`LineExp` = array of segments `[type, solid(0)/dash(1)?, x1,y1,x2,y2]` (dash = fold/crease,
solid = cut; arcs encoded too). This is the **flat dieline**; folding it by the crease lines
in three.js reproduces Excard's 3D. Requires a CSRF token (`__RequestVerificationToken`)
captured from the page.

## Delivery — `POST /uc/GetTranFeeByAreaID`
`Weight, AreaID, token → {WeightList:"0.5,10", FeeList:"5.5,0.6,0.6"}` (base + per-kg tiers).
We already have our own per-kg delivery model; can reuse or mirror.

## Auth note
The DIY page and GetPriceFactor2 returned 200 without login in recon, but a
`/acc/Login?isDialog=true` XHR appears (checkout/save needs the packaging-subdomain
account). Pricing/3D sampling appears to NOT need login; confirm during P1 sampling and, if
needed, add a packaging login (separate from the www session).

## Impact on the plan (refines PACKAGING_BOX_PLAN.md)
- **P1 pricing** becomes a **direct-API sampler** (`app/packaging_sampler.py`) calling
  GetPriceFactor2 threaded over (box × dims grid × material × processes × qty ladder) →
  `output/packaging_samples.json`; engine = per-box curve / area-law fit (our formula),
  audited vs the API. Fast (no browser) once the CSRF/token flow is set up.
- **P2 3D** uses LinTest3D dieline output (capture `LineExp` per box at sample dims, or
  re-derive the parametric panel math) → a three.js folding renderer. Dimensionally exact
  by construction.
- **Catalogue/options** come straight from the dumped globals (`packaging_catalogue.json` +
  `boxPmsLimit` + the process/material lists) — no scraping per box.
- **Open items for P1 start:** decode `Mid4DiyAndOrder` materials + the full process list
  (P0xx IDs) and which apply per box (parse `BOXLIB.boxes[].src` / per-box process menus);
  capture the token flow for the two APIs; confirm no-login pricing holds under load.
