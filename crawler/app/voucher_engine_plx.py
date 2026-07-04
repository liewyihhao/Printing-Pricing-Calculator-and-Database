"""Voucher (Litho) pricing engine — EXACT v4 CheckPrice pricelist.

Uses output/voucher_plx_params.json built by voucher_cp_sampler.
Curve key: "packform|size|paper|colour|sets=N|num=X|perf=Y"
Each curve is {qty: price}.  Exact match at orderable qtys; log-log interpolation
between them.
"""
from __future__ import annotations
import json, math, re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
PARAMS_FILE = OUT / "voucher_plx_params.json"
WEIGHT_FACTOR = 1.2065
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
_CACHE: dict = {}


def _plx() -> dict:
    if "p" not in _CACHE:
        _CACHE["p"] = json.loads(PARAMS_FILE.read_text(encoding="utf-8")) if PARAMS_FILE.exists() else {}
    return _CACHE["p"]


def _interp_ll(curve: dict, qty: int) -> float:
    pts = sorted((int(k), float(v)) for k, v in curve.items() if int(k) > 0 and float(v) > 0)
    if not pts:
        return 0.0
    x = math.log(max(float(qty), 1))
    xs = [math.log(p[0]) for p in pts]
    ys = [math.log(p[1]) for p in pts]
    if x <= xs[0]:
        return math.exp(ys[0])
    if x >= xs[-1]:
        return math.exp(ys[-1])
    for i in range(1, len(xs)):
        if x <= xs[i]:
            t = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return math.exp(ys[i - 1] + t * (ys[i] - ys[i - 1]))
    return math.exp(ys[-1])


def _make_key(packform: str, size: str, paper: str, colour: str,
              sets: str, numbering: str, perf: str) -> str:
    return f"{packform}|{size}|{paper}|{colour}|sets={sets}|num={numbering}|perf={perf}"


def cash_price(packform: str, size: str, paper: str, colour: str,
               sets: str, qty: int, perforation: str = "0", numbering: str = "No") -> float:
    p = _plx()
    curves = p.get("curves", {})
    if not curves:
        # Fallback to old engine if no plx params yet
        from app import voucher_engine as _old
        return _old.cash_price(packform, size, paper, colour, sets, qty,
                               perforation=str(perforation), numbering=(numbering == "Yes"))

    num_str = "Yes" if numbering in (True, "Yes") else "No"
    perf_str = str(perforation)
    sets_str = str(sets) if packform in ("Pad", "Book") else ""

    key = _make_key(packform, size, paper, colour, sets_str, num_str, perf_str)
    curve = curves.get(key)

    if curve:
        exact = curve.get(str(qty))
        if exact is not None:
            return round(float(exact), 2)
        return round(max(_interp_ll(curve, qty), 0.0), 2)

    # Try perf=0 fallback (some perfs may not have been sampled)
    fallback_key = _make_key(packform, size, paper, colour, sets_str, num_str, "0")
    curve_fb = curves.get(fallback_key)
    if curve_fb:
        return round(max(_interp_ll(curve_fb, qty), 0.0), 2)

    # Final fallback to formula engine
    from app import voucher_engine as _old
    return _old.cash_price(packform, size, paper, colour, sets_str, qty,
                           perforation=perf_str, numbering=(num_str == "Yes"))


def tiers(cash: float) -> dict:
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(size: str, paper: str, sets: str, qty: int) -> float:
    m = re.findall(r"(\d+)", size or "")
    w, h = (int(m[0]), int(m[1])) if len(m) >= 2 else (145, 210)
    g = re.search(r"(\d+)\s*gsm", paper or "")
    gsm = int(g.group(1)) if g else 100
    sets_int = int(sets) if sets and str(sets).isdigit() else 1
    sheets = float(qty) * sets_int
    return round((w * h / 1e6) * gsm * sheets / 1000.0 * WEIGHT_FACTOR, 3)
