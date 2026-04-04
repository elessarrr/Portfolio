import pytest
from app.models import Request, Incident, SystemTag, IncidentSource, AircraftVariant, Aircraft
from app import db
from unittest.mock import patch

def test_home_page(client):
    """Test that the home page loads correctly."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Aircraft Safety Tracker' in response.data
    assert b'Search for an aircraft' in response.data


def test_footer_renders_data_freshness(client, app):
    from app.models import ImportState
    from datetime import datetime
    from app import db

    with app.app_context():
        db.session.add(ImportState(source_name='NTSB', last_status='completed', last_successful_at=datetime.utcnow(), updated_at=datetime.utcnow()))
        db.session.commit()

    response = client.get('/')
    assert response.status_code == 200
    assert b'Data freshness' in response.data
    assert b'NTSB' in response.data

def test_search_endpoint_empty_db(client, app):
    """Test search endpoint behavior when the database is empty."""
    with app.app_context():
        # Ensure database is empty for this specific test
        db.session.query(Aircraft).delete()
        db.session.commit()
        
    response = client.get('/search?q=Boeing')
    assert response.status_code == 200
    assert b'No data loaded yet' in response.data
    assert b'No aircraft found matching' not in response.data

def test_search_endpoint(client, sample_data):
    """Test the search autocomplete endpoint."""
    # Test valid search
    response = client.get('/search?q=Boeing')
    assert response.status_code == 200
    assert b'Boeing 737' in response.data
    
    # Test empty search
    response = client.get('/search?q=')
    assert response.status_code == 200
    assert response.data == b''
    
    # Test short search
    response = client.get('/search?q=B')
    assert response.status_code == 200
    # A single character query like "B" should still match models starting with "B" (e.g. Boeing)
    # The current routes.py implementation only returns empty string for len < 1
    assert b'Boeing 737' in response.data
    
    # Test no results
    response = client.get('/search?q=Airbus')
    assert response.status_code == 200
    assert b'No aircraft found matching' in response.data


def test_search_includes_variants(client, app, sample_data):
    with app.app_context():
        db.session.add(AircraftVariant(aircraft_id=sample_data.id, variant_name='737-800', total_incidents=3, fatal_incidents=1))
        db.session.commit()

    response = client.get('/search?q=737-800')
    assert response.status_code == 200
    assert b'Boeing 737' in response.data
    assert b'737-800' in response.data
    assert b'variant=737-800' in response.data


def test_search_single_series_shows_models_empty_state(client, sample_data):
    response = client.get('/search?q=Boeing')
    assert response.status_code == 200
    assert b'Boeing 737' in response.data
    assert b'(All variants)' in response.data

def test_aircraft_details(client, sample_data):
    """Test the aircraft details page."""
    response = client.get(f'/aircraft/{sample_data.id}')
    assert response.status_code == 200
    assert b'Boeing 737' in response.data
    assert b'Total Incidents' in response.data
    assert b'50' in response.data  # Years in service
    
    # Test non-existent aircraft
    response = client.get('/aircraft/999')
    assert response.status_code == 404
    assert b'Page Not Found' in response.data

def test_incident_filtering(client, sample_data):
    """Test the incident filtering endpoint."""
    # Test all incidents
    response = client.get(f'/aircraft/{sample_data.id}/incidents')
    assert response.status_code == 200
    assert b'Alpha Airlines' in response.data
    assert b'Beta Airlines' in response.data
    
    # Test fatal incidents
    response = client.get(f'/aircraft/{sample_data.id}/incidents?type=fatal')
    assert response.status_code == 200
    assert b'Beta Airlines' in response.data
    assert b'Alpha Airlines' not in response.data
    
    # Test non-fatal incidents
    response = client.get(f'/aircraft/{sample_data.id}/incidents?type=nonfatal')
    assert response.status_code == 200
    assert b'Alpha Airlines' in response.data
    assert b'Beta Airlines' not in response.data


def test_incident_filtering_by_variant_name(client, app, sample_data):
    with app.app_context():
        incidents = Incident.query.filter_by(aircraft_id=sample_data.id).order_by(Incident.date.asc()).all()
        incidents[0].variant_name = '737-700'
        incidents[1].variant_name = '737-800'
        db.session.commit()

    response = client.get(f'/aircraft/{sample_data.id}/incidents?variant=737-800')
    assert response.status_code == 200
    assert b'Beta Airlines' in response.data
    assert b'Alpha Airlines' not in response.data


def test_incident_filtering_by_system_and_source(client, app, sample_data):
    with app.app_context():
        fatal_incident = Incident.query.filter_by(operator='Beta Airlines').first()
        nonfatal_incident = Incident.query.filter_by(operator='Alpha Airlines').first()
        db.session.add(SystemTag(incident_id=fatal_incident.id, system_name='Hydraulics', confidence='High', tagged_by='AI'))
        db.session.add(SystemTag(incident_id=nonfatal_incident.id, system_name='Electrical', confidence='Medium', tagged_by='AI'))
        db.session.add(IncidentSource(incident_id=fatal_incident.id, source_name='NTSB', source_url='https://example.com/ntsb'))
        db.session.add(IncidentSource(incident_id=nonfatal_incident.id, source_name='FAA', source_url='https://example.com/faa'))
        db.session.commit()

    response = client.get(f'/aircraft/{sample_data.id}/incidents?system=Hydraulics&source=NTSB')
    assert response.status_code == 200
    assert b'Beta Airlines' in response.data
    assert b'Alpha Airlines' not in response.data


def test_incident_export_csv(client, app, sample_data):
    with app.app_context():
        incident = Incident.query.filter_by(operator='Beta Airlines').first()
        db.session.add(SystemTag(incident_id=incident.id, system_name='Flight Controls', confidence='High', tagged_by='ASN'))
        db.session.add(IncidentSource(incident_id=incident.id, source_name='ASN', source_url='https://example.com/asn'))
        db.session.add(AircraftVariant(aircraft_id=sample_data.id, variant_name='737-800', years_in_service='20', total_incidents=3, fatal_incidents=1))
        db.session.commit()

    response = client.get(f'/aircraft/{sample_data.id}/incidents/export.csv?type=fatal')
    assert response.status_code == 200
    assert response.mimetype == 'text/csv'
    assert b'Date,Aircraft,Operator,System,Description,Source' in response.data
    assert b'Boeing 737' in response.data
    assert b'Flight Controls' in response.data


def test_incident_export_csv_respects_source_filter(client, app, sample_data):
    with app.app_context():
        incidents = Incident.query.filter_by(aircraft_id=sample_data.id).order_by(Incident.date.asc()).all()
        db.session.add(IncidentSource(incident_id=incidents[0].id, source_name='NTSB', source_url='https://example.com/ntsb'))
        db.session.add(IncidentSource(incident_id=incidents[1].id, source_name='FAA_AIDS', source_url='https://example.com/faa'))
        db.session.commit()

    response = client.get(f'/aircraft/{sample_data.id}/incidents/export.csv?source=NTSB')
    assert response.status_code == 200
    assert b'Alpha Airlines' in response.data
    assert b'Beta Airlines' not in response.data

def test_request_data_page(client):
    """Test the data request page."""
    response = client.get('/feedback/request')
    assert response.status_code == 200
    assert b'Request Missing Data' in response.data

def test_request_data_submission(client, app):
    """Test submitting a data request."""
    with app.app_context():
        initial_count = Request.query.count()
        
        response = client.post('/feedback/request', data={
            'aircraft_model': 'New Plane',
            'email': 'test@example.com'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Thank you! Your request has been recorded' in response.data
        assert Request.query.count() == initial_count + 1
        
        req = Request.query.filter_by(aircraft_model='New Plane').first()
        assert req is not None
        assert req.user_email == 'test@example.com'


def test_analyze_report_requires_input(client):
    response = client.post('/api/analyze-report', json={})
    assert response.status_code == 400
    body = response.get_json()
    assert body['error'] == 'Missing input'


def test_analyze_report_success(client):
    with patch('app.routes.ReportAnalyzerService') as mock_service:
        analyzer_instance = mock_service.return_value
        analyzer_instance.analyze_report.return_value = ({
            'root_cause': 'Hydraulic failure',
            'contributing_factors': ['Leak'],
            'summary': 'Test summary',
            'ai_model': 'mock',
            'cached': False,
            'remaining': 9
        }, 200)

        response = client.post('/api/analyze-report', json={
            'report_text': 'Synthetic report text for testing.',
            'model': 'gemini'
        })

        assert response.status_code == 200
        body = response.get_json()
        assert body['root_cause'] == 'Hydraulic failure'
        assert body['summary'] == 'Test summary'
