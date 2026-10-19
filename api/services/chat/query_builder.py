"""Safe Query Builder converting QuerySpec to SQLAlchemy queries without raw model SQL."""
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from api.db.models import Category, Transaction
from api.schemas import QuerySpec


class QueryExecutionResult:
    def __init__(
        self,
        aggregation: str,
        total_amount: Decimal | None = None,
        count: int = 0,
        average_amount: Decimal | None = None,
        rows: list[dict[str, Any]] | None = None,
        groups: list[dict[str, Any]] | None = None,
        filters_used: dict[str, Any] | None = None,
    ):
        self.aggregation = aggregation
        self.total_amount = total_amount
        self.count = count
        self.average_amount = average_amount
        self.rows = rows or []
        self.groups = groups or []
        self.filters_used = filters_used or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "aggregation": self.aggregation,
            "total_amount": float(self.total_amount) if self.total_amount is not None else None,
            "count": self.count,
            "average_amount": float(self.average_amount) if self.average_amount is not None else None,
            "rows": self.rows,
            "groups": self.groups,
            "filters_used": self.filters_used,
        }


class QueryBuilder:
    @staticmethod
    def execute(db: Session, spec: QuerySpec) -> QueryExecutionResult:
        """Execute a validated QuerySpec against the database safely."""
        query = db.query(Transaction)

        # Filters
        if spec.direction:
            query = query.filter(Transaction.direction == spec.direction.lower())
        if spec.start_date:
            query = query.filter(Transaction.txn_date >= spec.start_date)
        if spec.end_date:
            query = query.filter(Transaction.txn_date <= spec.end_date)
        if spec.statement_ids:
            query = query.filter(Transaction.statement_id.in_(spec.statement_ids))
        if spec.search:
            search_pat = f"%{spec.search}%"
            query = query.filter(
                Transaction.description_clean.ilike(search_pat)
                | Transaction.description_raw.ilike(search_pat)
            )
        if spec.categories:
            query = query.join(Category, Transaction.category_id == Category.id)
            query = query.filter(Category.name.in_(spec.categories))

        # Build readable filters_used dictionary
        filters_used: dict[str, Any] = {}
        if spec.categories:
            filters_used["Category"] = ", ".join(spec.categories)
        if spec.direction:
            filters_used["Direction"] = spec.direction.capitalize()
        if spec.start_date and spec.end_date:
            filters_used["Date Range"] = f"{spec.start_date} to {spec.end_date}"
        elif spec.start_date:
            filters_used["Date Range"] = f"From {spec.start_date}"
        elif spec.end_date:
            filters_used["Date Range"] = f"Until {spec.end_date}"
        if spec.search:
            filters_used["Search"] = spec.search
        if spec.aggregation == "top_n" and spec.top_n_limit:
            filters_used["Limit"] = f"Top {spec.top_n_limit}"

        agg = (spec.aggregation or "sum").lower()

        # Execute aggregation
        if agg == "count":
            count = query.count()
            return QueryExecutionResult(aggregation="count", count=count, filters_used=filters_used)

        elif agg == "average":
            result = query.with_entities(
                func.coalesce(func.avg(Transaction.amount), Decimal("0.00")).label("avg_amt"),
                func.count(Transaction.id).label("cnt"),
            ).first()
            avg_amt = Decimal(str(result.avg_amt or "0.00")).quantize(Decimal("0.01"))
            cnt = int(result.cnt or 0)
            return QueryExecutionResult(
                aggregation="average",
                average_amount=avg_amt,
                count=cnt,
                filters_used=filters_used,
            )

        elif agg in ["top_n", "list"]:
            limit = spec.top_n_limit or (5 if agg == "top_n" else 20)
            order_by_clause = Transaction.amount.desc()
            if spec.order_by == "date_desc":
                order_by_clause = Transaction.txn_date.desc()
            elif spec.order_by == "date_asc":
                order_by_clause = Transaction.txn_date.asc()
            elif spec.order_by == "amount_asc":
                order_by_clause = Transaction.amount.asc()

            items = query.order_by(order_by_clause).limit(limit).all()
            total_sum = sum((item.amount for item in items), Decimal("0.00"))
            rows = [
                {
                    "date": item.txn_date.isoformat(),
                    "description": item.description_clean or item.description_raw,
                    "amount": float(item.amount),
                    "direction": item.direction,
                    "category": item.category.name if item.category else "Other",
                }
                for item in items
            ]
            return QueryExecutionResult(
                aggregation=agg,
                total_amount=total_sum,
                count=len(rows),
                rows=rows,
                filters_used=filters_used,
            )

        else:  # Default to "sum"
            result = query.with_entities(
                func.coalesce(func.sum(Transaction.amount), Decimal("0.00")).label("sum_amt"),
                func.count(Transaction.id).label("cnt"),
            ).first()
            sum_amt = Decimal(str(result.sum_amt or "0.00"))
            cnt = int(result.cnt or 0)
            return QueryExecutionResult(
                aggregation="sum",
                total_amount=sum_amt,
                count=cnt,
                filters_used=filters_used,
            )
