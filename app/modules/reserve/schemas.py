from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.core.types import Money, NonNegativeMoney


class ReserveUpdate(BaseModel):
    amount: NonNegativeMoney


class ReserveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    amount: Money
    currency: Literal["RUB"] = "RUB"
    created_at: datetime
    updated_at: datetime
