"""Reconciliation service for verifying statement balance integrity."""
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from api.db.models import Statement, Transaction


class ReconciliationResult:
    def __init__(
        self,
        status: str,
        diff: Decimal | None = None,
        opening_balance: Decimal | None = None,
        closing_balance: Decimal | None = None,
        total_credits: Decimal = Decimal("0.00"),
        total_debits: Decimal = Decimal("0.00"),
        computed_balance: Decimal | None = None,
    ):
        self.status = status
        self.diff = diff
        self.opening_balance = opening_balance
        self.closing_balance = closing_balance
        self.total_credits = total_credits
        self.total_debits = total_debits
        self.computed_balance = computed_balance


class ReconciliationService:
    @staticmethod
    def compute_reconciliation(
        opening_balance: Decimal | None,
        closing_balance: Decimal | None,
        transactions: list[Transaction],
    ) -> ReconciliationResult:
        """Calculate balance reconciliation according to PRD Feature F3."""
        total_credits = Decimal("0.00")
        total_debits = Decimal("0.00")

        for txn in transactions:
            if txn.direction.lower() == "credit":
                total_credits += txn.amount
            elif txn.direction.lower() == "debit":
                total_debits += txn.amount

        # Rule: Missing opening or closing balance -> 'not_available', never 'passed'
        if opening_balance is None or closing_balance is None:
            return ReconciliationResult(
                status="not_available",
                diff=None,
                opening_balance=opening_balance,
                closing_balance=closing_balance,
                total_credits=total_credits,
                total_debits=total_debits,
                computed_balance=None,
            )

        computed_balance = opening_balance + total_credits - total_debits
        diff = closing_balance - computed_balance

        # Allow 1 cent/paisa rounding margin
        if abs(diff) < Decimal("0.01"):
            return ReconciliationResult(
                status="passed",
                diff=Decimal("0.00"),
                opening_balance=opening_balance,
                closing_balance=closing_balance,
                total_credits=total_credits,
                total_debits=total_debits,
                computed_balance=computed_balance,
            )
        else:
            return ReconciliationResult(
                status="failed",
                diff=diff,
                opening_balance=opening_balance,
                closing_balance=closing_balance,
                total_credits=total_credits,
                total_debits=total_debits,
                computed_balance=computed_balance,
            )

    def reconcile_statement(
        self,
        statement_id: uuid.UUID,
        db: Session,
    ) -> Statement:
        """Run reconciliation check on a stored statement and persist results."""
        statement = db.get(Statement, statement_id)
        if not statement:
            raise ValueError(f"Statement {statement_id} not found.")

        transactions = (
            db.query(Transaction)
            .filter(Transaction.statement_id == statement_id)
            .all()
        )

        res = self.compute_reconciliation(
            opening_balance=statement.opening_balance,
            closing_balance=statement.closing_balance,
            transactions=transactions,
        )

        statement.reconciliation_status = res.status
        statement.reconciliation_diff = res.diff
        db.commit()
        db.refresh(statement)
        return statement
