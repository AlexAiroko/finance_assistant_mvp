from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_session
from app.modules.auth.models import User


def get_current_user(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> User:
    settings = get_settings()
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        raise UnauthorizedError("authentication_required", "Требуется аутентификация")

    user_id = decode_access_token(token)
    user = session.get(User, user_id)
    if user is None:
        raise UnauthorizedError("authentication_required", "Требуется аутентификация")
    return user
