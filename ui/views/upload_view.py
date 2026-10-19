"""Upload screen adhering to Document 03 and Document 04."""
import time

import streamlit as st

from ui.api_client import client


def render_upload_view() -> None:
    st.markdown('<div class="page-title">Upload Bank Statement</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="text-muted">Upload a text-based bank statement PDF (English, INR, up to 10 MB, max 30 pages).</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<br/>", unsafe_allow_html=True)

    # File uploader dropzone
    uploaded_file = st.file_uploader(
        "Choose a bank statement PDF",
        type=["pdf"],
        help="Only text-based PDFs in English are supported. Scanned images are not supported in v1.",
        label_visibility="collapsed",
    )

    if uploaded_file is None:
        st.info("💡 Drop your PDF statement above to automatically extract, categorize, and verify transactions.")
        return

    # Trigger upload button
    col1, col2 = st.columns([1, 4])
    with col1:
        start_btn = st.button("Process Statement", type="primary", use_container_width=True)

    if start_btn:
        progress_placeholder = st.empty()
        file_bytes = uploaded_file.getvalue()
        filename = uploaded_file.name

        # Visual Stepper
        def update_stepper(active_step: int, done_steps: list[int]):
            steps = [
                (1, "Reading PDF and extracting layout"),
                (2, "Extracting structured transactions with AI"),
                (3, "Checking balance reconciliation"),
                (4, "Categorizing spending into 14 categories"),
            ]
            html = '<div class="stepper-container">'
            for step_num, step_name in steps:
                if step_num in done_steps:
                    cls = "step-item done"
                    dot = '<div class="step-dot done">✓</div>'
                elif step_num == active_step:
                    cls = "step-item active"
                    dot = f'<div class="step-dot active">{step_num}</div>'
                else:
                    cls = "step-item"
                    dot = f'<div class="step-dot">{step_num}</div>'
                html += f'<div class="{cls}">{dot}<span>{step_name}</span></div>'
            html += "</div>"
            progress_placeholder.markdown(html, unsafe_allow_html=True)

        update_stepper(1, [])
        time.sleep(0.3)

        try:
            update_stepper(2, [1])
            res = client.upload_statement(filename, file_bytes)
            update_stepper(4, [1, 2, 3, 4])

            statement_id = res["statement_id"]
            st.success("Statement processed successfully! All transactions extracted and reconciled.")

            if st.button("Review Transactions →", type="primary"):
                st.session_state["selected_statement_id"] = str(statement_id)
                st.session_state["nav_page"] = "Review"
                st.rerun()

        except Exception as exc:
            progress_placeholder.empty()
            error_msg = str(exc)
            st.error(f"**Upload Failed:** {error_msg}")
            st.button("Retry Upload", on_click=lambda: None)
