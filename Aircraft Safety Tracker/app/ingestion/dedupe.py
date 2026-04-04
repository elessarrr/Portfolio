import datetime
import re
from difflib import SequenceMatcher
from typing import Any, Dict, Optional, Tuple

from app import db
from app.models import DedupeDecision, Incident


def find_best_incident_match(
    *,
    date: datetime.date,
    registration: Optional[str],
    location: Optional[str],
    operator: Optional[str],
    window_days: int = 1,
    min_score: float = 0.82,
) -> Tuple[Optional[Incident], Optional[str], float, Dict[str, Any]]:
    reg_norm = _normalize_text(registration)
    loc_norm = _normalize_text(location)
    op_norm = _normalize_text(operator)

    start = date - datetime.timedelta(days=window_days)
    end = date + datetime.timedelta(days=window_days)
    candidates = Incident.query.filter(Incident.date >= start, Incident.date <= end).all()

    best_incident: Optional[Incident] = None
    best_rule: Optional[str] = None
    best_score = 0.0
    best_details: Dict[str, Any] = {}

    for incident in candidates:
        score, rule, details = _score_match(
            date=date,
            reg_norm=reg_norm,
            loc_norm=loc_norm,
            op_norm=op_norm,
            incident=incident,
        )
        if score > best_score:
            best_incident = incident
            best_rule = rule
            best_score = score
            best_details = details

    if best_incident is None or best_score < min_score:
        return None, None, best_score, best_details

    return best_incident, best_rule, best_score, best_details


def record_dedupe_decision(
    *,
    source_name: str,
    source_record_id: Optional[str],
    incoming_incident_id: Optional[int],
    matched_incident_id: Optional[int],
    decision: str,
    rule: Optional[str],
    score: Optional[float],
    details: Optional[Dict[str, Any]] = None,
) -> DedupeDecision:
    row = DedupeDecision(
        source_name=source_name,
        source_record_id=source_record_id,
        incoming_incident_id=incoming_incident_id,
        matched_incident_id=matched_incident_id,
        decision=decision,
        rule=rule,
        score=score,
        details=details or {},
    )
    db.session.add(row)
    db.session.commit()
    return row


def _score_match(
    *,
    date: datetime.date,
    reg_norm: str,
    loc_norm: str,
    op_norm: str,
    incident: Incident,
) -> Tuple[float, str, Dict[str, Any]]:
    inc_reg = _normalize_text(getattr(incident, 'registration', None))
    inc_loc = _normalize_text(getattr(incident, 'location', None))
    inc_op = _normalize_text(getattr(incident, 'operator', None))

    day_delta = abs((incident.date - date).days) if incident.date else 999
    date_score = 1.0 if day_delta == 0 else (0.7 if day_delta == 1 else 0.0)

    reg_match = bool(reg_norm and inc_reg and reg_norm == inc_reg)
    reg_score = 1.0 if reg_match else 0.0

    loc_sim = _similarity(loc_norm, inc_loc)
    op_sim = _similarity(op_norm, inc_op)

    score = 0.0
    rule = 'none'

    if reg_score == 1.0 and date_score == 1.0:
        score = 1.0
        rule = 'exact_date_registration'
    else:
        score = (0.45 * date_score) + (0.35 * reg_score) + (0.15 * loc_sim) + (0.05 * op_sim)
        rule = 'fuzzy_date_registration_location'

    details = {
        'day_delta': day_delta,
        'date_score': date_score,
        'registration_match': reg_match,
        'location_similarity': loc_sim,
        'operator_similarity': op_sim,
    }
    return score, rule, details


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def _normalize_text(value: Optional[str]) -> str:
    if not value:
        return ''
    text = str(value).strip().lower()
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return ' '.join(text.split())

