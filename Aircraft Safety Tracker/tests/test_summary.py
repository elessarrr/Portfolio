import pytest
from unittest.mock import patch
from app.models import Aircraft
from app import db

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

def test_regenerate_summary_redirect(client, sample_data, mock_deepseek, mock_thread):
    """Test regenerating summary via normal request (redirect)."""
    # Just mock the thread start to do nothing for this test, we only care about the redirect and flash
    
    response = client.get(f'/aircraft/{sample_data.id}/regenerate-summary', follow_redirects=True)
    
    assert response.status_code == 200
    # Should redirect to the aircraft details page
    assert b'Summary generation started' in response.data
