import abc
import datetime
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple

import httpx
from flask import current_app
from sqlalchemy import func

from app import db
from app.models import Aircraft, ImportLog, ImportState


MANUFACTURER_ALLOWLIST = frozenset({
    'Boeing', 'Airbus', 'Cessna', 'Lockheed', 'Douglas', 'Beechcraft',
    'Bombardier', 'Embraer', 'ATR', 'Saab', 'Ilyushin', 'Antonov',
    'Fokker', 'Dassault', 'Gulfstream', 'Learjet', 'Piper', 'Cirrus', 'Diamond',
})

BOEING_BASE_MODEL_PATTERN = re.compile(r"^\d{3}[A-Za-z0-9\-]*$")
AIRBUS_BASE_MODEL_PATTERN = re.compile(r"^A\d{3}[A-Za-z0-9\-]*$")
MODEL_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-\/]*$")


def validate_series_model_name(make_model: str) -> Tuple[bool, str]:
    """
    Validate make/model format before persistence to keep series data clean.

    Rules:
    - Must be "<Manufacturer> <Model...>" (at least two tokens).
    - Manufacturer must be in MANUFACTURER_ALLOWLIST.
    - Model part must contain at least one digit.
    - Each model token must use safe alphanumeric/hyphen/slash characters.
    - Boeing and Airbus must match stricter base token patterns.
    """
    normalized = normalize_make_model_for_storage(make_model)
    parts = normalized.split(None, 1)
    if len(parts) < 2:
        return False, "missing_model_part"

    manufacturer, model_part = parts[0], parts[1].strip()
    if manufacturer not in MANUFACTURER_ALLOWLIST:
        return False, "manufacturer_not_allowed"
    if not model_part:
        return False, "empty_model_part"
    if not any(ch.isdigit() for ch in model_part):
        return False, "model_missing_numeric_token"

    model_tokens = model_part.split()
    if any(MODEL_TOKEN_PATTERN.fullmatch(token) is None for token in model_tokens):
        return False, "model_contains_invalid_characters"

    first_token = model_tokens[0]
    if manufacturer == "Boeing" and BOEING_BASE_MODEL_PATTERN.fullmatch(first_token) is None:
        return False, "boeing_model_pattern_mismatch"
    if manufacturer == "Airbus" and AIRBUS_BASE_MODEL_PATTERN.fullmatch(first_token) is None:
        return False, "airbus_model_pattern_mismatch"

    return True, "ok"


