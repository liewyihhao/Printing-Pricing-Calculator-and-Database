"""Option-parity gap audit: for every product, compare the supplier's order-form controls
(output/option_audit/) against the fields our calculator exposes, and list controls we don't
show. Backs the project standard that a product isn't done until our UI mirrors EVERY supplier
option — including price-neutral and single-value ones (see memory
'completion-requires-full-option-parity').

Delivery/courier/quantity/VDP-internal controls are excluded (handled separately). Name
mismatches can produce false positives (e.g. Business Card 'cardType' is our 'Category'), so
treat the output as a review list, not a defect list.

  python -m app.option_gap_audit [--verbose]
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

from app.build_specs_page import clean_name
from app.product_quantity import _base_slug, _ALIAS

OUT = Path(__file__).resolve().parent.parent / "output"
AUDIT = OUT / "option_audit"

# controls handled elsewhere or not customer-facing options
SKIP = re.compile(r"country|courier|quantity|qty|review|favourite|rush|track|customsize|"
                  r"^txt|^chk|numberfr|numberto|vdp|k100|m100|eyelet|seal|fastener|alquran", re.I)
# our field key/label aliases for supplier control names that differ
ALIASES = {"cardtype": "category", "printmethod": "method", "product": "model",
           "type": "category", "bagcolour": "bag_colour", "handlecolour": "handle_colour"}


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def audit():
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))["products"]
    gaps = {}
    for p in data:
        slug = _base_slug(p["name"])
        slug = _ALIAS.get(slug, slug)
        f = AUDIT / f"{slug}.json"
        if not f.is_file():
            continue
        aud = json.loads(f.read_text(encoding="utf-8"))
        ours = {_norm(x.get("key", "")) for x in p.get("fields", [])}
        ours |= {_norm(x.get("label", "")) for x in p.get("fields", [])}
        ours.discard("")
        # every option VALUE we already expose anywhere on this product
        ourvals = {_norm(v) for x in p.get("fields", []) for v in (x.get("options") or []) if _norm(v)}
        miss = []
        for c in aud.get("controls", []):
            nm = c.get("name", "")
            opts = [o for o in (c.get("options") or []) if not str(o).strip().startswith(("-", "—"))]
            if not opts or SKIP.search(nm):
                continue
            ctrl = _norm(re.sub(r"^(rbl|ddl|combo)", "", nm))
            ctrl = ALIASES.get(ctrl, ctrl)
            if not ctrl:
                continue
            if any(ctrl in o or o in ctrl for o in ours):
                continue                                   # covered by a matching field name
            # covered if we already show its values (control renamed on our side)
            hit = sum(1 for o in opts if _norm(o) in ourvals)
            if hit and hit >= max(1, len(opts) // 2):
                continue
            miss.append({"control": nm, "options": opts[:6], "n": len(opts)})
        if miss:
            gaps[p["id"]] = {"name": clean_name(p["name"]), "missing": miss}
    return gaps


if __name__ == "__main__":
    g = audit()
    verbose = "--verbose" in sys.argv
    total = sum(len(v["missing"]) for v in g.values())
    print(f"option-parity review: {len(g)} products, {total} un-exposed supplier controls\n")
    for pid, v in sorted(g.items(), key=lambda kv: -len(kv[1]["missing"])):
        print(f"  [{pid}] {v['name'][:36]:36} {[m['control'] for m in v['missing']]}")
        if verbose:
            for m in v["missing"]:
                print(f"        {m['control']:28} ({m['n']}) {m['options']}")
    (OUT / "option_gap_audit.json").write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nwrote output/option_gap_audit.json")
