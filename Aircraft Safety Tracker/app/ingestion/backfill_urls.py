"""Backfill source_url / links[] on IncidentSource rows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy import or_

from app import db
from app.ingestion.canonical import attach_source_to_incident
from app.ingestion.url_builders import (
    build_asn_source_url,
    build_faa_aids_source_url,
    build_faa_sdr_source_url,
    build_ntsb_source_url,
)
from app.ingestion.link_schema import is_placeholder_url, sanitize_url
from app.models import IncidentSource


@dataclass
class BackfillSummary:
    scanned: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    details: List[str] = field(default_factory=list)


def _sources_missing_url(source_name: str, limit: Optional[int] = None):
    query = (
        IncidentSource.query.filter_by(source_name=source_name, is_active=True)
        .filter(
            or_(
                IncidentSource.source_url.is_(None),
                IncidentSource.source_url == "",
            )
        )
        .order_by(IncidentSource.id.asc())
    )
    if limit:
        query = query.limit(limit)
    return query.all()


def _sources_for_refresh(source_name: str, limit: Optional[int] = None, offset: int = 0):
    query = (
        IncidentSource.query.filter_by(source_name=source_name, is_active=True)
        .order_by(IncidentSource.id.asc())
    )
    if offset:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)
    return query.all()


def _resolved_url_for_row(source_name: str, row: IncidentSource, data: dict) -> Optional[str]:
    if source_name == "NTSB":
        return build_ntsb_source_url(
            source_record_id=row.source_record_id,
            source_url=row.source_url,
            source_data=data,
        )
    if source_name == "ASN":
        return build_asn_source_url(
            source_record_id=row.source_record_id,
            source_url=row.source_url,
        )
    if source_name == "FAA_AIDS":
        return sanitize_url(row.source_url)
    if source_name == "FAA_SDR":
        return build_faa_sdr_source_url(source_record_id=row.source_record_id)
    return sanitize_url(row.report_url or row.source_url)


def backfill_source_urls(
    source_name: str,
    *,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> BackfillSummary:
    summary = BackfillSummary()
    rows = _sources_missing_url(source_name, limit=limit)

    for row in rows:
        summary.scanned += 1
        data = row.source_data if isinstance(row.source_data, dict) else {}
        new_url = sanitize_url(_resolved_url_for_row(source_name, row, data))
        if not new_url:
            summary.skipped += 1
            continue

        if row.source_url and not is_placeholder_url(row.source_url):
            summary.skipped += 1
            continue

        if dry_run:
            summary.updated += 1
            summary.details.append(f"would set {source_name} id={row.id} -> {new_url[:80]}")
            continue

        try:
            attach_source_to_incident(
                incident_id=row.incident_id,
                source_name=row.source_name,
                source_record_id=row.source_record_id,
                source_url=new_url,
                report_url=row.report_url,
                source_data=data,
                confidence_level=row.confidence_level or "Medium",
            )
            summary.updated += 1
        except Exception as exc:
            db.session.rollback()
            summary.errors += 1
            summary.details.append(f"error source id={row.id}: {exc}")

    return summary


def refresh_source_links(
    source_name: str,
    *,
    dry_run: bool = False,
    limit: Optional[int] = None,
    offset: int = 0,
    commit_every: int = 500,
) -> BackfillSummary:
    """Rebuild source_data.links[] and normalize source_url for existing rows."""
    summary = BackfillSummary()
    rows = _sources_for_refresh(source_name, limit=limit, offset=offset)
    pending = 0

    for row in rows:
        summary.scanned += 1
        data = row.source_data if isinstance(row.source_data, dict) else {}
        resolved = sanitize_url(_resolved_url_for_row(source_name, row, data))
        current = sanitize_url(row.source_url)

        if dry_run:
            summary.updated += 1
            continue

        try:
            attach_source_to_incident(
                incident_id=row.incident_id,
                source_name=row.source_name,
                source_record_id=row.source_record_id,
                source_url=resolved or current,
                report_url=row.report_url,
                source_data=data,
                confidence_level=row.confidence_level or "Medium",
            )
            summary.updated += 1
            pending += 1
            if pending >= commit_every:
                db.session.commit()
                pending = 0
        except Exception as exc:
            db.session.rollback()
            summary.errors += 1
            summary.details.append(f"error source id={row.id}: {exc}")

    if not dry_run and pending > 0:
        db.session.commit()

    return summary