def validate_source_url(url: Optional[str], timeout: float = 10.0) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Validate that a source/docket URL is reachable and contains actual content.

    Used at ingestion time (FR-5) to ensure only valid URLs are stored. The
    caller decides what to store based on the returned tuple.

    For NTSB docket URLs (data.ntsb.gov/Docket/), performs GET + body inspection
    to detect "has not been released" messages that indicate permanently unavailable
    dockets (common for WA-coded international cases).

    Args:
        url: The URL to validate. May be None.
        timeout: Maximum seconds to wait before treating as unreachable.

    Returns:
        (is_valid, http_status, error_detail):
            - (True, status, None) if URL returns 2xx and contains actual content.
            - (False, status, reason) if URL returns 4xx/5xx, contains "not released" message, or request fails.
    """
    if not url:
        return False, None, "url_is_none"
    
    # Special handling for NTSB docket URLs - requires GET + body inspection
    # to detect "has not been released" messages for WA-coded international cases
    if url and "data.ntsb.gov/Docket/" in url:
        try:
            client = httpx.Client(timeout=timeout, follow_redirects=True)
            try:
                response = client.get(url)
                if response.status_code >= 400:
                    return False, response.status_code, f"http_{response.status_code}"
                
                # Check for "has not been released" message in WA-coded international cases
                response_text = response.text
                if "has not been released" in response_text:
                    return False, response.status_code, "docket_not_released"
                
                # Valid docket content
                return True, response.status_code, None
            finally:
                client.close()
        except httpx.TimeoutException:
            return False, None, "timeout"
        except httpx.TransportError as exc:
            return False, None, f"transport_error:{exc.__class__.__name__}"
        except Exception as exc:
            return False, None, f"unexpected:{exc.__class__.__name__}"
    
    # Standard HEAD-based validation for all other URLs
    try:
        client = httpx.Client(timeout=timeout, follow_redirects=True)
        try:
            response = client.head(url)
            if 200 <= response.status_code < 300:
                return True, response.status_code, None
            return False, response.status_code, f"http_{response.status_code}"
        finally:
            client.close()
    except httpx.TimeoutException:
        return False, None, "timeout"
    except httpx.TransportError as exc:
        return False, None, f"transport_error:{exc.__class__.__name__}"
    except Exception as exc:
        return False, None, f"unexpected:{exc.__class__.__name__}"


def validate_pdf_url(url: Optional[str], timeout: float = 10.0) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Validate that a PDF/report URL returns a real PDF (not an error payload).

    Per FR-8, NTSB PDF API can return HTTP 200 with a JSON error body like
    `{"Error": "The case with MKey 0 does not exist."}`. A HEAD-only check
    cannot detect this, so this function issues a GET and inspects the body.

    Args:
        url: The PDF URL to validate. May be None.
        timeout: Maximum seconds to wait before treating as unreachable.

    Returns:
        (is_valid, http_status, error_detail):
            - (True, status, None) if response is a real PDF (non-JSON or valid JSON array/object without "Error" key).
            - (False, status, detail) if JSON error payload detected or request fails.
    """
    if not url:
        return False, None, "url_is_none"
    try:
        client = httpx.Client(timeout=timeout, follow_redirects=True)
        try:
            response = client.get(url)
            if response.status_code >= 400:
                return False, response.status_code, f"http_{response.status_code}"
            content_type = response.headers.get('content-type', '').lower()
            text = response.text.strip()
            if 'application/json' in content_type or text.startswith('{') or text.startswith('['):
                try:
                    body = json.loads(text)
                    if isinstance(body, dict) and 'Error' in body:
                        return False, response.status_code, body.get('Error') or "json_error_payload"
                    if isinstance(body, dict) and body.get('ErrorCode') == 0:
                        return False, response.status_code, "mkey_0_error"
                except json.JSONDecodeError:
                    pass
            return True, response.status_code, None
        finally:
            client.close()
    except httpx.TimeoutException:
        return False, None, "timeout"
    except httpx.TransportError as exc:
        return False, None, f"transport_error:{exc.__class__.__name__}"
    except Exception as exc:
        return False, None, f"unexpected:{exc.__class__.__name__}"


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


