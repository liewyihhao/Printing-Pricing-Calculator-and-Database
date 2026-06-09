"""Stratified booklet price sampler (products 19 Litho & 37 Digital).

Reads output/booklet_options_<id>.json (the discovered cascade) and builds a
DOE that isolates the cost drivers the engine must learn:
  * PAGE sweep   - vary page count at a fixed size/paper -> per-content-sheet cost
  * SIZE sweep   - vary size at a fixed page/paper        -> area scaling
  * PAPER sweep  - vary content paper at fixed size/page  -> gsm/material cost
  * COLOUR       - a few 1C(Both) configs                 -> colour effect
Each config sweeps the whole quantity ladder (so volume economy is captured for
free). Saves output/booklet_samples_<id>.json as a list of:
  {orientation,size,ordertype,binding,page,cover_paper,content_paper,
   content_colour,outer_inner,qty,cash,weight}

Run:  python -m app.booklet_sampler <product_id> [account]
"""
from __future__ import annotations

import json
import sys
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

from . import accounts, products
from .browser import launch
from .order_runner import _new_page, _relaunch
from .booklet_capture import BookletSpec, capture_booklet
from .logging_setup import log

OUT = Path(__file__).resolve().parent.parent / "output"


def _gsm(paper: str) -> int:
    import re
    m = re.search(r"(\d+)\s*gsm", paper)
    return int(m.group(1)) if m else 250


def _valid_combos(opts: dict) -> dict:
    return {k: v for k, v in opts["combos"].items() if v}


def _pick(seq, n):
    """Evenly sample n items from a list (always includes first & last)."""
    if len(seq) <= n:
        return list(seq)
    idx = [round(i * (len(seq) - 1) / (n - 1)) for i in range(n)]
    return [seq[i] for i in sorted(set(idx))]


def build_configs(opts: dict) -> list[BookletSpec]:
    pid = opts["product_id"]
    url = opts["spec_url"]
    combos = _valid_combos(opts)
    seen = set()
    cfgs: list[BookletSpec] = []

    def add(orient, size, ot, binding, page, cover, content, colour,
            oi="4C: 4 Colour Outer Only"):
        key = (orient, size, ot, binding, page, cover, content, colour, oi)
        if key in seen:
            return
        seen.add(key)
        cfgs.append(BookletSpec(pid, url, orient, size, ot, binding, page,
                                cover, colour, content, "4C (Both)" if "4C" in colour
                                else colour, oi))

    # Anchor: prefer Portrait A5; fall back to any.
    def find(pred):
        for k, v in combos.items():
            o, s, ot, b = k.split("|")
            if pred(o, s, ot, b):
                return k, v
        return None, None

    # Group valid combos by binding+ordertype for per-type sampling.
    by_type: dict[tuple, list] = {}
    for k, v in combos.items():
        o, s, ot, b = k.split("|")
        by_type.setdefault((ot, b), []).append((o, s, v))

    for (ot, b), entries in by_type.items():
        # Prefer Portrait A5 anchor within this type, else first entry.
        anchor = next((e for e in entries if e[0] == "Portrait" and "A5" in e[1]),
                      entries[0])
        o, s, v = anchor
        covers = list(v["covers"].keys())
        # Anchor cover = a mid-weight card; anchor content = mid content paper.
        cover = covers[len(covers) // 2]
        contents = v["covers"][cover]["content_papers"]
        if not contents:
            continue
        content = contents[len(contents) // 2]
        colours = v["content_colours"] or ["4C (Both)"]
        c4 = "4C (Both)" if "4C (Both)" in colours else colours[0]
        c1 = "1C (Both)" if "1C (Both)" in colours else None
        pages = v["pages"]

        # 1) PAGE sweep (5 pages across the valid range) at anchor size/paper.
        for pg in _pick(pages, 5):
            add(o, s, ot, b, pg, cover, content, c4)
        mid_page = pages[len(pages) // 2]

        # 2) SIZE sweep at the mid page (all sizes valid for this type).
        for (o2, s2, v2) in entries:
            cv2 = list(v2["covers"].keys())
            if not cv2:
                continue
            cover2 = cv2[len(cv2) // 2]
            ct2 = v2["covers"][cover2]["content_papers"]
            if not ct2 or mid_page not in v2["pages"]:
                continue
            content2 = ct2[len(ct2) // 2]
            add(o2, s2, ot, b, mid_page, cover2, content2, c4)

        # 3) PAPER sweep: vary content paper (thin/thick) at anchor size/mid page.
        if mid_page in pages:
            for content3 in _pick(contents, 3):
                add(o, s, ot, b, mid_page, cover, content3, c4)
            # also vary cover (thin vs thick) once
            for cover3 in _pick(covers, 2):
                ct3 = v["covers"][cover3]["content_papers"]
                if ct3:
                    add(o, s, ot, b, mid_page, cover3, ct3[len(ct3)//2], c4)

        # 4) COLOUR: a couple of 1C(Both) configs.
        if c1 and mid_page in pages:
            add(o, s, ot, b, mid_page, cover, content, c1)
            add(o, s, ot, b, pages[0], cover, content, c1)

    return cfgs


async def run(product_id: int, account_id: int = 1, recycle_every: int = 5):
    opts = json.loads((OUT / f"booklet_options_{product_id}.json").read_text())
    cfgs = build_configs(opts)
    log.info("booklet_sample.start", product=product_id, configs=len(cfgs))
    print(f"sampling {len(cfgs)} booklet configs for product {product_id}...")
    account = accounts.get(account_id)
    out_path = OUT / f"booklet_samples_{product_id}.json"
    results: list[dict] = []
    if out_path.exists():
        try:
            results = json.loads(out_path.read_text())
        except Exception:
            results = []
    done_keys = {(r["size"], r["binding"], r["page"], r["cover_paper"],
                  r["content_paper"], r["content_colour"], r["orientation"],
                  r["ordertype"]) for r in results}

    async with async_playwright() as pw:
        browser = await launch(pw)
        page = await _new_page(browser, account=account)
        done = 0
        for spec in cfgs:
            ckey = (spec.size, spec.binding, spec.page, spec.cover_paper,
                    spec.content_paper, spec.content_colour, spec.orientation,
                    spec.ordertype)
            if ckey in done_keys:
                continue
            if done and done % recycle_every == 0:
                browser, page = await _relaunch(pw, browser, account)
            try:
                rows = await capture_booklet(page, spec)
                for r in rows:
                    if r["cash"]:
                        results.append({
                            "orientation": spec.orientation, "size": spec.size,
                            "ordertype": spec.ordertype, "binding": spec.binding,
                            "page": spec.page, "cover_paper": spec.cover_paper,
                            "content_paper": spec.content_paper,
                            "content_colour": spec.content_colour,
                            "outer_inner": spec.outer_inner,
                            "qty": r["qty"], "cash": r["cash"], "weight": r["weight"]})
                out_path.write_text(json.dumps(results, indent=0))
                log.info("booklet_sample.progress", done=done + 1, total=len(cfgs),
                         points=len(results))
            except Exception as e:  # noqa: BLE001
                log.error("booklet_sample.error", error=repr(e)[:140])
                browser, page = await _relaunch(pw, browser, account)
            done += 1
        try:
            await browser.close()
        except Exception:
            pass
    out_path.write_text(json.dumps(results, indent=0))
    log.info("booklet_sample.done", product=product_id, points=len(results))
    print(f"\nWrote {out_path}  ({len(results)} price points)")


if __name__ == "__main__":
    pid = int(sys.argv[1]) if len(sys.argv) > 1 else 19
    acct = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    asyncio.run(run(pid, acct))
