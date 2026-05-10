import pytest
from app import create_app, db
from app.models import Aircraft, AircraftVariant, ImportLog, Incident, IncidentSource, JASCMapping, ReportAnalysis, Request, SystemTag
from datetime import date
from sqlalchemy.exc import IntegrityError

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_aircraft_creation(app):
    """Test that an aircraft can be created and retrieved."""
    a = Aircraft(manufacturer='Boeing', model_name='737-800', icao_code='B738', years_in_service=25)
    db.session.add(a)
    db.session.commit()

    retrieved = Aircraft.query.filter_by(model_name='737-800').first()
    assert retrieved is not None
    assert retrieved.manufacturer == 'Boeing'
    assert retrieved.icao_code == 'B738'

def test_incident_creation(app):
    """Test that an incident can be created and linked to an aircraft."""
    a = Aircraft(manufacturer='Airbus', model_name='A320', icao_code='A320', years_in_service=30)
    db.session.add(a)
    db.session.commit()

    i = Incident(aircraft_id=a.id, date=date(2023, 1, 15), operator='Test Air', 
                 location='New York', fatalities=0, description='Minor tail strike', incident_type='Accident')
    db.session.add(i)
    db.session.commit()

    retrieved_incident = Incident.query.first()
    assert retrieved_incident is not None
    assert retrieved_incident.operator == 'Test Air'
    assert retrieved_incident.aircraft.model_name == 'A320'

def test_request_creation(app):
    """Test that a user request can be logged."""
    r = Request(aircraft_model='Cessna 172', user_email='test@example.com')
    db.session.add(r)
    db.session.commit()

    retrieved_request = Request.query.first()
    assert retrieved_request is not None
    assert retrieved_request.aircraft_model == 'Cessna 172'
    assert retrieved_request.user_email == 'test@example.com'

def test_incident_source_creation(app):
    aircraft = Aircraft(manufacturer='Boeing', model_name='747-400', icao_code='B744', years_in_service=35)
    db.session.add(aircraft)
    db.session.commit()

    incident = Incident(
        aircraft_id=aircraft.id,
        date=date(2020, 5, 17),
        operator='Sample Airline',
        location='Tokyo',
        fatalities=2,
        description='Sample incident',
        incident_type='Accident'
    )
    db.session.add(incident)
    db.session.commit()

    source = IncidentSource(
        incident_id=incident.id,
        source_name='ASN',
        source_record_id='ASN-TEST-1',
        source_url='https://aviation-safety.net/sample',
        source_data={'phase_of_flight': 'landing'},
        confidence_level='Unverified',
    )
    db.session.add(source)
    db.session.commit()

    retrieved_source = IncidentSource.query.filter_by(source_name='ASN').first()
    assert retrieved_source is not None
    assert retrieved_source.incident_id == incident.id
    assert retrieved_source.source_url == 'https://aviation-safety.net/sample'


def test_incident_source_unique_source_record_id(app):
    aircraft = Aircraft(manufacturer='Boeing', model_name='767-300', icao_code='B763', years_in_service=40)
    db.session.add(aircraft)
    db.session.commit()

    incident_one = Incident(
        aircraft_id=aircraft.id,
        date=date(2020, 1, 1),
        operator='A',
        location='X',
        fatalities=0,
        description='A',
        incident_type='Incident'
    )
    incident_two = Incident(
        aircraft_id=aircraft.id,
        date=date(2020, 1, 2),
        operator='B',
        location='Y',
        fatalities=0,
        description='B',
        incident_type='Incident'
    )
    db.session.add_all([incident_one, incident_two])
    db.session.commit()

    db.session.add(IncidentSource(
        incident_id=incident_one.id,
        source_name='NTSB',
        source_record_id='NTSB-2020-0001',
        source_url='https://example.com/1',
        source_data={},
    ))
    db.session.commit()

    db.session.add(IncidentSource(
        incident_id=incident_two.id,
        source_name='NTSB',
        source_record_id='NTSB-2020-0001',
        source_url='https://example.com/2',
        source_data={},
    ))
    with pytest.raises(IntegrityError):
        db.session.commit()

