"""Category seed data and seed runner."""
from sqlalchemy.orm import Session

from api.db.models import Category

DEFAULT_CATEGORIES: list[dict[str, str | int]] = [
    {"name": "Food and Dining", "sort_order": 1},
    {"name": "Groceries", "sort_order": 2},
    {"name": "Rent and Housing", "sort_order": 3},
    {"name": "Utilities and Bills", "sort_order": 4},
    {"name": "Transport", "sort_order": 5},
    {"name": "Shopping", "sort_order": 6},
    {"name": "Health", "sort_order": 7},
    {"name": "Entertainment", "sort_order": 8},
    {"name": "Travel", "sort_order": 9},
    {"name": "Education", "sort_order": 10},
    {"name": "Transfers", "sort_order": 11},
    {"name": "Income", "sort_order": 12},
    {"name": "Fees and Charges", "sort_order": 13},
    {"name": "Other", "sort_order": 14},
]


def seed_categories(db: Session) -> list[Category]:
    """Seed initial categories if not already present."""
    seeded: list[Category] = []
    for item in DEFAULT_CATEGORIES:
        name = str(item["name"])
        sort_order = int(item["sort_order"])
        existing = db.query(Category).filter(Category.name == name).first()
        if not existing:
            category = Category(name=name, sort_order=sort_order)
            db.add(category)
            seeded.append(category)
        else:
            seeded.append(existing)
    db.commit()
    return seeded
