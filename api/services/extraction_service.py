"""Transaction extraction service with LLM integration, retries, and deduplication."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from api.db.models import Category, ExtractionRun, Statement, Transaction
from api.schemas import ExtractedStatementPage, ExtractedTransactionRow
from api.services.llm.client import LLMClient
from api.services.llm.factory import get_llm_client
from api.services.llm.prompts import EXTRACTION_PROMPT_V1, RETRY_PROMPT_TEMPLATE
from api.services.llm.types import LLMResponse
from api.services.pdf_service import extract_text_per_page


def parse_date(date_str: str | None) -> date | None:
    """Parse ISO YYYY-MM-DD or standard bank date formats into date object."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


class ExtractionService:
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client or get_llm_client()

    def extract_page_with_retry(
        self,
        page_text: str,
        max_retries: int = 2,
    ) -> tuple[ExtractedStatementPage, LLMResponse]:
        """Extract transactions from one page, retrying up to max_retries on invalid JSON/schema."""
        prompt = EXTRACTION_PROMPT_V1.replace("{statement_text}", page_text)
        last_error = ""

        for attempt in range(max_retries + 1):
            if attempt > 0:
                prompt = (
                    RETRY_PROMPT_TEMPLATE
                    .replace("{error_message}", last_error)
                    .replace("{statement_text}", page_text)
                )

            try:
                page_data, llm_response = self.llm_client.generate_json(
                    prompt=prompt,
                    pydantic_schema=ExtractedStatementPage,
                    prompt_version="1.0",
                )
                return page_data, llm_response
            except ValueError as exc:
                last_error = str(exc)

        raise ValueError(f"Failed extraction after {max_retries + 1} attempts: {last_error}")

    def deduplicate_transactions(
        self,
        rows: list[ExtractedTransactionRow],
    ) -> list[ExtractedTransactionRow]:
        """Deduplicate overlapping transactions between adjacent pages."""
        seen: set[tuple[str, str, Decimal, str, Decimal | None]] = set()
        deduped: list[ExtractedTransactionRow] = []

        for row in rows:
            key = (
                row.date.strip(),
                row.description.strip(),
                row.amount,
                row.direction.lower(),
                row.balance,
            )
            if key not in seen:
                seen.add(key)
                deduped.append(row)

        return deduped

    def process_statement(
        self,
        statement_id: uuid.UUID,
        db: Session,
    ) -> Statement:
        """Execute full extraction pipeline: read PDF, call LLM, dedupe, and save in one DB transaction."""
        statement = db.get(Statement, statement_id)
        if not statement:
            raise ValueError(f"Statement {statement_id} not found.")

        file_path = Path(statement.file_path)
        if not file_path.exists():
            statement.status = "failed"
            statement.error_message = f"File not found: {file_path}"
            db.commit()
            return statement

        try:
            page_count, pages_text = extract_text_per_page(file_path)
        except Exception as exc:
            statement.status = "failed"
            statement.error_message = str(exc)
            db.commit()
            return statement

        all_extracted_rows: list[ExtractedTransactionRow] = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_latency_ms = 0
        total_cost = Decimal("0.0000")
        model_name = "unknown"

        bank_name = statement.bank_name
        account_last4 = statement.account_last4
        period_start = statement.period_start
        period_end = statement.period_end
        opening_balance = statement.opening_balance
        closing_balance = statement.closing_balance

        # Extract transactions page by page
        for page_text in pages_text:
            try:
                page_data, llm_res = self.extract_page_with_retry(page_text)
                total_input_tokens += llm_res.input_tokens
                total_output_tokens += llm_res.output_tokens
                total_latency_ms += llm_res.latency_ms
                total_cost += llm_res.estimated_cost
                model_name = llm_res.model_name

                if page_data.header:
                    h = page_data.header
                    if h.bank_name and not bank_name:
                        bank_name = h.bank_name
                    if h.account_last4 and not account_last4:
                        account_last4 = h.account_last4[-4:]
                    if h.period_start and not period_start:
                        period_start = parse_date(h.period_start)
                    if h.period_end and not period_end:
                        period_end = parse_date(h.period_end)
                    if h.opening_balance is not None and opening_balance is None:
                        opening_balance = h.opening_balance
                    if h.closing_balance is not None:
                        closing_balance = h.closing_balance

                all_extracted_rows.extend(page_data.transactions)

            except Exception as exc:
                # Log failed extraction run and mark statement failed
                run = ExtractionRun(
                    statement_id=statement.id,
                    stage="extract",
                    model=model_name,
                    prompt_version="1.0",
                    success=False,
                    error_message=str(exc),
                )
                db.add(run)
                statement.status = "failed"
                statement.error_message = f"LLM extraction error: {exc!s}"
                db.commit()
                return statement

        # Deduplicate overlapping transactions
        final_rows = self.deduplicate_transactions(all_extracted_rows)

        # Resolve default category 'Other'
        category_other = db.query(Category).filter(Category.name == "Other").first()
        category_id = category_other.id if category_other else 14

        # Atomic commit: insert all transactions and update statement
        try:
            created_txns: list[Transaction] = []
            for idx, row in enumerate(final_rows, start=1):
                txn_date = parse_date(row.date) or date.today()
                txn = Transaction(
                    statement_id=statement.id,
                    row_index=idx,
                    txn_date=txn_date,
                    description_raw=row.description,
                    amount=abs(row.amount),
                    direction=row.direction.lower(),
                    balance_after=row.balance,
                    category_id=category_id,
                    category_source="model",
                )
                db.add(txn)
                created_txns.append(txn)

            # Step 6: Compute reconciliation check
            from api.services.reconciliation_service import ReconciliationService

            reconcile_res = ReconciliationService.compute_reconciliation(
                opening_balance=opening_balance,
                closing_balance=closing_balance,
                transactions=created_txns,
            )

            statement.bank_name = bank_name
            statement.account_last4 = account_last4
            statement.period_start = period_start
            statement.period_end = period_end
            statement.opening_balance = opening_balance
            statement.closing_balance = closing_balance
            statement.status = "needs_review"
            statement.page_count = page_count
            statement.reconciliation_status = reconcile_res.status
            statement.reconciliation_diff = reconcile_res.diff

            run = ExtractionRun(
                statement_id=statement.id,
                stage="extract",
                model=model_name,
                prompt_version="1.0",
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                latency_ms=total_latency_ms,
                estimated_cost=total_cost,
                success=True,
            )
            db.add(run)
            db.commit()

            # Step 7: Batch Categorization
            from api.services.categorization_service import CategorizationService

            CategorizationService(llm_client=self.llm_client).categorize_statement(statement.id, db)

            db.refresh(statement)
            return statement

        except Exception as exc:
            db.rollback()
            statement.status = "failed"
            statement.error_message = f"Failed saving transactions: {exc!s}"
            db.commit()
            raise
