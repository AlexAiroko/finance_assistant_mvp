from datetime import UTC, datetime, timedelta

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.core.types import Money, PositiveMoney
from app.modules.operations.models import OperationType


class OperationCreate(BaseModel):
    type: OperationType
    amount: PositiveMoney
    occurred_at: AwareDatetime | None = None
    from_account_id: int | None = None
    to_account_id: int | None = None
    category_id: int | None = None
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

    @model_validator(mode="after")
    def _check_fields_by_type(self) -> "OperationCreate":
        if self.type in (OperationType.INCOME, OperationType.EXPENSE):
            if self.from_account_id is None:
                raise ValueError("from_account_id обязателен для income/expense")
            if self.to_account_id is not None:
                raise ValueError("to_account_id недопустим для income/expense")
            if self.category_id is None:
                raise ValueError("category_id обязателен для income/expense")
        elif self.type == OperationType.TRANSFER:
            if self.from_account_id is None:
                raise ValueError("from_account_id обязателен для transfer")
            if self.to_account_id is None:
                raise ValueError("to_account_id обязателен для transfer")
            if self.from_account_id == self.to_account_id:
                raise ValueError("Счета перевода должны различаться")
            if self.category_id is not None:
                raise ValueError("category_id недопустим для transfer")
        return self


class OperationUpdate(BaseModel):
    # type присутствует только для явного отклонения попытки смены типа.
    type: OperationType | None = None
    amount: PositiveMoney | None = None
    occurred_at: AwareDatetime | None = None
    from_account_id: int | None = None
    to_account_id: int | None = None
    category_id: int | None = None
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

    @model_validator(mode="after")
    def _check_update_semantics(self) -> "OperationUpdate":
        if not self.model_fields_set:
            raise ValueError("Должно быть передано хотя бы одно поле")
        if "type" in self.model_fields_set:
            raise ValueError("Изменение типа операции недопустимо")
        for required_field in ("amount", "occurred_at", "from_account_id"):
            if required_field in self.model_fields_set and getattr(self, required_field) is None:
                raise ValueError(f"Поле {required_field} не может быть null")
        return self


class OperationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: OperationType
    amount: Money
    occurred_at: datetime
    from_account_id: int | None
    to_account_id: int | None
    category_id: int | None
    comment: str | None
    created_at: datetime
    updated_at: datetime


class OperationListResponse(BaseModel):
    items: list[OperationResponse]
    total: int
    limit: int
    offset: int
