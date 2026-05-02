import importlib.util
from datetime import date
from pathlib import Path
from unittest.mock import patch

from app import db
from app.models import Aircraft, Incident, IncidentSource


def _load_validate_incident_links_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "validate_incident_links.py"
    )
    spec = importlib.util.spec_from_file_location("validate_incident_links_script", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _make_source(*, source_name: str, source_url: str, report_url: str = None) -> IncidentSource:
    aircraft = Aircraft(
        manufacturer="Boeing",
        model_name=f"Validator-{source_name}",
        total_incidents=0,
        fatal_incidents=0,
        total_fatalities=0,
    )
    db.session.add(aircraft)
    db.session.flush()

    incident = Incident(
        aircraft_id=aircraft.id,
        date=date(2024, 1, 1),
        operator="Validator Test",
        location="Test City",
        fatalities=0,
        description="Test incident",
        incident_type="Incident",
    )
    db.session.add(incident)
    db.session.flush()

    source = IncidentSource(
        incident_id=incident.id,
        source_name=source_name,
        source_record_id=f"RID-{source_name}-{incident.id}",
        source_url=source_url,
        report_url=report_url,
    )
    db.session.add(source)
    db.session.commit()
    return source


def test_validate_and_update_skips_ntsb_source_url_signal(app):
    module = _load_validate_incident_links_module()

    with app.app_context():
        source = _make_source(
            source_name="NTSB",
            source_url="https://carol.ntsb.gov/ReportMain/GenerateNewestReport/XYZ/pdf",
            report_url=None,
        )

        with patch.object(module, "validate_source_url", return_value=(True, 200, None)) as source_validate_mock, patch.object(
            module, "validate_pdf_url", return_value=(False, None, "url_is_none")
        ):
            log_entry = module.validate_and_update(source, dry_run=True)

        assert source_validate_mock.call_count == 0
        assert log_entry.result == "unchanged"
        assert log_entry.error_detail == "ntsb_report_url_missing_skip"


def test_validate_and_update_keeps_source_url_signal_for_non_ntsb(app):
    module = _load_validate_incident_links_module()

    with app.app_context():
        source = _make_source(
            source_name="ASN",
            source_url="https://aviation-safety.net/wikibase/12345",
            report_url=None,
        )

        with patch.object(module, "validate_source_url", return_value=(True, 200, None)) as source_validate_mock, patch.object(
            module, "validate_pdf_url", return_value=(False, None, "url_is_none")
        ):
            log_entry = module.validate_and_update(source, dry_run=True)

        assert source_validate_mock.call_count == 1
        assert log_entry.result == "valid"
        assert log_entry.http_status == 200


def test_validate_and_update_ntsb_uses_report_url_as_primary_signal(app):
    module = _load_validate_incident_links_module()

    with app.app_context():
        source = _make_source(
            source_name="NTSB",
            source_url="https://carol.ntsb.gov/ReportMain/GenerateNewestReport/XYZ/pdf",
            report_url="https://data.ntsb.gov/carol-repgen/api/Aviation/ReportMain/GenerateNewestReport/ABC/pdf",
        )

        with patch.object(module, "validate_source_url", return_value=(True, 200, None)) as source_validate_mock, patch.object(
            module, "validate_pdf_url", return_value=(True, 200, None)
        ):
            log_entry = module.validate_and_update(source, dry_run=True)

        assert source_validate_mock.call_count == 0
        assert log_entry.result == "valid"
        assert log_entry.http_status == 200


def test_validate_and_update_ntsb_missing_report_url_stamps_without_mutating_urls(app):
    module = _load_validate_incident_links_module()

    with app.app_context():
        source = _make_source(
            source_name="NTSB",
            source_url="https://carol.ntsb.gov/ReportMain/GenerateNewestReport/XYZ/pdf",
            report_url=None,
        )
        source_id = source.id
        original_source_url = source.source_url
        original_report_url = source.report_url

        with patch.object(module, "validate_source_url", return_value=(False, 404, "http_404")) as source_validate_mock, patch.object(
            module, "validate_pdf_url", return_value=(False, None, "url_is_none")
        ):
            log_entry = module.validate_and_update(source, dry_run=False)
            db.session.commit()

        persisted = db.session.get(IncidentSource, source_id)
        assert persisted is not None
        assert source_validate_mock.call_count == 0
        assert log_entry.result == "unchanged"
        assert persisted.source_url == original_source_url
        assert persisted.report_url == original_report_url
        assert persisted.last_validated_at is not None
