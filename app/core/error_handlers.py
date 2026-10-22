import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError

logger = logging.getLogger(__name__)


def error_payload(
    code: str,
    message: str,
    fields: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    detail: dict[str, Any] = {"code": code, "message": message}
    if fields:
        detail["fields"] = fields
    return {"detail": detail}


# Соответствие HTTP-статуса стандартных исключений FastAPI нашим машинным кодам.
_HTTP_STATUS_CODES: dict[int, str] = {
    400: "bad_request",
    401: "authentication_required",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.code, exc.message, exc.fields),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        # loc обычно выглядит как ("body", "email", "min_length"). Первый элемент
        # — источник (body/query/path), его убираем: клиенту полезен только путь
        # до конкретного поля. Если loc пуст после фильтра — используем __root__.
        fields = [
            {
                "field": ".".join(str(part) for part in err["loc"][1:]) or "__root__",
                "message": err["msg"],
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=error_payload(
                "validation_error",
                "Проверьте корректность введённых данных",
                fields,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_STATUS_CODES.get(exc.status_code, "http_error")
        message = exc.detail if isinstance(exc.detail, str) else "Ошибка запроса"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(code, message),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content=error_payload("internal_server_error", "Внутренняя ошибка сервера"),
        )
