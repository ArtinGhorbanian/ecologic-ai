"""Session-scoped SQLite persistence in the Flask instance directory."""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Callable
from contextlib import closing, suppress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .schemas import AnalysisResult, SchemaValidationError

SCHEMA_VERSION = 1
MAX_STORED_INPUT_CHARS = 500


class DatabaseError(RuntimeError):
    pass


class DatabaseIntegrityError(DatabaseError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_utc(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc)
    return normalized.isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class AnalysisRecord:
    id: int
    session_scope: str
    created_at: str
    expires_at: str
    input_text: str
    locale: str
    provider_mode: str
    provider_model: str | None
    result: AnalysisResult


class AnalysisRepository:
    def __init__(
        self,
        path: str | Path,
        *,
        retention_days: int = 30,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        if retention_days < 1:
            raise ValueError("retention_days must be positive")
        self.path = Path(path)
        self.retention_days = retention_days
        self._clock = clock

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA secure_delete = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA trusted_schema = OFF")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_scope TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    input_text TEXT NOT NULL,
                    locale TEXT NOT NULL,
                    provider_mode TEXT NOT NULL,
                    provider_model TEXT,
                    category TEXT NOT NULL,
                    risk_score INTEGER NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
                    result_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS analyses_session_id_idx
                    ON analyses(session_scope, id DESC);
                CREATE INDEX IF NOT EXISTS analyses_expiry_idx
                    ON analyses(expires_at);
                """
            )
            version_row = connection.execute(
                "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
            ).fetchone()
            if version_row is None:
                connection.execute(
                    "INSERT INTO schema_metadata(key, value) VALUES('schema_version', ?)",
                    (str(SCHEMA_VERSION),),
                )
            elif version_row["value"] != str(SCHEMA_VERSION):
                raise DatabaseError("Unsupported EcoLogic database schema version.")
            connection.commit()
        with suppress(OSError):
            os.chmod(self.path, 0o600)

    def insert(
        self,
        *,
        session_scope: str,
        input_text: str,
        locale: str,
        provider_mode: str,
        provider_model: str | None,
        result: AnalysisResult,
    ) -> AnalysisRecord:
        now = self._clock().astimezone(timezone.utc)
        created_at = format_utc(now)
        expires_at = format_utc(now + timedelta(days=self.retention_days))
        serialized = json.dumps(result.to_dict(), ensure_ascii=False, separators=(",", ":"))
        minimized_input = " ".join(input_text.split())[:MAX_STORED_INPUT_CHARS]
        with closing(self._connect()) as connection:
            connection.execute("DELETE FROM analyses WHERE expires_at <= ?", (created_at,))
            cursor = connection.execute(
                """
                INSERT INTO analyses(
                    session_scope, created_at, expires_at, input_text, locale,
                    provider_mode, provider_model, category, risk_score, result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_scope,
                    created_at,
                    expires_at,
                    minimized_input,
                    locale,
                    provider_mode,
                    provider_model,
                    result.category,
                    result.risk,
                    serialized,
                ),
            )
            if cursor.lastrowid is None:
                raise DatabaseError("SQLite did not return an analysis record identifier.")
            record_id = cursor.lastrowid
            connection.commit()
        return AnalysisRecord(
            id=record_id,
            session_scope=session_scope,
            created_at=created_at,
            expires_at=expires_at,
            input_text=minimized_input,
            locale=locale,
            provider_mode=provider_mode,
            provider_model=provider_model,
            result=result,
        )

    def _record_from_row(self, row: sqlite3.Row) -> AnalysisRecord:
        try:
            raw_result = json.loads(row["result_json"])
            result = AnalysisResult.from_mapping(raw_result)
        except (json.JSONDecodeError, SchemaValidationError, TypeError) as exc:
            raise DatabaseIntegrityError("Stored analysis data failed validation.") from exc
        return AnalysisRecord(
            id=int(row["id"]),
            session_scope=str(row["session_scope"]),
            created_at=str(row["created_at"]),
            expires_at=str(row["expires_at"]),
            input_text=str(row["input_text"]),
            locale=str(row["locale"]),
            provider_mode=str(row["provider_mode"]),
            provider_model=(
                str(row["provider_model"]) if row["provider_model"] is not None else None
            ),
            result=result,
        )

    def get_for_session(self, session_scope: str, record_id: int) -> AnalysisRecord | None:
        now = format_utc(self._clock())
        with closing(self._connect()) as connection:
            connection.execute("DELETE FROM analyses WHERE expires_at <= ?", (now,))
            row = connection.execute(
                "SELECT * FROM analyses WHERE id = ? AND session_scope = ?",
                (record_id, session_scope),
            ).fetchone()
            connection.commit()
        return None if row is None else self._record_from_row(row)

    def list_for_session(self, session_scope: str, limit: int = 10) -> list[AnalysisRecord]:
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        now = format_utc(self._clock())
        with closing(self._connect()) as connection:
            connection.execute("DELETE FROM analyses WHERE expires_at <= ?", (now,))
            rows = connection.execute(
                "SELECT * FROM analyses WHERE session_scope = ? ORDER BY id DESC LIMIT ?",
                (session_scope, limit),
            ).fetchall()
            connection.commit()
        records: list[AnalysisRecord] = []
        for row in rows:
            try:
                records.append(self._record_from_row(row))
            except DatabaseIntegrityError:
                continue
        return records

    def delete_for_session(self, session_scope: str, record_id: int) -> bool:
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                "DELETE FROM analyses WHERE id = ? AND session_scope = ?",
                (record_id, session_scope),
            )
            deleted = cursor.rowcount == 1
            connection.commit()
        return deleted

    def clear_for_session(self, session_scope: str) -> int:
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                "DELETE FROM analyses WHERE session_scope = ?", (session_scope,)
            )
            deleted = max(0, cursor.rowcount)
            connection.commit()
        return deleted

    def purge_expired(self) -> int:
        now = format_utc(self._clock())
        with closing(self._connect()) as connection:
            cursor = connection.execute("DELETE FROM analyses WHERE expires_at <= ?", (now,))
            deleted = max(0, cursor.rowcount)
            connection.commit()
        return deleted

    def health(self) -> bool:
        try:
            with closing(self._connect()) as connection:
                row = connection.execute(
                    "SELECT value FROM schema_metadata WHERE key = ?", ("schema_version",)
                ).fetchone()
            return row is not None and row["value"] == str(SCHEMA_VERSION)
        except sqlite3.Error:
            return False
