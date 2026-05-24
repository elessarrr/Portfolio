"""Attach orphan FAA Boeing/Airbus incidents to aircraft profiles; exact date+reg merge only."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func

from app import db
from app.ingestion.canonical import apply_canonical_rules
from app.ingestion.dedupe import record_dedupe_decision
from app.ingestion.importers.faa_aids_importer import FAAAIDSImporter
from app.ingestion.linking.incident_linker import _delete_orphan_incident, _reparent_sources
from app.link_helpers import resolve_source_href
from app.models import Aircraft, Incident, IncidentSource

_ASIAS = "%asias%"
_MAKE_BOEING = "BOEING"
_MAKE_AIRBUS = "AIRBUS"


@dataclass
class AttachSummary:
    scanned: int = 0
    attached: int = 0
    attach_failed: int = 0
    merge_linked: int = 0
    merge_skipped: int = 0
    merge_ambiguous: int = 0
    errors: int = 0
    attach_by_model: Dict[str, int] = field(default_factory=dict)
    details: List[str] = field(default_factory=list)


def exact_match_key(date, registration) -> Optional[Tuple[str, str]]:
    if not date:
        return None
    reg = re.sub(r"[^A-Z0-9]", "", (registration or "").upper())
    if not reg:
        return None
    return (date.isoformat(), reg)


def _faa_make(source_data: Optional[dict]) -> str:
    data = source_data or {}
    return (data.get("c23") or "").strip().upper()


def is_boeing_airbus_faa(source: IncidentSource) -> bool:
    if (source.source_name or "") != "FAA_AIDS" or not source.is_active:
        return False
    url = (source.source_url or "").lower()
    if "asias" not in url:
        return False
    make = _faa_make(source.source_data if isinstance(source.source_data, dict) else None)
    return make.startswith(_MAKE_BOEING) or make.startswith(_MAKE_AIRBUS)


def _registration_for(source: IncidentSource, incident: Incident) -> str:
    if incident.registration:
        return incident.registration
    data = source.source_data if isinstance(source.source_data, dict) else {}
    return (data.get("c203") or data.get("registration") or "").strip()


def _make_model_from_source(source: IncidentSource) -> str:
    data = source.source_data if isinstance(source.source_data, dict) else {}
    make = (data.get("c23") or "").strip()
    model = (data.get("c24") or "").strip()
    return f"{make} {model}".strip()


def iter_orphan_faa_boeing_airbus(limit: Optional[int] = None):
    query = (
        db.session.query(IncidentSource, Incident)
        .join(Incident, Incident.id == IncidentSource.incident_id)
        .filter(
            IncidentSource.source_name == "FAA_AIDS",
            IncidentSource.is_active.is_(True),
            IncidentSource.source_url.like(_ASIAS),
            Incident.aircraft_id.is_(None),
        )
        .order_by(IncidentSource.id.asc())
    )
    count = 0
    for row in query.yield_per(500):
        source, incident = row
        if not is_boeing_airbus_faa(source):
            continue
        yield source, incident
        count += 1
        if limit and count >= limit:
            break


def _incident_has_resolvable_link(incident: Incident) -> bool:
    for source in incident.sources:
        if source.is_active and resolve_source_href(source):
            return True
    return False


def attach_aircraft_ids(
    *,
    dry_run: bool = False,
    batch_size: int = 500,
    limit: Optional[int] = None,
) -> AttachSummary:
    summary = AttachSummary()
    resolver = FAAAIDSImporter()
    pending = 0

    for source, incident in iter_orphan_faa_boeing_airbus(limit=limit):
        summary.scanned += 1
        make_model = _make_model_from_source(source)
        aircraft_id = resolver.resolve_aircraft(
            {"make_model": make_model, "date": incident.date}
        )
        if not aircraft_id:
            summary.attach_failed += 1
            if len(summary.details) < 50:
                summary.details.append(f"attach_fail incident={incident.id} make_model={make_model!r}")
            continue

        aircraft = db.session.get(Aircraft, aircraft_id)
        model_label = aircraft.model_name if aircraft else str(aircraft_id)
        summary.attach_by_model[model_label] = summary.attach_by_model.get(model_label, 0) + 1

        if dry_run:
            summary.attached += 1
            continue

        try:
            incident.aircraft_id = aircraft_id
            summary.attached += 1
            pending += 1
            if pending >= batch_size:
                db.session.commit()
                pending = 0
        except Exception as exc:
            db.session.rollback()
            summary.errors += 1
            summary.details.append(f"attach_error incident={incident.id}: {exc}")

    if not dry_run and pending > 0:
        db.session.commit()

    return summary


def _faa_incidents_boeing_airbus(limit: Optional[int] = None) -> List[Tuple[IncidentSource, Incident]]:
    query = (
        db.session.query(IncidentSource, Incident)
        .join(Incident, Incident.id == IncidentSource.incident_id)
        .filter(
            IncidentSource.source_name == "FAA_AIDS",
            IncidentSource.is_active.is_(True),
            IncidentSource.source_url.like(_ASIAS),
        )
        .order_by(IncidentSource.id.asc())
    )
    out: List[Tuple[IncidentSource, Incident]] = []
    for source, incident in query.yield_per(500):
        if not is_boeing_airbus_faa(source):
            continue
        out.append((source, incident))
        if limit and len(out) >= limit:
            break
    return out


def exact_merge_faa_to_profile(
    *,
    dry_run: bool = False,
    limit: Optional[int] = None,
    commit_every: int = 200,
) -> AttachSummary:
    """Merge FAA sources onto no-link Boeing/Airbus profile rows — exact date+reg only."""
    summary = AttachSummary()
    faa_index: Dict[Tuple[str, str], List[int]] = {}

    for source, incident in _faa_incidents_boeing_airbus():
        key = exact_match_key(incident.date, _registration_for(source, incident))
        if not key:
            continue
        faa_index.setdefault(key, []).append(incident.id)

    pending = 0
    checked = 0
    aircraft_ids = [
        a.id
        for a in Aircraft.query.filter(
            func.upper(Aircraft.manufacturer).in_([_MAKE_BOEING, _MAKE_AIRBUS])
        ).all()
    ]

    for aircraft_id in aircraft_ids:
        for incident in Incident.query.filter_by(aircraft_id=aircraft_id).all():
            if _incident_has_resolvable_link(incident):
                continue
            key = exact_match_key(incident.date, incident.registration)
            if not key:
                summary.merge_skipped += 1
                continue

            checked += 1
            if limit and checked > limit:
                break

            candidates = [cid for cid in faa_index.get(key, []) if cid != incident.id]
            if len(candidates) == 0:
                summary.merge_skipped += 1
                continue
            if len(candidates) > 1:
                summary.merge_ambiguous += 1
                summary.details.append(
                    f"ambiguous key={key} target={incident.id} candidates={candidates}"
                )
                continue

            faa_incident_id = candidates[0]
            summary.scanned += 1

            if dry_run:
                summary.merge_linked += 1
                summary.details.append(
                    f"would merge faa_incident={faa_incident_id} -> target={incident.id} key={key}"
                )
                continue

            try:
                moved = _reparent_sources(faa_incident_id, incident.id)
                if moved:
                    summary.merge_linked += 1
                    apply_canonical_rules(incident)
                    record_dedupe_decision(
                        source_name="FAA_AIDS",
                        source_record_id=None,
                        incoming_incident_id=faa_incident_id,
                        matched_incident_id=incident.id,
                        decision="linked_exact_date_registration",
                        rule="exact_date_registration",
                        score=1.0,
                        details={"key": key},
                    )
                    if _delete_orphan_incident(faa_incident_id):
                        summary.details.append(f"deleted orphan incident {faa_incident_id}")
                pending += 1
                if pending >= commit_every:
                    db.session.commit()
                    pending = 0
            except Exception as exc:
                db.session.rollback()
                summary.errors += 1
                summary.details.append(
                    f"merge_error faa={faa_incident_id} target={incident.id}: {exc}"
                )

        if limit and checked > limit:
            break

    if not dry_run and pending > 0:
        db.session.commit()

    return summary


def run_faa_profile_attach(
    *,
    dry_run: bool = False,
    attach_only: bool = False,
    merge_only: bool = False,
    batch_size: int = 500,
    limit: Optional[int] = None,
    summary_path: Optional[str] = None,
) -> AttachSummary:
    combined = AttachSummary()

    if not merge_only:
        attach_summary = attach_aircraft_ids(
            dry_run=dry_run, batch_size=batch_size, limit=limit
        )
        combined.scanned += attach_summary.scanned
        combined.attached += attach_summary.attached
        combined.attach_failed += attach_summary.attach_failed
        combined.errors += attach_summary.errors
        combined.attach_by_model = attach_summary.attach_by_model
        combined.details.extend(attach_summary.details)

    if not attach_only:
        merge_summary = exact_merge_faa_to_profile(dry_run=dry_run, limit=limit)
        combined.scanned += merge_summary.scanned
        combined.merge_linked += merge_summary.merge_linked
        combined.merge_skipped += merge_summary.merge_skipped
        combined.merge_ambiguous += merge_summary.merge_ambiguous
        combined.errors += merge_summary.errors
        combined.details.extend(merge_summary.details)

    if summary_path:
        path = Path(summary_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(combined)
        payload["dry_run"] = dry_run
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return combined
