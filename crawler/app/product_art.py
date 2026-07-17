"""Original, animated SVG product illustrations for the customer UI.

We cannot (and must not) reuse the supplier's copyrighted product photos, so each product
gets an ORIGINAL dimensional SVG "mockup" in the Printoka palette, mapped by visual archetype
(card, sticker, sheet, book, box, bag, banner, apparel, mug, calendar, stamp, generic).

Motion is expressed with class hooks (`pa-float`, `pa-shine`, `pa-wave`, `pa-spin`,
`pa-press`, `pa-flip`) — the host page's CSS decides when they animate (always-on for a hero,
on-hover for grid thumbnails). `ART_KEYFRAMES` provides the shared keyframes/utilities.

  from app.product_art import svg_for, archetype_of, ART_KEYFRAMES
"""
from __future__ import annotations
import re

# palette
TEAL = "#005b7f"; TEAL_D = "#00485f"; TEAL_L = "#3f92b3"; YELLOW = "#fdb913"; YELLOW_D = "#e9a800"
PAPER = "#ffffff"; INK = "#20303a"; SOFT = "#eef4f7"

# ---- archetype mapping ---------------------------------------------------------------------
# Order matters — first match wins. Specific archetypes (calendar, stamp) come before broad
# ones (book, banner) so e.g. "Wire-O Wall Calendar" maps to calendar, not book.
_RULES = [
    ("calendar", ["calendar"]),
    ("stamp", ["stamp", "chop"]),
    ("card", ["business card", "name card", "pvc card", "id card", "kad kahwin", "kad terima",
              "greeting card", "tent card", "creative cut", "cut card", "lanyard"]),
    ("sticker", ["sticker", "label", "magnet", "cling", "decal"]),
    ("apparel", ["shirt", "jacket", "muslimah", "sweatshirt", "hoodie", "cap", "jersey", "apparel"]),
    ("mug", ["mug", "pillow", "fan", "badge", "button", "coaster", "keeper"]),
    ("book", ["booklet", "notebook", "bill-book", "bill book", "notepad", "voucher", "menu",
              "perfect bind", "computer form", "wire-o"]),
    ("bag", ["bag", "tote", "pouch"]),
    ("box", ["box", "kotak", "packaging", "carton", "food tray", "sachet", "papan kopi",
             "vacuum", "seal"]),
    ("banner", ["banner", "bunting", "roll-up", "roll up", "rollup", "wind flag", "flag",
                "standee", "pop display", "stand", "foamboard", "wobbler", "hanger"]),
    ("sheet", ["flyer", "brochure", "loose sheet", "letterhead", "customprint", "poster",
               "bookmark", "folder", "envelope", "arch file"]),
]


def archetype_of(name: str, category: str = "") -> str:
    n = (name or "").lower()
    for arch, kws in _RULES:
        if any(k in n for k in kws):
            return arch
    return "sheet"


def _seed(name: str) -> int:
    return sum(ord(c) for c in (name or ""))


# accent picks so the grid isn't monochrome (brand-anchored)
_ACCENTS = ["#005b7f", "#0d6385", "#127a9c", "#1f6f8b", "#00768f", "#0a5f7a"]


def _accent(name: str) -> str:
    return _ACCENTS[_seed(name) % len(_ACCENTS)]


# ---- shared scene helpers ------------------------------------------------------------------
def _frame(inner: str, extra_defs: str = "") -> str:
    return (
        f'<svg class="pa-svg" viewBox="0 0 320 240" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-hidden="true" preserveAspectRatio="xMidYMid meet">'
        f'<defs>'
        f'<linearGradient id="pabg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#f4fafc"/><stop offset="1" stop-color="#e7f1f5"/></linearGradient>'
        f'<linearGradient id="pash" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'{extra_defs}</defs>'
        f'<rect width="320" height="240" rx="18" fill="url(#pabg)"/>'
        f'<ellipse class="pa-shadow" cx="160" cy="205" rx="92" ry="15" fill="#0a3345" opacity=".13"/>'
        f'<g class="pa-float">{inner}</g>'
        f'</svg>')


def _shine(x, y, w, h, rx=8):
    # a diagonal gloss sweep clipped to the product face
    return (f'<clipPath id="pac{x}{y}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/></clipPath>'
            f'<g clip-path="url(#pac{x}{y})"><rect class="pa-shine" x="{x-60}" y="{y}" width="46" height="{h}" '
            f'fill="url(#pash)" transform="skewX(-18)"/></g>')


