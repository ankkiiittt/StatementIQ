"""StatementIQ — Streamlit Community Cloud Root Entrypoint.

Delegates execution to ui/app.py while ensuring root directory is in sys.path.
"""
import os
import runpy
import sys
from pathlib import Path

# Ensure repository root is on sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Populate environment variables from Streamlit secrets if running in Streamlit Cloud
try:
    import streamlit as st

    if hasattr(st, "secrets"):
        for k, v in st.secrets.items():
            if isinstance(v, (str, int, float, bool)) and k not in os.environ:
                os.environ[k] = str(v)
except Exception:
    pass

# Execute the main Streamlit application
runpy.run_path(str(root_dir / "ui" / "app.py"), run_name="__main__")
