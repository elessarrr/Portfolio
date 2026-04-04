from datetime import date

from app import db
from app.ingestion.canonical import attach_source_to_incident
from app.models import Aircraft, Incident, IncidentSource


def test_attach_source_to_incident_relinks_existing_source(app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='LINK-1')
        db.session.add(aircraft)
        db.session.commit()

        i1 = Incident(aircraft_id=aircraft.id, date=date(2024, 1, 1), incident_type='Accident')
        i2 = Incident(aircraft_id=aircraft.id, date=date(2024, 1, 2), incident_type='Accident')
        db.session.add_all([i1, i2])
        db.session.commit()

        src = IncidentSource(incident_id=i1.id, source_name='NTSB', source_record_id='R1', source_url='https://example.com')
        db.session.add(src)
        db.session.commit()

        attach_source_to_incident(
            incident_id=i2.id,
            source_name='NTSB',
            source_record_id='R1',
            source_url='https://example.com/new',
            report_url=None,
            source_data={'a': 1},
            confidence_level='High',
        )

        updated = IncidentSource.query.filter_by(source_name='NTSB', source_record_id='R1').first()
        assert updated is not None
        assert updated.incident_id == i2.id
        assert updated.source_url == 'https://example.com/new'

