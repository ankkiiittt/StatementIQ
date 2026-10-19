"""Batch categorization service using LLM with user edit protection."""
import json
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from api.db.models import Category, ExtractionRun, Statement, Transaction
from api.schemas import BatchCategorizationResult
from api.services.llm.client import LLMClient
from api.services.llm.factory import get_llm_client
from api.services.llm.prompts import CATEGORIZATION_PROMPT_V1

BATCH_SIZE = 50


class CategorizationService:
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client or get_llm_client()

    def categorize_statement(
        self,
        statement_id: uuid.UUID,
        db: Session,
    ) -> Statement:
        """Categorize statement transactions in batches of up to 50, protecting user-set categories."""
        statement = db.get(Statement, statement_id)
        if not statement:
            raise ValueError(f"Statement {statement_id} not found.")

        # Load all transactions for statement
        transactions = (
            db.query(Transaction)
            .filter(Transaction.statement_id == statement_id)
            .order_by(Transaction.row_index)
            .all()
        )

        # Filter out user-edited transactions: preserve user-set categories
        candidate_txns = [t for t in transactions if t.category_source != "user"]
        if not candidate_txns:
            return statement

        # Load categories map: name -> Category
        categories = db.query(Category).all()
        if not categories:
            from api.db.seed import seed_categories

            categories = seed_categories(db)

        cat_by_name = {c.name.lower(): c for c in categories}
        category_other = cat_by_name.get("other") or categories[0]

        total_input_tokens = 0
        total_output_tokens = 0
        total_latency_ms = 0
        total_cost = Decimal("0.0000")
        model_name = "unknown"

        # Process in batches of up to 50
        for i in range(0, len(candidate_txns), BATCH_SIZE):
            batch = candidate_txns[i : i + BATCH_SIZE]
            batch_data = [
                {
                    "row_index": t.row_index,
                    "description": t.description_clean or t.description_raw,
                    "amount": float(t.amount),
                    "direction": t.direction,
                }
                for t in batch
            ]

            prompt = CATEGORIZATION_PROMPT_V1.replace(
                "{transactions_json}",
                json.dumps(batch_data, indent=2),
            )

            try:
                cat_result, llm_res = self.llm_client.generate_json(
                    prompt=prompt,
                    pydantic_schema=BatchCategorizationResult,
                    prompt_version="1.0",
                )
                total_input_tokens += llm_res.input_tokens
                total_output_tokens += llm_res.output_tokens
                total_latency_ms += llm_res.latency_ms
                total_cost += llm_res.estimated_cost
                model_name = llm_res.model_name

                # Build row_index -> assignment map
                assignments = {a.row_index: a for a in cat_result.categories}

                for txn in batch:
                    assignment = assignments.get(txn.row_index)
                    if assignment and assignment.category:
                        matched = cat_by_name.get(assignment.category.strip().lower())
                        txn.category_id = matched.id if matched else category_other.id
                        txn.confidence = assignment.confidence or Decimal("0.85")
                    else:
                        txn.category_id = category_other.id
                        txn.confidence = Decimal("0.50")
                    txn.category_source = "model"

            except Exception as exc:
                # Log failed run
                run = ExtractionRun(
                    statement_id=statement.id,
                    stage="categorize",
                    model=model_name,
                    prompt_version="1.0",
                    success=False,
                    error_message=str(exc),
                )
                db.add(run)
                db.commit()
                raise

        # Record successful categorization run
        run = ExtractionRun(
            statement_id=statement.id,
            stage="categorize",
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
        db.refresh(statement)
        return statement
