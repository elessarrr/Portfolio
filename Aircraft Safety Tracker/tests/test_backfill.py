from datetime import date
import importlib.util
from pathlib import Path

from app import db
from app.models import Aircraft, Incident, IncidentSource

_BACKFILL_PATH = Path(__file__).resolve().parents[1] / "scripts" / "backfill_aircraft_ids.py"
_SPEC = importlib.util.spec_from_file_location("backfill_aircraft_ids", _BACKFILL_PATH)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(_MODULE)

extract_make_model_from_source = _MODULE.extract_make_model_from_source
link_orphan_incidents = _MODULE.link_orphan_incidents


def test_extract_make_model_field_priority():
    payload = {
        "make_model": "Boeing 737-800",
        "make": "Boeing",
        "model": "737-700",
        "acft_make": "Boeing",
        "acft_model": "737",
    }
    assert extract_make_model_from_source(payload) == "Boeing 737-800"


def test_backfill_links_unlinked_incident_and_is_idempotent(app):
    with app.app_context():
        incident = Incident(
            aircraft_id=None,
            date=date(2020, 1, 1),
            operator="Backfill Test Airline",
            location="Test City",
            fatalities=0,
            description="Backfill test incident",
            incident_type="Incident",
        )
        db.session.add(incident)
        db.session.flush()
        db.session.add(
            IncidentSource(
                incident_id=incident.id,
                source_name="NTSB",
                source_record_id="NTSB-BACKFILL-1",
                source_data={"make_model": "Boeing 737-800"},
            )
        )
        db.session.commit()

        aircraft_count_before = Aircraft.query.count()

        first_run = link_orphan_incidents(batch_size=10, dry_run=False)
        db.session.refresh(incident)
        assert incident.aircraft_id is not None
        assert first_run["total_newly_linked"] == 1

        aircraft_count_after_first = Aircraft.query.count()
        assert aircraft_count_after_first >= aircraft_count_before

        second_run = link_orphan_incidents(batch_size=10, dry_run=False)
        assert second_run["total_newly_linked"] == 0
        assert Aircraft.query.count() == aircraft_count_after_first


def test_backfill_ignores_non_boeing_airbus_records(app):
    with app.app_context():
        incident = Incident(
            aircraft_id=None,
            date=date(2020, 2, 1),
            operator="Ignored Scope Airline",
            location="Ignored Scope City",
            fatalities=0,
            description="Non-commercial aviation incident",
            incident_type="Incident",
        )
        db.session.add(incident)
        db.session.flush()
        db.session.add(
            IncidentSource(
                incident_id=incident.id,
                source_name="FAA_AIDS",
                source_record_id="FAA-AIDS-BACKFILL-1",
                source_data={"make": "Cessna", "model": "172"},
            )
        )
        db.session.commit()

        summary = link_orphan_incidents(batch_size=10, dry_run=False)
        db.session.refresh(incident)

        assert incident.aircraft_id is None
        assert summary["total_ignored"] >= 1
