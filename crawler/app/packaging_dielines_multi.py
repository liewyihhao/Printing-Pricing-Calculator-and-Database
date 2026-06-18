"""Capture each box's dieline at SEVERAL sizes (small/mid/large/tall) so the viewer can
show the dieline nearest to the user's chosen dimensions — works offline (no live call).

Saves output/packaging_dielines_multi.json {box: [{dims:[L,W,D], BoxJson, LineExp}, ...]}

  python -m app.packaging_dielines_multi [account]
"""
from __future__ import annotations
import json, sys, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from .packaging_api import bootstrap_session
from .logging_setup import log

OUT = Path(__file__).resolve().parent.parent / "output"


def _sizes(lim):
    L0 = (lim.get("L") or [50])[0] or 50
    W0 = (lim.get("W") or [50])[0] or 50
    Darr = lim.get("D") or [50]; D0 = Darr[0] or 50
    Dmax = Darr[2] if len(Darr) > 2 and Darr[2] else D0 * 4
    cD = lambda d: int(max(D0, min(d, Dmax)))
    return [(L0, W0, D0), (max(L0, 90), max(W0, 70), cD(max(D0, 50))),
            (max(L0, 150), max(W0, 110), cD(max(D0, 90))), (L0 * 2, W0 * 2, cD(D0 * 2))]


def run(account_id=1):
    lim = json.loads((OUT / "packaging_globals" / "boxPmsLimit.json").read_text())
    cat = [b["BoxID"] for b in json.loads((OUT / "packaging_catalogue.json").read_text()) if b.get("On")]
    out_f = OUT / "packaging_dielines_multi.json"
    data = json.loads(out_f.read_text()) if out_f.exists() else {}
    pk = bootstrap_session(account_id); lock = threading.Lock()
    if not pk.token:
        raise SystemExit("bootstrap failed")

    def do(box):
        if box in data and len(data[box]) >= 3:
            return box, "skip"
        seen, items = set(), []
        for dims in _sizes(lim.get(box, {})):
            if dims in seen:
                continue
            seen.add(dims)
            try:
                dl = pk.dieline(box, *dims)
                if dl and dl.get("LineExp"):
                    items.append({"dims": list(dims), "BoxJson": dl["BoxJson"], "LineExp": dl["LineExp"]})
            except Exception as e:  # noqa: BLE001
                log.info("diel.err", box=box, dims=dims, err=str(e)[:40])
        with lock:
            data[box] = items; out_f.write_text(json.dumps(data))
        return box, len(items)

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(do, b): b for b in cat}
        done = 0
        for f in as_completed(futs):
            box, n = f.result(); done += 1
            log.info("diel.box", box=box, n=n, prog=f"{done}/{len(cat)}")
    print(f"wrote {out_f.name}: {len(data)} boxes, {sum(len(v) for v in data.values())} dielines")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
