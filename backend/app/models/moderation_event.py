from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.common import utc_now


class ModerationEvent(SQLModel, table=True):
    __tablename__ = "moderation_events"

    id: int | None = Field(default=None, primary_key=True)
    message_id: str = Field(index=True)
    sender_id: str = Field(index=True)
    event_type: str
    old_reputation: int
    new_reputation: int
    notes: str
    created_at: datetime = Field(default_factory=utc_now)
