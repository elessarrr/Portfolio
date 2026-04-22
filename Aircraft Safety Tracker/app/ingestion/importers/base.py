import abc
import datetime
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple

from flask import current_app
from sqlalchemy import func

from app import db
from app.models import Aircraft, ImportLog, ImportState


def strip_duplicate_words(text: str) -> str:
    """
    Remove consecutive duplicate alphabetic words while preserving numbers.
    e.g., 'Boeing Boeing 717' -> 'Boeing 717'
    e.g., '700-700' -> '700-700'
    """
    if not text:
        return text

    # Use regex to find consecutive duplicate alphabetic words (case-insensitive)
    # \b([A-Za-z]+)\s+\1\b
    # We use a loop to handle multiple duplicates (e.g. "Boeing Boeing Boeing")
    prev_text = None
    while text != prev_text:
        prev_text = text
        text = re.sub(r'\b([A-Za-z]+)(?:\s+\1\b)+', r'\1', text, flags=re.IGNORECASE)

    return text


def normalize_make_model_for_comparison(text: str) -> str:
    """
    Normalize make/model text for resilient comparisons only.

    This function intentionally does not change what we persist to DB.
    We only normalize the incoming value used in lookup steps so common
    source formatting differences (extra spaces, underscore/hyphen drift,
    casing) do not create avoidable duplicate Aircraft rows.
    """
    normalized = (text or "").strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.replace(" - ", "-").replace("_", "-")
    return normalized.upper()


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

                    # Apply discrepancy flag if the dedupe logic found conflicts
                    # This check is performed after upsert to ensure the incident object is bound to the session
                    if 'discrepancy_details' in parsed:
                        # Find the incident that was just upserted/matched
                        source_record_id = parsed.get('source_record_id')
                        from app.models import IncidentSource
                        source = IncidentSource.query.filter_by(
                            source_name=self.source_name,
                            source_record_id=source_record_id
                        ).first()

                        if source and source.incident:
                            source.incident.has_discrepancy = True

                            # Merge new discrepancy details with existing ones
                            current_details = source.incident.discrepancy_details or {}
                            new_details = parsed['discrepancy_details']

                            # Use source name as key to track which source reported what
                            if self.source_name not in current_details:
                                current_details[self.source_name] = []

                            current_details[self.source_name].append(new_details)
                            source.incident.discrepancy_details = current_details

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
            db.session.rollback()
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
        record_date = parsed_record.get('date')
        if record_date and hasattr(record_date, 'year'):
            if record_date.year < 1985:
                return False
        return True

    def resolve_aircraft(self, parsed_record: Dict[str, Any]) -> Optional[int]:
        """
        Resolve an Aircraft ID from parsed_record["make_model"] with safe fallbacks:
        1) Exact match (case-insensitive) on normalized comparison string.
        2) Prefix match fallback (choose highest total_incidents if multiple).
        3) Boeing/Airbus auto-create as last resort.
        """
        make_model = parsed_record.get('make_model')
        if not make_model:
            return None

        make_model = strip_duplicate_words(make_model).strip()
        parsed_record['make_model'] = make_model
        normalized_make_model = normalize_make_model_for_comparison(make_model)

        # Step 1: exact case-insensitive match using normalized incoming value.
        aircraft = Aircraft.query.filter(
            func.upper(Aircraft.model_name) == normalized_make_model
        ).first()
        if aircraft:
            return aircraft.id

        # Step 2: prefix fallback before auto-create.
        # If multiple candidates exist, choose the most data-rich aircraft row.
        prefix_matches = (
            Aircraft.query
            .filter(func.upper(Aircraft.model_name).like(f"{normalized_make_model}%"))
            .order_by(Aircraft.total_incidents.desc(), Aircraft.id.asc())
            .all()
        )
        if len(prefix_matches) == 1:
            return prefix_matches[0].id
        if len(prefix_matches) > 1:
            return prefix_matches[0].id

        # Step 3/4 (existing behavior): auto-create only for Boeing/Airbus.
        lower_make_model = make_model.lower()
        manufacturer = None
        if lower_make_model.startswith('boeing'):
            manufacturer = 'Boeing'
        elif lower_make_model.startswith('airbus'):
            manufacturer = 'Airbus'

        if manufacturer:
            aircraft = Aircraft(
                manufacturer=manufacturer,
                model_name=make_model,
                total_incidents=0,
                fatal_incidents=0,
                total_fatalities=0
            )
            db.session.add(aircraft)
            db.session.flush()  # Flush to get the ID

            # Log the creation for backlog verification
            self._log_model_creation(aircraft)

            return aircraft.id

        return None

    def _log_model_creation(self, aircraft: Aircraft) -> None:
        try:
            log_path = os.path.join(current_app.root_path, '..', 'data', 'logs', 'model_verification.log')
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'a', encoding='utf-8') as f:
                log_entry = {
                    'timestamp': datetime.datetime.utcnow().isoformat() + "Z",
                    'event': 'model_auto_created',
                    'aircraft_id': aircraft.id,
                    'manufacturer': aircraft.manufacturer,
                    'model_name': aircraft.model_name,
                    'source': self.source_name
                }
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            current_app.logger.error(f"Failed to write model verification log: {e}")

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
