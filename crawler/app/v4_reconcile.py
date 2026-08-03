"""SPA-aware parity reconcile: compare each product's LIVE v4 form capture (output/v4_form/<id>.json
from app.v4_form_capture) against our calculator fields, so gaps the www-based audits can't see are
surfaced. Reports, per product:
  * SECTION mismatches — our field's section vs the supplier's actual section header.
  * PRESENCE gaps      — supplier controls (in General/Finishing/Add-On) with no field of ours.
  * VALUE gaps         — matched controls where we don't offer every supplier option value.

  python -m app.v4_reconcile [--verbose]
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from app.parity_common import norm
from app.build_specs_page import clean_name

OUT = Path(__file__).resolve().parent.parent / "output"
FDIR = OUT / "v4_form"

# Supplier section headers that are NOT product-config sections (delivery / quantity / chrome).
_SKIP_SEC = {"delivery", "net price for deal", "add name", "quantity", "artwork", "summary", "add-on info"}

# Shared-form template artefacts — controls the supplier form lists for a product but that aren't a
# real option for IT (verified). Label-Sticker Letterpress (foil on limited stock) shares the digital
# label form, so its print Paper/Package/Lamination/Cutting/Order-Type/Print-Colour aren't used;
# Label-Sticker Digital's "Cutting Method" is subsumed by our shape category (Cut-to-Size == Rect).
_NOT_OPTIONS = {
    61: {"order type", "paper", "package", "lamination", "cutting method", "print colour", "category"},
    60: {"cutting method"},
}
# control names that are page chrome / delivery / quantity / legacy ASP.NET internals — never a
# real product option axis
_SKIP_CTRL = re.compile(r"country|courier|qty|quantity|favourite|rush|track|custom.?size|"
                        r"^ddlproduct$|review|otherorder|ctl00|order_spec|dnn|__|^$", re.I)
# placeholder / non-value options: "-- Select Size --", "- Please Select -", "Not Required", etc.
_JUNK = re.compile(r"^\s*-*\s*(please\s*)?select\b|^\s*-{1,}\s*$|^\s*-{2}|not required|^none$|^$", re.I)


def sec_label(name):
    """Normalise a supplier section header to a clean display label (Title Case, known phrases)."""
    return " ".join(w.capitalize() for w in str(name).strip().split())


def _clean_opts(opts):
    return [o for o in (opts or []) if o and not _JUNK.search(o.strip())]


# Notation-tolerant token set: unifies supplier vs our wording so genuine matches aren't flagged
# as gaps — swapped dimensions (105×148 == 148×105), filler words (Paper / Best Seller / (NEW) /
# 2-sides-coated), and any "No X" / "None" negative == our "Not Required".
_NEG = re.compile(r"not required|no required|not require|^\s*none\s*$|no lamination|no hot ?stamping|"
                  r"no fold(ing)?|no cutting|not ?applicable", re.I)
_FILLER = re.compile(r"best ?seller|2 ?sides? ?coated|\bpaper\b|\bnew\b|\bcolour\b|\bcolor\b", re.I)


def _canon(s):
    """Order-insensitive token set for a value (words >= 2 chars + numbers), after negatives and
    filler words are normalised. Two values with the same set are the same option in different
    wording (e.g. 'Pink A6 (108mm × 159mm)' == '108mm x 159mm - Pink A6', or
    'Hot Stamping - 1 Colour (Front)' == '1C (Front)')."""
    if _NEG.search(str(s)):
        return frozenset({"__none__"})
    s = str(s).lower().replace("×", "x")
    s = re.sub(r"(\d+)\s*c\b|(\d+)\s*colours?", lambda m: (m.group(1) or m.group(2)) + "c", s)  # 1 Colour->1c
    s = re.sub(r"laminat(e|ion)", "laminat", s)                       # Laminate == Lamination
    s = re.sub(r"poly\s*p\w*ylene", "pp", s)                          # Polyprop(h)ylene typo
    s = re.sub(r"hot ?stamping|hole ?punching|diameter|binding|side", " ", s)   # descriptor words
    s = _FILLER.sub(" ", s)
    return frozenset(re.findall(r"\d+c|[a-z]{2,}|\d+", s))


def _sec_of_rows(rows):
    """Walk capture rows, yielding (section_label, control_dict) for real config controls, using the
    supplier's ACTUAL section labels (General / Optional Finishing / Add On / Cover / Content / …).
    Controls before the first section header, or under a skip section, are ignored."""
    cur = None                          # nothing counts until the first real config section header
    for r in rows:
        if r.get("kind") == "section":
            nm = r["name"].strip().lower()
            cur = None if nm in _SKIP_SEC else sec_label(r["name"])
        elif r.get("kind") == "control":
            if cur is None or _SKIP_CTRL.search(r.get("name", "")):
                continue
            yield cur, r


def reconcile_one(prod, cap):
    fields = prod.get("fields", [])
    our = []
    for f in fields:
        our.append({"key": norm(f.get("key", "")), "label": norm(f.get("label", "")),
                    "opts": {norm(o) for o in (f.get("options") or []) if norm(o)},
                    "canon": {_canon(o) for o in (f.get("options") or []) if str(o).strip()},
                    "section": f.get("section", "general"), "raw": f})
    all_opts = {v for f in our for v in f["opts"]}          # every value selectable anywhere
    all_canon = {c for f in our for c in f["canon"]}
    not_options = _NOT_OPTIONS.get(prod.get("id"), set())
    presence, values, section = [], [], []
    for sec, c in _sec_of_rows(cap.get("rows", [])):
        if (c.get("label", "").rstrip(" *").strip().lower()) in not_options:
            continue                                        # shared-form template artefact for this product
        cname, clabel = norm(c.get("name", "")), norm(c.get("label", ""))
        copts = {norm(o) for o in _clean_opts(c.get("options"))}
        # match to our field: name/label containment, or strong option overlap
        best, best_score = None, 0.0
        for f in our:
            nm = bool(cname) and (cname in f["key"] or f["key"] in cname or cname in f["label"] or clabel and clabel in f["label"])
            jac = len(copts & f["opts"]) / len(copts | f["opts"]) if (copts and f["opts"]) else 0.0
            score = (2.0 if nm else 0.0) + jac
            if score > best_score:
                best_score, best = score, f
        matched = best if best_score >= 2.0 or best_score >= 0.34 else None
        if matched is None:
            presence.append({"section": sec, "control": c.get("label") or c.get("name"),
                             "options": _clean_opts(c.get("options"))[:8]})
            continue
        # Skip VALUE diff for dynamic cascade fields (no static options in our data — their values
        # are computed by localOptions from the same supplier cascade, so they can't be "missing").
        def _present(o):
            no = norm(o)
            if any(no == v or no in v or v in no for v in all_opts):   # selectable anywhere on product
                return True
            return _canon(o) in all_canon                # notation-tolerant token-set match
        miss = [] if not matched["opts"] else [
            o for o in _clean_opts(c.get("options")) if not _present(o)]
        if miss:
            values.append({"control": c.get("label") or c.get("name"),
                           "field": matched["raw"].get("key"), "missing": miss[:12]})
        if sec != matched["section"]:
            section.append({"control": c.get("label") or c.get("name"),
                            "field": matched["raw"].get("key"),
                            "supplier_section": sec, "our_section": matched["section"]})
    return presence, values, section


def main():
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))["products"]
    by_id = {p["id"]: p for p in data}
    report = {}
    no_capture = []
    for f in sorted(FDIR.glob("*.json")) if FDIR.is_dir() else []:
        cap = json.loads(f.read_text(encoding="utf-8"))
        pid = cap.get("id")
        p = by_id.get(pid)
        if not p:
            continue
        if not cap.get("rows") or cap.get("sectionCount", 0) == 0:
            no_capture.append((pid, clean_name(p["name"]), cap.get("slug"), cap.get("error")))
            continue
        pres, val, sec = reconcile_one(p, cap)
        if pres or val or sec:
            report[pid] = {"name": clean_name(p["name"]), "presence": pres, "values": val, "sections": sec}
    (OUT / "v4_parity_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    np = sum(len(v["presence"]) for v in report.values())
    nv = sum(len(v["values"]) for v in report.values())
    ns = sum(len(v["sections"]) for v in report.values())
    print("=== SPA-AWARE PARITY RECONCILE (vs live v4 form) ===")
    print(f"captured products : {len(list(FDIR.glob('*.json'))) - len(no_capture)}"
          f"  (no form rendered: {len(no_capture)})")
    print(f"presence gaps : {np} controls across {sum(1 for v in report.values() if v['presence'])} products")
    print(f"value gaps    : {nv} controls across {sum(1 for v in report.values() if v['values'])} products")
    print(f"section fixes : {ns} controls across {sum(1 for v in report.values() if v['sections'])} products")
    if no_capture:
        print("\n-- no form rendered (need slug override / re-run) --")
        for pid, nm, slug, err in no_capture:
            print(f"  [{pid}] {nm[:30]:30} tried={slug} err={err}")
    if "--verbose" in sys.argv:
        for pid, v in sorted(report.items()):
            print(f"\n[{pid}] {v['name']}")
            for g in v["presence"]:
                print(f"   MISSING CONTROL ({g['section']}): {g['control']}  opts={g['options']}")
            for g in v["values"]:
                print(f"   MISSING VALUES [{g['field']}]: {g['missing']}")
            for g in v["sections"]:
                print(f"   SECTION: {g['control']} -> supplier={g['supplier_section']} ours={g['our_section']}")
    print("\nwrote output/v4_parity_report.json")


if __name__ == "__main__":
    main()
