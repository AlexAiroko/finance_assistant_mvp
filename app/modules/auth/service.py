from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.modules.auth import repository as auth_repository
from app.modules.auth.models import User
from app.modules.auth.schemas import LoginRequest, RegisterRequest
from app.modules.reserve import repository as reserve_repository


def register(session: Session, payload: RegisterRequest) -> User:
    email = payload.email.strip().lower()
    if auth_repository.get_by_email(session, email) is not None:
        raise ConflictError("email_already_exists", "Email уже зарегистрирован")

    try:
        user = auth_repository.create(
            session, email=email, password_hash=hash_password(payload.password)
        )
        reserve_repository.create_default(session, user.id)
        session.commit()
    except IntegrityError as exc:
        # Safety net на race-condition: между get_by_email и commit
        # кто-то мог создать того же пользователя.
        session.rollback()
        raise ConflictError("email_already_exists", "Email уже зарегистрирован") from exc
    except Exception:
        session.rollback()
        raise

    session.refresh(user)
    return user


def authenticate(session: Session, payload: LoginRequest) -> User:
    email = payload.email.strip().lower()
    user = auth_repository.get_by_email(session, email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("invalid_credentials", "Неверный email или пароль")
    return user
