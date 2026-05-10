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


def test_faq_page_loads_with_international_investigations_section(client):
    response = client.get('/faq')
    assert response.status_code == 200
    assert b'Frequently Asked Questions' in response.data
    assert b'id="international-investigations"' in response.data


def test_home_navigation_includes_faq_link_and_link_target_loads(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'href="/faq"' in response.data
    assert b'>FAQ<' in response.data

    faq_response = client.get('/faq')
    assert faq_response.status_code == 200
    assert b'Frequently Asked Questions' in faq_response.data


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


def test_search_orders_base_model_before_variant_model(client, app):
    with app.app_context():
        base = Aircraft(
            manufacturer='SortMaker',
            model_name='SortMaker 747',
            total_incidents=1,
            fatal_incidents=0,
            total_fatalities=0,
        )
        variant = Aircraft(
            manufacturer='SortMaker',
            model_name='SortMaker 747-400',
            total_incidents=1,
            fatal_incidents=0,
            total_fatalities=0,
        )
        db.session.add_all([variant, base])
        db.session.commit()
        base_id = base.id
        variant_id = variant.id

    response = client.get('/search?q=SortMaker')
    assert response.status_code == 200
    html = response.data.decode('utf-8')

    base_href = f'/aircraft/{base_id}'
    variant_href = f'/aircraft/{variant_id}'
    assert base_href in html
    assert variant_href in html
    assert html.index(base_href) < html.index(variant_href)


def test_autocomplete_orders_base_model_before_variant_model(client, app):
    with app.app_context():
        base = Aircraft(
            manufacturer='SortAuto',
            model_name='SortAuto 747',
            total_incidents=1,
            fatal_incidents=0,
            total_fatalities=0,
        )
        variant = Aircraft(
            manufacturer='SortAuto',
            model_name='SortAuto 747-400',
            total_incidents=1,
            fatal_incidents=0,
            total_fatalities=0,
        )
        db.session.add_all([variant, base])
        db.session.commit()

    response = client.get('/api/search/autocomplete?q=SortAuto')
    assert response.status_code == 200
    payload = response.get_json()
    names = [row['make_model'] for row in payload['results']]
    assert 'SortAuto 747' in names
    assert 'SortAuto 747-400' in names
    assert names.index('SortAuto 747') < names.index('SortAuto 747-400')


def test_search_includes_variants(client, app, sample_data):
    with app.app_context():
        db.session.add(AircraftVariant(aircraft_id=sample_data.id, variant_name='737-800', total_incidents=3, fatal_incidents=1))
        db.session.commit()

    response = client.get('/search?q=737-800')
    assert response.status_code == 200
    assert b'Boeing 737' in response.data
    assert b'737-800' in response.data
    assert b'variant=737-800' in response.data


def test_search_includes_aircraft_without_variants_when_same_series_has_variants(client, app, sample_data):
    with app.app_context():
        variant_backed_aircraft = Aircraft(
            manufacturer='Boeing',
            model_name='Boeing 737-800',
            total_incidents=2,
            fatal_incidents=0,
            total_fatalities=0,
        )
        variantless_aircraft = Aircraft(
            manufacturer='Boeing',
            model_name='Boeing 737 MAX',
            total_incidents=1,
            fatal_incidents=0,
            total_fatalities=0,
        )
        db.session.add_all([variant_backed_aircraft, variantless_aircraft])
        db.session.flush()

        db.session.add(AircraftVariant(
            aircraft_id=variant_backed_aircraft.id,
            variant_name='737-800',
            total_incidents=2,
            fatal_incidents=0,
        ))
        db.session.commit()

    response = client.get('/search?q=Boeing 737')
    assert response.status_code == 200
    assert b'737-800' in response.data
    assert b'Boeing 737 MAX' in response.data


def test_search_returns_aircraft_without_variants_that_match_query(client, app):
    with app.app_context():
        aircraft = Aircraft(
            manufacturer='Boeing',
            model_name='Boeing 717',
            total_incidents=3,
            fatal_incidents=0,
            total_fatalities=0,
        )
        db.session.add(aircraft)
        db.session.commit()

    response = client.get('/search?q=717')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'Boeing 717' in html
    assert 'variant=' not in html


def test_search_single_series_shows_models_empty_state(client, sample_data):
    response = client.get('/search?q=Boeing')
    assert response.status_code == 200
    assert b'Boeing 737' in response.data
    assert b'View Data' in response.data

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


def test_aircraft_details_returns_200_for_minimal_aircraft_record(client, app):
    with app.app_context():
        aircraft = Aircraft(
            manufacturer='McDonnell Douglas',
            model_name='McDonnell Douglas MD-80',
            years_in_service=0,
            total_incidents=0,
            fatal_incidents=0,
            total_fatalities=0,
            ai_summary=None,
        )
        db.session.add(aircraft)
        db.session.commit()
        aircraft_id = aircraft.id

    response = client.get(f'/aircraft/{aircraft_id}')
    assert response.status_code == 200
    assert b'McDonnell Douglas MD-80' in response.data
    assert b'Incident History' in response.data


def test_aircraft_details_returns_404_for_nonexistent_aircraft(client):
    response = client.get('/aircraft/999999')
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


def test_global_incident_list_renders_no_link_chip_when_source_urls_are_null(client, app):
    """
    Per PRD-0016 FR-28: When source_url and report_url are both null,
    no link element is rendered (suppressed entirely).
    """
    with app.app_context():
        aircraft = Aircraft.query.first()
        if not aircraft:
            aircraft = Aircraft(
                manufacturer='Airbus', model_name='Airbus A320',
                total_incidents=1, fatal_incidents=0, total_fatalities=0
            )
            db.session.add(aircraft)
            db.session.commit()
        aircraft_id = aircraft.id
        incident = Incident(
            aircraft_id=aircraft_id,
            date=date(2022, 5, 1),
            operator='Test Airways',
            location='Boston, MA',
            fatalities=0,
            description='Test',
            incident_type='Accident',
        )
        db.session.add(incident)
        db.session.flush()
        db.session.add(IncidentSource(
            incident_id=incident.id,
            source_name='FAA_AIDS',
            source_url=None,
            report_url=None,
        ))
        db.session.commit()

    response = client.get(f'/aircraft/{aircraft_id}/incidents')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'FAA_AIDS (Unavailable)' not in html


def test_aircraft_incident_list_hides_inactive_sources(client, app):
    with app.app_context():
        aircraft = Aircraft.query.first()
        if not aircraft:
            aircraft = Aircraft(
                manufacturer='Boeing', model_name='Boeing 737',
                total_incidents=1, fatal_incidents=0, total_fatalities=0
            )
            db.session.add(aircraft)
            db.session.commit()

        incident = Incident(
            aircraft_id=aircraft.id,
            date=date(2024, 1, 1),
            operator='Inactive Source Test Airline',
            location='Seattle, WA',
            fatalities=0,
            description='Inactive source visibility test',
            incident_type='Accident',
        )
        db.session.add(incident)
        db.session.flush()

        db.session.add(IncidentSource(
            incident_id=incident.id,
            source_name='NTSB',
            source_record_id='HIDE-ME-001',
            source_url='https://example.com/hidden-link',
            is_active=False,
        ))
        db.session.commit()
        aircraft_id = aircraft.id

    response = client.get(f'/aircraft/{aircraft_id}/incidents')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'HIDE-ME-001' not in html
    assert 'hidden-link' not in html


def test_ntsb_details_and_docs_both_render_when_both_urls_exist(client, app):
    """
    Per PRD-0016 (existing requirement): NTSB Details and NTSB Docs links
    both render when both URLs are non-null.
    The aircraft detail page (incident_list.html) shows two separate links:
    - NTSB link → Details (built from source_record_id docket URL)
    - NTSB Docs link → separate PDF/report link
    """
    with app.app_context():
        aircraft = Aircraft.query.first()
        if not aircraft:
            aircraft = Aircraft(
                manufacturer='Boeing', model_name='Boeing 737',
                total_incidents=1, fatal_incidents=0, total_fatalities=0
            )
            db.session.add(aircraft)
            db.session.commit()
        aircraft_id = aircraft.id
        incident = Incident(
            aircraft_id=aircraft_id,
            date=date(2023, 8, 1),
            operator='Test Airline',
            location='New York, NY',
            fatalities=0,
            description='Test',
            incident_type='Accident',
        )
        db.session.add(incident)
        db.session.flush()
        db.session.add(IncidentSource(
            incident_id=incident.id,
            source_name='NTSB',
            source_record_id='TEST123',
            source_url='https://data.ntsb.gov/Docket/?NTSBNumber=TEST123',
            report_url='https://data.ntsb.gov/carol-repgen/api/Aviation/ReportMain/GenerateNewestReport/TEST123/pdf',
        ))
        db.session.commit()

    response = client.get(f'/aircraft/{aircraft_id}/incidents')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'data.ntsb.gov/Docket' in html
    assert 'NTSB Docs' in html


def test_ntsb_external_links_have_target_blank_and_noopener(client, app):
    """
    Per PRD-0016 (existing requirement): NTSB external links must have
    target="_blank" and rel="noopener noreferrer" attributes.
    """
    with app.app_context():
        aircraft = Aircraft.query.first()
        if not aircraft:
            aircraft = Aircraft(
                manufacturer='Boeing', model_name='Boeing 747',
                total_incidents=1, fatal_incidents=0, total_fatalities=0
            )
            db.session.add(aircraft)
            db.session.commit()
        incident = Incident(
            aircraft_id=aircraft.id,
            date=date(2023, 9, 1),
            operator='Test Carrier',
            location='Chicago, IL',
            fatalities=0,
            description='Test',
            incident_type='Accident',
        )
        db.session.add(incident)
        db.session.flush()
        db.session.add(IncidentSource(
            incident_id=incident.id,
            source_name='NTSB',
            source_record_id='TEST456',
            source_url='https://data.ntsb.gov/Docket/?NTSBNumber=TEST456',
            report_url='https://data.ntsb.gov/carol-repgen/api/Aviation/ReportMain/GenerateNewestReport/TEST456/pdf',
        ))
        db.session.commit()

    response = client.get('/incidents')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'target="_blank"' in html
    assert 'rel="noopener noreferrer"' in html


def test_data_source_status_returns_valid_json(client, app):
    """
    Per PRD-0016 FR-15: GET /api/data-source-status returns JSON with source_name,
    last_successful_at, last_status, last_error for all configured sources.
    """
    with app.app_context():
        from datetime import datetime
        from app.models import ImportState, db

        db.session.add(ImportState(
            source_name='NTSB',
            last_status='completed',
            last_successful_at=datetime(2026, 4, 1, 10, 0, 0),
            last_attempted_at=datetime(2026, 4, 1, 10, 5, 0),
            last_error=None,
            updated_at=datetime.utcnow(),
        ))
        db.session.add(ImportState(
            source_name='FAA_AIDS',
            last_status='failed',
            last_attempted_at=datetime(2026, 4, 2, 8, 0, 0),
            last_error='Connection timeout',
            updated_at=datetime.utcnow(),
        ))
        db.session.commit()

    response = client.get('/api/data-source-status')
    assert response.status_code == 200
    assert response.content_type == 'application/json'
    data = response.get_json()
    assert isinstance(data, list)
    source_names = {item['source_name'] for item in data}
    assert 'NTSB' in source_names
    assert 'FAA_AIDS' in source_names
    ntsb_entry = next(item for item in data if item['source_name'] == 'NTSB')
    assert ntsb_entry['last_status'] == 'completed'
    assert ntsb_entry['last_error'] is None
    faa_entry = next(item for item in data if item['source_name'] == 'FAA_AIDS')
    assert faa_entry['last_status'] == 'failed'


# =============================================================================
# PRD-0017: Homepage Search Enhancement and Aircraft Details Error Handling
# =============================================================================

def test_search_returns_all_aircraft_without_limit(client, app):
    """
    Per PRD-0017 1.1: The search() function should return all Aircraft models
    without any artificial limit (previously limit(20) was applied).
    """
    with app.app_context():
        for i in range(25):
            aircraft = Aircraft(
                manufacturer='Acme',
                model_name=f'Galaxy {i}',
                total_incidents=i,
                fatal_incidents=0,
                total_fatalities=0
            )
            db.session.add(aircraft)
        db.session.commit()

    response = client.get('/search?q=Galaxy')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    for i in range(25):
        assert f'Galaxy {i}' in html, f'Galaxy {i} should be in results'


def test_search_groups_variants_by_series_correctly(client, app, sample_data):
    """
    Per PRD-0017 1.2: Grouping logic (series_name) works correctly with
    expanded dataset. Variants are grouped under their series name.
    """
    with app.app_context():
        AircraftVariant.query.filter_by(aircraft_id=sample_data.id).delete()
        db.session.add(AircraftVariant(aircraft_id=sample_data.id, variant_name='737-800', total_incidents=3, fatal_incidents=1))
        db.session.add(AircraftVariant(aircraft_id=sample_data.id, variant_name='737-900', total_incidents=2, fatal_incidents=0))
        db.session.commit()

    response = client.get('/search?q=Boeing')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert '737-800' in html
    assert '737-900' in html
    assert 'Boeing 737' in html


def test_search_returns_multiple_boeing_series_groups(client, app, sample_data):
    with app.app_context():
        db.session.add_all([
            Aircraft(
                manufacturer='Boeing',
                model_name='Boeing 707',
                total_incidents=4,
                fatal_incidents=1,
                total_fatalities=10,
            ),
            Aircraft(
                manufacturer='Boeing',
                model_name='Boeing 727',
                total_incidents=6,
                fatal_incidents=2,
                total_fatalities=20,
            ),
        ])
        db.session.commit()

    response = client.get('/search?q=Boeing')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'Boeing 707' in html
    assert 'Boeing 727' in html
    assert 'Boeing 737' in html
    assert html.count('class="series-btn') >= 3


def test_search_no_duplicate_entries(client, app):
    """
    Per PRD-0017 1.3: No duplicate entries appear in the rendered table.
    Each AircraftVariant should appear only once.
    """
    with app.app_context():
        Aircraft.query.delete()
        AircraftVariant.query.delete()
        db.session.commit()

        aircraft = Aircraft(
            manufacturer='Test',
            model_name='Test Aircraft',
            total_incidents=10,
            fatal_incidents=2,
            total_fatalities=50
        )
        db.session.add(aircraft)
        db.session.commit()

        db.session.add(AircraftVariant(aircraft_id=aircraft.id, variant_name='Variant-A', total_incidents=5, fatal_incidents=1))
        db.session.add(AircraftVariant(aircraft_id=aircraft.id, variant_name='Variant-B', total_incidents=3, fatal_incidents=0))
        db.session.commit()

    response = client.get('/search?q=Test')
    assert response.status_code == 200
    html = response.data.decode('utf-8')

    import re
    variant_a_links = re.findall(r'href="[^"]*variant=Variant-A"', html)
    variant_b_links = re.findall(r'href="[^"]*variant=Variant-B"', html)
    assert len(variant_a_links) == 1, f'Variant-A link should appear exactly once, found {len(variant_a_links)}'
    assert len(variant_b_links) == 1, f'Variant-B link should appear exactly once, found {len(variant_b_links)}'


def test_aircraft_details_with_valid_id_returns_200(client, sample_data):
    """
    Per PRD-0017 4.2.1: Accessing /aircraft/<valid_id> returns 200 OK.
    """
    response = client.get(f'/aircraft/{sample_data.id}')
    assert response.status_code == 200
    assert b'Boeing 737' in response.data


def test_aircraft_details_with_invalid_id_returns_404(client):
    """
    Per PRD-0017 4.2.2: Accessing /aircraft/<invalid_id> returns 404 Not Found.
    """
    response = client.get('/aircraft/99999')
    assert response.status_code == 404
    assert b'Page Not Found' in response.data


def test_global_incident_list_excludes_orphaned_incidents(client, app, sample_data):
    """
    Per PRD-0017 3.4: The global incidents routes should render successfully even
    when orphaned incident rows exist, and those rows should not break the list.
    """
    with app.app_context():
        orphaned_incident = Incident(
            aircraft_id=sample_data.id + 999,
            date=date(2023, 1, 1),
            operator='Orphaned Airline',
            location='Unknown Location',
            fatalities=0,
            description='Incident with invalid aircraft_id',
            incident_type='Incident',
            raw_model_variant='Unknown Boeing 747'
        )
        db.session.add(orphaned_incident)
        db.session.commit()

    response = client.get('/incidents')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'Orphaned Airline' not in html

    page_response = client.get('/incidents/page?page=1')
    assert page_response.status_code == 200
    assert 'Orphaned Airline' not in page_response.data.decode('utf-8')
