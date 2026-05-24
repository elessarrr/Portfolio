"""Step 1: pick_primary_href, link_schema contract, template safety."""

from datetime import date

import pytest

from app import db
from app.ingestion.link_schema import (
    assert_source_data_metadata_only,
    assert_valid_source_url,
    is_catalog_url,
    is_placeholder_url,
)
from app.link_picker import pick_primary_href
from app.models import Aircraft, Incident, IncidentSource


@pytest.fixture
def boeing_incident(app):
    with app.app_context():
        aircraft = Aircraft(
            manufacturer="Boeing",
            model_name="Boeing 737",
            years_in_service=50,
            total_incidents=1,
            fatal_incidents=0,
            total_fatalities=0,
        )
        db.session.add(aircraft)
        db.session.commit()

        incident = Incident(
            aircraft_id=aircraft.id,
            date=date(2020, 1, 1),
            operator="Test Air",
            location="Test",
            fatalities=0,
            incident_type="Accident",
        )
        db.session.add(incident)
        db.session.commit()
        incident_id = incident.id
        aircraft_id = aircraft.id

    return {"incident_id": incident_id, "aircraft_id": aircraft_id}


def test_pick_primary_asn_wins(app, boeing_incident):
    with app.app_context():
        incident = db.session.get(Incident, boeing_incident["incident_id"])
        incident.asn_url = "https://aviation-safety.net/wikibase/123"
        ntsb = IncidentSource(
            incident_id=incident.id,
            source_name="NTSB",
            source_record_id="ENG20FA001",
            source_url="https://data.ntsb.gov/Docket/ENG20FA001",
            is_active=True,
        )
        db.session.add(ntsb)
        db.session.commit()

        href = pick_primary_href(incident, [ntsb])
        assert href == incident.asn_url


def test_pick_primary_ntsb_fallback(app, boeing_incident):
    with app.app_context():
        incident = db.session.get(Incident, boeing_incident["incident_id"])
        incident.asn_url = None
        ntsb = IncidentSource(
            incident_id=incident.id,
            source_name="NTSB",
            source_record_id="ENG20FA002",
            source_url="https://data.ntsb.gov/Docket/ENG20FA002",
            is_active=True,
        )
        db.session.add(ntsb)
        db.session.commit()

        assert pick_primary_href(incident, [ntsb]) == ntsb.source_url


def test_pick_ignores_source_data_links_blob(app, boeing_incident):
    with app.app_context():
        incident = db.session.get(Incident, boeing_incident["incident_id"])
        source = IncidentSource(
            incident_id=incident.id,
            source_name="NTSB",
            source_record_id="ENG20FA003",
            source_url=None,
            source_data={
                "links": [{"url": "https://carol.ntsb.gov/investigations/detail/ENG20FA003"}]
            },
            is_active=True,
        )
        db.session.add(source)
        db.session.commit()

        assert pick_primary_href(incident, [source]) is None


def test_link_schema_rejects_placeholder():
    assert is_placeholder_url("https://example.com/foo")
    with pytest.raises(ValueError, match="placeholder"):
        assert_valid_source_url("https://example.com/foo")


def test_link_schema_rejects_catalog():
    catalog = "https://www.asias.faa.gov/pls/apex/f?p=100:11"
    assert is_catalog_url(catalog)
    with pytest.raises(ValueError, match="catalog"):
        assert_valid_source_url(catalog)


def test_no_links_in_source_data():
    with pytest.raises(ValueError, match="links"):
        assert_source_data_metadata_only({"links": [{"url": "https://example.com"}]})


def test_incident_list_renders_asn_details_href(client, app, boeing_incident):
    asn_url = "https://aviation-safety.net/wikibase/321654"
    with app.app_context():
        incident = db.session.get(Incident, boeing_incident["incident_id"])
        incident.asn_url = asn_url
        db.session.commit()

    response = client.get(f"/aircraft/{boeing_incident['aircraft_id']}/incidents")
    assert response.status_code == 200
    assert asn_url.encode() in response.data
    assert b"Details" in response.data


def test_incident_list_no_empty_href(client, boeing_incident):
    response = client.get(f"/aircraft/{boeing_incident['aircraft_id']}/incidents")
    assert response.status_code == 200
    assert b'href=""' not in response.data
    assert b"href=''" not in response.data
