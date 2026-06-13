"""Printoka formula engine — LABEL STICKER (Digital + Letterpress).

Custom-size product (no standard sizes): price is driven by IMPOSITION — how many
stickers nest on a press sheet — so it steps as W/H cross sheet-fit boundaries
(verified: 50x48=RM59.90 but 50x60=RM47.90; symmetric in W,H). We model it like the
digital loose-sheet engine:

  ups(W,H)  = max stickers per press sheet (both orientations, with bleed/gutter)
  sheets    = ceil(qty / ups)
  cash      = margin * ( setup + rate * mat[material] * colour * sheets ** gamma )

Calibrated against output/sticker_samples_<method>.json. Params frozen to
output/sticker_params_<method>.json.

  python -m app.sticker_engine digital
"""
from __future__ import annotations
import json, math, sys
import numpy as np
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065

MATERIALS = ["Mirror Kote", "Mirror Kote (Strong Glue)", "Transparent OPP",
             "White PP (Polypropylene)", "White PE (Polyethylene)", "Synthetic Paper",
             "Printing Paper", "Brown Craft Paper", "Matte Silver Polyester",
             "Bright Silver Polyester", "Removable Transparent OPP",
             "Removable White PP", "Warranty Sticker"]


def mat_idx(m):
    for i, x in enumerate(MATERIALS):
        if x.lower() == (m or "").lower():
            return i
    return 0


def ups(w, h, SW, SH, bleed):
    pw, ph = w + bleed, h + bleed
    if pw <= 0 or ph <= 0:
        return 1
    a = math.floor(SW / pw) * math.floor(SH / ph)
    b = math.floor(SW / ph) * math.floor(SH / pw)
    return max(1, a, b)


def _predict_one(p, w, h, m, colour1C, qty):
    # p: margin,setup,rate,gamma, SW1,SH1, SW2,SH2, bleed, mat[..], 1Cfac
    margin, setup, rate, gamma = p[0:4]
    SW1, SH1, SW2, SH2, bleed = p[4:9]
    mats = p[9:9 + len(MATERIALS)]; colf = p[9 + len(MATERIALS)]
    # Excard gangs onto the press sheet that fits the MOST stickers (best of 2 sheets).
    u = max(ups(w, h, SW1, SH1, bleed), ups(w, h, SW2, SH2, bleed))
    sheets = math.ceil(qty / u)
    col = colf if colour1C else 1.0
    return margin * (setup + rate * mats[m] * col * (sheets ** gamma))


def cash_price(method, h, w, paper, colour, qty, params=None):
    if params is None:
        params = load_params(method)
    c1 = "1C" in (colour or "")
    return float(_predict_one(params, w, h, mat_idx(paper), c1, float(qty)))


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(h, w, qty, gsm=150):
    return round((w * h / 1e6) * gsm * qty / 1000.0 * WEIGHT_FACTOR, 3)


def load_params(method="digital"):
    f = OUT / f"sticker_params_{method}.json"
    if f.exists():
        return json.loads(f.read_text())["params"]
    raise RuntimeError(f"Sticker {method} not calibrated — run: python -m app.sticker_engine {method}")


