"""Insights route: financial totals, category breakdown, monthly trends, top merchants."""
import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.db.session import get_db
from api.schemas import InsightsResponse
from api.services.insights_service import InsightsService

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get(
    "",
    response_model=InsightsResponse,
    summary="Get financial totals, category breakdown, monthly trends, and top merchants",
)
def get_insights(
    statement_id: uuid.UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
) -> InsightsResponse:
    return InsightsService.get_insights(
        db=db,
        statement_id=statement_id,
        start_date=start_date,
        end_date=end_date,
    )
