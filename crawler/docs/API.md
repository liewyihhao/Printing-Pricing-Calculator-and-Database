# Printoka Pricing & Ordering API — v1

The API that external sites/apps use as the pricing database and order intake for Printoka.

> **Important — there are two API modules in this repo. Only one is the product API.**
>
> | Module | Port | Purpose | Use it? |
> |---|---|---|---|
> | **`app/public_api.py`** | **8020** | **The product/pricing/ordering API. 93 products, full option schemas, quotes, orders.** | ✅ **Yes — this is the one** |
> | `app/api.py` | 8010 | Internal crawler dashboard API. Reads the crawler's SQL DB (crawl state, work queue, coverage). Its `/api/products` reflects *crawl* records, not the catalogue. | ❌ Internal only |
>
> If you are seeing a small/odd product list, you are almost certainly pointed at `app/api.py`
> (port 8010) instead of `app/public_api.py` (port 8020).

---

## Running it

```bash
uvicorn app.public_api:app --host 0.0.0.0 --port 8020
```

Interactive docs (auto-generated): **`http://localhost:8020/docs`**

- **Auth:** none.
- **CORS:** open (`*`) for GET/POST/OPTIONS.
- **Currency:** MYR. All prices are numbers (not strings).
- **Requirement:** Node.js must be installed — `/api/v1/quote` runs the shared pricing engine
  (`output/calculator_engine.cjs`), the exact same engine the calculator UI uses. One source of truth.

---

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Liveness + product count |
| GET | `/api/v1/products` | Product catalogue (93) |
| GET | `/api/v1/products/{id}` | Full option schema for one product |
| POST | `/api/v1/quote` | Price a configured product |
| POST | `/api/v1/orders` | Submit an order request |
| GET | `/api/v1/orders/{ref}` | Look up an order (tracking) |
| GET | `/api/v1/changes` | Latest market-change report |

---

### GET `/api/v1/health`

```json
{ "status": "ok", "products": 93 }
```

---

### GET `/api/v1/products`

Optional filters: `?category=Cards%20%26%20Stationery`, `?pricing_type=exact`.

```json
{
  "count": 93,
  "products": [
    { "id": 1, "name": "Business Card", "category": "Cards & Stationery", "pricing_type": "exact" },
    { "id": 104, "name": "Notepad — Litho", "category": "Books & Pads", "pricing_type": "exact" }
  ]
}
```

- **`pricing_type`** — `exact` (matches the market price to the cent) or `reference`
  (an estimate, quoted ~5–10% above market) or `contact` (no automated price).
- **Categories** — `Cards & Stationery`, `Books & Pads`, `Stickers & Labels`,
  `Marketing & Signage`, `Packaging & Bags`, `Calendars`, `Promo & Apparel`.

---

### GET `/api/v1/products/{id}`

Everything needed to render a configurator: **all variants** (size, paper, print colour,
lamination, package, finishing, hot-stamping, embossing …), validity rules, and quantity rules.

```jsonc
{
  "id": 1,
  "name": "Business Card",
  "category": "Cards & Stationery",
  "pricing_type": "exact",
  "markup": 1.0,
  "fields": [
    { "key": "size",        "label": "Size",        "options": ["54mm x 89mm", "52mm x 86mm", "…"] },
    { "key": "paper",       "label": "Paper",       "options": ["Gloss Art Card 250gsm", "…"] },
    { "key": "printcolour", "label": "Print Colour","options": ["4C (Both)", "4C (Front)"] },
    { "key": "lamination",  "label": "Lamination",  "options": ["Gloss Lamination (Both)",
                                                                "Matte Lamination (Both)",
                                                                "Gloss Water Based Varnish (Both)"] },
    { "key": "package",     "label": "Package",     "options": ["Normal", "2in1", "…"] },
    { "key": "hot_stamping","label": "Hot Stamping","options": ["No Hot Stamping", "1C (Front)", "…"] },
    { "key": "hot_stamping_colour", "label": "Hot Stamping — Foil Colour",
      "options": ["Gold", "Silver"],
      "showWhen": { "field": "hot_stamping", "notValues": ["No Hot Stamping"] } },
    { "key": "hot_stamping_w", "label": "Hot Stamping — Area width (mm)",
      "type": "number", "min": 5, "max": 300,
      "showWhen": { "field": "hot_stamping", "notValues": ["No Hot Stamping"] } }
  ],
  "validity": { "primary": "cardType", "fields": ["size", "paper", "colour"], "rules": { } },
  "quantity": {
    "moq": 50,
    "maxq": 10000,
    "options": [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 2000, "…"],
    "custom": false,
    "mode": "fixed",
    "note": "order quantity must be one of `options` (minimum = moq)"
  },
  "tiers": ["Cash", "Silver", "Gold", "Platinum"]
}
```

#### Field object

| Key | Meaning |
|---|---|
| `key` | Send this as the key in `options` when quoting |
| `label` | Human label for the control |
| `options` | Allowed values (omit/empty for `type: "number"` fields) |
| `type` | `"number"` for dimension inputs (with `min`/`max`); otherwise a select |
| `optional` | If true, may be omitted |
| `showWhen` | Conditional visibility: `{field, values?, notValues?}` — only show/send this field when the parent field's value matches (`values`) or doesn't match (`notValues`) |
| `note` | Guidance to display under the control |

