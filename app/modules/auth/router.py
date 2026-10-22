from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.cookies import clear_access_token_cookie, set_access_token_cookie
from app.core.security import create_access_token
from app.db.session import get_session
from app.modules.auth import service
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.schemas import LoginRequest, RegisterRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    session: Annotated[Session, Depends(get_session)],
) -> User:
    return service.register(session, payload)


@router.post("/login", response_model=UserResponse)
def login(
    payload: LoginRequest,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
) -> User:
    user = service.authenticate(session, payload)
    token = create_access_token(user.id)
    set_access_token_cookie(response, token)
    return user


@router.get("/me", response_model=UserResponse)
def me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    clear_access_token_cookie(response)
