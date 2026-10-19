"""Review and edit transactions screen adhering to Document 03 and Document 04."""
import streamlit as st

from ui.api_client import client
from ui.formatting import format_inr, render_reconciliation_badge, render_status_badge


def render_review_view() -> None:
    statement_id = st.session_state.get("selected_statement_id")

    # Support deep linking via query params (?id=...)
    if not statement_id and "id" in st.query_params:
        statement_id = st.query_params["id"]

    if not statement_id:
        st.warning("No statement selected for review.")
        if st.button("← Back to Statements"):
            st.session_state["nav_page"] = "Statements"
            st.rerun()
        return

    try:
        statement = client.get_statement(statement_id)
    except Exception as exc:
        st.error(f"Error loading statement: {exc!s}")
        return

    if not statement:
        st.error(f"Statement {statement_id} not found.")
        if st.button("← Back to Statements"):
            st.session_state["nav_page"] = "Statements"
            st.rerun()
        return

    # Categories list
    categories = client.get_categories()
    cat_names = [c["name"] for c in categories]
    cat_id_to_name = {c["id"]: c["name"] for c in categories}
    cat_name_to_id = {c["name"]: c["id"] for c in categories}

    # Header Card
    bank = statement.get("bank_name") or "Statement Review"
    p_start = statement.get("period_start") or "-"
    p_end = statement.get("period_end") or "-"
    account = statement.get("account_last4") or "XXXX"
    opening = statement.get("opening_balance")
    closing = statement.get("closing_balance")
    status_val = statement.get("status", "processing")
    reconcile_status = statement.get("reconciliation_status", "not_available")
    diff = statement.get("reconciliation_diff")

    st.markdown(f'<div class="page-title">{bank} (A/C: *{account})</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="text-muted">Period: {p_start} to {p_end} | File: {statement.get("filename")}</div>', unsafe_allow_html=True)
    st.markdown("<br/>", unsafe_allow_html=True)

    # Top summary metrics and action bar
    top_col1, top_col2 = st.columns([3, 1.2])

    with top_col1:
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Opening Balance</div><div class="metric-value">{format_inr(opening)}</div></div>',
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Closing Balance</div><div class="metric-value">{format_inr(closing)}</div></div>',
                unsafe_allow_html=True,
            )
        with m3:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Status</div><div style="margin-top:6px;">{render_status_badge(status_val)}</div></div>',
                unsafe_allow_html=True,
            )
        with m4:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Reconciliation</div><div style="margin-top:6px;">{render_reconciliation_badge(reconcile_status, diff)}</div></div>',
                unsafe_allow_html=True,
            )

    with top_col2:
        if status_val == "confirmed":
            st.success("✓ Statement Confirmed")
        else:
            if st.button("Confirm Statement", type="primary", use_container_width=True):
                if reconcile_status == "failed":
                    st.session_state["show_confirm_warning"] = True
                else:
                    client.confirm_statement(statement_id)
                    st.toast("Statement marked as Confirmed!", icon="✅")
                    st.rerun()

    if st.session_state.get("show_confirm_warning", False):
        st.warning(
            f"⚠️ **Warning**: Balance reconciliation failed by **{format_inr(diff)}**. "
            "Are you sure you want to confirm this statement?"
        )
        cw1, cw2 = st.columns([1, 4])
        with cw1:
            if st.button("Confirm Anyway", type="primary"):
                client.confirm_statement(statement_id)
                st.session_state["show_confirm_warning"] = False
                st.toast("Statement confirmed despite reconciliation difference.", icon="⚠️")
                st.rerun()
        with cw2:
            if st.button("Keep Editing"):
                st.session_state["show_confirm_warning"] = False
                st.rerun()

    st.markdown("<br/>", unsafe_allow_html=True)

    # Filter row
    f_col1, f_col2, f_col3 = st.columns([2, 2, 4])
    with f_col1:
        direction_filter = st.selectbox("Direction", ["All", "Debit", "Credit"], index=0)
    with f_col2:
        category_filter = st.selectbox("Category", ["All Categories"] + cat_names, index=0)
    with f_col3:
        search_query = st.text_input("Search description", placeholder="e.g. Swiggy, Salary, Uber...")

    # Fetch transactions
    direction_param = direction_filter.lower() if direction_filter != "All" else None
    cat_param = cat_name_to_id.get(category_filter) if category_filter != "All Categories" else None

    tx_data = client.get_transactions(
        statement_id=statement_id,
        direction=direction_param,
        category_id=cat_param,
        search=search_query if search_query else None,
        page_size=100,
    )

    transactions = tx_data.get("items", [])
    total_txns = tx_data.get("total", 0)

    st.markdown(f"**Transactions ({total_txns})**")

    if not transactions:
        st.info("No transactions found matching the selected filters.")
        return

    # Transaction review rows with immediate inline editing
    st.markdown(
        """
        <div style="display:flex; font-weight:600; color:#5F6B76; font-size:13px; border-bottom:1px solid #E1DED6; padding-bottom:8px; margin-bottom:8px;">
            <div style="flex:1;">Date</div>
            <div style="flex:3;">Raw Description</div>
            <div style="flex:3;">Cleaned Description</div>
            <div style="flex:2.5;">Category</div>
            <div style="flex:1.5; text-align:right;">Amount</div>
            <div style="flex:1; text-align:center;">Type</div>
            <div style="flex:1; text-align:center;">Action</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for txn in transactions:
        t_id = txn["id"]
        t_date = txn["txn_date"]
        t_desc_raw = txn["description_raw"]
        t_desc_clean = txn.get("description_clean") or ""
        t_amount = txn["amount"]
        t_dir = txn["direction"]
        current_cat_id = txn["category_id"]
        current_cat_name = cat_id_to_name.get(current_cat_id, "Other")
        current_cat_idx = cat_names.index(current_cat_name) if current_cat_name in cat_names else 13

        c_date, c_raw, c_clean, c_cat, c_amt, c_dir, c_act = st.columns([1, 3, 3, 2.5, 1.5, 1, 1])

        with c_date:
            st.write(t_date)

        with c_raw:
            st.caption(t_desc_raw)

        with c_clean:
            new_clean = st.text_input(
                "Cleaned",
                value=t_desc_clean,
                key=f"clean_{t_id}",
                label_visibility="collapsed",
                placeholder="Edit description",
            )
            if new_clean != t_desc_clean:
                client.update_transaction(t_id, description_clean=new_clean)
                st.toast("Saved description!", icon="💾")

        with c_cat:
            new_cat_name = st.selectbox(
                "Category",
                cat_names,
                index=current_cat_idx,
                key=f"cat_{t_id}",
                label_visibility="collapsed",
            )
            if new_cat_name != current_cat_name:
                new_cat_id = cat_name_to_id[new_cat_name]
                client.update_transaction(t_id, category_id=new_cat_id)
                st.toast(f"Category updated to {new_cat_name} (saved as user-set)!", icon="💾")
                st.rerun()

        with c_amt:
            amt_formatted = format_inr(t_amount)
            color = "#B3261E" if t_dir == "debit" else "#2E7D4F"
            st.markdown(f'<div style="text-align:right; font-weight:600; color:{color};">{amt_formatted}</div>', unsafe_allow_html=True)

        with c_dir:
            st.markdown(
                f'<div style="text-align:center;"><span class="status-badge" style="font-size:11px;">{t_dir.upper()}</span></div>',
                unsafe_allow_html=True,
            )

        with c_act:
            if st.button("🗑️", key=f"del_txn_{t_id}", help="Delete transaction row"):
                client.delete_transaction(t_id)
                st.toast("Transaction deleted.", icon="🗑️")
                st.rerun()

        st.divider()
