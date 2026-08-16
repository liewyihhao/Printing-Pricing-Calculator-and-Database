"""combo_validity_checker — verify that our configurator's VALID-COMBINATION space exactly matches
what Excard's live v4 order form offers, field by field, from the first control through to delivery.
This checks COMBINATION VALIDITY ONLY (never price): for every product it walks a cascade DFS that
mirrors Excard, and at each node compares the OFFERED option-set (and visibility) of the next control
on both sides.

  OUR SIDE   : app/our_side.cjs (reuses the shipped engine.localOptions + ports the template's
               allowedOptions / fieldShown) — byte-identical to what the customer UI shows.
  EXCARD SIDE: the live v4 SPA (v4.excard.com.my/ordering/<slug>), driven with light native events;
               at each node we read the next control's visible options. Cached per
               (field, influencer-signature) so a node is never read twice.

Traversal control: a field's offered options depend only on its cascade `depends`, its validity
primary(s), and its showWhen field(s). We branch a field's value only when some LATER field is
influenced by it; otherwise one representative value advances the walk. DFS state is memoised on the
values of still-relevant fields, so independent branchers don't multiply.

  python -m app.combo_validity_checker <id> [<id> ...]   # specific products
  python -m app.combo_validity_checker --all             # every product (long, live)
  python -m app.combo_validity_checker --our-only <id>   # our-side enumeration only (no browser)

Writes output/combo_validity_report.json and prints a per-product PASS / mismatch summary.
"""
from __future__ import annotations
import asyncio, json, re, subprocess, sys
from pathlib import Path

from app import browser as B
from app.readymade_enum import login_v4
from app.v4_form_capture import _V4_SLUG_BY_ID, _V4_SLUG
from app.product_quantity import _base_slug, _ALIAS
from app.parity_common import norm as _pnorm, ALIASES as _PALIASES


def ctrl_key(name: str) -> str:
    """Normalise an ASP.NET control name (ctl00$…$ddlPaper / rblCategory) to a parity control key,
    so WebForms products (no human labels) still match our field keys — same rules as parity_common."""
    tail = str(name).split("$")[-1].split("_")[-1]
    tail = re.sub(r"^(rbl|ddl|combo|rdb|rb|chk)", "", tail, flags=re.I)
    k = _pnorm(tail)
    return _pnorm(_PALIASES.get(k, k))


def name_key_match(cname: str, field_key: str, field_label: str) -> bool:
    ck = ctrl_key(cname)
    if not ck:
        return False
    fk, fl = _pnorm(field_key), _pnorm(field_label)
    return bool((ck in fk or fk in ck or ck in fl or fl in ck) and len(ck) >= 3)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
V4 = "https://v4.excard.com.my/ordering/"
REPORT = OUT / "combo_validity_report.json"

# Excard control labels that are page chrome / delivery / quantity — never a product-config axis.
_CHROME = re.compile(r"track order|^product$|quantity|country|courier|favourite|job name|"
                     r"add name|remark|custom size|please select", re.I)

# ── value equivalence (v4 SPA notation vs ours) ──
# Our side and the v4 SPA name the SAME option differently: v4 appends descriptor nouns ("Standard"
# vs "Standard Card"), coating/dimension notes ("… (2 side coated)", "…180micron (0.18mm)"), design
# counts ("2 In 1 (2 Designs)"). We must treat those as equal WITHOUT merging genuinely distinct
# options (1C Front ≠ 1C Back). vkey drops noise parentheticals + descriptor stop-words but keeps
# directional/colour qualifiers, so equal keys ⇒ same option.
_NEG = re.compile(r"not required|no required|^\s*none\s*$|no lamination|no hot ?stamping|"
                  r"no fold(ing)?|no cutting|not ?applicable|no hole ?punching|^\s*no\s*$", re.I)
_NOISE_PAREN = re.compile(r"coated|design|mm|cm|open size|micron|\d+\s*side", re.I)
_VSTOP = {"card", "cards", "paper", "design", "designs", "best", "seller", "new", "diameter", "free",
          "coated", "side", "sides", "gsm", "mm", "cm", "micron", "open", "size", "a", "the", "of"}


