from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OperationType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class Operation(Base):
    __tablename__ = "operations"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_operations_amount_positive"),
        CheckConstraint(
            "("
            "(type IN ('income', 'expense') AND from_account_id IS NOT NULL "
            "AND to_account_id IS NULL AND category_id IS NOT NULL) "
            "OR "
            "(type = 'transfer' AND from_account_id IS NOT NULL "
            "AND to_account_id IS NOT NULL AND from_account_id <> to_account_id "
            "AND category_id IS NULL)"
            ")",
            name="ck_operations_type_fields",
        ),
        Index(
            "ix_operations_user_occurred",
            "user_id",
            text("occurred_at DESC"),
            text("id DESC"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[OperationType] = mapped_column(
        PgEnum(
            OperationType,
            name="operation_type",
            values_callable=lambda e: [m.value for m in e],
            create_type=False,
        ),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    from_account_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("accounts.id"), nullable=True, index=True
    )
    to_account_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("accounts.id"), nullable=True, index=True
    )
    category_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("categories.id"), nullable=True
    )
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
