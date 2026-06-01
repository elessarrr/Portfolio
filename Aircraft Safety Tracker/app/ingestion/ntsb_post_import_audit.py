"""Post-import safety audit for NTSB bulk import (FR-22)."""

from __future__ import annotations

import re
from dataclasses import asdict
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.ingestion.dedupe.ntsb_asn import _norm_text, score_ntsb_vs_asn
from app.ingestion.link_schema import is_catalog_url, is_placeholder_url
from app.models import Aircraft, Incident, IncidentSource


def _candidate_asn_incidents(
    aircraft_id: int, ntsb_date: date, window_days: int
) -> List[Incident]:
    lo = ntsb_date.fromordinal(ntsb_date.toordinal() - window_days)
    hi = ntsb_date.fromordinal(ntsb_date.toordinal() + window_days)
    return (
        Incident.query.filter(
            Incident.aircraft_id == aircraft_id,
            Incident.asn_url.isnot(None),
            Incident.date >= lo,
            Incident.date <= hi,
        )
        .order_by(Incident.date.asc())
        .all()
    )


def audit_ntsb_vs_asn_duplicates(
    *,
    window_days: int = 7,
    max_issues: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """NTSB-only incidents that score ASN-covered vs another incident on the same page."""
    issues: List[Dict[str, Any]] = []
    sources = (
        IncidentSource.query.filter_by(source_name="NTSB", is_active=True)
        .order_by(IncidentSource.source_record_id.asc())
        .all()
    )

    for source in sources:
        incident = source.incident
        if incident is None:
            continue

        for asn_inc in _candidate_asn_incidents(
            incident.aircraft_id, incident.date, window_days
        ):
            if asn_inc.id == incident.id:
                continue
            decision = score_ntsb_vs_asn(
                ntsb_date=incident.date,
                asn_date=asn_inc.date,
                ntsb_operator=incident.operator,
                asn_operator=asn_inc.operator,
                ntsb_location=incident.location,
                asn_location=asn_inc.location,
                ntsb_fatalities=incident.fatalities,
                asn_fatalities=asn_inc.fatalities,
            )
            if not decision.asn_covered:
                continue
            issues.append(
                {
                    "severity": "critical",
                    "issue": "ntsb_asn_incident_duplicate",
                    "ntsb_source_record_id": source.source_record_id,
                    "ntsb_incident_id": incident.id,
                    "asn_incident_id": asn_inc.id,
                    "aircraft_id": incident.aircraft_id,
                    "decision": asdict(decision),
                }
            )
            if max_issues is not None and len(issues) >= max_issues:
                return issues
    return issues


def audit_aircraft_near_duplicates() -> List[Dict[str, Any]]:
    """Aircraft rows whose model_name differs only by case/spacing/punctuation."""
    by_key: Dict[str, List[Aircraft]] = {}
    for aircraft in Aircraft.query.order_by(Aircraft.id.asc()).all():
        key = _norm_text(aircraft.model_name)
        if not key:
            continue
        by_key.setdefault(key, []).append(aircraft)

    groups: List[Dict[str, Any]] = []
    for key, rows in sorted(by_key.items()):
        if len(rows) < 2:
            continue
        names = {a.model_name for a in rows}
        if len(names) < 2:
            continue
        groups.append(
            {
                "severity": "warning",
                "issue": "aircraft_near_duplicate",
                "normalized_key": key,
                "aircraft_ids": [a.id for a in rows],
                "model_names": sorted(names),
            }
        )
    return groups


def audit_orphan_ntsb_sources() -> List[Dict[str, Any]]:
    """NTSB IncidentSource rows missing or invalid source_url."""
    issues: List[Dict[str, Any]] = []
    sources = (
        IncidentSource.query.filter_by(source_name="NTSB", is_active=True)
        .order_by(IncidentSource.source_record_id.asc())
        .all()
    )
    for source in sources:
        url = source.source_url
        if not url or is_placeholder_url(url):
            issues.append(
                {
                    "severity": "critical",
                    "issue": "missing_or_placeholder_source_url",
                    "source_record_id": source.source_record_id,
                    "incident_id": source.incident_id,
                    "source_url": url,
                }
            )
        elif is_catalog_url(url):
            issues.append(
                {
                    "severity": "critical",
                    "issue": "catalog_source_url",
                    "source_record_id": source.source_record_id,
                    "incident_id": source.incident_id,
                    "source_url": url,
                }
            )
        if source.incident_id is None:
            issues.append(
                {
                    "severity": "critical",
                    "issue": "orphan_incident_source",
                    "source_record_id": source.source_record_id,
                    "incident_id": None,
                }
            )
    return issues


def _recalc_aircraft_stats(aircraft_ids) -> int:
    from datetime import datetime

    from sqlalchemy import case

    from app import db

    updated = 0
    for aid in sorted(set(aircraft_ids)):
        aircraft = db.session.get(Aircraft, aid)
        if aircraft is None:
            continue
        stats = (
            db.session.query(
                db.func.count(Incident.id),
                db.func.coalesce(db.func.sum(Incident.fatalities), 0),
                db.func.coalesce(
                    db.func.sum(case((Incident.fatalities > 0, 1), else_=0)), 0
                ),
            )
            .filter_by(aircraft_id=aid)
            .first()
        )
        aircraft.total_incidents = stats[0] or 0
        aircraft.total_fatalities = int(stats[1] or 0)
        aircraft.fatal_incidents = int(stats[2] or 0)
        aircraft.last_updated = datetime.utcnow()
        updated += 1
    db.session.commit()
    return updated


def remediate_incident_duplicates(
    incident_duplicates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Delete NTSB incidents flagged as ASN duplicates; keep ASN rows (FR-22.3)."""
    from app import db

    removed: List[str] = []
    aircraft_ids: set = set()

    for issue in incident_duplicates:
        if issue.get("issue") != "ntsb_asn_incident_duplicate":
            continue
        sid = issue["ntsb_source_record_id"]
        source = IncidentSource.query.filter_by(
            source_name="NTSB", source_record_id=sid
        ).first()
        if not source:
            continue
        incident = source.incident
        aircraft_id = incident.aircraft_id if incident else None
        db.session.delete(source)
        if incident:
            db.session.delete(incident)
        if aircraft_id:
            aircraft_ids.add(aircraft_id)
        removed.append(sid)

    db.session.commit()

    stats_updated = _recalc_aircraft_stats(aircraft_ids) if aircraft_ids else 0

    return {
        "removed_ntsb_source_record_ids": removed,
        "removed_count": len(removed),
        "aircraft_stats_recalced": stats_updated,
    }


def run_post_import_audit(
    *,
    window_days: int = 7,
    max_incident_duplicate_samples: int = 25,
) -> Dict[str, Any]:
    incident_duplicates = audit_ntsb_vs_asn_duplicates(window_days=window_days)
    aircraft_near_duplicates = audit_aircraft_near_duplicates()
    orphan_sources = audit_orphan_ntsb_sources()

    ntsb_total = IncidentSource.query.filter_by(
        source_name="NTSB", is_active=True
    ).count()

    critical_incident = len(incident_duplicates)
    critical_orphan = sum(1 for o in orphan_sources if o["severity"] == "critical")
    critical_count = critical_incident + critical_orphan

    return {
        "audit_at": datetime.utcnow().isoformat() + "Z",
        "window_days": window_days,
        "passed": critical_count == 0,
        "critical_duplicate_count": critical_count,
        "counts": {
            "ntsb_sources_active": ntsb_total,
            "incident_duplicate_critical": critical_incident,
            "aircraft_near_duplicate_groups": len(aircraft_near_duplicates),
            "orphan_source_critical": critical_orphan,
        },
        "incident_duplicates": incident_duplicates[:max_incident_duplicate_samples],
        "incident_duplicates_truncated": len(incident_duplicates)
        > max_incident_duplicate_samples,
        "incident_duplicates_total": len(incident_duplicates),
        "aircraft_near_duplicates": aircraft_near_duplicates,
        "orphan_ntsb_sources": orphan_sources,
    }
