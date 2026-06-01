import pytest
from unittest.mock import patch
from app.models import Aircraft
from app import db
from app.routes import generate_summary_background
from app.services.deepseek import SUMMARY_UNAVAILABLE_USER_MESSAGE

@pytest.fixture
def mock_deepseek():
    with patch('app.routes.DeepSeekService') as mock:
        yield mock

@pytest.fixture
def mock_thread():
    with patch('app.routes.threading.Thread') as mock:
        yield mock

def test_regenerate_summary_htmx(client, sample_data, mock_deepseek, mock_thread, app):
    """Test regenerating summary via HTMX."""
    # Setup mock thread to just call the target function directly synchronously for testing
    def run_target(*args, **kwargs):
        kwargs.get('target', args[0] if args else None)(*kwargs.get('args', args[1:] if len(args)>1 else ()))
        
    mock_thread_instance = mock_thread.return_value
    mock_thread_instance.start.side_effect = lambda: run_target(
        target=mock_thread.call_args[1]['target'], 
        args=mock_thread.call_args[1]['args']
    )
    
    mock_instance = mock_deepseek.return_value
    mock_instance.generate_aircraft_summary.return_value = "<h2>New Summary</h2>"
    
    # Make HTMX request
    headers = {'HX-Request': 'true'}
    response = client.get(f'/aircraft/{sample_data.id}/regenerate-summary', headers=headers)
    
    assert response.status_code == 200
    # The initial HTMX response should be the polling partial
    assert b'Generating AI summary... Please wait.' in response.data
    assert b'id="summary-card"' in response.data
    
    # Verify DB update happened via the "background" thread
    with app.app_context():
        updated_aircraft = db.session.get(Aircraft, sample_data.id)
        assert updated_aircraft.ai_summary == "<h2>New Summary</h2>"

def test_generate_summary_background_stores_safe_message_on_api_failure(app, sample_data):
    """Bug 4.1: never persist raw API error text in ai_summary."""
    with patch("app.routes.DeepSeekService") as mock_service:
        mock_service.return_value.generate_aircraft_summary.return_value = (
            SUMMARY_UNAVAILABLE_USER_MESSAGE
        )
        with app.app_context():
            generate_summary_background(app.app_context, sample_data.id)
            aircraft = db.session.get(Aircraft, sample_data.id)
            assert aircraft.ai_summary == SUMMARY_UNAVAILABLE_USER_MESSAGE
            assert "Error" not in aircraft.ai_summary
            assert "Authentication" not in aircraft.ai_summary


def test_regenerate_summary_redirect(client, sample_data, mock_deepseek, mock_thread):
    """Test regenerating summary via normal request (redirect)."""
    # Just mock the thread start to do nothing for this test, we only care about the redirect and flash
    
    response = client.get(f'/aircraft/{sample_data.id}/regenerate-summary', follow_redirects=True)
    
    assert response.status_code == 200
    # Should redirect to the aircraft details page
    assert b'Summary generation started' in response.data
