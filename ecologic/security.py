"""Session scoping, CSRF checks, request IDs, and response headers."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from flask import Flask, Response, current_app, g, request, session

from .errors import ApiError

ViewFunction = TypeVar("ViewFunction", bound=Callable[..., Any])


def _secret_bytes() -> bytes:
    secret = current_app.config["SECRET_KEY"]
    if isinstance(secret, bytes):
        return secret
    return str(secret).encode("utf-8")


def ensure_session_id() -> str:
    session_id = session.get("session_id")
    if not isinstance(session_id, str) or len(session_id) < 32:
        session_id = secrets.token_urlsafe(32)
        session["session_id"] = session_id
    session.permanent = True
    return session_id


def session_scope() -> str:
    """Return a non-reversible database scope for the signed browser session."""
    return hmac.new(
        _secret_bytes(), ensure_session_id().encode("utf-8"), hashlib.sha256
    ).hexdigest()


def get_csrf_token() -> str:
    token = session.get("csrf_token")
    if not isinstance(token, str) or len(token) < 32:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    ensure_session_id()
    return token


def require_csrf(view: ViewFunction) -> ViewFunction:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        expected = session.get("csrf_token")
        supplied = request.headers.get("X-CSRF-Token", "")
        if (
            not isinstance(expected, str)
            or not supplied
            or not hmac.compare_digest(expected, supplied)
        ):
            raise ApiError(403, "csrf_failed", "A valid CSRF token is required.")
        return view(*args, **kwargs)

    return cast(ViewFunction, wrapped)


def register_security(app: Flask) -> None:
    @app.before_request
    def assign_request_id() -> None:
        g.request_id = secrets.token_hex(12)

    @app.after_request
    def add_security_headers(response: Response) -> Response:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = app.config["CONTENT_SECURITY_POLICY"]
        response.headers["Permissions-Policy"] = (
            "camera=(), geolocation=(), payment=(), usb=(), microphone=(self)"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["X-Request-ID"] = getattr(g, "request_id", "unavailable")
        if request.path.startswith("/api") or request.path in {"/analyze", "/eco_coach"}:
            response.headers["Cache-Control"] = "no-store"
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
