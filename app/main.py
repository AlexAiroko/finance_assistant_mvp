import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import get_settings
from app.core.csrf import OriginCheckMiddleware
from app.core.error_handlers import register_exception_handlers
from app.db.session import engine
from app.modules.accounts.router import router as accounts_router
from app.modules.auth.router import router as auth_router
from app.modules.categories.router import router as categories_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.operations.router import router as operations_router
from app.modules.planned_expenses.router import router as planned_expenses_router
from app.modules.reserve.router import router as reserve_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    force=True,
)

logger = logging.getLogger(__name__)

_DESCRIPTION = """
Backend персонального финансового помощника.

**Основная ценность:** автоматический расчёт доступной суммы
(`available_amount = total_balance − upcoming_expenses_total − reserve_amount`).
Все денежные значения передаются строками с двумя знаками после запятой
(например, `"1250.00"`), валюта — RUB.

**Аутентификация:** `POST /api/auth/login` устанавливает JWT в HttpOnly cookie
`access_token` (`SameSite=Lax`, `Path=/`). Все защищённые эндпоинты читают
cookie автоматически. JWT **не** возвращается в теле ответа.

**Ручная проверка в Swagger UI:** выполните `POST /api/auth/login`,
cookie установится в браузере, дальнейшие запросы из этой же вкладки
будут её отправлять. Отдельный «Authorize» не требуется.
"""

_TAGS_METADATA = [
    {
        "name": "auth",
        "description": "Регистрация, вход, выход, текущий пользователь.",
    },
    {
        "name": "categories",
        "description": "Предустановленные категории доходов и расходов (только чтение).",
    },
    {
        "name": "accounts",
        "description": "Управление счетами и их балансами.",
    },
    {
        "name": "operations",
        "description": "Доходы, расходы, переводы; история операций.",
    },
    {
        "name": "planned-expenses",
        "description": "Запланированные расходы, оплата и возврат в pending.",
    },
    {
        "name": "reserve",
        "description": "Финансовый резерв пользователя.",
    },
    {
        "name": "dashboard",
        "description": "Агрегаты главного экрана и доступная сумма.",
    },
]


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection OK (env=%s)", settings.APP_ENV)
        yield

    app = FastAPI(
        title=settings.APP_NAME,
        description=_DESCRIPTION,
        openapi_tags=_TAGS_METADATA,
        lifespan=lifespan,
    )

    register_exception_handlers(app)

    app.add_middleware(OriginCheckMiddleware, allowed_origins=settings.CORS_ORIGINS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(categories_router)
    app.include_router(accounts_router)
    app.include_router(operations_router)
    app.include_router(planned_expenses_router)
    app.include_router(reserve_router)
    app.include_router(dashboard_router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
