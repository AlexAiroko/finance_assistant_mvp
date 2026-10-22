from fastapi import Response

from app.core.config import get_settings


def set_access_token_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path=settings.COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN or None,
    )


def clear_access_token_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path=settings.COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN or None,
    )
