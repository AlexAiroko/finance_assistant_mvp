from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.accounts import repository
from app.modules.accounts.models import Account
from app.modules.accounts.schemas import AccountCreate, AccountUpdate


def list_accounts(session: Session, user_id: int) -> list[Account]:
    return repository.list_by_user(session, user_id)


def get_account(session: Session, user_id: int, account_id: int) -> Account:
    account = repository.get_owned(session, user_id, account_id)
    if account is None:
        raise NotFoundError("account_not_found", "Счёт не найден")
    return account


def create_account(session: Session, user_id: int, payload: AccountCreate) -> Account:
    account = repository.create(
        session,
        user_id=user_id,
        name=payload.name,
        balance=payload.balance,
    )
    session.commit()
    session.refresh(account)
    return account


def update_account(
    session: Session,
    user_id: int,
    account_id: int,
    payload: AccountUpdate,
) -> Account:
    account = get_account(session, user_id, account_id)
    if "name" in payload.model_fields_set and payload.name is not None:
        account.name = payload.name
    if "balance" in payload.model_fields_set and payload.balance is not None:
        account.balance = payload.balance
    session.commit()
    session.refresh(account)
    return account


def delete_account(session: Session, user_id: int, account_id: int) -> None:
    account = get_account(session, user_id, account_id)
    if repository.has_operations(session, account.id):
        raise ConflictError(
            "account_has_operations",
            "Нельзя удалить счёт с операциями",
        )
    repository.delete(session, account)
    session.commit()
