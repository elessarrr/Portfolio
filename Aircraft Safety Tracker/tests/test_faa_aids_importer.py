from datetime import date

from app import db
from app.ingestion.importers.faa_aids_importer import FAAAIDSImporter
from app.models import DedupeDecision, Incident, IncidentSource


def test_faa_aids_importer_creates_incident_and_source(app):
    with app.app_context():
        importer = FAAAIDSImporter(records=[
            {
                'record_id': 'AIDS-1',
                'date': '2024-01-01',
                'reg': 'N12345',
                'location': 'Phoenix, AZ',
                'fatalities': '0',
                'narrative': 'Hard landing',
            }
        ])
        importer.run()

        incident = Incident.query.first()
        assert incident is not None
        assert incident.date == date(2024, 1, 1)
        assert incident.registration == 'N12345'
        assert incident.location == 'Phoenix, AZ'
        assert incident.description == 'Hard landing'

        source = IncidentSource.query.filter_by(source_name='FAA_AIDS', source_record_id='AIDS-1').first()
        assert source is not None
        assert source.confidence_level == 'Medium'


def test_faa_aids_importer_upserts_by_source_record_id(app):
    with app.app_context():
        importer = FAAAIDSImporter(records=[
            {
                'record_id': 'AIDS-1',
                'date': '2024-01-01',
                'location': 'A',
                'narrative': 'A',
            }
        ])
        importer.run()

        importer = FAAAIDSImporter(records=[
            {
                'record_id': 'AIDS-1',
                'date': '2024-01-01',
                'location': 'B',
                'narrative': 'B',
            }
        ])
        importer.run()

        assert Incident.query.count() == 1
        incident = Incident.query.first()
        assert incident.location == 'B'
        assert incident.description == 'B'


def test_faa_aids_importer_links_to_existing_ntsb_incident(app):
    with app.app_context():
        ntsb = Incident(
            date=date(2024, 1, 1),
            registration='N99999',
            location='Austin, TX',
            operator='Carrier',
            incident_type='Accident',
            description='NTSB authoritative',
            fatalities=2,
        )
        db.session.add(ntsb)
        db.session.commit()

        importer = FAAAIDSImporter(records=[
            {
                'record_id': 'AIDS-200',
                'date': '2024-01-01',
                'reg': 'N99999',
                'location': 'Austin, Texas',
                'operator': 'Carrier',
                'fatalities': '0',
                'narrative': 'FAA narrative',
            }
        ])
        importer.run()

        assert Incident.query.count() == 1
        source = IncidentSource.query.filter_by(source_name='FAA_AIDS', source_record_id='AIDS-200').first()
        assert source is not None
        assert source.incident_id == ntsb.id

        decision = DedupeDecision.query.filter_by(source_name='FAA_AIDS', source_record_id='AIDS-200').first()
        assert decision is not None
        assert decision.decision == 'linked_existing'
