"""SQLAlchemy ORM models — normalized schema for Excard pricing intelligence."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String,
    Text, UniqueConstraint, Index, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


def combo_hash(product_id: int, size_raw: str, paper_raw: str,
               lamination_raw: str, delivery_code: int) -> str:
    """Deterministic, field-order-independent hash for one Generate input."""
    parts = {
        "product": str(product_id),
        "size": size_raw or "",
        "paper": paper_raw or "",
        "lamination": lamination_raw or "",
        "delivery": str(delivery_code),
    }
    canonical = "|".join(f"{k}={parts[k]}" for k in sorted(parts))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class Product(Base):
    __tablename__ = "products"
    excard_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # active | unsupported | done
    status: Mapped[str] = mapped_column(String(20), default="active")
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_crawled: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    groups: Mapped[list["OptionGroup"]] = relationship(back_populates="product")


class OptionGroup(Base):
    __tablename__ = "option_groups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.excard_id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))          # e.g. "Size", "Paper", "Lamination"
    field_name: Mapped[str] = mapped_column(String(300))    # ASP.NET control name
    ordinal: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped[Product] = relationship(back_populates="groups")
    values: Mapped[list["OptionValue"]] = relationship(back_populates="group")
    __table_args__ = (UniqueConstraint("product_id", "field_name", name="uq_group_product_field"),)


class OptionValue(Base):
    __tablename__ = "option_values"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("option_groups.id", ondelete="CASCADE"))
    raw_value: Mapped[str] = mapped_column(Text)   # exact comma-packed payload (the <option> value)
    label: Mapped[str] = mapped_column(Text)       # exact visible label
    ordinal: Mapped[int] = mapped_column(Integer, default=0)

    group: Mapped[OptionGroup] = relationship(back_populates="values")
    __table_args__ = (UniqueConstraint("group_id", "raw_value", name="uq_value_group_raw"),)


class Delivery(Base):
    __tablename__ = "deliveries"
    code: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(100))


class Combination(Base):
    __tablename__ = "combinations"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.excard_id", ondelete="CASCADE"))
    combo_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # Store both the raw payloads (stable identity) and human labels (readability).
    size_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    paper_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    paper_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    lamination_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    lamination_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_code: Mapped[int] = mapped_column(ForeignKey("deliveries.code"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    work: Mapped["WorkItem"] = relationship(back_populates="combination", uselist=False)


class WorkItem(Base):
    __tablename__ = "work_queue"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    combination_id: Mapped[int] = mapped_column(
        ForeignKey("combinations.id", ondelete="CASCADE"), unique=True)
    # pending | in_progress | done | failed | skipped
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    combination: Mapped[Combination] = relationship(back_populates="work")
    __table_args__ = (Index("ix_work_status", "status"),)


class Pricing(Base):
    __tablename__ = "pricing"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    combination_id: Mapped[int] = mapped_column(
        ForeignKey("combinations.id", ondelete="CASCADE"), index=True)
    color_mode: Mapped[str] = mapped_column(String(10))     # "4C" | "4C+4C"
    quantity: Mapped[int] = mapped_column(Integer)
    tier: Mapped[str] = mapped_column(String(20))           # Platinum|Gold|Silver|Cash
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    suffix: Mapped[str | None] = mapped_column(String(8), nullable=True)  # e.g. "*"
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        UniqueConstraint("combination_id", "color_mode", "quantity", "tier",
                         name="uq_price_point"),
    )


class PriceHistory(Base):
    __tablename__ = "price_history"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    combination_id: Mapped[int] = mapped_column(Integer, index=True)
    color_mode: Mapped[str] = mapped_column(String(10))
    quantity: Mapped[int] = mapped_column(Integer)
    tier: Mapped[str] = mapped_column(String(20))
    old_price: Mapped[float] = mapped_column(Numeric(12, 2))
    new_price: Mapped[float] = mapped_column(Numeric(12, 2))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RawPayload(Base):
    __tablename__ = "raw_payloads"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    combination_id: Mapped[int] = mapped_column(
        ForeignKey("combinations.id", ondelete="CASCADE"), index=True)
    html: Mapped[str] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CrawlSession(Base):
    __tablename__ = "crawl_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    stats: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class OrderWork(Base):
    """One crawl unit on the order page: a config whose quantities get swept."""
    __tablename__ = "order_work"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, index=True)
    size_label: Mapped[str] = mapped_column(Text)
    paper_label: Mapped[str] = mapped_column(Text)
    colour_side: Mapped[str] = mapped_column(String(40))     # e.g. "4C (Front)"
    package: Mapped[str] = mapped_column(String(40))         # e.g. "Normal"
    delivery_code: Mapped[int] = mapped_column(Integer)
    priority: Mapped[int] = mapped_column(Integer, default=100, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    __table_args__ = (
        UniqueConstraint("product_id", "size_label", "paper_label", "colour_side",
                         "package", "delivery_code", name="uq_order_config"),
    )


class OrderQuote(Base):
    """A real order-page quote for one (config, quantity): the full breakdown."""
    __tablename__ = "order_quotes"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_work_id: Mapped[int] = mapped_column(
        ForeignKey("order_work.id", ondelete="CASCADE"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    before_discount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    discount_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    after_discount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    handling_fee: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    delivery_fee: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    nett: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    tiers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # {tier: nett}
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        UniqueConstraint("order_work_id", "quantity", name="uq_order_quote"),
    )


class ReverseEngineeringAnalysis(Base):
    """Stub for the later reverse-engineering engine; intentionally minimal."""
    __tablename__ = "reverse_engineering_analysis"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, index=True)
    metric: Mapped[str] = mapped_column(String(100))
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
