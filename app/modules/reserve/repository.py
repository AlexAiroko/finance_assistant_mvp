from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.reserve.models import Reserve


def get_by_user_id(session: Session, user_id: int) -> Reserve | None:
    stmt = select(Reserve).where(Reserve.user_id == user_id)
    return session.execute(stmt).scalar_one_or_none()


def create_default(session: Session, user_id: int) -> Reserve:
    reserve = Reserve(user_id=user_id, amount=Decimal("0.00"))
    session.add(reserve)
    session.flush()
    return reserve


def set_amount(session: Session, reserve: Reserve, amount: Decimal) -> Reserve:
    reserve.amount = amount
    session.flush()
    return reserve
