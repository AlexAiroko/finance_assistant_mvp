from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    UnprocessableEntityError,
)
from app.modules.accounts import repository as accounts_repository
from app.modules.accounts.models import Account
from app.modules.categories import service as categories_service
from app.modules.categories.models import CategoryType
from app.modules.operations import repository
from app.modules.operations.models import Operation, OperationType
from app.modules.operations.schemas import OperationCreate, OperationUpdate
from app.modules.planned_expenses import repository as planned_expenses_repository


def create_operation(session: Session, user_id: int, payload: OperationCreate) -> Operation:
    from_account = _resolve_account(session, user_id, payload.from_account_id)
    to_account = _resolve_account(session, user_id, payload.to_account_id)

    if payload.type == OperationType.INCOME:
        categories_service.ensure_category_of_type(
            session, payload.category_id, CategoryType.INCOME
        )
    elif payload.type == OperationType.EXPENSE:
        categories_service.ensure_category_of_type(
            session, payload.category_id, CategoryType.EXPENSE
        )

    occurred_at = payload.occurred_at or datetime.now(UTC)

    if payload.type == OperationType.INCOME:
        from_account.balance += payload.amount
    elif payload.type == OperationType.EXPENSE:
        _ensure_sufficient_funds(from_account, payload.amount)
        from_account.balance -= payload.amount
    elif payload.type == OperationType.TRANSFER:
        _ensure_sufficient_funds(from_account, payload.amount)
        from_account.balance -= payload.amount
        to_account.balance += payload.amount

    operation = repository.create(
        session,
        user_id=user_id,
        operation_type=payload.type,
        amount=payload.amount,
        occurred_at=occurred_at,
        from_account_id=payload.from_account_id,
        to_account_id=payload.to_account_id,
        category_id=payload.category_id,
        comment=payload.comment,
    )
    session.commit()
    session.refresh(operation)
    return operation


def update_operation(
    session: Session,
    user_id: int,
    operation_id: int,
    payload: OperationUpdate,
) -> Operation:
    operation = repository.get_owned(session, user_id, operation_id)
    if operation is None:
        raise NotFoundError("operation_not_found", "Операция не найдена")

    if planned_expenses_repository.exists_by_paid_operation_id(session, operation_id):
        raise ConflictError(
            "operation_linked_to_planned_expense",
            "Операция привязана к оплаченному запланированному расходу",
        )

    final_amount = payload.amount if "amount" in payload.model_fields_set else operation.amount
    final_occurred_at = (
        payload.occurred_at if "occurred_at" in payload.model_fields_set else operation.occurred_at
    )
    final_from = (
        payload.from_account_id
        if "from_account_id" in payload.model_fields_set
        else operation.from_account_id
    )
    final_to = (
        payload.to_account_id
        if "to_account_id" in payload.model_fields_set
        else operation.to_account_id
    )
    final_category = (
        payload.category_id if "category_id" in payload.model_fields_set else operation.category_id
    )
    final_comment = payload.comment if "comment" in payload.model_fields_set else operation.comment

    _validate_final_state(operation.type, final_from, final_to, final_category)

    old_from = (
        accounts_repository.get_owned(session, user_id, operation.from_account_id)
        if operation.from_account_id
        else None
    )
    old_to = (
        accounts_repository.get_owned(session, user_id, operation.to_account_id)
        if operation.to_account_id
        else None
    )
    new_from = _resolve_account(session, user_id, final_from)
    new_to = _resolve_account(session, user_id, final_to)

    if operation.type == OperationType.INCOME:
        categories_service.ensure_category_of_type(session, final_category, CategoryType.INCOME)
    elif operation.type == OperationType.EXPENSE:
        categories_service.ensure_category_of_type(session, final_category, CategoryType.EXPENSE)

    try:
        if operation.type == OperationType.INCOME:
            old_from.balance -= operation.amount
            new_from.balance += final_amount
        elif operation.type == OperationType.EXPENSE:
            old_from.balance += operation.amount
            new_from.balance -= final_amount
        else:
            old_from.balance += operation.amount
            old_to.balance -= operation.amount
            new_from.balance -= final_amount
            new_to.balance += final_amount

        for acc in (old_from, old_to, new_from, new_to):
            if acc is not None and acc.balance < 0:
                raise UnprocessableEntityError(
                    "insufficient_funds",
                    "Недостаточно средств на счёте после изменения операции",
                )

        operation.amount = final_amount
        operation.occurred_at = final_occurred_at
        operation.from_account_id = final_from
        operation.to_account_id = final_to
        operation.category_id = final_category
        operation.comment = final_comment

        session.commit()
        session.refresh(operation)
        return operation
    except Exception:
        session.rollback()
        raise


