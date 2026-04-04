from typing import Optional

from app import db
from app.models import Incident, IncidentSource


SOURCE_PRIORITY = {
    'NTSB': 100,
    'FAA_AIDS': 60,
    'FAA_SDR': 50,
    'ASN': 40,
}


def get_source_priority(source_name: Optional[str]) -> int:
    if not source_name:
        return 0
    return SOURCE_PRIORITY.get(source_name, 10)


def apply_canonical_rules(incident: Incident) -> None:
    sources = list(incident.sources.all())
    if not sources:
        return

    preferred = max(sources, key=lambda s: get_source_priority(s.source_name))
    data = preferred.source_data or {}

    if preferred.source_name == 'NTSB':
        incident.description = _coalesce(incident.description, data.get('probable_cause') or data.get('description'))
        incident.fatalities = _coalesce_int(incident.fatalities, data.get('fatalities'))
        incident.registration = _coalesce(incident.registration, data.get('registration') or data.get('reg'))
        incident.operator = _coalesce(incident.operator, data.get('operator'))
        incident.location = _coalesce(incident.location, data.get('location'))

    elif preferred.source_name in {'FAA_AIDS', 'FAA_SDR'}:
        incident.registration = _coalesce(incident.registration, data.get('registration') or data.get('reg'))
        incident.operator = _coalesce(incident.operator, data.get('operator'))
        incident.location = _coalesce(incident.location, data.get('location'))
        incident.description = _coalesce(incident.description, data.get('narrative') or data.get('description'))
        incident.fatalities = _coalesce_int(incident.fatalities, data.get('fatalities'))

    else:
        incident.description = _coalesce(incident.description, data.get('description'))

    db.session.commit()


def attach_source_to_incident(
    *,
    incident_id: int,
    source_name: str,
    source_record_id: Optional[str],
    source_url: Optional[str],
    report_url: Optional[str],
    source_data: dict,
    confidence_level: str,
) -> IncidentSource:
    existing = None
    if source_record_id:
        existing = IncidentSource.query.filter_by(source_name=source_name, source_record_id=source_record_id).first()
    if existing:
        if existing.incident_id != incident_id:
            existing.incident_id = incident_id
        existing.source_url = source_url or existing.source_url
        existing.report_url = report_url or existing.report_url
        existing.source_data = source_data or existing.source_data
        existing.confidence_level = confidence_level
        db.session.commit()
        return existing

    row = IncidentSource(
        incident_id=incident_id,
        source_name=source_name,
        source_record_id=source_record_id,
        source_url=source_url,
        report_url=report_url,
        source_data=source_data or {},
        confidence_level=confidence_level,
    )
    db.session.add(row)
    db.session.commit()
    return row


def _coalesce(current, candidate):
    if current:
        return current
    if candidate is None:
        return current
    text = str(candidate).strip()
    return text or current


def _coalesce_int(current, candidate):
    if current is not None and current != 0:
        return current
    if candidate is None or candidate == '':
        return current
    try:
        return int(candidate)
    except Exception:
        return current

