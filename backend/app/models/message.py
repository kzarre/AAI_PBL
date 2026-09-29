from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.common import utc_now


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: str = Field(primary_key=True)
    sender_id: str = Field(foreign_key="users.id", index=True)
    target_id: str | None = Field(default=None, foreign_key="users.id", index=True)
    text: str
    label: str = Field(index=True)
    confidence: float
    reason: str
    recommended_action: str
    created_at: datetime = Field(default_factory=utc_now, index=True)
