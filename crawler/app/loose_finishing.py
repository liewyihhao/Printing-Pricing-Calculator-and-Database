"""Digital Loose Sheet (product 50) finishing add-on pricing.

Reads output/loose_finishing_50.json (deltas sampled from the www order page):
  hot_stamping[opt] -> {qty: delta},  punch[opt] -> {qty: delta},
  fold[code] -> {"WxH": {qty: delta}}   (folding is size-dependent)

  finishing_cost(opts, qty, size_label) -> RM add-on
opts keys: hot_stamping (label or "Not Required"), punch ("No"/"3mm"/"6mm"),
fold (code or "None").
"""
from __future__ import annotations
import json, re
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "loose_finishing_50.json"

HOT_STAMP_OPTIONS = ["Not Required", "1C (Front)", "1C (Back)", "2C (Front)", "2C (Back)"]
PUNCH_OPTIONS = ["No", "3mm", "6mm"]
FOLD_OPTIONS = ["None", "1Fa", "2Fa", "2Fb", "2Fc", "3Fa", "3Fb", "4Fa", "4Fb"]

_CACHE = {}


def _load():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"hot_stamping": {}, "punch": {}, "fold": {}}
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


def _wxh(size_label):
    m = re.search(r"(\d+)\s*mm\s*x\s*(\d+)\s*mm", size_label or "")
    return (int(m.group(1)), int(m.group(2))) if m else (210, 297)


def finishing_cost(opts: dict, qty, size_label="") -> float:
    d = _load(); total = 0.0
    hs = opts.get("hot_stamping")
    if hs and hs != "Not Required":
        total += _interp(d["hot_stamping"].get(hs, {}), qty)
    pu = opts.get("punch")
    if pu in ("3mm", "6mm"):
        total += _interp(d["punch"].get(pu, {}), qty)
    fold = opts.get("fold")
    if fold and fold != "None" and fold in d.get("fold", {}):
        by_size = d["fold"][fold]
        w, h = _wxh(size_label); key = f"{w}x{h}"
        curve = by_size.get(key)
        if curve is None and by_size:
            # nearest sampled size by area
            def area(k):
                a, b = k.split("x"); return int(a) * int(b)
            curve = by_size[min(by_size, key=lambda k: abs(area(k) - w * h))]
        total += _interp(curve or {}, qty)
    return round(total, 2)
