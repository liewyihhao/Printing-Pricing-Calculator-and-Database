"""Parse the generated price-list tables from probe_generate.html to confirm we
can extract clean Quantity x price rows."""
import re, json
from pathlib import Path
from html.parser import HTMLParser

HTML = Path(__file__).parent / "output" / "probe_generate.html"


class TableExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.cur, self.row, self.cell = [], None, None, None
        self.in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "table": self.cur = []
        elif tag == "tr" and self.cur is not None: self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.in_cell = True; self.cell = []

    def handle_endtag(self, tag):
        if tag == "table" and self.cur is not None:
            if self.cur: self.tables.append(self.cur)
            self.cur = None
        elif tag == "tr" and self.row is not None:
            self.cur.append(self.row); self.row = None
        elif tag in ("td", "th") and self.in_cell:
            self.row.append(" ".join("".join(self.cell).split())); self.in_cell = False

    def handle_data(self, data):
        if self.in_cell: self.cell.append(data)


def main():
    p = TableExtractor(); p.feed(HTML.read_text(encoding="utf-8", errors="replace"))
    # A price table: has a "Quantity"-ish header and rows where col0 is a number
    # and other cols look like money (\d+\.\d{2}).
    price_tables = []
    for t in p.tables:
        flat = " ".join(c for r in t for c in r)
        money = len(re.findall(r"\d+\.\d{2}", flat))
        has_qty = bool(re.search(r"quantity|qty", flat, re.I))
        if money >= 6 and has_qty:
            price_tables.append(t)
    print(f"Found {len(price_tables)} price tables.")
    for i, t in enumerate(price_tables):
        print(f"\n=== Price table #{i} ({len(t)} rows) ===")
        for r in t[:8]:
            print("   ", r)
    # Save structured
    out = Path(__file__).parent / "output" / "parsed_pricelist.json"
    out.write_text(json.dumps(price_tables, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved -> {out.name}")


if __name__ == "__main__":
    main()
