"""Ask Your Statements chat screen adhering to Document 03 and Document 04."""
import uuid
from typing import Any

import streamlit as st

from ui.api_client import client


def render_ask_view() -> None:
    st.markdown('<div class="page-title">Ask Your Statements</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="text-muted">Ask questions about your transactions, categories, and spending habits in plain English.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<br/>", unsafe_allow_html=True)

    # 1. Initialize session ID and message history in session state
    if "chat_session_id" not in st.session_state:
        st.session_state["chat_session_id"] = str(uuid.uuid4())

    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []

    session_id = st.session_state["chat_session_id"]
    messages: list[dict[str, Any]] = st.session_state["chat_messages"]

    # 2. Empty State with Suggested Questions
    if not messages:
        st.markdown(
            """
            <div class="surface-card" style="text-align:left; margin-bottom: 24px;">
                <div style="font-weight: 600; font-size: 16px; margin-bottom: 8px;">Try asking:</div>
                <div class="text-muted" style="margin-bottom: 16px;">
                    Select an example prompt below or type your own question to query your bank statements without writing complex formulas.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        ex_col1, ex_col2, ex_col3 = st.columns(3)
        with ex_col1:
            if st.button("🍽️ How much did I spend on Food and Dining?", use_container_width=True):
                st.session_state["pending_chat_prompt"] = "How much did I spend on Food and Dining?"
                st.rerun()
        with ex_col2:
            if st.button("💳 What were my top 5 largest expenses?", use_container_width=True):
                st.session_state["pending_chat_prompt"] = "What were my top 5 largest expenses?"
                st.rerun()
        with ex_col3:
            if st.button("💰 How much total income was credited?", use_container_width=True):
                st.session_state["pending_chat_prompt"] = "How much total income was credited?"
                st.rerun()

    # 3. Render Message History
    for msg in messages:
        role = msg.get("role", "assistant")
        content = msg.get("content", "")
        filters = msg.get("filters_used")

        with st.chat_message(role):
            st.markdown(content)
            if role == "assistant" and filters:
                filter_items = [f"**{k}:** {v}" for k, v in filters.items()]
                if filter_items:
                    filter_str = " &nbsp;|&nbsp; ".join(filter_items)
                    st.markdown(
                        f"""
                        <div style="font-size: 12px; color: #5F6B76; background-color: #F0EFEA; border: 1px solid #E1DED6; padding: 4px 10px; border-radius: 6px; display: inline-block; margin-top: 8px;">
                            Filters applied: {filter_str}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # 4. Handle Pending Chat Prompt or New Chat Input
    prompt_to_send = None

    if "pending_chat_prompt" in st.session_state:
        prompt_to_send = st.session_state.pop("pending_chat_prompt")
    else:
        user_input = st.chat_input("Ask a question about your spending (e.g., 'How much did I spend on groceries?')...")
        if user_input:
            prompt_to_send = user_input.strip()

    if prompt_to_send:
        # Display user message immediately
        st.session_state["chat_messages"].append({"role": "user", "content": prompt_to_send})
        with st.chat_message("user"):
            st.markdown(prompt_to_send)

        # Call backend
        with st.chat_message("assistant"):
            with st.spinner("Analyzing statements..."):
                try:
                    response = client.send_chat_message(message=prompt_to_send, session_id=session_id)
                    answer = response.get("answer", "Here is what I found.")
                    filters_used = response.get("filters_used", {})

                    st.markdown(answer)
                    if filters_used:
                        filter_items = [f"**{k}:** {v}" for k, v in filters_used.items()]
                        if filter_items:
                            filter_str = " &nbsp;|&nbsp; ".join(filter_items)
                            st.markdown(
                                f"""
                                <div style="font-size: 12px; color: #5F6B76; background-color: #F0EFEA; border: 1px solid #E1DED6; padding: 4px 10px; border-radius: 6px; display: inline-block; margin-top: 8px;">
                                    Filters applied: {filter_str}
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                    st.session_state["chat_messages"].append({
                        "role": "assistant",
                        "content": answer,
                        "filters_used": filters_used,
                    })

                except Exception as exc:
                    err_msg = f"Sorry, I encountered an error answering your question: {exc!s}"
                    st.error(err_msg)
                    st.session_state["chat_messages"].append({
                        "role": "assistant",
                        "content": err_msg,
                        "filters_used": {"Status": "Error"},
                    })

        st.rerun()