def test_system_tag_creation(app):
    aircraft = Aircraft(manufacturer='Airbus', model_name='A321', icao_code='A321', years_in_service=28)
    db.session.add(aircraft)
    db.session.commit()

    incident = Incident(
        aircraft_id=aircraft.id,
        date=date(2021, 4, 2),
        operator='Sample Carrier',
        location='Paris',
        fatalities=0,
        description='Hydraulic caution',
        incident_type='Incident'
    )
    db.session.add(incident)
    db.session.commit()

    tag = SystemTag(
        incident_id=incident.id,
        system_name='Hydraulics',
        confidence='High',
        tagged_by='AI'
    )
    db.session.add(tag)
    db.session.commit()

    retrieved_tag = SystemTag.query.filter_by(system_name='Hydraulics').first()
    assert retrieved_tag is not None
    assert retrieved_tag.incident_id == incident.id
    assert retrieved_tag.confidence == 'High'
    assert retrieved_tag.tagged_by == 'AI'

def test_aircraft_variant_creation(app):
    aircraft = Aircraft(manufacturer='Boeing', model_name='737', icao_code='B737', years_in_service=58)
    db.session.add(aircraft)
    db.session.commit()

    variant = AircraftVariant(
        aircraft_id=aircraft.id,
        variant_name='737-800',
        years_in_service='1998-present',
        total_incidents=120,
        fatal_incidents=9
    )
    db.session.add(variant)
    db.session.commit()

    retrieved_variant = AircraftVariant.query.filter_by(variant_name='737-800').first()
    assert retrieved_variant is not None
    assert retrieved_variant.aircraft_id == aircraft.id
    assert retrieved_variant.total_incidents == 120
    assert retrieved_variant.fatal_incidents == 9

def test_report_analysis_creation(app):
    aircraft = Aircraft(manufacturer='Boeing', model_name='787-8', icao_code='B788', years_in_service=14)
    db.session.add(aircraft)
    db.session.commit()

    incident = Incident(
        aircraft_id=aircraft.id,
        date=date(2022, 9, 30),
        operator='Sample Airline',
        location='Doha',
        fatalities=0,
        description='Electrical smoke event',
        incident_type='Incident'
    )
    db.session.add(incident)
    db.session.commit()

    analysis = ReportAnalysis(
        incident_id=incident.id,
        report_url='https://example.com/report.pdf',
        root_cause='Electrical insulation breakdown',
        contributing_factors=['Moisture ingress', 'Aging harness'],
        findings='Localized thermal event in aft galley panel.',
        recommendations=['Inspect harness routing', 'Replace insulation type'],
        narrative_summary='An in-service event caused smoke detection and diversion.',
        analysis_confidence=0.84,
        ai_model='gemini-1.5-flash'
    )
    db.session.add(analysis)
    db.session.commit()

    retrieved_analysis = ReportAnalysis.query.filter_by(incident_id=incident.id).first()
    assert retrieved_analysis is not None
    assert retrieved_analysis.root_cause == 'Electrical insulation breakdown'
    assert retrieved_analysis.ai_model == 'gemini-1.5-flash'


def test_import_log_creation(app):
    log = ImportLog(
        source_name='ASN',
        status='completed',
        records_processed=123,
        duplicates_detected=4,
        duplicates_merged=3,
        errors_count=1,
        log_path='data/logs/import_20260329_120000.log',
        details={'elapsed_seconds': 12.3},
    )
    db.session.add(log)
    db.session.commit()

    retrieved = ImportLog.query.filter_by(source_name='ASN').first()
    assert retrieved is not None
    assert retrieved.status == 'completed'
    assert retrieved.records_processed == 123


def test_jasc_mapping_creation(app):
    mapping = JASCMapping(
        jasc_code='29-51-00',
        jasc_description='Hydraulic Power—Engine Driven Pump',
        system_name='Hydraulics',
        confidence='High',
    )
    db.session.add(mapping)
    db.session.commit()

    retrieved = JASCMapping.query.filter_by(jasc_code='29-51-00').first()
    assert retrieved is not None
    assert retrieved.system_name == 'Hydraulics'
