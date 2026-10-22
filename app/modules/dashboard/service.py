from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.accounts import repository as accounts_repository
from app.modules.dashboard.schemas import (
    DashboardAccountItem,
    DashboardResponse,
    DashboardUpcomingExpenseItem,
)
from app.modules.planned_expenses import repository as planned_expenses_repository
from app.modules.reserve import repository as reserve_repository

_UPCOMING_DISPLAY_LIMIT = 5


def get_dashboard(session: Session, user_id: int) -> DashboardResponse:
    """Собирает агрегаты главного экрана.

    Все три источника читаются один раз в рамках одной сессии, суммы
    вычисляются в Python по уже прочитанным спискам. Это даёт согласованный
    снимок для агрегатов и списков без явного уровня изоляции: если
    upcoming_expenses_total включает запись, она гарантированно попадёт
    в top-5-срез (или осознанно не попадёт — если она дальше пятой по
    due_date, но это ожидаемое поведение лимита отображения).
    """
    accounts = accounts_repository.list_by_user(session, user_id)
    total_balance = sum((a.balance for a in accounts), Decimal("0.00"))

    pending_expenses = planned_expenses_repository.list_pending(session, user_id)
    upcoming_expenses_total = sum((e.amount for e in pending_expenses), Decimal("0.00"))
    upcoming_expenses = pending_expenses[:_UPCOMING_DISPLAY_LIMIT]

    reserve = reserve_repository.get_by_user_id(session, user_id)
    reserve_amount = reserve.amount if reserve is not None else Decimal("0.00")

    available_amount = total_balance - upcoming_expenses_total - reserve_amount

    return DashboardResponse(
        total_balance=total_balance,
        upcoming_expenses_total=upcoming_expenses_total,
        reserve_amount=reserve_amount,
        available_amount=available_amount,
        accounts=[DashboardAccountItem.model_validate(a) for a in accounts],
        upcoming_expenses=[
            DashboardUpcomingExpenseItem.model_validate(e) for e in upcoming_expenses
        ],
    )
