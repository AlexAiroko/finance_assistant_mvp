from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.categories.models import Category, CategoryType


def list_categories(
    session: Session,
    category_type: CategoryType | None = None,
) -> list[Category]:
    stmt = select(Category).order_by(Category.id.asc())
    if category_type is not None:
        stmt = stmt.where(Category.type == category_type)
    return list(session.execute(stmt).scalars().all())


def get_by_id(session: Session, category_id: int) -> Category | None:
    return session.get(Category, category_id)
