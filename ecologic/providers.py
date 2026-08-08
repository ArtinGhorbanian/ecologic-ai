"""Deterministic demo and opt-in OpenAI Responses API providers."""

from __future__ import annotations

import importlib.util
import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from .schemas import (
    ANALYSIS_JSON_SCHEMA,
    CHAT_JSON_SCHEMA,
    COACH_JSON_SCHEMA,
    AnalysisInput,
    AnalysisResult,
    ChatResult,
    ChatTurn,
    CoachResult,
    RoadmapStep,
    SchemaValidationError,
)


class ProviderError(RuntimeError):
    """Base exception for failures at the provider boundary."""


class ProviderUnavailable(ProviderError):
    """The selected provider is not configured locally."""


class ProviderFailure(ProviderError):
    """The provider failed or returned an invalid result."""


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    mode: str
    model: str | None
    ready: bool
    live_calls_enabled: bool
    verification: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "model": self.model,
            "ready": self.ready,
            "live_calls_enabled": self.live_calls_enabled,
            "verification": self.verification,
        }


class AnalysisProvider(Protocol):
    @property
    def info(self) -> ProviderInfo: ...

    def analyze(self, request: AnalysisInput, actor_id: str) -> AnalysisResult: ...

    def coach(self, analysis: AnalysisResult, locale: str, actor_id: str) -> CoachResult: ...

    def chat(
        self,
        analysis: AnalysisResult,
        message: str,
        history: tuple[ChatTurn, ...],
        locale: str,
        actor_id: str,
    ) -> ChatResult: ...


_ENVIRONMENTAL_TERMS = {
    "air",
    "carbon",
    "climate",
    "ecology",
    "electricity",
    "emission",
    "energy",
    "environment",
    "environmental",
    "fuel",
    "leak",
    "pollution",
    "recycl",
    "solar",
    "sustainab",
    "waste",
    "water",
    "آب",
    "انرژی",
    "پسماند",
    "محیط",
    "زیست",
    "استدام",
    "تلوث",
    "طاقة",
    "مياه",
}
_ENVIRONMENTAL_STEMS = {
    "ecolog",
    "emission",
    "environment",
    "pollut",
    "recycl",
    "sustainab",
}
_ADVICE_TERMS = {
    "advice",
    "better",
    "can i",
    "guide",
    "help",
    "how",
    "improve",
    "optimize",
    "reduce",
    "save",
    "tips",
    "what",
    "چگونه",
    "راهنما",
    "صرفه",
    "كيف",
    "نصيحة",
}
_DAMAGE_TERMS = {
    "broken",
    "critical",
    "damage",
    "danger",
    "failure",
    "flood",
    "hazard",
    "leak",
    "overheat",
    "rupture",
    "smoke",
    "خراب",
    "خطر",
    "نشتی",
    "تسرب",
}


