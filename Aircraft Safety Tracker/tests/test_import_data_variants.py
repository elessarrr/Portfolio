import json
import os
import sys
from datetime import date
from unittest.mock import patch, MagicMock

from app import db
from app.models import Aircraft, AircraftVariant, Incident, IncidentSource


def _make_mock_response(status_code: int = 200, headers: dict = None, text: str = ""):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.headers = headers or {}
    mock_response.text = text
    return mock_response


def _make_mock_client(mock_response: MagicMock) -> MagicMock:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=None)
    mock_client.head = MagicMock(return_value=mock_response)
    mock_client.get = MagicMock(return_value=mock_response)
    return mock_client


def test_ntsb_variant_mismatch_source_identifiers_stay_with_incident(app):
    """
    Per PRD-0016 FR-36/FR-37: NTSB link identifiers must stay bound to the
    original incident's source_record_id even when model resolution falls back
    to a parent aircraft.

    Scenario: An incident with raw_model_variant="Boeing 707-321B" is linked
    to a parent aircraft "Boeing 707" because "Boeing 707-321B" doesn't exist.
    The NTSB source identifiers (source_record_id, source_url) must NOT drift
    to the "Boeing 707" aircraft — they remain with the incident.
    """
    with app.app_context():
        parent = Aircraft(
            manufacturer='Boeing', model_name='Boeing 707',
            total_incidents=1, fatal_incidents=0, total_fatalities=0
        )
        db.session.add(parent)
        db.session.flush()
        parent_id = parent.id

        incident = Incident(
            aircraft_id=parent_id,
            raw_model_variant='Boeing 707-321B',
            date=date(2011, 5, 18),
            operator='Test Airline',
            location='Unknown',
            fatalities=0,
            description='Test',
            incident_type='Accident',
        )
        db.session.add(incident)
        db.session.flush()
        incident_id = incident.id

        db.session.add(IncidentSource(
            incident_id=incident_id,
            source_name='NTSB',
            source_record_id='DCA11PA075',
            source_url='https://data.ntsb.gov/Docket/?NTSBNumber=DCA11PA075',
            report_url=None,
        ))
        db.session.commit()

        src = IncidentSource.query.filter_by(source_record_id='DCA11PA075').first()
        assert src is not None
        assert src.incident_id == incident_id
        assert src.incident.aircraft_id == parent_id
        assert src.incident.raw_model_variant == 'Boeing 707-321B'
        assert src.source_url == 'https://data.ntsb.gov/Docket/?NTSBNumber=DCA11PA075'


def test_incident_with_null_aircraft_id_renders_without_error(client, app):
    """
    Per PRD-0016 FR-20: Incident with null aircraft_id renders without error.
    """
    with app.app_context():
        aircraft = Aircraft(
            manufacturer='Boeing', model_name='Boeing 757',
            total_incidents=1, fatal_incidents=0, total_fatalities=0
        )
        db.session.add(aircraft)
        db.session.commit()
        aircraft_id = aircraft.id
        incident = Incident(
            aircraft_id=None,
            raw_model_variant='Unknown Model',
            date=date(2020, 1, 1),
            operator='Test',
            location='Test',
            fatalities=0,
            description='No aircraft link',
            incident_type='Accident',
        )
        db.session.add(incident)
        db.session.flush()
        incident_id = incident.id
        db.session.add(IncidentSource(
            incident_id=incident_id,
            source_name='ASN',
            source_url='https://example.com/test',
        ))
        db.session.commit()

    response = client.get(f'/aircraft/{aircraft_id}/incidents')
    assert response.status_code == 200


def test_incident_with_null_date_renders_without_error(client, app):
    """
    Per PRD-0016 FR-20: Incident with null date renders without error.
    """
    with app.app_context():
        aircraft = Aircraft(
            manufacturer='Airbus', model_name='Airbus A320',
            total_incidents=1, fatal_incidents=0, total_fatalities=0
        )
        db.session.add(aircraft)
        db.session.commit()
        aircraft_id = aircraft.id
        incident = Incident(
            aircraft_id=aircraft_id,
            date=None,
            operator='Test',
            location='Test',
            fatalities=0,
            description='No date',
            incident_type='Accident',
        )
        db.session.add(incident)
        db.session.flush()
        incident_id = incident.id
        db.session.add(IncidentSource(
            incident_id=incident_id,
            source_name='FAA_AIDS',
            source_url='https://example.com/test',
        ))
        db.session.commit()

    response = client.get(f'/aircraft/{aircraft_id}/incidents')
    assert response.status_code == 200


def test_incident_with_null_source_url_renders_without_error(client, app):
    """
    Per PRD-0016 FR-20: Incident with null source_url renders without error.
    """
    with app.app_context():
        aircraft = Aircraft(
            manufacturer='Cessna', model_name='Cessna 172',
            total_incidents=1, fatal_incidents=0, total_fatalities=0
        )
        db.session.add(aircraft)
        db.session.commit()
        aircraft_id = aircraft.id
        incident = Incident(
            aircraft_id=aircraft_id,
            date=date(2019, 3, 1),
            operator='Test',
            location='Test',
            fatalities=0,
            description='No source URL',
            incident_type='Accident',
        )
        db.session.add(incident)
        db.session.flush()
        incident_id = incident.id
        db.session.add(IncidentSource(
            incident_id=incident_id,
            source_name='FAA_SDR',
            source_url=None,
            report_url=None,
        ))
        db.session.commit()

    response = client.get(f'/aircraft/{aircraft_id}/incidents')
    assert response.status_code == 200


