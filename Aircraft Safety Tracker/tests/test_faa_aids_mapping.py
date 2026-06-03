"""FAA AIDS mapping gate tests (PRD 0007 FR-12.3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import db
from app.ingestion.faa_aids_mapping import (
    FaaAidsMakeModelMapping,
    bootstrap_create_approved_pages,
    load_faa_aids_make_model_mapping,
)
from app.ingestion.importers.faa_aids_importer import FAAAIDSImporter
from app.models import Aircraft, IncidentSource


def _write_mapping(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "mapping.jsonl"
    with path.open("w") as f:
        f.write("# test\n")
        for row in rows:
            f.write(json.dumps(row) + "\n")
    return path


def test_map_to_existing_by_model_name(app, tmp_path):
    with app.app_context():
        aircraft = Aircraft(manufacturer="Boeing", model_name="Boeing 757-200")
        db.session.add(aircraft)
        db.session.commit()

        path = _write_mapping(
            tmp_path,
            [
                {
                    "faa_make_model": "BOEING 757",
                    "canonical_model_name": "Boeing 757-200",
                    "action": "map_to_existing",
                }
            ],
        )
        mapping = load_faa_aids_make_model_mapping(path)
        assert mapping.resolve_aircraft_id("BOEING 757") == aircraft.id


def test_skip_action_returns_none(app, tmp_path):
    with app.app_context():
        path = _write_mapping(
            tmp_path,
            [
                {
                    "faa_make_model": "BOEING AG-1",
                    "canonical_model_name": "Boeing AG-1",
                    "action": "skip",
                },
                {
                    "faa_make_model": "BOEING 757",
                    "canonical_model_name": "Boeing 757-200",
                    "action": "map_to_existing",
                },
            ],
        )
        mapping = load_faa_aids_make_model_mapping(path)
        assert mapping.resolve_aircraft_id("BOEING AG-1") is None


def test_create_approved_idempotent(app, tmp_path):
    with app.app_context():
        path = _write_mapping(
            tmp_path,
            [
                {
                    "faa_make_model": "BOEING 787",
                    "canonical_model_name": "Boeing 787 Test Page",
                    "action": "create_approved",
                    "manufacturer": "Boeing",
                }
            ],
        )
        mapping = load_faa_aids_make_model_mapping(path)
        first = bootstrap_create_approved_pages(mapping, dry_run=False)
        second = bootstrap_create_approved_pages(mapping, dry_run=False)
        assert first["created_count"] == 1
        assert second["created_count"] == 0
        assert Aircraft.query.filter_by(model_name="Boeing 787 Test Page").count() == 1


def test_empty_jsonl_raises(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.write_text("# only header\n")
    with pytest.raises(ValueError, match="no mapping entries"):
        FaaAidsMakeModelMapping.load(path)


def test_importer_mapping_gate_skips_unmapped(app, tmp_path):
    with app.app_context():
        path = _write_mapping(
            tmp_path,
            [
                {
                    "faa_make_model": "BOEING 757",
                    "canonical_model_name": "Boeing 757-200",
                    "action": "map_to_existing",
                }
            ],
        )
        importer = FAAAIDSImporter(
            records=[
                {
                    "c5": "TEST001",
                    "c9": "01/15/2020",
                    "c23": "BOEING",
                    "c24": "737-800",
                    "c34": "0",
                }
            ],
            mapping=path,
        )
        assert importer.run() == 0
        assert "BOEING 737-800" in importer.skipped_unmapped


def test_importer_mapping_gate_writes_mapped(app, tmp_path):
    with app.app_context():
        aircraft = Aircraft(manufacturer="Airbus", model_name="Airbus A320")
        db.session.add(aircraft)
        db.session.commit()

        path = _write_mapping(
            tmp_path,
            [
                {
                    "faa_make_model": "AIRBUS A320",
                    "canonical_model_name": "Airbus A320",
                    "action": "map_to_existing",
                }
            ],
        )
        written = FAAAIDSImporter(
            records=[
                {
                    "c5": "TEST002",
                    "c9": "06/15/2020",
                    "c23": "AIRBUS",
                    "c24": "A320",
                    "c34": "0",
                }
            ],
            mapping=path,
        ).run()
        assert written == 1
        source = IncidentSource.query.filter_by(source_record_id="TEST002").one()
        assert source.incident.aircraft_id == aircraft.id
        assert source.source_data.get("faa_aids_make_model") == "AIRBUS A320"