# ---- archetypes ----------------------------------------------------------------------------
def _card(a):
    return _frame(
        f'<g transform="rotate(-7 160 120)">'
        f'<rect x="86" y="78" width="150" height="90" rx="9" fill="#0a3345" opacity=".10" transform="translate(5 7)"/>'
        f'<rect x="86" y="78" width="150" height="90" rx="9" fill="{PAPER}"/>'
        f'<rect x="86" y="78" width="150" height="30" rx="9" fill="{a}"/><rect x="86" y="99" width="150" height="9" fill="{a}"/>'
        f'<circle cx="108" cy="128" r="11" fill="{YELLOW}"/>'
        f'<rect x="128" y="122" width="70" height="6" rx="3" fill="#c9d6dd"/>'
        f'<rect x="128" y="135" width="52" height="5" rx="2.5" fill="#dbe4e9"/>'
        f'<rect x="102" y="150" width="118" height="5" rx="2.5" fill="#e4ebef"/>'
        + _shine(86, 78, 150, 90, 9) + '</g>')


def _sticker(a):
    return _frame(
        f'<g transform="rotate(-6 160 118)">'
        f'<path d="M96 96 q0-22 22-22 h84 q22 0 22 22 v56 q0 22-22 22 h-70 z" fill="#0a3345" opacity=".10" transform="translate(4 6)"/>'
        f'<path d="M96 96 q0-22 22-22 h84 q22 0 22 22 v56 q0 22-22 22 h-70 z" fill="{PAPER}" stroke="{a}" stroke-width="5"/>'
        f'<circle cx="160" cy="120" r="24" fill="{a}"/><circle cx="160" cy="120" r="12" fill="{YELLOW}"/>'
        # peeling corner
        f'<path class="pa-peel" d="M128 174 l-22 16 q-2-20 6-34 z" fill="#f1f6f8" stroke="{a}" stroke-width="2"/>'
        + _shine(96, 74, 128, 100, 20) + '</g>')


def _sheet(a):
    return _frame(
        f'<g transform="rotate(-5 160 118)">'
        f'<rect x="112" y="60" width="96" height="120" rx="6" fill="#0a3345" opacity=".10" transform="translate(5 7)"/>'
        f'<rect x="112" y="60" width="96" height="120" rx="6" fill="{PAPER}"/>'
        f'<rect x="112" y="60" width="96" height="40" rx="6" fill="{a}"/><rect x="112" y="92" width="96" height="8" fill="{a}"/>'
        f'<circle cx="188" cy="80" r="10" fill="{YELLOW}"/>'
        f'<rect x="124" y="112" width="72" height="6" rx="3" fill="#d3dee3"/>'
        f'<rect x="124" y="126" width="72" height="5" rx="2.5" fill="#e0e8ec"/>'
        f'<rect x="124" y="138" width="54" height="5" rx="2.5" fill="#e0e8ec"/>'
        f'<rect x="124" y="156" width="40" height="9" rx="4" fill="{YELLOW}"/>'
        + _shine(112, 60, 96, 120, 6) + '</g>')


def _book(a):
    return _frame(
        f'<g transform="rotate(-4 160 120)">'
        f'<rect x="108" y="70" width="104" height="110" rx="7" fill="#0a3345" opacity=".10" transform="translate(6 8)"/>'
        f'<rect x="112" y="66" width="100" height="110" rx="7" fill="#f3f7f9"/>'
        f'<rect x="106" y="70" width="100" height="110" rx="7" fill="{PAPER}"/>'
        f'<rect x="106" y="70" width="100" height="110" rx="7" fill="{a}" opacity=".92"/>'
        f'<rect x="120" y="88" width="60" height="7" rx="3.5" fill="#ffffff" opacity=".85"/>'
        f'<rect x="120" y="102" width="44" height="6" rx="3" fill="#ffffff" opacity=".55"/>'
        f'<circle cx="156" cy="140" r="16" fill="{YELLOW}"/>'
        # spiral binding
        + "".join(f'<rect x="100" y="{74+i*13}" width="16" height="6" rx="3" fill="{TEAL_D}"/>' for i in range(8))
        + _shine(106, 70, 100, 110, 7) + '</g>')


def _box(a):
    return _frame(
        f'<g transform="translate(0 6)">'
        f'<path d="M160 70 l64 30 v58 l-64 30 -64-30 v-58 z" fill="#0a3345" opacity=".10" transform="translate(4 8)"/>'
        f'<path d="M160 70 l64 30 -64 30 -64-30 z" fill="{YELLOW}"/>'             # top
        f'<path d="M160 130 v58 l-64-30 v-58 z" fill="{a}"/>'                        # left
        f'<path d="M160 130 v58 l64-30 v-58 z" fill="{TEAL_D}"/>'                     # right
        f'<path d="M160 130 v58 l64-30 v-58 z" fill="url(#pash)" opacity=".25"/>'
        f'<rect x="150" y="150" width="20" height="16" rx="2" fill="#ffffff" opacity=".7"/>'
        '</g>')


