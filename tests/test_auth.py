from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.auth.models import User
from app.modules.reserve.models import Reserve

_VALID = {"email": "user@example.com", "password": "strong_password_123"}


def test_register_returns_user_without_secrets(client: TestClient) -> None:
    response = client.post("/api/auth/register", json=_VALID)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "user@example.com"
    assert "id" in body and "created_at" in body
    assert "password_hash" not in body
    assert "password" not in body


def test_register_stores_argon2id_hash_and_zero_reserve(
    client: TestClient, db_session: Session
) -> None:
    client.post("/api/auth/register", json=_VALID)
    user = db_session.execute(select(User)).scalar_one()
    assert user.password_hash.startswith("$argon2id$v=19$")
    reserve = db_session.execute(select(Reserve)).scalar_one()
    assert reserve.user_id == user.id
    assert str(reserve.amount) == "0.00"


def test_register_normalizes_email(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "  USER@Example.COM ", "password": "strong_password_123"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"


def test_register_duplicate_email(client: TestClient) -> None:
    client.post("/api/auth/register", json=_VALID)
    response = client.post("/api/auth/register", json=_VALID)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "email_already_exists"


def test_register_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "short"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "validation_error"
    assert "password" in {f["field"] for f in detail["fields"]}


def test_register_invalid_email(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "strong_password_123"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "validation_error"
    assert "email" in {f["field"] for f in detail["fields"]}


def test_login_sets_httponly_cookie_without_jwt_in_body(client: TestClient) -> None:
    client.post("/api/auth/register", json=_VALID)
    response = client.post("/api/auth/login", json=_VALID)
    assert response.status_code == 200
    body = response.json()
    assert "access_token" not in body
    assert "token" not in body
    assert "jwt" not in body
    set_cookie = response.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie


def test_login_wrong_password(client: TestClient) -> None:
    client.post("/api/auth/register", json=_VALID)
    response = client.post(
        "/api/auth/login",
        json={"email": _VALID["email"], "password": "wrong_password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"


def test_login_unknown_user_returns_same_error(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "ghost@example.com", "password": "anything_123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"


def test_me_with_valid_cookie(auth_client: TestClient) -> None:
    response = auth_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


def test_me_without_cookie(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "authentication_required"


def test_me_with_invalid_token(client: TestClient) -> None:
    client.cookies.set("access_token", "garbage.token.value")
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "authentication_required"


def test_me_with_expired_token(client: TestClient) -> None:
    client.post("/api/auth/register", json=_VALID)
    settings = get_settings()
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": "1",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )
    client.cookies.set("access_token", expired)
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "authentication_required"


def test_logout_clears_cookie(auth_client: TestClient) -> None:
    response = auth_client.post("/api/auth/logout")
    assert response.status_code == 204
    set_cookie = response.headers.get("set-cookie", "")
    assert "Max-Age=0" in set_cookie or 'access_token=""' in set_cookie

    response = auth_client.get("/api/auth/me")
    assert response.status_code == 401
