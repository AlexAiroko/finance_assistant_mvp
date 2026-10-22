from collections.abc import Callable

from fastapi.testclient import TestClient


def _login_user(make_client: Callable[[], TestClient], email: str) -> TestClient:
    c = make_client()
    c.post(
        "/api/auth/register",
        json={"email": email, "password": "strong_password_123"},
    )
    c.post(
        "/api/auth/login",
        json={"email": email, "password": "strong_password_123"},
    )
    return c


def test_get_new_user_reserve_zero(auth_client: TestClient) -> None:
    r = auth_client.get("/api/reserve")
    assert r.status_code == 200
    body = r.json()
    assert body["amount"] == "0.00"
    assert body["currency"] == "RUB"
    assert "created_at" in body
    assert "updated_at" in body


def test_put_positive(auth_client: TestClient) -> None:
    r = auth_client.put("/api/reserve", json={"amount": "15000.00"})
    assert r.status_code == 200
    assert r.json()["amount"] == "15000.00"

    assert auth_client.get("/api/reserve").json()["amount"] == "15000.00"


def test_put_zero(auth_client: TestClient) -> None:
    auth_client.put("/api/reserve", json={"amount": "5000.00"})
    r = auth_client.put("/api/reserve", json={"amount": "0.00"})
    assert r.status_code == 200
    assert r.json()["amount"] == "0.00"


def test_put_idempotent(auth_client: TestClient) -> None:
    first = auth_client.put("/api/reserve", json={"amount": "1000.00"})
    second = auth_client.put("/api/reserve", json={"amount": "1000.00"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["amount"] == "1000.00"


def test_put_negative_rejected(auth_client: TestClient) -> None:
    r = auth_client.put("/api/reserve", json={"amount": "-100.00"})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["code"] == "validation_error"
    assert "amount" in {f["field"] for f in detail["fields"]}


def test_put_extra_precision_rejected(auth_client: TestClient) -> None:
    r = auth_client.put("/api/reserve", json={"amount": "100.001"})
    assert r.status_code == 422


def test_reserve_isolation(auth_client: TestClient, make_client: Callable[[], TestClient]) -> None:
    auth_client.put("/api/reserve", json={"amount": "5000.00"})

    other = _login_user(make_client, "other@example.com")
    assert other.get("/api/reserve").json()["amount"] == "0.00"

    other.put("/api/reserve", json={"amount": "700.00"})
    assert other.get("/api/reserve").json()["amount"] == "700.00"
    assert auth_client.get("/api/reserve").json()["amount"] == "5000.00"


def test_get_reserve_requires_auth(client: TestClient) -> None:
    r = client.get("/api/reserve")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "authentication_required"
