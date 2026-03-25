import json
import os
import sys

from app import db
from app.models import Aircraft, AircraftVariant, Incident


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

        variants = AircraftVariant.query.all()
        assert len(variants) == 1
        assert variants[0].variant_name == 'Boeing 707 320C'
        assert variants[0].total_incidents == 2
        assert variants[0].fatal_incidents == 1
