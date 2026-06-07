"""Parse Excard's generated price-list HTML into structured price points.

Output shape:
    {
      "context": {"shipping":..., "size":..., "paper":..., "lamination":...},
      "prices": [
         {"color_mode":"4C","quantity":250,"tier":"Platinum","price":475.50,"suffix":None},
         ...
      ]
    }
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

TIERS = ("Platinum", "Gold", "Silver", "Cash")
_QTY_RE = re.compile(r"^\d{1,3}(?:,\d{3})*$|^\d+$")
_PRICE_RE = re.compile(r"^(\d+(?:\.\d+)?)(\*?)$")


class _TableExtractor(HTMLParser):
    """Flatten every <table> into a list of rows (each a list of cell strings)."""

    def __init__(self):
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._cur = None
        self._row = None
        self._cell = None
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._cur = []
        elif tag == "tr" and self._cur is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._in_cell = True
            self._cell = []

    def handle_endtag(self, tag):
        if tag == "table" and self._cur is not None:
            if self._cur:
                self.tables.append(self._cur)
            self._cur = None
        elif tag == "tr" and self._row is not None:
            self._cur.append(self._row)
            self._row = None
        elif tag in ("td", "th") and self._in_cell:
            self._row.append(" ".join("".join(self._cell).split()))
            self._in_cell = False

    def handle_data(self, data):
        if self._in_cell:
            self._cell.append(data)


@dataclass
class PricePoint:
    color_mode: str
    quantity: int
    tier: str
    price: float
    suffix: str | None = None


@dataclass
class ParseResult:
    context: dict = field(default_factory=dict)
    prices: list[PricePoint] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.prices) > 0


def _parse_context(cell: str) -> dict:
    """'Shipping To : East M'sia Size : A4 ... Paper : ... Lamination : ...'"""
    ctx = {}
    for key, label in (("shipping", "Shipping To"), ("size", "Size"),
                       ("paper", "Paper"), ("lamination", "Lamination")):
        m = re.search(rf"{label}\s*:\s*(.*?)(?=(?:Shipping To|Size|Paper|Lamination)\s*:|$)",
                      cell)
        if m:
            ctx[key] = m.group(1).strip()
    return ctx


def parse_price_html(html: str) -> ParseResult:
    extractor = _TableExtractor()
    extractor.feed(html)

    result = ParseResult()
    color_mode = None
    tier_cols: list[str] | None = None

    for table in extractor.tables:
        for row in table:
            cells = [c.strip() for c in row]
            joined = " ".join(cells)

            if not result.context and "Shipping To" in joined and ":" in joined:
                result.context = _parse_context(joined)

            # Section markers.
            non_empty = [c for c in cells if c]
            if non_empty == ["4C"]:
                color_mode, tier_cols = "4C", None
                continue
            if non_empty == ["4C+4C"]:
                color_mode, tier_cols = "4C+4C", None
                continue

            # Header row defines tier column order.
            if cells[:1] == ["Quantity"] and any(t in cells for t in TIERS):
                tier_cols = cells[1:]
                continue

            if color_mode is None or tier_cols is None:
                continue

            # Data row: first cell a quantity, rest are prices.
            if not cells or not _QTY_RE.match(cells[0]):
                continue
            qty = int(cells[0].replace(",", ""))
            for tier, raw in zip(tier_cols, cells[1:]):
                if tier not in TIERS:
                    continue
                m = _PRICE_RE.match(raw.replace(",", ""))
                if not m:
                    continue
                result.prices.append(PricePoint(
                    color_mode=color_mode, quantity=qty, tier=tier,
                    price=float(m.group(1)), suffix=("*" if m.group(2) else None),
                ))
    return result
