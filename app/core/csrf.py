from urllib.parse import urlparse

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.error_handlers import error_payload

_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class OriginCheckMiddleware(BaseHTTPMiddleware):
    """Проверка Origin/Referer для изменяющих запросов (ТЗ 9.5).

    Логика:
    - Если есть Origin — проверяем его.
    - Если Origin нет, но есть Referer — проверяем origin, извлечённый из Referer.
    - Если ни Origin, ни Referer не переданы — запрос разрешён (MVP-упрощение).
    - Если проверяемый origin не входит в CORS_ORIGINS и не совпадает с self-origin
      приложения — 403 forbidden_origin.
    """

    def __init__(self, app, allowed_origins: list[str]) -> None:
        super().__init__(app)
        self._allowed = {origin.rstrip("/") for origin in allowed_origins}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in _MUTATING_METHODS:
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")

            candidate: str | None
            if origin:
                candidate = origin
            elif referer:
                parsed = urlparse(referer)
                candidate = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else None
            else:
                candidate = None

            if candidate is not None and not self._is_allowed(candidate, request):
                return JSONResponse(
                    status_code=403,
                    content=error_payload(
                        "forbidden_origin",
                        "Запрос отклонён: недопустимый Origin",
                    ),
                )

        return await call_next(request)

    def _is_allowed(self, origin: str, request: Request) -> bool:
        normalized = origin.rstrip("/")
        if normalized in self._allowed:
            return True
        # Self-origin: Swagger UI и same-origin frontend работают без настройки.
        base = str(request.base_url).rstrip("/")
        return normalized == base
