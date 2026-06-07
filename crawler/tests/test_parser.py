"""Parse the golden generated price-list HTML and assert structure."""
from pathlib import Path

from app.parser import parse_price_html, TIERS

GOLDEN = Path(__file__).resolve().parent.parent / "output" / "probe_generate.html"


def test_golden_parses():
    html = GOLDEN.read_text(encoding="utf-8", errors="replace")
    r = parse_price_html(html)
    assert r.ok
    # 2 color modes x 4 tiers x N quantities
    assert {p.color_mode for p in r.prices} == {"4C", "4C+4C"}
    assert {p.tier for p in r.prices} == set(TIERS)
    # 35 quantities each side in the golden file
    qtys = {p.quantity for p in r.prices}
    assert 250 in qtys and 50000 in qtys
    assert len(r.prices) == len(qtys) * 4 * 2

    # Known reference values (A4 / Gloss Art Card 250 / Matte / East M'sia).
    pt = next(p for p in r.prices
              if p.color_mode == "4C" and p.quantity == 250 and p.tier == "Platinum")
    assert float(pt.price) == 475.50
    assert pt.suffix is None

    star = next(p for p in r.prices
                if p.color_mode == "4C" and p.quantity == 500 and p.tier == "Platinum")
    assert star.suffix == "*"


def test_context_extracted():
    r = parse_price_html(GOLDEN.read_text(encoding="utf-8", errors="replace"))
    assert "A4" in r.context.get("size", "")
    assert "250gsm" in r.context.get("paper", "")
