# Printoka Pricing API

A standalone pricing service so external websites can use the Printoka calculator as a shared
**catalog + pricing database**. It serves the same products, customization options, valid-combination
rules, and prices as the calculator (single source of truth).

## Run

```bash
# 1. (re)build the catalog + engine artifacts
python -m app.build_standalone        # emits output/calculator_data.json + output/calculator_engine.cjs

# 2. start the API (needs Python deps + Node.js installed)
uvicorn app.public_api:app --host 0.0.0.0 --port 8020
```

Interactive docs: `http://<host>:8020/docs`. CORS is open (any website can call it).

## Endpoints

### `GET /api/v1/health`
`{ "status": "ok", "products": 51 }`

### `GET /api/v1/products`
List the catalog. Optional filters: `?category=Cards%20%26%20Stationery`, `?pricing_type=exact`.
```json
{ "count": 51, "products": [
  { "id": 105, "name": "Letterhead — Litho", "category": "Cards & Stationery", "pricing_type": "exact" }
]}
```
`pricing_type`: `exact` (matches the market price), `reference` (~5–10% above market), or `contact`.

### `GET /api/v1/products/{id}`
Full configuration schema for one product — render your own configurator from this.
```json
{
  "id": 107, "name": "Folder — Litho", "pricing_type": "exact",
  "fields": [
    { "key": "model", "label": "Folder model", "type": "select",
      "required": true, "options": ["FPF 001", "..."], "images": { "FPF 001": "data:image/jpeg;base64,..." } }
  ],
  "validity": { "primary": "ex_modelcategory", "fields": ["paper","model"], "rules": { "CD Jacket": { "model": ["FCD 004"] } } }
}
```
- `fields[].options` — allowed values. `fields[].images` — optional data-URI image per option.
- `validity` — valid-combination rules: when the user picks `validity.primary`, restrict each
  listed field to `rules[<primary value>][<field key>]` (exactly like the order page).

### `POST /api/v1/quote`
```json
// request
{ "product_id": 105, "options": { "paper": "Simili 80gsm", "colour": "1C (Front)", "packing": "Loose" }, "quantity": 1000 }

// response
{ "product_id": 105, "product": "Letterhead — Litho", "quantity": 1000, "currency": "MYR",
  "pricing_type": "exact", "cash": 123.40, "per_unit": 0.1234,
  "tiers": { "Cash": 123.40, "Silver": 118.46, "Gold": 113.53, "Platinum": 106.12 }, "weight_kg": 7.239 }
```
- `options` keys are the `fields[].key` values from the product schema.
- `cash` is the Cash-tier price; `tiers` are the membership prices (Silver −4%, Gold −8%, Platinum −14%).
- Quantity accepts any positive integer (price interpolates between breakpoints).
- Invalid/unpriceable combinations return HTTP 422; contact-only products return 422 with a message.

## Notes
- Prices come from the exact same engine the calculator UI uses (`output/calculator_engine.cjs`),
  so the API and the calculator never disagree.
- Rebuild the two `output/` artifacts whenever pricing/options change, then restart the API.
