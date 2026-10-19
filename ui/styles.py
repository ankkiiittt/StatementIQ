"""CSS theme and typography styles matching Document 04 Design Brief."""
import streamlit as st


def apply_custom_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            color: #1B1F23;
        }

        /* Container constraints */
        .block-container {
            max-width: 1100px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        /* Typography */
        h1, .page-title {
            font-size: 28px !important;
            font-weight: 700 !important;
            color: #1B1F23 !important;
            margin-bottom: 4px !important;
            line-height: 1.2 !important;
        }

        h2, .section-title {
            font-size: 20px !important;
            font-weight: 600 !important;
            color: #1B1F23 !important;
            margin-top: 18px !important;
            margin-bottom: 12px !important;
        }

        .text-muted {
            color: #5F6B76 !important;
            font-size: 14px;
        }

        /* Surface cards */
        .surface-card {
            background-color: #FFFFFF;
            border: 1px solid #E1DED6;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }

        .metric-card {
            background-color: #FFFFFF;
            border: 1px solid #E1DED6;
            border-radius: 8px;
            padding: 16px;
            text-align: left;
        }

        .metric-card .metric-label {
            font-size: 13px;
            font-weight: 500;
            color: #5F6B76;
            margin-bottom: 6px;
        }

        .metric-card .metric-value {
            font-size: 24px;
            font-weight: 700;
            color: #1B1F23;
            font-variant-numeric: tabular-nums;
        }

        .metric-card .metric-sub {
            font-size: 12px;
            color: #5F6B76;
            margin-top: 4px;
        }

        /* Badges */
        .status-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            line-height: 1.4;
        }

        .badge-confirmed {
            background-color: #E8F5E9;
            color: #2E7D4F;
            border: 1px solid #C8E6C9;
        }

        .badge-passed {
            background-color: #E8F5E9;
            color: #2E7D4F;
            border: 1px solid #C8E6C9;
        }

        .badge-review {
            background-color: #FFF8E1;
            color: #C8872B;
            border: 1px solid #FFE082;
        }

        .badge-processing {
            background-color: #E0F2F1;
            color: #0F5C4D;
            border: 1px solid #B2DFDB;
        }

        .badge-failed, .badge-reconcile-failed {
            background-color: #FFEBEE;
            color: #B3261E;
            border: 1px solid #FFCDD2;
        }

        .badge-na {
            background-color: #F0F2F5;
            color: #5F6B76;
            border: 1px solid #E1DED6;
        }

        /* Stepper */
        .stepper-container {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin: 20px 0;
            padding: 16px;
            background-color: #FFFFFF;
            border: 1px solid #E1DED6;
            border-radius: 8px;
        }

        .step-item {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 14px;
            color: #5F6B76;
        }

        .step-item.active {
            font-weight: 600;
            color: #0F5C4D;
        }

        .step-item.done {
            color: #2E7D4F;
        }

        .step-dot {
            width: 22px;
            height: 22px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            border: 1px solid #E1DED6;
            background-color: #F7F6F2;
        }

        .step-dot.active {
            background-color: #0F5C4D;
            color: #FFFFFF;
            border-color: #0F5C4D;
        }

        .step-dot.done {
            background-color: #2E7D4F;
            color: #FFFFFF;
            border-color: #2E7D4F;
        }

        /* Direction badges */
        .direction-debit {
            color: #B3261E;
            font-weight: 600;
        }

        .direction-credit {
            color: #2E7D4F;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
