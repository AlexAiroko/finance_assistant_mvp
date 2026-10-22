from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.core.types import Money
from app.modules.planned_expenses.models import PlannedExpenseStatus


class DashboardAccountItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    balance: Money


class DashboardUpcomingExpenseItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    amount: Money
    due_date: date
    status: PlannedExpenseStatus


class DashboardResponse(BaseModel):
    total_balance: Money
    upcoming_expenses_total: Money
    reserve_amount: Money
    available_amount: Money
    currency: Literal["RUB"] = "RUB"
    accounts: list[DashboardAccountItem]
    upcoming_expenses: list[DashboardUpcomingExpenseItem]
