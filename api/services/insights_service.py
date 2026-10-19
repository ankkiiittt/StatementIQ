"""Insights calculation service using database aggregation."""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from api.db.models import Category, Transaction
from api.schemas import (
    CategorySpendItem,
    InsightsResponse,
    MerchantSpendItem,
    MonthlyTrendItem,
)


class InsightsService:
    @staticmethod
    def get_insights(
        db: Session,
        statement_id: uuid.UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> InsightsResponse:
        """Calculate financial totals, category breakdown, monthly trends, and top merchants."""
        query = db.query(Transaction)

        if statement_id:
            query = query.filter(Transaction.statement_id == statement_id)
        if start_date:
            query = query.filter(Transaction.txn_date >= start_date)
        if end_date:
            query = query.filter(Transaction.txn_date <= end_date)

        # 1. Totals
        totals_query = query.with_entities(
            func.coalesce(
                func.sum(case((Transaction.direction == "debit", Transaction.amount), else_=Decimal("0.00"))),
                Decimal("0.00"),
            ).label("total_spend"),
            func.coalesce(
                func.sum(case((Transaction.direction == "credit", Transaction.amount), else_=Decimal("0.00"))),
                Decimal("0.00"),
            ).label("total_income"),
            func.count(Transaction.id).label("txn_count"),
        ).first()

        total_spend = Decimal(str(totals_query.total_spend or "0.00"))
        total_income = Decimal(str(totals_query.total_income or "0.00"))
        txn_count = int(totals_query.txn_count or 0)
        net_savings = total_income - total_spend

        # 2. Spend by Category (Debits only)
        cat_query = (
            query.filter(Transaction.direction == "debit")
            .join(Category, Transaction.category_id == Category.id)
            .with_entities(
                Category.id.label("category_id"),
                Category.name.label("category_name"),
                func.sum(Transaction.amount).label("category_total"),
                func.count(Transaction.id).label("category_count"),
            )
            .group_by(Category.id, Category.name)
            .order_by(func.sum(Transaction.amount).desc())
            .all()
        )

        spend_by_category: list[CategorySpendItem] = []
        for cat in cat_query:
            cat_amount = Decimal(str(cat.category_total or "0.00"))
            pct = (
                (cat_amount / total_spend * Decimal("100")).quantize(Decimal("0.01"))
                if total_spend > Decimal("0.00")
                else Decimal("0.00")
            )
            spend_by_category.append(
                CategorySpendItem(
                    category_id=cat.category_id,
                    category_name=cat.category_name,
                    total_amount=cat_amount,
                    percentage=pct,
                    transaction_count=cat.category_count,
                )
            )

        # 3. Monthly Trend (group by YYYY-MM)
        bind = db.get_bind()
        if bind.dialect.name == "postgresql":
            month_expr = func.to_char(Transaction.txn_date, "YYYY-MM")
        else:
            month_expr = func.strftime("%Y-%m", Transaction.txn_date)

        trend_query = (
            query.with_entities(
                month_expr.label("month_str"),
                func.coalesce(
                    func.sum(case((Transaction.direction == "debit", Transaction.amount), else_=Decimal("0.00"))),
                    Decimal("0.00"),
                ).label("month_spend"),
                func.coalesce(
                    func.sum(case((Transaction.direction == "credit", Transaction.amount), else_=Decimal("0.00"))),
                    Decimal("0.00"),
                ).label("month_income"),
            )
            .group_by("month_str")
            .order_by("month_str")
            .all()
        )

        monthly_trend: list[MonthlyTrendItem] = []
        for m in trend_query:
            m_spend = Decimal(str(m.month_spend or "0.00"))
            m_income = Decimal(str(m.month_income or "0.00"))
            monthly_trend.append(
                MonthlyTrendItem(
                    month=str(m.month_str or ""),
                    total_spend=m_spend,
                    total_income=m_income,
                    net_savings=m_income - m_spend,
                )
            )

        # 4. Top 10 Merchants (Debits only)
        merchant_expr = func.coalesce(Transaction.description_clean, Transaction.description_raw)
        merchant_query = (
            query.filter(Transaction.direction == "debit")
            .with_entities(
                merchant_expr.label("merchant_name"),
                func.sum(Transaction.amount).label("merchant_total"),
                func.count(Transaction.id).label("merchant_count"),
            )
            .group_by("merchant_name")
            .order_by(func.sum(Transaction.amount).desc())
            .limit(10)
            .all()
        )

        top_merchants: list[MerchantSpendItem] = []
        for m in merchant_query:
            m_amount = Decimal(str(m.merchant_total or "0.00"))
            m_pct = (
                (m_amount / total_spend * Decimal("100")).quantize(Decimal("0.01"))
                if total_spend > Decimal("0.00")
                else Decimal("0.00")
            )
            top_merchants.append(
                MerchantSpendItem(
                    merchant=str(m.merchant_name),
                    total_amount=m_amount,
                    transaction_count=m.merchant_count,
                    percentage=m_pct,
                )
            )

        return InsightsResponse(
            total_spend=total_spend,
            total_income=total_income,
            net_savings=net_savings,
            transaction_count=txn_count,
            spend_by_category=spend_by_category,
            monthly_trend=monthly_trend,
            top_merchants=top_merchants,
        )
