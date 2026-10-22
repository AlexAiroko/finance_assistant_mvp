from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.operations.models import Operation, OperationType


def create(
    session: Session,
    *,
    user_id: int,
    operation_type: OperationType,
    amount: Decimal,
    occurred_at: datetime,
    from_account_id: int | None,
    to_account_id: int | None,
    category_id: int | None,
    comment: str | None,
) -> Operation:
    operation = Operation(
        user_id=user_id,
        type=operation_type,
        amount=amount,
        occurred_at=occurred_at,
        from_account_id=from_account_id,
        to_account_id=to_account_id,
        category_id=category_id,
        comment=comment,
    )
    session.add(operation)
    session.flush()
    return operation


def get_owned(session: Session, user_id: int, operation_id: int) -> Operation | None:
    stmt = select(Operation).where(Operation.id == operation_id, Operation.user_id == user_id)
    return session.execute(stmt).scalar_one_or_none()


def list_operations(
    session: Session,
    user_id: int,
    *,
    operation_type: OperationType | None = None,
    account_id: int | None = None,
    category_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Operation], int]:
    base = select(Operation).where(Operation.user_id == user_id)
    if operation_type is not None:
        base = base.where(Operation.type == operation_type)
    if account_id is not None:
        base = base.where(
            or_(
                Operation.from_account_id == account_id,
                Operation.to_account_id == account_id,
            )
        )
    if category_id is not None:
        base = base.where(Operation.category_id == category_id)
    if date_from is not None:
        base = base.where(Operation.occurred_at >= date_from)
    if date_to is not None:
        base = base.where(Operation.occurred_at <= date_to)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = session.execute(count_stmt).scalar_one()

    stmt = (
        base.order_by(Operation.occurred_at.desc(), Operation.id.desc()).limit(limit).offset(offset)
    )
    items = list(session.execute(stmt).scalars().all())
    return items, total


def delete(session: Session, operation: Operation) -> None:
    session.delete(operation)
