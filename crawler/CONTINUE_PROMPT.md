# Printoka — Continue-in-new-session prompt

Paste everything in the ``` block below into a fresh Claude Code chat (run from the
`Printoka.com` repo root, branch `feat/business-card-standalone-calculator`).

```
Continue the Printoka pricing-calculator project. FIRST read crawler/HANDOFF.md (full
context) and crawler/NEW_PRODUCT_PROMPT.md (the reusable add-a-product workflow).

State: 7 products are live and on PR #1
(github.com/liewyihhao/Printing-Pricing-Calculator-and-Database, branch
feat/business-card-standalone-calculator): Business Card (1), Loose Sheet Litho (21),
Loose Sheet Digital (50), Booklet Litho (19), Booklet Digital (37), Label Sticker
Digital (60), Label Sticker Letterpress (61). Each has a pure-formula/curve engine in
crawler/app/*_engine.py + params in crawler/output/*.json (output/ is gitignored;
small params/curves are force-added). Two UIs, kept in sync and JS-verified == Python:
  - server calculator: crawler/ui/calculator.html via `cd crawler && .venv\Scripts\python.exe -m uvicorn app.api:app --port 8000` (calculator at /, dashboard at /dashboard)
  - standalone (no server): crawler/ui/calculator_standalone.html, rebuilt by
    `python -m app.build_standalone` from ui/_standalone_template.html. ALWAYS rebuild
    after changing any engine/params, and verify JS==Python with node by extracting the
    script up to "// ---------- UI ----------" and calling localQuote.
Pricing: discrete-option products use per-config Excard curves (exact at breakpoints);
Label Sticker uses an imposition formula; Business Card uses the v4 API
(devv2.excard.com.my/Product/CheckPrice, Basic ExcardAPI:EXCARDPNCAPI). Delivery =
per-kg (W.MY/SG/TH RM6, E.MY RM10) × ceil(weight). Finishing add-ons are sampled as
deltas and wired as schema "addon" fields; the generic UI supports addon + number +
optional fields.

ONE open task (#18) — full Excard ordering-page parity. DO NOT split it; DO NOT mark it
complete until every product's UI matches its Excard order page in completeness.
Remaining items only:
  1. Label Sticker "Multiple Dieline" cut category — sheet-based multi-design: controls
     ddlCutToSheet (A3+/A4/A5) + ddlSheetQty (10,20,30,... sheets) + ddlfinishing. It is
     priced by NUMBER OF SHEETS, not pieces. I was sampling it into
     output/sticker_multidieline.json (may be partial/missing) when interrupted. Finish:
     sample price by (sheet size × sheet qty), build a model (new category in
     app/sticker_categories.py treating the qty input as sheet count + a sheet-size
     field), wire into the digital sticker schema + quote + standalone, verify.
  2. Warranty / Synthetic premium sticker materials price ~20–40% off (the imposition
     model can't capture their distinct cost structure) — improve with a per-material
     model or accept + document. Not a missing control.
Everything else on every Excard order page (sizes/custom-size, materials, colour,
package, delivery, and all finishing incl. sticker lamination + all 6 standard cut
categories) is already present and priced.

Working notes that bite: the www sticker form's fold/category radios are HIDDEN — set
via JS el.click() / set select value + dispatchEvent('change'), not Playwright .check().
Two browsers starve on this one machine — run ONE www crawl at a time, in the background,
resumable. Login: app/accounts.get(1) (yushancorporation), www via app/browser.login,
v4 via app/bizcard_probe.v4_login. Commit incrementally to the PR; force-add only small
output/*.json (params/curves/finishing), never the large *_samples_*.json. Be honest
about accuracy — never claim a number you didn't measure; run app/audit.py for real
≥60% checks.

Continue with item 1 (Multiple Dieline). Don't ask to proceed — just keep going and
report progress; close #18 only after a side-by-side check vs each Excard order page.
```
