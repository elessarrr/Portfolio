"""Tests for NTSB make_model mapping gate (FR-16 / FR-17)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app import db
from app.ingestion.ntsb_mapping import NtsbMakeModelMapping, bootstrap_create_approved_pages, load_ntsb_make_model_mapping
from app.ingestion.importers.ntsb_importer import NTSBImporter
from app.models import Aircraft, IncidentSource


def _write_mapping(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "mapping.jsonl"
    with path.open("w") as f:
        f.write("# test mapping\n")
        for row in rows:
            f.write(json.dumps(row) + "\n")
    return path


def test_load_mapping_rejects_duplicate(tmp_path):
    path = _write_mapping(
        tmp_path,
        [
            {
                "ntsb_make_model": "BOEING 737",
                "canonical_aircraft_id": None,
                "canonical_model_name": "Boeing 737",
                "action": "create_approved",
                "manufacturer": "Boeing",
            },
            {
                "ntsb_make_model": "BOEING 737",
                "canonical_aircraft_id": None,
                "canonical_model_name": "Boeing 737",
                "action": "create_approved",
                "manufacturer": "Boeing",
            },
        ],
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_ntsb_make_model_mapping(path)


def test_map_to_existing_by_model_name(app, tmp_path):
    with app.app_context():
        aircraft = Aircraft(manufacturer="Boeing", model_name="Boeing 757-200")
        db.session.add(aircraft)
        db.session.commit()

        path = _write_mapping(
            tmp_path,
            [
                {
                    "ntsb_make_model": "BOEING 757",
                    "canonical_aircraft_id": 99999,
                    "canonical_model_name": "Boeing 757-200",
                    "action": "map_to_existing",
                }
            ],
        )
        mapping = load_ntsb_make_model_mapping(path)
        assert mapping.resolve_aircraft_id("BOEING 757") == aircraft.id


def test_create_approved_idempotent(app, tmp_path):
    with app.app_context():
        path = _write_mapping(
            tmp_path,
            [
                {
                    "ntsb_make_model": "BOEING 787",
                    "canonical_aircraft_id": None,
                    "canonical_model_name": "Boeing 787",
                    "action": "create_approved",
                    "manufacturer": "Boeing",
                }
            ],
        )
        mapping = load_ntsb_make_model_mapping(path)
        first = mapping.resolve_aircraft_id("BOEING 787")
        second = mapping.resolve_aircraft_id("BOEING 787")
        assert first == second
        assert Aircraft.query.filter_by(model_name="Boeing 787").count() == 1


def test_importer_mapping_gate_skips_unmapped(app, tmp_path):
    with app.app_context():
        path = _write_mapping(
            tmp_path,
            [
                {
                    "ntsb_make_model": "BOEING 757",
                    "canonical_aircraft_id": None,
                    "canonical_model_name": "Boeing 757-200",
                    "action": "map_to_existing",
                }
            ],
        )
        importer = NTSBImporter(
            records=[
                {
                    "cm_ntsbNum": "ENG20FA011",
                    "cm_eventDate": "2020-06-15",
                    "cm_vehicles": [{"make": "Boeing", "model": "737-800"}],
                }
            ],
            mapping=path,
        )
        written = importer.run()
        assert written == 0
        assert importer.skipped_unmapped == ["Boeing 737-800"]
        assert IncidentSource.query.filter_by(source_record_id="ENG20FA011").count() == 0


def test_importer_mapping_gate_writes_mapped(app, tmp_path):
    with app.app_context():
        aircraft = Aircraft(manufacturer="Airbus", model_name="Airbus A320")
        db.session.add(aircraft)
        db.session.commit()

        path = _write_mapping(
            tmp_path,
            [
                {
                    "ntsb_make_model": "AIRBUS A320",
                    "canonical_aircraft_id": None,
                    "canonical_model_name": "Airbus A320",
                    "action": "map_to_existing",
                }
            ],
        )
        written = NTSBImporter(
            records=[
                {
                    "cm_ntsbNum": "ENG20FA012",
                    "cm_eventDate": "2020-06-15",
                    "cm_vehicles": [{"make": "AIRBUS", "model": "A320"}],
                }
            ],
            mapping=path,
        ).run()
        assert written == 1
        source = IncidentSource.query.filter_by(source_record_id="ENG20FA012").one()
        assert source.incident.aircraft_id == aircraft.id
        assert source.source_data.get("ntsb_make_model") == "AIRBUS A320"


def test_importer_idempotent_re_run_with_mapping(app, tmp_path):
    """FR-9.1 / Task 7.1: second run updates in place; no duplicate IncidentSource rows."""
    with app.app_context():
        aircraft = Aircraft(manufacturer="Boeing", model_name="Boeing 737-800")
        db.session.add(aircraft)
        db.session.commit()

        path = _write_mapping(
            tmp_path,
            [
                {
                    "ntsb_make_model": "Boeing 737-800",
                    "canonical_aircraft_id": aircraft.id,
                    "canonical_model_name": "Boeing 737-800",
                    "action": "map_to_existing",
                    "manufacturer": "Boeing",
                }
            ],
        )
        record = {
            "cm_ntsbNum": "ENG20FA099",
            "cm_eventDate": "2020-06-15",
            "cm_vehicles": [{"make": "Boeing", "model": "737-800"}],
            "_audit_source_url": "https://data.ntsb.gov/Docket/?NTSBNumber=ENG20FA099",
        }
        first = NTSBImporter(records=[record], mapping=path).run()
        second = NTSBImporter(records=[record], mapping=path).run()

        assert first == 1
        assert second == 1
        assert IncidentSource.query.filter_by(source_name="NTSB").count() == 1
        assert IncidentSource.query.filter_by(source_record_id="ENG20FA099").count() == 1


def test_importer_without_mapping_uses_legacy_auto_create(app):
    with app.app_context():
        written = NTSBImporter(
            records=[
                {
                    "cm_ntsbNum": "ENG20FA013",
                    "cm_eventDate": "2020-06-15",
                    "cm_vehicles": [{"make": "Boeing", "model": "737-900"}],
                }
            ]
        ).run()
        assert written == 1
        assert Aircraft.query.filter_by(model_name="Boeing 737-900").count() == 1


def test_bootstrap_create_approved_pages_creates_and_idempotent(app, tmp_path):
    with app.app_context():
        path = _write_mapping(
            tmp_path,
            [
                {
                    "ntsb_make_model": "BOEING 737",
                    "canonical_aircraft_id": None,
                    "canonical_model_name": "Boeing 737",
                    "action": "create_approved",
                    "manufacturer": "Boeing",
                },
                {
                    "ntsb_make_model": "BOEING 737-7H4",
                    "canonical_aircraft_id": None,
                    "canonical_model_name": "Boeing 737",
                    "action": "create_approved",
                    "manufacturer": "Boeing",
                },
                {
                    "ntsb_make_model": "BOEING 787",
                    "canonical_aircraft_id": None,
                    "canonical_model_name": "Boeing 787",
                    "action": "create_approved",
                    "manufacturer": "Boeing",
                },
            ],
        )
        mapping = load_ntsb_make_model_mapping(path)
        first = bootstrap_create_approved_pages(mapping, dry_run=False)
        assert first["target_count"] == 2
        assert first["created_count"] == 2
        assert first["already_existed_count"] == 0
        assert Aircraft.query.filter_by(model_name="Boeing 737").count() == 1
        assert Aircraft.query.filter_by(model_name="Boeing 787").count() == 1

        second = bootstrap_create_approved_pages(mapping, dry_run=False)
        assert second["created_count"] == 0
        assert second["already_existed_count"] == 2


def test_bootstrap_create_approved_dry_run_no_writes(app, tmp_path):
    with app.app_context():
        path = _write_mapping(
            tmp_path,
            [
                {
                    "ntsb_make_model": "BOEING 787",
                    "canonical_aircraft_id": None,
                    "canonical_model_name": "Boeing 787",
                    "action": "create_approved",
                    "manufacturer": "Boeing",
                }
            ],
        )
        mapping = load_ntsb_make_model_mapping(path)
        report = bootstrap_create_approved_pages(mapping, dry_run=True)
        assert report["created_count"] == 1
        assert Aircraft.query.filter_by(model_name="Boeing 787").count() == 0

