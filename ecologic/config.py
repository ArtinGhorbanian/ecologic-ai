"""Configuration helpers with conservative local defaults."""

from __future__ import annotations

import os
import secrets
from datetime import timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(parsed, minimum)


def _env_list(name: str) -> list[str] | None:
    value = os.getenv(name, "").strip()
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def load_local_environment() -> None:
    """Load a local .env without overriding process-level configuration."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(PROJECT_ROOT / ".env", override=False)


load_local_environment()


class DefaultConfig:
    """Flask defaults. Production deployments should override secrets explicitly."""

    API_VERSION = "1.0"
    ENVIRONMENT = os.getenv("ECOLOGIC_ENV", "development").strip().lower()

    _configured_secret = os.getenv("ECOLOGIC_SECRET_KEY", "").strip()
    SECRET_KEY = _configured_secret or secrets.token_urlsafe(48)
    SECRET_KEY_EPHEMERAL = not bool(_configured_secret)

    SESSION_COOKIE_NAME = "ecologic_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("ECOLOGIC_SECURE_COOKIES", False)
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    TRUSTED_HOSTS = _env_list("ECOLOGIC_TRUSTED_HOSTS")

    DATABASE = os.getenv("ECOLOGIC_DATABASE", "").strip()
    HISTORY_RETENTION_DAYS = _env_int("ECOLOGIC_HISTORY_RETENTION_DAYS", 30)
    HISTORY_LIMIT = _env_int("ECOLOGIC_HISTORY_LIMIT", 10)

    ANALYSIS_PROVIDER = os.getenv("ECOLOGIC_PROVIDER", "demo").strip().lower()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o").strip()
    OPENAI_TIMEOUT_SECONDS = _env_int("OPENAI_TIMEOUT_SECONDS", 45)

    MAX_CONTENT_LENGTH = _env_int("ECOLOGIC_MAX_REQUEST_BYTES", 3 * 1024 * 1024)
    MAX_TEXT_LENGTH = _env_int("ECOLOGIC_MAX_TEXT_LENGTH", 4000)
    MAX_IMAGE_BYTES = _env_int("ECOLOGIC_MAX_IMAGE_BYTES", 2 * 1024 * 1024)

    ANALYSIS_RATE_LIMIT = _env_int("ECOLOGIC_ANALYSIS_RATE_LIMIT", 10)
    ANALYSIS_RATE_WINDOW = _env_int("ECOLOGIC_ANALYSIS_RATE_WINDOW", 60)
    COACH_RATE_LIMIT = _env_int("ECOLOGIC_COACH_RATE_LIMIT", 15)
    COACH_RATE_WINDOW = _env_int("ECOLOGIC_COACH_RATE_WINDOW", 3600)
    CHAT_RATE_LIMIT = _env_int("ECOLOGIC_CHAT_RATE_LIMIT", 30)
    CHAT_RATE_WINDOW = _env_int("ECOLOGIC_CHAT_RATE_WINDOW", 60)
    RATE_LIMIT_MAX_KEYS = _env_int("ECOLOGIC_RATE_LIMIT_MAX_KEYS", 2048)

    CONTENT_SECURITY_POLICY = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "font-src 'self'; "
        "img-src 'self' data: blob:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'none'; "
        "frame-ancestors 'none'; "
        "form-action 'self'"
    )

    JSON_SORT_KEYS = False
    PROPAGATE_EXCEPTIONS = False
