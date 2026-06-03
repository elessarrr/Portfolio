"""FAA AIDS vs ASN+NTSB baseline overlap audit (PRD 0009 FR-0)."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.ingestion.dedupe.ntsb_asn import fatalities_like_import, score_ntsb_vs_asn
from app.link_picker import pick_primary_href
from app.models import Incident, IncidentSource


def ntsb_incident_ids() -> set[int]:
    rows = (
        IncidentSource.query.filter_by(source_name="NTSB")
        .filter(IncidentSource.is_active.isnot(False))
        .with_entities(IncidentSource.incident_id)
        .all()
    )
    return {r[0] for r in rows if r[0] is not None}


def baseline_kind_for_incident(incident: Incident, ntsb_ids: set[int]) -> Optional[str]:
    has_asn = bool(incident.asn_url and str(incident.asn_url).strip())
    has_ntsb = incident.id in ntsb_ids
    if has_asn and has_ntsb:
        return "both"
    if has_asn:
        return "asn"
    if has_ntsb:
        return "ntsb"
    return None


def _baseline_url(incident: Incident, label: str) -> Optional[str]:
    if label in ("asn", "both") and incident.asn_url:
        return incident.asn_url.strip()
    for source in incident.sources or []:
        if (source.source_name or "").upper() == "NTSB" and source.is_active is not False:
            if source.source_url:
                return source.source_url.strip()
    return None


def audit_faa_baseline_overlap(*, window_days: int = 2) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Find active FAA rows that match an ASN or NTSB incident (≥2 strong signals)."""
    ntsb_ids = ntsb_incident_ids()
    covered_rows: List[Dict[str, Any]] = []
    counts = {
        "faa_active_scanned": 0,
        "covered_total": 0,
        "covered_by_asn": 0,
        "covered_by_ntsb": 0,
        "covered_by_both": 0,
    }

    faa_sources = (
        IncidentSource.query.filter_by(source_name="FAA_AIDS")
        .filter(IncidentSource.is_active.isnot(False))
        .order_by(IncidentSource.source_record_id.asc())
        .all()
    )

    for source in faa_sources:
        faa_inc = source.incident
        if faa_inc is None:
            continue
        counts["faa_active_scanned"] += 1

        lo = faa_inc.date - datetime.timedelta(days=window_days)
        hi = faa_inc.date + datetime.timedelta(days=window_days)
        candidates = (
            Incident.query.filter(
                Incident.aircraft_id == faa_inc.aircraft_id,
                Incident.id != faa_inc.id,
                Incident.date >= lo,
                Incident.date <= hi,
            )
            .all()
        )

        asn_matches: List[Dict[str, Any]] = []
        ntsb_matches: List[Dict[str, Any]] = []

        for other in candidates:
            label = baseline_kind_for_incident(other, ntsb_ids)
            if label is None:
                continue
            decision = score_ntsb_vs_asn(
                ntsb_date=faa_inc.date,
                asn_date=other.date,
                ntsb_operator=faa_inc.operator,
                asn_operator=other.operator,
                ntsb_location=faa_inc.location,
                asn_location=other.location,
                ntsb_fatalities=fatalities_like_import(faa_inc.fatalities),
                asn_fatalities=fatalities_like_import(other.fatalities),
            )
            if not decision.asn_covered:
                continue
            entry = {
                "baseline_incident_id": other.id,
                "baseline_kind": label,
                "baseline_url": _baseline_url(other, label),
                "score_detail": {
                    "strong_count": decision.signals.strong_count(),
                    "days_apart": decision.days_apart,
                    "operator_ratio": decision.operator_ratio,
                    "location_ratio": decision.location_ratio,
                },
            }
            if label in ("asn", "both"):
                asn_matches.append(entry)
            if label in ("ntsb", "both"):
                ntsb_matches.append(entry)

        if not asn_matches and not ntsb_matches:
            continue

        if asn_matches and ntsb_matches:
            covered_by = "both"
            counts["covered_by_both"] += 1
        elif asn_matches:
            covered_by = "asn"
            counts["covered_by_asn"] += 1
        else:
            covered_by = "ntsb"
            counts["covered_by_ntsb"] += 1

        counts["covered_total"] += 1
        best = (asn_matches or ntsb_matches)[0]
        covered_rows.append(
            {
                "source_record_id": source.source_record_id,
                "faa_incident_id": faa_inc.id,
                "faa_source_id": source.id,
                "covered_by": covered_by,
                "baseline_incident_id": best["baseline_incident_id"],
                "baseline_source": best["baseline_url"],
                "asn_match_count": len(asn_matches),
                "ntsb_match_count": len(ntsb_matches),
                "score_detail": best["score_detail"],
            }
        )

    counts["faa_unique_events"] = counts["faa_active_scanned"] - counts["covered_total"]
    return covered_rows, {**counts, "window_days": window_days}


def remediate_baseline_overlap(rows: List[Dict[str, Any]]) -> int:
    """Set is_active=False on covered FAA sources (provenance preserved)."""
    updated = 0
    for row in rows:
        sid = row.get("faa_source_id")
        if sid is None:
            continue
        source = IncidentSource.query.get(sid)
        if source is None or source.is_active is False:
            continue
        source.is_active = False
        updated += 1
    from app import db

    db.session.commit()
    return updated


def incident_visible_on_aircraft_page(
    incident: Incident,
    sources: Optional[List[IncidentSource]] = None,
) -> bool:
    """PRD 0009 FR-5.6: hide FAA-only rows with no honest outbound link."""
    srcs = list(sources) if sources is not None else list(incident.sources or [])
    if pick_primary_href(incident, srcs):
        return True
    active = [s for s in srcs if s.is_active is not False]
    if not active:
        return True
    names = {(s.source_name or "").upper() for s in active}
    if names <= {"FAA_AIDS"}:
        return False
    return True


def rebuild_retry4_input_jsonl(
    *,
    merged_audit_path: Path,
    overlap_audit_path: Path,
    output_path: Path,
    active_source_ids: Optional[set[str]] = None,
) -> int:
    """Non-brief merged rows excluding overlap-remediated FAA IDs."""
    excluded: set[str] = set()
    if overlap_audit_path.exists():
        for line in overlap_audit_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            row = json.loads(line)
            sid = row.get("source_record_id")
            if sid:
                excluded.add(str(sid))

    rows_out: List[Dict[str, Any]] = []
    for line in merged_audit_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        row = json.loads(line)
        if row.get("bucket") == "working_brief_report":
            continue
        sid = str(row.get("source_record_id") or "")
        if not sid or sid in excluded:
            continue
        if active_source_ids is not None and sid not in active_source_ids:
            continue
        rows_out.append(
            {
                "source_record_id": sid,
                "faa_aids_url": row.get("faa_aids_url"),
                "imported_incident_id": row.get("imported_incident_id"),
                "imported_aircraft_id": row.get("imported_aircraft_id"),
                "make_model": row.get("make_model"),
                "date": row.get("date"),
                "operator": row.get("operator"),
                "bucket": row.get("bucket"),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        f.write(f"# retry4 input — non-brief, post-FR-0 overlap exclude — n={len(rows_out)}\n")
        for row in rows_out:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows_out)
