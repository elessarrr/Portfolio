"""Schema tests for PRD 0012 — perpetual hosting hardening.

Covers the two new schema additions:
- `Aircraft.summary_generated_at` (AI summary cache TTL)
- `IngestionState` table (weekly ingest cron state)
"""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa

from app import db
from app.models import Aircraft, IngestionState


def test_aircraft_has_summary_generated_at_column():
    col = Aircraft.__table__.columns.get("summary_generated_at")
    assert col is not None, "Aircraft.summary_generated_at column must exist"
    assert isinstance(col.type, sa.DateTime), "summary_generated_at must be DateTime"
    assert col.nullable is True, "summary_generated_at must be nullable"


def test_aircraft_summary_generated_at_roundtrips(app):
    with app.app_context():
        now = datetime(2026, 6, 21, 12, 0, 0)
        a = Aircraft(manufacturer="Boeing", model_name="Boeing 737-800", summary_generated_at=now)
        db.session.add(a)
        db.session.commit()

        fetched = db.session.get(Aircraft, a.id)
        assert fetched.summary_generated_at == now


def test_ingestion_state_table_columns():
    cols = IngestionState.__table__.columns
    assert isinstance(cols["id"].type, sa.Integer)
    assert cols["id"].primary_key is True
    assert isinstance(cols["last_run_at"].type, sa.DateTime)
    assert cols["last_run_at"].nullable is True
    assert isinstance(cols["last_run_status"].type, sa.String)
    assert cols["last_run_status"].nullable is True


def test_ingestion_state_roundtrips(app):
    with app.app_context():
        now = datetime(2026, 6, 21, 2, 0, 0)
        row = IngestionState(last_run_at=now, last_run_status="ok")
        db.session.add(row)
        db.session.commit()

        fetched = db.session.get(IngestionState, row.id)
        assert fetched.last_run_at == now
        assert fetched.last_run_status == "ok"
