"""Post-import audit for FAA AIDS bulk import (PRD 0007 FR-11)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from app.ingestion.dedupe.ntsb_asn import score_ntsb_vs_asn
from app.ingestion.link_schema import assert_valid_source_url, is_catalog_url, is_placeholder_url
from app.models import Incident, IncidentSource


def _audit_faa_baseline_duplicates(
    *,
    window_days: int = 2,
    issue_asn: str = "faa_asn_duplicate",
    issue_ntsb: str = "faa_ntsb_duplicate",
) -> List[Dict[str, Any]]:
    """Active FAA rows that score as duplicates of ASN and/or NTSB incidents."""
    from app.ingestion.faa_baseline_overlap import audit_faa_baseline_overlap

    rows, _ = audit_faa_baseline_overlap(window_days=window_days)
    issues: List[Dict[str, Any]] = []
    for row in rows:
        covered_by = row.get("covered_by") or ""
        if covered_by in ("asn", "both"):
            issues.append(
                {
                    "severity": "critical",
                    "issue": issue_asn,
                    "faa_source_record_id": row.get("source_record_id"),
                    "faa_incident_id": row.get("faa_incident_id"),
                    "baseline_incident_id": row.get("baseline_incident_id"),
                    "covered_by": covered_by,
                    "score_detail": row.get("score_detail"),
                }
            )
        if covered_by in ("ntsb", "both"):
            issues.append(
                {
                    "severity": "critical",
                    "issue": issue_ntsb,
                    "faa_source_record_id": row.get("source_record_id"),
                    "faa_incident_id": row.get("faa_incident_id"),
                    "baseline_incident_id": row.get("baseline_incident_id"),
                    "covered_by": covered_by,
                    "score_detail": row.get("score_detail"),
                }
            )
    return issues


def audit_faa_asn_duplicates(*, window_days: int = 2) -> List[Dict[str, Any]]:
    return [i for i in _audit_faa_baseline_duplicates(window_days=window_days) if i["issue"] == "faa_asn_duplicate"]


def audit_faa_ntsb_duplicates(*, window_days: int = 2) -> List[Dict[str, Any]]:
    return [i for i in _audit_faa_baseline_duplicates(window_days=window_days) if i["issue"] == "faa_ntsb_duplicate"]


def audit_bad_faa_urls() -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    for source in IncidentSource.query.filter_by(source_name="FAA_AIDS", is_active=True):
        url = source.source_url
        try:
            if not url or is_placeholder_url(url) or is_catalog_url(url):
                raise ValueError("invalid url")
            assert_valid_source_url(url)
        except Exception as exc:
            issues.append(
                {
                    "severity": "critical",
                    "issue": "bad_faa_source_url",
                    "source_record_id": source.source_record_id,
                    "source_url": url,
                    "error": str(exc),
                }
            )
    return issues


def remediate_faa_duplicates(issues: List[Dict[str, Any]]) -> int:
    """Deactivate FAA sources for baseline duplicate issues (soft-delete)."""
    from app import db

    updated = 0
    seen_sources: set[int] = set()
    for issue in issues:
        if issue.get("issue") not in ("faa_asn_duplicate", "faa_ntsb_duplicate", "faa_asn_incident_duplicate"):
            continue
        iid = issue.get("faa_incident_id")
        if iid is None:
            continue
        incident = Incident.query.get(iid)
        if incident is None:
            continue
        for source in list(incident.sources):
            if source.source_name != "FAA_AIDS" or source.id in seen_sources:
                continue
            source.is_active = False
            seen_sources.add(source.id)
            updated += 1
    db.session.commit()
    return updated


def run_post_import_audit(*, remediate: bool = False) -> Dict[str, Any]:
    asn_dupes = audit_faa_asn_duplicates()
    ntsb_dupes = audit_faa_ntsb_duplicates()
    dupes = asn_dupes + ntsb_dupes
    bad_urls = audit_bad_faa_urls()
    remediated = 0
    if remediate and dupes:
        remediated = remediate_faa_duplicates(dupes)

    return {
        "duplicate_count": len(dupes),
        "faa_asn_duplicate_count": len(asn_dupes),
        "faa_ntsb_duplicate_count": len(ntsb_dupes),
        "bad_url_count": len(bad_urls),
        "duplicates": dupes[:20],
        "bad_urls": bad_urls[:20],
        "remediated": remediated,
        "passed": len(dupes) == 0 and len(bad_urls) == 0,
    }
