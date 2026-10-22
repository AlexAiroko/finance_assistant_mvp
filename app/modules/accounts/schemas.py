from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.types import Money, NonNegativeMoney


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    balance: NonNegativeMoney

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Название счёта не может быть пустым")
        return stripped


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    balance: NonNegativeMoney | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("Название счёта не может быть пустым")
        return stripped

    @model_validator(mode="after")
    def _check_partial_update(self) -> "AccountUpdate":
        if not self.model_fields_set:
            raise ValueError("Должно быть передано хотя бы одно поле")
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"Поле {field} не может быть null")
        return self


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    balance: Money
    created_at: datetime
    updated_at: datetime
