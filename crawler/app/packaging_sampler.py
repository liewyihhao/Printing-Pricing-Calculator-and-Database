"""Sample Excard packaging prices via the GetPriceFactor2 API (threaded, our-own engine
calibration). One bootstrap (Playwright login) gets the token+cookies, then requests
fires threaded. Each (box, dims) call returns the WHOLE qty ladder (Qtys is an array).

Also captures one dieline per box (LinTest3D) for the P2 3D renderer.

Saves output/packaging_samples.json {box: [{L,W,D,qty,total,unit,unit_weight,netarea,area,no,color}]}
      output/packaging_dielines.json {box: {BoxJson, LineExp}}

  python -m app.packaging_sampler [account]
"""
from __future__ import annotations
import json, sys, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from .packaging_api import bootstrap_session
from .logging_setup import log

OUT = Path(__file__).resolve().parent.parent / "output"
QTYS = [100, 200, 300, 500, 1000, 2000, 3000, 5000]


def _dims(lim):
    """A small representative L×W×D grid within a box's limits."""
    L0 = (lim.get("L") or [50])[0] or 50
    W0 = (lim.get("W") or [50])[0] or 50
    Darr = lim.get("D") or [50]
    D0 = Darr[0] or 50
    Dmax = Darr[2] if len(Darr) > 2 and Darr[2] else D0 * 4
    def cD(d): return int(max(D0, min(d, Dmax)))
    cand = [(L0, W0, D0),
            (L0 + 30, W0 + 20, cD(D0 + 30)),
            (max(L0, 100), max(W0, 80), cD(max(D0, 50))),
            (max(L0, 150), max(W0, 100), cD(max(D0, 80))),
            (L0 * 2, W0 * 2, cD(min(D0 * 2, Dmax)))]
    seen, out = set(), []
    for t in cand:
        t = (int(t[0]), int(t[1]), int(t[2]))
        if t not in seen:
            seen.add(t); out.append(t)
    return out


def run(account_id=1):
    cat = json.loads((OUT / "packaging_catalogue.json").read_text())
    lim = json.loads((OUT / "packaging_globals" / "boxPmsLimit.json").read_text())
    boxes = [b["BoxID"] for b in cat if b.get("On")]
    samples_f = OUT / "packaging_samples.json"
    diel_f = OUT / "packaging_dielines.json"
    samples = json.loads(samples_f.read_text()) if samples_f.exists() else {}
    dielines = json.loads(diel_f.read_text()) if diel_f.exists() else {}

    pk = bootstrap_session(account_id)
    if not pk.token:
        raise SystemExit("no token — login/bootstrap failed")
    log.info("pkg.boot", token_len=len(pk.token), cookies=list(pk.s.cookies.keys()))
    lock = threading.Lock()

    def do_box(box):
        if box in samples and len(samples[box]) >= len(_dims(lim.get(box, {}))) * len(QTYS) - 2:
            return box, "skip"
        rows = []
        for (L, W, D) in _dims(lim.get(box, {})):
            try:
                for r in pk.price(box, L, W, D, QTYS):
                    dic = r.get("dic", {})
                    rows.append({"L": L, "W": W, "D": D, "qty": r["qty"], "total": r["total"],
                                 "unit": r["unit"], "unit_weight": r["unit_weight"],
                                 "netarea": dic.get("netarea"), "area": dic.get("area"),
                                 "no": dic.get("no"), "color": dic.get("color")})
            except Exception as e:  # noqa: BLE001
                log.info("pkg.price_err", box=box, dims=f"{L}x{W}x{D}", err=str(e)[:60])
        # one dieline at the mid size
        if box not in dielines:
            try:
                mid = _dims(lim.get(box, {}))[min(2, len(_dims(lim.get(box, {}))) - 1)]
                dl = pk.dieline(box, *mid)
                with lock:
                    dielines[box] = dl; diel_f.write_text(json.dumps(dielines))
            except Exception as e:  # noqa: BLE001
                log.info("pkg.diel_err", box=box, err=str(e)[:60])
        with lock:
            samples[box] = rows; samples_f.write_text(json.dumps(samples))
        return box, len(rows)

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(do_box, b): b for b in boxes}
        done = 0
        for f in as_completed(futs):
            box, n = f.result(); done += 1
            log.info("pkg.box", box=box, n=n, prog=f"{done}/{len(boxes)}")
    samples_f.write_text(json.dumps(samples))
    print(f"wrote {samples_f.name}: {len(samples)} boxes, "
          f"{sum(len(v) for v in samples.values())} price points; dielines={len(dielines)}")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
