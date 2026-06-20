"""Folder (Litho) pricing engine.

Model (from output/folder_samples.json):
  * Per-MOULD base quantity curve at the reference paper (Gloss Art Card 250gsm 1 side),
    log-interpolated over qty (pieces).
  * PAPER delta vs the reference paper (additive plate/material cost from the REF mould,
    interpolated over qty) — additive transfers across moulds better than multiplicative
    (validated on a 2nd mould). No print-colour choice; die-cut + creasing are included.

  cash_price(mould, paper, qty) -> RM
"""
from __future__ import annotations
import json, math, re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "folder_samples.json"
PARAMS = OUT / "folder_params.json"
REF_PAPER = "Gloss Art Card 250gsm (1 side coated)"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"core": [], "paper": [], "check": []}
    return _CACHE["d"]


def _interp(curve: dict, qty):
    pts = sorted((int(q), c) for q, c in curve.items())
    if not pts:
        return 0.0
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


def _lin(pts, x):
    pts = sorted(pts)
    if not pts:
        return 0.0
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for i in range(1, len(pts)):
        if x <= pts[i][0]:
            t = (x - pts[i-1][0]) / (pts[i][0] - pts[i-1][0])
            return pts[i-1][1] + t * (pts[i][1] - pts[i-1][1])
    return pts[-1][1]


def _base_curves():
    if "bc" in _CACHE:
        return _CACHE["bc"]
    cv: dict = {}
    for r in _data().get("core", []):
        cv.setdefault(r["mould"], {})[str(r["qty"])] = r["cash"]
    _CACHE["bc"] = cv
    return cv


def _sizes():
    if "sz" not in _CACHE:
        _CACHE["sz"] = {r["mould"]: r.get("size", "") for r in _data().get("core", [])}
    return _CACHE["sz"]


def _paper_delta(paper, qty):
    """Additive delta vs REF_PAPER, interpolated over qty (from REF-mould paper table)."""
    pd = _CACHE.get("pd")
    if pd is None:
        pap = _data().get("paper", [])
        base = {r["qty"]: r["cash"] for r in pap if r["paper"] == REF_PAPER}
        pd = {}
        for r in pap:
            if r["qty"] in base:
                pd.setdefault(r["paper"], []).append((r["qty"], r["cash"] - base[r["qty"]]))
        _CACHE["pd"] = pd
    if paper == REF_PAPER:
        return 0.0
    return _lin(pd.get(paper, [(0, 0.0)]), qty)


def _code(mould):
    """Accept 'FPF 001' or a 'FPF 001 — 350x510mm' UI label; return the bare code."""
    m = re.match(r"\s*([A-Z]{3}\s*\d{3})", mould or "")
    return m.group(1).strip() if m else (mould or "").strip()


def _gsm_2x(paper):
    m = re.search(r"(\d+)\s*gsm", paper or "")
    return int(m.group(1)) if m else 250


def cash_price(mould, paper, qty):
    bc = _base_curves()
    code = _code(mould)
    if code not in bc:
        code = next(iter(bc), None)
    if not code:
        return 0.0
    return max(_interp(bc[code], qty) + _paper_delta(paper, qty), 0.0)


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(mould, paper, qty):
    s = _sizes().get(_code(mould), "")
    m = re.findall(r"(\d+)", s)
    w, h = (int(m[0]), int(m[1])) if len(m) >= 2 else (350, 510)
    return round((w * h / 1e6) * _gsm_2x(paper) * float(qty) / 1000.0 * WEIGHT_FACTOR, 3)


def build_params():
    _paper_delta(REF_PAPER, 500)  # warm pd cache
    pd = _CACHE.get("pd") or {}
    p = {"base_curves": _base_curves(), "sizes": _sizes(),
         "paper_delta": {k: sorted(v) for k, v in pd.items()},
         "ref_paper": REF_PAPER, "weight_factor": WEIGHT_FACTOR}
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    bc = _base_curves()
    print(f"folder: {len(bc)} mould curves")
    for m in list(bc)[:3]:
        print(f"  {m} ref q500: RM{round(cash_price(m, REF_PAPER, 500), 2)} "
              f"360gsm: RM{round(cash_price(m, 'Gloss Art Card 360gsm (2 side coated)', 500), 2)} "
              f"wt={weight_kg(m, REF_PAPER, 500)}kg")
