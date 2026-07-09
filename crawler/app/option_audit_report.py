"""Consolidate output/option_audit/<slug>.json enumerations into a single reviewable
markdown checklist: for every product, list every configuration control in DOM order
(section → label → type → options) from the first field through Delivery, plus a
price-relationship column to be filled from the CheckPrice toggle probes.

  python -m app.option_audit_report
Writes output/OPTION_AUDIT.md
"""
from __future__ import annotations
import json, sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "output"
AUD = OUT / "option_audit"
REL = OUT / "option_relationships.json"   # {slug: {control_name: "price-axis ~19%" | "neutral" | ...}}


def run():
    rel = json.loads(REL.read_text()) if REL.exists() else {}
    lines = ["# Excard option-parity audit — every control, first field → Delivery", ""]
    lines.append("_price relationship: **AXIS** = changes price (must be sampled), "
                 "**neutral** = present but price-independent, **delivery** = affects shipping fee only._\n")
    files = sorted(AUD.glob("*.json"))
    for f in files:
        d = json.loads(f.read_text())
        slug = d["slug"]
        lines.append(f"## {slug}")
        if d.get("error"):
            lines.append(f"> ⚠️ {d['error']}\n")
            continue
        srel = rel.get(slug, {})
        cur_sec = None
        for c in d["controls"]:
            if not c.get("visible"):
                continue
            if c["section"] != cur_sec:
                cur_sec = c["section"]
                lines.append(f"\n**{cur_sec}**")
            opts = c.get("options", [])
            os_ = ", ".join(opts[:8]) + (" …" if len(opts) > 8 else "")
            r = srel.get(c.get("name", ""), "?")
            label = c.get("label") or c.get("name") or "(unnamed)"
            lines.append(f"- `{c['type']}` **{label}** [{r}] — {os_}")
        lines.append("")
    (OUT / "OPTION_AUDIT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote output/OPTION_AUDIT.md ({len(files)} products)", file=sys.stderr)


if __name__ == "__main__":
    run()