class DemoProvider:
    """Explainable local provider. It performs no network requests."""

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            mode="demo",
            model=None,
            ready=True,
            live_calls_enabled=False,
            verification="deterministic_local_rules",
        )

    def _contains(
        self,
        text: str,
        terms: set[str],
        *,
        stems: set[str] | frozenset[str] = frozenset(),
    ) -> bool:
        normalized = text.casefold()
        tokens = set(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))
        if any(token.startswith(stem) for stem in stems for token in tokens):
            return True
        for term in terms:
            if " " in term:
                if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", normalized):
                    return True
            elif term in tokens:
                return True
        return False

    def _category(self, text: str) -> str:
        if self._contains(text, {"water", "leak", "flood", "آب", "نشتی", "مياه", "تسرب"}):
            return "WATER"
        if self._contains(text, {"energy", "electricity", "solar", "fuel", "انرژی", "طاقة"}):
            return "ENERGY"
        if self._contains(text, {"waste", "پسماند"}, stems={"recycl"}):
            return "WASTE"
        if self._contains(
            text,
            {"carbon", "climate", "تلوث"},
            stems={"emission", "pollut"},
        ):
            return "EMISSIONS"
        return "SUSTAINABILITY"

    def _roadmap(self, category: str, forensic: bool) -> tuple[RoadmapStep, ...]:
        first_task = "Isolate immediate hazards" if forensic else "Define the improvement objective"
        first_detail = (
            "Keep people clear of unsafe equipment and use a qualified professional "
            "for urgent hazards."
            if forensic
            else "State the desired outcome and identify the decision owner before "
            "changing the system."
        )
        return (
            RoadmapStep("Immediate", first_task, first_detail),
            RoadmapStep(
                "Observe",
                "Collect baseline evidence",
                f"Record representative {category.lower()} measurements, operating "
                "conditions, and dates.",
            ),
            RoadmapStep(
                "Verify",
                "Confirm the likely causes",
                "Compare observations with maintenance records and have a qualified "
                "person verify assumptions.",
            ),
            RoadmapStep(
                "Plan",
                "Choose a proportionate intervention",
                "Prioritize reversible actions and document cost, safety, and "
                "operational constraints.",
            ),
            RoadmapStep(
                "Implement",
                "Apply and document the selected action",
                "Record what changed, who approved it, and any controls required during "
                "implementation.",
            ),
            RoadmapStep(
                "Review",
                "Measure the outcome",
                "Repeat the baseline measurement and escalate if risk indicators do not improve.",
            ),
        )

    def analyze(self, request: AnalysisInput, actor_id: str) -> AnalysisResult:
        del actor_id
        text = request.text.strip()
        if not text or not self._contains(text, _ENVIRONMENTAL_TERMS, stems=_ENVIRONMENTAL_STEMS):
            refusal_messages = {
                "fa": "این ابزار فقط موضوعات محیط زیست و پایداری را بررسی می‌کند.",
                "ar": "هذه الأداة مخصصة لموضوعات البيئة والاستدامة فقط.",
            }
            return AnalysisResult(
                kind="refusal",
                category="OUT_OF_SCOPE",
                analysis_mode="unknown",
                risk=0,
                risk_breakdown={
                    "financial_risk": 0,
                    "operational_risk": 0,
                    "safety_risk": 0,
                },
                causes=(),
                status="Unsupported topic",
                message=refusal_messages.get(
                    request.locale.split("-", 1)[0],
                    "This tool only evaluates environmental and sustainability topics.",
                ),
                roadmap=(),
                financial_potential="Not applicable",
                iso_reference="Not applicable",
                kpi_label="Not applicable",
                confidence_note="No analysis was performed.",
            )

        category = self._category(text)
        is_advice = self._contains(text, _ADVICE_TERMS) and not self._contains(text, _DAMAGE_TERMS)
        forensic = request.image_data_url is not None or self._contains(text, _DAMAGE_TERMS)
        risk = 0
        if not is_advice:
            risk = 35
            if self._contains(text, {"leak", "flood", "rupture", "نشتی", "تسرب"}):
                risk += 20
            if self._contains(text, {"danger", "hazard", "smoke", "critical", "خطر"}):
                risk += 25
            if self._contains(text, {"high"}):
                risk += 10
            risk = min(risk, 90)

        if risk == 0:
            breakdown = {"financial_risk": 0, "operational_risk": 0, "safety_risk": 0}
            status = "Optimization opportunity"
            message = (
                f"Demo mode identified a {category.lower()} improvement opportunity. "
                "Measure a baseline before selecting an intervention."
            )
        else:
            safety_risk = min(100, risk if forensic else max(0, risk - 20))
            breakdown = {
                "financial_risk": max(0, risk - 15),
                "operational_risk": risk,
                "safety_risk": safety_risk,
            }
            status = "Qualified review recommended"
            message = (
                f"Demo rules identified a {category.lower()} observation that needs verification. "
                "Treat urgent hazards as a reason to stop work and contact a qualified "
                "professional."
            )

        causes = ["The observation has not yet been verified with measured baseline data"]
        if request.image_data_url is not None:
            causes.append("An image was supplied but still requires on-site confirmation")
        else:
            causes.append("Operating context and equipment history may change the assessment")

        return AnalysisResult(
            kind="analysis",
            category=category,
            analysis_mode="consultation" if risk == 0 else "forensic",
            risk=risk,
            risk_breakdown=breakdown,
            causes=tuple(causes),
            status=status,
            message=message,
            roadmap=self._roadmap(category, risk > 0),
            financial_potential="Requires measured site and cost data",
            iso_reference="Not assessed in demo mode",
            kpi_label="Establish and compare a measured baseline",
            confidence_note="Deterministic demo guidance; not independently verified.",
        )

    def coach(self, analysis: AnalysisResult, locale: str, actor_id: str) -> CoachResult:
        del locale, actor_id
        first_step = analysis.roadmap[0]
        return CoachResult(
            human_message=(
                f"Start with “{first_step.task}.” Complete that step before moving to "
                "later actions, "
                "and involve a qualified professional if safety may be affected."
            ),
            eco_tip="Capture a dated baseline so the result can be compared after the change.",
            confidence_note=(
                "Demo coaching is deterministic and has not been independently verified."
            ),
        )

    def chat(
        self,
        analysis: AnalysisResult,
        message: str,
        history: tuple[ChatTurn, ...],
        locale: str,
        actor_id: str,
    ) -> ChatResult:
        del message, history, locale, actor_id
        first_step = analysis.roadmap[0]
        return ChatResult(
            reply=(
                f"For this {analysis.category.lower()} result, begin with “{first_step.task}.” "
                f"{first_step.detail} This is deterministic demo guidance, not a live "
                "expert review."
            )
        )


_ANALYSIS_INSTRUCTIONS = """
You are EcoLogic, an environmental decision-support assistant. Return only the structured result.
The application has already restricted the request to environmental topics. For a consultation,
risk must be 0. For a reported failure or damage, assign a bounded non-zero risk only from stated
evidence. The analysis must contain exactly six practical roadmap steps. Never claim certification,
professional inspection, or measured confidence. Do not invent numeric savings. Use "Requires
measured site and cost data" when the request lacks measured financial inputs. State that results
require qualified human review.
""".strip()

