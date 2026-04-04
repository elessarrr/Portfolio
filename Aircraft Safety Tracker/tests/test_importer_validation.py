from app.ingestion.importers.ntsb_importer import NTSBImporter
from app.models import Incident


def test_ntsb_importer_skips_records_missing_required_fields(app):
    with app.app_context():
        importer = NTSBImporter(records=[
            {},
            {'ntsb_id': 'ABC12FA000'},
            {'event_date': '2020-01-01'},
        ])
        importer.run()
        assert Incident.query.count() == 0