def normalize_make_model_for_storage(text: str) -> str:
    """
    Normalize make/model text for persistence in title case.

    This keeps capitalization consistent for newly ingested records while
    preserving existing comparison behavior in normalize_make_model_for_comparison.
    """
    normalized = (text or "").strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.title()


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
        make_model = normalize_make_model_for_storage(make_model)
        parsed_record['make_model'] = make_model
        is_valid_model, validation_reason = validate_series_model_name(make_model)
        if not is_valid_model:
            parsed_record['make_model_validation_error'] = validation_reason
            current_app.logger.warning(
                "resolve_aircraft: rejecting invalid make_model",
                extra={"make_model": make_model, "reason": validation_reason},
            )
            return None

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

    def resolve_or_create_aircraft_variant(self, raw_variant: str) -> Optional[int]:
        """
        Resolve an Aircraft ID from a raw NTSB model variant string with
        precision-aware auto-creation.

        Extends resolve_aircraft() with an additional step that creates a new
        Aircraft record when a parent exists but no exact or prefix match does.
        This satisfies FR-2, FR-31 to FR-34 from PRD-0016.

        Resolution steps:
        1. Exact match (case-insensitive normalized).
        2. Prefix fallback (pick most-incident-rich match).
        3. Auto-create if parent exists, precision >= 2 chars, manufacturer in allowlist.
        4. Unknown manufacturer: return None, store raw string for later resolution.

        Args:
            raw_variant: Raw model string from NTSB payload (e.g., "Boeing 707-321B").

        Returns:
            Aircraft ID if resolved or auto-created; None if manufacturer unknown.
        """
        if not raw_variant:
            return None

        stripped_variant = strip_duplicate_words(raw_variant).strip()
        stripped_variant = normalize_make_model_for_storage(stripped_variant)
        is_valid_variant, validation_reason = validate_series_model_name(stripped_variant)
        if not is_valid_variant:
            current_app.logger.warning(
                "resolve_or_create_aircraft_variant: rejecting invalid raw_variant",
                extra={"raw_variant": raw_variant, "reason": validation_reason},
            )
            return None

        normalized_variant = normalize_make_model_for_comparison(stripped_variant)

        # Step 1: exact match
        exact = Aircraft.query.filter(
            func.upper(Aircraft.model_name) == normalized_variant
        ).first()
        if exact:
            return exact.id

        # Step 2: prefix fallback
        prefix_matches = (
            Aircraft.query
            .filter(func.upper(Aircraft.model_name).like(f"{normalized_variant}%"))
            .order_by(Aircraft.total_incidents.desc(), Aircraft.id.asc())
            .all()
        )
        if len(prefix_matches) == 1:
            return prefix_matches[0].id
        if len(prefix_matches) > 1:
            return prefix_matches[0].id

        # Step 3: auto-create when parent exists and constraints satisfied.
        # Parse manufacturer prefix to identify the potential parent.
        manufacturer, model_part = self._extract_manufacturer_and_model(stripped_variant)
        if manufacturer is None:
            current_app.logger.warning(
                "resolve_or_create_aircraft_variant: unknown manufacturer, returning None",
                extra={"raw_variant": raw_variant},
            )
            return None

        if manufacturer not in MANUFACTURER_ALLOWLIST:
            current_app.logger.warning(
                "resolve_or_create_aircraft_variant: manufacturer not in allowlist, returning None",
                extra={"raw_variant": raw_variant, "manufacturer": manufacturer},
            )
            return None

        # Find parent aircraft record (e.g., "Boeing 707" as parent of "Boeing 707-321B").
        # The parent is identified by the base model (first hyphen-separated part).
        parent_model_name = self._find_parent_model(manufacturer, stripped_variant)
        parent = None
        if parent_model_name:
            parent = Aircraft.query.filter(
                func.upper(Aircraft.model_name) == parent_model_name.upper()
            ).first()

        if parent is None:
            current_app.logger.warning(
                "resolve_or_create_aircraft_variant: no parent aircraft found, returning None",
                extra={"raw_variant": raw_variant, "manufacturer": manufacturer},
            )
            return None

        # Check precision: variant must differ meaningfully from parent.
        # E.g., "321B" has enough precision; "" or "Base" does not.
        if model_part and len(model_part) >= 2:
            aircraft = Aircraft(
                manufacturer=manufacturer,
                model_name=stripped_variant,
                total_incidents=0,
                fatal_incidents=0,
                total_fatalities=0
            )
            db.session.add(aircraft)
            db.session.flush()

            self._log_model_creation(aircraft)
            return aircraft.id

        current_app.logger.warning(
            "resolve_or_create_aircraft_variant: variant precision too low, returning None",
            extra={"raw_variant": raw_variant, "model_part": model_part},
        )
        return None

    def _extract_manufacturer_and_model(self, model_string: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract manufacturer prefix and model part from a model string.

        E.g., "Boeing 707-321B" → ("Boeing", "707-321B")
              "Airbus A320-200"  → ("Airbus", "A320-200")
              "Unknown Model"    → (None, None)
        """
        if not model_string:
            return None, None
        parts = model_string.split(None, 1)
        if len(parts) < 2:
            return None, None
        return parts[0], parts[1]

    def _find_parent_model(self, manufacturer: str, model_string: str) -> Optional[str]:
        """
        Find the parent Aircraft model name given a variant string.

        E.g., "Boeing 707-321B" → "Boeing 707"
              "Airbus A320-200"  → "Airbus A320"
              "Boeing 707"       → None (already a base model)

        The parent is determined by splitting on the first hyphen in the
        numeric/model part. If no hyphen exists, the model has no parent.
        """
        parts = model_string.split(None, 1)
        if len(parts) < 2:
            return None
        model_part = parts[1]
        hyphen_idx = model_part.find('-')
        if hyphen_idx == -1:
            return None
        base_model_part = model_part[:hyphen_idx]
        return f"{manufacturer} {base_model_part}"

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
