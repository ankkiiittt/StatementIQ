"""Pydantic request and response schemas for StatementIQ."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sort_order: int


class StatementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    bank_name: str | None = None
    account_last4: str | None = None
    currency: str = "INR"
    period_start: date | None = None
    period_end: date | None = None
    opening_balance: Decimal | None = None
    closing_balance: Decimal | None = None
    status: str
    reconciliation_status: str
    reconciliation_diff: Decimal | None = None
    page_count: int | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class StatementUploadResponse(BaseModel):
    statement_id: uuid.UUID
    filename: str
    status: str
    page_count: int | None = None
    message: str


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    statement_id: uuid.UUID
    row_index: int
    txn_date: date
    description_raw: str
    description_clean: str | None = None
    amount: Decimal
    direction: str
    balance_after: Decimal | None = None
    category_id: int
    category_name: str = "Other"
    category_source: str
    confidence: Decimal | None = None
    created_at: datetime
    updated_at: datetime


class PaginatedTransactionsResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TransactionUpdateRequest(BaseModel):
    category_id: int | None = None
    description_clean: str | None = None


# --- Insights Schemas ---
class CategorySpendItem(BaseModel):
    category_id: int
    category_name: str
    total_amount: Decimal
    percentage: Decimal
    transaction_count: int


class MonthlyTrendItem(BaseModel):
    month: str  # YYYY-MM
    total_spend: Decimal
    total_income: Decimal
    net_savings: Decimal


class MerchantSpendItem(BaseModel):
    merchant: str
    total_amount: Decimal
    transaction_count: int
    percentage: Decimal | None = None


class InsightsResponse(BaseModel):
    total_spend: Decimal
    total_income: Decimal
    net_savings: Decimal
    transaction_count: int
    spend_by_category: list[CategorySpendItem]
    monthly_trend: list[MonthlyTrendItem]
    top_merchants: list[MerchantSpendItem]


# --- Extraction Schemas ---
class ExtractedTransactionRow(BaseModel):
    date: str
    description: str
    amount: Decimal
    direction: str  # "debit" or "credit"
    balance: Decimal | None = None


class ExtractedStatementHeader(BaseModel):
    bank_name: str | None = None
    account_last4: str | None = None
    currency: str | None = "INR"
    period_start: str | None = None
    period_end: str | None = None
    opening_balance: Decimal | None = None
    closing_balance: Decimal | None = None


class ExtractedStatementPage(BaseModel):
    header: ExtractedStatementHeader | None = None
    transactions: list[ExtractedTransactionRow] = []


class TransactionCategoryAssignment(BaseModel):
    row_index: int
    category: str
    confidence: Decimal | None = None


class BatchCategorizationResult(BaseModel):
    categories: list[TransactionCategoryAssignment] = []


# --- Chat & QuerySpec Schemas ---
class QuerySpec(BaseModel):
    is_refusal: bool = False
    refusal_reason: str | None = None
    aggregation: str = "sum"  # "sum", "count", "average", "list", "top_n"
    direction: str | None = None  # "debit", "credit", or None
    categories: list[str] | None = None
    search: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    group_by: str | None = None  # "category", "month", "merchant", or None
    top_n_limit: int | None = 10
    order_by: str | None = None  # "amount_desc", "amount_asc", "date_desc", "date_asc"
    statement_ids: list[uuid.UUID] | None = None


class ChatRequest(BaseModel):
    message: str
    session_id: uuid.UUID | None = None


class ChatResponse(BaseModel):
    session_id: uuid.UUID
    message_id: uuid.UUID
    role: str = "assistant"
    answer: str
    filters_used: dict[str, Any]
    query_spec: dict[str, Any]
    created_at: datetime


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    query_spec: dict[str, Any] | None = None
    created_at: datetime
