"""EcoLogic Flask application factory."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from flask import Flask, Response

from .config import PROJECT_ROOT, DefaultConfig
from .database import AnalysisRepository, DatabaseError
from .errors import ApiError, error_response, register_error_handlers
from .providers import (
    AnalysisProvider,
    DemoProvider,
    OpenAIResponsesProvider,
    ProviderFailure,
    ProviderUnavailable,
)
from .rate_limit import BoundedRateLimiter
from .routes import api, web
from .schemas import SchemaValidationError
from .security import register_security
from .services import AnalysisNotFound, AnalysisService, UnsupportedTopic

_ALLOWED_ENVIRONMENTS = {"development", "testing", "production"}


def _validated_trusted_hosts(value: Any) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, (list, tuple)) or not value:
        raise RuntimeError("ECOLOGIC_TRUSTED_HOSTS must be a comma-separated host list.")
    hosts: list[str] = []
    for raw_host in value:
        if not isinstance(raw_host, str):
            raise RuntimeError("ECOLOGIC_TRUSTED_HOSTS entries must be strings.")
        host = raw_host.strip()
        if (
            not host
            or host == "*"
            or "://" in host
            or "/" in host
            or "\\" in host
            or any(character.isspace() for character in host)
        ):
            raise RuntimeError(
                "ECOLOGIC_TRUSTED_HOSTS entries must be hostnames without schemes or paths."
            )
        hosts.append(host)
    return hosts


def _build_provider(app: Flask) -> AnalysisProvider:
    injected = app.config.get("PROVIDER_INSTANCE")
    if injected is not None:
        return cast(AnalysisProvider, injected)
    mode = str(app.config["ANALYSIS_PROVIDER"]).strip().lower()
    if mode == "demo":
        return DemoProvider()
    if mode == "openai":
        return OpenAIResponsesProvider(
            api_key=str(app.config.get("OPENAI_API_KEY", "")),
            model=str(app.config.get("OPENAI_MODEL", "gpt-4o")),
            timeout_seconds=int(app.config.get("OPENAI_TIMEOUT_SECONDS", 45)),
        )
    raise RuntimeError("ECOLOGIC_PROVIDER must be either 'demo' or 'openai'.")


def _register_domain_errors(app: Flask) -> None:
    @app.errorhandler(SchemaValidationError)
    def schema_error(error: SchemaValidationError) -> Response:
        return error_response(
            ApiError(422, "validation_error", "The request did not pass validation.", error.issues)
        )

    @app.errorhandler(ProviderUnavailable)
    def provider_unavailable(_error: ProviderUnavailable) -> Response:
        return error_response(
            ApiError(
                503,
                "provider_unavailable",
                "The selected analysis provider is not available.",
            )
        )

    @app.errorhandler(ProviderFailure)
    def provider_failure(_error: ProviderFailure) -> Response:
        return error_response(
            ApiError(
                502,
                "provider_failure",
                "The analysis provider could not produce a valid result.",
            )
        )

    @app.errorhandler(DatabaseError)
    def database_failure(_error: DatabaseError) -> Response:
        return error_response(
            ApiError(
                503,
                "database_unavailable",
                "Analysis history is temporarily unavailable.",
            )
        )

    @app.errorhandler(AnalysisNotFound)
    def analysis_not_found(_error: AnalysisNotFound) -> Response:
        return error_response(
            ApiError(404, "analysis_not_found", "Analysis not found for this session.")
        )

    @app.errorhandler(UnsupportedTopic)
    def unsupported_topic(error: UnsupportedTopic) -> Response:
        return error_response(ApiError(422, "unsupported_topic", error.public_message))


def create_app(test_config: Mapping[str, Any] | None = None) -> Flask:
    instance_path = None
    if test_config and test_config.get("INSTANCE_PATH"):
        instance_path = str(test_config["INSTANCE_PATH"])
    app = Flask(
        __name__,
        instance_path=instance_path,
        instance_relative_config=True,
        template_folder=str(PROJECT_ROOT / "templates"),
        static_folder=str(PROJECT_ROOT / "static"),
    )
    app.config.from_object(DefaultConfig)
    if test_config:
        app.config.update(test_config)

    environment = str(app.config["ENVIRONMENT"]).strip().lower()
    if environment not in _ALLOWED_ENVIRONMENTS:
        allowed = ", ".join(sorted(_ALLOWED_ENVIRONMENTS))
        raise RuntimeError(f"ECOLOGIC_ENV must be one of: {allowed}.")
    trusted_hosts = _validated_trusted_hosts(app.config.get("TRUSTED_HOSTS"))
    app.config["TRUSTED_HOSTS"] = trusted_hosts
    if environment == "production":
        if bool(app.config.get("SECRET_KEY_EPHEMERAL")):
            raise RuntimeError("ECOLOGIC_SECRET_KEY is required in production.")
        configured_secret = app.config.get("SECRET_KEY", "")
        secret_bytes = (
            configured_secret
            if isinstance(configured_secret, bytes)
            else str(configured_secret).encode("utf-8")
        )
        if len(secret_bytes) < 32:
            raise RuntimeError("ECOLOGIC_SECRET_KEY must contain at least 32 bytes in production.")
        if not bool(app.config.get("SESSION_COOKIE_SECURE")):
            raise RuntimeError("Secure session cookies are required in production.")
        if not trusted_hosts:
            raise RuntimeError("ECOLOGIC_TRUSTED_HOSTS is required in production.")

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    database_value = str(app.config.get("DATABASE", "")).strip()
    database_path = (
        Path(database_value) if database_value else Path(app.instance_path) / "ecologic.sqlite3"
    )
    repository = AnalysisRepository(
        database_path,
        retention_days=int(app.config["HISTORY_RETENTION_DAYS"]),
    )
    repository.initialize()
    provider = _build_provider(app)
    service = AnalysisService(repository, provider)

    app.extensions["ecologic_repository"] = repository
    app.extensions["ecologic_service"] = service
    app.extensions["ecologic_rate_limiter"] = BoundedRateLimiter(
        max_keys=int(app.config["RATE_LIMIT_MAX_KEYS"])
    )
    app.json.sort_keys = False
    app.logger.setLevel(logging.INFO)

    register_error_handlers(app)
    _register_domain_errors(app)
    register_security(app)
    app.register_blueprint(web)
    app.register_blueprint(api)
    app.logger.info(
        "EcoLogic initialized environment=%s provider=%s live_calls_enabled=%s",
        environment,
        provider.info.mode,
        provider.info.live_calls_enabled,
    )
    return app
