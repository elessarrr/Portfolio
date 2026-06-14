import pytest
from app.models import Request

def test_home_page(client):
    """Test that the home page loads correctly."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Aircraft Safety Tracker' in response.data
    assert b'Search for an aircraft' in response.data

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

def test_aircraft_details(client, sample_data):
    """Test the aircraft details page."""
    response = client.get(f'/aircraft/{sample_data.id}')
    assert response.status_code == 200
    assert b'Boeing 737' in response.data
    assert b'Total Incidents' in response.data
    assert b'Years in Service' not in response.data
    assert b'10' in response.data  # total_incidents from sample_data
    
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

def test_request_data_page(client):
    """Test the data request page."""
    response = client.get('/feedback/request')
    assert response.status_code == 200
    assert b'Request Missing Data' in response.data

def test_request_data_empty_submit_shows_validation(client):
    """Bug 4.2: empty POST must show server-side validation errors."""
    response = client.post(
        '/feedback/request',
        data={'aircraft_model': '', 'email': ''},
    )
    assert response.status_code == 200
    assert b'This field is required' in response.data
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