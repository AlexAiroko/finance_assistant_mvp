from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.planned_expenses.models import PlannedExpense, PlannedExpenseStatus


def get_owned(session: Session, user_id: int, planned_expense_id: int) -> PlannedExpense | None:
    stmt = select(PlannedExpense).where(
        PlannedExpense.id == planned_expense_id,
        PlannedExpense.user_id == user_id,
    )
    return session.execute(stmt).scalar_one_or_none()


def list_by_user(
    session: Session,
    user_id: int,
    status: PlannedExpenseStatus | None = None,
) -> list[PlannedExpense]:
    stmt = select(PlannedExpense).where(PlannedExpense.user_id == user_id)
    if status is not None:
        stmt = stmt.where(PlannedExpense.status == status)
    stmt = stmt.order_by(PlannedExpense.due_date.asc(), PlannedExpense.id.asc())
    return list(session.execute(stmt).scalars().all())


def list_pending(session: Session, user_id: int) -> list[PlannedExpense]:
    stmt = (
        select(PlannedExpense)
        .where(
            PlannedExpense.user_id == user_id,
            PlannedExpense.status == PlannedExpenseStatus.PENDING,
        )
        .order_by(PlannedExpense.due_date.asc(), PlannedExpense.id.asc())
    )
    return list(session.execute(stmt).scalars().all())


def create(
    session: Session,
    *,
    user_id: int,
    name: str,
    amount: Decimal,
    due_date: date,
) -> PlannedExpense:
    planned_expense = PlannedExpense(
        user_id=user_id,
        name=name,
        amount=amount,
        due_date=due_date,
        status=PlannedExpenseStatus.PENDING,
    )
    session.add(planned_expense)
    session.flush()
    return planned_expense


def delete(session: Session, planned_expense: PlannedExpense) -> None:
    session.delete(planned_expense)


def exists_by_paid_operation_id(session: Session, operation_id: int) -> bool:
    stmt = (
        select(PlannedExpense.id).where(PlannedExpense.paid_operation_id == operation_id).limit(1)
    )
    return session.execute(stmt).first() is not None
