from collections.abc import Sequence

from sqlmodel import Session, col, select

from app.models.common import utc_now
from app.models.user import User
from app.schemas.user_schema import ReputationSummary, RiskLevel, UserRef


def get_user(session: Session, user_id: str) -> User | None:
    return session.get(User, user_id)


def upsert_user(session: Session, ref: UserRef) -> User:
    """Create the user if new; keep the latest display name if it changed."""
    user = session.get(User, ref.id)
    if user is None:
        user = User(id=ref.id, name=ref.name)
    elif user.name != ref.name:
        user.name = ref.name
        user.updated_at = utc_now()
    session.add(user)
    return user


def list_users(session: Session, risk_level: RiskLevel | None = None) -> Sequence[User]:
    query = select(User).order_by(col(User.reputation_score), col(User.id))
    if risk_level is not None:
        query = query.where(User.risk_level == risk_level)
    return session.exec(query).all()


def to_reputation_summary(user: User) -> ReputationSummary:
    return ReputationSummary(
        user_id=user.id, name=user.name, score=user.reputation_score, risk_level=user.risk_level
    )
