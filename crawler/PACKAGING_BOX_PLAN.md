# Packaging Box — Study & Implementation Plan

_Planning only. Do NOT start building until approved. Decisions locked with the user
on 2026-06-15 (see "Locked decisions")._

## Locked decisions (user)
1. **3D simulation:** TRUE parametric, accurate per box style (dieline that folds into the
   real shape, like Excard) — highest fidelity.
2. **Scope:** ALL ~43 box styles.
3. **Pricing:** OUR OWN calibrated formula (sample Excard, runtime-offline, ~3–5% target —
   same principle as every other product in this project).
4. **Placement:** a NEW "Packaging Boxes" section inside this app (server calculator +
   standalone), separate from the current product picker but same codebase/UI shell.

---

## 1. What Excard has (from study so far)
- **Style catalogue:** `https://www.excard.com.my/packaging-box-style` lists **~43 box
  styles** in ~15 categories: Basic, Window, Hanging, Hanging+Window, Hinged-Lid,
  Trays/Telescopic, Gift/Display, Sleeve, Folder & Envelope, Divider, Inner-Holding,
  Inner-Support, Cardboard, Most-Popular. Each has a code (e.g. `A001X` RTE, `A002X` STE,
  `C001A` Semi-Auto-Bottom-Lock, `D040A` Friction Base+Lid, `E005X` RETF, `K016X` Gable,
  `J023A` Sleeve, `G012` Envelope, `M016` Divider…).
- **Configurator:** each code opens `https://packaging.excard.com.my/uc/diy/<CODE>` — a
  separate **JavaScript SPA** on its own subdomain with **real-time 3D box preview** and a
  **price simulation**. Hash-routed; the structure/options/price all load client-side, so
  static fetch reveals nothing. **Requires a browser + network capture to map.**

### Box-structure families (engineering view — what the 3D must produce)
Most of the 43 reduce to a smaller set of **structural archetypes** (tuck/lock/tray), each
parameterised by W×D×H plus features. The 3D engine should be archetype-based, not 43
one-offs:
- **Tuck-end tubes:** RTE (Reverse Tuck End), STE (Straight Tuck End) — + tongue-lock,
  window-patch, hang-hole, sombrero-hole variants.
- **Auto / semi-auto bottom-lock tubes:** C001 family (+ window / hang variants).
- **Trays & telescopic:** friction base/lid, base-only, lid-only (D007/D030/D040).
- **Hinged-lid / RETF:** E005/E028/E049.
- **Gable / handle, cones, triangles:** K016X, L044, L082.
- **Sleeves, envelopes, dividers, inner-holding/inner-support inserts.**
⇒ ~8–10 parametric archetypes cover all 43; each style = an archetype + feature flags +
default proportions.

---

## 2. What the recon crawl MUST capture (pending — needs the browser)
Run after the Bill-Book sampler frees the single browser. One headless session, read-only:
1. **Catalogue:** scrape all 43 codes + names + category + thumbnail + the canonical
   archetype each maps to. (`packaging_catalogue.json`)
2. **Per-style option schema:** open each `/uc/diy/<CODE>`, capture every control:
   - dimension inputs (W/D/H, min/max, units, step)
   - material/board type + thickness (e.g. art card gsm, corrugated flute)
   - print colour/sides, finishing (lamination/spot-UV/foil/emboss), window film,
     handle/insert options, quantity ladder, packaging.
3. **Pricing API:** capture the XHR/fetch the SPA calls when dimensions/qty change
   (endpoint, headers, request body, response shape). This is the sampling target — the
   analogue of the bizcard `CheckPrice` API or the www order page. Determine: public vs
   login, rate limits, whether price is per-unit/box/sheet.
4. **3D source:** identify the rendering lib (three.js? custom canvas/WebGL?), and whether
   the **dieline geometry** (fold lines, panel dims as f(W,D,H)) is available in JS/JSON —
   if so we can reuse the panel math rather than re-deriving every archetype.
5. **Auth:** confirm whether the packaging subdomain needs a separate login (the main www
   login may not carry over).

Deliverable of recon: `PACKAGING_BOX_FINDINGS.md` + raw JSON dumps, which finalises the
data model and the sampling grid below.

---

## 3. Proposed architecture (mirrors the existing pattern)

