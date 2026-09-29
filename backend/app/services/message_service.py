from collections.abc import Sequence

from sqlmodel import Session, col, or_, select

from app.models.common import to_utc, utc_now
from app.models.message import Message
from app.schemas.message_schema import ClassifyRequest
from app.schemas.moderation_schema import Decision


def message_exists(session: Session, message_id: str) -> bool:
    return session.get(Message, message_id) is not None


def build_message(payload: ClassifyRequest, decision: Decision) -> Message:
    return Message(
        id=payload.message_id,
        sender_id=payload.sender.id,
        target_id=payload.target.id if payload.target else None,
        text=payload.text,
        label=decision.label,
        confidence=decision.confidence,
        reason=decision.reason,
        recommended_action=decision.recommended_action,
        created_at=to_utc(payload.timestamp) if payload.timestamp else utc_now(),
    )


def list_recent_messages(session: Session, label: str | None = None, limit: int = 50) -> Sequence[Message]:
    query = select(Message).order_by(col(Message.created_at).desc()).limit(limit)
    if label is not None:
        query = query.where(Message.label == label)
    return session.exec(query).all()


def list_user_messages(session: Session, user_id: str, limit: int = 50) -> Sequence[Message]:
    """Messages the user sent or received, newest first."""
    query = (
        select(Message)
        .where(or_(Message.sender_id == user_id, Message.target_id == user_id))
        .order_by(col(Message.created_at).desc())
        .limit(limit)
    )
    return session.exec(query).all()
