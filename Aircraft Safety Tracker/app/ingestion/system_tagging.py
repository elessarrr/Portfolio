from typing import Optional, Tuple

from app import db
from app.ingestion.normalization.jasc import normalize_jasc
import datetime

from app.models import JASCMapping, SystemTag, UnmappedJASC


def apply_jasc_mapping_to_incident(
    incident_id: int,
    jasc_code: Optional[str],
    *,
    tagged_by: str = 'FAA',
) -> Tuple[str, str]:
    normalized = normalize_jasc(jasc_code)
    if not normalized:
        system_name = 'Unknown System'
        confidence = 'Low'
    else:
        mapping = JASCMapping.query.filter_by(jasc_code=normalized).first()
        if mapping:
            system_name = mapping.system_name
            confidence = mapping.confidence or 'Medium'
        else:
            system_name = 'Unknown System'
            confidence = 'Low'
            now = datetime.datetime.utcnow()
            unmapped = UnmappedJASC.query.filter_by(source_name=tagged_by, jasc_code=normalized).first()
            if unmapped:
                unmapped.occurrences = (unmapped.occurrences or 0) + 1
                unmapped.last_seen_at = now
            else:
                db.session.add(UnmappedJASC(
                    source_name=tagged_by,
                    jasc_code=normalized,
                    occurrences=1,
                    first_seen_at=now,
                    last_seen_at=now,
                ))
            db.session.commit()

    existing = SystemTag.query.filter_by(
        incident_id=incident_id,
        system_name=system_name,
        tagged_by=tagged_by,
    ).first()
    if not existing:
        db.session.add(SystemTag(
            incident_id=incident_id,
            system_name=system_name,
            confidence=confidence,
            tagged_by=tagged_by,
        ))
        db.session.commit()

    return system_name, confidence
