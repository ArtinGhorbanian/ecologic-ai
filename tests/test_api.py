from __future__ import annotations

import base64
from pathlib import Path

import pytest

from ecologic import create_app
from ecologic.providers import ProviderFailure, ProviderInfo


def make_app(tmp_path: Path, **overrides):
    config = {
        "TESTING": True,
        "ENVIRONMENT": "testing",
        "SECRET_KEY": "test-secret-key-that-is-long-and-stable",
        "SECRET_KEY_EPHEMERAL": False,
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


def analyze(client, token: str, text: str = "How can I reduce energy use?"):
    return client.post(
        "/api/v1/analyses",
        json={"text": text},
        headers={"X-CSRF-Token": token},
    )


def test_health_and_session_are_truthful_and_hardened(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    client = app.test_client()

    health = client.get("/api/v1/health")
    assert health.status_code == 200
    body = health.get_json()
    assert body["status"] == "ok"
    assert body["live_provider_verified"] is False
    assert body["components"]["provider"] == {
        "mode": "demo",
        "model": None,
        "ready": True,
        "live_calls_enabled": False,
        "verification": "deterministic_local_rules",
    }
    assert "unsafe-inline" not in health.headers["Content-Security-Policy"]
    assert "cdn.jsdelivr" not in health.headers["Content-Security-Policy"]
    assert health.headers["X-Content-Type-Options"] == "nosniff"
    assert health.headers["Cache-Control"] == "no-store"

    session_response = client.get("/api/v1/session")
    assert len(session_response.get_json()["csrf_token"]) >= 32


def test_analysis_history_coach_chat_and_delete_are_session_scoped(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    owner = app.test_client()
    owner_token = csrf(owner)

    response = analyze(owner, owner_token)
    assert response.status_code == 201
    payload = response.get_json()
    analysis = payload["analysis"]
    assert payload["api_version"] == "1.0"
    assert analysis["risk"] == 0
    assert analysis["analysis_mode"] == "consultation"
    assert len(analysis["roadmap"]) == 6
    assert analysis["provider"]["live_calls_enabled"] is False
    analysis_id = analysis["id"]

    history = owner.get("/api/v1/history").get_json()["items"]
    assert len(history) == 1
    assert history[0]["id"] == analysis_id
    assert history[0]["result"]["locale"] == "en"

    other = app.test_client()
    other_token = csrf(other)
    assert other.get("/api/v1/history").get_json()["items"] == []
    denied_delete = other.delete(
        f"/api/v1/history/{analysis_id}", headers={"X-CSRF-Token": other_token}
    )
    assert denied_delete.status_code == 404

    coach_response = owner.post(
        "/api/v1/coach",
        json={"analysis_id": analysis_id},
        headers={"X-CSRF-Token": owner_token},
    )
    assert coach_response.status_code == 200
    assert set(coach_response.get_json()["coach"]) == {
        "human_message",
        "eco_tip",
        "confidence_note",
        "provider",
    }

    chat_response = owner.post(
        "/api/v1/chat",
        json={
            "analysis_id": analysis_id,
            "message": "What should I do first?",
            "history": [{"role": "user", "content": "Please explain the result."}],
        },
        headers={"X-CSRF-Token": owner_token},
    )
    assert chat_response.status_code == 200
    assert "reply" in chat_response.get_json()["chat"]

    deleted = owner.delete(f"/api/v1/history/{analysis_id}", headers={"X-CSRF-Token": owner_token})
    assert deleted.status_code == 200
    assert owner.get("/api/v1/history").get_json()["items"] == []


def test_mutations_require_csrf_and_strict_json(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    client = app.test_client()

    assert client.post("/api/v1/analyses", json={"text": "energy"}).status_code == 403
    token = csrf(client)
    wrong_type = client.post(
        "/api/v1/analyses",
        data="not-json",
        content_type="text/plain",
        headers={"X-CSRF-Token": token},
    )
    assert wrong_type.status_code == 415
    unknown = client.post(
        "/api/v1/analyses",
        json={"text": "energy", "unexpected": True},
        headers={"X-CSRF-Token": token},
    )
    assert unknown.status_code == 422
    assert unknown.get_json()["error"]["code"] == "validation_error"


def test_unsupported_topic_is_non_success_and_not_persisted(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    client = app.test_client()
    token = csrf(client)

    response = analyze(client, token, "Who won the football match?")
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "unsupported_topic"

    substring_response = analyze(client, token, "What is a chair?")
    assert substring_response.status_code == 422
    assert substring_response.get_json()["error"]["code"] == "unsupported_topic"
    assert client.get("/api/v1/history").get_json()["items"] == []


def test_image_contract_validates_media_signature(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    client = app.test_client()
    token = csrf(client)
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"safe-test-payload"
    data_url = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")

    image_only = client.post(
        "/api/v1/analyses",
        json={"image": {"data_url": data_url}},
        headers={"X-CSRF-Token": token},
    )
    assert image_only.status_code == 422
    assert image_only.get_json()["error"]["code"] == "validation_error"
    assert client.get("/api/v1/history").get_json()["items"] == []

    accepted = client.post(
        "/api/v1/analyses",
        json={"text": "Inspect this water leak", "image": {"data_url": data_url}},
        headers={"X-CSRF-Token": token},
    )
    assert accepted.status_code == 201
    assert accepted.get_json()["analysis"]["analysis_mode"] == "forensic"

    rejected = client.post(
        "/api/v1/analyses",
        json={
            "text": "Inspect this water leak",
            "image": {"data_url": "data:image/png;base64," + base64.b64encode(b"not-png").decode()},
        },
        headers={"X-CSRF-Token": token},
    )
    assert rejected.status_code == 422


def test_rate_limit_and_provider_failure_are_typed(tmp_path: Path) -> None:
    limited_app = make_app(tmp_path / "limited", ANALYSIS_RATE_LIMIT=1)
    client = limited_app.test_client()
    token = csrf(client)
    assert analyze(client, token).status_code == 201
    limited = analyze(client, token)
    assert limited.status_code == 429
    assert limited.get_json()["error"]["code"] == "rate_limit_exceeded"
    assert int(limited.headers["Retry-After"]) >= 1

    class FailingProvider:
        info = ProviderInfo("test", None, True, False, "deterministic_failure")

        def analyze(self, request, actor_id):
            raise ProviderFailure("private provider detail")

        def coach(self, analysis, locale, actor_id):
            raise ProviderFailure("private provider detail")

        def chat(self, analysis, message, history, locale, actor_id):
            raise ProviderFailure("private provider detail")

    failing_app = make_app(tmp_path / "failing", PROVIDER_INSTANCE=FailingProvider())
    failing_client = failing_app.test_client()
    failing_token = csrf(failing_client)
    failed = analyze(failing_client, failing_token)
    assert failed.status_code == 502
    assert failed.get_json()["error"]["code"] == "provider_failure"
    assert "private" not in failed.get_data(as_text=True)
    assert failing_client.get("/api/v1/history").get_json()["items"] == []


def test_production_fails_closed_without_stable_secure_sessions(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="ECOLOGIC_ENV"):
        make_app(tmp_path / "environment-typo", ENVIRONMENT="prod")

    with pytest.raises(RuntimeError, match="ECOLOGIC_SECRET_KEY"):
        make_app(
            tmp_path,
            ENVIRONMENT="production",
            SECRET_KEY_EPHEMERAL=True,
            SESSION_COOKIE_SECURE=False,
        )

    with pytest.raises(RuntimeError, match="ECOLOGIC_TRUSTED_HOSTS"):
        make_app(
            tmp_path / "missing-trusted-hosts",
            ENVIRONMENT="production",
            SECRET_KEY="a-production-secret-with-at-least-32-bytes",
            SECRET_KEY_EPHEMERAL=False,
            SESSION_COOKIE_SECURE=True,
            TRUSTED_HOSTS=None,
        )

    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        make_app(
            tmp_path / "short-secret",
            ENVIRONMENT="production",
            SECRET_KEY="guessable",
            SECRET_KEY_EPHEMERAL=False,
            SESSION_COOKIE_SECURE=True,
        )

    with pytest.raises(RuntimeError, match="Secure session cookies"):
        make_app(
            tmp_path / "insecure-cookie",
            ENVIRONMENT="production",
            SECRET_KEY="a-production-secret-with-at-least-32-bytes",
            SECRET_KEY_EPHEMERAL=False,
            SESSION_COOKIE_SECURE=False,
        )


def test_backend_public_text_has_no_common_mojibake_markers() -> None:
    root = Path(__file__).resolve().parent.parent
    markers = tuple(chr(value) for value in (0x00E2, 0x00D8, 0x00D9, 0x00F0, 0x00C3))
    files = [root / "app.py", root / "wsgi.py", *sorted((root / "ecologic").glob("*.py"))]
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert not any(marker in text for marker in markers), path
