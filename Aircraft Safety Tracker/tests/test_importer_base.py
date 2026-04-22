import datetime
import json
import os

from app import db
from app.ingestion.importers.base import DataSourceImporter, strip_duplicate_words
from app.models import ImportLog, ImportState, Aircraft


class DummyImporter(DataSourceImporter):
    source_name = "DUMMY"

    def fetch(self):
        return [
            {"id": 1, "ok": True},
            {"id": 2, "ok": False},
            {"id": 3, "ok": True},
            {"id": 4, "ok": True, "make_model": "Boeing 737-800"},
            {"id": 5, "ok": True, "make_model": "Airbus Airbus A320-200"}
        ]

    def parse(self, raw_record):
        if raw_record["id"] == 2:
            raise RuntimeError("parse error")
        return {
            "external_id": str(raw_record["id"]),
            "date": datetime.date(2020, 1, 1),
            "make_model": raw_record.get("make_model")
        }

    def validate(self, parsed_record):
        return bool(parsed_record.get("external_id"))

    def upsert(self, parsed_record):
        # To test the aircraft auto-creation, we call resolve_aircraft here
        # similar to how actual importers do it.
        aircraft_id = self.resolve_aircraft(parsed_record)
        parsed_record['resolved_aircraft_id'] = aircraft_id
        return None


def test_strip_duplicate_words():
    assert strip_duplicate_words("Boeing Boeing 717") == "Boeing 717"
    assert strip_duplicate_words("Airbus AIRBUS A320") == "Airbus A320"
    assert strip_duplicate_words("700-700") == "700-700"
    assert strip_duplicate_words("Boeing Boeing Boeing 737") == "Boeing 737"


def test_importer_creates_import_log_and_stats(app):
    with app.app_context():
        importer = DummyImporter()
        import_log, stats = importer.run()

        db.session.refresh(import_log)
        assert import_log.status in {"completed", "failed"}
        assert import_log.source_name == "DUMMY"
        assert stats.records_processed == 4
        assert stats.errors_count == 1

        persisted = ImportLog.query.filter_by(id=import_log.id).first()
        assert persisted is not None
        assert persisted.records_processed == 4
        assert persisted.errors_count == 1


def test_importer_auto_creates_aircraft(app):
    with app.app_context():
        # Start with an empty Aircraft table
        assert Aircraft.query.count() == 0

        importer = DummyImporter()
        importer.run()

        # Two aircraft should be created
        aircrafts = Aircraft.query.all()
        assert len(aircrafts) == 2

        boeing = Aircraft.query.filter_by(model_name="Boeing 737-800").first()
        assert boeing is not None
        assert boeing.manufacturer == "Boeing"

        airbus = Aircraft.query.filter_by(model_name="Airbus A320-200").first()
        assert airbus is not None
        assert airbus.manufacturer == "Airbus"

        # Check that the verification log was written
        log_path = os.path.join(app.root_path, '..', 'data', 'logs', 'model_verification.log')
        assert os.path.exists(log_path)
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) >= 2
            data1 = json.loads(lines[-2])
            data2 = json.loads(lines[-1])
            assert data1['event'] == 'model_auto_created'
            assert data1['model_name'] == 'Boeing 737-800'
            assert data2['event'] == 'model_auto_created'
            assert data2['model_name'] == 'Airbus A320-200'


def test_importer_updates_import_state(app):
    with app.app_context():
        importer = DummyImporter()
        import_log, stats = importer.run()

        state = ImportState.query.filter_by(source_name='DUMMY').first()
        assert state is not None
        assert state.last_attempted_at is not None
        assert state.last_import_log_id == import_log.id
        assert state.last_records_processed == stats.records_processed
        assert state.last_errors_count == stats.errors_count


def test_importer_writes_log_file(app, tmp_path):
    with app.app_context():
        log_path = tmp_path / 'import_test.log'
        importer = DummyImporter(log_path=str(log_path))
        importer.run()

        content = log_path.read_text(encoding='utf-8')
        assert '"event": "import_started"' in content
        assert '"event": "import_finished"' in content


def test_resolve_aircraft_exact_match_case_insensitive(app):
    with app.app_context():
        existing = Aircraft(
            manufacturer="Boeing",
            model_name="Boeing 737-800",
            total_incidents=10,
            fatal_incidents=1,
            total_fatalities=5,
        )
        db.session.add(existing)
        db.session.commit()

        importer = DummyImporter()
        aircraft_id = importer.resolve_aircraft({"make_model": "boeing 737-800"})
        assert aircraft_id == existing.id
        assert Aircraft.query.count() == 1


def test_resolve_aircraft_prefix_fallback_uses_existing_model(app):
    with app.app_context():
        existing = Aircraft(
            manufacturer="Boeing",
            model_name="Boeing 737-800",
            total_incidents=42,
            fatal_incidents=2,
            total_fatalities=12,
        )
        db.session.add(existing)
        db.session.commit()

        importer = DummyImporter()
        aircraft_id = importer.resolve_aircraft({"make_model": "BOEING 737"})
        assert aircraft_id == existing.id
        assert Aircraft.query.count() == 1


def test_resolve_aircraft_normalizes_spacing_for_matching(app):
    with app.app_context():
        existing = Aircraft(
            manufacturer="Boeing",
            model_name="Boeing 737-800",
            total_incidents=7,
            fatal_incidents=0,
            total_fatalities=0,
        )
        db.session.add(existing)
        db.session.commit()

        importer = DummyImporter()
        # Double spaces should normalize for lookup and still resolve existing row.
        aircraft_id = importer.resolve_aircraft({"make_model": "BOEING  737-800"})
        assert aircraft_id == existing.id
        assert Aircraft.query.count() == 1


def test_resolve_aircraft_auto_creates_boeing_when_missing(app):
    with app.app_context():
        assert Aircraft.query.count() == 0

        importer = DummyImporter()
        aircraft_id = importer.resolve_aircraft({"make_model": "BOEING 999"})
        assert aircraft_id is not None

        created = db.session.get(Aircraft, aircraft_id)
        assert created is not None
        assert created.manufacturer == "Boeing"
        assert created.model_name == "BOEING 999"
        assert Aircraft.query.count() == 1


def test_resolve_aircraft_returns_none_for_non_target_manufacturer(app):
    with app.app_context():
        importer = DummyImporter()
        aircraft_id = importer.resolve_aircraft({"make_model": "CESSNA 172"})
        assert aircraft_id is None
        assert Aircraft.query.count() == 0


def test_resolve_aircraft_auto_create_is_idempotent(app):
    with app.app_context():
        importer = DummyImporter()

        first_id = importer.resolve_aircraft({"make_model": "BOEING 999"})
        second_id = importer.resolve_aircraft({"make_model": "BOEING 999"})

        assert first_id is not None
        assert second_id == first_id
        assert Aircraft.query.filter_by(model_name="BOEING 999").count() == 1
