from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from url_audit.classify import BUCKET_BRIEF, BUCKET_NOT_WORKING, BUCKET_SEARCH
from url_audit.db_writeback import (
    WriteBackError,
    WriteBackTarget,
    apply_sqlite_writeback,
    bucket_should_remain_active,
    plan_sqlite_writeback,
    prompt_confirm,
    run_writeback,
)


def _create_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute(
        """
        CREATE TABLE incident_source (
            id INTEGER PRIMARY KEY,
            source_name TEXT,
            source_record_id TEXT UNIQUE,
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    conn.execute(
        "INSERT INTO incident_source (source_name, source_record_id, is_active) VALUES (?, ?, ?)",
        ("FAA_AIDS", "A1", 1),
    )
    conn.execute(
        "INSERT INTO incident_source (source_name, source_record_id, is_active) VALUES (?, ?, ?)",
        ("FAA_AIDS", "A2", 0),
    )
    conn.commit()
    conn.close()


def test_bucket_should_remain_active() -> None:
    assert bucket_should_remain_active(BUCKET_BRIEF, "brief") is True
    assert bucket_should_remain_active(BUCKET_SEARCH, "brief") is False
    assert bucket_should_remain_active(BUCKET_NOT_WORKING, "brief") is False
    assert bucket_should_remain_active(BUCKET_SEARCH, "search") is True
    assert bucket_should_remain_active(BUCKET_NOT_WORKING, "search") is False


def test_dry_run_performs_zero_writes(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    _create_db(db)
    url = f"sqlite:///{db}"
    results = [
        {"source_record_id": "A1", "bucket": BUCKET_NOT_WORKING},
        {"source_record_id": "A2", "bucket": BUCKET_BRIEF},
    ]
    target = WriteBackTarget(source_name="FAA_AIDS")
    summary = run_writeback(
        url,
        results,
        target=target,
        url_mode="brief",
        dry_run=True,
        assume_yes=True,
    )
    assert summary.true_to_false >= 1
    conn = sqlite3.connect(str(db))
    row = conn.execute(
        "SELECT is_active FROM incident_source WHERE source_record_id = 'A1'"
    ).fetchone()
    assert row[0] == 1
    conn.close()


def test_writeback_requires_confirmation(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    _create_db(db)
    url = f"sqlite:///{db}"
    results = [{"source_record_id": "A1", "bucket": BUCKET_NOT_WORKING}]
    target = WriteBackTarget(source_name="FAA_AIDS")

    run_writeback(
        url,
        results,
        target=target,
        url_mode="brief",
        confirm=lambda _msg: False,
    )

    conn = sqlite3.connect(str(db))
    assert conn.execute(
        "SELECT is_active FROM incident_source WHERE source_record_id = 'A1'"
    ).fetchone()[0] == 1
    conn.close()


def test_writeback_applies_when_confirmed(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    _create_db(db)
    url = f"sqlite:///{db}"
    results = [{"source_record_id": "A1", "bucket": BUCKET_NOT_WORKING}]
    target = WriteBackTarget(source_name="FAA_AIDS")

    run_writeback(
        url,
        results,
        target=target,
        url_mode="brief",
        confirm=lambda _msg: True,
    )

    conn = sqlite3.connect(str(db))
    assert conn.execute(
        "SELECT is_active FROM incident_source WHERE source_record_id = 'A1'"
    ).fetchone()[0] == 0
    conn.close()


def test_plan_and_apply(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    _create_db(db)
    conn = sqlite3.connect(str(db))
    target = WriteBackTarget(source_name="FAA_AIDS")
    results = [{"source_record_id": "A2", "bucket": BUCKET_BRIEF}]
    summary, changes = plan_sqlite_writeback(conn, results, target=target, url_mode="brief")
    assert summary.false_to_true == 1
    apply_sqlite_writeback(conn, changes, target=target)
    assert conn.execute(
        "SELECT is_active FROM incident_source WHERE source_record_id = 'A2'"
    ).fetchone()[0] == 1
    conn.close()


def test_unsupported_database_url() -> None:
    with pytest.raises(WriteBackError):
        run_writeback(
            "postgresql://localhost/db",
            [],
            target=WriteBackTarget(),
            url_mode="brief",
            dry_run=True,
        )


def test_prompt_confirm_default_no() -> None:
    assert prompt_confirm("test", confirm=lambda _m: False) is False
