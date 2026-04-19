from unittest.mock import patch
from datetime import date, timedelta

import pytest

from app import create_app, db
from app.models import Aircraft, AircraftVariant, Incident, IncidentSource, Request, SystemTag
from config import config as app_config


def test_home_page(client):
    """Test that the home page loads correctly."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Aircraft Safety Tracker' in response.data
    assert b'Search for an aircraft' in response.data


def test_footer_renders_data_freshness(client, app):
    from datetime import datetime

    from app import db
    from app.models import ImportState

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


def test_date_from_filter_applies_to_incident_list_and_export(client, sample_data):
    response = client.get(f'/aircraft/{sample_data.id}/incidents?date_from=2021-01-01')
    assert response.status_code == 200
    assert b'Beta Airlines' in response.data
    assert b'Alpha Airlines' not in response.data

    export_response = client.get(f'/aircraft/{sample_data.id}/incidents/export.csv?date_from=2021-01-01')
    assert export_response.status_code == 200
    assert b'Beta Airlines' in export_response.data
    assert b'Alpha Airlines' not in export_response.data


def test_aircraft_detail_and_incident_list_cap_results_to_50(client, app, sample_data):
    with app.app_context():
        for index in range(60):
            db.session.add(Incident(
                aircraft_id=sample_data.id,
                date=date(1990, 1, 1) + timedelta(days=index),
                operator=f'Load Test Airline {index:02d}',
                location='Performance Test Location',
                fatalities=0,
                description='Performance test incident',
                incident_type='Incident',
            ))
        db.session.commit()

    details_response = client.get(f'/aircraft/{sample_data.id}')
    assert details_response.status_code == 200
    assert b'Load Test Airline 59' in details_response.data
    assert b'Load Test Airline 00' not in details_response.data

    list_response = client.get(f'/aircraft/{sample_data.id}/incidents')
    assert list_response.status_code == 200
    assert b'Load Test Airline 59' in list_response.data
    assert b'Load Test Airline 00' not in list_response.data


def test_null_date_incidents_do_not_break_sorting_on_detail_routes(client, app, sample_data):
    with app.app_context():
        db.session.add(Incident(
            aircraft_id=sample_data.id,
            date=None,
            operator='Null Date Airline',
            location='Unknown Date Location',
            fatalities=0,
            description='Incident with null date',
            incident_type='Incident',
        ))
        db.session.commit()

    details_response = client.get(f'/aircraft/{sample_data.id}')
    assert details_response.status_code == 200
    assert b'Null Date Airline' in details_response.data

    list_response = client.get(f'/aircraft/{sample_data.id}/incidents')
    assert list_response.status_code == 200
    assert b'Null Date Airline' in list_response.data

    export_response = client.get(f'/aircraft/{sample_data.id}/incidents/export.csv')
    assert export_response.status_code == 200
    assert b'Null Date Airline' in export_response.data


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


def test_incident_priority_order_prefers_ntsb_then_faa_aids_then_faa_sdr_then_asn(client, app, sample_data):
    with app.app_context():
        priority_incidents = []
        for operator in ('Priority NTSB', 'Priority FAA_AIDS', 'Priority FAA_SDR', 'Priority ASN'):
            incident = Incident(
                aircraft_id=sample_data.id,
                date=date(2022, 1, 1),
                operator=operator,
                location='Priority Ordering Location',
                fatalities=0,
                description='Priority ordering test incident',
                incident_type='Incident',
            )
            db.session.add(incident)
            priority_incidents.append(incident)
        db.session.flush()

        db.session.add(IncidentSource(incident_id=priority_incidents[0].id, source_name='NTSB', source_url='https://example.com/ntsb'))
        db.session.add(IncidentSource(incident_id=priority_incidents[1].id, source_name='FAA_AIDS', source_url='https://example.com/faa-aids'))
        db.session.add(IncidentSource(incident_id=priority_incidents[2].id, source_name='FAA_SDR', source_url='https://example.com/faa-sdr'))
        db.session.add(IncidentSource(incident_id=priority_incidents[3].id, source_name='ASN', source_url='https://example.com/asn'))
        db.session.commit()

    response = client.get(f'/aircraft/{sample_data.id}/incidents')
    assert response.status_code == 200
    body = response.data
    ntsb_pos = body.find(b'Priority NTSB')
    faa_aids_pos = body.find(b'Priority FAA_AIDS')
    faa_sdr_pos = body.find(b'Priority FAA_SDR')
    asn_pos = body.find(b'Priority ASN')

    assert -1 not in (ntsb_pos, faa_aids_pos, faa_sdr_pos, asn_pos)
    assert ntsb_pos < faa_aids_pos < faa_sdr_pos < asn_pos


def test_incident_list_shows_primary_source_indicator_badge(client, app, sample_data):
    with app.app_context():
        incident = Incident.query.filter_by(aircraft_id=sample_data.id, operator='Alpha Airlines').first()
        db.session.add(IncidentSource(incident_id=incident.id, source_name='FAA_SDR', source_url='https://example.com/faa-sdr'))
        db.session.add(IncidentSource(incident_id=incident.id, source_name='NTSB', source_url='https://example.com/ntsb'))
        db.session.commit()

    response = client.get(f'/aircraft/{sample_data.id}/incidents')
    assert response.status_code == 200
    assert b'Primary Source: NTSB' in response.data


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


def test_analyze_report_client_id_uses_remote_addr_by_default(client, app):
    with patch('app.routes.ReportAnalyzerService') as mock_service:
        analyzer_instance = mock_service.return_value
        analyzer_instance.analyze_report.return_value = ({'summary': 'ok'}, 200)
        app.config['TRUST_X_FORWARDED_FOR'] = False

        response = client.post('/api/analyze-report', json={
            'report_text': 'Synthetic report text for testing.',
            'model': 'gemini'
        }, headers={'X-Forwarded-For': '203.0.113.10'})

        assert response.status_code == 200
        call_kwargs = analyzer_instance.analyze_report.call_args.kwargs
        assert call_kwargs['client_id'] == '127.0.0.1'


def test_analyze_report_client_id_can_use_forwarded_for_when_trusted(client, app):
    with patch('app.routes.ReportAnalyzerService') as mock_service:
        analyzer_instance = mock_service.return_value
        analyzer_instance.analyze_report.return_value = ({'summary': 'ok'}, 200)
        app.config['TRUST_X_FORWARDED_FOR'] = True

        response = client.post('/api/analyze-report', json={
            'report_text': 'Synthetic report text for testing.',
            'model': 'gemini'
        }, headers={'X-Forwarded-For': '203.0.113.10, 10.0.0.1'})

        assert response.status_code == 200
        call_kwargs = analyzer_instance.analyze_report.call_args.kwargs
        assert call_kwargs['client_id'] == '203.0.113.10'


def test_analyze_report_rejects_oversized_report_text(client, app):
    max_chars = app.config['REPORT_ANALYZER_MAX_REPORT_TEXT_CHARS']
    response = client.post('/api/analyze-report', json={
        'report_text': 'x' * (max_chars + 1),
        'model': 'gemini'
    })
    assert response.status_code == 413
    body = response.get_json()
    assert body['error'] == 'Payload too large'


def test_create_app_production_requires_secret_key(monkeypatch):
    monkeypatch.setattr(app_config['production'], 'SECRET_KEY', None)
    with pytest.raises(ValueError):
        create_app('production')


def test_create_app_production_accepts_strong_secret_key(monkeypatch):
    monkeypatch.setattr(app_config['production'], 'SECRET_KEY', 'x' * 32)
    app = create_app('production')
    assert app.config['SECRET_KEY'] == 'x' * 32
