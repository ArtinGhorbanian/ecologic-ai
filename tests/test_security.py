from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from ecologic import create_app


def make_app(tmp_path: Path, **overrides):
    config = {
        "TESTING": True,
        "ENVIRONMENT": "testing",
        "SECRET_KEY": hashlib.sha256(b"ecologic-security-tests").hexdigest(),
        "SECRET_KEY_EPHEMERAL": False,
        "SESSION_COOKIE_SECURE": True,
        "INSTANCE_PATH": tmp_path / "instance",
        "DATABASE": str(tmp_path / "instance" / "test.sqlite3"),
        "ANALYSIS_PROVIDER": "demo",
        "ANALYSIS_RATE_LIMIT": 100,
        "COACH_RATE_LIMIT": 100,
        "CHAT_RATE_LIMIT": 100,
    }
    config.update(overrides)
    return create_app(config)


def csrf(client) -> str:
    response = client.get("/api/v1/session")
    assert response.status_code == 200
    return response.get_json()["csrf_token"]


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("post", "/api/v1/analyses", {"text": "How can I reduce energy use?"}),
        ("delete", "/api/v1/history/1", None),
        ("delete", "/api/v1/history", None),
        ("post", "/api/v1/coach", {"analysis_id": 1}),
        (
            "post",
            "/api/v1/chat",
            {"analysis_id": 1, "message": "What should I do first?", "history": []},
        ),
    ],
)
def test_every_mutating_route_rejects_missing_and_wrong_csrf(
    tmp_path: Path, method: str, path: str, payload: dict | None
) -> None:
    client = make_app(tmp_path).test_client()
    request_method = getattr(client, method)

    missing = request_method(path, json=payload)
    assert missing.status_code == 403
    assert missing.get_json()["error"]["code"] == "csrf_failed"

    csrf(client)
    wrong = request_method(path, json=payload, headers={"X-CSRF-Token": "wrong-token"})
    assert wrong.status_code == 403
    assert wrong.get_json()["error"]["code"] == "csrf_failed"


def test_coach_and_chat_cannot_cross_session_boundaries(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    owner = app.test_client()
    owner_token = csrf(owner)
    created = owner.post(
        "/api/v1/analyses",
        json={"text": "How can I reduce energy use?"},
        headers={"X-CSRF-Token": owner_token},
    )
    assert created.status_code == 201
    analysis_id = created.get_json()["analysis"]["id"]

    other = app.test_client()
    other_token = csrf(other)
    coach = other.post(
        "/api/v1/coach",
        json={"analysis_id": analysis_id},
        headers={"X-CSRF-Token": other_token},
    )
    chat = other.post(
        "/api/v1/chat",
        json={"analysis_id": analysis_id, "message": "Explain it", "history": []},
        headers={"X-CSRF-Token": other_token},
    )

    for response in (coach, chat):
        assert response.status_code == 404
        assert response.get_json()["error"]["code"] == "analysis_not_found"


def test_session_cookie_and_error_responses_keep_security_headers(tmp_path: Path) -> None:
    client = make_app(tmp_path).test_client()
    session_response = client.get("/api/v1/session")
    cookie = session_response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Secure" in cookie

    error_response = client.post("/api/v1/analyses", json={"text": "energy"})
    assert error_response.status_code == 403
    assert error_response.headers["Cache-Control"] == "no-store"
    assert error_response.headers["X-Content-Type-Options"] == "nosniff"
    assert error_response.headers["X-Frame-Options"] == "DENY"
    assert "unsafe-inline" not in error_response.headers["Content-Security-Policy"]
    assert "Access-Control-Allow-Origin" not in error_response.headers


def test_production_rejects_insecure_cookie_with_stable_secret(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Secure session cookies"):
        make_app(
            tmp_path,
            ENVIRONMENT="production",
            SECRET_KEY_EPHEMERAL=False,
            SESSION_COOKIE_SECURE=False,
        )
