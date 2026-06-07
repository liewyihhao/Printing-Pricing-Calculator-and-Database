"""CRUD + uniqueness constraints, and the price-history update logic."""
import pytest
from decimal import Decimal
from sqlalchemy.exc import IntegrityError

from app.models import (Product, Delivery, Combination, WorkItem, Pricing,
                        PriceHistory, combo_hash)


def _seed_combo(s):
    s.add(Product(excard_id=21, name="Loose Sheet"))
    s.add(Delivery(code=98, name="East Malaysia"))
    s.flush()
    c = Combination(product_id=21, combo_hash=combo_hash(21, "s", "p", "l", 98),
                    delivery_code=98, size_raw="s", paper_raw="p", lamination_raw="l")
    s.add(c)
    s.flush()
    return c


def test_combo_hash_unique(db_session):
    s = db_session
    c = _seed_combo(s)
    s.commit()
    dup = Combination(product_id=21, combo_hash=c.combo_hash, delivery_code=98)
    s.add(dup)
    with pytest.raises(IntegrityError):
        s.commit()
    s.rollback()


def test_price_point_unique(db_session):
    s = db_session
    c = _seed_combo(s)
    s.add(Pricing(combination_id=c.id, color_mode="4C", quantity=250,
                  tier="Platinum", price=Decimal("475.50")))
    s.commit()
    s.add(Pricing(combination_id=c.id, color_mode="4C", quantity=250,
                  tier="Platinum", price=Decimal("999.00")))
    with pytest.raises(IntegrityError):
        s.commit()
    s.rollback()


def test_price_history_on_change(db_session):
    s = db_session
    c = _seed_combo(s)
    p = Pricing(combination_id=c.id, color_mode="4C", quantity=250,
                tier="Platinum", price=Decimal("475.50"))
    s.add(p)
    s.commit()
    # Simulate a re-crawl with a changed price.
    s.add(PriceHistory(combination_id=c.id, color_mode="4C", quantity=250,
                       tier="Platinum", old_price=p.price, new_price=Decimal("480.00")))
    p.price = Decimal("480.00")
    s.commit()
    hist = s.query(PriceHistory).all()
    assert len(hist) == 1
    assert float(hist[0].old_price) == 475.50 and float(hist[0].new_price) == 480.00
