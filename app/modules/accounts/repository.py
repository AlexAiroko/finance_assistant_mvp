from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.accounts.models import Account
from app.modules.operations.models import Operation


def list_by_user(session: Session, user_id: int) -> list[Account]:
    stmt = select(Account).where(Account.user_id == user_id).order_by(Account.id.asc())
    return list(session.execute(stmt).scalars().all())


def get_by_id(session: Session, account_id: int) -> Account | None:
    return session.get(Account, account_id)


def get_owned(session: Session, user_id: int, account_id: int) -> Account | None:
    stmt = select(Account).where(Account.id == account_id, Account.user_id == user_id)
    return session.execute(stmt).scalar_one_or_none()


def create(session: Session, *, user_id: int, name: str, balance: Decimal) -> Account:
    account = Account(user_id=user_id, name=name, balance=balance)
    session.add(account)
    session.flush()
    return account


def delete(session: Session, account: Account) -> None:
    session.delete(account)


def has_operations(session: Session, account_id: int) -> bool:
    stmt = (
        select(Operation.id)
        .where(
            or_(
                Operation.from_account_id == account_id,
                Operation.to_account_id == account_id,
            )
        )
        .limit(1)
    )
    return session.execute(stmt).first() is not None
