"""Categories routes: list fixed categories."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.db.models import Category
from api.db.seed import seed_categories
from api.db.session import get_db
from api.schemas import CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get(
    "",
    response_model=list[CategoryResponse],
    summary="List all categories sorted by display order",
)
def list_categories(
    db: Session = Depends(get_db),
) -> list[Category]:
    categories = db.query(Category).order_by(Category.sort_order.asc()).all()
    if not categories:
        categories = seed_categories(db)
    return categories
