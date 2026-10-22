from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, UnprocessableEntityError
from app.modules.categories import repository
from app.modules.categories.models import Category, CategoryType


def list_categories(
    session: Session,
    category_type: CategoryType | None = None,
) -> list[Category]:
    return repository.list_categories(session, category_type=category_type)


def ensure_category_of_type(
    session: Session,
    category_id: int,
    expected_type: CategoryType,
) -> Category:
    """Возвращает категорию, проверяя, что её тип совпадает с ожидаемым.

    Используется в модуле operations (этап 8) для income/expense.
    Единая точка проверки правила «категория соответствует типу операции».
    """
    category = repository.get_by_id(session, category_id)
    if category is None:
        raise NotFoundError("category_not_found", "Категория не найдена")
    if category.type != expected_type:
        raise UnprocessableEntityError(
            "validation_error",
            "Категория не соответствует типу операции",
        )
    return category
