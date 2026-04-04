from datetime import date

from app import db
from app.ingestion.importers.ntsb_importer import NTSBImporter
from app.models import Incident, IncidentSource


def test_ntsb_importer_creates_incident_and_source(app):
    with app.app_context():
        importer = NTSBImporter(records=[
            {
                'ntsb_id': 'ABC12FA000',
                'event_date': '2020-01-02',
                'location': 'Austin, TX',
                'operator': 'Test Operator',
                'fatalities': '2',
                'probable_cause': 'Loss of control',
                'url': 'https://example.com/case',
                'pdf_report_url': 'https://example.com/report.pdf',
            }
        ])
        importer.run()

        incident = Incident.query.first()
        assert incident is not None
        assert incident.date == date(2020, 1, 2)
        assert incident.location == 'Austin, TX'
        assert incident.fatalities == 2
        assert incident.description == 'Loss of control'

        source = IncidentSource.query.filter_by(source_name='NTSB', source_record_id='ABC12FA000').first()
        assert source is not None
        assert source.incident_id == incident.id
        assert source.confidence_level == 'High'
        assert source.report_url == 'https://example.com/report.pdf'


def test_ntsb_importer_upserts_by_source_record_id(app):
    with app.app_context():
        importer = NTSBImporter(records=[
            {
                'ntsb_id': 'ABC12FA000',
                'event_date': '2020-01-02',
                'location': 'Austin, TX',
                'operator': 'Op',
                'fatalities': '0',
                'probable_cause': 'Initial',
            }
        ])
        importer.run()

        importer = NTSBImporter(records=[
            {
                'ntsb_id': 'ABC12FA000',
                'event_date': '2020-01-02',
                'location': 'Austin, Texas',
                'fatalities': '1',
                'probable_cause': 'Updated',
            }
        ])
        importer.run()

        assert Incident.query.count() == 1
        incident = Incident.query.first()
        assert incident.location == 'Austin, Texas'
        assert incident.fatalities == 1
        assert incident.description == 'Updated'


def test_ntsb_importer_rejects_out_of_range_dates(app):
    with app.app_context():
        importer = NTSBImporter(records=[
            {
                'ntsb_id': 'ABC12FA000',
                'event_date': '1984-12-31',
                'location': 'X',
                'probable_cause': 'Old',
            },
            {
                'ntsb_id': 'ABC12FA001',
                'event_date': '2026-01-01',
                'location': 'Y',
                'probable_cause': 'Future',
            },
        ])
        importer.run()
        assert Incident.query.count() == 0
