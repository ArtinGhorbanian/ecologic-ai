"""Typed, non-sensitive API errors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from flask import Flask, Response, current_app, g, jsonify, request
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge


@dataclass(slots=True)
class ApiError(Exception):
    status: int
    code: str
    message: str
    details: Any = None
    headers: dict[str, str] = field(default_factory=dict)


class ValidationApiError(ApiError):
    def __init__(self, details: list[str] | None = None) -> None:
        super().__init__(422, "validation_error", "The request did not pass validation.", details)


def error_response(error: ApiError) -> Response:
    request_id = getattr(g, "request_id", "unavailable")
    payload: dict[str, Any] = {
        "api_version": current_app.config["API_VERSION"],
        "error": {
            "code": error.code,
            "message": error.message,
            "request_id": request_id,
        },
    }
    if error.details is not None:
        payload["error"]["details"] = error.details
    response = jsonify(payload)
    response.status_code = error.status
    for name, value in error.headers.items():
        response.headers[name] = value
    return response


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError) -> Response:
        return error_response(error)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_too_large(_error: RequestEntityTooLarge) -> Response:
        return error_response(
            ApiError(413, "request_too_large", "The request exceeds the configured size limit.")
        )

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException) -> ResponseReturnValue:
        if not request.path.startswith("/api") and request.path not in {"/analyze", "/eco_coach"}:
            return error
        status = error.code or 500
        return error_response(ApiError(status, error.name.lower().replace(" ", "_"), error.name))

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> ResponseReturnValue:
        request_id = getattr(g, "request_id", "unavailable")
        app.logger.exception(
            "Unhandled request failure request_id=%s error_type=%s",
            request_id,
            type(error).__name__,
        )
        if not request.path.startswith("/api") and request.path not in {"/analyze", "/eco_coach"}:
            return "Internal Server Error", 500
        return error_response(
            ApiError(500, "internal_error", "The server could not complete the request.")
        )
