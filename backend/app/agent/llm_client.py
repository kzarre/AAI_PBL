import json
import logging
from functools import lru_cache
from typing import Any

from groq import Groq

from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Thin wrapper around Groq chat completions that returns parsed JSON or None."""

    def __init__(self, api_key: str, model: str, timeout: float) -> None:
        self._client = Groq(api_key=api_key, timeout=timeout)
        self._model = model

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
            data = json.loads(response.choices[0].message.content or "")
        except Exception as exc:  # network, auth, rate limit, bad JSON...
            logger.warning("LLM call failed: %s", exc)
            return None
        return data if isinstance(data, dict) else None


@lru_cache(maxsize=4)
def _build_client(api_key: str, model: str, timeout: float) -> LLMClient:
    return LLMClient(api_key, model, timeout)


def get_llm_client() -> LLMClient | None:
    if not settings.groq_api_key:
        return None
    return _build_client(settings.groq_api_key, settings.groq_model, settings.llm_timeout_seconds)
