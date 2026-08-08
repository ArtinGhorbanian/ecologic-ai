from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ecologic.database import AnalysisRepository
from ecologic.providers import DemoProvider
from ecologic.schemas import AnalysisInput


def result_fixture():
    return DemoProvider().analyze(AnalysisInput("How can I save energy?", "en"), "actor")


def test_database_is_new_secure_and_session_scoped(tmp_path: Path) -> None:
    path = tmp_path / "instance" / "ecologic.sqlite3"
    repository = AnalysisRepository(path)
    repository.initialize()
    assert path.exists()
    assert repository.health()

    # Repository-owned connections apply the privacy and integrity pragmas.
    with closing(repository._connect()) as connection:
        assert connection.execute("PRAGMA secure_delete").fetchone()[0] == 1
        assert (
            connection.execute(
                "SELECT value FROM schema_metadata WHERE key='schema_version'"
            ).fetchone()[0]
            == "1"
        )

    long_input = "energy " * 200
    record = repository.insert(
        session_scope="owner-a",
        input_text=long_input,
        locale="en",
        provider_mode="demo",
        provider_model=None,
        result=result_fixture(),
    )
    assert record.created_at.endswith("Z")
    assert len(record.input_text) <= 500
    assert repository.get_for_session("owner-a", record.id) is not None
    assert repository.get_for_session("owner-b", record.id) is None
    assert repository.list_for_session("owner-b") == []
    assert not repository.delete_for_session("owner-b", record.id)
    assert repository.delete_for_session("owner-a", record.id)


def test_retention_purges_expired_records(tmp_path: Path) -> None:
    now = [datetime(2026, 1, 1, tzinfo=timezone.utc)]
    repository = AnalysisRepository(
        tmp_path / "retention.sqlite3",
        retention_days=1,
        clock=lambda: now[0],
    )
    repository.initialize()
    record = repository.insert(
        session_scope="owner",
        input_text="energy",
        locale="en",
        provider_mode="demo",
        provider_model=None,
        result=result_fixture(),
    )
    assert repository.get_for_session("owner", record.id) is not None

    now[0] += timedelta(days=2)
    assert repository.list_for_session("owner") == []
    assert repository.get_for_session("owner", record.id) is None


def test_clear_only_removes_current_session(tmp_path: Path) -> None:
    repository = AnalysisRepository(tmp_path / "clear.sqlite3")
    repository.initialize()
    for owner in ("owner-a", "owner-b"):
        repository.insert(
            session_scope=owner,
            input_text="energy",
            locale="en",
            provider_mode="demo",
            provider_model=None,
            result=result_fixture(),
        )
    assert repository.clear_for_session("owner-a") == 1
    assert repository.list_for_session("owner-a") == []
    assert len(repository.list_for_session("owner-b")) == 1
