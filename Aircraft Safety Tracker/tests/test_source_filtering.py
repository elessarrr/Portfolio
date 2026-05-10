from datetime import date

from app import db
from app.models import Aircraft, Incident, IncidentSource


def test_aircraft_details_source_options_and_filtering(client, app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='FILTER-1')
        db.session.add(aircraft)
        db.session.commit()

        aircraft_id = aircraft.id

        i1 = Incident(aircraft_id=aircraft.id, date=date(2024, 1, 1), operator='Op1', location='Loc', fatalities=0, incident_type='Accident')
        i2 = Incident(aircraft_id=aircraft.id, date=date(2024, 1, 2), operator='Op2', location='Loc', fatalities=0, incident_type='Accident')
        db.session.add_all([i1, i2])
        db.session.commit()

        db.session.add(IncidentSource(incident_id=i1.id, source_name='NTSB', source_record_id='X1', source_url='https://example.com/ntsb'))
        db.session.add(IncidentSource(incident_id=i2.id, source_name='FAA_AIDS', source_record_id='Y1', source_url='https://example.com/faa'))
        db.session.commit()

    response = client.get(f'/aircraft/{aircraft_id}')
    assert response.status_code == 200
    assert b'NTSB' in response.data
    assert b'FAA_AIDS' in response.data

    response = client.get(f'/aircraft/{aircraft_id}/incidents?source=NTSB')
    assert response.status_code == 200
    assert b'Op1' in response.data
    assert b'Op2' not in response.data