def vkey(s, extra=()):
    """Canonical identity of an option value, tolerant of v4-vs-ours notation. `extra` = the field's
    label tokens (e.g. round/corner) which v4 often repeats inside the option text
    ("No Round Corner", "Hole Punching - Diameter 3mm") — strip them FIRST so the negative/positive
    signal ("No"/"Required") and the real qualifier ("3mm") are what remain."""
    s = str(s).lower().replace("×", "x")
    for w in extra:
        if len(w) >= 2:
            s = re.sub(r"\b" + re.escape(w) + r"\b", " ", s)
    if _NEG.search(s):
        return frozenset({"__none__"})
    s = re.sub(r"\(([^)]*)\)", lambda m: " " if _NOISE_PAREN.search(m.group(1)) else " " + m.group(1) + " ", s)
    s = re.sub(r"(\d+)\s*c\b", r"\1c", s)
    s = re.sub(r"(\d+)\s*colours?", r"\1c", s)
    return frozenset(t for t in re.findall(r"\d+c|[a-z]{2,}|\d+", s) if t not in _VSTOP)


def labnorm(s: str) -> str:
    s = (s or "").lower().replace("×", "x")
    s = re.sub(r"\(.*?\)", " ", s)          # drop parenthetical notes
    s = s.replace("*", " ")
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def label_match(our_label: str, ex_label: str) -> bool:
    a, b = labnorm(our_label), labnorm(ex_label)
    if not a or not b:
        return False
    if a == b:
        return True
    ta, tb = set(a.split()), set(b.split())
    # subset either way, keyed on the LAST (most-specific) token: our "Lamination" ↔ excard "Paper
    # Lamination" (both end "lamination") match, but our "Paper" ↔ excard "Paper Lamination" don't.
    short, long = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    return short <= long and a.split()[-1] == b.split()[-1]


