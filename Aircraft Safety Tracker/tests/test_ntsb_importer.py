"""Step 3: NTSB URL builder and importer contract."""

from datetime import date

from app import db
from app.ingestion.importers.ntsb_importer import NTSBImporter
from app.ingestion.url_builders.ntsb import resolve_ntsb_source_url
from app.models import Aircraft, Incident, IncidentSource


def test_other_agency_no_carol_url():
    url = resolve_ntsb_source_url(
        "DCA17RA058",
        {"cm_agency": "Other", "cm_mkey": "abc123", "cm_ntsbNum": "DCA17RA058"},
    )
    assert url is not None
    assert "carol.ntsb.gov" not in url.lower()
    assert "NTSBNumber=DCA17RA058" in url


def test_director_brief_uses_docket_not_carol():
    url = resolve_ntsb_source_url(
        "ENG16IA001",
        {
            "cm_reportType": "DirectorBrief",
            "cm_mkey": "should-not-use",
            "cm_ntsbNum": "ENG16IA001",
        },
    )
    assert url is not None
    assert "carol.ntsb.gov" not in url.lower()
    assert "ENG16IA001" in url


def test_public_carol_wins_over_docket():
    url = resolve_ntsb_source_url(
        "DCA17RA058",
        {
            "cm_agency": "NTSB",
            "cm_ntsbNum": "DCA17RA058",
            "cm_mkey": "abc123",
            # Make CAROL "public" per heuristic: narrative length > 40 chars
            "factualNarrative": "This is long enough to be considered public content for CAROL.",
        },
    )
    assert url == "https://carol.ntsb.gov/investigations/detail/abc123"


def test_importer_skips_non_boeing_airbus(app):
    with app.app_context():
        written = NTSBImporter(
            records=[
                {
                    "cm_ntsbNum": "CEN20FA001",
                    "cm_eventDate": "2020-01-01",
                    "cm_vehicles": [{"make": "Cessna", "model": "172"}],
                }
            ]
        ).run()
        assert written == 0
        assert IncidentSource.query.filter_by(source_name="NTSB").count() == 0


def test_importer_writes_incident_source(app):
    with app.app_context():
        written = NTSBImporter(
            records=[
                {
                    "cm_ntsbNum": "ENG20FA010",
                    "cm_eventDate": "2020-06-15",
                    "cm_agency": "NTSB",
                    "cm_vehicles": [{"make": "Boeing", "model": "737-800"}],
                }
            ]
        ).run()
        assert written == 1
        source = IncidentSource.query.filter_by(
            source_name="NTSB", source_record_id="ENG20FA010"
        ).one()
        assert source.source_url
        assert "ENG20FA010" in source.source_url
        assert "links" not in (source.source_data or {})


def test_incident_list_foreign_led_faq_copy(client, app):
    with app.app_context():
        aircraft = Aircraft(
            manufacturer="Boeing",
            model_name="Boeing 737",
            years_in_service=40,
            total_incidents=1,
            fatal_incidents=0,
            total_fatalities=0,
        )
        db.session.add(aircraft)
        db.session.commit()
        incident = Incident(
            aircraft_id=aircraft.id,
            date=date(2017, 1, 16),
            operator="Test",
            location="Bishkek",
            fatalities=0,
            incident_type="Accident",
        )
        db.session.add(incident)
        db.session.flush()
        db.session.add(
            IncidentSource(
                incident_id=incident.id,
                source_name="NTSB",
                source_record_id="DCA17RA058",
                source_url=None,
                source_data={"cm_agency": "Other", "cm_ntsbNum": "DCA17RA058"},
                is_active=True,
            )
        )
        db.session.commit()
        aircraft_id = aircraft.id

    response = client.get(f"/aircraft/{aircraft_id}/incidents")
    assert response.status_code == 200
    assert b"Foreign-led" in response.data
