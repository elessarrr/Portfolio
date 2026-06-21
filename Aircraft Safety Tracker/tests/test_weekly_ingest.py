"""Weekly ingest orchestration tests — PRD 0012 Task 4.0.

Covers retry-with-backoff, ok vs partial status, and IngestionState upsert.
Source functions are injected so no network/DB-heavy work runs here.
"""

from __future__ import annotations

import pytest

from app import db
from app.ingestion.weekly_ingest import _run_with_retry, run_ingest
from app.models import IngestionState

NOSLEEP = lambda _s: None  # noqa: E731


def test_run_ingest_ok_sets_status_ok(app):
    with app.app_context():
        result = run_ingest(
            ntsb_fn=lambda: {"written": 1},
            asn_fn=lambda: {"new": 2},
            sleep=NOSLEEP,
        )
        assert result["status"] == "ok"
        state = IngestionState.query.first()
        assert state is not None
        assert state.last_run_status == "ok"
        assert state.last_run_at is not None


def test_retry_succeeds_on_third_attempt(app):
    attempts = {"n": 0}

    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("transient")
        return {"written": 5}

    with app.app_context():
        result = run_ingest(ntsb_fn=flaky, asn_fn=lambda: {}, sleep=NOSLEEP)
        assert attempts["n"] == 3
        assert result["status"] == "ok"
        assert IngestionState.query.first().last_run_status == "ok"


def test_all_retries_fail_marks_partial(app):
    def always_fail():
        raise RuntimeError("down")

    with app.app_context():
        result = run_ingest(ntsb_fn=always_fail, asn_fn=lambda: {"new": 1}, sleep=NOSLEEP)
        assert result["status"] == "partial"
        state = IngestionState.query.first()
        assert state.last_run_status == "partial"
        # last_run_at must still advance even on partial failure.
        assert state.last_run_at is not None


def test_last_run_at_updates_existing_row(app):
    with app.app_context():
        db.session.add(IngestionState(last_run_at=None, last_run_status="seed"))
        db.session.commit()
        run_ingest(ntsb_fn=lambda: {}, asn_fn=lambda: {}, sleep=NOSLEEP)
        rows = IngestionState.query.all()
        # Upsert, not insert: still a single row.
        assert len(rows) == 1
        assert rows[0].last_run_status == "ok"
        assert rows[0].last_run_at is not None


def test_run_with_retry_stops_after_max(app):
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        raise ValueError("x")

    result, ok = _run_with_retry(fn, "demo", max_retries=3, delay=0, sleep=NOSLEEP)
    assert ok is False
    assert result is None
    assert calls["n"] == 3
