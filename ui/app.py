"""StatementIQ Streamlit UI Application."""
import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import streamlit as st

from ui.api_client import client
from ui.backend_runner import ensure_backend_alive
from ui.styles import apply_custom_styles
from ui.views.ask_view import render_ask_view
from ui.views.insights_view import render_insights_view
from ui.views.review_view import render_review_view
from ui.views.statements_view import render_statements_view
from ui.views.upload_view import render_upload_view

st.set_page_config(
    page_title="StatementIQ",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply Document 04 design tokens and styles
apply_custom_styles()

# Query params routing
query_page = st.query_params.get("page")
query_id = st.query_params.get("id")

if query_page == "review" and query_id:
    st.session_state["nav_page"] = "Review"
    st.session_state["selected_statement_id"] = query_id

if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = "Upload"

# Sidebar Navigation
st.sidebar.markdown(
    """
    <div style="margin-bottom: 16px;">
        <span style="font-size: 22px; font-weight: 700; color: #0F5C4D;">StatementIQ</span><br/>
        <span style="font-size: 13px; color: #5F6B76;">Bank Statement Analyzer</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# Determine sidebar selection
nav_options = ["Upload", "Statements", "Insights", "Ask"]
current_nav = st.session_state.get("nav_page", "Upload")
sidebar_selected_nav = "Statements" if current_nav == "Review" else current_nav
default_idx = nav_options.index(sidebar_selected_nav) if sidebar_selected_nav in nav_options else 0

selected_page = st.sidebar.radio(
    "Navigation",
    nav_options,
    index=default_idx,
    label_visibility="collapsed",
)

# If user clicked on a different sidebar item, switch view
if selected_page != sidebar_selected_nav:
    st.session_state["nav_page"] = selected_page
    st.rerun()

# Backend connectivity check (auto-launches for Streamlit Cloud standalone deployment if down)
ensure_backend_alive()
is_healthy = client.health()
st.sidebar.divider()
if is_healthy:
    st.sidebar.markdown(
        '<span class="status-badge badge-passed" style="font-size:12px;">● Backend Connected</span>',
        unsafe_allow_html=True,
    )
else:
    st.sidebar.markdown(
        '<span class="status-badge badge-failed" style="font-size:12px;">○ Backend Disconnected</span>',
        unsafe_allow_html=True,
    )

# Page Rendering
active_page = st.session_state.get("nav_page", "Upload")

if active_page == "Upload":
    render_upload_view()
elif active_page == "Statements":
    render_statements_view()
elif active_page == "Review":
    render_review_view()
elif active_page == "Insights":
    render_insights_view()
elif active_page == "Ask":
    render_ask_view()
