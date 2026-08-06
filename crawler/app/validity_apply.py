"""Generate EXACT conditional validity (showWhen visibility + validity option-rules) for each
product from its live-form capture (output/validity/<id>.json via app.validity_capture), and apply
it to the calculator fields. Driven by the supplier's actual per-selection behaviour, so it's exact
(e.g. loose-sheet lamination is by paper WEIGHT, not a 'Card' heuristic).

Called from build_standalone AFTER the fields exist. Idempotent.
"""
from __future__ import annotations
import json
from pathlib import Path
from app.parity_common import norm
from app.validity_analyze import analyze

OUT = Path(__file__).resolve().parent.parent / "output"
VDIR = OUT / "validity"


def _strip(lbl):
    return lbl.replace("*", "").strip()


def _field_for(label, fields):
    """Match a captured control/driver label to one of our fields (by normalized label/key)."""
    n = norm(_strip(label))
    if not n:
        return None
    best = None
    for f in fields:
        fk, fl = norm(f.get("key", "")), norm(f.get("label", ""))
        if n == fl or n == fk or (fl and (n in fl or fl in n)) or (fk and (n in fk or fk in n)):
            # prefer exact label match
            if n == fl or n == fk:
                return f
            best = best or f
    return best


import re

# _loose_sheet_exact owns the loose-sheet litho family (richer compound/mutual-exclusion rules);
# don't let the generic applier overwrite those.
_SKIP_PIDS = {21, 101, 102, 103}


def _toks(s):
    return set(re.findall(r"[a-z]+|\d+", str(s).lower()))


def _map_values(capvals, options):
    """Map captured driver values (e.g. 'Gloss Art Card 250gsm ') to OUR exact option strings by
    token-set containment (tolerates our extra suffixes like '(2 sides coated) - Best Seller')."""
    out = []
    for cv in capvals:
        ct = _toks(cv)
        if not ct:
            continue
        best, best_ov = None, -1
        for o in options:
            ot = _toks(o)
            if ct <= ot:                          # every captured token present in our option
                ov = len(ct & ot)
                if ov > best_ov:
                    best_ov, best = ov, o
        if best and best not in out:
            out.append(best)
    return out


def apply(data):
    if not VDIR.is_dir():
        return 0
    by_id = {p["id"]: p for p in data["products"]}
    n_vis = n_opt = 0
    for f in VDIR.glob("*.json"):
        cap = json.loads(f.read_text(encoding="utf-8"))
        p = by_id.get(cap.get("id"))
        if not p or not cap.get("variations") or cap.get("id") in _SKIP_PIDS:
            continue
        fields = p["fields"]
        r = analyze(cap)

        # 1) conditional VISIBILITY -> showWhen {field: driver, values: mapped shownWhen}
        for v in r["visibility"]:
            ctrl_f = _field_for(v["control"], fields)
            drv_f = _field_for(v["driverLabel"], fields)
            if not ctrl_f or not drv_f or ctrl_f is drv_f:
                continue
            vals = _map_values(v["shownWhen"], drv_f.get("options") or [])
            if len(vals) >= 1 and len(vals) < len(drv_f.get("options") or []):
                ctrl_f["showWhen"] = {"field": drv_f["key"], "values": vals}
                n_vis += 1

        # 2) conditional OPTIONS -> validity (single primary = the most common driver)
        opt_rules = {}          # {driver_field_key: {driver_value: {ctrl_key: [opts]}}}
        for o in r["options"]:
            ctrl_f = _field_for(o["control"], fields)
            drv_f = _field_for(o["driverLabel"], fields)
            if not ctrl_f or not drv_f or ctrl_f is drv_f or not ctrl_f.get("options"):
                continue
            drv_opts = drv_f.get("options") or []
            per = opt_rules.setdefault(drv_f["key"], {})
            for dval, capopts in o["optionsByValue"].items():
                our_dval = (_map_values([dval], drv_opts) or [None])[0]
                our_opts = _map_values(capopts, ctrl_f["options"])
                if our_dval and our_opts:
                    per.setdefault(our_dval, {})[ctrl_f["key"]] = our_opts
        if opt_rules:
            primary = max(opt_rules, key=lambda k: len(opt_rules[k]))   # driver covering most values
            rules = opt_rules[primary]
            fkeys = sorted({fk for r_ in rules.values() for fk in r_})
            existing = p.get("validity") or {}
            if existing.get("primary") in (None, primary):
                merged = existing.get("rules", {})
                for dv, m in rules.items():
                    merged.setdefault(dv, {}).update(m)
                p["validity"] = {"primary": primary, "fields": sorted(set(existing.get("fields", [])) | set(fkeys)),
                                 "rules": merged}
                n_opt += len(fkeys)
    print(f"validity: applied {n_vis} conditional-visibility + {n_opt} option rules from live captures")
    return n_vis + n_opt
