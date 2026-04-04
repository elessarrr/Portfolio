import datetime
from app import create_app, db
from app.models import Incident, IncidentSource, Aircraft
from app.ingestion.importers.faa_aids_importer import FAAAIDSImporter

app = create_app()
with app.app_context():
    # Clean up before testing
    db.session.query(IncidentSource).filter_by(source_record_id='FAA-999').delete()
    db.session.query(Incident).filter_by(registration='N12345').delete()
    db.session.commit()

    # 1. Create an aircraft
    aircraft = Aircraft.query.filter_by(model_name='747-400').first()
    if not aircraft:
        aircraft = Aircraft(manufacturer='Boeing', model_name='747-400')
        db.session.add(aircraft)
        db.session.commit()
    
    # 2. Add an "ASN" incident
    incident = Incident(
        aircraft_id=aircraft.id,
        date=datetime.date(2020, 1, 1),
        registration='N12345',
        location='Test City',
        operator='Test Airlines',
        description='Test description ASN',
        incident_type='Accident'
    )
    db.session.add(incident)
    db.session.commit()
    
    # 3. Simulate FAAAIDSImporter processing the same incident
    faa_record = {
        'record_id': 'FAA-999',
        'date': '2020-01-01',
        'registration': 'N12345',
        'city': 'Test City',
        'operator': 'Test Airlines',
        'fatalities': 0,
        'narrative': 'Test description FAA',
        'url': 'http://faa.gov/test'
    }
    
    importer = FAAAIDSImporter(records=[faa_record])
    parsed = importer.parse(faa_record)
    if importer.validate(parsed):
        importer.upsert(parsed)
        
    # 4. Check if they merged
    incidents = Incident.query.filter_by(registration='N12345').all()
    print(f"Number of incidents after merge: {len(incidents)}")
    if len(incidents) == 1:
        sources = IncidentSource.query.filter_by(incident_id=incidents[0].id).all()
        print(f"Sources attached: {[s.source_name for s in sources]}")