from datetime import UTC, date, datetime, timedelta

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.core.types import Money, PositiveMoney
from app.modules.planned_expenses.models import PlannedExpenseStatus


class PlannedExpenseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    amount: PositiveMoney
    due_date: date

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Название не может быть пустым")
        return stripped


class PlannedExpenseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    amount: PositiveMoney | None = None
    due_date: date | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("Название не может быть пустым")
        return stripped

    @model_validator(mode="after")
    def _check_partial_update(self) -> "PlannedExpenseUpdate":
        if not self.model_fields_set:
            raise ValueError("Должно быть передано хотя бы одно поле")
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"Поле {field} не может быть null")
        return self


class PlannedExpensePayRequest(BaseModel):
    account_id: int
    category_id: int
    occurred_at: AwareDatetime | None = None
    comment: str | None = Field(default=None, max_length=500)

    @field_validator("occurred_at")
    @classmethod
    def _check_not_future(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        max_allowed = datetime.now(UTC) + timedelta(minutes=5)
        if value > max_allowed:
            raise ValueError("occurred_at не может быть в будущем")
        return value


class PlannedExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    amount: Money
    due_date: date
    status: PlannedExpenseStatus
    paid_at: datetime | None
    paid_operation_id: int | None
    created_at: datetime
    updated_at: datetime
