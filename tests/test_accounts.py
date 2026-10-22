from collections.abc import Callable

from fastapi.testclient import TestClient


def _create_account(client: TestClient, name: str = "A", balance: str = "100.00") -> dict:
    response = client.post("/api/accounts", json={"name": name, "balance": balance})
    assert response.status_code == 201
    return response.json()


def test_list_accounts_empty(auth_client: TestClient) -> None:
    response = auth_client.get("/api/accounts")
    assert response.status_code == 200
    assert response.json() == []


def test_create_account_returns_balance_as_string(auth_client: TestClient) -> None:
    response = auth_client.post("/api/accounts", json={"name": "Основной", "balance": "10000.00"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Основной"
    assert body["balance"] == "10000.00"
    assert isinstance(body["balance"], str)


def test_create_account_zero_balance(auth_client: TestClient) -> None:
    response = auth_client.post("/api/accounts", json={"name": "X", "balance": "0.00"})
    assert response.status_code == 201
    assert response.json()["balance"] == "0.00"


def test_create_account_negative_balance(auth_client: TestClient) -> None:
    response = auth_client.post("/api/accounts", json={"name": "X", "balance": "-1.00"})
    assert response.status_code == 422


def test_create_account_extra_precision(auth_client: TestClient) -> None:
    response = auth_client.post("/api/accounts", json={"name": "X", "balance": "100.001"})
    assert response.status_code == 422


def test_create_account_empty_name(auth_client: TestClient) -> None:
    response = auth_client.post("/api/accounts", json={"name": "   ", "balance": "1.00"})
    assert response.status_code == 422


def test_get_account(auth_client: TestClient) -> None:
    created = _create_account(auth_client, name="A")
    response = auth_client.get(f"/api/accounts/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "A"


def test_patch_account_name(auth_client: TestClient) -> None:
    created = _create_account(auth_client)
    response = auth_client.patch(f"/api/accounts/{created['id']}", json={"name": "B"})
    assert response.status_code == 200
    assert response.json()["name"] == "B"
    assert response.json()["balance"] == "100.00"


def test_patch_account_balance(auth_client: TestClient) -> None:
    created = _create_account(auth_client)
    response = auth_client.patch(f"/api/accounts/{created['id']}", json={"balance": "200.00"})
    assert response.status_code == 200
    assert response.json()["balance"] == "200.00"


def test_patch_account_empty_body(auth_client: TestClient) -> None:
    created = _create_account(auth_client)
    response = auth_client.patch(f"/api/accounts/{created['id']}", json={})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "validation_error"


def test_patch_account_null_field(auth_client: TestClient) -> None:
    created = _create_account(auth_client)
    response = auth_client.patch(f"/api/accounts/{created['id']}", json={"name": None})
    assert response.status_code == 422


def test_delete_account_without_operations(auth_client: TestClient) -> None:
    created = _create_account(auth_client)
    response = auth_client.delete(f"/api/accounts/{created['id']}")
    assert response.status_code == 204
    assert auth_client.get(f"/api/accounts/{created['id']}").status_code == 404


def test_creating_account_does_not_create_operation(auth_client: TestClient) -> None:
    _create_account(auth_client)
    response = auth_client.get("/api/operations")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_foreign_account_returns_404(
    auth_client: TestClient, make_client: Callable[[], TestClient]
) -> None:
    created = _create_account(auth_client)

    other = make_client()
    other.post(
        "/api/auth/register",
        json={"email": "other@example.com", "password": "strong_password_123"},
    )
    other.post(
        "/api/auth/login",
        json={"email": "other@example.com", "password": "strong_password_123"},
    )

    assert other.get(f"/api/accounts/{created['id']}").status_code == 404
    assert other.patch(f"/api/accounts/{created['id']}", json={"name": "X"}).status_code == 404
    assert other.delete(f"/api/accounts/{created['id']}").status_code == 404
