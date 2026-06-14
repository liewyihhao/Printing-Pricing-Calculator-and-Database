"""Label Sticker LAMINATION finishing cost (ddlfinishing), from sticker_finishing.json.
Applies to all cut categories. delta[opt]["WxH"][qty]; size-nearest fallback.

  finishing_cost(opt, h, w, qty) -> RM add-on
"""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "sticker_finishing.json"
LAM_OPTIONS = ["Not Required", "Matte Laminate (Front)", "Gloss Laminate (Front)",
               "Gloss Water Based Varnish", "UV Varnish", "Soft Touch Laminate (Front)"]
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {}
    return _CACHE["d"]


def _interp(curve, qty):
    if not curve:
        return 0.0
    qs = sorted(int(q) for q in curve); ys = [curve[str(q)] for q in qs]; x = float(qty)
    if x <= qs[0]:
        return ys[0]
    if x >= qs[-1]:
        return ys[-1]
    for i in range(1, len(qs)):
        if x <= qs[i]:
            t = (x - qs[i-1]) / (qs[i] - qs[i-1])
            return ys[i-1] + t * (ys[i] - ys[i-1])
    return ys[-1]


def finishing_cost(opt, h, w, qty) -> float:
    if not opt or opt == "Not Required":
        return 0.0
    by_size = _data().get(opt)
    if not by_size:
        return 0.0
    key = f"{int(h)}x{int(w)}"
    curve = by_size.get(key)
    if curve is None:
        def area(k):
            a, b = k.split("x"); return int(a) * int(b)
        curve = by_size[min(by_size, key=lambda k: abs(area(k) - h * w))]
    return round(_interp(curve, qty), 2)