def delete_operation(session: Session, user_id: int, operation_id: int) -> None:
    operation = repository.get_owned(session, user_id, operation_id)
    if operation is None:
        raise NotFoundError("operation_not_found", "Операция не найдена")

    if planned_expenses_repository.exists_by_paid_operation_id(session, operation_id):
        raise ConflictError(
            "operation_linked_to_planned_expense",
            "Операция привязана к оплаченному запланированному расходу",
        )

    old_from = (
        accounts_repository.get_owned(session, user_id, operation.from_account_id)
        if operation.from_account_id
        else None
    )
    old_to = (
        accounts_repository.get_owned(session, user_id, operation.to_account_id)
        if operation.to_account_id
        else None
    )

    try:
        if operation.type == OperationType.INCOME:
            old_from.balance -= operation.amount
        elif operation.type == OperationType.EXPENSE:
            old_from.balance += operation.amount
        else:
            old_from.balance += operation.amount
            old_to.balance -= operation.amount

        for acc in (old_from, old_to):
            if acc is not None and acc.balance < 0:
                raise UnprocessableEntityError(
                    "insufficient_funds",
                    "Невозможно удалить операцию: недостаточно средств на счёте",
                )

        repository.delete(session, operation)
        session.commit()
    except Exception:
        session.rollback()
        raise


def list_operations(session: Session, user_id: int, **filters) -> tuple[list[Operation], int]:
    return repository.list_operations(session, user_id, **filters)


def get_operation(session: Session, user_id: int, operation_id: int) -> Operation:
    operation = repository.get_owned(session, user_id, operation_id)
    if operation is None:
        raise NotFoundError("operation_not_found", "Операция не найдена")
    return operation


def _resolve_account(
    session: Session,
    user_id: int,
    account_id: int | None,
) -> Account | None:
    if account_id is None:
        return None
    account = accounts_repository.get_owned(session, user_id, account_id)
    if account is None:
        raise NotFoundError("account_not_found", "Счёт не найден")
    return account


def _ensure_sufficient_funds(account: Account, amount) -> None:
    if account.balance < amount:
        raise UnprocessableEntityError("insufficient_funds", "Недостаточно средств на счёте")


def _validate_final_state(
    operation_type: OperationType,
    from_account_id: int | None,
    to_account_id: int | None,
    category_id: int | None,
) -> None:
    if operation_type in (OperationType.INCOME, OperationType.EXPENSE):
        if from_account_id is None:
            raise UnprocessableEntityError("validation_error", "from_account_id обязателен")
        if to_account_id is not None:
            raise UnprocessableEntityError("validation_error", "to_account_id недопустим")
        if category_id is None:
            raise UnprocessableEntityError("validation_error", "category_id обязателен")
    elif operation_type == OperationType.TRANSFER:
        if from_account_id is None:
            raise UnprocessableEntityError("validation_error", "from_account_id обязателен")
        if to_account_id is None:
            raise UnprocessableEntityError("validation_error", "to_account_id обязателен")
        if from_account_id == to_account_id:
            raise UnprocessableEntityError(
                "invalid_transfer_accounts",
                "Счета перевода должны различаться",
            )
        if category_id is not None:
            raise UnprocessableEntityError("validation_error", "category_id недопустим")
