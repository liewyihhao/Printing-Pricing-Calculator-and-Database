"""Business-card FINISHING add-on pricing (v4 API).

Finishing deltas (price WITH finishing − base price) are per-unit costs that scale
with quantity and are independent of size/paper (verified), so each finishing is a
single delta-vs-quantity curve. Lamination + Spot UV are encoded in the API's
`Lamination` field and are mutually exclusive (one surface finish per card). Round
corner / hole punch are independent toggles. Hot stamping & embossing are
block/mould charges NOT exposed by the pricing API (it only adds process days) — we
flag those as "quoted separately" rather than invent a number.

  build()                              # sample delta curves -> output/bizcard_finishing.json
  finishing_cost(opts, qty) -> float   # sum of selected finishing deltas (interpolated)

`opts` keys: surface (lamination/spot-uv label or "None"), round_corner (bool),
hole_punch ("No"/"3mm"/"5mm").
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "bizcard_finishing.json"

# surface finish label -> API Lamination value
SURFACE = {
    "None": "",
    "Gloss Lamination (Both)": "Gloss Lamination (Both)",
    "Matte Lamination (Both)": "Matte Lamination (Both)",
    "Soft Touch Lamination (Both)": "Soft Touch Lamination (Both)",
    "Spot UV (Front)": "Matte Lamination (Both) + Spot UV (Front)",
    "Spot UV (Both)": "Matte Lamination (Both) + Spot UV (Both)",
}
SURFACE_OPTIONS = list(SURFACE.keys())
HOLE_OPTIONS = ["No", "3mm", "5mm"]
# Specialty block-charge finishings the pricing API doesn't expose (process-day only)
HOT_STAMPING_OPTIONS = ["No Hot Stamping", "1C (Front)", "1C (Back)", "2C (Front)", "2C (Back)"]
EMBOSSING_OPTIONS = ["Not Required", "Embossing Front", "Embossing Back"]


def build():
    from .bizcard_api import make_spec, price
    from .bizcard_sampler import QTYS
    cfg = dict(OrderDesc="Standard", Size="54mm x 89mm", Paper="Gloss Art Card 250gsm",
               PrintColour="4C (Both)")
    data = {"surface": {}, "round_corner": {}, "hole_punch": {}}
    for q in QTYS:
        base = price(make_spec(**cfg, Lamination="", Quantity=str(q)))
        if not base:
            continue
        for label, lam in SURFACE.items():
            if label == "None":
                continue
            p = price(make_spec(**cfg, Lamination=lam, Quantity=str(q)))
            if p:
                data["surface"].setdefault(label, {})[str(q)] = round(p - base, 2)
        rc = price(make_spec(**cfg, Lamination="", Quantity=str(q), RoundCorner="RC0601"))
        if rc:
            data["round_corner"][str(q)] = round(rc - base, 2)
        hp = price(make_spec(**cfg, Lamination="", Quantity=str(q), HolePunch="3mm"))
        if hp:
            data["hole_punch"][str(q)] = round(hp - base, 2)
    FILE.write_text(json.dumps(data, indent=1))
    print(f"wrote {FILE.name}: surfaces={list(data['surface'])} "
          f"qtys={len(data['round_corner'])}")
    return data


_CACHE = {}


def _load():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"surface": {}, "round_corner": {}, "hole_punch": {}}
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


def finishing_cost(opts: dict, qty) -> float:
    d = _load()
    total = 0.0
    surf = opts.get("surface")
    if surf and surf != "None":
        total += _interp(d["surface"].get(surf, {}), qty)
    if opts.get("round_corner") in (True, "true", "Required", "Yes"):
        total += _interp(d.get("round_corner", {}), qty)
    if opts.get("hole_punch") in ("3mm", "5mm"):
        total += _interp(d.get("hole_punch", {}), qty)
    return round(total, 2)


if __name__ == "__main__":
    build()
