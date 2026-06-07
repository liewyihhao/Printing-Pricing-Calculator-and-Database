"""Database engine/session helpers and schema initialization."""
from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from . import config
from .models import Base, Delivery

_engine = None
_Session = None


def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(config.dsn(), pool_pre_ping=True, future=True)
    return _engine


def Session_() -> Session:
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=engine(), expire_on_commit=False, future=True)
    return _Session()


@contextmanager
def session_scope():
    s = Session_()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def ensure_database():
    """CREATE DATABASE <name> if it does not exist (connects to 'postgres')."""
    admin = create_engine(config.dsn("postgres"), isolation_level="AUTOCOMMIT", future=True)
    with admin.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"),
            {"n": config.PGDATABASE},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{config.PGDATABASE}"'))
    admin.dispose()


def init_db():
    """Create database, all tables, and seed delivery rows. Idempotent."""
    ensure_database()
    Base.metadata.create_all(engine())
    with session_scope() as s:
        for code, name in config.DELIVERIES.items():
            if not s.get(Delivery, code):
                s.add(Delivery(code=code, name=name))