def _bag(a):
    return _frame(
        f'<g transform="translate(0 4)">'
        f'<rect x="112" y="86" width="96" height="104" rx="5" fill="#0a3345" opacity=".10" transform="translate(5 7)"/>'
        f'<path d="M124 78 q0-16 16-16 q0 12 0 16" fill="none" stroke="{TEAL_D}" stroke-width="5"/>'
        f'<path d="M196 78 q0-16-16-16 q0 12 0 16" fill="none" stroke="{TEAL_D}" stroke-width="5"/>'
        f'<rect x="112" y="80" width="96" height="110" rx="5" fill="{a}"/>'
        f'<rect x="112" y="80" width="96" height="110" rx="5" fill="url(#pash)" opacity=".25"/>'
        f'<circle cx="160" cy="128" r="20" fill="{YELLOW}"/>'
        f'<rect x="140" y="160" width="40" height="7" rx="3.5" fill="#ffffff" opacity=".7"/>'
        + _shine(112, 80, 96, 110, 5) + '</g>')


def _banner(a):
    return _frame(
        f'<g>'
        f'<rect x="150" y="70" width="20" height="120" rx="4" fill="#0a3345" opacity=".10" transform="translate(4 6)"/>'
        f'<path class="pa-wave" d="M120 60 h80 v130 q-40 12-80 0 z" fill="{a}"/>'
        f'<path class="pa-wave" d="M120 60 h80 v130 q-40 12-80 0 z" fill="url(#pash)" opacity=".2"/>'
        f'<circle cx="160" cy="98" r="16" fill="{YELLOW}"/>'
        f'<rect x="134" y="126" width="52" height="7" rx="3.5" fill="#fff" opacity=".8"/>'
        f'<rect x="140" y="140" width="40" height="6" rx="3" fill="#fff" opacity=".5"/>'
        f'<rect x="150" y="190" width="20" height="10" rx="3" fill="{TEAL_D}"/>'
        f'<rect x="130" y="198" width="60" height="7" rx="3.5" fill="{TEAL_D}"/>'
        '</g>')


def _apparel(a):
    return _frame(
        f'<g transform="translate(0 8)">'
        f'<path d="M128 78 l-28 16 8 26 20-8 v70 h64 v-70 l20 8 8-26 -28-16 q-16 14-36 0 z" '
        f'fill="#0a3345" opacity=".10" transform="translate(5 7)"/>'
        f'<path d="M128 78 l-28 16 8 26 20-8 v70 h64 v-70 l20 8 8-26 -28-16 q-16 14-36 0 z" fill="{a}"/>'
        f'<path d="M128 78 q16 14 36 0" fill="none" stroke="#ffffff" stroke-width="3" opacity=".6"/>'
        f'<circle cx="160" cy="128" r="18" fill="{YELLOW}"/>'
        + '</g>')


def _mug(a):
    return _frame(
        f'<g transform="translate(-6 6)">'
        f'<ellipse cx="150" cy="188" rx="46" ry="10" fill="#0a3345" opacity=".10"/>'
        f'<path d="M118 96 h64 v76 q0 14-14 14 h-36 q-14 0-14-14 z" fill="{a}"/>'
        f'<path d="M118 96 h64 v76 q0 14-14 14 h-36 q-14 0-14-14 z" fill="url(#pash)" opacity=".3"/>'
        f'<ellipse cx="150" cy="96" rx="32" ry="9" fill="{TEAL_D}"/>'
        f'<path d="M182 110 q30 4 30 26 q0 22-30 24" fill="none" stroke="{a}" stroke-width="10"/>'
        f'<circle cx="150" cy="138" r="15" fill="{YELLOW}"/>'
        f'<path class="pa-steam" d="M140 84 q6-8 0-16" stroke="#b9d3dd" stroke-width="3" fill="none" stroke-linecap="round"/>'
        f'<path class="pa-steam" d="M160 84 q6-8 0-16" stroke="#b9d3dd" stroke-width="3" fill="none" stroke-linecap="round" style="animation-delay:.6s"/>'
        '</g>')


def _calendar(a):
    return _frame(
        f'<g transform="rotate(-3 160 120)">'
        f'<rect x="108" y="76" width="104" height="98" rx="6" fill="#0a3345" opacity=".10" transform="translate(5 7)"/>'
        f'<rect x="108" y="76" width="104" height="98" rx="6" fill="{PAPER}"/>'
        f'<rect x="108" y="76" width="104" height="26" rx="6" fill="{a}"/><rect x="108" y="94" width="104" height="8" fill="{a}"/>'
        + "".join(f'<rect x="{120+c*18}" y="{112+r*15}" width="12" height="10" rx="2" '
                  f'fill="{YELLOW if (r*4+c)==5 else "#dbe6ea"}"/>' for r in range(4) for c in range(5))
        + "".join(f'<rect x="{124+i*20}" y="66" width="7" height="18" rx="3" fill="{TEAL_D}"/>' for i in range(5))
        + '</g>')