def calibrate_and_report(method="digital"):
    from scipy.optimize import differential_evolution
    data = [d for d in json.loads((OUT / f"sticker_samples_{method}.json").read_text())
            if d.get("cash") and d.get("category", "").startswith("Rectangle")]
    if len(data) < 20:
        # fall back to all categories if Rectangle-only is sparse
        data = [d for d in json.loads((OUT / f"sticker_samples_{method}.json").read_text()) if d.get("cash")]
    w = np.array([d["w"] for d in data], float); h = np.array([d["h"] for d in data], float)
    m = np.array([mat_idx(d["paper"]) for d in data]); q = np.array([d["qty"] for d in data], float)
    c1 = np.array([1 if "1C" in d["colour"] else 0 for d in data])
    cash = np.array([d["cash"] for d in data], float)
    keys = [(d["h"], d["w"], d["paper"], d["colour"]) for d in data]
    rng = np.random.default_rng(7); uniq = list({k for k in keys}); rng.shuffle(uniq)
    hold = set(uniq[: max(1, len(uniq) // 4)])
    tr = [i for i, k in enumerate(keys) if k not in hold]
    te = [i for i, k in enumerate(keys) if k in hold]

    def predict(p, idx):
        return np.array([_predict_one(p, w[i], h[i], m[i], c1[i], q[i]) for i in idx])

    def loss(p):
        pred = predict(p, tr)
        ape = np.abs(pred - cash[tr]) / cash[tr]
        # blend median (robust) + mean (so premium materials like Warranty, which are
        # a minority of points, aren't ignored by a pure-median objective)
        return float(0.5 * np.median(ape) + 0.5 * np.mean(ape))

    nmat = len(MATERIALS)
    bounds = [(1.0, 3.0), (0, 40), (0.01, 30), (0.5, 1.05),      # margin, setup, rate, gamma
              (200, 760), (200, 760), (200, 760), (200, 760), (2, 20)] + \
             [(0.3, 9.0)] * nmat + [(0.3, 1.0)]                  # 2 sheets + bleed; mat mults; 1C factor
    res = differential_evolution(loss, bounds, maxiter=400, popsize=30, seed=7,
                                 tol=1e-7, workers=1, polish=True)
    p = list(res.x)
    # Two-stage: re-center a MATERIAL multiplier to its empirical median ratio ONLY
    # when the global fit leaves it badly off (>15% median), so premium materials
    # (e.g. Warranty ~5.5x) get corrected without disturbing the well-fit majority.
    allidx = list(range(len(cash)))
    for mi in range(nmat):
        sub = [i for i in allidx if m[i] == mi]
        if len(sub) < 3:
            continue
        cur = predict(p, sub)
        if float(np.median(np.abs(cur - cash[sub]) / cash[sub])) <= 0.15:
            continue
        p_unit = list(p); p_unit[9 + mi] = 1.0
        pred1 = predict(p_unit, sub)
        p[9 + mi] = max(0.05, float(np.median(cash[sub] / pred1)))
    (OUT / f"sticker_params_{method}.json").write_text(
        json.dumps({"params": p, "materials": MATERIALS}, indent=1))

    def stat(name, idx):
        pred = predict(p, idx); e = np.abs(pred - cash[idx]) / cash[idx] * 100
        print(f"{name}: n={len(idx)} MAPE {e.mean():.1f}% median {np.median(e):.1f}% "
              f"<=5% {(e<=5).mean()*100:.0f}% <=10% {(e<=10).mean()*100:.0f}% "
              f"<=15% {(e<=15).mean()*100:.0f}%")
        return e
    print(f"sheets={p[4]:.0f}x{p[5]:.0f},{p[6]:.0f}x{p[7]:.0f} bleed={p[8]:.1f} margin={p[0]:.2f} "
          f"setup={p[1]:.1f} rate={p[2]:.2f} gamma={p[3]:.3f} 1Cfac={p[-1]:.2f}")
    stat("TRAIN", tr); e = stat("TEST (held-out sizes/configs)", te)
    (OUT / f"spot_test_report_sticker_{method}.json").write_text(json.dumps({
        "product": f"label_sticker_{method}", "sample_points": len(data),
        "median": round(float(np.median(e)), 2),
        "within_5pct": round(float((e <= 5).mean() * 100)),
        "within_10pct": round(float((e <= 10).mean() * 100)),
        "mape": round(float(e.mean()), 2), "method": "imposition formula (sticker)"}, indent=1))
    print(f"saved -> sticker_params_{method}.json")


if __name__ == "__main__":
    calibrate_and_report(sys.argv[1] if len(sys.argv) > 1 else "digital")
