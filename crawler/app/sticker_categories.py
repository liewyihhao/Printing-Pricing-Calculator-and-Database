"""Label Sticker alternative cut categories (beyond Rectangle/Square + Custom Die-Cut).

From sampling (output/sticker_categories.json):
  * Standard Shape (H×W) and Round (diameter d == H=W=d) are IDENTICAL and price as
    the Rectangle imposition × a fixed premium (~1.3× actual, cutting waste).
  * No Cut  -> full-sheet, qty-only (size-independent), per material.
  * Kiss Cut-> ~flat qty curve (1 sticker per sheet).

  category_price(category, h, w, paper, colour, qty, diameter=0) -> RM
"""
from __future__ import annotations
import json
from pathlib import Path
from . import sticker_engine as SE

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "sticker_categories.json"
CATEGORIES = ["Rectangle/Square", "Custom Die-Cut", "Standard Shape", "Round", "No Cut", "Kiss Cut"]
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {
            "round": [], "standard_shape": [], "no_cut": [], "kiss_cut": []}
    return _CACHE["d"]


def _interp(pts, qty):
    """pts = list of (qty, cash) -> log-linear interpolation."""
    import math
    if not pts:
        return 0.0
    pts = sorted(pts)
    xs = [p[0] for p in pts]; ys = [math.log(p[1]) for p in pts]; x = float(qty)
    if x <= xs[0]:
        return math.exp(ys[0])
    if x >= xs[-1]:
        return math.exp(ys[-1])
    for i in range(1, len(xs)):
        if x <= xs[i]:
            t = (x - xs[i-1]) / (xs[i] - xs[i-1])
            return math.exp(ys[i-1] + t * (ys[i] - ys[i-1]))
    return math.exp(ys[-1])


def _std_mult():
    """Premium of Standard-Shape/Round over the Rectangle imposition engine."""
    if "m" in _CACHE:
        return _CACHE["m"]
    import numpy as np
    d = _data(); ratios = []
    for r in d.get("standard_shape", []):
        pred = SE.cash_price("digital", r["h"], r["w"], "Mirror Kote", "4C", r["qty"])
        if pred > 0:
            ratios.append(r["cash"] / pred)
    _CACHE["m"] = float(np.median(ratios)) if ratios else 1.3
    return _CACHE["m"]


def _nocut_pts(paper):
    d = _data()
    pts = [(r["qty"], r["cash"]) for r in d.get("no_cut", []) if r["paper"] == paper]
    if not pts:  # fall back to Mirror Kote × that material's premium
        pts = [(r["qty"], r["cash"]) for r in d.get("no_cut", []) if "Mirror" in r["paper"]]
        prem = SE.cash_price("digital", 50, 50, paper, "4C", 500) / max(
            SE.cash_price("digital", 50, 50, "Mirror Kote", "4C", 500), 1e-6)
        pts = [(q, c * prem) for q, c in pts]
    return pts


def category_price(category, h, w, paper, colour, qty, diameter=0):
    cat = category or "Rectangle/Square"
    if cat in ("Rectangle/Square", "Custom Die-Cut"):
        return SE.cash_price("digital", h, w, paper, colour, qty)
    if cat == "Round":
        d = int(diameter or h or w or 50)
        return SE.cash_price("digital", d, d, paper, colour, qty) * _std_mult()
    if cat == "Standard Shape":
        return SE.cash_price("digital", h, w, paper, colour, qty) * _std_mult()
    if cat == "No Cut":
        return _interp(_nocut_pts(paper), qty)
    if cat == "Kiss Cut":
        return _interp([(r["qty"], r["cash"]) for r in _data().get("kiss_cut", [])], qty)
    return SE.cash_price("digital", h, w, paper, colour, qty)
