# CONTINUE: Exact rebuild from v4 price-lists

_Read this first when resuming. Branch `feat/business-card-standalone-calculator`,
work in `crawler/`, venv `.venv\Scripts\python.exe`._
_Shell gotcha: prefix every command with `cd /c/Users/User/OneDrive/Desktop/Printoka.com/crawler &&`._

## What this task is

The 43 built products were calibrated by **sampling the old www `/spec/` forms**. An audit against
the **authoritative v4 price-list pages** (`https://v4.excard.com.my/price-list/<slug>`) proved that
**option selects silently failed during the original sampling**, so several priced options were
recorded at the base price and wrongly modelled as "no price change / quoted separately".
We are **rebuilding affected products EXACTLY from the v4 price-list data** (no interpolation error,
no missed options).

## ROOT CAUSE (confirmed)

Original samplers sometimes read the price BEFORE the option select actually applied → recorded the
base price → false "neutral" conclusion. Examples found: Notepad Spot UV, Folder print-colour /
Document-Key-CD mould groups / Spot UV, Letterhead Pad packing. Every `"no price change"` /
`"quoted separately"` claim across products must be re-checked against the v4 price-list.

## DONE so far (committed + pushed)

- **`app/pricelist_engine.py`** — generic EXACT lookup engine. `build_params(tag, axis_cols)` parses
  `output/v4_pricelists/<tag>.csv` (drops the DataTables junk filter row), keys curves by
  `"|".join(axis values)` → `{qty: WM_price}`, log-log qty interp. `cash_price(params, config_dict, qty)`.
- **Generic `"pricelist"` JS branch** in `ui/_standalone_template.html`: product dict carries
  `engine:"pricelist"`, `paramKey`, `axisFields:[field keys in axis order]`; builds the key from the
  selected field values and interpolates. `_pl_params(tag)` loader added in `api.py`.
- **Notepad (104) FIXED** — Spot UV is priced (+RM22@250 … +RM726@20000); paper 260/310gsm confirmed
  genuinely neutral. (engine delta, not full lookup.)
- **Folder (107) REBUILT EXACT** from `folder.csv` (9265 rows → 692 config curves). Axes:
  Model(11, all groups) × Paper(8) × Print Colour(4C Front/Both) × Lamination(8 incl Spot UV) ×
  Colour Protective Layer(N/A / Gloss Waterbase Varnish Back). JS==Python verified vs live price-list.
- **Letterhead (105) REBUILT EXACT** from `letterhead.csv`. Axes: Paper(6) × Print Colour
  (1C/2C/4C Front, 4C Both) × Packing(Loose / Pad 100pcs). **Pad packing** was the missed priced
  axis. paramKey `letterhead`. JS==Python exact (maxdiff 0 / 336 cases).
- **PVC Card (113) REBUILT EXACT** from `pvc_card.csv`. Axes: Print Colour(4C Front/Both) × Hole
  Punch × VDP — **Hole Punch + VDP are PRICED** (old model treated them as separate/neutral).
  Orientation/size confirmed price-neutral. paramKey `pvccard` (note tag≠csv: built with
  `csv_name='pvc_card.csv'`). JS==Python exact (maxdiff 0 / 128 cases).
- **Money Packet (138) NEW PRODUCT, EXACT** from `money_packet_standard.csv`. Axes:
  Model(MP 101/103/104) × Package(Normal/Dual/5/6 Design) × Paper × Finishing. Packing method
  price-neutral. JS==Python exact (maxdiff 0 / 273 cases). NOTE: only the **Standard** category is
  built — the other 3 Money-Packet categories (Hot Stamping / Premium / Packaging) still need CSV
  export + a multi-category lookup.

## BROWSER STATUS (2026-06-25 session)

