"""Statements list view adhering to Document 03 and Document 04."""
import streamlit as st

from ui.api_client import client
from ui.formatting import render_reconciliation_badge, render_status_badge


def render_statements_view() -> None:
    st.markdown('<div class="page-title">Statements</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="text-muted">Manage all uploaded bank statements, verification status, and reconciliation badges.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<br/>", unsafe_allow_html=True)

    try:
        statements = client.list_statements()
    except Exception as exc:
        st.error(f"Could not load statements: {exc!s}")
        if st.button("Retry"):
            st.rerun()
        return

    if not statements:
        st.info("No statements yet. Upload your first bank statement to get started!")
        if st.button("Go to Upload Page", type="primary"):
            st.session_state["nav_page"] = "Upload"
            st.rerun()
        return

    # Table of statements
    for stmt in statements:
        stmt_id = stmt["id"]
        bank = stmt.get("bank_name") or "Unknown Bank"
        filename = stmt.get("filename") or "statement.pdf"
        p_start = stmt.get("period_start") or "-"
        p_end = stmt.get("period_end") or "-"
        status_val = stmt.get("status", "processing")
        reconcile_status = stmt.get("reconciliation_status", "not_available")
        diff = stmt.get("reconciliation_diff")

        status_html = render_status_badge(status_val)
        reconcile_html = render_reconciliation_badge(reconcile_status, diff)

        with st.container():
            col1, col2, col3, col4, col5 = st.columns([2.5, 3, 2.5, 1.2, 1.2])

            with col1:
                st.markdown(f"**{bank}**<br/><span class='text-muted'>{filename}</span>", unsafe_allow_html=True)

            with col2:
                st.markdown(f"{status_html} &nbsp; {reconcile_html}", unsafe_allow_html=True)

            with col3:
                st.markdown(f"Period: **{p_start}** to **{p_end}**", unsafe_allow_html=True)

            with col4:
                if status_val == "failed":
                    if st.button("Retry", key=f"retry_{stmt_id}", help="Retry processing"):
                        try:
                            client.retry_statement(stmt_id)
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                else:
                    if st.button("Review", key=f"review_{stmt_id}", type="primary"):
                        st.session_state["selected_statement_id"] = stmt_id
                        st.session_state["nav_page"] = "Review"
                        st.rerun()

            with col5:
                # Delete with confirmation in session state
                if st.button("Delete", key=f"del_{stmt_id}"):
                    st.session_state[f"confirm_delete_{stmt_id}"] = True

            # If delete was clicked, show confirmation banner
            if st.session_state.get(f"confirm_delete_{stmt_id}", False):
                with st.chat_message("assistant"):
                    st.warning(f"Are you sure you want to permanently delete **{filename}** and all its transactions?")
                    cd1, cd2 = st.columns([1, 4])
                    with cd1:
                        if st.button("Yes, Delete", key=f"confirm_yes_{stmt_id}", type="primary"):
                            client.delete_statement(stmt_id)
                            st.session_state.pop(f"confirm_delete_{stmt_id}", None)
                            st.rerun()
                    with cd2:
                        if st.button("Cancel", key=f"confirm_no_{stmt_id}"):
                            st.session_state.pop(f"confirm_delete_{stmt_id}", None)
                            st.rerun()

            st.divider()
