from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["good", "watch", "risky", "dangerous"]


class UserRef(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=100)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    reputation_score: int
    risk_level: RiskLevel
    total_messages: int
    green_count: int
    yellow_count: int
    severe_count: int


class ReputationSummary(BaseModel):
    user_id: str
    name: str
    score: int
    risk_level: RiskLevel
