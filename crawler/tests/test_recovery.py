"""Recovery behaviour: session-loss detection + quarantine after max attempts."""
import asyncio

from app import config
from app.browser import is_logged_out
from app.models import Product, Delivery, Combination, WorkItem, combo_hash


class FakePage:
    def __init__(self, url):
        self.url = url

    def locator(self, _):  # pretend the login button is absent
        class _L:
            async def count(self_inner):
                return 0
        return _L()


def test_is_logged_out_by_url():
    assert asyncio.run(is_logged_out(FakePage("https://www.excard.com.my/login")))
    assert not asyncio.run(is_logged_out(FakePage("https://www.excard.com.my/price-list/Litho/21")))


def test_quarantine_after_max_attempts(db_session, monkeypatch):
    """_finish('error') should retry until MAX_ATTEMPTS, then mark failed."""
    from app import runner
    monkeypatch.setattr(config, "MAX_ATTEMPTS", 2)
    # Route runner's session_scope to the test DB session.
    import contextlib

    @contextlib.contextmanager
    def fake_scope():
        yield db_session
        db_session.commit()
    monkeypatch.setattr(runner, "session_scope", fake_scope)

    db_session.add(Product(excard_id=21, name="X"))
    db_session.add(Delivery(code=98, name="East"))
    db_session.flush()
    c = Combination(product_id=21, combo_hash=combo_hash(21, "s", "p", "l", 98),
                    delivery_code=98)
    db_session.add(c); db_session.flush()
    item = WorkItem(combination_id=c.id, status="in_progress", attempts=1)
    db_session.add(item); db_session.commit()

    runner._finish(item.id, "error", "boom")
    db_session.refresh(item)
    assert item.status == "pending"      # attempt 1 < 2 -> retry

    item.attempts = 2; db_session.commit()
    runner._finish(item.id, "error", "boom again")
    db_session.refresh(item)
    assert item.status == "failed"       # attempts reached MAX -> quarantine
