import importlib.util
from datetime import date
from pathlib import Path
from unittest.mock import patch

from app import db
from app.models import Aircraft, Incident, IncidentSource


def _load_link_validator_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / "Planning"
        / "scripts"
        / "link_validator.py"
    )
    spec = importlib.util.spec_from_file_location("link_validator_script", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _make_incident_source(*, source_url: str, report_url: str = None, is_active: bool = True) -> int:
    aircraft = Aircraft(
        manufacturer="Boeing",
        model_name=f"Boeing 737-{source_url.split('/')[-1]}",
        total_incidents=0,
        fatal_incidents=0,
        total_fatalities=0,
    )
    db.session.add(aircraft)
    db.session.flush()
    incident = Incident(
        aircraft_id=aircraft.id,
        date=date(2023, 1, 1),
        operator="Validator Test",
        location="Test",
        fatalities=0,
        description="Validator test incident",
        incident_type="Accident",
    )
    db.session.add(incident)
    db.session.flush()
    source = IncidentSource(
        incident_id=incident.id,
        source_name="NTSB",
        source_record_id=f"RID-{aircraft.id}",
        source_url=source_url,
        report_url=report_url,
        is_active=is_active,
    )
    db.session.add(source)
    db.session.commit()
    return source.id


def test_link_validator_sets_inactive_on_broken_links(app):
    module = _load_link_validator_module()

    with app.app_context():
        source_id = _make_incident_source(source_url="https://broken.example/404", is_active=True)

        with patch.object(module, "validate_source_url", return_value=(False, 404, "http_404")), patch.object(
            module, "validate_pdf_url", return_value=(False, 404, "http_404")
        ):
            summary = module.run_link_validator(
                dry_run=False,
                batch_size=10,
                per_domain_delay_seconds=0.0,
            )

        updated = db.session.get(IncidentSource, source_id)
        assert summary["processed"] == 1
        assert summary["active_set_false"] == 1
        assert updated is not None and updated.is_active is False


def test_link_validator_keeps_active_when_report_url_is_valid(app):
    module = _load_link_validator_module()

    with app.app_context():
        source_id = _make_incident_source(
            source_url="https://broken.example/ntsb",
            report_url="https://docs.example/report.pdf",
            is_active=True,
        )

        with patch.object(module, "validate_source_url", return_value=(False, 404, "http_404")), patch.object(
            module, "validate_pdf_url", return_value=(True, 200, None)
        ):
            summary = module.run_link_validator(
                dry_run=False,
                batch_size=10,
                per_domain_delay_seconds=0.0,
            )

        updated = db.session.get(IncidentSource, source_id)
        assert summary["processed"] == 1
        assert summary["unchanged"] == 1
        assert updated is not None and updated.is_active is True


def test_link_validator_dry_run_does_not_persist_changes(app):
    module = _load_link_validator_module()

    with app.app_context():
        source_id = _make_incident_source(source_url="https://broken.example/dry-run", is_active=True)

        with patch.object(module, "validate_source_url", return_value=(False, 404, "http_404")), patch.object(
            module, "validate_pdf_url", return_value=(False, 404, "http_404")
        ):
            summary = module.run_link_validator(
                dry_run=True,
                batch_size=10,
                per_domain_delay_seconds=0.0,
            )

        db.session.expire_all()
        updated = db.session.get(IncidentSource, source_id)
        assert summary["active_set_false"] == 1
        assert updated is not None and updated.is_active is True
