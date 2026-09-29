"""Classification agent: LLM first, rule-based fallback. Never touches the database."""

import logging
from typing import Any

from pydantic import ValidationError

from app.agent.llm_client import get_llm_client
from app.agent.prompts import SYSTEM_PROMPT, build_user_prompt
from app.schemas.moderation_schema import AgentOutput, AIResult, RecentContext, RuleResult
from app.tools import rule_checker

logger = logging.getLogger(__name__)

_FALLBACK: dict[str, tuple[float, str]] = {
    "green": (0.6, "No action needed."),
    "yellow": (0.75, "Monitor and warn if repeated."),
    "severe": (0.95, "Hide the message, alert a moderator, and review the sender."),
}


def classify(text: str, sender_name: str, target_name: str | None, context: RecentContext) -> AgentOutput:
    rules = rule_checker.check(text)
    ai = _classify_with_llm(text, sender_name, target_name, context)
    if ai is None:
        return AgentOutput(ai=fallback_classify(rules), rules=rules, source="rules")
    return AgentOutput(ai=ai, rules=rules, source="llm")


def fallback_classify(rules: RuleResult) -> AIResult:
    confidence, action = _FALLBACK[rules.label]
    if rules.matches:
        reason = f"Rule-based: matched {rules.label} pattern(s): {', '.join(rules.matches)}."
    else:
        reason = "Rule-based: no harmful patterns detected."
    return AIResult(label=rules.label, confidence=confidence, reason=reason, recommended_action=action)


def _classify_with_llm(
    text: str, sender_name: str, target_name: str | None, context: RecentContext
) -> AIResult | None:
    client = get_llm_client()
    if client is None:
        return None
    raw = client.complete_json(SYSTEM_PROMPT, build_user_prompt(text, sender_name, target_name, context))
    return _parse_llm_output(raw) if raw is not None else None


def _parse_llm_output(raw: dict[str, Any]) -> AIResult | None:
    if isinstance(raw.get("label"), str):
        raw = {**raw, "label": raw["label"].strip().lower()}
    try:
        return AIResult.model_validate(raw)
    except ValidationError as exc:
        logger.warning("Invalid LLM output %s: %s", raw, exc)
        return None
