import pytest
from unittest.mock import patch
from app.models import Aircraft
from app import db

@pytest.fixture
def mock_gemini():
    with patch('app.routes.GeminiService') as mock:
        yield mock

def test_regenerate_summary_htmx(client, sample_data, mock_gemini, app):
    """Test regenerating summary via HTMX."""
    # Setup mock
    mock_instance = mock_gemini.return_value
    mock_instance.generate_aircraft_summary.return_value = "<h2>New Summary</h2>"
    
    # Make HTMX request
    headers = {'HX-Request': 'true'}
    response = client.get(f'/aircraft/{sample_data.id}/regenerate-summary', headers=headers)
    
    assert response.status_code == 200
    assert b'New Summary' in response.data
    assert b'id="summary-card"' in response.data
    
    # Verify DB update
    with app.app_context():
        updated_aircraft = db.session.get(Aircraft, sample_data.id)
        assert updated_aircraft.ai_summary == "<h2>New Summary</h2>"

def test_regenerate_summary_redirect(client, sample_data, mock_gemini):
    """Test regenerating summary via normal request (redirect)."""
    mock_instance = mock_gemini.return_value
    mock_instance.generate_aircraft_summary.return_value = "Redirect Summary"
    
    response = client.get(f'/aircraft/{sample_data.id}/regenerate-summary', follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Redirect Summary' in response.data
    assert b'Summary regenerated successfully' in response.data
