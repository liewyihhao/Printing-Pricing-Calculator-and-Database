"""Per-product order quantity spec (MOQ + display quantities + whether custom qty is allowed),
sourced from the supplier's order-form quantity dropdown captured in output/option_audit/.

Excard's minimum order quantity = the smallest value in the product's quantity dropdown; the
displayed values are the standard order quantities; an "Other" entry means custom qty is allowed.

  quantity_spec(name) -> {"moq","maxq","options","custom","mode"} | None
  attach(data)        -> sets product["quantity"] for every product (with a safe fallback)
"""
from __future__ import annotations
import json, re
from pathlib import Path

from app.build_specs_page import clean_name

OUT = Path(__file__).resolve().parent.parent / "output"
AUDIT = OUT / "option_audit"
_DEFAULT_CHIPS = [100, 250, 500, 1000, 2000, 5000, 10000]


# our base-slug -> option_audit filename, where they differ
_ALIAS = {
    "l-shape-plastic-folder": "l-shape-folder",
    "papan-kopi-sachet-board": "papan-kopi",
    "label-sticker": "label-sticker-with-hot-stamping",
    "static-cling-window-sticker": "static-cling-window-sticker",
    "stamp-chop": "Stamp-chop",
    "wire-o-notebook": "Wire-O-Notebook",
    "exclusive-leather-cover-wire-o-notebook": "Wire-O-Notebook",
    "hard-cover-perfect-bind-notebook": "Wire-O-Notebook",
    # Apparel: only Sublimation Shirt shares the sublimation-jersey form. Cap, Jacket, Corporate
    # Shirt, Sweatshirt/Hoodies, DTF/Silkscreen shirt and Muslimah are distinct products built
    # from the readymade engine with NO matching option_audit — do NOT alias them to shirt.json
    # (doing so injected "Soccer Pants" and produced false parity gaps).
    "sublimation-shirt": "sublimation-shirt",
    "brochure": "brochure", "flyer": "flyer", "customprint": "customprint",
    "premium-money-packet": "money-packet", "hot-stamping-money-packet": "money-packet",
    "envelope-money-packet": "money-packet", "kraft-paper-bag": "paper-bag",
    "premium-desk-calendar": "desk-calendar-hard-stand",
}


def _base_slug(name: str) -> str:
    b = re.split(r"[—(]", clean_name(name))[0]
    return re.sub(r"[^a-z0-9]+", "-", b.strip().lower()).strip("-")


def _num(s: str):
    s = re.sub(r"[—-].*$", "", str(s)).replace(",", "").strip()   # drop "— Best Seller"
    return int(s) if s.isdigit() else None


def _audit_qty(slug: str):
    """Return (sorted_options, custom_allowed) from the richest quantity dropdown, or None."""
    f = AUDIT / f"{slug}.json"
    if not f.is_file():
        return None
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None
    best = None
    for c in d.get("controls", []):
        nm = (c.get("name", "") + " " + c.get("label", "")).lower()
        if not ("quantity" in nm or "qty" in nm or c.get("name") == "comboQty"):
            continue
        opts = c.get("options") or []
        nums = sorted({n for n in (_num(o) for o in opts) if n})
        if not nums:
            continue
        custom = any("other" in str(o).lower() for o in opts)
        if best is None or len(nums) > len(best[0]):
            best = (nums, custom)
    return best


def _spec(options, custom):
    moq, maxq = options[0], options[-1]
    contiguous = len(options) > 20 and options == list(range(moq, maxq + 1))
    mode = "free" if (custom or contiguous) else "fixed"
    # curate display chips: keep <=8 representative values
    chips = options if len(options) <= 8 else (
        [options[0]] + [o for o in options[1:-1] if o in (100, 200, 300, 500, 1000, 2000, 5000)][:6] + [options[-1]])
    chips = sorted(set(chips))
    return {"moq": moq, "maxq": maxq, "options": options, "custom": custom, "mode": mode, "chips": chips}


def quantity_spec(name: str):
    slug = _base_slug(name)
    a = _audit_qty(_ALIAS.get(slug, slug)) or _audit_qty(slug)
    return _spec(a[0], a[1]) if a else None


def attach(data):
    n = hit = 0
    for p in data["products"]:
        q = quantity_spec(p["name"])
        if q is None:                                   # fallback: keep prior open behaviour
            q = {"moq": 1, "maxq": None, "options": _DEFAULT_CHIPS, "custom": True,
                 "mode": "free", "chips": _DEFAULT_CHIPS}
        else:
            hit += 1
        p["quantity"] = q
        n += 1
    return n, hit


if __name__ == "__main__":
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))
    n, hit = attach(data)
    print(f"quantity: {hit}/{n} products have an order-form MOQ; rest use the open fallback")
    import collections
    ex = collections.Counter()
    for p in data["products"]:
        q = p["quantity"]
        ex[(q["mode"], q["custom"])] += 1
    print("modes:", dict(ex))
    for p in data["products"][:20]:
        q = p["quantity"]
        print(f"  {clean_name(p['name'])[:32]:32} MOQ={q['moq']:<6} max={q['maxq']} mode={q['mode']} custom={q['custom']}")
