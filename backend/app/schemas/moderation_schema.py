from typing import Literal

from pydantic import BaseModel, Field

Label = Literal["green", "yellow", "severe"]


class ContextMessage(BaseModel):
    sender_id: str
    target_id: str | None
    text: str
    label: Label


class RecentContext(BaseModel):
    """Recent history used by the agent (as prompt context) and the decision engine."""

    sender_recent: list[ContextMessage] = Field(default_factory=list)
    sender_to_target_recent: list[ContextMessage] = Field(default_factory=list)

    @property
    def yellow_to_target_count(self) -> int:
        return sum(1 for m in self.sender_to_target_recent if m.label == "yellow")


class RuleResult(BaseModel):
    label: Label
    matches: list[str] = Field(default_factory=list)


class AIResult(BaseModel):
    label: Label
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)
    recommended_action: str = Field(min_length=1)


class AgentOutput(BaseModel):
    ai: AIResult
    rules: RuleResult
    source: Literal["llm", "rules"]


class Decision(BaseModel):
    label: Label
    confidence: float
    reason: str
    recommended_action: str
    escalated: bool = False
    notes: list[str] = Field(default_factory=list)
