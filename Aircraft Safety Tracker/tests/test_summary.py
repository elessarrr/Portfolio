from unittest.mock import patch

import pytest

from app import db
from app.models import Aircraft, SummaryGenerationJob


@pytest.fixture
def mock_deepseek():
    with patch('app.routes.DeepSeekService') as mock:
        yield mock

def test_regenerate_summary_htmx(client, sample_data, mock_deepseek, app):
    mock_instance = mock_deepseek.return_value
    mock_instance.generate_aircraft_summary.return_value = "New Summary"

    headers = {'HX-Request': 'true'}
    response = client.get(f'/aircraft/{sample_data.id}/regenerate-summary', headers=headers)

    assert response.status_code == 200
    assert b'Generating AI summary... Please wait.' in response.data
    assert b'id="summary-card"' in response.data

    with app.app_context():
        jobs = SummaryGenerationJob.query.filter_by(aircraft_id=sample_data.id).all()
        assert len(jobs) == 1
        assert jobs[0].status == 'pending'

    status_response = client.get(f'/aircraft/{sample_data.id}/summary-status', headers=headers)
    assert status_response.status_code == 200
    assert b'New Summary' in status_response.data

    with app.app_context():
        updated_aircraft = db.session.get(Aircraft, sample_data.id)
        assert updated_aircraft.ai_summary == "New Summary"
        job = SummaryGenerationJob.query.filter_by(aircraft_id=sample_data.id).first()
        assert job.status == 'completed'

def test_regenerate_summary_redirect(client, sample_data, mock_deepseek):
    response = client.get(f'/aircraft/{sample_data.id}/regenerate-summary', follow_redirects=True)

    assert response.status_code == 200
    assert b'Summary generation started' in response.data


def test_summary_disabled_when_no_incidents(client, app):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='NO-INCIDENTS-1', ai_summary='Stale summary')
        db.session.add(aircraft)
        db.session.commit()
        aircraft_id = aircraft.id

    response = client.get(f'/aircraft/{aircraft_id}')
    assert response.status_code == 200
    assert b'AI Safety Summary' not in response.data
    assert b'No incidents available for this aircraft. AI summary is disabled until incident data exists.' not in response.data
    assert b'Regenerate' not in response.data
    assert b'Stale summary' not in response.data


def test_regenerate_summary_htmx_skips_when_no_incidents(client, app, mock_deepseek):
    with app.app_context():
        aircraft = Aircraft(manufacturer='Boeing', model_name='NO-INCIDENTS-2', ai_summary='Old generated summary')
        db.session.add(aircraft)
        db.session.commit()
        aircraft_id = aircraft.id

    response = client.get(f'/aircraft/{aircraft_id}/regenerate-summary', headers={'HX-Request': 'true'})
    assert response.status_code == 200
    assert b'No incidents available for this aircraft. AI summary is disabled until incident data exists.' in response.data
    assert b'Generating AI summary... Please wait.' not in response.data
    assert b'Regenerate' not in response.data
    mock_deepseek.assert_not_called()

    with app.app_context():
        refreshed = db.session.get(Aircraft, aircraft_id)
        assert refreshed.ai_summary is None