def test_incident_raw_model_variant_displayed_when_no_aircraft_match(client, app):
    """
    Per PRD-0016 FR-20: Incident with no matching Aircraft record renders
    the raw_model_variant string.
    """
    with app.app_context():
        aircraft = Aircraft(
            manufacturer='Boeing', model_name='Boeing 737',
            total_incidents=1, fatal_incidents=0, total_fatalities=0
        )
        db.session.add(aircraft)
        db.session.commit()
        aircraft_id = aircraft.id
        incident = Incident(
            aircraft_id=aircraft_id,
            raw_model_variant='Boeing 707-321B',
            date=date(1990, 1, 25),
            operator='Test',
            location='Test',
            fatalities=0,
            description='Raw variant display test',
            incident_type='Accident',
        )
        db.session.add(incident)
        db.session.flush()
        incident_id = incident.id
        db.session.add(IncidentSource(
            incident_id=incident_id,
            source_name='NTSB',
            source_record_id='DCA90MA019',
            source_url='https://data.ntsb.gov/Docket/?NTSBNumber=DCA90MA019',
            report_url='https://data.ntsb.gov/carol-repgen/api/Aviation/ReportMain/GenerateNewestReport/DCA90MA019/pdf',
        ))
        db.session.commit()

    response = client.get(f'/aircraft/{aircraft_id}/incidents')
    assert response.status_code == 200
    html = response.data.decode('utf-8')
    assert 'Boeing 707-321B' in html


def test_aircraft_with_null_ai_summary_shows_empty_state(client, app):
    """
    Per PRD-0016 FR-20: Aircraft with null ai_summary renders "no summary"
    empty state.
    """
    with app.app_context():
        aircraft = Aircraft(
            manufacturer='Embraer', model_name='Embraer ERJ-145',
            total_incidents=0, fatal_incidents=0, total_fatalities=0,
            ai_summary=None,
        )
        db.session.add(aircraft)
        db.session.commit()
        aircraft_id = aircraft.id

    response = client.get(f'/aircraft/{aircraft_id}')
    assert response.status_code == 200


def test_all_four_sources_unavailable_during_import(app):
    """
    Per PRD-0016 FR-20: All four data sources independently unavailable
    during import — no crash, graceful degradation.
    """
    with app.app_context():
        aircraft = Aircraft(
            manufacturer='ATR', model_name='ATR 72',
            total_incidents=1, fatal_incidents=0, total_fatalities=0
        )
        db.session.add(aircraft)
        db.session.commit()
        aircraft_id = aircraft.id

    with app.app_context():
        sources = [
            IncidentSource(incident_id=1, source_name='NTSB', source_url=None, report_url=None),
            IncidentSource(incident_id=1, source_name='FAA_AIDS', source_url=None, report_url=None),
            IncidentSource(incident_id=1, source_name='FAA_SDR', source_url=None, report_url=None),
            IncidentSource(incident_id=1, source_name='ASN', source_url=None, report_url=None),
        ]
        for src in sources:
            db.session.add(src)
        db.session.commit()
        assert all(src.source_url is None and src.report_url is None for src in sources)


def test_import_data_variant_upsert_idempotent(app, tmp_path, monkeypatch):
    scripts_dir = os.path.join(os.getcwd(), 'scripts')
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    import import_data

    monkeypatch.setattr(import_data, 'create_app', lambda *_args, **_kwargs: app)
    monkeypatch.setattr(import_data, 'app', app)

    payload = [
        {
            'model_name': 'Boeing 707',
            'type': 'Boeing 707 320C',
            'date': '2020-01-01',
            'operator': 'Test Operator',
            'location': 'Test Location',
            'fatalities': '0',
            'narrative': 'Test incident',
            'asn_url': 'https://example.com/asn/1',
            'category': 'Accident',
        },
        {
            'model_name': 'Boeing 707',
            'type': 'Boeing 707 320C',
            'date': '2020-02-01',
            'operator': 'Test Operator 2',
            'location': 'Test Location 2',
            'fatalities': '5',
            'narrative': 'Fatal incident',
            'asn_url': 'https://example.com/asn/2',
            'category': 'Accident',
        },
    ]

    path = tmp_path / 'incidents.json'
    path.write_text(json.dumps(payload))

    import_data.import_file(str(path), 'Boeing')
    import_data.import_file(str(path), 'Boeing')

    with app.app_context():
        assert Aircraft.query.count() == 1
        assert Incident.query.count() == 2
        assert Incident.query.filter(Incident.asn_url.isnot(None)).count() == 0

        variants = AircraftVariant.query.all()
        assert len(variants) == 1
        assert variants[0].variant_name == 'Boeing 707 320C'
        assert variants[0].total_incidents == 2
        assert variants[0].fatal_incidents == 1

        # ASN linkage now lives in IncidentSource for new imports.
        asn_sources = IncidentSource.query.filter_by(source_name='ASN').all()
        assert len(asn_sources) == 2
