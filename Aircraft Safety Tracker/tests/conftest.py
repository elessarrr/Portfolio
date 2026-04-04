import pytest
from app import create_app, db
from app.models import Aircraft, Incident
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

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def sample_data(app):
    # Create sample aircraft
    a1 = Aircraft(
        manufacturer='Boeing',
        model_name='Boeing 737',
        years_in_service=50,
        total_incidents=10,
        fatal_incidents=2,
        total_fatalities=100
    )
    db.session.add(a1)
    db.session.commit()
    
    # Create sample incidents
    i1 = Incident(
        aircraft_id=a1.id,
        date=date(2020, 1, 1),
        operator='Alpha Airlines',
        location='Test Location',
        fatalities=0,
        description='Test incident',
        incident_type='Accident'
    )
    i2 = Incident(
        aircraft_id=a1.id,
        date=date(2021, 1, 1),
        operator='Beta Airlines',
        location='Test Location 2',
        fatalities=50,
        description='Fatal incident',
        incident_type='Accident'
    )
    db.session.add_all([i1, i2])
    db.session.commit()
    
    return a1
