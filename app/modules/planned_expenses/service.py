from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    UnprocessableEntityError,
)
from app.modules.accounts import repository as accounts_repository
from app.modules.categories import service as categories_service
from app.modules.categories.models import CategoryType
from app.modules.operations import repository as operations_repository
from app.modules.operations.models import OperationType
from app.modules.planned_expenses import repository
from app.modules.planned_expenses.models import PlannedExpense, PlannedExpenseStatus
from app.modules.planned_expenses.schemas import (
    PlannedExpenseCreate,
    PlannedExpensePayRequest,
    PlannedExpenseUpdate,
)


def list_planned_expenses(
    session: Session,
    user_id: int,
    status: PlannedExpenseStatus | None = None,
) -> list[PlannedExpense]:
    return repository.list_by_user(session, user_id, status=status)


def get_planned_expense(session: Session, user_id: int, planned_expense_id: int) -> PlannedExpense:
    pe = repository.get_owned(session, user_id, planned_expense_id)
    if pe is None:
        raise NotFoundError("planned_expense_not_found", "Запланированный расход не найден")
    return pe


def create_planned_expense(
    session: Session, user_id: int, payload: PlannedExpenseCreate
) -> PlannedExpense:
    planned_expense = repository.create(
        session,
        user_id=user_id,
        name=payload.name,
        amount=payload.amount,
        due_date=payload.due_date,
    )
    session.commit()
    session.refresh(planned_expense)
    return planned_expense


def update_planned_expense(
    session: Session,
    user_id: int,
    planned_expense_id: int,
    payload: PlannedExpenseUpdate,
) -> PlannedExpense:
    pe = get_planned_expense(session, user_id, planned_expense_id)
    if pe.status == PlannedExpenseStatus.PAID:
        raise ConflictError(
            "planned_expense_already_paid",
            "Нельзя изменить оплаченный запланированный расход",
        )

    if "name" in payload.model_fields_set and payload.name is not None:
        pe.name = payload.name
    if "amount" in payload.model_fields_set and payload.amount is not None:
        pe.amount = payload.amount
    if "due_date" in payload.model_fields_set and payload.due_date is not None:
        pe.due_date = payload.due_date

    session.commit()
    session.refresh(pe)
    return pe


def pay_planned_expense(
    session: Session,
    user_id: int,
    planned_expense_id: int,
    payload: PlannedExpensePayRequest,
) -> PlannedExpense:
    pe = get_planned_expense(session, user_id, planned_expense_id)
    if pe.status == PlannedExpenseStatus.PAID:
        raise ConflictError(
            "planned_expense_already_paid",
            "Запланированный расход уже оплачен",
        )

    account = accounts_repository.get_owned(session, user_id, payload.account_id)
    if account is None:
        raise NotFoundError("account_not_found", "Счёт не найден")

    categories_service.ensure_category_of_type(session, payload.category_id, CategoryType.EXPENSE)

    occurred_at = payload.occurred_at or datetime.now(UTC)
    if account.balance < pe.amount:
        raise UnprocessableEntityError("insufficient_funds", "Недостаточно средств на счёте")

    try:
        operation = operations_repository.create(
            session,
            user_id=user_id,
            operation_type=OperationType.EXPENSE,
            amount=pe.amount,
            occurred_at=occurred_at,
            from_account_id=account.id,
            to_account_id=None,
            category_id=payload.category_id,
            comment=payload.comment,
        )
        account.balance -= pe.amount

        pe.status = PlannedExpenseStatus.PAID
        pe.paid_at = datetime.now(UTC)
        pe.paid_operation_id = operation.id

        session.commit()
        session.refresh(pe)
        return pe
    except Exception:
        session.rollback()
        raise


def unpay_planned_expense(
    session: Session, user_id: int, planned_expense_id: int
) -> PlannedExpense:
    pe = get_planned_expense(session, user_id, planned_expense_id)
    if pe.status == PlannedExpenseStatus.PENDING:
        raise ConflictError(
            "planned_expense_not_paid",
            "Запланированный расход не оплачен",
        )

    operation = operations_repository.get_owned(session, user_id, pe.paid_operation_id)
    if operation is None:
        # Нарушение консистентности: pending помечен как paid, но операции нет.
        raise NotFoundError("operation_not_found", "Связанная операция не найдена")

    account = accounts_repository.get_owned(session, user_id, operation.from_account_id)
    if account is None:
        raise NotFoundError("account_not_found", "Счёт не найден")

    try:
        # Сначала снимаем связь и меняем статус — иначе CHECK-constraint
        # "paid требует paid_operation_id" упадёт при удалении операции.
        pe.status = PlannedExpenseStatus.PENDING
        pe.paid_at = None
        pe.paid_operation_id = None
        session.flush()

        account.balance += operation.amount
        session.delete(operation)

        session.commit()
        session.refresh(pe)
        return pe
    except Exception:
        session.rollback()
        raise


def delete_planned_expense(session: Session, user_id: int, planned_expense_id: int) -> None:
    pe = get_planned_expense(session, user_id, planned_expense_id)
    # Для paid связанная операция остаётся в истории — мы удаляем только
    # planned_expense; FK ON DELETE SET NULL сработает, если операция
    # когда-либо будет удалена через API операций (что запрещено при linkage).
    repository.delete(session, pe)
    session.commit()
