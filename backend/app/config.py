import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass
class Settings:
    app_name: str = "Cyberbullying Moderation Service"
    database_url: str = field(default_factory=lambda: _env("DATABASE_URL", "sqlite:///./moderation.db"))
    groq_api_key: str | None = field(default_factory=lambda: _env("GROQ_API_KEY") or None)
    groq_model: str = field(default_factory=lambda: _env("GROQ_MODEL", "openai/gpt-oss-120b"))
    llm_timeout_seconds: float = field(default_factory=lambda: float(_env("LLM_TIMEOUT_SECONDS", "10")))
    recent_context_limit: int = field(default_factory=lambda: int(_env("RECENT_CONTEXT_LIMIT", "10")))


settings = Settings()
