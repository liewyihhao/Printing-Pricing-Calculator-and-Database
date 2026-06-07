"""Shared fixtures. DB tests use a throwaway 'printoka_test' database and skip
gracefully when PostgreSQL isn't reachable (e.g. PGPASSWORD not set yet)."""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app import config
from app.models import Base

TEST_DB = "printoka_test"


def _make_test_engine():
    admin = create_engine(config.dsn("postgres"), isolation_level="AUTOCOMMIT", future=True)
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname=:n"), {"n": TEST_DB}).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
    admin.dispose()
    return create_engine(config.dsn(TEST_DB), future=True)


@pytest.fixture()
def db_session():
    try:
        engine = _make_test_engine()
    except Exception as e:  # no DB / wrong creds → skip DB-dependent tests
        pytest.skip(f"PostgreSQL not available: {type(e).__name__}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    s = Session()
    try:
        yield s
    finally:
        s.close()
        engine.dispose()
