"""API client for communicating with the FastAPI backend."""
import os
import uuid
from datetime import date
from typing import Any

import requests

from api.config import settings

API_URL = os.getenv("API_URL", settings.api_url)


class APIClient:
    def __init__(self, base_url: str = API_URL):
        self.base_url = base_url.rstrip("/")

    def health(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/health", timeout=3)
            return r.status_code == 200 and r.json().get("status") == "ok"
        except Exception:
            return False

    def get_categories(self) -> list[dict[str, Any]]:
        try:
            r = requests.get(f"{self.base_url}/categories", timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception:
            return []

    def list_statements(self) -> list[dict[str, Any]]:
        try:
            r = requests.get(f"{self.base_url}/statements", timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            raise RuntimeError(f"Could not load statements: {exc!s}") from exc

    def get_statement(self, statement_id: uuid.UUID | str) -> dict[str, Any] | None:
        try:
            r = requests.get(f"{self.base_url}/statements/{statement_id}", timeout=5)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch statement {statement_id}: {exc!s}") from exc

    def upload_statement(self, filename: str, content: bytes) -> dict[str, Any]:
        files = {"file": (filename, content, "application/pdf")}
        r = requests.post(f"{self.base_url}/statements", files=files, timeout=60)
        if not r.ok:
            error_detail = "Failed to upload statement."
            try:
                error_detail = r.json().get("detail", error_detail)
            except Exception:
                pass
            raise RuntimeError(error_detail)
        return r.json()

    def get_transactions(
        self,
        statement_id: uuid.UUID | str,
        page: int = 1,
        page_size: int = 50,
        direction: str | None = None,
        category_id: int | None = None,
        search: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
        }
        if direction:
            params["direction"] = direction
        if category_id is not None:
            params["category_id"] = category_id
        if search:
            params["search"] = search
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()

        r = requests.get(f"{self.base_url}/statements/{statement_id}/transactions", params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def update_transaction(
        self,
        transaction_id: uuid.UUID | str,
        category_id: int | None = None,
        description_clean: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if category_id is not None:
            payload["category_id"] = category_id
        if description_clean is not None:
            payload["description_clean"] = description_clean

        r = requests.patch(f"{self.base_url}/transactions/{transaction_id}", json=payload, timeout=5)
        r.raise_for_status()
        return r.json()

    def delete_transaction(self, transaction_id: uuid.UUID | str) -> bool:
        r = requests.delete(f"{self.base_url}/transactions/{transaction_id}", timeout=5)
        r.raise_for_status()
        return r.json().get("deleted", False)

    def confirm_statement(self, statement_id: uuid.UUID | str) -> dict[str, Any]:
        r = requests.post(f"{self.base_url}/statements/{statement_id}/confirm", timeout=5)
        r.raise_for_status()
        return r.json()

    def retry_statement(self, statement_id: uuid.UUID | str) -> dict[str, Any]:
        r = requests.post(f"{self.base_url}/statements/{statement_id}/retry", timeout=60)
        r.raise_for_status()
        return r.json()

    def delete_statement(self, statement_id: uuid.UUID | str) -> bool:
        r = requests.delete(f"{self.base_url}/statements/{statement_id}", timeout=10)
        r.raise_for_status()
        return r.json().get("deleted", False)

    def get_insights(
        self,
        statement_id: uuid.UUID | str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if statement_id:
            params["statement_id"] = str(statement_id)
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()

        r = requests.get(f"{self.base_url}/insights", params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def send_chat_message(
        self,
        message: str,
        session_id: uuid.UUID | str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"message": message}
        if session_id:
            payload["session_id"] = str(session_id)
        r = requests.post(f"{self.base_url}/chat", json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    def get_chat_history(self, session_id: uuid.UUID | str) -> list[dict[str, Any]]:
        r = requests.get(f"{self.base_url}/chat/{session_id}", timeout=10)
        r.raise_for_status()
        return r.json()


client = APIClient()
