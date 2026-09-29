from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.database import get_session
from app.models.message import Message
from app.schemas.message_schema import ClassifyRequest, ClassifyResponse, MessageRead
from app.schemas.moderation_schema import Label
from app.services import message_service, moderation_service

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/classify", response_model=ClassifyResponse)
def classify_message(payload: ClassifyRequest, session: Session = Depends(get_session)) -> ClassifyResponse:
    try:
        return moderation_service.process_message(session, payload)
    except moderation_service.DuplicateMessageError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Message '{payload.message_id}' has already been classified.",
        )


@router.get("", response_model=list[MessageRead])
def list_messages(
    label: Label | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> Sequence[Message]:
    return message_service.list_recent_messages(session, label, limit)
