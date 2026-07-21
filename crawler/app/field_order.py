"""Arrange each product's configuration fields in the SAME sequence the supplier's order form
uses, so customers see options in the order they expect.

The order form's control sequence is captured in DOM order in output/option_audit/<slug>.json.
Control NAMES are inconsistent across products (cardType / rblCategory / paperType / ddlPaper),
so we match each supplier control to one of our fields by its OPTION VALUES (which we mirror for
option parity) — a Jaccard match on the normalised option sets, with a name fallback.

Fields with a `showWhen` parent are always kept directly after that parent, and fields with no
supplier counterpart (our `ex_*` extras) keep their relative order at the end.

  python -m app.field_order          # report the reordering per product
"""
from __future__ import annotations
import json, re
from pathlib import Path

from app.build_specs_page import clean_name
from app.product_quantity import _base_slug, _ALIAS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
AUDIT = OUT / "option_audit"

# controls that aren't product configuration (delivery, quantity, plumbing)
_SKIP = re.compile(
    r"country|courier|track|review|rush|favourite|quantity|qty|customsize|customquantity|"
    r"vdp|isalquran|artwork|remark|upload|file|search|login|password|email", re.I)
_PREFIX = re.compile(r"^(rbl|ddl|txt|chk|cbo|combo|lst|is)", re.I)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _norm_name(s: str) -> str:
    return _norm(_PREFIX.sub("", str(s)))


def excard_sequence(slug: str):
    """[(control_name, {normalised option values})] in the supplier's on-page order."""
    f = AUDIT / f"{slug}.json"
    if not f.is_file():
        return None
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None
    seq = []
    for c in d.get("controls", []):
        nm = c.get("name") or ""
        if not nm or _SKIP.search(nm):
            continue
        opts = [o for o in (c.get("options") or []) if not re.match(r"^\s*[-–]{0,2}\s*(please\s+)?select", str(o), re.I)]
        if len(opts) < 2:
            continue
        seq.append((nm, {_norm(o) for o in opts}))
    return seq


def _match(fields, seq):
    """field index -> supplier position, by best option-set overlap (greedy, one-to-one)."""
    fopts = []
    for f in fields:
        vals = {_norm(o) for o in (f.get("options") or [])}
        fopts.append(vals)
    pairs = []
    for si, (sname, sopts) in enumerate(seq):
        for fi, fo in enumerate(fopts):
            if not fo or not sopts:
                continue
            inter = len(fo & sopts)
            if not inter:
                continue
            jac = inter / len(fo | sopts)
            pairs.append((jac, si, fi))
    pairs.sort(reverse=True)
    used_s, used_f, pos = set(), set(), {}
    for jac, si, fi in pairs:
        if jac < 0.34 or si in used_s or fi in used_f:
            continue
        used_s.add(si); used_f.add(fi); pos[fi] = si
    # name fallback for still-unmatched fields (e.g. number inputs with no options)
    for fi, f in enumerate(fields):
        if fi in used_f:
            continue
        fk = _norm(f.get("key", ""))
        for si, (sname, _o) in enumerate(seq):
            if si in used_s:
                continue
            sn = _norm_name(sname)
            if fk and sn and (fk == sn or fk in sn or sn in fk):
                used_s.add(si); used_f.add(fi); pos[fi] = si
                break
    return pos


def reorder_fields(product):
    """Return the product's fields resequenced to the supplier's order (or None if no audit)."""
    slug = _base_slug(product["name"])
    seq = excard_sequence(_ALIAS.get(slug, slug)) or excard_sequence(slug)
    if not seq:
        return None
    fields = product.get("fields") or []
    if not fields:
        return None
    pos = _match(fields, seq)
    if not pos:
        return None
    # Confidence gate: only resequence when we've confidently matched most of the option-bearing
    # fields. A weak match (e.g. a control captured empty) would otherwise strand real fields at
    # the end — worse than leaving our existing order alone.
    with_opts = sum(1 for f in fields if f.get("options"))
    if with_opts and len(pos) / with_opts < 0.6:
        return None
    # Matched fields take the supplier's position. An UNMATCHED field (e.g. a size control that
    # was empty at capture time) stays anchored right after the last matched field that preceded
    # it originally, so it never gets dumped at the end.
    keyed, last, sub = [], -1, 0
    for i, f in enumerate(fields):
        if i in pos:
            last, sub = pos[i], 0
            keyed.append(((last, 0, i), f))
        else:
            sub += 1
            keyed.append(((last, sub, i), f))
    keyed.sort(key=lambda t: t[0])
    ordered = [f for _k, f in keyed]
    # keep conditional sub-fields directly after their parent
    by_key = {f.get("key"): f for f in ordered}
    out, placed = [], set()
    for f in ordered:
        k = f.get("key")
        if k in placed:
            continue
        sw = f.get("showWhen")
        if sw and sw.get("field") in by_key and sw["field"] not in placed:
            continue          # parent not emitted yet — it will pull this child in
        out.append(f); placed.add(k)
        for c in ordered:
            ck = c.get("key")
            if ck in placed:
                continue
            csw = c.get("showWhen")
            if csw and csw.get("field") == k:
                out.append(c); placed.add(ck)
    for f in ordered:                                  # safety: nothing dropped
        if f.get("key") not in placed:
            out.append(f); placed.add(f.get("key"))
    return out


def reorder(data):
    n = changed = 0
    for p in data["products"]:
        new = reorder_fields(p)
        n += 1
        if new and [f.get("key") for f in new] != [f.get("key") for f in p.get("fields") or []]:
            p["fields"] = new
            changed += 1
        elif new:
            p["fields"] = new
    return n, changed


if __name__ == "__main__":
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))
    for p in data["products"]:
        before = [f.get("key") for f in p.get("fields") or []]
        new = reorder_fields(p)
        if new:
            after = [f.get("key") for f in new]
            if after != before:
                print(f"\n{clean_name(p['name'])}")
                print("  before:", before)
                print("  after :", after)
    n, changed = reorder(data)
    print(f"\n{changed}/{n} products resequenced to the supplier's option order")
