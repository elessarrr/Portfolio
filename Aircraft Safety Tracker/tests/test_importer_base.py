import datetime

from app import db
from app.ingestion.importers.base import DataSourceImporter
from app.models import ImportLog, ImportState


class DummyImporter(DataSourceImporter):
    source_name = "DUMMY"

    def fetch(self):
        return [
            {"id": 1, "ok": True},
            {"id": 2, "ok": False},
            {"id": 3, "ok": True},
        ]

    def parse(self, raw_record):
        if raw_record["id"] == 2:
            raise RuntimeError("parse error")
        return {
            "external_id": str(raw_record["id"]),
            "date": datetime.date(2020, 1, 1),
        }

    def validate(self, parsed_record):
        return bool(parsed_record.get("external_id"))

    def upsert(self, parsed_record):
        return None


def test_importer_creates_import_log_and_stats(app):
    with app.app_context():
        importer = DummyImporter()
        import_log, stats = importer.run()

        db.session.refresh(import_log)
        assert import_log.status in {"completed", "failed"}
        assert import_log.source_name == "DUMMY"
        assert stats.records_processed == 2
        assert stats.errors_count == 1

        persisted = ImportLog.query.filter_by(id=import_log.id).first()
        assert persisted is not None
        assert persisted.records_processed == 2
        assert persisted.errors_count == 1


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
