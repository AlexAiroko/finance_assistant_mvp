from sqlalchemy.orm import Session

from app.modules.reserve import repository
from app.modules.reserve.models import Reserve
from app.modules.reserve.schemas import ReserveUpdate


def get_reserve(session: Session, user_id: int) -> Reserve:
    """Возвращает резерв пользователя, создавая нулевой при отсутствии.

    Инвариант регистрации (этап 5) гарантирует наличие записи, но GET не
    должен падать 500, если запись когда-либо исчезнет. Ленивая инициализация
    с нулём — самое предсказуемое поведение.
    """
    reserve = repository.get_by_user_id(session, user_id)
    if reserve is None:
        reserve = repository.create_default(session, user_id)
        session.commit()
        session.refresh(reserve)
    return reserve


def set_reserve(session: Session, user_id: int, payload: ReserveUpdate) -> Reserve:
    reserve = repository.get_by_user_id(session, user_id)
    if reserve is None:
        reserve = repository.create_default(session, user_id)
    repository.set_amount(session, reserve, payload.amount)
    session.commit()
    session.refresh(reserve)
    return reserve
