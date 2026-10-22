from collections.abc import Callable

from fastapi.testclient import TestClient

EXPENSE_CAT = 3  # groceries
HOUSING_CAT = 6  # housing
INCOME_CAT = 1  # salary


def _create_account(client: TestClient, name: str = "A", balance: str = "1000.00") -> dict:
    r = client.post("/api/accounts", json={"name": name, "balance": balance})
    assert r.status_code == 201, r.text
    return r.json()


def _balance(client: TestClient, account_id: int) -> str:
    r = client.get(f"/api/accounts/{account_id}")
    assert r.status_code == 200
    return r.json()["balance"]


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
    name: str = "Аренда",
    amount: str = "100.00",
    due_date: str = "2026-11-01",
) -> dict:
    r = client.post(
        "/api/planned-expenses",
        json={"name": name, "amount": amount, "due_date": due_date},
    )
    assert r.status_code == 201, r.text
    return r.json()


# --- CRUD ---


def test_create_returns_pending(auth_client: TestClient) -> None:
    pe = _create_pe(auth_client)
    assert pe["status"] == "pending"
    assert pe["paid_at"] is None
    assert pe["paid_operation_id"] is None
    assert pe["amount"] == "100.00"


def test_list_filter_by_status(auth_client: TestClient) -> None:
    acct = _create_account(auth_client, balance="1000.00")
    pe1 = _create_pe(auth_client, name="P1", amount="50.00")
    _create_pe(auth_client, name="P2", amount="60.00")

    auth_client.patch(
        f"/api/planned-expenses/{pe1['id']}/pay",
        json={"account_id": acct["id"], "category_id": EXPENSE_CAT},
    )

    pending = auth_client.get("/api/planned-expenses?status=pending").json()
    paid = auth_client.get("/api/planned-expenses?status=paid").json()
    all_items = auth_client.get("/api/planned-expenses").json()

    assert len(pending) == 1
    assert pending[0]["name"] == "P2"
    assert len(paid) == 1
    assert paid[0]["name"] == "P1"
    assert len(all_items) == 2


def test_list_invalid_status_422(auth_client: TestClient) -> None:
    r = auth_client.get("/api/planned-expenses?status=invalid")
    assert r.status_code == 422


