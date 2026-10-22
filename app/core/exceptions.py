class AppError(Exception):
    """Базовое доменное исключение приложения.

    Содержит HTTP-статус, машинный код и человекочитаемое сообщение.
    Подклассы фиксируют статус, конкретные ошибки — инстансы с code/message.
    """

    status_code: int = 400
    default_code: str = "error"
    default_message: str = "Ошибка запроса"

    def __init__(
        self,
        code: str | None = None,
        message: str | None = None,
        fields: list[dict[str, str]] | None = None,
    ) -> None:
        self.code = code or self.default_code
        self.message = message or self.default_message
        self.fields = fields
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class UnprocessableEntityError(AppError):
    status_code = 422
