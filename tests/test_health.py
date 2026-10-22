from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_auth_client_has_session_cookie(auth_client: TestClient) -> None:
    response = auth_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
