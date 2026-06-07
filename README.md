# Printoka Pricing Calculator & Database

Printoka's own **offline, formula-driven** print-pricing calculator (mirrors Excard's
product options exactly; prices via our own formulas, Excard = reference only; target
3–5% deviation from cash tier; physics-based weight).

## 👉 START HERE (for a new Claude Code chat)
**Read the full handoff:** [`crawler/HANDOFF.md`](crawler/HANDOFF.md)
Raw: https://raw.githubusercontent.com/liewyihhao/Printing-Pricing-Calculator-and-Database/main/crawler/HANDOFF.md

It contains: current state, architecture, every key file, the 3 accounts, DB state,
domain learnings (offset vs digital economics), how to run, and the pending tasks
(next: Booklet products 19 Litho + 37 Digital).

## Quick status
- ✅ Digital Loose Sheet formula — median 1.3%, 86% within 5% (meets bar).
- ✅ Litho Loose Sheet formula — ~8% median (offset step-pricing limit).
- ✅ Weight (physics ~3%), options via discovery, product-aware "Printoka Formulation" UI.
- ⏳ Pending: Booklet (19/37), finishing add-ons, West/East delivery, Litho per-size tuning.

## Run
```
cd crawler
.venv\Scripts\python.exe -m uvicorn app.api:app --port 8000   # → http://localhost:8000
```
Secrets live in `crawler/.env` (git-ignored) — recreate from `crawler/.env.example`.
