"""Application services that join validation, providers, and persistence."""

from __future__ import annotations

import re
from typing import Any

from .database import AnalysisRecord, AnalysisRepository
from .providers import AnalysisProvider
from .schemas import AnalysisInput, ChatTurn

DISCLAIMER = (
    "Decision-support guidance is informational. It is not a professional inspection, "
    "safety clearance, financial estimate, or certification. Verify findings with measured "
    "data and a qualified person."
)


class AnalysisNotFound(LookupError):
    pass


class UnsupportedTopic(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.public_message = message


class AnalysisService:
    def __init__(self, repository: AnalysisRepository, provider: AnalysisProvider) -> None:
        self.repository = repository
        self.provider = provider

    def _provider_dict(self, record: AnalysisRecord | None = None) -> dict[str, Any]:
        if record is None:
            return self.provider.info.to_dict()
        return {
            "mode": record.provider_mode,
            "model": record.provider_model,
            "ready": True,
            "live_calls_enabled": record.provider_mode == "openai",
            "verification": "stored_validated_result",
        }

    def _public_analysis(self, record: AnalysisRecord) -> dict[str, Any]:
        result = record.result.to_dict()
        return {
            "id": record.id,
            "created_at": record.created_at,
            "locale": record.locale,
            "provider": self._provider_dict(record),
            **result,
            "disclaimer": DISCLAIMER,
        }

    def create_analysis(self, request: AnalysisInput, session_scope: str) -> dict[str, Any]:
        result = self.provider.analyze(request, session_scope)
        if result.kind == "refusal":
            raise UnsupportedTopic(result.message)
        info = self.provider.info
        record = self.repository.insert(
            session_scope=session_scope,
            input_text=request.text,
            locale=request.locale,
            provider_mode=info.mode,
            provider_model=info.model,
            result=result,
        )
        return self._public_analysis(record)

    def get_analysis(self, session_scope: str, analysis_id: int) -> AnalysisRecord:
        record = self.repository.get_for_session(session_scope, analysis_id)
        if record is None:
            raise AnalysisNotFound("Analysis not found for this session.")
        return record

    def history(self, session_scope: str, limit: int) -> list[dict[str, Any]]:
        records = self.repository.list_for_session(session_scope, limit)
        items: list[dict[str, Any]] = []
        for record in records:
            normalized_input = re.sub(r"\s+", " ", record.input_text).strip()
            excerpt = (
                normalized_input[:157] + "..." if len(normalized_input) > 160 else normalized_input
            )
            items.append(
                {
                    "id": record.id,
                    "created_at": record.created_at,
                    "category": record.result.category,
                    "risk_score": record.result.risk,
                    "input_excerpt": excerpt or "Image observation",
                    "result": self._public_analysis(record),
                }
            )
        return items

    def delete(self, session_scope: str, analysis_id: int) -> None:
        if not self.repository.delete_for_session(session_scope, analysis_id):
            raise AnalysisNotFound("Analysis not found for this session.")

    def clear(self, session_scope: str) -> int:
        return self.repository.clear_for_session(session_scope)

    def coach(self, session_scope: str, analysis_id: int) -> dict[str, Any]:
        record = self.get_analysis(session_scope, analysis_id)
        result = self.provider.coach(record.result, record.locale, session_scope)
        return {**result.to_dict(), "provider": self._provider_dict()}

    def chat(
        self,
        session_scope: str,
        analysis_id: int,
        message: str,
        history: tuple[ChatTurn, ...],
    ) -> dict[str, Any]:
        record = self.get_analysis(session_scope, analysis_id)
        result = self.provider.chat(
            record.result,
            message,
            history,
            record.locale,
            session_scope,
        )
        return {**result.to_dict(), "provider": self._provider_dict()}

    def health(self) -> dict[str, Any]:
        return {
            "database": {"ready": self.repository.health()},
            "provider": self.provider.info.to_dict(),
            "history": {"retention_days": self.repository.retention_days},
        }
