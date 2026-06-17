"""Build the enriched packaging catalogue for the UI: code, name, category, image, and
dimension limits (from output/packaging_globals/*). Writes output/packaging_catalogue_ui.json.

  python -m app.packaging_catalogue
"""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
IMG = "https://packaging.excard.com.my{}"

# friendly names from the public style page (excard.com.my/packaging-box-style)
NAMES = {
    "A001": "Reverse Tuck End (RTE) Box", "A001A": "RTE Box, Window Patching",
    "A001X": "Reverse Tuck End (RTE) Box", "A002X": "Straight Tuck End (STE) Box",
    "A002AX": "STE Box, Window Patching", "A002BX": "STE Box, Tongue Lock",
    "A002CX": "STE Box, Window Patching", "A002FX": "STE Box, Tongue Lock (Hanging)",
    "B037": "STE Box, Tongue Lock (Hanging + Window)", "B038": "RTE Box, Tongue Lock",
    "B040A": "RTE Box (Hanging)", "B042A": "RTE Box, Tongue Lock (Hanging)",
    "B044X": "Semi Auto Bottom Lock, Tongue Lock", "B048A": "Auto Bottom Lock, Tongue Lock",
    "B052A": "Open Top Box with Hole Punch", "C001A": "Semi Auto Bottom Lock Box",
    "C001AA": "Semi Auto Bottom Lock", "C001AB": "Semi Auto Bottom Lock",
    "C001AC": "Semi Auto Bottom Lock (Window)", "C001AD": "Auto Bottom Lock",
    "C001AE": "Auto Bottom Lock (Window)", "C001B": "Semi Auto Bottom Lock, Window Patching",
    "C001IX": "Semi Auto Bottom Lock, Sombrero Hole", "C001JX": "Semi Auto Bottom Lock, Window (Hanging)",
    "C001M": "Auto Bottom Lock Box", "C001N": "Auto Bottom Lock, Window Patching",
    "C001QX": "Auto Bottom Lock, Sombrero Hole", "C001RX": "Auto Bottom Lock, Window (Hanging)",
    "D007A": "Friction Box with Base Only", "D030": "Friction Box with Lid Only",
    "D040A": "Friction Base and Lid Gift Box", "D052A": "Inner Holding Box",
    "E005X": "Roll End Tuck Front (RETF) Box", "E028A": "Roll End Tuck Front (RETF) Box",
    "E049": "Roll End Tuck Front (RETF) Box", "G012": "Gift Card Envelope",
    "J023A": "Packaging Sleeve", "K003": "Tongue Lock", "K006": "Top with Dual Lock",
    "K016X": "Gable with Handle", "K024": "Semi Auto Bottom Lock Box",
    "L044": "Triangular Cone Box", "L069A": "Self Lock Box", "L082": "Triangle Box",
    "M013": "Divider Box", "M014": "Divider Box", "M015": "Divider Box", "M016": "Divider Boxes",
    "M061": "Inner Holding Box", "M062": "Inner Holding Box", "M063": "Inner Holding Box",
    "M064": "Inner Holding Box", "Z039A": "Roll End Tuck Front (RETF) Box", "0930": "Divider Boxes",
}
# category by code-prefix family
def _category(code):
    if code.startswith(("A001", "B038", "B040", "B042")): return "Reverse Tuck (RTE)"
    if code.startswith(("A002", "B037")): return "Straight Tuck (STE)"
    if code.startswith(("C001", "B044", "B048", "K024")): return "Lock Bottom"
    if code.startswith(("D0", "D040", "D007", "D030")): return "Trays & Top-Base"
    if code.startswith(("E0", "Z0")): return "Hinged Lid / RETF"
    if code.startswith("G0"): return "Folder & Envelope"
    if code.startswith("J0"): return "Sleeve"
    if code.startswith(("M01", "0930")): return "Divider"
    if code.startswith(("M06", "D052")): return "Inner Holding"
    if code.startswith(("K003", "K006", "K016", "L044", "L069", "L082", "L021")): return "Gift / Display"
    return "Other"


def build():
    cat = json.loads((OUT / "packaging_catalogue.json").read_text())
    lim = json.loads((OUT / "packaging_globals" / "boxPmsLimit.json").read_text())
    bl = json.loads((OUT / "packaging_globals" / "BOXLIB.json").read_text())
    src = {b["BoxID"]: b.get("src") for b in bl.get("boxes", [])}
    params = json.loads((OUT / "packaging_params.json").read_text()) if (OUT / "packaging_params.json").exists() else {}
    out = []
    for b in cat:
        code = b["BoxID"]
        if code not in params:   # only boxes we can actually price
            continue
        lm = lim.get(code, {})
        out.append({
            "code": code, "name": NAMES.get(code, code), "category": _category(code),
            "image": IMG.format(src[code]) if src.get(code) else None,
            "limits": {"L": (lm.get("L") or [20])[0], "W": (lm.get("W") or [20])[0],
                       "Dmin": (lm.get("D") or [20])[0],
                       "Dmax": (lm.get("D") or [None, None, 300])[2] if len(lm.get("D", [])) > 2 and lm["D"][2] else None}})
    out.sort(key=lambda x: (x["category"], x["code"]))
    (OUT / "packaging_catalogue_ui.json").write_text(json.dumps(out, indent=0))
    print(f"wrote packaging_catalogue_ui.json: {len(out)} priceable boxes, "
          f"{len(set(x['category'] for x in out))} categories")
    return out


if __name__ == "__main__":
    build()
