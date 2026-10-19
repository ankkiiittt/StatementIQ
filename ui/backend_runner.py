"""Helper to ensure FastAPI backend is running for standalone/cloud deployments (e.g. Streamlit Cloud)."""
import atexit
import os
import subprocess
import sys
import time
from urllib.parse import urlparse

import requests

from api.config import settings

_backend_process: subprocess.Popen | None = None


def is_backend_healthy(base_url: str) -> bool:
    try:
        r = requests.get(f"{base_url.rstrip('/')}/health", timeout=2)
        return r.status_code == 200 and r.json().get("status") == "ok"
    except Exception:
        return False


def ensure_backend_alive(api_url: str | None = None) -> bool:
    """Check if the FastAPI backend is running; if not and host is localhost, launch it."""
    global _backend_process

    # Sync secrets if running inside Streamlit
    try:
        import streamlit as st

        if hasattr(st, "secrets"):
            for k, v in st.secrets.items():
                if isinstance(v, (str, int, float, bool)) and k not in os.environ:
                    os.environ[k] = str(v)
    except Exception:
        pass

    base_url = api_url or os.getenv("API_URL", settings.api_url)

    if is_backend_healthy(base_url):
        return True

    # Parse port from API URL
    parsed = urlparse(base_url)
    port = parsed.port or 8001
    host = parsed.hostname or "127.0.0.1"

    # Only attempt to auto-start if target is localhost / 127.0.0.1
    if host not in ("127.0.0.1", "localhost", "0.0.0.0"):
        return False

    # Initialize DB and seed categories if needed
    try:
        from api.db.seed import seed_categories
        from api.db.session import init_db, session_factory

        init_db()
        db = session_factory()
        seed_categories(db)
        db.close()
    except Exception as exc:
        print(f"[StatementIQ] DB init info: {exc}")

    # If backend process was already launched and is running, just wait for it
    if _backend_process is not None and _backend_process.poll() is None:
        for _ in range(20):
            time.sleep(0.5)
            if is_backend_healthy(base_url):
                return True
        return False

    # Launch uvicorn as a background process
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        host,
        "--port",
        str(port),
        "--log-level",
        "info",
    ]

    try:
        from pathlib import Path

        log_dir = Path("uploads")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = open(log_dir / "backend.log", "a", encoding="utf-8")

        _backend_process = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=log_file,
            env=os.environ.copy(),
        )
        atexit.register(cleanup_backend)

        # Wait up to 15 seconds for backend to become ready
        for _ in range(30):
            time.sleep(0.5)
            if is_backend_healthy(base_url):
                return True
            if _backend_process.poll() is not None:
                print(f"[StatementIQ] Backend exited prematurely with code {_backend_process.poll()}")
                break
    except Exception as exc:
        print(f"[StatementIQ] Failed to launch backend: {exc}")
        return False

    return is_backend_healthy(base_url)


def cleanup_backend():
    """Terminate the background backend process on exit."""
    global _backend_process
    if _backend_process and _backend_process.poll() is None:
        try:
            _backend_process.terminate()
            _backend_process.wait(timeout=2)
        except Exception:
            try:
                _backend_process.kill()
            except Exception:
                pass
