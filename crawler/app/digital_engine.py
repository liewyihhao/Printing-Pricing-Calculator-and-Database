"""Printoka pure-formula engine — DIGITAL Loose Sheet (product 50).

Digital economics: NO plates. Charged per "click" (impression) per side per sheet.
Cost is ~linear in quantity (flat per-unit) — unlike offset which drops steeply with
volume. We encode that with a volume exponent `gamma` that is ~1.0 for digital
(little economy of scale) vs <1 for offset.

  sheets = ceil(qty / ups[size])              # imposition on a digital SRA3 sheet
  cash = margin * ( setup
                    + ( sides*click_rate[colour]                       # press clicks
                        + sra3_kg(gsm)*paper_RM[cat] ) * sheets        # paper
                    * (qty ** (gamma-1)) )                             # ~1 -> flat
Calibrated against a spot-test SAMPLE (output/spot_samples_50.json); params frozen to
output/printoka_params_digital.json. Runtime = pure formula (no price lookups).
"""
from __future__ import annotations
import re, json
import numpy as np
from pathlib import Path

CATS = ["Simili", "Gloss Art Paper", "Matte Art Paper", "Gloss Art Card", "Fine Card"]
FINE = ("Linen", "Metal Ice", "Synthetic", "Super White", "Suwen", "Vellum")
PARAMS_FILE = Path(__file__).resolve().parent.parent / "output" / "printoka_params_digital.json"
SAMPLES = Path(__file__).resolve().parent.parent / "output" / "spot_samples_50.json"
SRA3 = (320, 450)            # digital press sheet (mm)
TIER_DISCOUNTS = {"Cash": 0.0, "Silver": 0.04, "Gold": 0.08, "Platinum": 0.14}
WEIGHT_FACTOR = 1.2065


def cat_of(p):
    if any(f.lower() in p.lower() for f in FINE):
        return 4
    for i, c in enumerate(CATS[:4]):
        if c.lower() in p.lower():
            return i
    return 1


def dims(size_label):
    m = re.search(r"(\d+)\s*mm\s*x\s*(\d+)\s*mm", size_label)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def gsm_of(p):
    m = re.search(r"(\d+)\s*gsm", p)
    return int(m.group(1)) if m else (180 if "micron" in p.lower() else 250)


def sides_of(colour):
    return 2 if "Both" in colour else 1


def ups(w, h, bleed=4, grip=8):
    W, H = SRA3[0] - grip, SRA3[1] - grip
    a = (W // (w + bleed)) * (H // (h + bleed))
    b = (W // (h + bleed)) * (H // (w + bleed))
    return max(1, a, b)


def _predict(p, w, h, gsm, sides, qty, cat):
    setup, margin, gamma, c4 = p[:4]
    paper = np.array(p[4:9])[cat]
    sheets = np.ceil(qty / np.array([ups(int(wi), int(hi)) for wi, hi in zip(w, h)]))
    sra3_kg = (SRA3[0] * SRA3[1] / 1e6) * gsm / 1000.0
    var = (sides * c4 + sra3_kg * paper) * sheets * np.power(qty, gamma - 1)
    return margin * (setup + var)


def cash_price(size, paper_label, colour, qty, params=None):
    if params is None:
        params = load_params()
    w, h = dims(size)
    return float(_predict(np.array(params), np.array([w]), np.array([h]),
                          np.array([gsm_of(paper_label)]), np.array([sides_of(colour)]),
                          np.array([qty]), np.array([cat_of(paper_label)]))[0])


def tiers(cash):
    return {t: round(cash * (1 - d), 2) for t, d in TIER_DISCOUNTS.items()}


def weight_kg(size, paper_label, qty):
    w, h = dims(size)
    return round((w * h / 1e6) * gsm_of(paper_label) * qty / 1000.0 * WEIGHT_FACTOR, 2)


def load_params():
    if PARAMS_FILE.exists():
        return json.loads(PARAMS_FILE.read_text())["params"]
    raise RuntimeError("Digital not calibrated — run: python -m app.digital_engine")


def calibrate_and_report():
    from scipy.optimize import differential_evolution
    data = json.loads(SAMPLES.read_text())
    rows = [(dims(d["size"]), gsm_of(d["paper"]), sides_of(d["colour"]), d["qty"],
             cat_of(d["paper"]), float(d["cash"]),
             (d["size"], d["paper"], d["colour"])) for d in data if d.get("cash")]
    rng = np.random.default_rng(7)
    w = np.array([r[0][0] for r in rows]); h = np.array([r[0][1] for r in rows])
    g = np.array([r[1] for r in rows]); sd = np.array([r[2] for r in rows])
    q = np.array([r[3] for r in rows], float); cat = np.array([r[4] for r in rows])
    cash = np.array([r[5] for r in rows]); keys = [r[6] for r in rows]
    uniq = list({k for k in keys}); rng.shuffle(uniq)
    hold = set(uniq[: max(1, len(uniq)//4)])
    tr = np.array([i for i, k in enumerate(keys) if k not in hold])
    te = np.array([i for i, k in enumerate(keys) if k in hold])

    def loss(p):
        pred = _predict(p, w[tr], h[tr], g[tr], sd[tr], q[tr], cat[tr])
        return float(np.median(np.abs(pred - cash[tr]) / cash[tr]))

    # gamma bounded near 1 (digital flat); c4 = per-side click rate
    bounds = [(0, 50), (1.0, 3.0), (0.85, 1.02), (0.05, 2.0),
              (1, 18), (1, 18), (1, 18), (1, 18), (1, 25)]
    res = differential_evolution(loss, bounds, maxiter=200, popsize=25, seed=7,
                                 tol=1e-6, workers=1, polish=True)
    p = res.x
    PARAMS_FILE.write_text(json.dumps({"params": list(p), "cats": CATS}, indent=1))

    def stat(name, idx):
        pred = _predict(p, w[idx], h[idx], g[idx], sd[idx], q[idx], cat[idx])
        e = np.abs(pred - cash[idx]) / cash[idx] * 100
        print(f"{name}: n={len(idx)} MAPE {e.mean():.1f}% median {np.median(e):.1f}% "
              f"<=3% {(e<=3).mean()*100:.0f}% <=5% {(e<=5).mean()*100:.0f}% "
              f"<=10% {(e<=10).mean()*100:.0f}% under {(pred<cash[idx]).mean()*100:.0f}%")
    print(f"params: setup={p[0]:.1f} margin={p[1]:.2f} gamma={p[2]:.3f} click={p[3]:.2f} "
          f"paper={[round(x,1) for x in p[4:]]}")
    stat("TRAIN", tr)
    stat("TEST (held-out configs)", te)
    print(f"saved -> {PARAMS_FILE}")


if __name__ == "__main__":
    calibrate_and_report()
