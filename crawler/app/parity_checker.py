"""Parity checker — for every BUILT product, deep-configure the live Excard order form
(revealing all dependent/finishing controls), capture EVERY option Excard offers, and diff
it against our FIELD_SCHEMAS. Flags: (a) Excard controls with no matching field in our build
(missed dimensions), and (b) option values Excard offers that our field is missing.

  python -m app.parity_checker            # check all
  python -m app.parity_checker kadkahwin  # check one family
  python -m app.parity_checker --print    # print the saved report

Writes output/parity_report.json. The /api/printoka/parity endpoint serves it.
"""
from __future__ import annotations
import asyncio, json, re, sys
from pathlib import Path
from playwright.async_api import async_playwright
from .browser import launch, login
from . import accounts

OUT = Path(__file__).resolve().parent.parent / "output"

# family -> live Excard spec form to compare against (the priced source).
FAMILY_URL = {
    "notepad": "https://www.excard.com.my/spec/Litho/Notepad",
    "letterhead": "https://www.excard.com.my/spec/Litho/Letterhead",
    "envelope": "https://www.excard.com.my/spec/Litho/Envelope",
    "folder": "https://www.excard.com.my/spec/Litho/Folder",
    "lshape": "https://www.excard.com.my/spec/Digital/L_Shape_Plastic_Folder",
    "bookmark": "https://www.excard.com.my/spec/Digital/Bookmark",
    "voucher": "https://www.excard.com.my/spec/Litho/voucher",
    "computerform": "https://www.excard.com.my/spec/Litho/Computer_Form",
    "wireo": "https://www.excard.com.my/spec/Litho/Wire-O_Notebook",
    "pvccard": "https://www.excard.com.my/spec/Digital/PVC_Card",
    "kadkahwin": "https://www.excard.com.my/spec/Digital/Kad_Kahwin",
    "kadterima": "https://www.excard.com.my/spec/Digital/kad_Terima_Kasih",
    "staticcling": "https://www.excard.com.my/spec/Digital/Static_Cling_Window_Sticker",
    "wallcal": "https://www.excard.com.my/spec/Litho/Wall_Calendar",
    "loose": "https://www.excard.com.my/spec/Litho/Loose_Sheet",
    "loose_digital": "https://www.excard.com.my/spec/Digital/Loose_Sheet",
    "booklet": "https://www.excard.com.my/spec/Litho/Booklet",
    "billbook": "https://www.excard.com.my/spec/Litho/Bill-Book",
    "sticker_digital": "https://www.excard.com.my/spec/Digital/Label_Sticker",
    "sticker_letterpress": "https://www.excard.com.my/spec/Letterpress/Label_Sticker_with_Hot_Stamping",
    # Large-format
    "banner": "https://www.excard.com.my/spec/Litho/Banner",
    "bunting": "https://www.excard.com.my/spec/Litho/Bunting",
    "wobbler": "https://www.excard.com.my/spec/Digital/Wobbler",
    "rollup": "https://www.excard.com.my/spec/Litho/Roll_Up_Stand",
    # Calendars
    "deskcal_hard": "https://www.excard.com.my/spec/Litho/Desk_Calendar_(Hard_Stand)",
    "deskcal_soft": "https://www.excard.com.my/spec/Litho/Desk_Calendar_(Soft_Stand)",
    "wireow": "https://www.excard.com.my/spec/Litho/Wire-O_Wall_Calendar",
    # Gifts
    "buttonbadge": "https://www.excard.com.my/spec/Digital/button_badge",
    "handfan": "https://www.excard.com.my/spec/Digital/Hand_Fan",
    "hanger": "https://www.excard.com.my/spec/Digital/Hanger",
    "hardmenu": "https://www.excard.com.my/spec/Digital/Hard_Cover_Menu",
    "magnet": "https://www.excard.com.my/spec/Digital/Magnet",
    "mug": "https://www.excard.com.my/spec/Litho/Mug",
    "pillow": "https://www.excard.com.my/spec/Litho/Pillow",
    "stamp_chop": "https://www.excard.com.my/spec/Litho/Stamp_Chop",
    "archfile": "https://www.excard.com.my/spec/Digital/Arch_File",
    # Bags & packaging
    "paperbag": "https://www.excard.com.my/spec/Litho/Paper_Bag",
    "canvastote": "https://www.excard.com.my/spec/Litho/Canvas_Tote_Bag",
    "pouch": "https://www.excard.com.my/spec/Litho/Standing_Pouch",
    # Misc
    "tent_card": "https://www.excard.com.my/spec/Litho/Tent_Card",
    "money_packet": "https://www.excard.com.my/spec/Litho/Money_Packet",
    "non_woven_bag": "https://www.excard.com.my/spec/Litho/Non_Woven_Bag",
    "papan_kopi": "https://www.excard.com.my/spec/Litho/Papan_Kopi",
    # Digital Booklet uses a different URL but shares the same FIELD_SCHEMAS family
    "booklet_digital": "https://www.excard.com.my/spec/Digital/Booklet",
}
# Some families share a FIELD_SCHEMAS key (e.g. digital/litho booklet share "booklet")
FAMILY_ALIAS: dict[str, str] = {
    "booklet_digital": "booklet",
}
# control name substrings to ignore (not product spec drivers)
IGNORE = ("country", "courier", "comboqty", "ddlqty", "qty", "track", "review-filter",
          "ddlproduct", "ddlprintmethod", "otherorder", "numberingfrom", "numberto",
          "ddllayer",   # per-ply NCR tint colour dropdowns — price-neutral production input
          "vdpfont", "vdpbold", "fontalignment", "vdptype",  # VDP text sub-options (cosmetic)
          "")           # the top nav (Track Order / Product) has an empty name
