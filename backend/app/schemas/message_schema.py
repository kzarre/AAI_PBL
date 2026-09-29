from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.moderation_schema import Label
from app.schemas.user_schema import ReputationSummary, UserRef


class ClassifyRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message_id: str = Field(min_length=1, max_length=64)
    sender: UserRef
    target: UserRef | None = None
    text: str = Field(min_length=1, max_length=2000)
    timestamp: datetime | None = None


class ClassifyResponse(BaseModel):
    message_id: str
    label: Label
    confidence: float
    reason: str
    recommended_action: str
    sender_reputation: ReputationSummary


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sender_id: str
    target_id: str | None
    text: str
    label: Label
    confidence: float
    reason: str
    recommended_action: str
    created_at: datetime
