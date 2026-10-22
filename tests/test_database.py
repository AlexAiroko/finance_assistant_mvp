from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.modules.accounts.models import Account
from app.modules.auth.models import User
from app.modules.categories.models import Category
from app.modules.operations.models import Operation
from app.modules.planned_expenses.models import PlannedExpense
from app.modules.reserve.models import Reserve


def _user(db_session: Session) -> User:
    return db_session.execute(select(User)).scalar_one()


def _account(
    db_session: Session, user_id: int, name: str = "A", balance: str = "1000.00"
) -> Account:
    acc = Account(user_id=user_id, name=name, balance=Decimal(balance))
    db_session.add(acc)
    db_session.flush()
    return acc


def _category(db_session: Session, code: str = "salary") -> Category:
    return db_session.execute(select(Category).where(Category.code == code)).scalar_one()


# --- CHECK-constraints ---


def test_check_account_balance_non_negative(auth_client: TestClient, db_session: Session) -> None:
    user = _user(db_session)
    with pytest.raises(DBAPIError):
        db_session.add(Account(user_id=user.id, name="X", balance=Decimal("-1.00")))
        db_session.commit()
    db_session.rollback()


def test_check_operation_amount_positive(auth_client: TestClient, db_session: Session) -> None:
    user = _user(db_session)
    acc = _account(db_session, user.id)
    cat = _category(db_session)
    with pytest.raises(DBAPIError):
        db_session.add(
            Operation(
                user_id=user.id,
                type="income",
                amount=Decimal("0.00"),
                occurred_at=datetime.now(UTC),
                from_account_id=acc.id,
                category_id=cat.id,
            )
        )
        db_session.commit()
    db_session.rollback()


def test_check_operation_income_requires_category(
    auth_client: TestClient, db_session: Session
) -> None:
    user = _user(db_session)
    acc = _account(db_session, user.id)
    with pytest.raises(DBAPIError):
        db_session.add(
            Operation(
                user_id=user.id,
                type="income",
                amount=Decimal("100.00"),
                occurred_at=datetime.now(UTC),
                from_account_id=acc.id,
                category_id=None,
            )
        )
        db_session.commit()
    db_session.rollback()


def test_check_operation_income_forbids_to_account(
    auth_client: TestClient, db_session: Session
) -> None:
    user = _user(db_session)
    acc = _account(db_session, user.id, name="A")
    second = _account(db_session, user.id, name="B", balance="0.00")
    cat = _category(db_session)
    with pytest.raises(DBAPIError):
        db_session.add(
            Operation(
                user_id=user.id,
                type="income",
                amount=Decimal("100.00"),
                occurred_at=datetime.now(UTC),
                from_account_id=acc.id,
                to_account_id=second.id,
                category_id=cat.id,
            )
        )
        db_session.commit()
    db_session.rollback()


def test_check_operation_transfer_requires_distinct_accounts(
    auth_client: TestClient, db_session: Session
) -> None:
    user = _user(db_session)
    acc = _account(db_session, user.id)
    with pytest.raises(DBAPIError):
        db_session.add(
            Operation(
                user_id=user.id,
                type="transfer",
                amount=Decimal("100.00"),
                occurred_at=datetime.now(UTC),
                from_account_id=acc.id,
                to_account_id=acc.id,
            )
        )
        db_session.commit()
    db_session.rollback()


def test_check_operation_transfer_forbids_category(
    auth_client: TestClient, db_session: Session
) -> None:
    user = _user(db_session)
    acc = _account(db_session, user.id, name="A")
    second = _account(db_session, user.id, name="B", balance="0.00")
    cat = _category(db_session)
    with pytest.raises(DBAPIError):
        db_session.add(
            Operation(
                user_id=user.id,
                type="transfer",
                amount=Decimal("100.00"),
                occurred_at=datetime.now(UTC),
                from_account_id=acc.id,
                to_account_id=second.id,
                category_id=cat.id,
            )
        )
        db_session.commit()
    db_session.rollback()


def test_check_planned_expense_amount_positive(
    auth_client: TestClient, db_session: Session
) -> None:
    user = _user(db_session)
    with pytest.raises(DBAPIError):
        db_session.add(
            PlannedExpense(
                user_id=user.id,
                name="X",
                amount=Decimal("0.00"),
                due_date=date(2026, 12, 1),
                status="pending",
            )
        )
        db_session.commit()
    db_session.rollback()


