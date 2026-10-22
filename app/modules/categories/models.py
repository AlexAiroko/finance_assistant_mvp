from enum import StrEnum

from sqlalchemy import BigInteger, String
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CategoryType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[CategoryType] = mapped_column(
        PgEnum(
            CategoryType,
            name="category_type",
            values_callable=lambda e: [m.value for m in e],
            create_type=False,
        ),
        nullable=False,
    )
