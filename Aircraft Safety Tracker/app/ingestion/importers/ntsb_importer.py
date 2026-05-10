import datetime
from typing import Any, Dict, Optional

from flask import current_app

from app import db
from app.ingestion.canonical import apply_canonical_rules, attach_source_to_incident
from app.ingestion.dedupe import find_best_incident_match, record_dedupe_decision
from app.ingestion.importers.base import (
    DataSourceImporter,
    strip_duplicate_words,
    validate_source_url,
    validate_pdf_url,
)
from app.models import Incident, IncidentSource


class NTSBImporter(DataSourceImporter):
    source_name = 'NTSB'
    min_year = 1985
    max_year = 2025
    legacy_cutover_year = 2008

    @staticmethod
    def _is_boeing_airbus_make_model(make_model: Optional[str]) -> bool:
        value = (make_model or '').strip().lower()
        return value.startswith('boeing') or value.startswith('airbus')

    def __init__(self, records=None, **kwargs):
        super().__init__(**kwargs)
        self._records = list(records or [])

    def fetch(self):
        return self._records

    def parse(self, raw_record: Any) -> Optional[Dict[str, Any]]:
        """
        Parse an NTSB raw record into a normalized incident dict.

        Per PRD-0016 (FR-1, FR-5 to FR-9, FR-36):
        - Stores raw_model_variant from cm_acftmodel before any normalization.
        - Validates source_url (docket/details) via HEAD request.
        - Validates report_url (PDF) via GET + body check for JSON error payloads.
        - Always preserves a valid source_url even if report_url is invalidated.
        """
        if not isinstance(raw_record, dict):
            return None

        date_value = raw_record.get('cm_eventDate') or raw_record.get('event_date') or raw_record.get('date')
        parsed_date = self._parse_date(date_value)
        if not parsed_date:
            return None

        vehicles = raw_record.get('cm_vehicles', [])
        vehicle = vehicles[0] if vehicles else {}

        make = vehicle.get('make') or ''
        model = vehicle.get('model') or ''
        make_model = f"{make} {model}".strip() if make or model else raw_record.get('make_model')
        if make_model:
            make_model = strip_duplicate_words(make_model)

        registration = vehicle.get('registrationNumber') or raw_record.get('registration')
        operator = vehicle.get('operatorName') or raw_record.get('operator')

        fatalities = raw_record.get('cm_fatalInjuryCount')
        if fatalities is None:
            fatalities = self._parse_int(raw_record.get('fatalities'))

        location: Optional[str] = f"{raw_record.get('cm_city', '')}, {raw_record.get('cm_state', '')}".strip(', ')
        if not location:
            location = raw_record.get('location')

        ntsb_num = raw_record.get('cm_ntsbNum') or raw_record.get('ntsb_id') or raw_record.get('source_record_id')

        description = raw_record.get('analysisNarrative') or raw_record.get('factualNarrative') or raw_record.get('prelimNarrative') or raw_record.get('probable_cause') or raw_record.get('description')
        if description == '-':
            description = None

        source_url = None
        # Identifier-aware routing:
        # 1) explicit legacy ev_id -> legacy brief URL
        # 2) NTSB number -> docket URL
        # 3) CAROL fallback only for cutover-era and newer records
        ev_id = self._parse_int(raw_record.get('ev_id') or raw_record.get('cm_ev_id'))
        if ev_id is not None:
            candidate = f"https://www.ntsb.gov/Pages/brief.aspx?ev_id={ev_id}&key=0"
            is_valid, _, _ = validate_source_url(candidate)
            if is_valid:
                source_url = candidate

        if source_url is None and ntsb_num:
            candidate = f"https://data.ntsb.gov/Docket/?NTSBNumber={ntsb_num}"
            is_valid, _, _ = validate_source_url(candidate)
            if is_valid:
                source_url = candidate
            else:
                current_app.logger.warning(
                    "NTSB source_url failed validation, falling back",
                    extra={
                        "source_name": self.source_name,
                        "source_record_id": str(ntsb_num or '').strip() or None,
                        "candidate_url": candidate,
                    },
                )

        allow_carol_fallback = parsed_date.year >= self.legacy_cutover_year
        if source_url is None and allow_carol_fallback and raw_record.get('cm_mkey'):
            candidate = f"https://carol.ntsb.gov/investigations/detail/{raw_record.get('cm_mkey')}"
            is_valid, _, _ = validate_source_url(candidate)
            if is_valid:
                source_url = candidate

        if source_url is None and raw_record.get('source_url'):
            candidate = raw_record.get('source_url')
            is_valid, _, _ = validate_source_url(candidate)
            if is_valid:
                source_url = candidate

        report_url = None
        if raw_record.get('cm_reportNum') and ntsb_num:
            candidate = f"https://data.ntsb.gov/carol-repgen/api/Aviation/ReportMain/GenerateNewestReport/{ntsb_num}/pdf"
            is_valid, http_status, error_detail = validate_pdf_url(candidate)
            if is_valid:
                report_url = candidate
            else:
                current_app.logger.warning(
                    "NTSB report_url failed validation",
                    extra={
                        "source_name": self.source_name,
                        "source_record_id": str(ntsb_num or '').strip() or None,
                        "candidate_url": candidate,
                        "http_status": http_status,
                        "error_detail": error_detail,
                    },
                )
        elif raw_record.get('pdf_report_url'):
            is_valid, http_status, error_detail = validate_pdf_url(raw_record.get('pdf_report_url'))
            if is_valid:
                report_url = raw_record.get('pdf_report_url')
            else:
                current_app.logger.warning(
                    "NTSB pdf_report_url failed validation",
                    extra={
                        "source_name": self.source_name,
                        "source_record_id": str(ntsb_num or '').strip() or None,
                        "candidate_url": raw_record.get('pdf_report_url'),
                        "http_status": http_status,
                        "error_detail": error_detail,
                    },
                )

        raw_model_variant = (
            raw_record.get('cm_acftmodel')
            or raw_record.get('aircraft_model')
            or make_model
        )

        return {
            'source_record_id': str(ntsb_num or '').strip() or None,
            'date': parsed_date,
            'location': location or None,
            'operator': (operator or '').strip() or None,
            'registration': (registration or '').strip() or None,
            'fatalities': fatalities,
            'description': (description or '').strip() or None,
            'source_url': source_url,
            'report_url': report_url,
            'make_model': make_model,
            'raw_model_variant': raw_model_variant,
            'source_data': dict(raw_record),
        }

    def validate(self, parsed_record: Dict[str, Any]) -> bool:
        if not parsed_record.get('date'):
            return False
        if not parsed_record.get('source_record_id') and not parsed_record.get('source_url'):
            return False
        year = parsed_record['date'].year
        if year < self.min_year or year > self.max_year:
            return False
        return True

    def upsert(self, parsed_record: Dict[str, Any]) -> None:
        source_record_id = parsed_record.get('source_record_id')

        existing_source = None
        if source_record_id:
            existing_source = IncidentSource.query.filter_by(
                source_name=self.source_name,
                source_record_id=source_record_id,
            ).first()

        if existing_source:
            incident = existing_source.incident
        else:
            matched, rule, score, details = find_best_incident_match(
                date=parsed_record['date'],
                registration=parsed_record.get('registration'),
                location=parsed_record.get('location'),
                operator=parsed_record.get('operator'),
                fatalities=parsed_record.get('fatalities'),
            )

            if matched:
                attach_source_to_incident(
                    incident_id=matched.id,
                    source_name=self.source_name,
                    source_record_id=source_record_id,
                    source_url=parsed_record.get('source_url'),
                    report_url=parsed_record.get('report_url'),
                    source_data=parsed_record.get('source_data') or {},
                    confidence_level='High',
                )
                record_dedupe_decision(
                    source_name=self.source_name,
                    source_record_id=source_record_id,
                    incoming_incident_id=None,
                    matched_incident_id=matched.id,
                    decision='linked_existing',
                    rule=rule,
                    score=score,
                    details=details,
                )
                if 'discrepancy' in details:
                    parsed_record['discrepancy_details'] = details['discrepancy']
                apply_canonical_rules(matched)
                return

            raw_variant = parsed_record.get('raw_model_variant')
            aircraft_id = self.resolve_or_create_aircraft_variant(raw_variant) if raw_variant else None
            if aircraft_id is None and raw_variant:
                current_app.logger.warning(
                    "NTSB unresolved variant during upsert",
                    extra={
                        "source_name": self.source_name,
                        "source_record_id": source_record_id,
                        "raw_model_variant": raw_variant,
                    },
                )

            incident = Incident(
                aircraft_id=aircraft_id,
                raw_model_variant=raw_variant,
                date=parsed_record['date'],
                operator=parsed_record.get('operator'),
                location=parsed_record.get('location'),
                fatalities=parsed_record.get('fatalities') or 0,
                description=parsed_record.get('description'),
                incident_type='Accident',
                registration=parsed_record.get('registration'),
            )
            db.session.add(incident)
            db.session.flush()

            record_dedupe_decision(
                source_name=self.source_name,
                source_record_id=source_record_id,
                incoming_incident_id=incident.id,
                matched_incident_id=None,
                decision='created_new',
                rule=None,
                score=None,
                details={'reason': 'authoritative_source'},
            )

            attach_source_to_incident(
                incident_id=incident.id,
                source_name=self.source_name,
                source_record_id=source_record_id,
                source_url=parsed_record.get('source_url'),
                report_url=parsed_record.get('report_url'),
                source_data=parsed_record.get('source_data') or {},
                confidence_level='High',
            )

        incident.operator = parsed_record.get('operator') or incident.operator
        incident.location = parsed_record.get('location') or incident.location
        if parsed_record.get('fatalities') is not None:
            incident.fatalities = parsed_record.get('fatalities')
        incident.description = parsed_record.get('description') or incident.description
        incident.registration = parsed_record.get('registration') or incident.registration

        apply_canonical_rules(incident)

    def _parse_date(self, value):
        if isinstance(value, datetime.date):
            return value
        if not value:
            return None
        text = str(value).strip()
        # Handle ISO format like 1988-07-01T20:19:00Z
        if 'T' in text:
            text = text.split('T')[0]
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d'):
            try:
                return datetime.datetime.strptime(text, fmt).date()
            except Exception:
                continue
        return None

    def _parse_int(self, value):
        if value is None or value == '':
            return None
        try:
            return int(value)
        except Exception:
            return None
