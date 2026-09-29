"""Pattern-based guardrail. Catches obvious cases; it is not the whole classifier."""

import re

from app.schemas.moderation_schema import RuleResult

_THREAT_VERB = r"(?:\s+will|'ll|\s+am\s+going\s+to|'m\s+going\s+to|\s+am\s+gonna|'m\s+gonna)"

SEVERE_PATTERNS: dict[str, re.Pattern[str]] = {
    "kill yourself": re.compile(r"\bkill\s+(?:your\s*self|urself)\b"),
    "kys": re.compile(r"\bkys\b"),
    "i hope you die": re.compile(r"\bi\s+hope\s+(?:you|u)\s+die\b"),
    "go die": re.compile(r"\bgo\s+die\b"),
    "nobody should let you live": re.compile(r"\bnobody\s+should\s+let\s+(?:you|u)\s+live\b"),
    "i will kill you": re.compile(rf"\bi{_THREAT_VERB}\s+kill\s+(?:you|u)\b"),
}

YELLOW_PATTERNS: dict[str, re.Pattern[str]] = {
    "useless": re.compile(r"\buseless\b"),
    "stupid": re.compile(r"\bstupid\b"),
    "idiot": re.compile(r"\bidiots?\b"),
    "loser": re.compile(r"\blosers?\b"),
    "dumb": re.compile(r"\bdumb\b"),
    "nobody likes you": re.compile(r"\bnobody\s+likes\s+(?:you|u)\b"),
}


def _normalize(text: str) -> str:
    return text.lower().replace("’", "'").replace("‘", "'")


def _find(patterns: dict[str, re.Pattern[str]], text: str) -> list[str]:
    return [name for name, pattern in patterns.items() if pattern.search(text)]


def check(text: str) -> RuleResult:
    normalized = _normalize(text)
    if severe := _find(SEVERE_PATTERNS, normalized):
        return RuleResult(label="severe", matches=severe)
    if yellow := _find(YELLOW_PATTERNS, normalized):
        return RuleResult(label="yellow", matches=yellow)
    return RuleResult(label="green")
