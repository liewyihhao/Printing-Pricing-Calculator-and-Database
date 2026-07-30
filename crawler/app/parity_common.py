"""Shared parity primitives: read the supplier's order-form controls (output/option_audit/,
captured in DOM order) as the ground truth, and match them to our calculator fields.

Used by:
  - option_gap_audit  (presence: which controls we don't expose)
  - field_order        (sequence: reorder our fields to the supplier's DOM order)
  - parity_full_audit  (complete diff: presence + values + order)

One place for the filtering + matching + verified-artefact rules, so all three agree.
"""
from __future__ import annotations
import json, re
from pathlib import Path

from app.product_quantity import _base_slug, _ALIAS

OUT = Path(__file__).resolve().parent.parent / "output"
AUDIT = OUT / "option_audit"

# Controls that are not customer-facing product options (delivery, nav, quantity, internals,
# and hot-stamp foil colour/size which is a quoted-separately detail, not a selectable axis).
SKIP = re.compile(r"country|courier|quantity|qty|review|favourite|rush|track|customsize|"
                  r"^txt|^chk|numberfr|numberto|vdp|k100|m100|eyelet|seal|fastener|alquran|"
                  r"^ddlProduct$|hotstamping\w*colour|hotstampingblock|hotstamping\w*size|"
                  r"hscolour|coverhs|hssize|debosssize", re.I)

# supplier control name (normalized, prefix-stripped) -> our field key/label it maps to
ALIASES = {"cardtype": "category", "printmethod": "method", "product": "model",
           "type": "category", "bagcolour": "bag_colour", "handlecolour": "handle_colour",
           "mould": "stamptype", "shape": "category", "rdbidning": "binding", "bidning": "binding",
           "coverlamination": "finishingcover", "addcontent": "additionalcontent",
           "silkscreenspotuv": "silkscreen_spot_uv", "hotstampingenable": "hot_stamping",
           "roundcornerenable": "round_corner", "papertype": "paper", "cardsize": "size",
           "printcolour": "printcolour", "holepunching": "holepunching"}

# Controls verified (via CheckPrice / price-metrics) NOT to be real options for a product —
# artefacts of a shared order-form template that lists a superset of controls.
VERIFIED_NOT_OPTIONS = {
    169: {"model", "paper", "packing", "packingmethod", "mixdesign", "package"},
    160: {"finishing", "size"}, 161: {"finishing"}, 162: {"finishing"},
    135: {"finishing"}, 1: {"creasing"}, 178: {"paper"},
}

_JUNK_OPT = re.compile(r"n/?a|none|nil|null", re.I)


def norm(s):
    # unify visual variants before stripping: × → x, smart dashes → -, so "54mm × 89mm" and
    # "54mm x 89mm" compare equal.
    s = str(s).lower().replace("×", "x").replace("✕", "x").replace("–", "-").replace("—", "-")
    return re.sub(r"[^a-z0-9]", "", s)


def audit_for(product):
    """Load the supplier order-form audit for a product (or None)."""
    slug = _base_slug(product["name"])
    slug = _ALIAS.get(slug, slug)
    for s in (slug, _base_slug(product["name"])):
        f = AUDIT / f"{s}.json"
        if f.is_file():
            return json.loads(f.read_text(encoding="utf-8"))
    return None


def _catalogue_names():
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))["products"]
    return {norm(re.split(r"[—(]", p["name"])[0]) for p in data}


_CAT = None


def _is_product_switcher(opts):
    global _CAT
    if _CAT is None:
        _CAT = _catalogue_names()
    if len(opts) < 2:
        return False
    hits = sum(1 for o in opts if any(c and (c in norm(o) or norm(o) in c) for c in _CAT))
    return hits >= max(2, len(opts) // 2)


def excard_controls(product):
    """Ordered list (supplier DOM order) of the product's REAL option controls:
    [{'idx','name','ctrl','options'}]. Filtering mirrors the parity standard."""
    aud = audit_for(product)
    if not aud:
        return []
    out = []
    for c in aud.get("controls", []):
        nm = c.get("name", "")
        if not nm or SKIP.search(nm):
            continue
        opts = [o for o in (c.get("options") or [])
                if str(o).strip() and not str(o).strip().startswith(("-", "—"))
                and not _JUNK_OPT.fullmatch(str(o).strip())]
        if not opts or _is_product_switcher(opts):
            continue
        ctrl = norm(re.sub(r"^(rbl|ddl|combo)", "", nm))
        ctrl = norm(ALIASES.get(ctrl, ctrl))
        if not ctrl or ctrl in VERIFIED_NOT_OPTIONS.get(product["id"], set()):
            continue
        out.append({"idx": len(out), "name": nm, "ctrl": ctrl, "options": opts})
    return out


def _field_keys(f):
    return norm(f.get("key", "")), norm(f.get("label", ""))


def match_field_to_control(f, controls):
    """Return the control dict this field maps to, or None. Signal = name match OR strong
    bidirectional option-value overlap (Jaccard), so dimension-like fields (e.g. an emboss-size
    field) can't spuriously match a card-size control."""
    fk, fl = _field_keys(f)
    fvals = {norm(v) for v in (f.get("options") or []) if norm(v)}
    best, best_score = None, 0.0
    for c in controls:
        ck = c["ctrl"]
        name_hit = bool(ck) and (ck in fk or fk in ck or ck in fl or fl in ck)
        cvals = {norm(o) for o in c["options"] if norm(o)}
        jac = len(fvals & cvals) / len(fvals | cvals) if (fvals and cvals) else 0.0
        score = (2.0 if name_hit else 0.0) + jac
        if score > best_score:
            best_score, best = score, c
    # accept on a name match (score >= 2) or a solid value overlap (Jaccard >= 0.34)
    return best if best_score >= 2.0 or best_score >= 0.34 else None


def control_is_covered(c, ours_keys, ourvals):
    """Whether a supplier control is exposed anywhere in our fields (name or values)."""
    ck = c["ctrl"]
    if any(ck in o or o in ck for o in ours_keys):
        return True
    hit = sum(1 for o in c["options"] if norm(o) in ourvals)
    return bool(hit and hit >= max(1, len(c["options"]) // 2))