**`showWhen` matters:** e.g. only send `hot_stamping_colour` when `hot_stamping` is not
`"No Hot Stamping"`. Hidden fields should not be sent and never block pricing.

#### `quantity` object (order quantity rules)

Mirrored from the supplier's order form — **enforce these in your UI**:

| Key | Meaning |
|---|---|
| `moq` | Minimum order quantity |
| `maxq` | Maximum (or `null`) |
| `options` | The standard order quantities to offer |
| `custom` | `true` = any quantity ≥ `moq` is accepted |
| `mode` | `"free"` = any qty in range · `"fixed"` = must be one of `options` |

Examples: Business Card `moq 50`, fixed · Money Packet `moq 600`, fixed ·
Folder `moq 250`, custom allowed · Mug `moq 20`, fixed.

---

### POST `/api/v1/quote`

```bash
curl -X POST http://localhost:8020/api/v1/quote \
  -H "Content-Type: application/json" \
  -d '{
        "product_id": 1,
        "options": {
          "size": "54mm x 89mm",
          "paper": "Gloss Art Card 250gsm",
          "printcolour": "4C (Both)",
          "lamination": "Gloss Lamination (Both)",
          "package": "Normal"
        },
        "quantity": 1000
      }'
```

```json
{
  "product_id": 1, "product": "Business Card", "quantity": 1000, "currency": "MYR",
  "pricing_type": "exact",
  "cash": 98.20, "per_unit": 0.0982,
  "tiers": { "Cash": 98.20, "Silver": 94.27, "Gold": 90.34, "Platinum": 84.45 },
  "weight_kg": 60.325
}
```

- **`cash`** is the list price. **`tiers`** are the membership prices
  (Silver −4%, Gold −8%, Platinum −14%) — this is the agent pricing.
- **`per_unit`** = `cash / quantity`.
- **`weight_kg`** — use it to compute delivery (courier rate/kg × chargeable weight, rounded up).

**Errors**

| Status | Meaning |
|---|---|
| 400 | Quantity below `moq`, or not one of `options` when `mode: "fixed"`. Body includes `moq` + `options`. |
| 404 | Unknown `product_id` |
| 422 | Option combination can't be priced (`quote_only: true` ⇒ quote on request) |
| 500 | Node.js missing / pricing engine error |

```json
{ "detail": { "error": "quantity below minimum order quantity", "moq": 600, "options": [600, 1250, "…"] } }
```

---

### POST `/api/v1/orders`

Submits an **order request** (no payment is taken; you confirm and collect payment separately).

```bash
curl -X POST http://localhost:8020/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "items": [{
      "product_id": 1, "product_name": "Business Card",
      "options": {"Size": "54mm x 89mm", "Paper": "Gloss Art Card 250gsm"},
      "quantity": 1000, "unit_price": 0.0982, "cash": 98.20, "weight_kg": 60.325
    }],
    "contact":  {"name": "Ada Lim", "email": "ada@studio.my", "phone": "0123456789", "company": "Studio Co"},
    "delivery": {"destination": "99", "dest_label": "West Malaysia",
                 "line1": "12 Jalan Ampang", "line2": "", "city": "Kuala Lumpur",
                 "state": "WP", "postcode": "50450"},
    "artwork":  {"design_service": "ready", "filename": "card.pdf", "note": "matte finish"},
    "totals":   {"subtotal": 98.20, "delivery_fee": 366.00, "grand_total": 464.20},
    "remarks":  ""
  }'
```

```json
{ "ok": true, "order_ref": "ORD-260716-CBA308", "status": "received",
  "received_at": "2026-07-16T07:26:02" }
```

Stored as one JSON per order under `output/orders/` plus an append-only `output/orders.jsonl`.

### GET `/api/v1/orders/{order_ref}`

Returns the full stored order (tracking). `404` if the reference is unknown.

---

### GET `/api/v1/changes`

Latest market-change report (new/removed products, changed options) from the crawler watch job.

---

## Delivery rates (client-side)

`quote` returns `weight_kg`; delivery = `ceil(weight_kg) × rate`:

| Code | Destination | Rate (RM/kg) |
|---|---|---|
| `99` | West Malaysia | 6 |
| `98` | East Malaysia | 10 |
| `SG` | Singapore | 6 |
| `TH` | Thailand (Bangkok) | 6 |

---

## Integration checklist

1. `GET /api/v1/products` → list/browse.
2. `GET /api/v1/products/{id}` → build the configurator from `fields`; honour `showWhen`.
3. Enforce `quantity.moq` / `mode` / `options` in the quantity control.
4. `POST /api/v1/quote` on every change → show `cash` + `tiers`, add delivery from `weight_kg`.
5. `POST /api/v1/orders` to submit; show `order_ref`; track via `GET /api/v1/orders/{ref}`.

## Rebuilding the data

Catalogue, options and the pricing engine are generated together — one source of truth:

```bash
python -m app.build_standalone     # -> output/calculator_data.json + calculator_engine.cjs
```

Restart the API to pick up changes.
