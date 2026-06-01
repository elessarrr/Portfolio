"""Tests for post-import NTSB audit (FR-22)."""

from __future__ import annotations

from datetime import date

from app import db
from app.ingestion.ntsb_post_import_audit import run_post_import_audit
from app.models import Aircraft, Incident, IncidentSource


def test_post_import_audit_passes_clean_db(app):
    with app.app_context():
        aircraft = Aircraft(
            manufacturer="Boeing",
            model_name="Boeing 737-800",
            total_incidents=0,
            fatal_incidents=0,
            total_fatalities=0,
        )
        db.session.add(aircraft)
        db.session.flush()

        ntsb_inc = Incident(
            aircraft_id=aircraft.id,
            date=date(2021, 1, 1),
            operator="Delta",
            location="Atlanta, GA",
            fatalities=0,
            incident_type="Accident",
        )
        db.session.add(ntsb_inc)
        db.session.flush()
        db.session.add(
            IncidentSource(
                incident_id=ntsb_inc.id,
                source_name="NTSB",
                source_record_id="NTSB001",
                source_url="https://data.ntsb.gov/Docket/?NTSBNumber=NTSB001",
                source_data={"ntsb_make_model": "Boeing 737-800"},
                is_active=True,
            )
        )
        db.session.commit()

        report = run_post_import_audit()
        assert report["passed"] is True
        assert report["critical_duplicate_count"] == 0


def test_post_import_audit_flags_ntsb_asn_duplicate(app):
    with app.app_context():
        aircraft = Aircraft(
            manufacturer="Boeing",
            model_name="Boeing 737-800",
            total_incidents=0,
            fatal_incidents=0,
            total_fatalities=0,
        )
        db.session.add(aircraft)
        db.session.flush()

        asn_inc = Incident(
            aircraft_id=aircraft.id,
            date=date(2020, 6, 15),
            operator="United Airlines",
            location="Denver, CO",
            fatalities=0,
            incident_type="Accident",
            asn_url="https://aviation-safety.net/wikibase/1",
        )
        ntsb_inc = Incident(
            aircraft_id=aircraft.id,
            date=date(2020, 6, 15),
            operator="United Airlines",
            location="Denver, CO",
            fatalities=0,
            incident_type="Accident",
        )
        db.session.add_all([asn_inc, ntsb_inc])
        db.session.flush()
        db.session.add(
            IncidentSource(
                incident_id=ntsb_inc.id,
                source_name="NTSB",
                source_record_id="ENG20FA010",
                source_url="https://data.ntsb.gov/Docket/?NTSBNumber=ENG20FA010",
                source_data={},
                is_active=True,
            )
        )
        db.session.commit()

        report = run_post_import_audit()
        assert report["passed"] is False
        assert report["counts"]["incident_duplicate_critical"] >= 1


def test_post_import_audit_flags_orphan_url(app):
    with app.app_context():
        aircraft = Aircraft(
            manufacturer="Boeing",
            model_name="Boeing 737",
            total_incidents=0,
            fatal_incidents=0,
            total_fatalities=0,
        )
        db.session.add(aircraft)
        db.session.flush()
        ntsb_inc = Incident(
            aircraft_id=aircraft.id,
            date=date(2020, 1, 1),
            operator="Test",
            location="Test",
            fatalities=0,
            incident_type="Accident",
        )
        db.session.add(ntsb_inc)
        db.session.flush()
        db.session.add(
            IncidentSource(
                incident_id=ntsb_inc.id,
                source_name="NTSB",
                source_record_id="NOURL001",
                source_url=None,
                source_data={},
                is_active=True,
            )
        )
        db.session.commit()

        report = run_post_import_audit()
        assert report["passed"] is False
        assert report["counts"]["orphan_source_critical"] >= 1
