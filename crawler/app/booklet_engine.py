"""Printoka pure-formula engine — BOOKLET (products 19 Litho & 37 Digital).

A booklet's cost is driven by:
  * the COVER  (one spread; paper area x gsm + cover printing), and
  * the CONTENT (page count x per-sheet paper + impressions), plus
  * a per-binding fixed run cost (plates/make-ready/binding setup).

Offset (19) amortises a large fixed run cost over the quantity, so per-unit drops
steeply -> volume exponent gamma < 1. Digital (37) is ~flat -> gamma ~= 1. Same
offset-vs-digital principle as Loose Sheet, applied per booklet.

Model (per order, Cash tier):
  area   = w_mm * h_mm / 1e6                              # close-size m^2
  cpages = page-4 (Saddle) | page (Perfect, cover separate)   # content pages
  cover_kg   = 2 * area * cover_gsm/1000                  # spread ~2 faces
  content_kg = (cpages/2) * area * content_gsm/1000       # leaves = pages/2
  content_imp = (cpages/2) * colour_factor                # impressions x colour
  per_book = bind_const[b] + p_paper*(cover_kg+content_kg) + p_ink*content_imp
  cash = margin * ( fixed[b] + per_book * qty**gamma )

b in {0:Saddle, 1:Perfect-Soft, 2:Perfect-Hard}. Calibrated against
output/booklet_samples_<id>.json; params frozen to
output/booklet_params_<id>.json.

  python -m app.booklet_engine 19      # calibrate + held-out report
  python -m app.booklet_engine 37
"""
from __future__ import annotations
import re, json, sys
import numpy as np
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065

# Close-size dimensions (mm) by size label prefix.
SIZE_DIMS = {"A4": (210, 297), "A5": (148, 210), "B5": (176, 250),
             "A6": (105, 148), "B5+": (190, 266)}


def dims(size_label: str):
    m = re.search(r"(\d+)\s*mm\s*x\s*(\d+)\s*mm", size_label)
    if m:
        return int(m.group(1)), int(m.group(2))
    for k, v in SIZE_DIMS.items():
        if size_label.startswith(k):
            return v
    return (148, 210)


def gsm_of(paper: str) -> int:
    m = re.search(r"(\d+)\s*gsm", paper)
    return int(m.group(1)) if m else 250


def bind_index(ordertype: str, binding: str) -> int:
    if "Saddle" in binding:
        return 0
    return 2 if "Hard" in ordertype else 1   # Perfect: soft=1, hard=2


def content_pages(page, binding: str) -> int:
    p = int(page)
    return max(0, p - 4) if "Saddle" in binding else p   # cover separate in Perfect


def _cover_plates(outer_inner: str) -> float:
    """4C cover, 1 side (Outer Only) = 4 plates; Outer & Inner = 8."""
    return 8.0 if "Inner" in (outer_inner or "") else 4.0


def _content_plates_per_sheet(content_colour: str) -> float:
    """Offset plates per open-size content sheet: 4C both sides = 8; 1C both = 2."""
    return 8.0 if "4C" in content_colour else 2.0


def _features(size, page, ordertype, binding, cover_paper, content_paper,
              colour, outer_inner="4C: 4 Colour Outer Only"):
    """Physical drivers per BOOK:
      paper_kg  - cover + content paper mass (area x gsm)
      sheets    - open-size sheets per book (cover + content)
      plates    - offset plates (cover + content_sheets x content-colour plates)
    Offset price = margin*(setup + variable*qty^gamma); setup amortises plates over
    the run (the real source of volume economy), variable is per-book material+run.
    """
    w, h = dims(size)
    area = w * h / 1e6                                  # close-size m^2 (one face)
    cpages = content_pages(page, binding)
    content_sheets = cpages / 4.0                       # 4 pages per open-size sheet
    cover_sheets = 1.0
    # Cover spread ~ 2 faces; content open-size sheet ~ 2 faces (4 pages folded).
    cover_kg = 2 * area * gsm_of(cover_paper) / 1000.0
    content_kg = content_sheets * 2 * area * gsm_of(content_paper) / 1000.0
    paper_kg = cover_kg + content_kg
    sheets = cover_sheets + content_sheets
    plates = _cover_plates(outer_inner) + content_sheets * _content_plates_per_sheet(colour)
    b = bind_index(ordertype, binding)
    return paper_kg, sheets, plates, b


