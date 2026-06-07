"""Printoka Formulation engine — Litho Loose Sheet.

Offline pricing built on OUR data + math (Excard = reference only):
  - exact captured quantity  -> use it
  - in-between quantity       -> piecewise-linear interpolation on the config curve
  - config we don't have      -> scale from the nearest captured config by area/paper
  - weight                    -> first-principles physics (area x gsm x qty x factor)

Cash is our estimate of Excard's CASH tier; selling price applies Printoka margin.
Tier estimates derive from cash (Silver/Gold/Platinum = -4/-8/-14%).
"""
from __future__ import annotations
import re
from functools import lru_cache
import numpy as np

WEIGHT_FACTOR = 1.2065          # calibrated: Excard weight / paper physics (wastage+packing)
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}


def _area_mm2(size_label):
    m = re.search(r"(\d+)\s*mm\s*x\s*(\d+)\s*mm", size_label)
    return (int(m.group(1)) * int(m.group(2))) if m else 0


def _gsm(paper_label):
    m = re.search(r"(\d+)\s*gsm", paper_label)
    return int(m.group(1)) if m else 128


@lru_cache(maxsize=1)
def _ladders():
    """Load captured cash curves: {(size,paper,colour,package): sorted[(qty,cash)]}."""
    from .db import session_scope
    from .models import OrderWork, OrderQuote
    from sqlalchemy import select
    from collections import defaultdict
    out = defaultdict(list)
    with session_scope() as s:
        works = {w.id: w for w in s.scalars(select(OrderWork)).all()}
        for q in s.scalars(select(OrderQuote).where(OrderQuote.before_discount != None)).all():
            w = works.get(q.order_work_id)
            if w and float(q.before_discount) >= 1:
                out[(w.size_label, w.paper_label, w.colour_side, w.package)].append(
                    (int(q.quantity), float(q.before_discount)))
    return {k: sorted(set(v)) for k, v in out.items()}


def refresh():
    _ladders.cache_clear()


def _interp(curve, qty):
    xs = [c[0] for c in curve]; ys = [c[1] for c in curve]
    if qty in xs:
        return ys[xs.index(qty)], "exact"
    if qty < xs[0] or qty > xs[-1]:
        # extrapolate at the curve's edge unit-rate (rare)
        return float(np.interp(qty, xs, ys)), "edge"
    return float(np.interp(qty, xs, ys)), "interpolated"


def cash(size, paper, colour, package, qty):
    """Printoka cash estimate (Excard cash tier). Returns (price, method)."""
    L = _ladders()
    key = (size, paper, colour, package)
    if key in L:
        return _interp(L[key], qty)
    # fallback: scale from same paper+colour+package at the nearest size by area
    a0 = _area_mm2(size)
    cands = [(k, v) for k, v in L.items()
             if k[1] == paper and k[2] == colour and k[3] == package and _area_mm2(k[0]) > 0]
    if a0 and cands:
        k, v = min(cands, key=lambda kv: abs(_area_mm2(kv[0][0]) - a0))
        base, _ = _interp(v, qty)
        return base * (a0 / _area_mm2(k[0])), "scaled(area)"
    return None, "unavailable"


def tiers(cash_price):
    if cash_price is None:
        return {}
    return {t: round(cash_price * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(size, paper, qty):
    a = _area_mm2(size) / 1_000_000          # m^2
    return round(a * _gsm(paper) * qty / 1000.0 * WEIGHT_FACTOR, 2)


def quote(size, paper, colour, package, qty):
    c, method = cash(size, paper, colour, package, qty)
    return {
        "cash": round(c, 2) if c is not None else None,
        "method": method,
        "tiers": tiers(c),
        "weight_kg": weight_kg(size, paper, qty),
    }
