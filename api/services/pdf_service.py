"""PDF intake, validation, storage, and text extraction services."""
import uuid
from pathlib import Path

import pdfplumber
from fastapi import HTTPException, status

from api.config import settings

SCANNED_ERROR_MESSAGE = "Scanned statements are not supported in version one."
MAX_PAGES = 30


class PDFValidationError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


def validate_pdf_content(file_bytes: bytes, filename: str) -> None:
    """Validate file content type and size before storing."""
    # Size check
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise PDFValidationError(f"File exceeds maximum size of {settings.max_upload_mb} MB.")

    # Content type / magic byte check
    if not file_bytes.startswith(b"%PDF-"):
        raise PDFValidationError("Only PDF files are supported.")


def save_pdf(statement_id: uuid.UUID, file_bytes: bytes) -> Path:
    """Store the uploaded PDF under a generated UUID file path."""
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / f"{statement_id}.pdf"
    destination.write_bytes(file_bytes)
    return destination


def extract_text_per_page(file_path: Path) -> tuple[int, list[str]]:
    """Extract text per page and detect scanned PDFs with no extractable text.

    Returns:
        tuple[int, list[str]]: (page_count, list of page text strings)

    Raises:
        PDFValidationError: If page count exceeds MAX_PAGES or if statement is scanned.
    """
    try:
        with pdfplumber.open(file_path) as pdf:
            page_count = len(pdf.pages)
            if page_count > MAX_PAGES:
                raise PDFValidationError(f"Statement exceeds maximum limit of {MAX_PAGES} pages.")

            pages_text: list[str] = []
            total_text_length = 0

            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)
                total_text_length += len(text.strip())

            # Detect statements with no extractable text (e.g. scanned images)
            if total_text_length < 20:
                raise PDFValidationError(SCANNED_ERROR_MESSAGE)

            return page_count, pages_text

    except PDFValidationError:
        raise
    except Exception as exc:
        raise PDFValidationError(f"Failed to process PDF: {exc!s}") from exc
