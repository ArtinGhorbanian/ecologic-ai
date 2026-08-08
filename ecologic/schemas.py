"""Strict request and provider-result contracts."""

from __future__ import annotations

import base64
import binascii
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


class SchemaValidationError(ValueError):
    def __init__(self, issues: list[str]) -> None:
        super().__init__("; ".join(issues))
        self.issues = issues


def _as_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError([f"{field} must be an object."])
    return value


def _reject_unknown(value: Mapping[str, Any], allowed: set[str], field: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise SchemaValidationError([f"{field} contains unknown fields: {', '.join(unknown)}."])


def _string(
    value: Any,
    field: str,
    *,
    minimum: int = 0,
    maximum: int = 1000,
) -> str:
    if not isinstance(value, str):
        raise SchemaValidationError([f"{field} must be a string."])
    normalized = value.strip()
    if len(normalized) < minimum:
        raise SchemaValidationError([f"{field} is too short."])
    if len(normalized) > maximum:
        raise SchemaValidationError([f"{field} exceeds {maximum} characters."])
    return normalized


def _integer(value: Any, field: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaValidationError([f"{field} must be an integer."])
    if not minimum <= value <= maximum:
        raise SchemaValidationError([f"{field} must be between {minimum} and {maximum}."])
    return value


_LOCALE_RE = re.compile(r"^[A-Za-z]{2,3}(?:[-_][A-Za-z]{2})?$")
_DATA_URL_RE = re.compile(
    r"^data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/]*={0,2})$",
    re.IGNORECASE,
)


def infer_locale(text: str) -> str:
    if re.search(r"[\u0600-\u06ff]", text):
        if re.search(r"[\u067e\u0686\u0698\u06af\u06cc\u06a9]", text):
            return "fa"
        return "ar"
    return "en"


def normalize_locale(value: Any, text: str) -> str:
    if value is None or value == "":
        return infer_locale(text)
    locale = _string(value, "locale", minimum=2, maximum=6)
    if not _LOCALE_RE.fullmatch(locale):
        raise SchemaValidationError(["locale must use a language code such as en, fa, or en-US."])
    parts = locale.replace("_", "-").split("-", 1)
    return parts[0].lower() if len(parts) == 1 else f"{parts[0].lower()}-{parts[1].upper()}"


def validate_image_data_url(value: Any, max_image_bytes: int) -> tuple[str, str]:
    data_url = _string(value, "image.data_url", minimum=24, maximum=max_image_bytes * 2)
    match = _DATA_URL_RE.fullmatch(data_url)
    if not match:
        raise SchemaValidationError(
            ["image.data_url must be a base64 PNG, JPEG, or WebP data URL."]
        )
    mime_type = match.group(1).lower()
    encoded = match.group(2)
    if len(encoded) > ((max_image_bytes + 2) // 3) * 4:
        raise SchemaValidationError(["image exceeds the configured decoded size limit."])
    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise SchemaValidationError(["image.data_url contains invalid base64 data."]) from exc
    if not image_bytes or len(image_bytes) > max_image_bytes:
        raise SchemaValidationError(["image exceeds the configured decoded size limit."])

    signatures = {
        "image/png": image_bytes.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/jpeg": image_bytes.startswith(b"\xff\xd8\xff"),
        "image/webp": image_bytes.startswith(b"RIFF")
        and len(image_bytes) >= 12
        and image_bytes[8:12] == b"WEBP",
    }
    if not signatures[mime_type]:
        raise SchemaValidationError(["image bytes do not match the declared media type."])
    return data_url, mime_type


@dataclass(frozen=True, slots=True)
class AnalysisInput:
    text: str
    locale: str
    image_data_url: str | None = None
    image_mime_type: str | None = None

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
        *,
        max_text_length: int,
        max_image_bytes: int,
    ) -> AnalysisInput:
        _reject_unknown(value, {"text", "locale", "image"}, "request")
        text = _string(
            value.get("text", ""),
            "text",
            minimum=1,
            maximum=max_text_length,
        )
        image_data_url: str | None = None
        image_mime_type: str | None = None
        image = value.get("image")
        if image is not None:
            image_object = _as_mapping(image, "image")
            _reject_unknown(image_object, {"data_url"}, "image")
            image_data_url, image_mime_type = validate_image_data_url(
                image_object.get("data_url"), max_image_bytes
            )
        return cls(
            text=text,
            locale=normalize_locale(value.get("locale"), text),
            image_data_url=image_data_url,
            image_mime_type=image_mime_type,
        )


@dataclass(frozen=True, slots=True)
class RoadmapStep:
    phase: str
    task: str
    detail: str

    @classmethod
    def from_mapping(cls, value: Any, index: int) -> RoadmapStep:
        item = _as_mapping(value, f"roadmap[{index}]")
        _reject_unknown(item, {"phase", "task", "detail"}, f"roadmap[{index}]")
        return cls(
            phase=_string(item.get("phase"), f"roadmap[{index}].phase", minimum=1, maximum=80),
            task=_string(item.get("task"), f"roadmap[{index}].task", minimum=1, maximum=160),
            detail=_string(item.get("detail"), f"roadmap[{index}].detail", minimum=1, maximum=500),
        )

    def to_dict(self) -> dict[str, str]:
        return {"phase": self.phase, "task": self.task, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    kind: str
    category: str
    analysis_mode: str
    risk: int
    risk_breakdown: dict[str, int]
    causes: tuple[str, ...]
    status: str
    message: str
    roadmap: tuple[RoadmapStep, ...]
    financial_potential: str
    iso_reference: str
    kpi_label: str
    confidence_note: str

    @classmethod
    def from_mapping(cls, value: Any) -> AnalysisResult:
        result = _as_mapping(value, "analysis result")
        fields = {
            "kind",
            "category",
            "analysis_mode",
            "risk",
            "risk_breakdown",
            "causes",
            "status",
            "message",
            "roadmap",
            "financial_potential",
            "iso_reference",
            "kpi_label",
            "confidence_note",
        }
        _reject_unknown(result, fields, "analysis result")
        kind = _string(result.get("kind"), "kind", minimum=1, maximum=16)
        if kind not in {"analysis", "refusal"}:
            raise SchemaValidationError(["kind must be analysis or refusal."])
        analysis_mode = _string(result.get("analysis_mode"), "analysis_mode", minimum=1, maximum=20)
        if analysis_mode not in {"consultation", "forensic", "unknown"}:
            raise SchemaValidationError(
                ["analysis_mode must be consultation, forensic, or unknown."]
            )

        breakdown_value = _as_mapping(result.get("risk_breakdown"), "risk_breakdown")
        breakdown_fields = {"financial_risk", "operational_risk", "safety_risk"}
        _reject_unknown(breakdown_value, breakdown_fields, "risk_breakdown")
        breakdown = {
            name: _integer(
                breakdown_value.get(name), f"risk_breakdown.{name}", minimum=0, maximum=100
            )
            for name in sorted(breakdown_fields)
        }

        causes_value = result.get("causes")
        if not isinstance(causes_value, list):
            raise SchemaValidationError(["causes must be an array."])
        if len(causes_value) > 5:
            raise SchemaValidationError(["causes may contain at most 5 items."])
        causes = tuple(
            _string(item, f"causes[{index}]", minimum=1, maximum=180)
            for index, item in enumerate(causes_value)
        )

        roadmap_value = result.get("roadmap")
        if not isinstance(roadmap_value, list):
            raise SchemaValidationError(["roadmap must be an array."])
        if len(roadmap_value) > 6:
            raise SchemaValidationError(["roadmap may contain at most 6 items."])
        roadmap = tuple(
            RoadmapStep.from_mapping(item, index) for index, item in enumerate(roadmap_value)
        )

        risk = _integer(result.get("risk"), "risk", minimum=0, maximum=100)
        if kind == "analysis" and (len(roadmap) != 6 or not causes):
            raise SchemaValidationError(
                ["An analysis must include at least one cause and exactly 6 roadmap steps."]
            )
        if kind == "analysis" and analysis_mode == "consultation" and risk != 0:
            raise SchemaValidationError(["A consultation analysis must have zero risk."])
        if kind == "analysis" and analysis_mode == "consultation" and any(breakdown.values()):
            raise SchemaValidationError(
                ["A consultation analysis must have an all-zero risk breakdown."]
            )
        if kind == "analysis" and analysis_mode == "forensic" and risk == 0:
            raise SchemaValidationError(["A forensic analysis must have a non-zero risk."])
        if kind == "analysis" and analysis_mode == "forensic" and not any(breakdown.values()):
            raise SchemaValidationError(
                ["A forensic analysis must have at least one non-zero risk component."]
            )
        if kind == "analysis" and analysis_mode == "unknown":
            raise SchemaValidationError(["A completed analysis may not use unknown mode."])
        if kind == "refusal" and analysis_mode != "unknown":
            raise SchemaValidationError(["A refusal must use unknown analysis mode."])
        if kind == "refusal" and (risk != 0 or roadmap or causes):
            raise SchemaValidationError(
                ["A refusal must have zero risk, no causes, and no roadmap steps."]
            )

        return cls(
            kind=kind,
            category=_string(result.get("category"), "category", minimum=1, maximum=80),
            analysis_mode=analysis_mode,
            risk=risk,
            risk_breakdown=breakdown,
            causes=causes,
            status=_string(result.get("status"), "status", minimum=1, maximum=120),
            message=_string(result.get("message"), "message", minimum=1, maximum=1200),
            roadmap=roadmap,
            financial_potential=_string(
                result.get("financial_potential"),
                "financial_potential",
                minimum=1,
                maximum=200,
            ),
            iso_reference=_string(
                result.get("iso_reference"), "iso_reference", minimum=1, maximum=120
            ),
            kpi_label=_string(result.get("kpi_label"), "kpi_label", minimum=1, maximum=160),
            confidence_note=_string(
                result.get("confidence_note"), "confidence_note", minimum=1, maximum=300
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "category": self.category,
            "analysis_mode": self.analysis_mode,
            "risk": self.risk,
            "risk_breakdown": dict(self.risk_breakdown),
            "causes": list(self.causes),
            "status": self.status,
            "message": self.message,
            "roadmap": [step.to_dict() for step in self.roadmap],
            "financial_potential": self.financial_potential,
            "iso_reference": self.iso_reference,
            "kpi_label": self.kpi_label,
            "confidence_note": self.confidence_note,
        }


@dataclass(frozen=True, slots=True)
class CoachResult:
    human_message: str
    eco_tip: str
    confidence_note: str

    @classmethod
    def from_mapping(cls, value: Any) -> CoachResult:
        item = _as_mapping(value, "coach result")
        _reject_unknown(item, {"human_message", "eco_tip", "confidence_note"}, "coach result")
        return cls(
            human_message=_string(
                item.get("human_message"), "human_message", minimum=1, maximum=600
            ),
            eco_tip=_string(item.get("eco_tip"), "eco_tip", minimum=1, maximum=300),
            confidence_note=_string(
                item.get("confidence_note"), "confidence_note", minimum=1, maximum=240
            ),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "human_message": self.human_message,
            "eco_tip": self.eco_tip,
            "confidence_note": self.confidence_note,
        }


@dataclass(frozen=True, slots=True)
class ChatTurn:
    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True, slots=True)
class ChatResult:
    reply: str

    @classmethod
    def from_mapping(cls, value: Any) -> ChatResult:
        item = _as_mapping(value, "chat result")
        _reject_unknown(item, {"reply"}, "chat result")
        return cls(reply=_string(item.get("reply"), "reply", minimum=1, maximum=1000))

    def to_dict(self) -> dict[str, str]:
        return {"reply": self.reply}


def parse_coach_request(value: Mapping[str, Any]) -> int:
    _reject_unknown(value, {"analysis_id"}, "request")
    return _integer(value.get("analysis_id"), "analysis_id", minimum=1, maximum=2**63 - 1)


def parse_chat_request(value: Mapping[str, Any]) -> tuple[int, str, tuple[ChatTurn, ...]]:
    _reject_unknown(value, {"analysis_id", "message", "history"}, "request")
    analysis_id = _integer(value.get("analysis_id"), "analysis_id", minimum=1, maximum=2**63 - 1)
    message = _string(value.get("message"), "message", minimum=1, maximum=1000)
    history_value = value.get("history", [])
    if not isinstance(history_value, list):
        raise SchemaValidationError(["history must be an array."])
    if len(history_value) > 6:
        raise SchemaValidationError(["history may contain at most 6 turns."])
    turns: list[ChatTurn] = []
    for index, raw_turn in enumerate(history_value):
        turn = _as_mapping(raw_turn, f"history[{index}]")
        _reject_unknown(turn, {"role", "content"}, f"history[{index}]")
        role = _string(turn.get("role"), f"history[{index}].role", minimum=1, maximum=9)
        if role not in {"user", "assistant"}:
            raise SchemaValidationError([f"history[{index}].role is not allowed."])
        content = _string(turn.get("content"), f"history[{index}].content", minimum=1, maximum=600)
        turns.append(ChatTurn(role, content))
    return analysis_id, message, tuple(turns)


_ROADMAP_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "phase": {"type": "string"},
        "task": {"type": "string"},
        "detail": {"type": "string"},
    },
    "required": ["phase", "task", "detail"],
}

ANALYSIS_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "kind": {"type": "string", "enum": ["analysis"]},
        "category": {"type": "string"},
        "analysis_mode": {
            "type": "string",
            "enum": ["consultation", "forensic"],
        },
        "risk": {"type": "integer", "minimum": 0, "maximum": 100},
        "risk_breakdown": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "financial_risk": {"type": "integer", "minimum": 0, "maximum": 100},
                "operational_risk": {"type": "integer", "minimum": 0, "maximum": 100},
                "safety_risk": {"type": "integer", "minimum": 0, "maximum": 100},
            },
            "required": ["financial_risk", "operational_risk", "safety_risk"],
        },
        "causes": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 5,
        },
        "status": {"type": "string"},
        "message": {"type": "string"},
        "roadmap": {
            "type": "array",
            "items": _ROADMAP_ITEM_SCHEMA,
            "minItems": 6,
            "maxItems": 6,
        },
        "financial_potential": {"type": "string"},
        "iso_reference": {"type": "string"},
        "kpi_label": {"type": "string"},
        "confidence_note": {"type": "string"},
    },
    "required": [
        "kind",
        "category",
        "analysis_mode",
        "risk",
        "risk_breakdown",
        "causes",
        "status",
        "message",
        "roadmap",
        "financial_potential",
        "iso_reference",
        "kpi_label",
        "confidence_note",
    ],
}

COACH_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "human_message": {"type": "string"},
        "eco_tip": {"type": "string"},
        "confidence_note": {"type": "string"},
    },
    "required": ["human_message", "eco_tip", "confidence_note"],
}

CHAT_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "reply": {"type": "string"},
    },
    "required": ["reply"],
}
