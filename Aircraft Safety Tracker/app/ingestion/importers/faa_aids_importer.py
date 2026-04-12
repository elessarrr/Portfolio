import datetime
from typing import Any, Dict, Optional

from app import db
from app.ingestion.canonical import attach_source_to_incident, apply_canonical_rules
from app.ingestion.dedupe import find_best_incident_match, record_dedupe_decision
from app.ingestion.importers.base import DataSourceImporter, strip_duplicate_words
from app.models import Incident, IncidentSource


class FAAAIDSImporter(DataSourceImporter):
    source_name = 'FAA_AIDS'

    def __init__(self, records=None, **kwargs):
        super().__init__(**kwargs)
        self._records = list(records or [])

    def fetch(self):
        return self._records

    def parse(self, raw_record: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(raw_record, dict):
            return None

        record_id = str(
            raw_record.get('c5') # Unique control number
            or raw_record.get('record_id')
            or raw_record.get('aids_id')
            or raw_record.get('event_id')
            or ''
        ).strip() or None

        date_value = raw_record.get('c9') or raw_record.get('date') or raw_record.get('event_date')
        parsed_date = self._parse_date(date_value)
        if not parsed_date:
            return None
            
        make = raw_record.get('c23') or ''
        model = raw_record.get('c24') or ''
        make_model = f"{make} {model}".strip() if make or model else raw_record.get('make_model')
        if make_model:
            make_model = strip_duplicate_words(make_model)
        
        city = raw_record.get('c14') or raw_record.get('city') or ''
        state = raw_record.get('c13') or raw_record.get('state') or ''
        location = f"{city}, {state}".strip(', ') if city or state else raw_record.get('location')

        return {
            'source_record_id': record_id,
            'date': parsed_date,
            'location': location or None,
            'operator': (raw_record.get('c120') or raw_record.get('operator') or raw_record.get('operator_name') or '').strip() or None,
            'registration': (raw_record.get('c203') or raw_record.get('registration') or raw_record.get('reg') or '').strip() or None,
            'fatalities': self._parse_int(raw_record.get('c76') or raw_record.get('fatalities') or raw_record.get('fatal')),
            'description': (raw_record.get('c119') or raw_record.get('narrative') or raw_record.get('description') or '').strip() or None,
            'make_model': make_model,
            'source_url': raw_record.get('source_url') or raw_record.get('url'),
            'source_data': dict(raw_record),
        }

    def validate(self, parsed_record: Dict[str, Any]) -> bool:
        if not parsed_record.get('date'):
            return False
        if not parsed_record.get('source_record_id') and not parsed_record.get('source_url'):
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
            attach_source_to_incident(
                incident_id=incident.id,
                source_name=self.source_name,
                source_record_id=source_record_id,
                source_url=parsed_record.get('source_url'),
                report_url=None,
                source_data=parsed_record.get('source_data') or {},
                confidence_level='Medium',
            )

            incident.operator = parsed_record.get('operator') or incident.operator
            incident.location = parsed_record.get('location') or incident.location
            incident.registration = parsed_record.get('registration') or incident.registration
            if parsed_record.get('fatalities') is not None:
                incident.fatalities = parsed_record.get('fatalities')
            incident.description = parsed_record.get('description') or incident.description
            db.session.commit()

            apply_canonical_rules(incident)
            return

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
                report_url=None,
                source_data=parsed_record.get('source_data') or {},
                confidence_level='Medium',
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

        incident = Incident(
            aircraft_id=self.resolve_aircraft(parsed_record),
            date=parsed_record['date'],
            operator=parsed_record.get('operator'),
            location=parsed_record.get('location'),
            fatalities=parsed_record.get('fatalities') or 0,
            description=parsed_record.get('description'),
            incident_type='Incident',
            registration=parsed_record.get('registration'),
        )
        db.session.add(incident)
        db.session.commit()

        attach_source_to_incident(
            incident_id=incident.id,
            source_name=self.source_name,
            source_record_id=source_record_id,
            source_url=parsed_record.get('source_url'),
            report_url=None,
            source_data=parsed_record.get('source_data') or {},
            confidence_level='Medium',
        )
        record_dedupe_decision(
            source_name=self.source_name,
            source_record_id=source_record_id,
            incoming_incident_id=incident.id,
            matched_incident_id=None,
            decision='created_new',
            rule=None,
            score=None,
            details={'reason': 'no_match'},
        )

    def _parse_date(self, value):
        if isinstance(value, datetime.date):
            return value
        if not value:
            return None
        text = str(value).strip()
        # Handle YYYYMMDD format from FAA TXT file (c9)
        if len(text) == 8 and text.isdigit():
            try:
                return datetime.datetime.strptime(text, '%Y%m%d').date()
            except Exception:
                pass
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
