from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.common import utc_now


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(primary_key=True)
    name: str
    reputation_score: int = 100
    risk_level: str = Field(default="good", index=True)
    total_messages: int = 0
    green_count: int = 0
    yellow_count: int = 0
    severe_count: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
