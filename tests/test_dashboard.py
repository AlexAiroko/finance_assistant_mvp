from collections.abc import Callable
from decimal import Decimal

from fastapi.testclient import TestClient

INCOME_CAT = 1  # salary
EXPENSE_CAT = 3  # groceries
HOUSING_CAT = 6  # housing


def _create_account(client: TestClient, name: str = "A", balance: str = "0.00") -> dict:
    r = client.post("/api/accounts", json={"name": name, "balance": balance})
    assert r.status_code == 201, r.text
    return r.json()


def _login_user(make_client: Callable[[], TestClient], email: str) -> TestClient:
    c = make_client()
    r = c.post(
        "/api/auth/register",
        json={"email": email, "password": "strong_password_123"},
    )
    assert r.status_code == 201, r.text
    r = c.post(
        "/api/auth/login",
        json={"email": email, "password": "strong_password_123"},
    )
    assert r.status_code == 200, r.text
    return c


def _create_pe(
    client: TestClient,
    name: str,
    amount: str,
    due_date: str,
) -> dict:
    r = client.post(
        "/api/planned-expenses",
        json={"name": name, "amount": amount, "due_date": due_date},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _dashboard(client: TestClient) -> dict:
    r = client.get("/api/dashboard")
    assert r.status_code == 200, r.text
    return r.json()


def _assert_dashboard_amounts(
    body: dict,
    *,
    total: str,
    upcoming: str,
    reserve: str,
    available: str,
) -> None:
    """Сверяет все четыре денежных поля и формулу доступной суммы."""
    assert body["total_balance"] == total
    assert body["upcoming_expenses_total"] == upcoming
    assert body["reserve_amount"] == reserve
    assert body["available_amount"] == available
    assert body["currency"] == "RUB"
    expected = Decimal(total) - Decimal(upcoming) - Decimal(reserve)
    assert Decimal(available) == expected


# --- A. Пустое состояние ---


def test_empty_state(auth_client: TestClient) -> None:
    body = _dashboard(auth_client)
    _assert_dashboard_amounts(body, total="0.00", upcoming="0.00", reserve="0.00", available="0.00")
    assert body["accounts"] == []
    assert body["upcoming_expenses"] == []


# --- B. Счета и операции ---


def test_accounts_and_operations(auth_client: TestClient) -> None:
    a = _create_account(auth_client, name="A", balance="10000.00")
    b = _create_account(auth_client, name="B", balance="5000.00")

    auth_client.post(
        "/api/operations",
        json={
            "type": "income",
            "amount": "5000.00",
            "from_account_id": a["id"],
            "category_id": INCOME_CAT,
        },
    )
    auth_client.post(
        "/api/operations",
        json={
            "type": "expense",
            "amount": "3000.00",
            "from_account_id": a["id"],
            "category_id": EXPENSE_CAT,
        },
    )
    auth_client.post(
        "/api/operations",
        json={
            "type": "transfer",
            "amount": "2000.00",
            "from_account_id": a["id"],
            "to_account_id": b["id"],
        },
    )

    body = _dashboard(auth_client)
    _assert_dashboard_amounts(
        body,
        total="17000.00",
        upcoming="0.00",
        reserve="0.00",
        available="17000.00",
    )
    assert len(body["accounts"]) == 2
    balances = {acc["name"]: acc["balance"] for acc in body["accounts"]}
    assert balances == {"A": "10000.00", "B": "7000.00"}


# --- C. Pending уменьшает available ---


def test_pending_reduces_available(auth_client: TestClient) -> None:
    _create_account(auth_client, balance="17000.00")
    _create_pe(auth_client, name="Аренда", amount="5000.00", due_date="2026-11-01")
    _create_pe(auth_client, name="Связь", amount="3000.00", due_date="2026-11-15")

    body = _dashboard(auth_client)
    _assert_dashboard_amounts(
        body,
        total="17000.00",
        upcoming="8000.00",
        reserve="0.00",
        available="9000.00",
    )
    assert len(body["upcoming_expenses"]) == 2
    names_in_order = [e["name"] for e in body["upcoming_expenses"]]
    assert names_in_order == ["Аренда", "Связь"]


# --- D. Резерв уменьшает available ---


def test_reserve_reduces_available(auth_client: TestClient) -> None:
    _create_account(auth_client, balance="17000.00")
    _create_pe(auth_client, name="Аренда", amount="5000.00", due_date="2026-11-01")
    _create_pe(auth_client, name="Связь", amount="3000.00", due_date="2026-11-15")
    auth_client.put("/api/reserve", json={"amount": "4000.00"})

    body = _dashboard(auth_client)
    _assert_dashboard_amounts(
        body,
        total="17000.00",
        upcoming="8000.00",
        reserve="4000.00",
        available="5000.00",
    )


# --- E. Оплата не меняет available (ключевая проверка) ---


def test_pay_does_not_change_available(auth_client: TestClient) -> None:
    acct = _create_account(auth_client, balance="17000.00")
    pe = _create_pe(auth_client, name="Аренда", amount="5000.00", due_date="2026-11-01")
    _create_pe(auth_client, name="Связь", amount="3000.00", due_date="2026-11-15")
    auth_client.put("/api/reserve", json={"amount": "4000.00"})

    before = _dashboard(auth_client)
    assert before["available_amount"] == "5000.00"

    auth_client.patch(
        f"/api/planned-expenses/{pe['id']}/pay",
        json={"account_id": acct["id"], "category_id": HOUSING_CAT},
    )

    after = _dashboard(auth_client)
    # total уменьшился на 5000 (списание), upcoming уменьшился на 5000 (аренда оплачена)
    # available не изменился
    _assert_dashboard_amounts(
        after,
        total="12000.00",
        upcoming="3000.00",
        reserve="4000.00",
        available="5000.00",
    )


# --- F. Unpay восстанавливает состояние ---


def test_unpay_restores_available(auth_client: TestClient) -> None:
    acct = _create_account(auth_client, balance="17000.00")
    pe = _create_pe(auth_client, name="Аренда", amount="5000.00", due_date="2026-11-01")
    _create_pe(auth_client, name="Связь", amount="3000.00", due_date="2026-11-15")
    auth_client.put("/api/reserve", json={"amount": "4000.00"})

    auth_client.patch(
        f"/api/planned-expenses/{pe['id']}/pay",
        json={"account_id": acct["id"], "category_id": HOUSING_CAT},
    )
    auth_client.patch(f"/api/planned-expenses/{pe['id']}/unpay")

    body = _dashboard(auth_client)
    _assert_dashboard_amounts(
        body,
        total="17000.00",
        upcoming="8000.00",
        reserve="4000.00",
        available="5000.00",
    )


# --- G. Отрицательный available ---


def test_negative_available(auth_client: TestClient) -> None:
    _create_account(auth_client, balance="17000.00")
    _create_pe(auth_client, name="Аренда", amount="5000.00", due_date="2026-11-01")
    _create_pe(auth_client, name="Связь", amount="3000.00", due_date="2026-11-15")
    _create_pe(auth_client, name="Крупный", amount="20000.00", due_date="2026-12-01")
    auth_client.put("/api/reserve", json={"amount": "4000.00"})

    body = _dashboard(auth_client)
    _assert_dashboard_amounts(
        body,
        total="17000.00",
        upcoming="28000.00",
        reserve="4000.00",
        available="-15000.00",
    )
    # Отрицательное значение — валидный ответ, не ошибка
    assert Decimal(body["available_amount"]) < 0


# --- H. Top-5 vs сумма всех pending ---


def test_upcoming_expenses_top5_vs_total(auth_client: TestClient) -> None:
    _create_account(auth_client, balance="17000.00")
    _create_pe(auth_client, name="Аренда", amount="5000.00", due_date="2026-11-01")
    _create_pe(auth_client, name="Связь", amount="3000.00", due_date="2026-11-15")
    _create_pe(auth_client, name="E3", amount="100.00", due_date="2026-10-05")
    _create_pe(auth_client, name="E4", amount="100.00", due_date="2026-10-10")
    _create_pe(auth_client, name="E5", amount="100.00", due_date="2026-10-20")
    _create_pe(auth_client, name="E6", amount="100.00", due_date="2026-10-30")

    body = _dashboard(auth_client)
    # 6 pending: 5000 + 3000 + 100*4 = 8400
    # available = 17000 - 8400 - 0 = 8600
    _assert_dashboard_amounts(
        body,
        total="17000.00",
        upcoming="8400.00",
        reserve="0.00",
        available="8600.00",
    )

    # В списке ровно 5, первые по due_date; Связь (2026-11-15) — шестая, не попала
    assert len(body["upcoming_expenses"]) == 5
    names = [e["name"] for e in body["upcoming_expenses"]]
    assert names == ["E3", "E4", "E5", "E6", "Аренда"]
    assert "Связь" not in names

    # Но Связь учтена в сумме
    shown_total = sum(
        (Decimal(e["amount"]) for e in body["upcoming_expenses"]),
        Decimal("0.00"),
    )
    assert shown_total == Decimal("5400.00")  # 5000+100*4
    assert Decimal(body["upcoming_expenses_total"]) == Decimal("8400.00")


# --- I. Изоляция ---


def test_isolation_between_users(
    auth_client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    # user1
    _create_account(auth_client, name="U1-A", balance="17000.00")
    _create_pe(auth_client, name="U1-P", amount="8400.00", due_date="2026-11-01")
    auth_client.put("/api/reserve", json={"amount": "4000.00"})

    # user2
    other = _login_user(make_client, "other@example.com")
    _create_account(other, name="U2-A", balance="500.00")
    _create_pe(other, name="U2-P", amount="200.00", due_date="2026-12-01")
    other.put("/api/reserve", json={"amount": "50.00"})

    u1 = _dashboard(auth_client)
    _assert_dashboard_amounts(
        u1,
        total="17000.00",
        upcoming="8400.00",
        reserve="4000.00",
        available="4600.00",
    )
    assert [a["name"] for a in u1["accounts"]] == ["U1-A"]
    assert [e["name"] for e in u1["upcoming_expenses"]] == ["U1-P"]

    u2 = _dashboard(other)
    _assert_dashboard_amounts(
        u2,
        total="500.00",
        upcoming="200.00",
        reserve="50.00",
        available="250.00",
    )
    assert [a["name"] for a in u2["accounts"]] == ["U2-A"]
    assert [e["name"] for e in u2["upcoming_expenses"]] == ["U2-P"]

    # Контроль: после запросов user2 данные user1 не изменились
    u1_again = _dashboard(auth_client)
    assert u1_again == u1


# --- J. Без cookie ---


def test_dashboard_requires_auth(client: TestClient) -> None:
    r = client.get("/api/dashboard")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "authentication_required"
