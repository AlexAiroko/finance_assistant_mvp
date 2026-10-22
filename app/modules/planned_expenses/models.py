from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlannedExpenseStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"


class PlannedExpense(Base):
    __tablename__ = "planned_expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_planned_expenses_amount_positive"),
        CheckConstraint(
            "("
            "(status = 'pending' AND paid_at IS NULL AND paid_operation_id IS NULL) "
            "OR "
            "(status = 'paid' AND paid_at IS NOT NULL AND paid_operation_id IS NOT NULL)"
            ")",
            name="ck_planned_expenses_paid_consistency",
        ),
        Index("ix_planned_expenses_user_status_due", "user_id", "status", "due_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[PlannedExpenseStatus] = mapped_column(
        PgEnum(
            PlannedExpenseStatus,
            name="planned_expense_status",
            values_callable=lambda e: [m.value for m in e],
            create_type=False,
        ),
        nullable=False,
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_operation_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("operations.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
