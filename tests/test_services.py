from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from ecologic.providers import DemoProvider, OpenAIResponsesProvider, ProviderFailure
from ecologic.rate_limit import BoundedRateLimiter
from ecologic.schemas import (
    ANALYSIS_JSON_SCHEMA,
    CHAT_JSON_SCHEMA,
    COACH_JSON_SCHEMA,
    AnalysisInput,
    AnalysisResult,
    SchemaValidationError,
)


def test_demo_provider_is_deterministic_and_preserves_mode_invariants() -> None:
    provider = DemoProvider()
    advice = AnalysisInput("How can I save energy?", "en")
    first = provider.analyze(advice, "actor")
    second = provider.analyze(advice, "actor")

    assert first == second
    assert first.analysis_mode == "consultation"
    assert first.risk == 0
    assert len(first.roadmap) == 6
    assert provider.info.live_calls_enabled is False

    forensic = provider.analyze(AnalysisInput("Critical water leak", "en"), "actor")
    assert forensic.analysis_mode == "forensic"
    assert 1 <= forensic.risk <= 100
    assert len(forensic.roadmap) == 6

    out_of_scope = provider.analyze(AnalysisInput("What is a chair?", "en"), "actor")
    assert out_of_scope.kind == "refusal"

    advice_with_image = provider.analyze(
        AnalysisInput(
            "How can I save water?",
            "en",
            "data:image/png;base64,iVBORw0KGgo=",
            "image/png",
        ),
        "actor",
    )
    assert advice_with_image.analysis_mode == "consultation"
    assert advice_with_image.risk == 0
    assert advice_with_image.roadmap[0].task == "Define the improvement objective"


def test_analysis_result_enforces_consultation_and_forensic_risk() -> None:
    provider = DemoProvider()
    payload = provider.analyze(AnalysisInput("How can I save energy?", "en"), "actor").to_dict()
    payload["risk"] = 20
    with pytest.raises(SchemaValidationError, match="consultation"):
        AnalysisResult.from_mapping(payload)

    payload = provider.analyze(AnalysisInput("How can I save energy?", "en"), "actor").to_dict()
    payload["risk_breakdown"]["financial_risk"] = 20
    with pytest.raises(SchemaValidationError, match="all-zero risk breakdown"):
        AnalysisResult.from_mapping(payload)

    payload = provider.analyze(AnalysisInput("Water leak", "en"), "actor").to_dict()
    payload["risk"] = 0
    with pytest.raises(SchemaValidationError, match="forensic"):
        AnalysisResult.from_mapping(payload)

    payload = provider.analyze(AnalysisInput("Water leak", "en"), "actor").to_dict()
    payload["risk_breakdown"] = {
        "financial_risk": 0,
        "operational_risk": 0,
        "safety_risk": 0,
    }
    with pytest.raises(SchemaValidationError, match="non-zero risk component"):
        AnalysisResult.from_mapping(payload)


class FakeResponses:
    def __init__(self, output: dict) -> None:
        self.output = output
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=json.dumps(self.output))


class FakeClient:
    def __init__(self, output: dict) -> None:
        self.responses = FakeResponses(output)


def test_openai_adapter_uses_responses_structured_output_without_storage() -> None:
    expected = DemoProvider().analyze(AnalysisInput("How can I save energy?", "en"), "actor")
    client = FakeClient(expected.to_dict())
    provider = OpenAIResponsesProvider(
        api_key="test-key",
        model="gpt-4o",
        client=client,
    )

    result = provider.analyze(AnalysisInput("How can I save energy?", "en"), "actor-hash")
    assert result == expected
    call = client.responses.calls[0]
    assert call["store"] is False
    assert call["safety_identifier"] == "actor-hash"
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["strict"] is True
    assert call["input"][0]["content"][0]["type"] == "input_text"

    image_only_client = FakeClient(expected.to_dict())
    image_only_provider = OpenAIResponsesProvider(
        api_key="test-key",
        model="gpt-4o",
        client=image_only_client,
    )
    refusal = image_only_provider.analyze(
        AnalysisInput("", "en", "data:image/png;base64,iVBORw0KGgo=", "image/png"),
        "actor-hash",
    )
    assert refusal.kind == "refusal"
    assert image_only_client.responses.calls == []


def test_provider_schemas_exclude_unsupported_string_length_keywords() -> None:
    def keywords(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from keywords(child)
        elif isinstance(value, list):
            for child in value:
                yield from keywords(child)

    for schema in (ANALYSIS_JSON_SCHEMA, COACH_JSON_SCHEMA, CHAT_JSON_SCHEMA):
        assert {"minLength", "maxLength"}.isdisjoint(keywords(schema))


def test_openai_adapter_rejects_invalid_provider_output() -> None:
    provider = OpenAIResponsesProvider(
        api_key="test-key",
        model="gpt-4o",
        client=FakeClient({"unexpected": True}),
    )
    with pytest.raises(ProviderFailure):
        provider.analyze(AnalysisInput("energy use", "en"), "actor")


def test_rate_limiter_is_bounded_and_expires_windows() -> None:
    now = [100.0]
    limiter = BoundedRateLimiter(max_keys=2, clock=lambda: now[0])
    assert limiter.check("a", 1, 10).allowed
    assert not limiter.check("a", 1, 10).allowed
    limiter.check("b", 1, 10)
    limiter.check("c", 1, 10)
    assert len(limiter._events) == 2
    now[0] = 111.0
    assert limiter.check("a", 1, 10).allowed
