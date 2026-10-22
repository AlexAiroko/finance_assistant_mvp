"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. ENUM-типы — до таблиц.
    postgresql.ENUM("income", "expense", name="category_type").create(bind, checkfirst=True)
    postgresql.ENUM("income", "expense", "transfer", name="operation_type").create(
        bind, checkfirst=True
    )
    postgresql.ENUM("pending", "paid", name="planned_expense_status").create(bind, checkfirst=True)

    # 2. users (нет FK-зависимостей).
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    # 3. categories (нет FK).
    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM("income", "expense", name="category_type", create_type=False),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_categories_code"),
    )

    # 4. accounts (FK -> users).
    op.create_table(
        "accounts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("balance", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("balance >= 0", name="ck_accounts_balance_non_negative"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])

    # 5. operations (FK -> users, accounts, categories).
    op.create_table(
        "operations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "type",
            postgresql.ENUM(
                "income", "expense", "transfer", name="operation_type", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("from_account_id", sa.BigInteger(), nullable=True),
        sa.Column("to_account_id", sa.BigInteger(), nullable=True),
        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column("comment", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name="ck_operations_amount_positive"),
        sa.CheckConstraint(
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["to_account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_operations_from_account_id", "operations", ["from_account_id"])
    op.create_index("ix_operations_to_account_id", "operations", ["to_account_id"])
    op.execute(
        "CREATE INDEX ix_operations_user_occurred "
        "ON operations (user_id, occurred_at DESC, id DESC)"
    )

    # 6. reserves (FK -> users, UNIQUE user_id).
    op.create_table(
        "reserves",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount >= 0", name="ck_reserves_amount_non_negative"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_reserves_user_id"),
    )

    # 7. planned_expenses (FK -> users, operations).
    op.create_table(
        "planned_expenses",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("pending", "paid", name="planned_expense_status", create_type=False),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_operation_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name="ck_planned_expenses_amount_positive"),
        sa.CheckConstraint(
            "("
            "(status = 'pending' AND paid_at IS NULL AND paid_operation_id IS NULL) "
            "OR "
            "(status = 'paid' AND paid_at IS NOT NULL AND paid_operation_id IS NOT NULL)"
            ")",
            name="ck_planned_expenses_paid_consistency",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paid_operation_id"], ["operations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_planned_expenses_user_id", "planned_expenses", ["user_id"])
    op.create_index(
        "ix_planned_expenses_user_status_due",
        "planned_expenses",
        ["user_id", "status", "due_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_planned_expenses_user_status_due", table_name="planned_expenses")
    op.drop_index("ix_planned_expenses_user_id", table_name="planned_expenses")
    op.drop_table("planned_expenses")

    op.drop_table("reserves")

    op.execute("DROP INDEX IF EXISTS ix_operations_user_occurred")
    op.drop_index("ix_operations_to_account_id", table_name="operations")
    op.drop_index("ix_operations_from_account_id", table_name="operations")
    op.drop_table("operations")

    op.drop_index("ix_accounts_user_id", table_name="accounts")
    op.drop_table("accounts")

    op.drop_table("categories")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS planned_expense_status")
    op.execute("DROP TYPE IF EXISTS operation_type")
    op.execute("DROP TYPE IF EXISTS category_type")
