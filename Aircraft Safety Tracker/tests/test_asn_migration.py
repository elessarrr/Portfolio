from datetime import date
import importlib.util
from pathlib import Path

from app import db
from app.models import Incident, IncidentSource


_MIGRATION_PATH = Path(__file__).resolve().parents[1] / "scripts" / "migrate_asn_to_incident_source.py"
_MIGRATION_SPEC = importlib.util.spec_from_file_location("migrate_asn_to_incident_source", _MIGRATION_PATH)
_MIGRATION_MODULE = importlib.util.module_from_spec(_MIGRATION_SPEC)
assert _MIGRATION_SPEC and _MIGRATION_SPEC.loader
_MIGRATION_SPEC.loader.exec_module(_MIGRATION_MODULE)

migrate_asn_incident_sources = _MIGRATION_MODULE.migrate_asn_incident_sources

_IMPORT_DATA_PATH = Path(__file__).resolve().parents[1] / "scripts" / "import_data.py"
_IMPORT_DATA_SPEC = importlib.util.spec_from_file_location("import_data", _IMPORT_DATA_PATH)
_IMPORT_DATA_MODULE = importlib.util.module_from_spec(_IMPORT_DATA_SPEC)
assert _IMPORT_DATA_SPEC and _IMPORT_DATA_SPEC.loader
_IMPORT_DATA_SPEC.loader.exec_module(_IMPORT_DATA_MODULE)

upsert_asn_incident_source = _IMPORT_DATA_MODULE.upsert_asn_incident_source


def test_asn_migration_creates_incident_source_and_is_idempotent(app):
    with app.app_context():
        incident = Incident(
            aircraft_id=None,
            date=date(2024, 1, 1),
            operator="ASN Migration Airline",
            location="Test Location",
            fatalities=0,
            description="ASN migration test",
            asn_url="https://asn.example.com/record/123",
            incident_type="Accident",
        )
        db.session.add(incident)
        db.session.commit()

        first = migrate_asn_incident_sources(batch_size=10, dry_run=False)
        created_source = IncidentSource.query.filter_by(
            incident_id=incident.id,
            source_name="ASN",
        ).first()

        assert created_source is not None
        assert created_source.source_record_id == incident.asn_url
        assert first["total_created"] == 1

        second = migrate_asn_incident_sources(batch_size=10, dry_run=False)
        assert second["total_created"] == 0
        assert IncidentSource.query.filter_by(incident_id=incident.id, source_name="ASN").count() == 1


def test_import_data_asn_upsert_path_creates_and_reuses_source(app):
    with app.app_context():
        incident = Incident(
            aircraft_id=None,
            date=date(2024, 2, 1),
            operator="ASN Upsert Airline",
            location="Upsert City",
            fatalities=0,
            description="ASN import path test",
            asn_url="https://asn.example.com/record/456",
            incident_type="Incident",
        )
        db.session.add(incident)
        db.session.commit()

        upsert_asn_incident_source(incident.id, incident.asn_url)
        db.session.commit()

        source = IncidentSource.query.filter_by(
            source_name="ASN",
            source_record_id=incident.asn_url,
        ).first()
        assert source is not None
        assert source.incident_id == incident.id

        # Re-run to verify upsert semantics (no duplicate rows).
        upsert_asn_incident_source(incident.id, incident.asn_url)
        db.session.commit()
        assert IncidentSource.query.filter_by(source_name="ASN", source_record_id=incident.asn_url).count() == 1


def test_asn_migration_skips_duplicate_asn_urls_safely(app):
    with app.app_context():
        duplicate_url = "https://asn.example.com/record/dup-1"
        incident_one = Incident(
            aircraft_id=None,
            date=date(2024, 3, 1),
            operator="ASN Dup Airline 1",
            location="Dup City 1",
            fatalities=0,
            description="ASN duplicate URL test 1",
            asn_url=duplicate_url,
            incident_type="Accident",
        )
        incident_two = Incident(
            aircraft_id=None,
            date=date(2024, 3, 2),
            operator="ASN Dup Airline 2",
            location="Dup City 2",
            fatalities=0,
            description="ASN duplicate URL test 2",
            asn_url=duplicate_url,
            incident_type="Incident",
        )
        db.session.add(incident_one)
        db.session.add(incident_two)
        db.session.commit()

        summary = migrate_asn_incident_sources(batch_size=10, dry_run=False)

        assert summary["total_created"] == 1
        assert summary["total_skipped_duplicate_source_record_id"] == 1
        assert IncidentSource.query.filter_by(
            source_name="ASN",
            source_record_id=duplicate_url,
        ).count() == 1
