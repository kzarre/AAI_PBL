from app.models.common import utc_now
from app.models.user import User
from app.schemas.moderation_schema import Label
from app.schemas.user_schema import RiskLevel

LABEL_DELTAS: dict[str, int] = {"green": 1, "yellow": -5, "severe": -20}
MIN_SCORE, MAX_SCORE = 0, 100


def clamp(score: int) -> int:
    return max(MIN_SCORE, min(MAX_SCORE, score))


def risk_level_for(score: int) -> RiskLevel:
    if score >= 80:
        return "good"
    if score >= 60:
        return "watch"
    if score >= 30:
        return "risky"
    return "dangerous"


def apply_label(user: User, label: Label) -> tuple[int, int]:
    """Update score, risk level and counters in place. Returns (old_score, new_score)."""
    old_score = user.reputation_score
    user.reputation_score = clamp(old_score + LABEL_DELTAS[label])
    user.risk_level = risk_level_for(user.reputation_score)
    user.total_messages += 1
    setattr(user, f"{label}_count", getattr(user, f"{label}_count") + 1)
    user.updated_at = utc_now()
    return old_score, user.reputation_score