# ───────────────────────── our-side (Node) client ─────────────────────────
class OurSide:
    def __init__(self):
        self.p = subprocess.Popen(
            ["node", str(ROOT / "app" / "our_side.cjs")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8",
            cwd=str(ROOT))

    def resolve(self, pid: int, V: dict) -> dict:
        self.p.stdin.write(json.dumps({"id": pid, "V": V}) + "\n"); self.p.stdin.flush()
        line = self.p.stdout.readline()
        return json.loads(line)

    def close(self):
        try:
            self.p.stdin.write(json.dumps({"cmd": "quit"}) + "\n"); self.p.stdin.flush()
        except Exception:
            pass
        try:
            self.p.terminate()
        except Exception:
            pass


# ───────────────────────── excard-side (SPA) JS ─────────────────────────
_JS_OPTS = r"""
(labRx) => {
  const rx = new RegExp(labRx, 'i');
  const vis = el => el && el.offsetParent !== null && el.getBoundingClientRect().height > 1;
  const junk = t => !t || /^[-—\s]+$/.test(t) || /please select|^[-—]*\s*select|select\b.*\bfirst/i.test(t);
  for (const sel of document.querySelectorAll('select')) {
    if (!vis(sel)) continue;
    const g = sel.closest('.form-group,.row,.mb-3,.field') || sel.parentElement;
    const le = g && g.querySelector('label,.control-label,b,h5,h6');
    const lab = le ? le.textContent.trim() : (sel.name || '');
    if (rx.test(lab) || rx.test(sel.name || '')) {   // anchor may be a human label OR an ASP.NET name
      const opts = [...sel.options].map(o => o.text.trim()).filter(t => !junk(t));
      return { visible: true, type: 'select', label: lab, options: opts };
    }
  }
  const groups = {};
  for (const r of document.querySelectorAll("input[type=radio]")) { (groups[r.name || r.id] = groups[r.name || r.id] || []).push(r); }
  for (const grp in groups) {
    const rs = groups[grp]; if (!rs.some(vis)) continue;
    const box = rs[0].closest('.form-group,.row,.mb-3,.field') || rs[0].parentElement;
    const le = box && box.querySelector('label,.control-label,b,h5,h6');
    const lab = le ? le.textContent.trim() : grp;
    if (rx.test(lab) || rx.test(grp)) {
      const opts = rs.filter(vis).map(r => (r.closest('label')?.textContent
        || document.querySelector(`label[for='${r.id}']`)?.textContent
        || r.parentElement?.textContent || '').trim()).filter(Boolean);
      return { visible: true, type: 'radio', label: lab, options: opts };
    }
  }
  return { visible: false };
}
"""

_JS_SET = r"""
(args) => {
  const [labRx, val] = args; const rx = new RegExp(labRx, 'i');
  const vis = el => el && el.offsetParent !== null;
  for (const sel of document.querySelectorAll('select')) {
    if (!vis(sel)) continue;
    const g = sel.closest('.form-group,.row,.mb-3,.field') || sel.parentElement;
    const le = g && g.querySelector('label,.control-label,b,h5,h6');
    const lab = le ? le.textContent.trim() : (sel.name || '');
    if (rx.test(lab) || rx.test(sel.name || '')) {   // anchor may be a human label OR an ASP.NET name
      const i = [...sel.options].findIndex(o => o.text.trim() === val);
      if (i >= 0) { sel.selectedIndex = i; sel.dispatchEvent(new Event('input', {bubbles:true})); sel.dispatchEvent(new Event('change', {bubbles:true})); return true; }
      return false;
    }
  }
  for (const r of document.querySelectorAll("input[type=radio]")) {
    if (!vis(r)) continue;
    const l = (r.closest('label')?.textContent || document.querySelector(`label[for='${r.id}']`)?.textContent || r.parentElement?.textContent || '').trim();
    if (l === val) { r.click(); r.checked = true; r.dispatchEvent(new Event('change', {bubbles:true})); return true; }
  }
  return false;
}
"""

_JS_ALL = r"""
() => {
  const vis = el => el && el.offsetParent !== null && el.getBoundingClientRect().height > 1;
  const humanLabel = le => { if (!le) return ''; const t = le.textContent.trim();
    return /^ctl00\$|^mainContent/i.test(t) ? '' : t; };   // ASP.NET control-name is NOT a human label
  const out = [];
  for (const sel of document.querySelectorAll('select')) {
    if (!vis(sel)) continue;
    const g = sel.closest('.form-group,.row,.mb-3,.field') || sel.parentElement;
    const le = g && g.querySelector('label,.control-label,b,h5,h6');
    out.push({ type: 'select', label: humanLabel(le), name: (sel.name || sel.id || '') });
  }
  const seen = new Set();
  for (const r of document.querySelectorAll("input[type=radio]")) {
    if (!vis(r)) continue; const grp = r.name || r.id; if (seen.has(grp)) continue; seen.add(grp);
    const box = r.closest('.form-group,.row,.mb-3,.field') || r.parentElement;
    const le = box && box.querySelector('label,.control-label,b,h5,h6');
    out.push({ type: 'radio', label: humanLabel(le), name: grp });
  }
  return out;
}
"""


class Excard:
    def __init__(self, page):
        self.page = page
        self._all = None

    async def slug_for(self, prod):
        base = _base_slug(prod["name"])
        for s in (_V4_SLUG_BY_ID.get(prod["id"]), _V4_SLUG.get(base), base, _ALIAS.get(base, base)):
            if s:
                return s
        return base

    async def load(self, slug):
        await self.page.goto(V4 + slug, wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_timeout(6000)
        self._all = None
        # Forms the live probe can't drive with plain select/radio events, so their reads are stale
        # and their valid-combo space is curve-governed (see memory), not the live form:
        #   • WebForms (ASP.NET order_spec) — cascade via full __doPostBack (Foamboard, Money Packet…)
        #   • Readymade shirt modal — model/sleeve/fabric chosen in a +ADD MODEL popup (shirts, cap…)
        try:
            info = await self.page.evaluate(
                "() => ({ webforms: !!document.querySelector(\"[name*='order_spec_controller'],[name*='order_spec_standard']\"),"
                " modal: !!document.querySelector('#shirt_add_model,.shirt-model-card,[id*=\"add_model\"]') })")
        except Exception:
            info = {}
        self.form_reason = "webforms" if info.get("webforms") else ("modal" if info.get("modal") else "")
        self.is_webforms = bool(self.form_reason)

    async def all_controls(self, force=False):
        if self._all is None or force:
            try:
                self._all = await self.page.evaluate(_JS_ALL)
            except Exception:
                self._all = []
        return self._all

    async def opts(self, label_rx):
        try:
            return await self.page.evaluate(_JS_OPTS, label_rx)
        except Exception as e:
            return {"visible": False, "error": str(e)[:80]}

    async def set(self, label_rx, value):
        try:
            ok = await self.page.evaluate(_JS_SET, [label_rx, value])
        except Exception:
            ok = False
        if ok:
            await self.page.wait_for_timeout(1400)
        return ok


# ───────────────────────── influence graph ─────────────────────────
def influencers(prod, fkey):
    """Fields whose VALUE changes fkey's offered options or visibility: cascade depends + validity
    primaries constraining fkey + showWhen driver fields."""
    infl = set()
    fdef = next((f for f in prod["fields"] if f["key"] == fkey), None)
    if not fdef:
        return infl
    for d in fdef.get("depends") or []:
        infl.add(d)
    V = prod.get("validity")
    for VV in (V if isinstance(V, list) else [V] if V else []):
        if fkey in (VV.get("fields") or []):
            infl.add(VV["primary"])
    sw = fdef.get("showWhen")
    if sw:
        for c in (sw["all"] if sw.get("all") else [sw]):
            if c.get("field"):
                infl.add(c["field"])
    return infl


# ───────────────────────── comparison / DFS ─────────────────────────
async def check_product(prod, ex: Excard, our: OurSide):
    pid = prod["id"]
    fields = prod["fields"]
    order = [f["key"] for f in fields]
    fdef = {f["key"]: f for f in fields}

    # which fields are influenced BY each field (reverse graph) -> decides where we branch
    infl_of = {fk: influencers(prod, fk) for fk in order}
    influences = {fk: set() for fk in order}
    for fk in order:
        for src in infl_of[fk]:
            if src in influences:
                influences[src].add(fk)
    branchers = {fk for fk in order if influences[fk]}
    # relevant(i): fields that influence any field at position >= i (for DFS memo key)
    pos = {fk: i for i, fk in enumerate(order)}
    relevant_at = {}
    for i, fk in enumerate(order):
        rel = set()
        for j in range(i, len(order)):
            rel |= infl_of[order[j]]
        relevant_at[i] = {r for r in rel if r in pos}

    findings = []           # mismatch records
    exlabel_cache = {}      # our_key -> excard label (lazily discovered, in-context)
    read_cache = {}         # (fkey, sig) -> excard opts result
    compared = set()        # (fkey, sig) already compared
    soft_skipped = set()    # conditional fields not probed on a WebForms/postback form
    match_kind = {}         # fkey -> "label" (SPA, driveable) | "name" (ASP.NET WebForms)
    memo = set()            # DFS states already fully explored
    budget = {"reads": 0, "max": 600}

    async def ex_label_for(fk):
        if exlabel_cache.get(fk):            # cache POSITIVE hits only — a transient hide (field
            return exlabel_cache[fk]         # not yet revealed) must not poison later branches
        ctrls = await ex.all_controls(force=True)
        our_lab = fdef[fk]["label"]
        # 1) human label (SPA products, driveable) — anchor on the label text
        hit = next((c["label"] for c in ctrls
                    if c.get("label") and not _CHROME.search(c["label"]) and label_match(our_lab, c["label"])), None)
        if hit:
            match_kind[fk] = "label"
        else:  # 2) ASP.NET control name (WebForms full-postback form) — anchor on the raw name
            hit = next((c["name"] for c in ctrls
                        if c.get("name") and not _CHROME.search(c["name"])
                        and name_key_match(c["name"], fk, our_lab)), None)
            if hit:
                match_kind[fk] = "name"
        if hit:
            exlabel_cache[fk] = hit
        return hit

    def sig_of(fk, V):
        return tuple(sorted((k, V[k]) for k in infl_of[fk] if k in V))

    async def compare(fk, V):
        ofld = None
        res = our.resolve(pid, V)
        ofld = next((f for f in res["fields"] if f["key"] == fk), None)
        if not ofld:
            return
        if ofld["kind"] in ("number", "image", "swatch"):
            return          # dimension inputs / colour-swatch & image-card pickers: not a select/radio combo axis
        if getattr(ex, "is_webforms", False) and infl_of[fk]:
            soft_skipped.add(fk)      # conditional field on a postback form — can't drive the driver
            return                    # via native events, so the read is stale; curve-validity stands
        # A cascade/validity field can only be compared if EVERY driver it depends on matched an
        # Excard control (so we actually set the driver on the live form). If a driver is unmatched,
        # the Excard control sits at its "select … first" placeholder and the read is meaningless.
        if any(infl not in exlabel_cache for infl in infl_of[fk]):
            soft_skipped.add(fk)
            return
        sig = sig_of(fk, V)
        if (fk, sig) in compared:
            return
        compared.add((fk, sig))
        exlab = await ex_label_for(fk)
        our_vis = ofld["visible"]
        our_opts = ofld["options"] if our_vis else []
        if exlab is None:
            # no matching excard control; only a problem if WE show a real multi-option control
            if our_vis and ofld["kind"] in ("select",) and len(our_opts) > 1:
                findings.append({"field": fk, "our_label": fdef[fk]["label"], "context": dict(V),
                                 "issue": "our_control_not_on_excard", "our_options": our_opts})
            return
        rx = "^" + re.escape(exlab) + "$"
        key = (fk, sig)
        if key in read_cache:
            exres = read_cache[key]
        else:
            budget["reads"] += 1
            exres = await ex.opts(rx)
            read_cache[key] = exres
        ex_vis = exres.get("visible", False)
        ex_opts = exres.get("options", []) if ex_vis else []
        # visibility mismatch
        if our_vis != ex_vis:
            findings.append({"field": fk, "our_label": fdef[fk]["label"], "context": dict(V),
                             "issue": "visibility", "we_show": our_vis, "excard_shows": ex_vis,
                             "our_options": our_opts, "excard_options": ex_opts})
            return
        if not our_vis:
            return
        # option-set diff (canon-matched). Strip the field's own label nouns (ours + excard's) which
        # v4 repeats inside option text, so "No Round Corner" == our "No", "…Diameter 3mm" == "3mm".
        lbl = tuple(set(labnorm(fdef[fk]["label"]).split()) | set(labnorm(exlab).split()))
        oc = {vkey(o, lbl): o for o in our_opts}
        ec = {vkey(o, lbl): o for o in ex_opts}
        over = [oc[c] for c in oc if c not in ec]          # we offer, excard doesn't -> invalid combo we allow
        under = [ec[c] for c in ec if c not in oc]         # excard offers, we don't
        if over or under:
            findings.append({"field": fk, "our_label": fdef[fk]["label"], "context": dict(V),
                             "issue": "options", "OVER_we_offer_excard_doesnt": over,
                             "UNDER_excard_offers_we_dont": under,
                             "our_options": our_opts, "excard_options": ex_opts})

    def our_field(fk, V):
        res = our.resolve(pid, V)
        return next((f for f in res["fields"] if f["key"] == fk), None)

    async def value_to_set(fk, V, ofld):
        """The common (both-offered) values to descend for coverage. Excard value strings, mapped."""
        exlab = await ex_label_for(fk)
        our_opts = ofld["options"]
        if exlab is None:
            return [(o, None) for o in our_opts]        # excard has no control; drive our side only
        rx = "^" + re.escape(exlab) + "$"
        key = (fk, sig_of(fk, V))
        exres = read_cache.get(key)
        if exres is None:
            budget["reads"] += 1
            exres = await ex.opts(rx); read_cache[key] = exres
        ex_opts = exres.get("options", []) if exres.get("visible") else []
        lbl = tuple(set(labnorm(fdef[fk]["label"]).split()) | set(labnorm(exlab).split()))
        ecanon = {vkey(o, lbl): o for o in ex_opts}
        pairs = []
        for o in our_opts:
            ev = ecanon.get(vkey(o, lbl))
            if ev is not None:
                pairs.append((o, ev))                    # (our value, excard value)
        if not pairs and our_opts:                       # no common ground: still walk our first opt
            pairs = [(our_opts[0], None)]
        return pairs

    async def dfs(i, V):
        if i >= len(order) or budget["reads"] >= budget["max"]:
            return
        state = (i, tuple(sorted((k, V[k]) for k in relevant_at[i] if k in V)))
        if state in memo:
            return
        memo.add(state)
        fk = order[i]
        ofld = our_field(fk, V)
        await compare(fk, V)
        if ofld is None or not ofld["visible"] or ofld["kind"] == "number" or not ofld["options"]:
            await dfs(i + 1, V)         # nothing to select here; advance
            return
        pairs = await value_to_set(fk, V, ofld)
        vals = pairs if fk in branchers else pairs[:1]
        for our_v, ex_v in vals:
            V2 = dict(V); V2[fk] = our_v
            if ex_v is not None:
                exlab = exlabel_cache.get(fk)
                if exlab:
                    await ex.set("^" + re.escape(exlab) + "$", ex_v)
            await dfs(i + 1, V2)

    await dfs(0, {})
    matched = len(exlabel_cache)   # fields that resolved to an Excard control
    # Form type from HOW fields matched: SPA controls carry human labels (driveable, authoritative);
    # ASP.NET WebForms controls only match by name and cascade via full __doPostBack (not driveable
    # by native events, and NOT authoritative — validity there is curve-governed, see memory). A form
    # with any name-match and no label-match is a WebForms form.
    webforms = bool(getattr(ex, "is_webforms", False)) or (bool(match_kind) and "label" not in match_kind.values())
    # A form with NO matchable config control is a legacy / postback form the live probe can't touch
    # (money-packet, foamboard, envelope, folder-picker …). Emit ONE product note, not per-field spam.
    if matched == 0 and findings:
        findings = [{"issue": "form_unprobeable_or_legacy", "context": {},
                     "note": "no config control matched by human label or ASP.NET name — live cascade "
                             "not probeable; validity governed by captured price curves",
                     "our_fields": [f["key"] for f in fields if f.get("options")][:40]}]
    elif webforms:
        # WebForms/postback form: keep the findings for reference but demote them — the live form is
        # not authoritative and its cascade can't be driven, so these are not actionable mismatches.
        for f in findings:
            if f["issue"] in ("options", "visibility"):
                f["issue_downgraded_from"] = f["issue"]
                f["issue"] = "webforms_unverified"
    # REAL validity mismatches = options / visibility on a driveable SPA form only
    real = [f for f in findings if f["issue"] in ("options", "visibility")]
    form_type = (getattr(ex, "form_reason", "") or "webforms") if webforms else ("legacy" if matched == 0 else "spa")
    return {"id": pid, "name": prod["name"], "findings": findings,
            "real_mismatches": len(real), "matched_fields": matched,
            "form_type": form_type,
            "soft_skipped_conditional": sorted(soft_skipped),
            "reads": budget["reads"], "fields_checked": len(compared),
            "branchers": sorted(branchers)}


# ───────────────────────── our-side-only enumeration (offline) ─────────────────────────
def our_only(prod, our: OurSide):
    """Enumerate our valid-combo cascade offline (no browser) — sanity view of what we offer."""
    pid = prod["id"]
    order = [f["key"] for f in prod["fields"]]
    infl_of = {fk: influencers(prod, fk) for fk in order}
    influences = {fk: set() for fk in order}
    for fk in order:
        for s in infl_of[fk]:
            if s in influences:
                influences[s].add(fk)
    branchers = {fk for fk in order if influences[fk]}
    lines = []
    seen = set()

    def dfs(i, V):
        if i >= len(order):
            return
        fk = order[i]
        f = next((x for x in our.resolve(pid, V)["fields"] if x["key"] == fk), None)
        if f is None:
            return
        if f["visible"] and f["kind"] != "number" and f["options"]:
            sig = tuple(sorted((k, V[k]) for k in infl_of[fk] if k in V))
            if (fk, sig) not in seen:
                seen.add((fk, sig))
                lines.append({"field": fk, "context": {k: V[k] for k in infl_of[fk] if k in V},
                              "options": f["options"]})
            vals = f["options"] if fk in branchers else f["options"][:1]
            for v in vals:
                V2 = dict(V); V2[fk] = v; dfs(i + 1, V2)
        else:
            dfs(i + 1, V)

    dfs(0, {})
    return {"id": pid, "name": prod["name"], "nodes": lines}


# ───────────────────────── runner ─────────────────────────
async def run(ids, our_only_mode=False):
    data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))["products"]
    by_id = {p["id"]: p for p in data}
    targets = [by_id[i] for i in ids if i in by_id]
    our = OurSide()
    report = {}
    if our_only_mode:
        for p in targets:
            r = our_only(p, our)
            report[str(p["id"])] = r
            print(f"id{p['id']:>3} {p['name'][:34]:34} nodes={len(r['nodes'])}")
        our.close()
        print(json.dumps(report, indent=1, ensure_ascii=False)[:4000])
        return
    async with async_playwright_ctx() as pw:
        b = await B.launch(pw)
        page = await b.new_page(viewport={"width": 1500, "height": 2600})
        await login_v4(page)
        ex = Excard(page)
        for p in targets:
            if p.get("engine") == "contact":
                continue
            slug = await ex.slug_for(p)
            try:
                await ex.load(slug)
                r = await check_product(p, ex, our)
            except Exception as e:
                r = {"id": p["id"], "name": p["name"], "error": str(e)[:200], "findings": []}
            r["slug"] = slug
            report[str(p["id"])] = r
            findings = r.get("findings", [])
            real = r.get("real_mismatches", len([f for f in findings if f.get("issue") in ("options", "visibility")]))
            soft = len(findings) - real
            ftype = r.get("form_type")
            if "error" in r:
                status = "ERROR"
            elif ftype in ("legacy", "webforms", "modal"):
                nf = sum(1 for f in findings if f.get("issue") not in ("form_unprobeable_or_legacy",))
                status = f"SKIP ({ftype} — curve-governed)" + (f", {nf} unverified" if nf else "")
            elif real:
                status = f"{real} MISMATCH" + (f" (+{soft} soft)" if soft else "")
            else:
                status = "PASS" + (f" ({soft} soft)" if soft else "")
            print(f"id{p['id']:>3} {p['name'][:34]:34} slug={slug:28} reads={r.get('reads','?'):>4} "
                  f"checked={r.get('fields_checked','?'):>3} matched={r.get('matched_fields','?'):>2}  {status}", file=sys.stderr)
            for f in findings:
                if f.get("issue") in ("form_unprobeable_or_legacy", "webforms_unverified", "our_control_not_on_excard"):
                    continue        # probe-limitation noise; only print actionable SPA mismatches
                print(f"     · {f.get('field','-'):20} {f['issue']:24} "
                      f"OVER={f.get('OVER_we_offer_excard_doesnt', f.get('our_options') if f['issue']!='options' else [])} "
                      f"UNDER={f.get('UNDER_excard_offers_we_dont','')}", file=sys.stderr)
        await b.close()
    our.close()
    # merge into existing report so single-product runs don't wipe others
    existing = {}
    if REPORT.exists():
        try:
            existing = json.loads(REPORT.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    existing.update(report)
    REPORT.write_text(json.dumps(existing, indent=1, ensure_ascii=False), encoding="utf-8")
    total_real = sum(r.get("real_mismatches", 0) for r in report.values())
    skipped = sum(1 for r in report.values() if r.get("form_type") in ("webforms", "legacy", "modal"))
    spa = sum(1 for r in report.values() if r.get("form_type") == "spa")
    print(f"\n{len(report)} product(s) checked — {spa} SPA (authoritative), {skipped} webforms/legacy "
          f"(curve-governed, skipped); {total_real} REAL mismatch(es). -> {REPORT}", file=sys.stderr)


# playwright context helper (kept local so --our-only needs no browser import side effects)
def async_playwright_ctx():
    from playwright.async_api import async_playwright
    return async_playwright()


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit(0)
    if args[0] == "--our-only":
        data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))["products"]
        ids = [int(a) for a in args[1:]] or [p["id"] for p in data]
        asyncio.run(run(ids, our_only_mode=True))
    elif args[0] == "--all":
        data = json.loads((OUT / "calculator_data.json").read_text(encoding="utf-8"))["products"]
        asyncio.run(run([p["id"] for p in data]))
    else:
        asyncio.run(run([int(a) for a in args]))
