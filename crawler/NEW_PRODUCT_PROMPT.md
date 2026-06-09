# Printoka — "Add / Reproduce an Excard Product" Prompt

Paste the text below into a fresh Claude Code chat **together with**:
1. the **product spec PDF**,
2. the **artwork spec PDF**, and
3. the **Excard ordering link** (e.g. `https://v4.excard.com.my/ordering/<slug>`).

Then I will run the full build end-to-end against this project.

---

## PROMPT (copy from here)

You are continuing the **Printoka pricing-calculator** project in `crawler/`. Goal:
reproduce an Excard product as our OWN offline, calibrated pricing formula, wired
into the calculator UI, with an honest accuracy audit. Read `crawler/HANDOFF.md`
first for full context and conventions.

I am giving you: the product spec PDF, the artwork spec PDF, and the Excard ordering
link. Build this product following the established pattern. Specifically:

1. **Understand the product.** Extract text from the PDFs (pypdf in the venv) and
   list every option dimension + constraint: sizes, papers (+gsm/material), print
   colour/sides, quantity ladder, packaging (Nin1), and ALL finishing
   (lamination, spot UV, hot stamping, embossing, round corner, hole punch,
   creasing, folding) with their gating rules. Do not miss any combination.

2. **Find the pricing source.**
   - If the link is `v4.excard.com.my/ordering/<slug>`: it's the new platform. Log
     in with account 1 (`app/bizcard_probe.v4_login`), open the form, and capture a
     real `Product/CheckPrice` request (see `app/bizcard_api.py`). The pricing API is
     `POST https://devv2.excard.com.my/Product/CheckPrice` with
     `Authorization: Basic ExcardAPI:EXCARDPNCAPI` + `Api-Key: RjvaNM0xSDxcKyneFhFFxek42Nrnd4FuE9rScoHQ`,
     body `{"type":"<Type>","spec":[{...}]}` → returns `Price` (cash/before-discount),
     `Weight`, `DeliveryFee`. Call it DIRECTLY for sampling (no browser, threaded).
     Learn the form-label→API-value rules (e.g. size `×`→`x`, strip `(...)` from paper).
   - If it's `www.excard.com.my/spec/<Method>/<slug>`: it's the old ASP.NET order
     page. Reuse the browser-driven capture pattern (`app/order_capture.py`,
     `app/booklet_capture.py`) — set the cascade, sweep quantities, read
     "PRICE BEFORE DISCOUNT". Watch for the stale-price quirk (toggle delivery; verify
     a larger qty yields a different price, else re-read/skip).

3. **Sample.** Build `app/<product>_sampler.py`. Sweep a representative grid over
   every option × the full quantity ladder. Package Nin1 is a ×N multiplier (verify,
   don't sample it). Sample finishing as on-vs-base DELTAS. Save
   `output/<product>_samples.json`. Use the API path if available (fast); else crawl.

4. **Build the engine** `app/<product>_engine.py`. Excard offset pricing is step/promo
   (best-seller quantities discounted; odd quantities spike; paper cost is per-MATERIAL
   not ∝gsm). A smooth formula caps ~8–18% — to hit ≤10% use a **per-config quantity
   curve** keyed by the full option combo (`cardType|size|paper|colour|...`) storing
   `{qty: log(cash)}`, log-interpolated for arbitrary quantities, with a nearest-config
   area-scaled fallback. Digital products are nearly flat (a smooth formula is fine).
   Provide `cash_price(...)`, `tiers(cash)` (Cash→Silver −4→Gold −8→Platinum −14),
   `weight_kg(...)` (area_m²×gsm×qty/1000×1.2065).

5. **Delivery** is product-independent: `RM/kg × ceil(weight_kg, min 1)`. Rates:
   West Malaysia 6, East Malaysia 10, Singapore 6, Thailand 6 (RM/kg). Reuse — don't
   re-derive unless the link implies different rates.

6. **Audit honestly** with `app/audit.py` (≥60% of samples, vs Excard ground truth —
   live API if available, else stored samples). Report median, % within 5/10%, and the
   worst configs over 10%. DO NOT fabricate accuracy. Iterate (densify sampling /
   per-config curve / fix structural outliers) until ≤10% on ~all configs, or clearly
   state why a product can't and what's needed.

7. **Wire into the API + both UIs.** Add the product to `PRODUCTS_UI`,
   `FIELD_SCHEMAS`, and `_family()` in `app/api.py`; add its `options` + `quote`
   endpoints; the schema-driven `ui/calculator.html` then renders it automatically.
   Add the same to the standalone build (`app/build_standalone.py` +
   `ui/_standalone_template.html` JS engine port) and run `python -m app.build_standalone`.
   Include the price breakdown (material / printing / finishing / delivery) and the
   feedback box.

8. **Verify in the preview** (`preview_start "printoka-api"`, open `/`) and **update
   `HANDOFF.md`** with the product's state, accuracy, and any gaps.

Work in small verified steps; run long crawls/samplers in the background; never claim
an accuracy number you didn't measure. Tell me honestly what passes ≤10% and what doesn't.

## END PROMPT
