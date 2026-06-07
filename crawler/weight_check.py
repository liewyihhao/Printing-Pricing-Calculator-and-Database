"""Validate a GSM-physics weight model against Excard's captured weights."""
import re
import numpy as np
from app.db import session_scope
from app.models import OrderWork, OrderQuote
from sqlalchemy import select


def area_m2(size_label):
    m = re.search(r"(\d+)\s*mm\s*x\s*(\d+)\s*mm", size_label)
    return (int(m.group(1)) * int(m.group(2))) / 1_000_000 if m else None


def gsm_of(paper_label):
    m = re.search(r"(\d+)\s*gsm", paper_label)
    return int(m.group(1)) if m else None


ratios = []
samples = []
with session_scope() as s:
    works = {w.id: w for w in s.scalars(select(OrderWork)).all()}
    for q in s.scalars(select(OrderQuote).where(OrderQuote.weight_kg != None)).all():
        w = works.get(q.order_work_id)
        if not w or w.package != "Normal":
            continue
        a = area_m2(w.size_label); g = gsm_of(w.paper_label)
        wt = float(q.weight_kg)
        if not a or not g or wt <= 0 or wt > 2000:
            continue
        physics = a * g * q.quantity / 1000.0   # kg, paper only
        if physics <= 0:
            continue
        ratios.append(wt / physics)
        samples.append((w.size_label[:6], g, q.quantity, round(physics, 2), wt))

ratios = np.array(ratios)
k = np.median(ratios)   # calibration factor
print(f"samples={len(ratios)}  median factor (excard/physics) = {k:.4f}")
# apply factor, measure error
pred = np.array([r and (k) for r in ratios])  # placeholder
err = np.abs((k / ratios) - 1) * 100  # |predicted/actual - 1| since predicted=physics*k, actual=physics*ratio
print(f"weight error with single factor k={k:.3f}:")
print(f"  MAPE {err.mean():.2f}%  median {np.median(err):.2f}%  within 3% {(err<=3).mean()*100:.1f}%  within 5% {(err<=5).mean()*100:.1f}%")
print("examples (size, gsm, qty, physics_kg, excard_kg, model_kg):")
for (sz, g, qn, ph, wt) in samples[:8]:
    print(f"  {sz:6} {g}gsm x{qn:>5}: physics={ph:>7.2f}  excard={wt:>7.2f}  model={ph*k:>7.2f}")
