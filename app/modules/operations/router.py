from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.operations import service
from app.modules.operations.models import Operation, OperationType
from app.modules.operations.schemas import (
    OperationCreate,
    OperationListResponse,
    OperationResponse,
    OperationUpdate,
)

router = APIRouter(prefix="/api/operations", tags=["operations"])


@router.get("", response_model=OperationListResponse)
def list_operations(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    operation_type: Annotated[OperationType | None, Query(alias="type")] = None,
    account_id: Annotated[int | None, Query()] = None,
    category_id: Annotated[int | None, Query()] = None,
    date_from: Annotated[AwareDatetime | None, Query(alias="from")] = None,
    date_to: Annotated[AwareDatetime | None, Query(alias="to")] = None,
) -> OperationListResponse:
    items, total = service.list_operations(
        session,
        current_user.id,
        operation_type=operation_type,
        account_id=account_id,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return OperationListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "",
    response_model=OperationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_operation(
    payload: OperationCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Operation:
    return service.create_operation(session, current_user.id, payload)


@router.get("/{operation_id}", response_model=OperationResponse)
def get_operation(
    operation_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Operation:
    return service.get_operation(session, current_user.id, operation_id)


@router.patch("/{operation_id}", response_model=OperationResponse)
def update_operation(
    operation_id: int,
    payload: OperationUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Operation:
    return service.update_operation(session, current_user.id, operation_id, payload)


@router.delete("/{operation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_operation(
    operation_id: int,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    service.delete_operation(session, current_user.id, operation_id)
