from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.categories import service
from app.modules.categories.models import Category, CategoryType
from app.modules.categories.schemas import CategoryResponse

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
def list_categories(
    session: Annotated[Session, Depends(get_session)],
    _current_user: Annotated[User, Depends(get_current_user)],
    category_type: Annotated[CategoryType | None, Query(alias="type")] = None,
) -> list[Category]:
    return service.list_categories(session, category_type=category_type)