# option values that are not real spec gaps (custom-size escape hatch, % discount label noise)
IGNORE_OPTS = ("others", "% off", "out of stock")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


async def _deep_configure(page):
    """Pick the first real option in every select + first value in every spec radio group,
    over several passes, so dependent/finishing controls get revealed."""
    for _ in range(6):
        await page.evaluate(r"""() => {
            const fire = el => { el.dispatchEvent(new Event('change',{bubbles:true}));
                                 el.dispatchEvent(new Event('input',{bubbles:true})); };
            for (const s of document.querySelectorAll('select')) {
                if (!s.offsetParent) continue;
                const n=(s.name||'').toLowerCase();
                if (/country|courier|qty|product|printmethod|review/.test(n)) continue;
                if (s.selectedIndex<=0) {
                    const opt=[...s.options].findIndex(o=>o.text.trim() && !/please select|not required|^-/i.test(o.text.trim()));
                    if (opt>=0){ s.selectedIndex=opt; fire(s); }
                }
            }
            const seen={};
            for (const r of document.querySelectorAll('input[type=radio]')) {
                const n=(r.name||'').toLowerCase();
                if (/country|courier/.test(n)) continue;
                if (!seen[r.name]) { seen[r.name]=1; if(!r.checked){ r.checked=true; r.click(); } }
            }
        }""")
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        await asyncio.sleep(1.0)


async def _dump(page):
    selects = await page.evaluate(r"""() => [...document.querySelectorAll('select')]
        .filter(s=>s.offsetParent).map(s=>({name:(s.name||'').split('$').pop(),
        options:[...s.options].map(o=>o.text.trim()).filter(t=>t && !/^-|please select/i.test(t))}))
        .filter(s=>s.options.length)""")
    radios = await page.evaluate(r"""() => { const g={}; for(const r of document.querySelectorAll('input[type=radio]')){
        if(!r.offsetParent) continue; const n=(r.name||'').split('$').pop();
        const lbl=(r.closest('label')?.innerText|| r.parentElement?.innerText || r.value||'').trim().split('\n')[0];
        (g[n]=g[n]||[]).push(lbl||r.value); } return g; }""")
    return {"selects": selects, "radios": radios}


def _schema_options(family):
    from .api import FIELD_SCHEMAS
    sch = FIELD_SCHEMAS.get(family, {})
    out = {}
    for f in sch.get("fields", []):
        opts = f.get("options")
        if opts:
            out[f["key"]] = opts
        else:
            out[f["key"]] = []  # cascade field (options fetched dynamically)
    return out


# control-name keyword -> our schema field-key keyword (so rblPunchHole matches hole_punch, etc.)
KEYWORD_FIELDS = {"laminat": ("lamination", "surface", "finishing"), "punch": ("punch", "hole"),
                  "hole": ("punch", "hole"), "corner": ("corner", "finishing"), "fold": ("fold",),
                  "emboss": ("emboss",), "stamp": ("hot_stamping", "stamp"),
                  "envelope": ("envelope",), "round": ("round_corner", "corner"),
                  "vdp": ("vdp",), "size": ("size",), "paper": ("paper",), "colour": ("colour", "color"),
                  # Excard's binding control is the misspelled "rdbidning"; our booklet field is the
                  # dynamic `binding` cascade (options fetched at runtime, so they read empty here).
                  "binding": ("binding",), "bidning": ("binding",),
                  # rblMouldGroup is a grouping radio (Presentation/Document/Key/CD Jacket) that
                  # filters which individual mould models appear. Our flat `model` field lists all
                  # moulds across groups — it covers the group implicitly via model selection.
                  "mould": ("model", "mould"), "orient": ("orientation",),
                  # Bunting ddlColourProtective = fitting (Wood/PVC Pipe/Wood+Wire) → our `protective`
                  "protective": ("protective",),
                  # Wobbler rblRoundCorner (Round Corner / Custom Die-Cut) — we cover both in `finishing`
                  "diecut": ("finishing",),
                  # Money Packet / bags packaging controls
                  "packing": ("packing", "package"), "package": ("packing", "package"),
                  # Banner/large-format controls
                  "banner": ("size",), "material": ("paper", "material"),
                  # Gifts finishing
                  "finishing": ("finishing",), "shape": ("shape",),
                  # addcontent for Hard Cover Menu
                  "addcontent": ("addcontent",), "content": ("addcontent", "content"),
                  # Bag colour / handle
                  "handle": ("handle_length", "handle_colour", "handle"),
                  "bagcolour": ("bag_colour",),
                  # Category radio for desk calendar
                  "category": ("cat", "category"),
                  # Tent Card model
                  "model": ("model",),
                  }


