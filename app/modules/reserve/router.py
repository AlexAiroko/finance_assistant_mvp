from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.reserve import service
from app.modules.reserve.models import Reserve
from app.modules.reserve.schemas import ReserveResponse, ReserveUpdate

router = APIRouter(prefix="/api/reserve", tags=["reserve"])


@router.get("", response_model=ReserveResponse)
def get_reserve(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Reserve:
    return service.get_reserve(session, current_user.id)


@router.put("", response_model=ReserveResponse)
def set_reserve(
    payload: ReserveUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Reserve:
    return service.set_reserve(session, current_user.id, payload)
