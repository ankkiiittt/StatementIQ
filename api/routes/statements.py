"""Statement routes: upload, list, details, transactions, confirm, retry, and delete."""
import math
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from api.db.models import Category, Statement, Transaction
from api.db.session import get_db
from api.schemas import (
    PaginatedTransactionsResponse,
    StatementResponse,
    StatementUploadResponse,
    TransactionResponse,
)
from api.services.extraction_service import ExtractionService
from api.services.pdf_service import (
    SCANNED_ERROR_MESSAGE,
    PDFValidationError,
    extract_text_per_page,
    save_pdf,
    validate_pdf_content,
)

router = APIRouter(prefix="/statements", tags=["Statements"])


@router.get(
    "",
    response_model=list[StatementResponse],
    summary="List all statements with status and reconciliation result",
)
def list_statements(
    db: Session = Depends(get_db),
) -> list[Statement]:
    return db.query(Statement).order_by(Statement.created_at.desc()).all()


@router.post(
    "",
    response_model=StatementUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a bank statement PDF and start processing",
)
async def upload_statement(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> StatementUploadResponse:
    filename = file.filename or "statement.pdf"
    content = await file.read()

    # Validate file type and size
    validate_pdf_content(content, filename)

    statement_id = uuid.uuid4()
    saved_path: Path | None = None

    try:
        saved_path = save_pdf(statement_id, content)
        page_count, _ = extract_text_per_page(saved_path)

        statement = Statement(
            id=statement_id,
            filename=filename,
            file_path=str(saved_path),
            page_count=page_count,
            status="processing",
            reconciliation_status="not_available",
        )
        db.add(statement)
        db.commit()
        db.refresh(statement)

        # Run extraction, reconciliation, and categorization pipeline
        statement = ExtractionService().process_statement(statement.id, db)

        return StatementUploadResponse(
            statement_id=statement.id,
            filename=statement.filename,
            status=statement.status,
            page_count=statement.page_count,
            message="Statement uploaded and processed successfully.",
        )

    except PDFValidationError as exc:
        if exc.detail == SCANNED_ERROR_MESSAGE:
            statement = Statement(
                id=statement_id,
                filename=filename,
                file_path=str(saved_path) if saved_path else "",
                status="failed",
                error_message=SCANNED_ERROR_MESSAGE,
                reconciliation_status="not_available",
            )
            db.add(statement)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=SCANNED_ERROR_MESSAGE,
            ) from exc

        if saved_path and saved_path.exists():
            saved_path.unlink(missing_ok=True)
        raise exc


@router.get(
    "/{statement_id}",
    response_model=StatementResponse,
    summary="Get statement details and processing status",
)
def get_statement(
    statement_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Statement:
    statement = db.get(Statement, statement_id)
    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Statement {statement_id} not found.",
        )
    return statement


@router.get(
    "/{statement_id}/transactions",
    response_model=PaginatedTransactionsResponse,
    summary="Get transactions for a statement with filters and pagination",
)
def get_statement_transactions(
    statement_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    direction: str | None = Query(None, pattern="^(debit|credit)$"),
    category_id: int | None = None,
    search: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
) -> PaginatedTransactionsResponse:
    statement = db.get(Statement, statement_id)
    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Statement {statement_id} not found.",
        )

    query = (
        db.query(Transaction)
        .filter(Transaction.statement_id == statement_id)
        .join(Category, Transaction.category_id == Category.id)
    )

    if direction:
        query = query.filter(Transaction.direction == direction.lower())
    if category_id is not None:
        query = query.filter(Transaction.category_id == category_id)
    if start_date:
        query = query.filter(Transaction.txn_date >= start_date)
    if end_date:
        query = query.filter(Transaction.txn_date <= end_date)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            (Transaction.description_raw.ilike(term)) | (Transaction.description_clean.ilike(term))
        )

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    txns = (
        query.order_by(Transaction.row_index.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        TransactionResponse(
            id=t.id,
            statement_id=t.statement_id,
            row_index=t.row_index,
            txn_date=t.txn_date,
            description_raw=t.description_raw,
            description_clean=t.description_clean,
            amount=t.amount,
            direction=t.direction,
            balance_after=t.balance_after,
            category_id=t.category_id,
            category_name=t.category.name if t.category else "Other",
            category_source=t.category_source,
            confidence=t.confidence,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in txns
    ]

    return PaginatedTransactionsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/{statement_id}/confirm",
    response_model=StatementResponse,
    summary="Mark a statement as confirmed",
)
def confirm_statement(
    statement_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Statement:
    statement = db.get(Statement, statement_id)
    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Statement {statement_id} not found.",
        )

    statement.status = "confirmed"
    db.commit()
    db.refresh(statement)
    return statement


@router.post(
    "/{statement_id}/retry",
    response_model=StatementResponse,
    summary="Re-run processing for a failed statement",
)
def retry_statement(
    statement_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Statement:
    statement = db.get(Statement, statement_id)
    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Statement {statement_id} not found.",
        )

    # Clean up previous transactions and extraction runs
    db.query(Transaction).filter(Transaction.statement_id == statement_id).delete()
    statement.status = "processing"
    statement.error_message = None
    db.commit()

    # Re-run extraction pipeline
    statement = ExtractionService().process_statement(statement_id, db)
    return statement


@router.delete(
    "/{statement_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete the statement, rows and stored PDF",
)
def delete_statement(
    statement_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict[str, str | bool]:
    statement = db.get(Statement, statement_id)
    if not statement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Statement {statement_id} not found.",
        )

    # Delete physical file from disk if present
    file_path = Path(statement.file_path) if statement.file_path else None
    if file_path and file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            pass

    # Delete statement (cascades to transactions and extraction_runs)
    db.delete(statement)
    db.commit()

    return {"deleted": True, "statement_id": str(statement_id)}