def _predict(p, paper_kg, sheets, plates, b, qty):
    margin, gamma = p[0], p[1]
    base_setup = np.array(p[2:5])[b]     # per-run base by binding
    plate_cost, p_paper, p_imp = p[5], p[6], p[7]
    # setup = make-ready (one plate per sheet-side-colour), amortised over the run.
    # variable (per book) = paper material + printing/running (per impression, so
    # 4C content costs more ink per book than 1C — not just more plates).
    setup = base_setup + plate_cost * plates
    variable = p_paper * paper_kg + p_imp * plates
    return margin * (setup + variable * np.power(qty, gamma))


# ---- per-config quantity curves (exact reproduction of Excard where sampled) ----
import math
_CURVE_CACHE: dict = {}


def _curve_key(size, page, ordertype, binding, cover_paper, content_paper, content_colour):
    return "|".join([str(size), str(page), str(ordertype), str(binding),
                     str(cover_paper), str(content_paper), str(content_colour)])


def _load_curves(product_id):
    if product_id not in _CURVE_CACHE:
        f = OUT / f"booklet_curve_{product_id}.json"
        _CURVE_CACHE[product_id] = json.loads(f.read_text()) if f.exists() else {}
    return _CURVE_CACHE[product_id]


def _interp_log(curve, qty):
    qs = sorted(int(q) for q in curve)
    ys = [curve[str(q)] for q in qs]
    x = float(qty)
    if x <= qs[0]:
        return ys[0]
    if x >= qs[-1]:
        return ys[-1]
    for i in range(1, len(qs)):
        if x <= qs[i]:
            t = (x - qs[i-1]) / (qs[i] - qs[i-1])
            return ys[i-1] + t * (ys[i] - ys[i-1])
    return ys[-1]


def build_curves(product_id=19):
    """Build per-config quantity curves from the Excard samples -> exact prices for
    sampled configs; the smooth formula remains the fallback for unsampled combos."""
    data = json.loads((OUT / f"booklet_samples_{product_id}.json").read_text())
    curves: dict = {}
    for r in data:
        if not r.get("cash"):
            continue
        k = _curve_key(r["size"], r["page"], r["ordertype"], r["binding"],
                       r["cover_paper"], r["content_paper"], r["content_colour"])
        curves.setdefault(k, {})[str(int(r["qty"]))] = math.log(r["cash"])
    (OUT / f"booklet_curve_{product_id}.json").write_text(json.dumps(curves))
    _CURVE_CACHE.pop(product_id, None)
    return len(curves)


def cash_price(size, page, ordertype, binding, cover_paper, content_paper,
               content_colour, qty, outer_inner="4C: 4 Colour Outer Only",
               params=None, product_id=19) -> float:
    # 1) exact per-config curve (interpolated across qty) where we sampled Excard
    curve = _load_curves(product_id).get(
        _curve_key(size, page, ordertype, binding, cover_paper, content_paper, content_colour))
    if curve and len(curve) >= 2:
        return float(math.exp(_interp_log(curve, qty)))
    # 2) fallback: calibrated smooth formula for unsampled combos
    if params is None:
        params = load_params(product_id)
    pk, sh, pl, b = _features(size, page, ordertype, binding, cover_paper,
                              content_paper, content_colour, outer_inner)
    return float(_predict(np.array(params), np.array([pk]), np.array([sh]),
                          np.array([pl]), np.array([b]), np.array([float(qty)]))[0])


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(size, page, ordertype, binding, cover_paper, content_paper, qty):
    w, h = dims(size)
    area = w * h / 1e6
    cpages = content_pages(page, binding)
    per_book_kg = 2 * area * gsm_of(cover_paper) / 1000.0 + \
        (cpages / 2.0) * area * gsm_of(content_paper) / 1000.0
    return round(per_book_kg * qty * WEIGHT_FACTOR, 2)


def load_params(product_id=19):
    f = OUT / f"booklet_params_{product_id}.json"
    if f.exists():
        return json.loads(f.read_text())["params"]
    raise RuntimeError(f"Booklet {product_id} not calibrated — "
                       f"run: python -m app.booklet_engine {product_id}")