def test_get_one(auth_client: TestClient) -> None:
    pe = _create_pe(auth_client)
    r = auth_client.get(f"/api/planned-expenses/{pe['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == pe["id"]


def test_patch_pending(auth_client: TestClient) -> None:
    pe = _create_pe(auth_client)
    r = auth_client.patch(
        f"/api/planned-expenses/{pe['id']}",
        json={"name": "Новое", "amount": "200.00"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Новое"
    assert r.json()["amount"] == "200.00"


def test_patch_empty_rejected(auth_client: TestClient) -> None:
    pe = _create_pe(auth_client)
    r = auth_client.patch(f"/api/planned-expenses/{pe['id']}", json={})
    assert r.status_code == 422


def test_patch_paid_rejected(auth_client: TestClient) -> None:
    acct = _create_account(auth_client, balance="1000.00")
    pe = _create_pe(auth_client, amount="100.00")
    auth_client.patch(
        f"/api/planned-expenses/{pe['id']}/pay",
        json={"account_id": acct["id"], "category_id": EXPENSE_CAT},
    )
    r = auth_client.patch(f"/api/planned-expenses/{pe['id']}", json={"amount": "200.00"})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "planned_expense_already_paid"


def test_foreign_pe_404(auth_client: TestClient, make_client: Callable[[], TestClient]) -> None:
    pe = _create_pe(auth_client)
    other = _login_user(make_client, "other@example.com")

    assert other.get(f"/api/planned-expenses/{pe['id']}").status_code == 404
    assert (
        other.patch(f"/api/planned-expenses/{pe['id']}", json={"amount": "1.00"}).status_code == 404
    )
    assert other.delete(f"/api/planned-expenses/{pe['id']}").status_code == 404


# --- pay ---


def test_pay_creates_operation_and_decreases_balance(
    auth_client: TestClient,
) -> None:
    acct = _create_account(auth_client, balance="1000.00")
    pe = _create_pe(auth_client, amount="300.00")

    r = auth_client.patch(
        f"/api/planned-expenses/{pe['id']}/pay",
        json={"account_id": acct["id"], "category_id": HOUSING_CAT},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "paid"
    assert body["paid_at"] is not None
    assert body["paid_operation_id"] is not None

    assert _balance(auth_client, acct["id"]) == "700.00"

    op = auth_client.get(f"/api/operations/{body['paid_operation_id']}").json()
    assert op["type"] == "expense"
    assert op["amount"] == "300.00"
    assert op["from_account_id"] == acct["id"]
    assert op["category_id"] == HOUSING_CAT


def test_pay_already_paid_409(auth_client: TestClient) -> None:
    acct = _create_account(auth_client, balance="1000.00")
    pe = _create_pe(auth_client)
    auth_client.patch(
        f"/api/planned-expenses/{pe['id']}/pay",
        json={"account_id": acct["id"], "category_id": EXPENSE_CAT},
    )

    r = auth_client.patch(
        f"/api/planned-expenses/{pe['id']}/pay",
        json={"account_id": acct["id"], "category_id": EXPENSE_CAT},
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "planned_expense_already_paid"


def test_pay_insufficient_funds(auth_client: TestClient) -> None:
    acct = _create_account(auth_client, balance="50.00")
    pe = _create_pe(auth_client, amount="100.00")

    r = auth_client.patch(
        f"/api/planned-expenses/{pe['id']}/pay",
        json={"account_id": acct["id"], "category_id": EXPENSE_CAT},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "insufficient_funds"
    assert _balance(auth_client, acct["id"]) == "50.00"

    fetched = auth_client.get(f"/api/planned-expenses/{pe['id']}").json()
    assert fetched["status"] == "pending"
    assert fetched["paid_operation_id"] is None


def test_pay_income_category_rejected(auth_client: TestClient) -> None:
    acct = _create_account(auth_client, balance="1000.00")
    pe = _create_pe(auth_client)
    r = auth_client.patch(
        f"/api/planned-expenses/{pe['id']}/pay",
        json={"account_id": acct["id"], "category_id": INCOME_CAT},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "validation_error"


def test_pay_foreign_account_404(
    auth_client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    pe = _create_pe(auth_client)
    other = _login_user(make_client, "other@example.com")
    other_acct = _create_account(other, name="Other")

    r = auth_client.patch(
        f"/api/planned-expenses/{pe['id']}/pay",
        json={"account_id": other_acct["id"], "category_id": EXPENSE_CAT},
    )
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "account_not_found"


# --- unpay ---


def test_unpay_restores_balance_and_status(auth_client: TestClient) -> None:
    acct = _create_account(auth_client, balance="1000.00")
    pe = _create_pe(auth_client, amount="300.00")
    pay = auth_client.patch(
        f"/api/planned-expenses/{pe['id']}/pay",
        json={"account_id": acct["id"], "category_id": EXPENSE_CAT},
    ).json()
    op_id = pay["paid_operation_id"]
    assert _balance(auth_client, acct["id"]) == "700.00"

    r = auth_client.patch(f"/api/planned-expenses/{pe['id']}/unpay")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "pending"
    assert body["paid_at"] is None
    assert body["paid_operation_id"] is None

    assert _balance(auth_client, acct["id"]) == "1000.00"
    assert auth_client.get(f"/api/operations/{op_id}").status_code == 404


def test_unpay_pending_409(auth_client: TestClient) -> None:
    pe = _create_pe(auth_client)
    r = auth_client.patch(f"/api/planned-expenses/{pe['id']}/unpay")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "planned_expense_not_paid"


# --- delete ---


def test_delete_pending(auth_client: TestClient) -> None:
    pe = _create_pe(auth_client)
    r = auth_client.delete(f"/api/planned-expenses/{pe['id']}")
    assert r.status_code == 204
    assert auth_client.get(f"/api/planned-expenses/{pe['id']}").status_code == 404


def test_delete_paid_keeps_operation(auth_client: TestClient) -> None:
    acct = _create_account(auth_client, balance="1000.00")
    pe = _create_pe(auth_client, amount="300.00")
    pay = auth_client.patch(
        f"/api/planned-expenses/{pe['id']}/pay",
        json={"account_id": acct["id"], "category_id": EXPENSE_CAT},
    ).json()
    op_id = pay["paid_operation_id"]

    r = auth_client.delete(f"/api/planned-expenses/{pe['id']}")
    assert r.status_code == 204
    assert auth_client.get(f"/api/planned-expenses/{pe['id']}").status_code == 404

    # Операция осталась в истории, баланс не изменился
    op = auth_client.get(f"/api/operations/{op_id}")
    assert op.status_code == 200
    assert op.json()["amount"] == "300.00"
    assert _balance(auth_client, acct["id"]) == "700.00"


# --- linkage через API ---


def test_linked_operation_protected_then_released(auth_client: TestClient) -> None:
    acct = _create_account(auth_client, balance="1000.00")
    pe = _create_pe(auth_client, amount="100.00")
    pay = auth_client.patch(
        f"/api/planned-expenses/{pe['id']}/pay",
        json={"account_id": acct["id"], "category_id": EXPENSE_CAT},
    ).json()
    op_id = pay["paid_operation_id"]

    # Пока paid — операция защищена
    patch_r = auth_client.patch(f"/api/operations/{op_id}", json={"amount": "50.00"})
    assert patch_r.status_code == 409
    assert patch_r.json()["detail"]["code"] == "operation_linked_to_planned_expense"
    del_r = auth_client.delete(f"/api/operations/{op_id}")
    assert del_r.status_code == 409
    assert del_r.json()["detail"]["code"] == "operation_linked_to_planned_expense"

    # unpay удаляет операцию — теперь 404 (а не 409)
    auth_client.patch(f"/api/planned-expenses/{pe['id']}/unpay")
    assert auth_client.get(f"/api/operations/{op_id}").status_code == 404
