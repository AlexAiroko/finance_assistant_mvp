"""seed predefined categories

Revision ID: 0002_seed_categories
Revises: 0001_initial_schema
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_seed_categories"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CATEGORIES: list[dict[str, str]] = [
    {"code": "salary", "name": "Зарплата", "type": "income"},
    {"code": "other_income", "name": "Прочие доходы", "type": "income"},
    {"code": "groceries", "name": "Продукты", "type": "expense"},
    {"code": "cafes", "name": "Кафе и рестораны", "type": "expense"},
    {"code": "transport", "name": "Транспорт", "type": "expense"},
    {"code": "housing", "name": "Жильё и коммунальные услуги", "type": "expense"},
    {"code": "communication", "name": "Связь и интернет", "type": "expense"},
    {"code": "entertainment", "name": "Развлечения", "type": "expense"},
    {"code": "health", "name": "Здоровье", "type": "expense"},
    {"code": "other_expense", "name": "Прочие расходы", "type": "expense"},
]

_CATEGORY_CODES: list[str] = [item["code"] for item in _CATEGORIES]


def upgrade() -> None:
    categories_table = sa.table(
        "categories",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("type", sa.String),
    )
    op.bulk_insert(categories_table, _CATEGORIES)


def downgrade() -> None:
    categories_table = sa.table(
        "categories",
        sa.column("code", sa.String),
    )
    op.execute(categories_table.delete().where(categories_table.c.code.in_(_CATEGORY_CODES)))
