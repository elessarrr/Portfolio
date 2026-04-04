import pytest
from app import create_app, db
from app.models import Incident, IncidentSource, Aircraft
from bs4 import BeautifulSoup
import datetime

@pytest.fixture
def app():
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_incident_card_with_source_url(client, app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='737')
        db.session.add(aircraft)
        db.session.commit()

        inc = Incident(date=datetime.date(2023, 1, 1), operator='Test Air', aircraft_id=aircraft.id)
        db.session.add(inc)
        db.session.commit()

        src = IncidentSource(incident_id=inc.id, source_name='Aviation Safety Network', source_url='https://aviation-safety.net/test')
        db.session.add(src)
        db.session.commit()

    resp = client.get('/incidents')
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.data, 'html.parser')
    
    link = next((a for a in soup.find_all('a') if 'Aviation Safety Network' in a.get_text()), None)
    assert link is not None
    assert link['href'] == 'https://aviation-safety.net/test'
    assert link['target'] == '_blank'
    assert 'noopener' in link['rel']
    assert 'noreferrer' in link['rel']
    assert 'aria-label' in link.attrs

def test_incident_card_without_source_url(client, app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='737')
        db.session.add(aircraft)
        db.session.commit()

        inc = Incident(date=datetime.date(2023, 1, 1), operator='Test Air', aircraft_id=aircraft.id)
        db.session.add(inc)
        db.session.commit()

        src = IncidentSource(incident_id=inc.id, source_name='Secret DB', source_url=None, report_url=None)
        db.session.add(src)
        db.session.commit()

    resp = client.get('/incidents')
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.data, 'html.parser')
    
    span = next((s for s in soup.find_all('span') if 'Secret DB' in s.get_text()), None)
    assert span is not None
    assert '(Unavailable)' in span.text
    assert 'Source URL unavailable' in span.get('aria-label', '')

def test_incident_card_with_asn_fallback(client, app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='737')
        db.session.add(aircraft)
        db.session.commit()

        inc = Incident(date=datetime.date(2023, 1, 1), operator='Test Air', aircraft_id=aircraft.id, asn_url='https://asn.fallback')
        db.session.add(inc)
        db.session.commit()

    resp = client.get('/incidents')
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.data, 'html.parser')
    
    link = next((a for a in soup.find_all('a') if 'Aviation Safety Network' in a.get_text()), None)
    assert link is not None
    assert link['href'] == 'https://asn.fallback'