"""Orchestrates the full moderation flow for one incoming message."""

from sqlmodel import Session

from app.agent import moderation_agent
from app.models.moderation_event import ModerationEvent
from app.schemas.message_schema import ClassifyRequest, ClassifyResponse
from app.schemas.moderation_schema import AgentOutput, Decision
from app.services import context_service, message_service, reputation_service, user_service
from app.tools import decision_engine


class DuplicateMessageError(Exception):
    pass


def process_message(session: Session, payload: ClassifyRequest) -> ClassifyResponse:
    if message_service.message_exists(session, payload.message_id):
        raise DuplicateMessageError(payload.message_id)

    sender = user_service.upsert_user(session, payload.sender)
    target = user_service.upsert_user(session, payload.target) if payload.target else None

    context = context_service.get_recent_context(session, sender.id, target.id if target else None)
    agent_output = moderation_agent.classify(
        payload.text, sender.name, target.name if target else None, context
    )
    decision = decision_engine.decide(agent_output, context, sender.reputation_score)

    old_score, new_score = reputation_service.apply_label(sender, decision.label)
    session.add(message_service.build_message(payload, decision))
    session.add(_build_event(payload, agent_output, decision, old_score, new_score))
    session.commit()
    session.refresh(sender)

    return ClassifyResponse(
        message_id=payload.message_id,
        label=decision.label,
        confidence=decision.confidence,
        reason=decision.reason,
        recommended_action=decision.recommended_action,
        sender_reputation=user_service.to_reputation_summary(sender),
    )


def _build_event(
    payload: ClassifyRequest, agent_output: AgentOutput, decision: Decision, old_score: int, new_score: int
) -> ModerationEvent:
    notes = [f"label={decision.label}", f"source={agent_output.source}", *decision.notes]
    return ModerationEvent(
        message_id=payload.message_id,
        sender_id=payload.sender.id,
        event_type="escalation" if decision.escalated else "classification",
        old_reputation=old_score,
        new_reputation=new_score,
        notes="; ".join(notes),
    )
