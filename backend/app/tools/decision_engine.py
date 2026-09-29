"""Combines rule checker, AI result, recent context and reputation into a final label."""

from app.schemas.moderation_schema import AgentOutput, AIResult, Decision, RecentContext

REPEATED_YELLOW_THRESHOLD = 3
LOW_REPUTATION_THRESHOLD = 30
ESCALATION_CONFIDENCE = 0.9
SEVERE_ACTION = "Hide the message, alert a moderator, and review the sender."


def decide(agent_output: AgentOutput, context: RecentContext, sender_reputation: int) -> Decision:
    ai, rules = agent_output.ai, agent_output.rules

    if rules.label == "severe":
        return _severe(ai, f"Rule checker matched severe content: {', '.join(rules.matches)}.")
    if ai.label == "severe":
        return _from_ai(ai)
    if ai.label == "yellow":
        return _check_yellow_escalation(ai, context, sender_reputation)
    return _from_ai(ai)


def _check_yellow_escalation(ai: AIResult, context: RecentContext, sender_reputation: int) -> Decision:
    # Count includes the current (yellow) message.
    repeated = context.yellow_to_target_count + 1
    if repeated >= REPEATED_YELLOW_THRESHOLD:
        return _severe(ai, f"Repeated targeted abuse: {repeated} yellow messages to the same target recently.")
    if sender_reputation < LOW_REPUTATION_THRESHOLD:
        return _severe(ai, f"Escalated: sender reputation {sender_reputation} is below {LOW_REPUTATION_THRESHOLD}.")
    return _from_ai(ai)


def _from_ai(ai: AIResult) -> Decision:
    return Decision(**ai.model_dump())


def _severe(ai: AIResult, note: str) -> Decision:
    if ai.label == "severe":
        return Decision(**ai.model_dump(), notes=[note])
    return Decision(
        label="severe",
        confidence=max(ai.confidence, ESCALATION_CONFIDENCE),
        reason=note,
        recommended_action=SEVERE_ACTION,
        escalated=True,
        notes=[note, f"Original AI label: {ai.label}."],
    )
