import abc
import datetime
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple

from flask import current_app

from app import db
from app.models import ImportLog, ImportState


@dataclass
class ImportStats:
    records_processed: int = 0
    duplicates_detected: int = 0
    duplicates_merged: int = 0
    errors_count: int = 0


class DataSourceImporter(abc.ABC):
    source_name: str = "UNKNOWN"

    def __init__(
        self,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
        incremental: bool = False,
        log_path: Optional[str] = None,
    ):
        self.start_date = start_date
        self.end_date = end_date
        self.incremental = incremental
        self.log_path = log_path
        self.stats = ImportStats()

    def run(self) -> Tuple[ImportLog, ImportStats]:
        started_at = datetime.datetime.utcnow()

        state = ImportState.query.filter_by(source_name=self.source_name).first()
        if not state:
            state = ImportState(source_name=self.source_name)
            db.session.add(state)

        if self.incremental and self.start_date is None and state.last_successful_at is not None:
            self.start_date = state.last_successful_at.date()

        state.last_attempted_at = started_at
        state.last_status = "running"
        state.updated_at = started_at
        db.session.commit()

        import_log = ImportLog(
            source_name=self.source_name,
            status="running",
            started_at=started_at,
            log_path=self.log_path,
            details={
                "incremental": bool(self.incremental),
                "start_date": self.start_date.isoformat() if self.start_date else None,
                "end_date": self.end_date.isoformat() if self.end_date else None,
            },
        )
        db.session.add(import_log)
        db.session.commit()

        self.append_log_line({
            "level": "INFO",
            "event": "import_started",
            "context": {
                "import_log_id": import_log.id,
                "incremental": bool(self.incremental),
                "start_date": self.start_date.isoformat() if self.start_date else None,
                "end_date": self.end_date.isoformat() if self.end_date else None,
            },
        })

        try:
            for raw_record in self.fetch():
                try:
                    parsed = self.parse(raw_record)
                    if parsed is None:
                        continue
                    if not self.validate(parsed):
                        self.stats.errors_count += 1
                        self.append_log_line({
                            "level": "WARN",
                            "event": "record_validation_failed",
                        })
                        continue
                    self.upsert(parsed)
                    self.stats.records_processed += 1
                except Exception:
                    self.stats.errors_count += 1
                    current_app.logger.exception("Importer record processing failed")
                    self.append_log_line({
                        "level": "ERROR",
                        "event": "record_processing_failed",
                    })

            import_log.status = "completed"
        except Exception:
            import_log.status = "failed"
            self.stats.errors_count += 1
            current_app.logger.exception("Importer run failed")
            self.append_log_line({
                "level": "ERROR",
                "event": "import_failed",
            })
        finally:
            finished_at = datetime.datetime.utcnow()
            import_log.finished_at = finished_at
            import_log.records_processed = self.stats.records_processed
            import_log.duplicates_detected = self.stats.duplicates_detected
            import_log.duplicates_merged = self.stats.duplicates_merged
            import_log.errors_count = self.stats.errors_count

            state.last_status = import_log.status
            state.last_import_log_id = import_log.id
            state.last_records_processed = self.stats.records_processed
            state.last_duplicates_detected = self.stats.duplicates_detected
            state.last_duplicates_merged = self.stats.duplicates_merged
            state.last_errors_count = self.stats.errors_count
            state.updated_at = finished_at
            if import_log.status == "completed":
                state.last_successful_at = finished_at
                state.last_error = None
            else:
                state.last_error = "import_failed"

            db.session.commit()

            self.append_log_line({
                "level": "INFO" if import_log.status == "completed" else "ERROR",
                "event": "import_finished",
                "context": {
                    "import_log_id": import_log.id,
                    "status": import_log.status,
                    "records_processed": self.stats.records_processed,
                    "duplicates_detected": self.stats.duplicates_detected,
                    "duplicates_merged": self.stats.duplicates_merged,
                    "errors_count": self.stats.errors_count,
                    "elapsed_seconds": (finished_at - started_at).total_seconds(),
                },
            })

        return import_log, self.stats

    @abc.abstractmethod
    def fetch(self) -> Iterable[Any]:
        raise NotImplementedError

    @abc.abstractmethod
    def parse(self, raw_record: Any) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def validate(self, parsed_record: Dict[str, Any]) -> bool:
        return True

    @abc.abstractmethod
    def upsert(self, parsed_record: Dict[str, Any]) -> None:
        raise NotImplementedError

    def build_default_log_path(self) -> str:
        os.makedirs("data/logs", exist_ok=True)
        stamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_source = "".join(ch if ch.isalnum() else "-" for ch in str(self.source_name)).strip("-")
        return os.path.join("data/logs", f"import_{stamp}_{safe_source}.log")

    def append_log_line(self, payload: Dict[str, Any]) -> None:
        if not self.log_path:
            self.log_path = self.build_default_log_path()
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        row = dict(payload)
        row.setdefault("timestamp", datetime.datetime.utcnow().isoformat() + "Z")
        row.setdefault("source", self.source_name)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")
