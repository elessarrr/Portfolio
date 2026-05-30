"""FR-10.6: NTSB audit JSONL export tests."""

import importlib.util
import json
import os
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from app import db
from app.ingestion.audit_export import (
    count_export_buckets,
    export_row,
    validate_export_against_report,
    write_export_row,
)
from app.models import Aircraft, Incident

_ROOT = Path(__file__).resolve().parents[1]
_AUDIT_SPEC = importlib.util.spec_from_file_location(
    "audit_ntsb_enrichment",
    _ROOT / "scripts" / "audit_ntsb_enrichment.py",
)
audit_ntsb_enrichment = importlib.util.module_from_spec(_AUDIT_SPEC)
assert _AUDIT_SPEC.loader is not None
_AUDIT_SPEC.loader.exec_module(audit_ntsb_enrichment)
run_audit = audit_ntsb_enrichment.run_audit


def test_export_row_includes_bucket():
    row = export_row("viable_with_working_link", {"source_record_id": "ABC123", "date": "2020-01-01"})
    assert row["bucket"] == "viable_with_working_link"
    assert row["source_record_id"] == "ABC123"


def test_write_export_row_jsonl(tmp_path):
    path = tmp_path / "rows.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        write_export_row(f, "skipped_deduped_asn_covered", {"source_record_id": "X1"})
        write_export_row(f, "viable_with_working_link", {"source_record_id": "X2"})
    counts = count_export_buckets(str(path))
    assert counts == {
        "skipped_deduped_asn_covered": 1,
        "viable_with_working_link": 1,
    }


def test_validate_export_against_report_matches():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        write_export_row(f, "skipped_deduped_asn_covered", {"source_record_id": "A"})
        write_export_row(f, "viable_with_working_link", {"source_record_id": "B"})
        write_export_row(f, "viable_with_broken_link", {"source_record_id": "C"})
        path = f.name

    report = {
        "skipped_deduped_asn_covered": 1,
        "viable_with_working_link": 1,
        "viable_with_broken_link": 1,
    }
    result = validate_export_against_report(path, report)
    assert result["matched"] is True
    assert result["total_lines"] == 3
    os.unlink(path)


def test_validate_export_against_report_mismatch_raises():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        write_export_row(f, "viable_with_working_link", {"source_record_id": "B"})
        path = f.name

    report = {"viable_with_working_link": 2}
    with pytest.raises(ValueError, match="do not match"):
        validate_export_against_report(path, report)
    os.unlink(path)


def test_run_audit_writes_export_buckets(app):
    with app.app_context():
        aircraft = Aircraft(
            manufacturer="Boeing",
            model_name="Boeing 737-800",
            years_in_service=20,
            total_incidents=1,
            fatal_incidents=0,
            total_fatalities=0,
        )
        db.session.add(aircraft)
        db.session.flush()
        db.session.add(
            Incident(
                aircraft_id=aircraft.id,
                date=date(2020, 6, 15),
                operator="United Airlines",
                location="Denver, CO",
                fatalities=0,
                incident_type="Accident",
                asn_url="https://aviation-safety.net/wikibase/1",
            )
        )
        db.session.commit()

        records = [
            {
                "cm_ntsbNum": "DEDUP001",
                "cm_eventDate": "2020-06-15",
                "cm_city": "Denver",
                "cm_state": "CO",
                "cm_vehicles": [{"make": "Boeing", "model": "737-800", "operatorName": "United Airlines"}],
            },
            {
                "cm_ntsbNum": "UNIQUE001",
                "cm_eventDate": "2019-01-01",
                "cm_city": "Phoenix",
                "cm_state": "AZ",
                "cm_vehicles": [{"make": "Boeing", "model": "737-800"}],
            },
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            export_path = f.name

        with patch.object(audit_ntsb_enrichment, "validate_ntsb_url") as mock_validate:
            mock_validate.return_value = (True, 200, None)
            with open(export_path, "w", encoding="utf-8") as export_file:
                report = run_audit(
                    records,
                    include_unknown_aircraft=True,
                    check_links=True,
                    export_file=export_file,
                )

        counts = count_export_buckets(export_path)
        assert report["skipped_deduped_asn_covered"] == 1
        assert report["viable_with_working_link"] == 1
        assert counts["skipped_deduped_asn_covered"] == 1
        assert counts["viable_with_working_link"] == 1
        validate_export_against_report(export_path, report)

        with open(export_path, encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        working = [line for line in lines if line["bucket"] == "viable_with_working_link"][0]
        assert working["source_record_id"] == "UNIQUE001"
        assert working["link_viable"] is True
        assert "bucket" in working
        os.unlink(export_path)
