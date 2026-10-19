"""Currency, date, and badge formatting utilities adhering to Document 04."""
from decimal import Decimal


def format_inr(amount: Decimal | float | int | None) -> str:
    """Format numeric values as Indian Rupee with comma grouping."""
    if amount is None:
        return "-"
    try:
        val = Decimal(str(amount))
        # Format with Indian numbering system (e.g. 1,00,000.00) or standard 2 decimals
        is_negative = val < 0
        abs_val = abs(val)
        parts = f"{abs_val:.2f}".split(".")
        integer_part = parts[0]
        decimal_part = parts[1]

        if len(integer_part) > 3:
            last_three = integer_part[-3:]
            remaining = integer_part[:-3]
            # Group in pairs of two for Indian lakhs/crores
            groups = []
            while len(remaining) > 2:
                groups.insert(0, remaining[-2:])
                remaining = remaining[:-2]
            if remaining:
                groups.insert(0, remaining)
            formatted_int = ",".join(groups) + "," + last_three
        else:
            formatted_int = integer_part

        formatted = f"₹{formatted_int}.{decimal_part}"
        return f"-{formatted}" if is_negative else formatted
    except Exception:
        return str(amount)


def render_status_badge(status_str: str) -> str:
    """Render status badge matching Document 04 design."""
    s = (status_str or "").lower()
    if s == "confirmed":
        return '<span class="status-badge badge-confirmed">✓ Confirmed</span>'
    elif s == "needs_review":
        return '<span class="status-badge badge-review">● Needs Review</span>'
    elif s == "processing":
        return '<span class="status-badge badge-processing">◌ Processing</span>'
    elif s == "failed":
        return '<span class="status-badge badge-failed">✕ Failed</span>'
    return f'<span class="status-badge">{status_str}</span>'


def render_reconciliation_badge(reconcile_status: str, diff: Decimal | float | None = None) -> str:
    """Render reconciliation badge (Passed in green, Failed with diff in red, Not Available in grey)."""
    r = (reconcile_status or "").lower()
    if r == "passed":
        return '<span class="status-badge badge-passed">✓ Reconciliation Passed</span>'
    elif r == "failed":
        diff_str = f" ({format_inr(diff)})" if diff is not None else ""
        return f'<span class="status-badge badge-reconcile-failed">✕ Reconciliation Failed{diff_str}</span>'
    else:
        return '<span class="status-badge badge-na">○ Not Available</span>'
