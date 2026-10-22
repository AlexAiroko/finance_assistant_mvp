from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.accounts import service
from app.modules.accounts.models import Account
from app.modules.accounts.schemas import AccountCreate, AccountResponse, AccountUpdate
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountResponse])
def list_accounts(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[Account]:
    return service.list_accounts(session, current_user.id)


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_account(
    payload: AccountCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Account:
    return service.create_account(session, current_user.id, payload)


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Account:
    return service.get_account(session, current_user.id, account_id)


@router.patch("/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: int,
    payload: AccountUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Account:
    return service.update_account(session, current_user.id, account_id, payload)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    service.delete_account(session, current_user.id, account_id)
