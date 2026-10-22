from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.dashboard import service
from app.modules.dashboard.schemas import DashboardResponse

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DashboardResponse:
    return service.get_dashboard(session, current_user.id)
