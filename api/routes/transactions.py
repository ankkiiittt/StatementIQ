"""Transaction routes: edit category, edit cleaned description, and delete row."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.db.models import Category, Transaction
from api.db.session import get_db
from api.schemas import TransactionResponse, TransactionUpdateRequest
from api.services.reconciliation_service import ReconciliationService

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.patch(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Edit category or cleaned description for a transaction",
)
def update_transaction(
    transaction_id: uuid.UUID,
    payload: TransactionUpdateRequest,
    db: Session = Depends(get_db),
) -> TransactionResponse:
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found.",
        )

    if payload.category_id is not None:
        cat = db.get(Category, payload.category_id)
        if not cat:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category {payload.category_id} does not exist.",
            )
        txn.category_id = payload.category_id
        txn.category_source = "user"  # Explicitly marked as user-set per PRD F4

    if payload.description_clean is not None:
        txn.description_clean = payload.description_clean.strip()

    db.commit()
    db.refresh(txn)

    return TransactionResponse(
        id=txn.id,
        statement_id=txn.statement_id,
        row_index=txn.row_index,
        txn_date=txn.txn_date,
        description_raw=txn.description_raw,
        description_clean=txn.description_clean,
        amount=txn.amount,
        direction=txn.direction,
        balance_after=txn.balance_after,
        category_id=txn.category_id,
        category_name=txn.category.name if txn.category else "Other",
        category_source=txn.category_source,
        confidence=txn.confidence,
        created_at=txn.created_at,
        updated_at=txn.updated_at,
    )


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a transaction row",
)
def delete_transaction(
    transaction_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict[str, str | bool]:
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found.",
        )

    statement_id = txn.statement_id
    db.delete(txn)
    db.commit()

    # Re-run reconciliation on parent statement
    ReconciliationService().reconcile_statement(statement_id, db)

    return {"deleted": True, "transaction_id": str(transaction_id)}