# Per-family control names to ignore (constants that aren't user-selectable dimensions)
FAMILY_IGNORE: dict[str, tuple[str, ...]] = {
    # rdType="Magnet" is a form-navigation constant (not a user dim); magnet has no type split
    "magnet": ("rdtype",),
    # Wire-O Wall Calendar: rblPunchHole shows only "Not Required" — hole punching is already
    # compulsory/included in the fixed spec; the single option is a display artifact, not a choice.
    "wireow": ("punchhole",),
}


def _diff(family, excard):
    ours = _schema_options(FAMILY_ALIAS.get(family, family))
    our_all_norm = {_norm(o) for opts in ours.values() for o in opts}
    our_keys = [k.lower() for k in ours]
    fam_ign = FAMILY_IGNORE.get(family, ())
    gaps = []
    controls = []
    items = [(s["name"], s["options"]) for s in excard["selects"]]
    items += [(name, vals) for name, vals in excard["radios"].items()]
    for name, opts in items:
        if name == "" or any(k and k in name.lower() for k in IGNORE) or \
                any(k in name.lower() for k in fam_ign):
            continue
        # drop placeholder + noise options (out of stock, custom-size escape, % discount labels)
        opts = [o for o in opts if o and not re.match(r"^-|please select", o, re.I)
                and not any(ig in o.lower() for ig in IGNORE_OPTS)]
        if not opts:
            continue
        controls.append({"control": name, "options": opts})
        nl = name.lower()
        # represented if: a field key keyword-matches the control, or option values overlap
        kw_match = any(kw in nl and any(fk in k for k in our_keys for fk in fks)
                       for kw, fks in KEYWORD_FIELDS.items())
        nmatch = any(_norm(name).replace("ddl", "").replace("rbl", "") in _norm(k) or
                     _norm(k) in _norm(name) for k in ours)
        overlap = sum(1 for o in opts if _norm(o) in our_all_norm)
        if not (kw_match or nmatch) and overlap == 0:
            gaps.append({"type": "missing_field", "control": name, "options": opts})
        elif overlap >= max(1, len(opts) // 2):
            missing = [o for o in opts if _norm(o) not in our_all_norm]
            if missing:
                gaps.append({"type": "missing_options", "control": name, "missing": missing})
    return {"family": family, "excard_controls": controls, "our_fields": ours, "gaps": gaps}


async def check(families, account_id=1):
    a = accounts.get(account_id)
    # When running a subset, merge into the existing report so we don't lose other families
    rpt_path = OUT / "parity_report.json"
    all_fams = list(FAMILY_URL.keys())
    running_subset = set(families) != set(all_fams)
    report = {}
    if running_subset and rpt_path.exists():
        try:
            report = json.loads(rpt_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    async with async_playwright() as pw:
        b = await launch(pw); ctx = await b.new_context(viewport={"width": 1440, "height": 1600})
        page = await ctx.new_page(); await login(page, username=a.username, password=a.password)
        for fam in families:
            url = FAMILY_URL.get(fam)
            if not url:
                continue
            try:
                await page.goto(url, wait_until="domcontentloaded")
                try: await page.wait_for_load_state("networkidle", timeout=12000)
                except Exception: pass
                await asyncio.sleep(1.5)
                await _deep_configure(page)
                excard = await _dump(page)
                report[fam] = _diff(fam, excard)
                g = report[fam]["gaps"]
                print(f"=== {fam}: {len(g)} gap(s) ===")
                for gg in g:
                    if gg["type"] == "missing_field":
                        print(f"  [MISSING FIELD] {gg['control']}: {gg['options'][:8]}")
                    else:
                        print(f"  [MISSING OPTIONS] {gg['control']}: {gg['missing'][:8]}")
            except Exception as e:  # noqa: BLE001
                report[fam] = {"error": str(e)[:120]}
                print(f"=== {fam}: ERROR {str(e)[:80]}")
        try: await b.close()
        except Exception: pass
    rpt_path.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    total = sum(len(r.get("gaps", [])) for r in report.values() if isinstance(r, dict))
    print(f"\nTOTAL gaps across {len(report)} families: {total}. Report -> output/parity_report.json")
    return report


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--print" in sys.argv:
        rep = json.loads((OUT / "parity_report.json").read_text(encoding="utf-8"))
        for fam, r in rep.items():
            print(f"=== {fam}: {len(r.get('gaps', []))} gaps ===")
            for g in r.get("gaps", []):
                print("  ", g)
    else:
        fams = args if args else list(FAMILY_URL.keys())
        asyncio.run(check(fams))
