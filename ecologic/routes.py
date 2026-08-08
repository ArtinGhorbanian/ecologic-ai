"""HTTP routes for the versioned EcoLogic API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from flask import Blueprint, Response, current_app, jsonify, render_template, request

from .errors import ApiError, ValidationApiError
from .rate_limit import BoundedRateLimiter
from .schemas import AnalysisInput, SchemaValidationError, parse_chat_request, parse_coach_request
from .security import get_csrf_token, require_csrf, session_scope
from .services import AnalysisService

web = Blueprint("web", __name__)
api = Blueprint("api", __name__)


def _service() -> AnalysisService:
    return cast(AnalysisService, current_app.extensions["ecologic_service"])


def _limiter() -> BoundedRateLimiter:
    return cast(BoundedRateLimiter, current_app.extensions["ecologic_rate_limiter"])


def _json_object() -> Mapping[str, Any]:
    if not request.is_json:
        raise ApiError(
            415,
            "unsupported_media_type",
            "Use application/json for this endpoint.",
        )
    value = request.get_json(silent=True)
    if not isinstance(value, Mapping):
        raise ApiError(400, "invalid_json", "The request body must be a JSON object.")
    return value


def _enforce_limit(scope: str, name: str, limit_key: str, window_key: str) -> None:
    decision = _limiter().check(
        f"{scope}:{name}",
        int(current_app.config[limit_key]),
        int(current_app.config[window_key]),
    )
    if not decision.allowed:
        raise ApiError(
            429,
            "rate_limit_exceeded",
            "Too many requests. Try again later.",
            details={"retry_after_seconds": decision.retry_after},
            headers={"Retry-After": str(decision.retry_after)},
        )


def _api_payload(**values: Any) -> dict[str, Any]:
    return {"api_version": current_app.config["API_VERSION"], **values}


@web.get("/")
def index() -> str:
    return render_template("index.html")


@api.get("/api/v1/session")
def session_info() -> Response:
    return jsonify(
        _api_payload(
            csrf_token=get_csrf_token(),
            provider=_service().provider.info.to_dict(),
        )
    )


@api.get("/api/v1/health")
@api.get("/healthz")
def health() -> tuple[Response, int]:
    components = _service().health()
    ready = bool(components["database"]["ready"] and components["provider"]["ready"])
    payload = _api_payload(
        status="ok" if ready else "degraded",
        service="EcoLogic API",
        live_provider_verified=False,
        components=components,
    )
    return jsonify(payload), 200 if ready else 503


@api.post("/api/v1/analyses")
@api.post("/analyze")
@require_csrf
def create_analysis() -> tuple[Response, int]:
    scope = session_scope()
    _enforce_limit(scope, "analysis", "ANALYSIS_RATE_LIMIT", "ANALYSIS_RATE_WINDOW")
    try:
        analysis_input = AnalysisInput.from_mapping(
            _json_object(),
            max_text_length=int(current_app.config["MAX_TEXT_LENGTH"]),
            max_image_bytes=int(current_app.config["MAX_IMAGE_BYTES"]),
        )
    except SchemaValidationError as exc:
        raise ValidationApiError(exc.issues) from exc
    analysis = _service().create_analysis(analysis_input, scope)
    return jsonify(_api_payload(analysis=analysis)), 201


@api.get("/api/v1/history")
@api.get("/api/history")
def history() -> Response:
    raw_limit = request.args.get("limit", str(current_app.config["HISTORY_LIMIT"]))
    try:
        limit = int(raw_limit)
    except ValueError as exc:
        raise ValidationApiError(["limit must be an integer."]) from exc
    maximum = min(50, int(current_app.config["HISTORY_LIMIT"]))
    if not 1 <= limit <= maximum:
        raise ValidationApiError([f"limit must be between 1 and {maximum}."])
    return jsonify(_api_payload(items=_service().history(session_scope(), limit)))


@api.delete("/api/v1/history/<int:analysis_id>")
@api.delete("/api/history/<int:analysis_id>")
@require_csrf
def delete_history_item(analysis_id: int) -> Response:
    _service().delete(session_scope(), analysis_id)
    return jsonify(_api_payload(deleted=True, id=analysis_id))


@api.delete("/api/v1/history")
@require_csrf
def clear_history() -> Response:
    deleted = _service().clear(session_scope())
    return jsonify(_api_payload(deleted=deleted))


@api.post("/api/v1/coach")
@api.post("/eco_coach")
@require_csrf
def coach() -> Response:
    scope = session_scope()
    _enforce_limit(scope, "coach", "COACH_RATE_LIMIT", "COACH_RATE_WINDOW")
    try:
        analysis_id = parse_coach_request(_json_object())
    except SchemaValidationError as exc:
        raise ValidationApiError(exc.issues) from exc
    return jsonify(_api_payload(coach=_service().coach(scope, analysis_id)))


@api.post("/api/v1/chat")
@api.post("/api/chat")
@require_csrf
def chat() -> Response:
    scope = session_scope()
    _enforce_limit(scope, "chat", "CHAT_RATE_LIMIT", "CHAT_RATE_WINDOW")
    try:
        analysis_id, message, turns = parse_chat_request(_json_object())
    except SchemaValidationError as exc:
        raise ValidationApiError(exc.issues) from exc
    return jsonify(_api_payload(chat=_service().chat(scope, analysis_id, message, turns)))
