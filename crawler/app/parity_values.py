"""Value-level parity check: for every product, align each Excard control to our best-matching
field and report Excard OPTION VALUES that are missing from ours (so every combo Excard offers
is selectable in our calculator). Complements the control-level gap audit.

  python -m app.parity_values          # all products
  python -m app.parity_values 24 1     # specific ids
"""
from __future__ import annotations
import json, os, re, sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"


def norm(s):
    s = str(s).lower().replace("×", "x").replace("�", "x")
    s = re.sub(r"\s*-\s*best seller", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def nkey(s):  # aggressive key for matching (drop punctuation/parentheticals)
    s = norm(s)
    s = re.sub(r"\([^)]*\)", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


PLACE = re.compile(r"please select|^--|^- |track order|^product$|relevance|newest|oldest|highest|^-?\s*not required|^no required", re.I)
DROP = re.compile(r"courier|countr|others countries|west malaysia|east malaysia|singapore|thailand|appointed|skynet|remark|artwork|upload|email|name|phone|address|quantity", re.I)


def is_qty(opts):
    return len([o for o in opts if re.fullmatch(r"[\d,]+", o.strip())]) >= 3


def load_slug2ids():
    cat = json.loads((OUT / "excard_catalogue.json").read_text(encoding="utf-8"))
    m = {}
    for c in cat["products"]:
        ids = [int(x) for b in c.get("built_as", []) for x in re.findall(r"\((?:id )?(\d+)", b)]
        m[c["slug"]] = ids
    return m


def run(only=None):
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))
    prods = {p["id"]: p for p in data["products"]}
    slug2ids = load_slug2ids()
    findings = []
    for slug, ids in slug2ids.items():
        f = OUT / "option_audit" / f"{slug}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("error"):
            continue
        ctrls = []
        for c in d["controls"]:
            if not c.get("visible", True) or c["section"].upper() == "DELIVERY":
                continue
            opts = [o for o in c.get("options", []) if not PLACE.match(o)]
            if not opts or c.get("options", [])[:2] == ["Track Order", "Product"] or DROP.search(c.get("label") or ""):
                continue
            if is_qty(opts):
                continue
            ctrls.append((c.get("label") or c.get("name") or "?", opts))
        for pid in ids:
            if only and pid not in only:
                continue
            p = prods.get(pid)
            if not p:
                continue
            ourfields = [(fld.get("label") or fld.get("key"), [o for o in (fld.get("options") or [])]) for fld in p["fields"]]
            our_nkeys = [set(nkey(o) for o in opts) for _, opts in ourfields]
            for label, exopts in ctrls:
                exkeys = [nkey(o) for o in exopts]
                exset = set(k for k in exkeys if k)
                if not exset:
                    continue
                # best-matching our field by key overlap
                best_i, best_ov = -1, 0.0
                for i, ok in enumerate(our_nkeys):
                    ov = len(exset & ok) / len(exset)
                    if ov > best_ov:
                        best_ov, best_i = ov, i
                if best_ov < 0.34:
                    continue  # no corresponding field (control-level gap, handled elsewhere)
                ourk = our_nkeys[best_i]
                missing = [o for o, k in zip(exopts, exkeys) if k and k not in ourk]
                if missing:
                    findings.append((pid, p["name"][:26], label[:18], ourfields[best_i][0][:16], missing))
    findings.sort()
    for pid, name, exlab, ourlab, missing in findings:
        print(f"#{pid} {name}: Excard [{exlab}] -> our [{ourlab}] MISSING VALUES: " + " | ".join(missing[:6]))
    print(f"\ntotal controls with missing values: {len(findings)}")


if __name__ == "__main__":
    only = set(int(x) for x in sys.argv[1:]) if len(sys.argv) > 1 else None
    run(only)
