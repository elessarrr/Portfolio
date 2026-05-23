from datetime import date

from app import db
from app.ingestion.linking.incident_linker import link_incidents_batch
from app.models import Aircraft, Incident, IncidentSource


def test_link_incidents_merges_faa_into_ntsb(app):
    with app.app_context():
        aircraft = Aircraft(manufacturer="Boeing", model_name="Boeing 737")
        db.session.add(aircraft)
        db.session.commit()

        ntsb_incident = Incident(
            aircraft_id=aircraft.id,
            date=date(2020, 5, 1),
            registration="N12345",
            location="Seattle, WA",
            operator="Test Air",
            fatalities=0,
            incident_type="Accident",
        )
        db.session.add(ntsb_incident)
        db.session.commit()

        db.session.add(
            IncidentSource(
                incident_id=ntsb_incident.id,
                source_name="NTSB",
                source_record_id="SEA20LA001",
                source_url="https://carol.ntsb.gov/investigations/detail/12345",
                is_active=True,
            )
        )

        faa_incident = Incident(
            aircraft_id=aircraft.id,
            date=date(2020, 5, 1),
            registration="N12345",
            location="Seattle, WA",
            operator="Test Air",
            fatalities=0,
            incident_type="Incident",
        )
        db.session.add(faa_incident)
        db.session.commit()

        db.session.add(
            IncidentSource(
                incident_id=faa_incident.id,
                source_name="FAA_AIDS",
                source_record_id="AIDS-LINK-1",
                is_active=True,
            )
        )
        db.session.commit()

        summary = link_incidents_batch(dry_run=False, limit=100)
        assert summary.linked >= 1

        faa_source = IncidentSource.query.filter_by(source_record_id="AIDS-LINK-1").first()
        assert faa_source.incident_id == ntsb_incident.id
