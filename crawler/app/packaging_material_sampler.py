"""Sample which materials each box actually supports, via the member packaging pricing API
(it returns "Cannot find material MID=..." for a material a box template doesn't support). Writes
output/packaging_box_materials.json = {boxcode: [valid MIDs]}.  Validity (success/fail) is not a
price, so light concurrency is safe.  python -m app.packaging_material_sampler
"""
from __future__ import annotations
import json, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from app.packaging_api import bootstrap_session, Packaging

OUT = Path(__file__).resolve().parent.parent / "output"
MATS = ["M0024", "M0001", "M0003", "M0006", "M0007", "M0011", "M0012", "M0013",
        "M0014", "M0015", "M0103", "M0106", "M0109", "M0021"]


def _size(lim):
    """A valid mid-ish size within the box's limits."""
    L = (lim.get("L") or 100) + 20
    W = (lim.get("W") or 100) + 20
    dmin = lim.get("Dmin") or 20
    D = dmin + 20
    return L, W, D


def main(workers=3):
    cat = json.loads((OUT / "packaging_catalogue_ui.json").read_text(encoding="utf-8"))
    boot = bootstrap_session(1)
    token = boot.token
    cookies = {k: v for k, v in boot.s.cookies.items()}
    print(f"token {len(token)} cookies {list(cookies)}", file=sys.stderr)

    def valid_mats(box, lim):
        pk = Packaging(box=box["code"], token=token, cookies=cookies)
        L, W, D = _size(lim)
        ok = []
        for m in MATS:
            try:
                rows = pk.price(box["code"], L, W, D, 300, material=m)
                if rows:
                    ok.append(m)
            except Exception as e:
                if "Cannot find material" not in str(e):
                    print(f"  {box['code']} {m} unexpected: {str(e)[:60]}", file=sys.stderr)
        return box["code"], ok

    result = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(valid_mats, b, b.get("limits", {})): b["code"] for b in cat}
        for f in as_completed(futs):
            code, ok = f.result()
            result[code] = ok
            print(f"   {code:7} {len(ok):2} mats: {ok}", file=sys.stderr)
    result = {k: result[k] for k in sorted(result)}
    (OUT / "packaging_box_materials.json").write_text(json.dumps(result, indent=0), encoding="utf-8")
    from collections import Counter
    dist = Counter(len(v) for v in result.values())
    print(f"wrote packaging_box_materials.json: {len(result)} boxes; material-count distribution {dict(dist)}")


if __name__ == "__main__":
    main()
