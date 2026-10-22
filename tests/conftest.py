import contextlib
import os

# Переопределяем настройки ДО импорта app.*: get_settings() кешируется,
# а engine создаётся при импорте app.db.session.
# Ruff не срабатывает на E402 для этой идиомы: присваивания os.environ
# перед импортами — стандартный паттерн в conftest.py.
os.environ["APP_ENV"] = "test"
os.environ["DB_NAME"] = "finance_assistant_test"

if not os.environ["DB_NAME"].endswith("_test"):
    raise RuntimeError(
        f"Тесты должны запускаться на *_test базе, получено: {os.environ['DB_NAME']}"
    )

from collections.abc import Callable, Iterator

import psycopg2
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal, engine
from app.main import app

_TRUNCATE_SQL = text(
    "TRUNCATE TABLE planned_expenses, operations, accounts, reserves, users "
    "RESTART IDENTITY CASCADE"
)


def _ensure_database_exists() -> None:
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASS.get_secret_value(),
        dbname="postgres",
    )
    try:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (settings.DB_NAME,),
            )
            if cur.fetchone() is None:
                cur.execute(f'CREATE DATABASE "{settings.DB_NAME}"')
    finally:
        conn.close()


@pytest.fixture(scope="session", autouse=True)
def _prepare_database() -> Iterator[None]:
    _ensure_database_exists()
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean_database(_prepare_database: None) -> Iterator[None]:
    with engine.begin() as conn:
        conn.execute(_TRUNCATE_SQL)
    yield


@pytest.fixture
def db_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_client(client: TestClient) -> TestClient:
    email = "test@example.com"
    password = "strong_password_123"
    client.post("/api/auth/register", json={"email": email, "password": password})
    client.post("/api/auth/login", json={"email": email, "password": password})
    return client


@pytest.fixture
def make_client() -> Iterator[Callable[[], TestClient]]:
    entered: list[TestClient] = []

    def _make() -> TestClient:
        c = TestClient(app)
        c.__enter__()
        entered.append(c)
        return c

    yield _make

    for c in entered:
        with contextlib.suppress(Exception):
            c.__exit__(None, None, None)
