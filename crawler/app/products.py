"""Registry of crawlable Excard products (order-page based).

Excard separates by PRINT METHOD: the same product name under a different method
is a distinct product with its own ID, order-page URL, and price list. Each entry
maps our internal product_id -> the /spec/<Method>/<slug> order page.

Add a product here, then:
    python -m app order-discover --product <id>     # Phase 1: enumerate valid combos
    python -m app order-crawl    --product <id>     # Phase 2: price the valid combos
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductTarget:
    product_id: int
    name: str
    method: str          # "Litho" (Offset) | "Digital" | ...
    spec_url: str


# Known order-page products. IDs match Excard's internal product IDs.
PRODUCTS: dict[int, ProductTarget] = {
    21: ProductTarget(21, "Loose Sheet", "Litho",
                      "https://www.excard.com.my/spec/Litho/Loose_Sheet"),
    50: ProductTarget(50, "Loose Sheet", "Digital",
                      "https://www.excard.com.my/spec/Digital/Loose_Sheet"),
    19: ProductTarget(19, "Booklet", "Litho",
                      "https://www.excard.com.my/spec/Litho/Booklet"),
    37: ProductTarget(37, "Booklet", "Digital",
                      "https://www.excard.com.my/spec/Digital/Booklet"),
}


def get(product_id: int) -> ProductTarget:
    if product_id not in PRODUCTS:
        raise KeyError(f"Unknown product_id {product_id}. Add it to app/products.py "
                       f"(known: {sorted(PRODUCTS)})")
    return PRODUCTS[product_id]
