"""create_initial_schema_and_seed_categories

Revision ID: 1d38b6d153de
Revises:
Create Date: 2026-10-19 12:16:05.696645

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1d38b6d153de"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_CATEGORIES = [
    {"name": "Food and Dining", "sort_order": 1},
    {"name": "Groceries", "sort_order": 2},
    {"name": "Rent and Housing", "sort_order": 3},
    {"name": "Utilities and Bills", "sort_order": 4},
    {"name": "Transport", "sort_order": 5},
    {"name": "Shopping", "sort_order": 6},
    {"name": "Health", "sort_order": 7},
    {"name": "Entertainment", "sort_order": 8},
    {"name": "Travel", "sort_order": 9},
    {"name": "Education", "sort_order": 10},
    {"name": "Transfers", "sort_order": 11},
    {"name": "Income", "sort_order": 12},
    {"name": "Fees and Charges", "sort_order": 13},
    {"name": "Other", "sort_order": 14},
]


def upgrade() -> None:
    # 1. categories
    categories_table = op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # 2. statements
    op.create_table(
        "statements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("bank_name", sa.Text(), nullable=True),
        sa.Column("account_last4", sa.String(length=4), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="INR", nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("opening_balance", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("closing_balance", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("status", sa.Text(), server_default="processing", nullable=False),
        sa.Column("reconciliation_status", sa.Text(), server_default="not_available", nullable=False),
        sa.Column("reconciliation_diff", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('processing', 'needs_review', 'confirmed', 'failed')",
            name="chk_statement_status",
        ),
        sa.CheckConstraint(
            "reconciliation_status IN ('passed', 'failed', 'not_available')",
            name="chk_statement_reconciliation_status",
        ),
    )

    # 3. transactions
    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("statement_id", sa.Uuid(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("txn_date", sa.Date(), nullable=False),
        sa.Column("description_raw", sa.Text(), nullable=False),
        sa.Column("description_clean", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("balance_after", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("category_source", sa.Text(), server_default="model", nullable=False),
        sa.Column("confidence", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["statement_id"], ["statements.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("statement_id", "row_index", name="uq_statement_row_index"),
        sa.CheckConstraint("amount > 0", name="chk_transaction_amount_positive"),
        sa.CheckConstraint("direction IN ('debit', 'credit')", name="chk_transaction_direction"),
        sa.CheckConstraint(
            "category_source IN ('model', 'user')",
            name="chk_transaction_category_source",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="chk_transaction_confidence_range",
        ),
    )
    op.create_index("ix_transactions_statement_id", "transactions", ["statement_id"])
    op.create_index("ix_transactions_txn_date", "transactions", ["txn_date"])
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"])

    # 4. extraction_runs
    op.create_table(
        "extraction_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("statement_id", sa.Uuid(), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["statement_id"], ["statements.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "stage IN ('extract', 'categorize')",
            name="chk_extraction_run_stage",
        ),
    )
    op.create_index("ix_extraction_runs_statement_id", "extraction_runs", ["statement_id"])

    # 5. chat_messages
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "query_spec",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="chk_chat_message_role"),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])

    # Seed categories
    op.bulk_insert(categories_table, DEFAULT_CATEGORIES)


def downgrade() -> None:
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_extraction_runs_statement_id", table_name="extraction_runs")
    op.drop_table("extraction_runs")
    op.drop_index("ix_transactions_category_id", table_name="transactions")
    op.drop_index("ix_transactions_txn_date", table_name="transactions")
    op.drop_index("ix_transactions_statement_id", table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("statements")
    op.drop_table("categories")