### Data / catalogue
- `app/packaging_catalogue.py` + `output/packaging_catalogue.json` — the 43 styles, each:
  `{code, name, category, archetype, features[], dim_ranges, materials[], finishing[],
  qty_ladder}`.

### 3D engine (the new, hard part) — `ui` client-side, three.js
- A small **parametric dieline library** in JS: one builder per archetype that, given
  (W, D, H, board thickness, feature flags), returns panel geometry + fold lines, then
  renders a foldable 3D mesh + an optional flat-dieline view. Print artwork/material shown
  as a texture; window panels as transparent cutouts.
- Goal: visually match Excard closely and be **dimensionally exact** so users judge real
  size (a reference object / ruler like Excard helps).
- Reused identically by the server calculator and the standalone (bundled, no network).
- Effort note: this is the single biggest work item — effectively a 3D sub-project. Phase
  it by archetype (Phase A ships tuck-end + tray; later phases add the rest).

### Pricing engine — `app/packaging_engine.py` (our own formula)
- Packaging price ≈ f(board area of the unfolded dieline × material cost, + die/cutting
  setup amortised over qty, + finishing, + printing) — i.e. a **per-archetype curve keyed
  by (style|material|finishing) over (size, qty)**, log-interpolated, exactly like the
  curve products. Sample via the captured pricing API (fast) or the SPA (slow).
- `cash_price(...)`, `tiers(...)` (Cash→Silver→Gold→Platinum), `weight_kg(...)`
  (dieline area × board gsm), delivery per-kg (reuse existing rates).
- Honest audit with `app/audit.py` (≥60% held-out, ≤10% target).

### Sampling — `app/packaging_sampler.py`
- For each style × representative materials × finishing: sweep a 3D grid of
  (W,D,H) sizes × the qty ladder. Package/finishing as deltas. Resumable, stale-guarded,
  ONE browser/API at a time (same machine constraint). Likely large → sample smart
  (Latin-hypercube over dims + full qty ladder at anchor sizes).

### API — `app/api.py`
- `/api/printoka/packaging/catalogue`, `/packaging/options?code=`, `/packaging/quote?...`.
- New schema family `packaging` in `FIELD_SCHEMAS` + `_family()`; but the 3D preview needs
  a **custom renderer**, so the generic schema UI is extended with a `box3d` field type.

### UI — new "Packaging Boxes" section (server + standalone)
- Style gallery (43 cards by category) → configurator: 3D canvas + dimension sliders +
  option cascade + live price panel + breakdown + delivery + feedback (same shell as the
  current calculator). Standalone bakes in catalogue + params + the three.js bundle.

---

## 4. Phased delivery (proposed)
- **P0 — Recon crawl** (after Bill-Book): map catalogue, per-style options, pricing API, 3D
  source, auth. Produce findings + finalise data model. _(study; low risk)_
- **P1 — Pricing spine, no 3D:** catalogue + options + sampler + engine + API + a basic
  (non-3D) configurator with a size-accurate placeholder preview. Ships real prices for all
  styles. _(reuses the proven product pattern)_
- **P2 — 3D engine, archetype by archetype:** tuck-end + tray first, then lock-bottom,
  hinged-lid, gable/cone/triangle, sleeve/envelope/divider/insert. Each archetype covers
  several styles.
- **P3 — Finishing/material fidelity + standalone bundling + full audit + parity pass** vs
  each Excard DIY page.

## 5. Risks / open questions (to resolve in P0 + with user)
- **3D accuracy bar:** "matches Excard" — exact dieline fold animation, or accurate static
  3D with correct proportions/features? (Affects P2 effort a lot.)
- **Pricing API availability:** if packaging has a clean JSON pricing API (like bizcard v4),
  sampling is fast; if it's only the SPA, sampling is slow (browser, serialized).
- **Material/board model:** corrugated flutes vs folding-carton gsm price very differently;
  need the real material list + costs from recon.
- **Units & min/max** per style; custom vs standard sizes.
- **Standalone size:** bundling three.js + 43 styles + params into one offline HTML — may
  need a JS bundle file alongside (vs the current single-file standalone).

## 6. Effort estimate (rough, post-recon refines it)
- P0 recon: small. P1 pricing spine: medium (proven pattern × 43 styles). P2 parametric
  3D: **large** (the dominant cost). P3 polish/audit: medium.