def calibrate_and_report(product_id=19):
    from scipy.optimize import differential_evolution
    data = json.loads((OUT / f"booklet_samples_{product_id}.json").read_text())
    rows = [(_features(d["size"], d["page"], d["ordertype"], d["binding"],
                       d["cover_paper"], d["content_paper"], d["content_colour"],
                       d.get("outer_inner", "4C: 4 Colour Outer Only")),
             float(d["qty"]), float(d["cash"]),
             (d["size"], d["binding"], d["cover_paper"], d["content_paper"],
              d["content_colour"], d["page"]))
            for d in data if d.get("cash")]
    if not rows:
        print("no samples yet"); return
    pk = np.array([r[0][0] for r in rows]); sh = np.array([r[0][1] for r in rows])
    pl = np.array([r[0][2] for r in rows]); b = np.array([r[0][3] for r in rows])
    qty = np.array([r[1] for r in rows]); cash = np.array([r[2] for r in rows])
    keys = [r[3] for r in rows]
    rng = np.random.default_rng(7)
    uniq = list({k for k in keys}); rng.shuffle(uniq)
    hold = set(uniq[: max(1, len(uniq) // 4)])
    tr = np.array([i for i, k in enumerate(keys) if k not in hold])
    te = np.array([i for i, k in enumerate(keys) if k in hold])

    def loss(p):
        pred = _predict(p, pk[tr], sh[tr], pl[tr], b[tr], qty[tr])
        return float(np.median(np.abs(pred - cash[tr]) / cash[tr]))

    # Offset booklet is ~LINEAR in qty (volume economy comes from amortising the
    # plate setup), so gamma sits near 1 for both; digital flatter still.
    gamma_bounds = (0.9, 1.03) if product_id == 37 else (0.85, 1.02)
    bounds = [(1.0, 4.0), gamma_bounds,            # margin, gamma
              (0, 5000), (0, 8000), (0, 12000),     # base_setup[saddle,perf_soft,perf_hard]
              (0, 60),                              # plate_cost (RM/plate, amortised)
              (0, 30), (0, 8)]                      # p_paper(RM/kg), p_imp(RM/impression/book)
    res = differential_evolution(loss, bounds, maxiter=400, popsize=30, seed=7,
                                 tol=1e-7, workers=1, polish=True)
    p = res.x
    (OUT / f"booklet_params_{product_id}.json").write_text(
        json.dumps({"params": list(p), "product_id": product_id}, indent=1))

    def stat(name, idx):
        pred = _predict(p, pk[idx], sh[idx], pl[idx], b[idx], qty[idx])
        e = np.abs(pred - cash[idx]) / cash[idx] * 100
        print(f"{name}: n={len(idx)} MAPE {e.mean():.1f}% median {np.median(e):.1f}% "
              f"<=5% {(e<=5).mean()*100:.0f}% <=10% {(e<=10).mean()*100:.0f}% "
              f"under {(pred<cash[idx]).mean()*100:.0f}%")
    print(f"params: margin={p[0]:.2f} gamma={p[1]:.3f} base_setup={[round(x) for x in p[2:5]]} "
          f"plate_cost={p[5]:.2f} p_paper={p[6]:.2f} p_imp={p[7]:.3f}")
    stat("TRAIN", tr)
    stat("TEST (held-out)", te)

    # Write a KPI report matching the existing spot_test_report_*.json shape.
    pred_te = _predict(p, pk[te], sh[te], pl[te], b[te], qty[te])
    e = np.abs(pred_te - cash[te]) / cash[te] * 100
    (OUT / f"spot_test_report_{product_id}.json").write_text(json.dumps({
        "product": product_id, "test": "held-out configs (25%)",
        "sample_points": len(rows),
        "median": round(float(np.median(e)), 2),
        "within_3pct": round(float((e <= 3).mean() * 100)),
        "within_5pct": round(float((e <= 5).mean() * 100)),
        "within_10pct": round(float((e <= 10).mean() * 100)),
        "mape": round(float(e.mean()), 2),
        "under_predict_pct": round(float((pred_te < cash[te]).mean() * 100)),
        "method": "pure formula (booklet)"}, indent=1))
    print(f"saved -> booklet_params_{product_id}.json + spot_test_report_{product_id}.json")


if __name__ == "__main__":
    pid = int(sys.argv[1]) if len(sys.argv) > 1 else 19
    calibrate_and_report(pid)
