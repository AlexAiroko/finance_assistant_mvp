from fastapi.testclient import TestClient

_EXPECTED_INCOME = {"salary", "other_income"}
_EXPECTED_EXPENSE = {
    "groceries",
    "cafes",
    "transport",
    "housing",
    "communication",
    "entertainment",
    "health",
    "other_expense",
}


def test_list_all_categories(auth_client: TestClient) -> None:
    response = auth_client.get("/api/categories")
    assert response.status_code == 200
    categories = response.json()
    assert len(categories) == 10
    codes = {c["code"] for c in categories}
    assert codes == _EXPECTED_INCOME | _EXPECTED_EXPENSE
    for c in categories:
        assert set(c.keys()) == {"id", "code", "name", "type"}


def test_filter_income(auth_client: TestClient) -> None:
    response = auth_client.get("/api/categories?type=income")
    assert response.status_code == 200
    assert {c["code"] for c in response.json()} == _EXPECTED_INCOME


def test_filter_expense(auth_client: TestClient) -> None:
    response = auth_client.get("/api/categories?type=expense")
    assert response.status_code == 200
    assert {c["code"] for c in response.json()} == _EXPECTED_EXPENSE


def test_filter_invalid_type(auth_client: TestClient) -> None:
    response = auth_client.get("/api/categories?type=invalid")
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "validation_error"
    assert "type" in {f["field"] for f in detail["fields"]}


def test_categories_require_auth(client: TestClient) -> None:
    response = client.get("/api/categories")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "authentication_required"
