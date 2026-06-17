"""Bill-Book (Litho) pricing engine — NCR carbonless book/pad.

Model (calibrated from output/billbook_samples.json, sampled off the live order page):
  * Per-config QUANTITY CURVE keyed by (layers|colour|sets) at A4, log-interpolated over
    qty (number of BOOKS). Exact at Excard's order quantities for A4.
  * SIZE factor: price scales by a per-size factor vs A4 (from the size scan; area-
    interpolated for unsampled sizes).
  * sets: 2-ply books offer 50/100 sets per book; 3+ ply forms are fixed (sets="-").
  * PackForm: Pad ~= Book x 0.988.
  * Numbering: free (no price delta). Hole punch: + ~RM0.358 per book.

  cash_price(size, layers, colour, sets, qty, packform, numbering, punch) -> RM
"""
from __future__ import annotations
import json, math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
FILE = OUT / "billbook_samples.json"
PARAMS = OUT / "billbook_params.json"

SIZE_MM = {  # label -> (w,h) mm for area-interp + weight
    "A4 (210mm x 297mm)": (210, 297), "B5 (176mm x 250mm)": (176, 250),
    "145mm x 210mm": (145, 210), "90mm x 140mm": (90, 140), "105mm x 145mm": (105, 145),
}
PAD_FACTOR = 0.988
PUNCH_PER_BOOK = 0.3581   # (1488.80 - 1452.99 base 'punch' delta) / 100 books
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065
NCR_GSM = 55
_CACHE: dict = {}


def _data():
    if "d" not in _CACHE:
        _CACHE["d"] = json.loads(FILE.read_text()) if FILE.exists() else {"core": [], "size_scan": []}
    return _CACHE["d"]


def _interp(curve: dict, qty):
    """curve {qty:cash} -> log-linear interpolation over qty."""
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


def _curves():
    if "c" in _CACHE:
        return _CACHE["c"]
    cv: dict = {}
    for r in _data().get("core", []):
        cv.setdefault(f"{r['layers']}|{r['colour']}|{r['sets']}", {})[str(r["qty"])] = r["cash"]
    _CACHE["c"] = cv
    return cv


def _size_factor(size):
    """Price factor vs A4 from the size scan; area-interpolated for unsampled sizes."""
    sf = _CACHE.get("sf")
    if sf is None:
        d = _data(); ss = d.get("size_scan", [])
        a4 = {r["qty"]: r["cash"] for r in ss if r["size"].startswith("A4")}
        from collections import defaultdict
        bysz = defaultdict(dict)
        for r in ss:
            bysz[r["size"]][r["qty"]] = r["cash"]
        sf = {}
        for s, c in bysz.items():
            facs = [c[q] / a4[q] for q in c if q in a4 and a4[q]]
            if facs:
                sf[s] = sum(facs) / len(facs)
        _CACHE["sf"] = sf
    if size in sf:
        return sf[size]
    # area-interpolate by box face area
    area = _area(size)
    pts = sorted((_area(s), f) for s, f in sf.items() if _area(s))
    if not pts or not area:
        return 1.0
    if area <= pts[0][0]:
        return pts[0][1]
    if area >= pts[-1][0]:
        return pts[-1][1]
    for i in range(1, len(pts)):
        if area <= pts[i][0]:
            t = (area - pts[i-1][0]) / (pts[i][0] - pts[i-1][0])
            return pts[i-1][1] + t * (pts[i][1] - pts[i-1][1])
    return 1.0


def _area(size):
    wh = SIZE_MM.get(size)
    if wh:
        return wh[0] * wh[1]
    import re
    m = re.findall(r"(\d+)\s*mm", size or "")
    return (int(m[0]) * int(m[1])) if len(m) >= 2 else 0


def _n_layers(layers):
    import re
    m = re.search(r"(\d+)", layers or "")
    return int(m.group(1)) if m else 2


def cash_price(size, layers, colour, sets, qty, packform="Book", numbering=False, punch=False):
    cv = _curves()
    key = f"{layers}|{colour}|{sets}"
    if key not in cv:  # fall back: 3+ ply use sets='-'; 2 ply default '50'
        alt = f"{layers}|{colour}|{'-' if _n_layers(layers) >= 3 else '50'}"
        key = alt if alt in cv else next((k for k in cv if k.startswith(f"{layers}|{colour}|")), None)
    if not key:
        return 0.0
    base = _interp(cv[key], qty) * _size_factor(size)
    if packform == "Pad":
        base *= PAD_FACTOR
    if punch:
        base += PUNCH_PER_BOOK * float(qty)
    # numbering is free (no delta observed)
    return base


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(size, layers, sets, qty, packform="Book"):
    w, h = SIZE_MM.get(size, (210, 297))
    sets_n = 50 if (sets in ("-", None) or not str(sets).isdigit()) else int(sets)
    sheets = float(qty) * sets_n * _n_layers(layers)
    return round((w * h / 1e6) * NCR_GSM * sheets / 1000.0 * WEIGHT_FACTOR, 3)


def build_params():
    """Emit a compact params blob for the standalone (curves + size factors + deltas)."""
    p = {"curves": _curves(),
         "size_factors": {s: round(_size_factor(s), 8) for s in SIZE_MM},
         "size_mm": SIZE_MM, "pad_factor": PAD_FACTOR, "punch_per_book": PUNCH_PER_BOOK,
         "ncr_gsm": NCR_GSM, "weight_factor": WEIGHT_FACTOR}
    PARAMS.write_text(json.dumps(p, indent=0))
    return p


if __name__ == "__main__":
    build_params()
    print("billbook params written.")
    for (s, L, c, st, q) in [("A4 (210mm x 297mm)", "NCR - 2 Layers", "1C (Front)", "50", 100),
                             ("A4 (210mm x 297mm)", "NCR - 3 Layers", "4C (Front)", "-", 200),
                             ("B5 (176mm x 250mm)", "NCR - 2 Layers", "1C (Front)", "100", 100)]:
        print(f"  {s[:6]} {L[-8:]} {c} sets{st} q{q}: RM{round(cash_price(s,L,c,st,q),2)} "
              f"wt={weight_kg(s,L,st,q)}kg")
