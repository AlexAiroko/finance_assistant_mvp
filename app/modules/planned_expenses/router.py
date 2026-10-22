from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.planned_expenses import service
from app.modules.planned_expenses.models import PlannedExpense, PlannedExpenseStatus
from app.modules.planned_expenses.schemas import (
    PlannedExpenseCreate,
    PlannedExpensePayRequest,
    PlannedExpenseResponse,
    PlannedExpenseUpdate,
)

router = APIRouter(prefix="/api/planned-expenses", tags=["planned-expenses"])


@router.get("", response_model=list[PlannedExpenseResponse])
def list_planned_expenses(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    status_filter: Annotated[PlannedExpenseStatus | None, Query(alias="status")] = None,
) -> list[PlannedExpense]:
    return service.list_planned_expenses(session, current_user.id, status=status_filter)


@router.post(
    "",
    response_model=PlannedExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_planned_expense(
    payload: PlannedExpenseCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PlannedExpense:
    return service.create_planned_expense(session, current_user.id, payload)


@router.get("/{planned_expense_id}", response_model=PlannedExpenseResponse)
def get_planned_expense(
    planned_expense_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PlannedExpense:
    return service.get_planned_expense(session, current_user.id, planned_expense_id)


@router.patch("/{planned_expense_id}", response_model=PlannedExpenseResponse)
def update_planned_expense(
    planned_expense_id: int,
    payload: PlannedExpenseUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PlannedExpense:
    return service.update_planned_expense(session, current_user.id, planned_expense_id, payload)


@router.patch("/{planned_expense_id}/pay", response_model=PlannedExpenseResponse)
def pay_planned_expense(
    planned_expense_id: int,
    payload: PlannedExpensePayRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PlannedExpense:
    return service.pay_planned_expense(session, current_user.id, planned_expense_id, payload)


@router.patch("/{planned_expense_id}/unpay", response_model=PlannedExpenseResponse)
def unpay_planned_expense(
    planned_expense_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PlannedExpense:
    return service.unpay_planned_expense(session, current_user.id, planned_expense_id)


@router.delete("/{planned_expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_planned_expense(
    planned_expense_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    service.delete_planned_expense(session, current_user.id, planned_expense_id)
