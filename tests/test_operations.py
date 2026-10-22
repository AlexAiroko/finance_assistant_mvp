from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

INCOME_CAT = 1  # salary
EXPENSE_CAT = 3  # groceries
HOUSING_CAT = 6  # housing


def _create_account(client: TestClient, name: str = "A", balance: str = "1000.00") -> dict:
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


def _income(
    client: TestClient,
    account_id: int,
    amount: str = "100.00",
    category_id: int = INCOME_CAT,
    **kw,
) -> dict:
    payload = {
        "type": "income",
        "amount": amount,
        "from_account_id": account_id,
        "category_id": category_id,
        **kw,
    }
    r = client.post("/api/operations", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _expense(
    client: TestClient,
    account_id: int,
    amount: str = "100.00",
    category_id: int = EXPENSE_CAT,
    **kw,
) -> dict:
    payload = {
        "type": "expense",
        "amount": amount,
        "from_account_id": account_id,
        "category_id": category_id,
        **kw,
    }
    r = client.post("/api/operations", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _transfer(
    client: TestClient,
    from_id: int,
    to_id: int,
    amount: str = "100.00",
    **kw,
) -> dict:
    payload = {
        "type": "transfer",
        "amount": amount,
        "from_account_id": from_id,
        "to_account_id": to_id,
        **kw,
    }
    r = client.post("/api/operations", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _balance(client: TestClient, account_id: int) -> str:
    r = client.get(f"/api/accounts/{account_id}")
    assert r.status_code == 200
    return r.json()["balance"]


def _total_balance(client: TestClient) -> str:
    accounts = client.get("/api/accounts").json()
    total = sum((Decimal(a["balance"]) for a in accounts), Decimal("0.00"))
    return f"{total:.2f}"


# --- create ---


def test_create_income_increases_balance(auth_client: TestClient) -> None:
    acct = _create_account(auth_client, balance="1000.00")
    op = _income(auth_client, acct["id"], amount="500.00")
    assert op["type"] == "income"
    assert op["amount"] == "500.00"
    assert op["from_account_id"] == acct["id"]
    assert op["to_account_id"] is None
    assert _balance(auth_client, acct["id"]) == "1500.00"


def test_create_expense_decreases_balance(auth_client: TestClient) -> None:
    acct = _create_account(auth_client, balance="1000.00")
    op = _expense(auth_client, acct["id"], amount="300.00")
    assert op["to_account_id"] is None
    assert op["category_id"] == EXPENSE_CAT
    assert _balance(auth_client, acct["id"]) == "700.00"


def test_create_transfer_preserves_total_balance(auth_client: TestClient) -> None:
    a = _create_account(auth_client, name="A", balance="1000.00")
    b = _create_account(auth_client, name="B", balance="500.00")
    total_before = _total_balance(auth_client)
    _transfer(auth_client, a["id"], b["id"], amount="200.00")
    assert _balance(auth_client, a["id"]) == "800.00"
    assert _balance(auth_client, b["id"]) == "700.00"
    assert _total_balance(auth_client) == total_before


def test_create_expense_insufficient_funds(auth_client: TestClient) -> None:
    acct = _create_account(auth_client, balance="100.00")
    r = auth_client.post(
        "/api/operations",
        json={
            "type": "expense",
            "amount": "200.00",
            "from_account_id": acct["id"],
            "category_id": EXPENSE_CAT,
        },
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "insufficient_funds"
    assert _balance(auth_client, acct["id"]) == "100.00"
    assert auth_client.get("/api/operations").json()["total"] == 0


def test_create_transfer_insufficient_funds(auth_client: TestClient) -> None:
    a = _create_account(auth_client, name="A", balance="100.00")
    b = _create_account(auth_client, name="B", balance="0.00")
    r = auth_client.post(
        "/api/operations",
        json={
            "type": "transfer",
            "amount": "200.00",
            "from_account_id": a["id"],
            "to_account_id": b["id"],
        },
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "insufficient_funds"
    assert _balance(auth_client, a["id"]) == "100.00"
    assert _balance(auth_client, b["id"]) == "0.00"


def test_create_transfer_same_account_rejected(auth_client: TestClient) -> None:
    acct = _create_account(auth_client)
    r = auth_client.post(
        "/api/operations",
        json={
            "type": "transfer",
            "amount": "100.00",
            "from_account_id": acct["id"],
            "to_account_id": acct["id"],
        },
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "validation_error"


def test_create_operation_foreign_account_404(
    auth_client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    other = _login_user(make_client, "other@example.com")
    other_acct = _create_account(other, name="Other")

    r = auth_client.post(
        "/api/operations",
        json={
            "type": "income",
            "amount": "100.00",
            "from_account_id": other_acct["id"],
            "category_id": INCOME_CAT,
        },
    )
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "account_not_found"


def test_create_income_with_expense_category_rejected(
    auth_client: TestClient,
) -> None:
    acct = _create_account(auth_client)
    r = auth_client.post(
        "/api/operations",
        json={
            "type": "income",
            "amount": "100.00",
            "from_account_id": acct["id"],
            "category_id": EXPENSE_CAT,
        },
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "validation_error"


def test_create_occurred_at_in_future_rejected(auth_client: TestClient) -> None:
    acct = _create_account(auth_client)
    future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    r = auth_client.post(
        "/api/operations",
        json={
            "type": "income",
            "amount": "100.00",
            "from_account_id": acct["id"],
            "category_id": INCOME_CAT,
            "occurred_at": future,
        },
    )
    assert r.status_code == 422


def test_create_occurred_at_naive_rejected(auth_client: TestClient) -> None:
    acct = _create_account(auth_client)
    r = auth_client.post(
        "/api/operations",
        json={
            "type": "income",
            "amount": "100.00",
            "from_account_id": acct["id"],
            "category_id": INCOME_CAT,
            "occurred_at": "2026-01-01T00:00:00",
        },
    )
    assert r.status_code == 422


def test_create_income_without_category_rejected(auth_client: TestClient) -> None:
    acct = _create_account(auth_client)
    r = auth_client.post(
        "/api/operations",
        json={
            "type": "income",
            "amount": "100.00",
            "from_account_id": acct["id"],
        },
    )
    assert r.status_code == 422


def test_create_income_with_to_account_rejected(auth_client: TestClient) -> None:
    acct = _create_account(auth_client)
    r = auth_client.post(
        "/api/operations",
        json={
            "type": "income",
            "amount": "100.00",
            "from_account_id": acct["id"],
            "to_account_id": acct["id"],
            "category_id": INCOME_CAT,
        },
    )
    assert r.status_code == 422


# --- list ---


def test_list_filter_by_type(auth_client: TestClient) -> None:
    a = _create_account(auth_client, name="A", balance="1000.00")
    b = _create_account(auth_client, name="B", balance="1000.00")
    _income(auth_client, a["id"])
    _expense(auth_client, a["id"], amount="50.00")
    _transfer(auth_client, a["id"], b["id"], amount="25.00")

    assert auth_client.get("/api/operations?type=income").json()["total"] == 1
    assert auth_client.get("/api/operations?type=expense").json()["total"] == 1
    assert auth_client.get("/api/operations?type=transfer").json()["total"] == 1


def test_list_filter_by_account_includes_from_and_to(
    auth_client: TestClient,
) -> None:
    a = _create_account(auth_client, name="A", balance="1000.00")
    b = _create_account(auth_client, name="B", balance="1000.00")
    _income(auth_client, a["id"])
    _transfer(auth_client, a["id"], b["id"])
    _income(auth_client, b["id"])

    assert auth_client.get(f"/api/operations?account_id={a['id']}").json()["total"] == 2
    assert auth_client.get(f"/api/operations?account_id={b['id']}").json()["total"] == 2


def test_list_sorted_by_occurred_at_desc(auth_client: TestClient) -> None:
    acct = _create_account(auth_client)
    base = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)
    ids = [
        _income(
            auth_client,
            acct["id"],
            occurred_at=(base + timedelta(hours=i)).isoformat(),
        )["id"]
        for i in range(3)
    ]
    r = auth_client.get("/api/operations")
    assert [o["id"] for o in r.json()["items"]] == [ids[2], ids[1], ids[0]]


def test_list_pagination(auth_client: TestClient) -> None:
    acct = _create_account(auth_client, balance="10000.00")
    base = datetime(2026, 10, 1, 12, 0, 0, tzinfo=UTC)
    for i in range(5):
        _income(
            auth_client,
            acct["id"],
            amount="10.00",
            occurred_at=(base + timedelta(hours=i)).isoformat(),
        )

    page1 = auth_client.get("/api/operations?limit=2&offset=0").json()
    assert page1["total"] == 5
    assert page1["limit"] == 2
    assert page1["offset"] == 0
    assert len(page1["items"]) == 2

    page3 = auth_client.get("/api/operations?limit=2&offset=4").json()
    assert len(page3["items"]) == 1


# --- get ---


def test_get_operation(auth_client: TestClient) -> None:
    acct = _create_account(auth_client)
    op = _income(auth_client, acct["id"])
    r = auth_client.get(f"/api/operations/{op['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == op["id"]


def test_foreign_operation_returns_404(
    auth_client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    acct = _create_account(auth_client)
    op = _income(auth_client, acct["id"])
    other = _login_user(make_client, "other@example.com")

    assert other.get(f"/api/operations/{op['id']}").status_code == 404
    assert other.patch(f"/api/operations/{op['id']}", json={"amount": "1.00"}).status_code == 404
    assert other.delete(f"/api/operations/{op['id']}").status_code == 404


# --- patch ---


def test_patch_amount_recalculates_balance(auth_client: TestClient) -> None:
    acct = _create_account(auth_client, balance="1000.00")
    op = _income(auth_client, acct["id"], amount="200.00")
    assert _balance(auth_client, acct["id"]) == "1200.00"

    r = auth_client.patch(f"/api/operations/{op['id']}", json={"amount": "300.00"})
    assert r.status_code == 200
    assert r.json()["amount"] == "300.00"
    assert _balance(auth_client, acct["id"]) == "1300.00"


def test_patch_from_account_recalculates_balances(auth_client: TestClient) -> None:
    a = _create_account(auth_client, name="A", balance="1000.00")
    b = _create_account(auth_client, name="B", balance="500.00")
    op = _expense(auth_client, a["id"], amount="300.00")
    assert _balance(auth_client, a["id"]) == "700.00"
    assert _balance(auth_client, b["id"]) == "500.00"

    r = auth_client.patch(f"/api/operations/{op['id']}", json={"from_account_id": b["id"]})
    assert r.status_code == 200
    assert _balance(auth_client, a["id"]) == "1000.00"
    assert _balance(auth_client, b["id"]) == "200.00"


def test_patch_type_change_rejected(auth_client: TestClient) -> None:
    acct = _create_account(auth_client)
    op = _income(auth_client, acct["id"])
    r = auth_client.patch(f"/api/operations/{op['id']}", json={"type": "expense"})
    assert r.status_code == 422


def test_patch_empty_rejected(auth_client: TestClient) -> None:
    acct = _create_account(auth_client)
    op = _income(auth_client, acct["id"])
    r = auth_client.patch(f"/api/operations/{op['id']}", json={})
    assert r.status_code == 422


def test_patch_null_amount_rejected(auth_client: TestClient) -> None:
    acct = _create_account(auth_client)
    op = _income(auth_client, acct["id"])
    r = auth_client.patch(f"/api/operations/{op['id']}", json={"amount": None})
    assert r.status_code == 422


def test_patch_null_category_rejected(auth_client: TestClient) -> None:
    acct = _create_account(auth_client)
    op = _income(auth_client, acct["id"])
    r = auth_client.patch(f"/api/operations/{op['id']}", json={"category_id": None})
    assert r.status_code == 422


def test_patch_insufficient_funds(auth_client: TestClient) -> None:
    acct = _create_account(auth_client, balance="1000.00")
    op = _expense(auth_client, acct["id"], amount="800.00")
    assert _balance(auth_client, acct["id"]) == "200.00"

    r = auth_client.patch(f"/api/operations/{op['id']}", json={"amount": "2000.00"})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "insufficient_funds"
    assert _balance(auth_client, acct["id"]) == "200.00"


def test_patch_foreign_account_404(
    auth_client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    acct = _create_account(auth_client)
    op = _income(auth_client, acct["id"])

    other = _login_user(make_client, "other@example.com")
    other_acct = _create_account(other, name="Other")

    r = auth_client.patch(
        f"/api/operations/{op['id']}",
        json={"from_account_id": other_acct["id"]},
    )
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "account_not_found"


def test_patch_nonexistent_account_404(auth_client: TestClient) -> None:
    acct = _create_account(auth_client)
    op = _income(auth_client, acct["id"])
    r = auth_client.patch(f"/api/operations/{op['id']}", json={"from_account_id": 99999})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "account_not_found"


# --- delete ---


def test_delete_income_rolls_back_balance(auth_client: TestClient) -> None:
    acct = _create_account(auth_client, balance="1000.00")
    op = _income(auth_client, acct["id"], amount="200.00")
    assert _balance(auth_client, acct["id"]) == "1200.00"

    r = auth_client.delete(f"/api/operations/{op['id']}")
    assert r.status_code == 204
    assert _balance(auth_client, acct["id"]) == "1000.00"
    assert auth_client.get(f"/api/operations/{op['id']}").status_code == 404


def test_delete_insufficient_for_rollback(auth_client: TestClient) -> None:
    acct = _create_account(auth_client, balance="1000.00")
    op = _income(auth_client, acct["id"], amount="500.00")
    # баланс 1500, откат даст 1500 - 500 = 1000
    # уменьшаем вручную до 200 — откат уведёт в минус
    auth_client.patch(f"/api/accounts/{acct['id']}", json={"balance": "200.00"})

    r = auth_client.delete(f"/api/operations/{op['id']}")
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "insufficient_funds"
    assert auth_client.get(f"/api/operations/{op['id']}").status_code == 200
    assert _balance(auth_client, acct["id"]) == "200.00"


# --- linkage ---


def test_linked_operation_cannot_be_patched_or_deleted(
    auth_client: TestClient,
) -> None:
    acct = _create_account(auth_client, balance="1000.00")
    pe = auth_client.post(
        "/api/planned-expenses",
        json={"name": "Аренда", "amount": "100.00", "due_date": "2026-11-01"},
    ).json()

    pay = auth_client.patch(
        f"/api/planned-expenses/{pe['id']}/pay",
        json={"account_id": acct["id"], "category_id": HOUSING_CAT},
    )
    assert pay.status_code == 200
    op_id = pay.json()["paid_operation_id"]

    patch_resp = auth_client.patch(f"/api/operations/{op_id}", json={"amount": "50.00"})
    assert patch_resp.status_code == 409
    assert patch_resp.json()["detail"]["code"] == "operation_linked_to_planned_expense"

    del_resp = auth_client.delete(f"/api/operations/{op_id}")
    assert del_resp.status_code == 409
    assert del_resp.json()["detail"]["code"] == "operation_linked_to_planned_expense"


# --- account delete protection ---


def test_account_with_operations_cannot_be_deleted(
    auth_client: TestClient,
) -> None:
    acct = _create_account(auth_client)
    _income(auth_client, acct["id"])
    r = auth_client.delete(f"/api/accounts/{acct['id']}")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "account_has_operations"
