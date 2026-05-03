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
    
    link = next((a for a in soup.find_all('a') if a.get('href') == 'https://aviation-safety.net/test'), None)
    assert link is not None
    assert link['href'] == 'https://aviation-safety.net/test'
    assert link['target'] == '_blank'
    assert 'noopener' in link['rel']
    assert 'noreferrer' in link['rel']
    assert 'aria-label' in link.attrs

def test_incident_card_without_source_url(client, app):
    """
    Per PRD-0016 FR-28: Sources with null source_url AND null report_url
    are suppressed — no link element or span is rendered for them.
    """
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

    link = next((a for a in soup.find_all('a') if 'Secret DB' in a.get_text()), None)
    assert link is None
    span = next((s for s in soup.find_all('span') if 'Secret DB' in s.get_text()), None)
    assert span is None

def test_incident_card_with_asn_incident_source_link(client, app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='737')
        db.session.add(aircraft)
        db.session.commit()

        inc = Incident(date=datetime.date(2023, 1, 1), operator='Test Air', aircraft_id=aircraft.id)
        db.session.add(inc)
        db.session.flush()

        src = IncidentSource(
            incident_id=inc.id,
            source_name='ASN',
            source_url='https://asn.fallback',
            source_record_id='https://asn.fallback',
        )
        db.session.add(src)
        db.session.commit()

    resp = client.get('/incidents')
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.data, 'html.parser')
    
    link = next((a for a in soup.find_all('a') if a.get('href') == 'https://asn.fallback'), None)
    assert link is not None
    assert link['href'] == 'https://asn.fallback'


def test_global_incident_list_renders_media_source_with_generic_link_style(client, app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='737')
        db.session.add(aircraft)
        db.session.commit()

        inc = Incident(date=datetime.date(2024, 1, 1), operator='Media Air', aircraft_id=aircraft.id)
        db.session.add(inc)
        db.session.commit()

        src = IncidentSource(
            incident_id=inc.id,
            source_name='MEDIA',
            source_url='https://news.example.com/article-1',
            is_active=True,
        )
        db.session.add(src)
        db.session.commit()

    resp = client.get('/incidents')
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.data, 'html.parser')

    link = next((a for a in soup.find_all('a') if a.get('href') == 'https://news.example.com/article-1'), None)
    assert link is not None
    assert 'MEDIA' in link.get_text()
    assert 'border-gray-300' in link.get('class', [])
    assert 'bg-white' in link.get('class', [])
    assert link.get('target') is None


def test_aircraft_incident_list_renders_media_source_with_generic_link_style(client, app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Airbus', model_name='A320')
        db.session.add(aircraft)
        db.session.commit()
        aircraft_id = aircraft.id

        inc = Incident(date=datetime.date(2024, 2, 1), operator='Media Jet', aircraft_id=aircraft.id)
        db.session.add(inc)
        db.session.commit()

        src = IncidentSource(
            incident_id=inc.id,
            source_name='MEDIA',
            source_url='https://wire.example.com/article-2',
            is_active=True,
        )
        db.session.add(src)
        db.session.commit()

    resp = client.get(f'/aircraft/{aircraft_id}')
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.data, 'html.parser')

    link = next((a for a in soup.find_all('a') if a.get('href') == 'https://wire.example.com/article-2'), None)
    assert link is not None
    assert 'MEDIA' in link.get_text()
    assert 'bg-blue-100' in link.get('class', [])
    assert 'text-blue-800' in link.get('class', [])
    assert link.get('target') is None


def test_aircraft_incident_list_shows_wa_faq_note_for_inactive_ntsb_only(client, app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='777')
        db.session.add(aircraft)
        db.session.commit()
        aircraft_id = aircraft.id

        inc = Incident(date=datetime.date(2024, 3, 1), operator='WA Air', aircraft_id=aircraft_id)
        db.session.add(inc)
        db.session.commit()

        ntsb_inactive = IncidentSource(
            incident_id=inc.id,
            source_name='NTSB',
            source_record_id='WPR24LA123',
            source_url='https://data.ntsb.gov/Docket/?NTSBNumber=WPR24LA123',
            is_active=False,
        )
        db.session.add(ntsb_inactive)
        db.session.commit()

    resp = client.get(f'/aircraft/{aircraft_id}')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'No official NTSB docket -' in html
    assert '/faq#international-investigations' in html


def test_aircraft_incident_list_hides_wa_faq_note_when_active_ntsb_exists(client, app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='787')
        db.session.add(aircraft)
        db.session.commit()
        aircraft_id = aircraft.id

        inc = Incident(date=datetime.date(2024, 4, 1), operator='Not WA-only Air', aircraft_id=aircraft_id)
        db.session.add(inc)
        db.session.commit()

        db.session.add(IncidentSource(
            incident_id=inc.id,
            source_name='NTSB',
            source_record_id='WPR24LA555',
            source_url='https://data.ntsb.gov/Docket/?NTSBNumber=WPR24LA555',
            is_active=False,
        ))
        db.session.add(IncidentSource(
            incident_id=inc.id,
            source_name='NTSB',
            source_record_id='WPR24LA556',
            source_url='https://data.ntsb.gov/Docket/?NTSBNumber=WPR24LA556',
            is_active=True,
        ))
        db.session.commit()

    resp = client.get(f'/aircraft/{aircraft_id}')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert '/faq#international-investigations' not in html


def test_global_incident_list_shows_wa_faq_note_for_inactive_ntsb_only(client, app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='767')
        db.session.add(aircraft)
        db.session.commit()

        inc = Incident(date=datetime.date(2024, 5, 1), operator='Global WA Air', aircraft_id=aircraft.id)
        db.session.add(inc)
        db.session.commit()

        db.session.add(IncidentSource(
            incident_id=inc.id,
            source_name='NTSB',
            source_record_id='WPR24LA777',
            source_url='https://data.ntsb.gov/Docket/?NTSBNumber=WPR24LA777',
            is_active=False,
        ))
        db.session.commit()

    resp = client.get('/incidents')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert '/faq#international-investigations' in html