def _stamp(a):
    return _frame(
        f'<g class="pa-press">'
        f'<ellipse cx="160" cy="196" rx="44" ry="9" fill="#0a3345" opacity=".12"/>'
        f'<rect x="128" y="150" width="64" height="26" rx="6" fill="{a}"/>'
        f'<rect x="120" y="140" width="80" height="16" rx="5" fill="{TEAL_D}"/>'
        f'<rect x="140" y="96" width="40" height="48" rx="8" fill="{a}"/>'
        f'<ellipse cx="160" cy="92" rx="26" ry="12" fill="{YELLOW}"/>'
        '</g>'
        f'<g transform="translate(120 182)"><circle cx="40" cy="6" r="16" fill="none" stroke="{a}" stroke-width="3" opacity=".5"/></g>')


def _generic(a):
    return _frame(
        f'<g transform="rotate(-6 160 120)">'
        f'<rect x="106" y="74" width="108" height="96" rx="8" fill="#0a3345" opacity=".10" transform="translate(5 7)"/>'
        f'<rect x="106" y="74" width="108" height="96" rx="8" fill="{PAPER}"/>'
        f'<rect x="120" y="90" width="80" height="10" rx="5" fill="{a}"/>'
        f'<circle cx="160" cy="128" r="16" fill="{YELLOW}"/>'
        f'<rect x="120" y="150" width="80" height="7" rx="3.5" fill="#dbe6ea"/>'
        + _shine(106, 74, 108, 96, 8) + '</g>')


_ARCH = {"card": _card, "sticker": _sticker, "sheet": _sheet, "book": _book, "box": _box,
         "bag": _bag, "banner": _banner, "apparel": _apparel, "mug": _mug,
         "calendar": _calendar, "stamp": _stamp, "generic": _generic}


def svg_for(name: str, category: str = "") -> str:
    arch = archetype_of(name, category)
    return _ARCH.get(arch, _generic)(_accent(name))


# Shared keyframes + motion utilities. Included once per page; animation is gated by the host
# (always-on under .hero-art, hover-only under .pcard) so grids stay calm.
ART_KEYFRAMES = r"""
  .pa-svg{width:100%;height:100%;display:block}
  @keyframes paFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}
  @keyframes paShadow{0%,100%{transform:scaleX(1);opacity:.13}50%{transform:scaleX(.9);opacity:.09}}
  @keyframes paShine{0%{transform:translateX(0) skewX(-18deg)}60%,100%{transform:translateX(240px) skewX(-18deg)}}
  @keyframes paWave{0%,100%{d:path("M120 60 h80 v130 q-40 12 -80 0 z")}50%{d:path("M120 60 h80 v130 q-40 -6 -80 0 z")}}
  @keyframes paPeel{0%,100%{transform:rotate(0)}50%{transform:rotate(-8deg)}}
  @keyframes paSteam{0%{opacity:0;transform:translateY(4px)}40%{opacity:.7}100%{opacity:0;transform:translateY(-10px)}}
  @keyframes paPress{0%,100%{transform:translateY(0)}45%{transform:translateY(10px)}55%{transform:translateY(10px)}}
  .pa-shine{transform:translateX(0) skewX(-18deg)}
  /* always-on (hero) */
  .hero-art .pa-float{animation:paFloat 4.5s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
  .hero-art .pa-shadow{animation:paShadow 4.5s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
  .hero-art .pa-shine{animation:paShine 5s ease-in-out infinite}
  .hero-art .pa-wave{animation:paWave 4s ease-in-out infinite}
  .hero-art .pa-peel{animation:paPeel 4.5s ease-in-out infinite;transform-box:fill-box;transform-origin:top right}
  .hero-art .pa-steam{animation:paSteam 3s ease-in-out infinite}
  .hero-art .pa-press{animation:paPress 3.2s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
  /* hover (thumbnails) */
  .pa-thumb .pa-float{transition:transform .4s ease}
  .pcard:hover .pa-thumb .pa-float,.pa-thumb:hover .pa-float{animation:paFloat 4.5s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
  .pcard:hover .pa-thumb .pa-shine,.pa-thumb:hover .pa-shine{animation:paShine 1.2s ease-out}
  @media(prefers-reduced-motion:reduce){.pa-float,.pa-shine,.pa-wave,.pa-peel,.pa-steam,.pa-press,.pa-shadow{animation:none!important}}
"""
