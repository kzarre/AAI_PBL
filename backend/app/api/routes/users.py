from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.database import get_session
from app.models.message import Message
from app.models.user import User
from app.schemas.message_schema import MessageRead
from app.schemas.user_schema import RiskLevel, UserRead
from app.services import message_service, user_service

router = APIRouter(prefix="/users", tags=["users"])


def _get_user_or_404(session: Session, user_id: str) -> User:
    user = user_service.get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{user_id}' not found.")
    return user


@router.get("", response_model=list[UserRead])
def list_users(
    risk_level: RiskLevel | None = None, session: Session = Depends(get_session)
) -> Sequence[User]:
    return user_service.list_users(session, risk_level)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: str, session: Session = Depends(get_session)) -> User:
    return _get_user_or_404(session, user_id)


@router.get("/{user_id}/messages", response_model=list[MessageRead])
def get_user_messages(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> Sequence[Message]:
    _get_user_or_404(session, user_id)
    return message_service.list_user_messages(session, user_id, limit)
