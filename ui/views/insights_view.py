"""Insights dashboard adhering to Document 03 and Document 04."""
from datetime import date
from decimal import Decimal
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from ui.api_client import client
from ui.formatting import format_inr


def render_insights_view() -> None:
    st.markdown('<div class="page-title">Spending Insights</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="text-muted">High-level overview of money out and in, categorized spending, monthly trends, and top merchants.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<br/>", unsafe_allow_html=True)

    # 1. Fetch available statements for filtering
    try:
        statements = client.list_statements()
    except Exception as exc:
        st.error(f"Could not load statements: {exc!s}")
        if st.button("Retry"):
            st.rerun()
        return

    # Empty state: No statements exist yet
    if not statements:
        st.info("💡 Upload a bank statement to see spending insights, category breakdowns, and monthly trends.")
        if st.button("Go to Upload Page", type="primary"):
            st.session_state["nav_page"] = "Upload"
            st.rerun()
        return

    # 2. Filter Bar
    stmt_options = ["All Statements"]
    stmt_id_map: dict[str, str | None] = {"All Statements": None}

    for s in statements:
        bank = s.get("bank_name") or "Statement"
        filename = s.get("filename") or "statement.pdf"
        p_start = s.get("period_start") or ""
        p_end = s.get("period_end") or ""
        label = f"{bank} ({p_start} - {p_end}) — {filename}" if p_start and p_end else f"{bank} — {filename}"
        stmt_options.append(label)
        stmt_id_map[label] = str(s["id"])

    f_col1, f_col2, f_col3 = st.columns([3, 1.5, 1.5])

    with f_col1:
        selected_stmt_label = st.selectbox(
            "Filter by Statement",
            stmt_options,
            index=0,
            key="insights_stmt_filter",
        )
        selected_stmt_id = stmt_id_map.get(selected_stmt_label)

    with f_col2:
        start_date_val = st.date_input(
            "From Date",
            value=None,
            key="insights_start_date",
        )

    with f_col3:
        end_date_val = st.date_input(
            "To Date",
            value=None,
            key="insights_end_date",
        )

    # Convert date values
    filter_start = start_date_val if isinstance(start_date_val, date) else None
    filter_end = end_date_val if isinstance(end_date_val, date) else None

    # 3. Fetch Insights Data from Backend
    try:
        insights = client.get_insights(
            statement_id=selected_stmt_id,
            start_date=filter_start,
            end_date=filter_end,
        )
    except Exception as exc:
        st.error(f"Failed to calculate insights: {exc!s}")
        return

    txn_count = insights.get("transaction_count", 0)

    # Empty state for filtered query
    if txn_count == 0:
        st.warning("No transactions found matching the selected statement or date range.")
        return

    total_spend = Decimal(str(insights.get("total_spend", "0.00")))
    total_income = Decimal(str(insights.get("total_income", "0.00")))
    net_savings = Decimal(str(insights.get("net_savings", "0.00")))

    # 4. Four Top Metric Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Total Spend (Debits)</div>
                <div class="metric-value">{format_inr(total_spend)}</div>
                <div class="metric-sub">Money out</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Total Income (Credits)</div>
                <div class="metric-value">{format_inr(total_income)}</div>
                <div class="metric-sub">Money in</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m3:
        savings_color = "#2E7D4F" if net_savings >= Decimal("0.00") else "#B3261E"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Net Savings</div>
                <div class="metric-value" style="color: {savings_color};">{format_inr(net_savings)}</div>
                <div class="metric-sub">Income − Spend</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Transactions</div>
                <div class="metric-value">{txn_count:,}</div>
                <div class="metric-sub">Total records</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br/>", unsafe_allow_html=True)

    # 5. Charts Section (Category Spend & Monthly Trend)
    chart_col1, chart_col2 = st.columns([1.2, 1])

    with chart_col1:
        st.markdown('<div class="section-title">Spend by Category</div>', unsafe_allow_html=True)
        categories_data: list[dict[str, Any]] = insights.get("spend_by_category", [])

        if categories_data:
            cat_df = pd.DataFrame([
                {
                    "Category": c["category_name"],
                    "Spend": float(c["total_amount"]),
                    "Percentage": float(c["percentage"]),
                    "Count": c["transaction_count"],
                    "Display": f"₹{float(c['total_amount']):,.2f} ({float(c['percentage']):.1f}%)",
                }
                for c in categories_data
            ])

            # Horizontal bar chart sorted descending
            chart_height = max(320, len(categories_data) * 26)
            cat_chart = (
                alt.Chart(cat_df)
                .mark_bar(color="#0F5C4D", cornerRadiusEnd=3)
                .encode(
                    x=alt.X("Spend:Q", title="Total Spend (₹)", axis=alt.Axis(format="~s")),
                    y=alt.Y("Category:N", sort="-x", title=None),
                    tooltip=[
                        alt.Tooltip("Category:N"),
                        alt.Tooltip("Spend:Q", format=",.2f", title="Spend (₹)"),
                        alt.Tooltip("Percentage:Q", format=".1f", title="Share (%)"),
                        alt.Tooltip("Count:Q", title="Transactions"),
                    ],
                )
                .properties(height=chart_height)
            )

            st.altair_chart(cat_chart, use_container_width=True)
        else:
            st.info("No debit transactions recorded for category breakdown.")

    with chart_col2:
        st.markdown('<div class="section-title">Monthly Trend</div>', unsafe_allow_html=True)
        monthly_data: list[dict[str, Any]] = insights.get("monthly_trend", [])

        if monthly_data:
            trend_rows = []
            for m in monthly_data:
                month_label = m["month"]
                trend_rows.append({"Month": month_label, "Type": "Income", "Amount": float(m["total_income"])})
                trend_rows.append({"Month": month_label, "Type": "Spent", "Amount": float(m["total_spend"])})

            trend_df = pd.DataFrame(trend_rows)

            trend_chart = (
                alt.Chart(trend_df)
                .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
                .encode(
                    x=alt.X("Month:N", title=None),
                    xOffset="Type:N",
                    y=alt.Y("Amount:Q", title="Amount (₹)", axis=alt.Axis(format="~s")),
                    color=alt.Color(
                        "Type:N",
                        scale=alt.Scale(
                            domain=["Income", "Spent"],
                            range=["#2E7D4F", "#B3261E"],
                        ),
                        title=None,
                        legend=alt.Legend(orient="top", direction="horizontal"),
                    ),
                    tooltip=[
                        alt.Tooltip("Month:N"),
                        alt.Tooltip("Type:N"),
                        alt.Tooltip("Amount:Q", format=",.2f", title="Amount (₹)"),
                    ],
                )
                .properties(height=320)
            )

            st.altair_chart(trend_chart, use_container_width=True)
        else:
            st.info("No monthly trend data available.")

    st.markdown("<br/>", unsafe_allow_html=True)

    # 6. Top 10 Merchants Table
    st.markdown('<div class="section-title">Top 10 Merchants by Spend</div>', unsafe_allow_html=True)
    merchants_data: list[dict[str, Any]] = insights.get("top_merchants", [])

    if merchants_data:
        st.markdown(
            """
            <div style="display:flex; font-weight:600; color:#5F6B76; font-size:13px; border-bottom:1px solid #E1DED6; padding-bottom:8px; margin-bottom:8px;">
                <div style="flex:0.5;">#</div>
                <div style="flex:4;">Merchant Name</div>
                <div style="flex:1.5; text-align:center;">Transactions</div>
                <div style="flex:2; text-align:right;">Total Spent</div>
                <div style="flex:1.5; text-align:right;">Share (%)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for idx, m in enumerate(merchants_data, start=1):
            name = m.get("merchant") or "Unknown"
            count = m.get("transaction_count", 0)
            m_amount = m.get("total_amount", 0)
            pct = m.get("percentage")
            pct_str = f"{float(pct):.1f}%" if pct is not None else "-"

            st.markdown(
                f"""
                <div style="display:flex; align-items:center; padding:8px 0; border-bottom:1px solid #F0EFEA; font-size:14px;">
                    <div style="flex:0.5; color:#5F6B76; font-size:13px;">{idx}</div>
                    <div style="flex:4; font-weight:500;">{name}</div>
                    <div style="flex:1.5; text-align:center; color:#5F6B76;">{count}</div>
                    <div style="flex:2; text-align:right; font-weight:600; color:#B3261E;">{format_inr(m_amount)}</div>
                    <div style="flex:1.5; text-align:right; color:#5F6B76;">{pct_str}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No merchant spending data available.")