_COACH_INSTRUCTIONS = """
Provide concise environmental coaching grounded only in the supplied validated analysis. Do not
invent measurements, savings, certification, or certainty. Mention qualified human review when
safety could be affected. Return only the structured result in the requested locale.
""".strip()

_CHAT_INSTRUCTIONS = """
Answer only about the supplied environmental analysis and its roadmap. Refuse unrelated topics.
Do not invent measurements, savings, certification, or certainty. Return only the structured result
in the requested locale.
""".strip()


class OpenAIResponsesProvider:
    """Opt-in official SDK adapter. Construction and health checks make no API calls."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int = 45,
        client: Any = None,
    ) -> None:
        self._api_key = api_key.strip()
        self._model = model.strip()
        self._timeout_seconds = timeout_seconds
        self._client = client
        self._sdk_available = client is not None or importlib.util.find_spec("openai") is not None

    @property
    def info(self) -> ProviderInfo:
        ready = bool(self._api_key and self._model and self._sdk_available)
        return ProviderInfo(
            mode="openai",
            model=self._model or None,
            ready=ready,
            live_calls_enabled=ready,
            verification="configured_not_live_verified" if ready else "not_configured",
        )

    def _get_client(self) -> Any:
        if not self.info.ready:
            raise ProviderUnavailable(
                "The OpenAI provider is selected but its local configuration is incomplete."
            )
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ProviderUnavailable("The OpenAI SDK is not installed.") from exc
            self._client = OpenAI(
                api_key=self._api_key,
                timeout=self._timeout_seconds,
                max_retries=1,
            )
        return self._client

    def _structured_call(
        self,
        *,
        instructions: str,
        input_items: list[dict[str, Any]],
        schema: dict[str, Any],
        schema_name: str,
        actor_id: str,
        max_output_tokens: int,
    ) -> Any:
        try:
            response = self._get_client().responses.create(
                model=self._model,
                instructions=instructions,
                input=input_items,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": schema_name,
                        "strict": True,
                        "schema": schema,
                    }
                },
                max_output_tokens=max_output_tokens,
                safety_identifier=actor_id[:64],
                store=False,
            )
            output_text = response.output_text
            if not isinstance(output_text, str) or not output_text:
                raise ProviderFailure("The provider returned no structured output.")
            return json.loads(output_text)
        except ProviderError:
            raise
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ProviderFailure("The provider returned an invalid structured result.") from exc
        except Exception as exc:
            raise ProviderFailure(
                "The configured provider could not complete the request."
            ) from exc

    def analyze(self, request: AnalysisInput, actor_id: str) -> AnalysisResult:
        domain_guard = DemoProvider().analyze(request, actor_id)
        if domain_guard.kind == "refusal":
            return domain_guard
        content: list[dict[str, Any]] = [
            {
                "type": "input_text",
                "text": json.dumps(
                    {
                        "locale": request.locale,
                        "observation": request.text or "Analyze the supplied environmental image.",
                    },
                    ensure_ascii=False,
                ),
            }
        ]
        if request.image_data_url is not None:
            content.append(
                {
                    "type": "input_image",
                    "image_url": request.image_data_url,
                    "detail": "high",
                }
            )
        raw = self._structured_call(
            instructions=_ANALYSIS_INSTRUCTIONS,
            input_items=[{"role": "user", "content": content}],
            schema=ANALYSIS_JSON_SCHEMA,
            schema_name="ecologic_analysis",
            actor_id=actor_id,
            max_output_tokens=2500,
        )
        try:
            return AnalysisResult.from_mapping(raw)
        except SchemaValidationError as exc:
            raise ProviderFailure("The provider result failed local validation.") from exc

    def coach(self, analysis: AnalysisResult, locale: str, actor_id: str) -> CoachResult:
        raw = self._structured_call(
            instructions=_COACH_INSTRUCTIONS,
            input_items=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {"locale": locale, "analysis": analysis.to_dict()}, ensure_ascii=False
                    ),
                }
            ],
            schema=COACH_JSON_SCHEMA,
            schema_name="ecologic_coach",
            actor_id=actor_id,
            max_output_tokens=500,
        )
        try:
            return CoachResult.from_mapping(raw)
        except SchemaValidationError as exc:
            raise ProviderFailure("The provider result failed local validation.") from exc

    def chat(
        self,
        analysis: AnalysisResult,
        message: str,
        history: tuple[ChatTurn, ...],
        locale: str,
        actor_id: str,
    ) -> ChatResult:
        raw = self._structured_call(
            instructions=_CHAT_INSTRUCTIONS,
            input_items=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "locale": locale,
                            "analysis": analysis.to_dict(),
                            "history": [turn.to_dict() for turn in history],
                            "question": message,
                        },
                        ensure_ascii=False,
                    ),
                }
            ],
            schema=CHAT_JSON_SCHEMA,
            schema_name="ecologic_chat",
            actor_id=actor_id,
            max_output_tokens=700,
        )
        try:
            return ChatResult.from_mapping(raw)
        except SchemaValidationError as exc:
            raise ProviderFailure("The provider result failed local validation.") from exc
