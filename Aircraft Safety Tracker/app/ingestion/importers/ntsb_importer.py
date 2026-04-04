import datetime
from typing import Any, Dict, Optional

from app import db
from app.ingestion.canonical import attach_source_to_incident, apply_canonical_rules
from app.ingestion.dedupe import record_dedupe_decision
from app.ingestion.importers.base import DataSourceImporter
from app.models import Incident, IncidentSource


class NTSBImporter(DataSourceImporter):
    source_name = 'NTSB'
    min_year = 1985
    max_year = 2025

    def __init__(self, records=None, **kwargs):
        super().__init__(**kwargs)
        self._records = list(records or [])

    def fetch(self):
        return self._records

    def parse(self, raw_record: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(raw_record, dict):
            return None

        date_value = raw_record.get('event_date') or raw_record.get('date')
        parsed_date = self._parse_date(date_value)
        if not parsed_date:
            return None

        return {
            'source_record_id': str(raw_record.get('ntsb_id') or raw_record.get('source_record_id') or '').strip() or None,
            'date': parsed_date,
            'location': (raw_record.get('location') or '').strip() or None,
            'operator': (raw_record.get('operator') or '').strip() or None,
            'registration': (raw_record.get('registration') or '').strip() or None,
            'fatalities': self._parse_int(raw_record.get('fatalities')),
            'description': (raw_record.get('probable_cause') or raw_record.get('description') or '').strip() or None,
            'source_url': raw_record.get('source_url') or raw_record.get('url'),
            'report_url': raw_record.get('pdf_report_url') or raw_record.get('report_url'),
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
            incident = Incident(
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