Chrome extension `Browser 1` (deviceId 104892cb-…) is paired and `tabs_context_mcp` responds, but
**`navigate` and `computer` both hang for the full 300s timeout** and the tab never leaves
`chrome://newtab` — the extension's navigate/CDP path is wedged. Could not export any new CSVs this
session. **Next session: ask the user to reload/re-pair the Chrome extension (or restart Chrome)
before attempting browser exports.** All 4 products above were built from CSVs already on disk.

## THE PIPELINE (repeat per product)

1. **Get the CSV**: open `https://v4.excard.com.my/price-list/<slug>` in the connected Chrome
   (extension), wait ~7s for the async "Loading In Progress" table to clear, click the **CSV** button
   (top-left, ~`(291,264)` at the default viewport). **One product per browser_batch** — a following
   navigation cancels an in-flight download. Downloads land in `C:\Users\User\Downloads\` (the user
   enabled automatic downloads for `v4.excard.com.my`). Copy into `output/v4_pricelists/<tag>.csv`.
   - **DataTable price-lists** have the CSV button (notepad, letterhead, pvc-card, folder, money-packet,
     bookmark, and most simple products).
   - **Generate-form price-lists** (title `"<X> - Price List"`: business-card, bill-book,
     kad-terima-kasih, envelope, …) have NO top CSV — you must select options + **Generate** first,
     then the generated table exposes CSV. These are harder; handle per high-level choice.
2. **Inspect axes**: read the CSV header + distinct values per column to pick `axis_cols`
   (drop fixed/Compulsory columns and Size when implied by Model).
3. **Build**: `PE.build_params("<tag>", [axis cols], note="…")` → writes `output/<tag>_pl_params.json`.
4. **Wire** (mirror Folder):
   - `build_standalone.py`: product dict `engine:"pricelist", paramKey:"<tag>", axisFields:[...]`,
     `fields:[...]` with the EXACT CSV option strings; load `"<tag>": _load("<tag>_pl_params.json", …)`.
   - `api.py`: rewrite the `<tag>_quote` endpoint to `PE.cash_price(_pl_params("<tag>"), cfg, qty)`,
     and update the `FIELD_SCHEMAS` fields + `FORMULATED[id]=0.0`.
   - JS branch is already generic — nothing to add.
5. **Verify**: `python -m app.build_standalone`, then node-vs-python check on `<tag>_pl_params.json`
   (must be exact). Commit small `output/*_pl_params.json` (force-add) + code; never the `*_samples_*`.

## NEXT UP (needs browser CSV export — blocked until extension is un-wedged)

- **Money Packet** — export the other 3 categories (Hot Stamping / Premium / Packaging), extend the
  `money_packet` lookup to a multi-category model (add a Category axis or per-category param files).
- **Mask Keeper** and **Non-Woven Bag** — new v4 products, build fresh via the same lookup approach.
- Letterhead(105), PVC Card(113), Money Packet-Standard(138) are DONE (see above).

## STILL TO AUDIT/REBUILD (re-verify every neutral/separate claim vs v4 price-list)

bizcard(1) hot-stamping/surface/embossing • loose(21)/loose_digital(50) addons • booklet(19/37)
embossing/hot-stamping • billbook(24) **Normal Paper** (engine is NCR-only) + numbering •
computerform(111) numbering/copychange • voucher(110) numbering • wireo(112) lamination/hot-stamping •
kadkahwin(114)/kadterima(115) lamination (claimed neutral — RE-VERIFY) • envelope(106) models/paper •
lshape(108) • stickers(60/61) • and spot-check the simple qty products (wall-calendar, banner, mug,
desk-calendars, etc.) for any hidden priced option.
NOTE: slugs differ sometimes (wire-o-notebook / booklet / loose-sheet / voucher returned Runtime Error
or empty — confirm the real `/price-list/<slug>` from each product's ordering-page "Price List" button).

## Browser access

Chrome extension is paired (`mcp__Claude_in_Chrome__*`); the user is logged into v4 as account
142059498. `select_browser` the connected device, `tabs_context_mcp{createIfEmpty:true}`, then drive.
WM Price = the price to model (EM = East-Malaysia shipping variant, ignore).
