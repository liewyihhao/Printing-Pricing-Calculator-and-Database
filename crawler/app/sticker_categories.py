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
MD_FILE = OUT / "sticker_multidieline.json"
CATEGORIES = ["Rectangle/Square", "Custom Die-Cut", "Standard Shape", "Round",
              "No Cut", "Kiss Cut", "Multiple Dieline"]
MD_SHEET_SIZES = ["A3+", "A4", "A5"]   # Delivery Sheet Size (317x425 / 210x297 / 148x210 mm)
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


# ---------------- Multiple Dieline (sheet-based multi-design) ----------------
# Priced by NUMBER OF SHEETS, per Delivery Sheet Size (A3+/A4/A5). The number of
# die lines nested per sheet (txtTtlArtwork) has NO price effect (verified by
# sampling dl=1/5/20/40 -> identical price). Material/colour act as multipliers
# vs Mirror Kote 4C, calibrated from sampled premiums and the imposition engine's
# per-material factors for unsampled materials.

def _md():
    if "md" not in _CACHE:
        _CACHE["md"] = (json.loads(MD_FILE.read_text()) if MD_FILE.exists()
                        else {"sheets": [], "dieline_sens": [], "mat_sens": []})
    return _CACHE["md"]


def _md_base_pts(sheet_size):
    """Mirror Kote 4C (qty, cash) curve for a sheet size; fall back to A3+ if absent."""
    d = _md()
    pts = [(r["sheet_qty"], r["cash"]) for r in d.get("sheets", [])
           if r["sheet_size"] == sheet_size and r["paper"] == "Mirror Kote" and r["colour"] == "4C"]
    if not pts:
        pts = [(r["sheet_qty"], r["cash"]) for r in d.get("sheets", [])
               if r["sheet_size"] == "A3+" and r["paper"] == "Mirror Kote" and r["colour"] == "4C"]
    return pts


def _md_colour_mult():
    """1C / 4C price ratio (median over sampled qtys)."""
    if "md_col" in _CACHE:
        return _CACHE["md_col"]
    d = _md()
    base = {(r["sheet_size"], r["sheet_qty"]): r["cash"] for r in d.get("sheets", [])
            if r["paper"] == "Mirror Kote" and r["colour"] == "4C"}
    ratios = []
    for r in d.get("mat_sens", []):
        if r["colour"] == "1C" and r["paper"] == "Mirror Kote":
            b = base.get(("A3+", r["sheet_qty"]))
            if b:
                ratios.append(r["cash"] / b)
    import statistics
    _CACHE["md_col"] = float(statistics.median(ratios)) if ratios else 0.85
    return _CACHE["md_col"]


def _md_mat_mult(paper):
    """Material multiplier vs Mirror Kote. Linear map from the imposition engine's
    relative material factor, calibrated on the sampled premiums (Mirror Kote,
    White PP, Synthetic)."""
    if paper == "Mirror Kote" or not paper:
        return 1.0
    key = f"md_mat_{paper}"
    if key in _CACHE:
        return _CACHE[key]
    d = _md()
    # engine relative factors (normalised to Mirror Kote)
    import json as _j
    p = _j.loads((OUT / "sticker_params_digital.json").read_text())["params"]
    n = len(SE.MATERIALS); mats = p[9:9 + n]; ef = {m: mats[i] / mats[0] for i, m in enumerate(SE.MATERIALS)}
    # measured md multipliers at A3+ (avg over qtys)
    base = {(r["sheet_size"], r["sheet_qty"]): r["cash"] for r in d.get("sheets", [])
            if r["paper"] == "Mirror Kote" and r["colour"] == "4C"}
    meas = {}  # paper -> list of measured multipliers
    for r in d.get("mat_sens", []):
        if r["colour"] != "4C":
            continue
        b = base.get(("A3+", r["sheet_qty"]))
        if b:
            meas.setdefault(r["paper"], []).append(r["cash"] / b)
    import statistics
    # fit md_mult = a + b*ef on points {Mirror Kote:1.0} + measured
    xs = [1.0]; ys = [1.0]
    for pap, vals in meas.items():
        if pap in ef:
            xs.append(ef[pap]); ys.append(statistics.median(vals))
    if len(xs) >= 2:
        import numpy as np
        bb, aa = np.polyfit(xs, ys, 1)
    else:
        aa, bb = 0.0, 1.0
    mult = max(0.5, aa + bb * ef.get(paper, 1.0))
    _CACHE[key] = float(mult)
    return _CACHE[key]


def multidieline_price(sheet_size, sheet_qty, paper, colour):
    pts = _md_base_pts(sheet_size or "A3+")
    if not pts:
        return 0.0
    base = _interp(pts, sheet_qty)
    mult = _md_mat_mult(paper)
    if (colour or "").startswith("1C"):
        mult *= _md_colour_mult()
    return base * mult


def category_price(category, h, w, paper, colour, qty, diameter=0, sheet_size="A3+"):
    if category == "Multiple Dieline":
        return multidieline_price(sheet_size, qty, paper, colour)
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
