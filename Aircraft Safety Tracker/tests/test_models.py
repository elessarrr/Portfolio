import pytest
from app import create_app, db
from app.models import Aircraft, Incident, Request
from datetime import date

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_aircraft_creation(app):
    """Test that an aircraft can be created and retrieved."""
    a = Aircraft(manufacturer='Boeing', model_name='737-800', icao_code='B738', years_in_service=25)
    db.session.add(a)
    db.session.commit()

    retrieved = Aircraft.query.filter_by(model_name='737-800').first()
    assert retrieved is not None
    assert retrieved.manufacturer == 'Boeing'
    assert retrieved.icao_code == 'B738'

def test_incident_creation(app):
    """Test that an incident can be created and linked to an aircraft."""
    a = Aircraft(manufacturer='Airbus', model_name='A320', icao_code='A320', years_in_service=30)
    db.session.add(a)
    db.session.commit()

    i = Incident(aircraft_id=a.id, date=date(2023, 1, 15), operator='Test Air', 
                 location='New York', fatalities=0, description='Minor tail strike', incident_type='Accident')
    db.session.add(i)
    db.session.commit()

    retrieved_incident = Incident.query.first()
    assert retrieved_incident is not None
    assert retrieved_incident.operator == 'Test Air'
    assert retrieved_incident.aircraft.model_name == 'A320'

def test_request_creation(app):
    """Test that a user request can be logged."""
    r = Request(aircraft_model='Cessna 172', user_email='test@example.com')
    db.session.add(r)
    db.session.commit()

    retrieved_request = Request.query.first()
    assert retrieved_request is not None
    assert retrieved_request.aircraft_model == 'Cessna 172'
    assert retrieved_request.user_email == 'test@example.com'
