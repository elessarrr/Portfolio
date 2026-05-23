"""Retroactive cross-source incident linking (merge FAA orphans into NTSB/ASN incidents)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from sqlalchemy import and_, exists, not_, or_

from app import db
from sqlalchemy import text
from app.ingestion.canonical import apply_canonical_rules
from app.ingestion.dedupe import _score_match, find_best_incident_match, record_dedupe_decision
from app.link_helpers import incident_has_active_link
from app.models import Incident, IncidentSource, ReportAnalysis, SystemTag

_LINK_MERGE_INDEXES = (
    "CREATE INDEX IF NOT EXISTS ix_incident_date_registration ON incident(date, registration)",
    "CREATE INDEX IF NOT EXISTS ix_incident_source_name_incident ON incident_source(source_name, incident_id)",
)


def ensure_link_merge_indexes() -> None:
    """Speed up exact date+registration merges on large SQLite DBs."""
    for stmt in _LINK_MERGE_INDEXES:
        db.session.execute(text(stmt))
    db.session.commit()


@dataclass
class LinkIncidentsSummary:
    scanned: int = 0
    linked: int = 0
    merged_incidents: int = 0
    ambiguous: int = 0
    no_match: int = 0
    skipped_has_link: int = 0
    errors: int = 0
    details: List[str] = field(default_factory=list)


def _incident_has_linkable_source(incident_id: int) -> bool:
    return (
        db.session.query(IncidentSource.id)
        .filter(
            IncidentSource.incident_id == incident_id,
            IncidentSource.is_active.is_(True),
            or_(
                and_(IncidentSource.source_url.isnot(None), IncidentSource.source_url != ""),
                and_(IncidentSource.report_url.isnot(None), IncidentSource.report_url != ""),
            ),
        )
        .first()
        is not None
    )


def _faa_only_incident_ids(limit: Optional[int] = None) -> List[int]:
    """Incidents with FAA_AIDS and no active NTSB/ASN/MEDIA URL."""
    has_faa = exists().where(
        and_(
            IncidentSource.incident_id == Incident.id,
            IncidentSource.source_name == "FAA_AIDS",
        )
    )
    has_link = exists().where(
        and_(
            IncidentSource.incident_id == Incident.id,
            IncidentSource.is_active.is_(True),
            IncidentSource.source_name.in_(("NTSB", "ASN", "MEDIA")),
            or_(
                and_(IncidentSource.source_url.isnot(None), IncidentSource.source_url != ""),
                and_(IncidentSource.report_url.isnot(None), IncidentSource.report_url != ""),
            ),
        )
    )
    query = (
        Incident.query.filter(has_faa)
        .filter(not_(has_link))
        .order_by(Incident.id.asc())
    )
    if limit:
        query = query.limit(limit)
    return [row.id for row in query.all()]


def find_best_linkable_incident_match(
    incident: Incident,
    *,
    window_days: int = 1,
    min_score: float = 0.72,
):
    """Like find_best_incident_match but only considers incidents with outbound links."""
    import datetime

    from app.ingestion.dedupe import _normalize_text

    if not incident.date:
        return None, None, 0.0, {}

    reg_norm = _normalize_text(incident.registration)
    loc_norm = _normalize_text(incident.location)
    op_norm = _normalize_text(incident.operator)

    start = incident.date - datetime.timedelta(days=window_days)
    end = incident.date + datetime.timedelta(days=window_days)
    candidates = Incident.query.filter(Incident.date >= start, Incident.date <= end).all()

    best_incident = None
    best_rule = None
    best_score = 0.0
    best_details: Dict[str, object] = {}

    for candidate in candidates:
        if candidate.id == incident.id:
            continue
        if not _incident_has_linkable_source(candidate.id):
            continue
        score, rule, details = _score_match(
            date=incident.date,
            reg_norm=reg_norm,
            loc_norm=loc_norm,
            op_norm=op_norm,
            incident=candidate,
        )
        if score > best_score:
            best_incident = candidate
            best_rule = rule
            best_score = score
            best_details = details

    if best_incident is None or best_score < min_score:
        return None, None, best_score, best_details
    return best_incident, best_rule, best_score, best_details


def find_relaxed_match(
    incident: Incident,
    *,
    window_days: int = 3,
    min_score: float = 0.72,
) -> tuple:
    """Try tight window first, then wider window and slightly lower threshold."""
    reg = (incident.registration or "").strip()
    tight_min = min_score if reg else min_score + 0.05

    matched, rule, score, details = find_best_linkable_incident_match(
        incident,
        window_days=1,
        min_score=tight_min,
    )
    if matched:
        return matched, rule, score, details

    relaxed_min = max(0.68, min_score - 0.06) if reg else min_score
    return find_best_linkable_incident_match(
        incident,
        window_days=window_days,
        min_score=relaxed_min,
    )


def _reparent_sources(source_incident_id: int, target_incident_id: int) -> int:
    moved = 0
    sources = IncidentSource.query.filter_by(incident_id=source_incident_id).all()
    for src in sources:
        if src.incident_id == target_incident_id:
            continue
        conflict = None
        if src.source_record_id:
            conflict = IncidentSource.query.filter_by(
                source_name=src.source_name,
                source_record_id=src.source_record_id,
            ).first()
        if conflict and conflict.incident_id == target_incident_id:
            db.session.delete(src)
            continue
        if conflict and conflict.id != src.id:
            db.session.delete(src)
            continue
        src.incident_id = target_incident_id
        moved += 1
    return moved


def _delete_orphan_incident(incident_id: int) -> bool:
    remaining = IncidentSource.query.filter_by(incident_id=incident_id).count()
    if remaining > 0:
        return False
    incident = Incident.query.get(incident_id)
    if not incident:
        return False
    SystemTag.query.filter_by(incident_id=incident_id).delete(synchronize_session=False)
    ReportAnalysis.query.filter_by(incident_id=incident_id).delete(synchronize_session=False)
    db.session.delete(incident)
    return True


def link_incidents_batch(
    *,
    dry_run: bool = False,
    limit: Optional[int] = None,
    min_score: float = 0.72,
    commit_every: int = 200,
) -> LinkIncidentsSummary:
    summary = LinkIncidentsSummary()
    candidate_ids = _faa_only_incident_ids(limit=limit)
    seen_targets: Set[int] = set()
    pending_commits = 0

    for incident_id in candidate_ids:
        summary.scanned += 1
        source_incident = Incident.query.get(incident_id)
        if not source_incident or not source_incident.date:
            summary.no_match += 1
            continue

        if incident_has_active_link(source_incident):
            summary.skipped_has_link += 1
            continue

        matched, rule, score, details = find_relaxed_match(
            source_incident, min_score=min_score
        )
        if not matched or matched.id == source_incident.id:
            summary.no_match += 1
            continue

        if not _incident_has_linkable_source(matched.id):
            summary.no_match += 1
            continue

        if matched.id in seen_targets and score < 0.9:
            summary.ambiguous += 1
            continue

        summary.linked += 1
        seen_targets.add(matched.id)

        if dry_run:
            summary.details.append(
                f"would merge incident {source_incident.id} -> {matched.id} "
                f"(score={score:.2f}, rule={rule})"
            )
            continue

        try:
            moved = _reparent_sources(source_incident.id, matched.id)
            if moved:
                summary.merged_incidents += 1
            apply_canonical_rules(matched)
            record_dedupe_decision(
                source_name="FAA_AIDS",
                source_record_id=None,
                incoming_incident_id=source_incident.id,
                matched_incident_id=matched.id,
                decision="linked_retroactive",
                rule=rule,
                score=score,
                details=details,
            )
            if _delete_orphan_incident(source_incident.id):
                summary.details.append(f"deleted orphan incident {source_incident.id}")
            pending_commits += 1
            if pending_commits >= commit_every:
                db.session.commit()
                pending_commits = 0
        except Exception as exc:
            db.session.rollback()
            summary.errors += 1
            summary.details.append(f"error incident {source_incident.id}: {exc}")

    if not dry_run and pending_commits > 0:
        db.session.commit()

    return summary


def link_incidents_exact_batch(
    *,
    dry_run: bool = False,
    limit: Optional[int] = None,
    max_ntsb_scan: Optional[int] = None,
    commit_every: int = 200,
) -> LinkIncidentsSummary:
    """Fast path: merge FAA rows that share exact date + registration with a linked NTSB incident."""
    ensure_link_merge_indexes()
    summary = LinkIncidentsSummary()
    pending_commits = 0

    db.session.execute(text("DROP TABLE IF EXISTS _link_ntsb_keys"))
    ntsb_keys_sql = """
        CREATE TEMP TABLE _link_ntsb_keys AS
        SELECT i.id AS ntsb_id, i.date AS incident_date, i.registration AS tail
        FROM incident i
        INNER JOIN incident_source n
            ON n.incident_id = i.id
            AND n.source_name = 'NTSB'
            AND n.is_active = 1
            AND n.source_url IS NOT NULL
            AND n.source_url != ''
        WHERE i.registration IS NOT NULL
            AND i.registration != ''
    """
    if max_ntsb_scan is not None:
        ntsb_keys_sql += f" LIMIT {int(max_ntsb_scan)}"
    db.session.execute(text(ntsb_keys_sql))
    db.session.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_link_ntsb_keys_date_tail "
            "ON _link_ntsb_keys(incident_date, tail)"
        )
    )

    pair_sql = """
        SELECT i_faa.id AS faa_incident_id, k.ntsb_id AS target_incident_id
        FROM _link_ntsb_keys k
        INNER JOIN incident i_faa
            ON i_faa.date = k.incident_date
            AND i_faa.registration = k.tail
            AND i_faa.id != k.ntsb_id
        INNER JOIN incident_source f
            ON f.incident_id = i_faa.id AND f.source_name = 'FAA_AIDS'
        ORDER BY i_faa.id
    """
    if limit:
        pair_sql += f" LIMIT {int(limit)}"
    pairs = db.session.execute(text(pair_sql)).fetchall()

    for faa_id, target_id in pairs:
        summary.scanned += 1
        if dry_run:
            summary.linked += 1
            summary.details.append(f"would merge {faa_id} -> {target_id} (exact date+reg)")
            continue
        try:
            moved = _reparent_sources(int(faa_id), int(target_id))
            if moved:
                summary.merged_incidents += 1
            summary.linked += 1
            target = Incident.query.get(int(target_id))
            if target:
                apply_canonical_rules(target)
            record_dedupe_decision(
                source_name="FAA_AIDS",
                source_record_id=None,
                incoming_incident_id=int(faa_id),
                matched_incident_id=int(target_id),
                decision="linked_exact_date_registration",
                rule="exact_date_registration",
                score=1.0,
                details={},
            )
            if _delete_orphan_incident(int(faa_id)):
                summary.details.append(f"deleted orphan incident {faa_id}")
            pending_commits += 1
            if pending_commits >= commit_every:
                db.session.commit()
                pending_commits = 0
        except Exception as exc:
            db.session.rollback()
            summary.errors += 1
            summary.details.append(f"error merge {faa_id}->{target_id}: {exc}")

    if not dry_run and pending_commits > 0:
        db.session.commit()

    return summary
