from app.schemas.moderation_schema import ContextMessage, RecentContext

SYSTEM_PROMPT = """You are a cyberbullying classification agent.

Classify the current message into exactly one label:

green:
No harm, normal conversation, friendly joke, neutral message.

yellow:
Mild teasing, sarcasm, passive aggression, insult, or possibly harmful message.
No direct threat or severe harassment.

severe:
Direct harassment, threats, hate speech, sexual harassment, self-harm encouragement,
repeated targeted abuse, or severe humiliation.

Consider sender name, target name, current message, and recent context.

Return JSON only in this exact format:
{
  "label": "green" | "yellow" | "severe",
  "confidence": 0.0,
  "reason": "short reason",
  "recommended_action": "short action"
}"""


def _format_history(messages: list[ContextMessage]) -> str:
    if not messages:
        return "  (none)"
    return "\n".join(f"  - [{m.label}] {m.text!r}" for m in messages)


def build_user_prompt(text: str, sender_name: str, target_name: str | None, context: RecentContext) -> str:
    return (
        f"Sender: {sender_name}\n"
        f"Target: {target_name or '(group / no specific target)'}\n"
        f"Recent messages from sender:\n{_format_history(context.sender_recent)}\n"
        f"Recent messages from sender to this target:\n{_format_history(context.sender_to_target_recent)}\n"
        f"Current message: {text!r}"
    )
