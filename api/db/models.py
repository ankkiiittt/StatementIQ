"""SQLAlchemy ORM models for StatementIQ."""
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from api.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class Statement(Base):
    __tablename__ = "statements"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    bank_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="INR", default="INR")
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    opening_balance: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    closing_balance: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="processing",
        default="processing",
    )
    reconciliation_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="not_available",
        default="not_available",
    )
    reconciliation_diff: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=utc_now,
        nullable=False,
    )

    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="statement",
        cascade="all, delete-orphan",
    )
    extraction_runs: Mapped[list["ExtractionRun"]] = relationship(
        "ExtractionRun",
        back_populates="statement",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'needs_review', 'confirmed', 'failed')",
            name="chk_statement_status",
        ),
        CheckConstraint(
            "reconciliation_status IN ('passed', 'failed', 'not_available')",
            name="chk_statement_reconciliation_status",
        ),
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="category",
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    statement_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("statements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    txn_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description_raw: Mapped[str] = mapped_column(Text, nullable=False)
    description_clean: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    direction: Mapped[str] = mapped_column(Text, nullable=False)
    balance_after: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    category_source: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="model",
        default="model",
    )
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=utc_now,
        nullable=False,
    )

    statement: Mapped["Statement"] = relationship("Statement", back_populates="transactions")
    category: Mapped["Category"] = relationship("Category", back_populates="transactions")

    __table_args__ = (
        UniqueConstraint("statement_id", "row_index", name="uq_statement_row_index"),
        CheckConstraint("amount > 0", name="chk_transaction_amount_positive"),
        CheckConstraint("direction IN ('debit', 'credit')", name="chk_transaction_direction"),
        CheckConstraint("category_source IN ('model', 'user')", name="chk_transaction_category_source"),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="chk_transaction_confidence_range",
        ),
    )


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    statement_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("statements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=utc_now,
        nullable=False,
    )

    statement: Mapped["Statement"] = relationship("Statement", back_populates="extraction_runs")

    __table_args__ = (
        CheckConstraint("stage IN ('extract', 'categorize')", name="chk_extraction_run_stage"),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    query_spec: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=utc_now,
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="chk_chat_message_role"),
    )