def test_check_planned_expense_paid_consistency(
    auth_client: TestClient, db_session: Session
) -> None:
    user = _user(db_session)
    with pytest.raises(DBAPIError):
        db_session.add(
            PlannedExpense(
                user_id=user.id,
                name="X",
                amount=Decimal("100.00"),
                due_date=date(2026, 12, 1),
                status="paid",
                paid_at=None,
                paid_operation_id=None,
            )
        )
        db_session.commit()
    db_session.rollback()


def test_check_reserve_amount_non_negative(auth_client: TestClient, db_session: Session) -> None:
    user = _user(db_session)
    existing = db_session.execute(select(Reserve).where(Reserve.user_id == user.id)).scalar_one()
    db_session.delete(existing)
    db_session.flush()

    with pytest.raises(DBAPIError):
        db_session.add(Reserve(user_id=user.id, amount=Decimal("-1.00")))
        db_session.commit()
    db_session.rollback()


# --- ENUM ---


def test_enum_operation_type_rejects_invalid(auth_client: TestClient, db_session: Session) -> None:
    user = _user(db_session)
    acc = _account(db_session, user.id)
    cat = _category(db_session)
    with pytest.raises(DBAPIError):
        db_session.add(
            Operation(
                user_id=user.id,
                type="invalid",
                amount=Decimal("100.00"),
                occurred_at=datetime.now(UTC),
                from_account_id=acc.id,
                category_id=cat.id,
            )
        )
        db_session.commit()
    db_session.rollback()


def test_enum_planned_expense_status_rejects_invalid(
    auth_client: TestClient, db_session: Session
) -> None:
    user = _user(db_session)
    with pytest.raises(DBAPIError):
        db_session.add(
            PlannedExpense(
                user_id=user.id,
                name="X",
                amount=Decimal("100.00"),
                due_date=date(2026, 12, 1),
                status="invalid",
            )
        )
        db_session.commit()
    db_session.rollback()


# --- Транзакции ---


def test_insufficient_funds_does_not_leak_partial_data(
    auth_client: TestClient,
) -> None:
    acct = auth_client.post("/api/accounts", json={"name": "A", "balance": "100.00"}).json()

    total_before = auth_client.get("/api/operations").json()["total"]
    balance_before = auth_client.get(f"/api/accounts/{acct['id']}").json()["balance"]

    r = auth_client.post(
        "/api/operations",
        json={
            "type": "expense",
            "amount": "200.00",
            "from_account_id": acct["id"],
            "category_id": 3,
        },
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "insufficient_funds"

    total_after = auth_client.get("/api/operations").json()["total"]
    balance_after = auth_client.get(f"/api/accounts/{acct['id']}").json()["balance"]
    assert total_before == total_after == 0
    assert balance_before == balance_after == "100.00"


def test_delete_operation_via_sql_blocked_by_planned_expense_check(
    auth_client: TestClient, db_session: Session
) -> None:
    """Прямой DELETE операции, на которую ссылается paid planned_expense,
    блокируется CHECK-constraint:
    FK ON DELETE SET NULL обнулит paid_operation_id, а CHECK требует NOT NULL
    при status='paid'. Через API до этого не дойти (409 linkage), здесь
    подтверждаем, что и БД защищает инвариант.
    """
    acct = auth_client.post("/api/accounts", json={"name": "A", "balance": "1000.00"}).json()
    pe = auth_client.post(
        "/api/planned-expenses",
        json={"name": "P", "amount": "100.00", "due_date": "2026-12-01"},
    ).json()
    pay = auth_client.patch(
        f"/api/planned-expenses/{pe['id']}/pay",
        json={"account_id": acct["id"], "category_id": 6},
    ).json()
    op_id = pay["paid_operation_id"]

    with pytest.raises(DBAPIError):
        db_session.execute(text("DELETE FROM operations WHERE id = :id"), {"id": op_id})
        db_session.commit()
    db_session.rollback()

    row = db_session.execute(
        text("SELECT id FROM operations WHERE id = :id"), {"id": op_id}
    ).first()
    assert row is not None
