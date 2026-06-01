"""Tests for NTSB dedupe re-pass with mapped aircraft_id (FR-18)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from app import db
from app.ingestion.ntsb_dedupe_repass import (
    load_working_link_rows,
    run_dedupe_repass,
)
from app.ingestion.ntsb_mapping import load_ntsb_make_model_mapping
from app.models import Aircraft, Incident


def _write_mapping(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "mapping.jsonl"
    with path.open("w") as f:
        f.write("# test mapping\n")
        for row in rows:
            f.write(json.dumps(row) + "\n")
    return path


def _write_audit_rows(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "audit_rows.jsonl"
    with path.open("w") as f:
        for row in rows:
            payload = {"bucket": "viable_with_working_link", **row}
            f.write(json.dumps(payload) + "\n")
    return path


def test_mapped_aircraft_id_enables_dedupe_audit_skipped(app, tmp_path):
    """Rows with unknown_aircraft at audit become ASN-covered after mapped re-pass."""
    with app.app_context():
        aircraft = Aircraft(manufacturer="Boeing", model_name="Boeing 737")
        db.session.add(aircraft)
        db.session.flush()

        asn = Incident(
            aircraft_id=aircraft.id,
            date=date(2020, 6, 15),
            operator="United Airlines",
            location="Denver, CO",
            fatalities=0,
            description="ASN baseline",
            incident_type="Accident",
            asn_url="https://aviation-safety.net/wikibase/12345",
        )
        db.session.add(asn)
        db.session.commit()

        mapping_path = _write_mapping(
            tmp_path,
            [
                {
                    "ntsb_make_model": "BOEING 737",
                    "canonical_aircraft_id": None,
                    "canonical_model_name": "Boeing 737",
                    "action": "map_to_existing",
                }
            ],
        )
        audit_path = _write_audit_rows(
            tmp_path,
            [
                {
                    "source_record_id": "ENG20FA100",
                    "make_model": "BOEING 737",
                    "date": "2020-06-15",
                    "operator": "United Airlines",
                    "location": "Denver, CO",
                    "fatalities": 0,
                    "unknown_aircraft": True,
                    "closest_asn_match": None,
                }
            ],
        )

        mapping = load_ntsb_make_model_mapping(mapping_path)
        working = load_working_link_rows(audit_path)
        report, normalized = run_dedupe_repass(working, mapping)

        assert report["newly_deduped_count"] == 1
        assert report["still_viable_count"] == 0
        assert normalized[0]["dedupe_repasse_status"] == "skip_asn_covered"
        assert normalized[0]["mapped_aircraft_id"] == aircraft.id
        assert normalized[0]["dedupe_repasse_closest_asn_match"]["incident_id"] == asn.id


def test_null_fatalities_coerced_like_import_skips_duplicate(app, tmp_path):
    """Null audit fatalities must score like import (0) so dupes are caught pre-import."""
    with app.app_context():
        aircraft = Aircraft(manufacturer="Boeing", model_name="Boeing 767-300")
        db.session.add(aircraft)
        db.session.flush()

        asn = Incident(
            aircraft_id=aircraft.id,
            date=date(2002, 4, 5),
            operator="Delta Air Lines",
            location="Atlanta, Georgia",
            fatalities=0,
            incident_type="Accident",
            asn_url="https://aviation-safety.net/wikibase/297434",
        )
        db.session.add(asn)
        db.session.commit()

        mapping_path = _write_mapping(
            tmp_path,
            [
                {
                    "ntsb_make_model": "Boeing 767-332ER",
                    "canonical_aircraft_id": aircraft.id,
                    "canonical_model_name": "Boeing 767-300",
                    "action": "map_to_existing",
                }
            ],
        )
        audit_path = _write_audit_rows(
            tmp_path,
            [
                {
                    "source_record_id": "ATL02LA075",
                    "make_model": "Boeing 767-332ER",
                    "date": "2002-04-05",
                    "operator": None,
                    "location": "Atlanta, GA",
                    "fatalities": None,
                    "unknown_aircraft": True,
                }
            ],
        )

        mapping = load_ntsb_make_model_mapping(mapping_path)
        report, normalized = run_dedupe_repass(
            load_working_link_rows(audit_path), mapping
        )

        assert normalized[0]["dedupe_repasse_status"] == "skip_asn_covered"
        assert report["newly_deduped_count"] == 1


def test_create_approved_pending_skips_dedupe_without_db_create(app, tmp_path):
    with app.app_context():
        mapping_path = _write_mapping(
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
        audit_path = _write_audit_rows(
            tmp_path,
            [
                {
                    "source_record_id": "ENG20FA101",
                    "make_model": "BOEING 787",
                    "date": "2020-06-15",
                    "operator": "Test Air",
                    "location": "Seattle, WA",
                    "fatalities": 0,
                    "unknown_aircraft": True,
                }
            ],
        )

        mapping = load_ntsb_make_model_mapping(mapping_path)
        report, normalized = run_dedupe_repass(
            load_working_link_rows(audit_path), mapping
        )

        assert report["skipped_pending_create"] == 1
        assert normalized[0]["dedupe_repasse_status"] == "skip_pending_create"
        assert Aircraft.query.filter_by(model_name="Boeing 787").count() == 0


def test_unmapped_string_marked_skip_unmapped(app, tmp_path):
    with app.app_context():
        mapping_path = _write_mapping(
            tmp_path,
            [
                {
                    "ntsb_make_model": "BOEING 737",
                    "canonical_aircraft_id": None,
                    "canonical_model_name": "Boeing 737",
                    "action": "map_to_existing",
                }
            ],
        )
        audit_path = _write_audit_rows(
            tmp_path,
            [
                {
                    "source_record_id": "ENG20FA102",
                    "make_model": "UNKNOWN TYPE",
                    "date": "2020-06-15",
                    "unknown_aircraft": True,
                }
            ],
        )
        mapping = load_ntsb_make_model_mapping(mapping_path)
        report, normalized = run_dedupe_repass(
            load_working_link_rows(audit_path), mapping
        )

        assert report["skipped_unmapped"] == 1
        assert normalized[0]["dedupe_repasse_status"] == "skip_unmapped"
