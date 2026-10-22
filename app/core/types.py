from decimal import Decimal
from typing import Annotated

from pydantic import Field, PlainSerializer

# Форматирование денежных значений в ответах API: строка с двумя знаками.
Money = Annotated[
    Decimal,
    PlainSerializer(lambda v: f"{v:.2f}", return_type=str),
]

# Входные денежные значения: неотрицательные, не более 12 цифр, не более 2 знаков.
NonNegativeMoney = Annotated[Money, Field(ge=0, max_digits=12, decimal_places=2)]

# Входные денежные значения: строго положительные (для сумм операций и planned expense).
PositiveMoney = Annotated[Money, Field(gt=0, max_digits=12, decimal_places=2)]
