"""API client for communicating with the FastAPI backend.

Supports both external HTTP backend communication and zero-config in-process
execution for standalone environments like Streamlit Community Cloud.
"""
import os
import uuid
from datetime import date
from typing import Any

import requests

from api.config import settings

# Force 127.0.0.1 instead of localhost to prevent Linux IPv6 ::1 resolution errors
RAW_API_URL = os.getenv("API_URL", settings.api_url)
if "localhost" in RAW_API_URL:
    RAW_API_URL = RAW_API_URL.replace("localhost", "127.0.0.1")

API_URL = RAW_API_URL


class UnifiedResponse:
    """Wrapper that unifies requests.Response and httpx.Response interface."""

    def __init__(self, raw):
        self._raw = raw
        self.status_code = raw.status_code

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    def json(self) -> Any:
        return self._raw.json()

    def raise_for_status(self):
        self._raw.raise_for_status()

    @property
    def text(self) -> str:
        return self._raw.text


class APIClient:
    def __init__(self, base_url: str = API_URL):
        self._base_url = base_url.rstrip("/")
        self._in_process_client = None

    @property
    def base_url(self) -> str:
        url = os.getenv("API_URL", self._base_url)
        if "localhost" in url:
            url = url.replace("localhost", "127.0.0.1")
        return url.rstrip("/")

    def _get_direct_client(self):
        if self._in_process_client is None:
            try:
                from fastapi.testclient import TestClient

                from api.db.session import init_db
                from api.main import app

                init_db()
                self._in_process_client = TestClient(app)
            except Exception as exc:
                print(f"[StatementIQ] Direct in-process client init error: {exc}")
                return None
        return self._in_process_client

    def _request(self, method: str, path: str, **kwargs) -> UnifiedResponse:
        endpoint = path if path.startswith("/") else f"/{path}"
        url = f"{self.base_url}{endpoint}"

        # If base_url points to localhost / 127.0.0.1, try HTTP with immediate in-process fallback
        is_local = "127.0.0.1" in self.base_url or "localhost" in self.base_url

        try:
            timeout = kwargs.pop("timeout", 10)
            res = requests.request(method, url, timeout=timeout, **kwargs)
            return UnifiedResponse(res)
        except Exception as exc:
            # Fall back to in-process execution on connection failure for standalone deployments
            if is_local:
                direct = self._get_direct_client()
                if direct is not None:
                    direct_res = direct.request(method, endpoint, **kwargs)
                    return UnifiedResponse(direct_res)
            raise exc

    def health(self) -> bool:
        try:
            r = self._request("GET", "/health", timeout=2)
            return r.status_code == 200 and r.json().get("status") == "ok"
        except Exception:
            return False

    def get_categories(self) -> list[dict[str, Any]]:
        try:
            r = self._request("GET", "/categories", timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception:
            return []

    def list_statements(self) -> list[dict[str, Any]]:
        try:
            r = self._request("GET", "/statements", timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            raise RuntimeError(f"Could not load statements: {exc!s}") from exc

    def get_statement(self, statement_id: uuid.UUID | str) -> dict[str, Any] | None:
        try:
            r = self._request("GET", f"/statements/{statement_id}", timeout=5)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch statement {statement_id}: {exc!s}") from exc

    def upload_statement(self, filename: str, content: bytes) -> dict[str, Any]:
        files = {"file": (filename, content, "application/pdf")}
        r = self._request("POST", "/statements", files=files, timeout=60)
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

        r = self._request("GET", f"/statements/{statement_id}/transactions", params=params, timeout=10)
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

        r = self._request("PATCH", f"/transactions/{transaction_id}", json=payload, timeout=5)
        r.raise_for_status()
        return r.json()

    def delete_transaction(self, transaction_id: uuid.UUID | str) -> bool:
        r = self._request("DELETE", f"/transactions/{transaction_id}", timeout=5)
        r.raise_for_status()
        return r.json().get("deleted", False)

    def confirm_statement(self, statement_id: uuid.UUID | str) -> dict[str, Any]:
        r = self._request("POST", f"/statements/{statement_id}/confirm", timeout=5)
        r.raise_for_status()
        return r.json()

    def retry_statement(self, statement_id: uuid.UUID | str) -> dict[str, Any]:
        r = self._request("POST", f"/statements/{statement_id}/retry", timeout=60)
        r.raise_for_status()
        return r.json()

    def delete_statement(self, statement_id: uuid.UUID | str) -> bool:
        r = self._request("DELETE", f"/statements/{statement_id}", timeout=10)
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

        r = self._request("GET", "/insights", params=params, timeout=10)
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
        r = self._request("POST", "/chat", json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    def get_chat_history(self, session_id: uuid.UUID | str) -> list[dict[str, Any]]:
        r = self._request("GET", f"/chat/{session_id}", timeout=10)
        r.raise_for_status()
        return r.json()


client = APIClient()
