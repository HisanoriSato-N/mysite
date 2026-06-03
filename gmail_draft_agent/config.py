import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\'").strip('"')
        os.environ.setdefault(key, value)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    value = int(os.getenv(name, str(default)))
    if minimum is not None and value < minimum:
        return minimum
    if maximum is not None and value > maximum:
        return maximum
    return value


def _env_path(name: str, default: str) -> Path:
    return Path(os.getenv(name, default))


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "gmail-draft-agent"))
    database_path: Path = field(default_factory=lambda: _env_path("DATABASE_PATH", "data/agent.sqlite3"))
    poll_interval_seconds: int = field(default_factory=lambda: _env_int("POLL_INTERVAL_SECONDS", 300, 60))
    max_messages_per_run: int = field(default_factory=lambda: _env_int("MAX_MESSAGES_PER_RUN", 10, 1, 100))
    gmail_query: str = field(default_factory=lambda: os.getenv("GMAIL_QUERY", "in:inbox newer_than:1d -in:drafts -from:me"))
    google_credentials_file: Path = field(default_factory=lambda: _env_path("GOOGLE_CREDENTIALS_FILE", "credentials.json"))
    google_token_file: Path = field(default_factory=lambda: _env_path("GOOGLE_TOKEN_FILE", "token.json"))
    openai_api_key: str | None = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    responder_language: Literal["auto", "ja", "en"] = field(default_factory=lambda: os.getenv("RESPONDER_LANGUAGE", "auto"))
    responder_tone: str = field(default_factory=lambda: os.getenv("RESPONDER_TONE", "丁寧で簡潔なビジネス文体"))
    notification_webhook_url: str | None = field(default_factory=lambda: os.getenv("NOTIFICATION_WEBHOOK_URL"))
    notification_channel_name: str = field(default_factory=lambda: os.getenv("NOTIFICATION_CHANNEL_NAME", "mail-review"))
    draft_signature: str = field(default_factory=lambda: os.getenv("DRAFT_SIGNATURE", ""))
    dry_run: bool = field(default_factory=lambda: _env_bool("DRY_RUN", False))


@lru_cache
def get_settings() -> Settings:
    _load_dotenv()
    return Settings()
