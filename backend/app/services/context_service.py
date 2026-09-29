from sqlalchemy import ColumnElement
from sqlmodel import Session, col, select

from app.config import settings
from app.models.message import Message
from app.schemas.moderation_schema import ContextMessage, RecentContext


def get_recent_context(session: Session, sender_id: str, target_id: str | None) -> RecentContext:
    limit = settings.recent_context_limit
    sender_recent = _recent(session, Message.sender_id == sender_id, limit)
    to_target = (
        _recent(session, (Message.sender_id == sender_id) & (Message.target_id == target_id), limit)
        if target_id
        else []
    )
    return RecentContext(sender_recent=sender_recent, sender_to_target_recent=to_target)


def _recent(session: Session, condition: ColumnElement[bool], limit: int) -> list[ContextMessage]:
    query = select(Message).where(condition).order_by(col(Message.created_at).desc()).limit(limit)
    return [
        ContextMessage(sender_id=m.sender_id, target_id=m.target_id, text=m.text, label=m.label)
        for m in session.exec(query).all()
    ]
