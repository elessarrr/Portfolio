"""Dedupe re-pass for NTSB working-link rows using mapped aircraft_id (FR-18 / FR-19)."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.ingestion.dedupe.ntsb_asn import fatalities_like_import, score_ntsb_vs_asn
from app.ingestion.ntsb_mapping import NtsbMakeModelMapping, NtsbMappingEntry
from app.models import Aircraft, Incident


def load_audit_jsonl_rows(path: Path | str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with Path(path).open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def load_working_link_rows(path: Path | str) -> List[Dict[str, Any]]:
    return [
        row
        for row in load_audit_jsonl_rows(path)
        if row.get("bucket") == "viable_with_working_link"
    ]


def lookup_mapped_aircraft_id(
    mapping: NtsbMakeModelMapping, make_model: str
) -> Tuple[Optional[int], Optional[NtsbMappingEntry]]:
    """Lookup-only: resolve catalog id for dedupe without creating Aircraft rows."""
    entry = mapping.get(make_model)
    if entry is None:
        return None, None
    aircraft = Aircraft.query.filter_by(model_name=entry.canonical_model_name).first()
    if aircraft:
        return aircraft.id, entry
    return None, entry


def _candidate_asn_incidents(aircraft_id: int, ntsb_date: date, window_days: int):
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


def _best_dedupe_match(
    *,
    aircraft_id: int,
    ntsb_date: date,
    ntsb_operator: Optional[str],
    ntsb_location: Optional[str],
    ntsb_fatalities: Optional[int],
    window_days: int,
):
    candidates = _candidate_asn_incidents(aircraft_id, ntsb_date, window_days)
    best_decision = None
    best_incident: Optional[Incident] = None

    for inc in candidates:
        decision = score_ntsb_vs_asn(
            ntsb_date=ntsb_date,
            asn_date=inc.date,
            ntsb_operator=ntsb_operator,
            asn_operator=inc.operator,
            ntsb_location=ntsb_location,
            asn_location=inc.location,
            ntsb_fatalities=ntsb_fatalities,
            asn_fatalities=inc.fatalities,
        )
        if not best_decision:
            best_decision, best_incident = decision, inc
            continue
        if decision.signals.strong_count() > best_decision.signals.strong_count():
            best_decision, best_incident = decision, inc
            continue
        if (
            decision.signals.strong_count() == best_decision.signals.strong_count()
            and decision.days_apart < best_decision.days_apart
        ):
            best_decision, best_incident = decision, inc

    return best_decision, best_incident


def _parse_date(value: Any) -> Optional[date]:
    if isinstance(value, date):
        return value
    if not value:
        return None
    text = str(value).strip()
    if "T" in text:
        text = text.split("T")[0]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def run_dedupe_repass(
    working_rows: List[Dict[str, Any]],
    mapping: NtsbMakeModelMapping,
    *,
    window_days: int = 7,
    sample_size: int = 10,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    normalized: List[Dict[str, Any]] = []
    newly_deduped_samples: List[Dict[str, Any]] = []
    newly_deduped_count = 0
    still_viable_count = 0
    skipped_unmapped = 0
    skipped_pending_create = 0
    skipped_asn_covered_repasse = 0
    distinct_canonical_ids: set[int] = set()
    distinct_canonical_names: set[str] = set()

    for row in working_rows:
        make_model = row.get("make_model") or ""
        mapped_id, entry = lookup_mapped_aircraft_id(mapping, make_model)
        original_unknown = bool(row.get("unknown_aircraft"))
        original_had_dedupe = row.get("closest_asn_match") is not None

        out = dict(row)
        out["mapped_aircraft_id"] = mapped_id
        out["mapped_model_name"] = entry.canonical_model_name if entry else None
        out["mapping_action"] = entry.action if entry else None

        if entry is None:
            out["dedupe_repasse_status"] = "skip_unmapped"
            skipped_unmapped += 1
            normalized.append(out)
            continue

        distinct_canonical_names.add(entry.canonical_model_name)

        if mapped_id is None:
            out["dedupe_repasse_status"] = "skip_pending_create"
            out["dedupe_repasse_closest_asn_match"] = None
            skipped_pending_create += 1
            normalized.append(out)
            continue

        distinct_canonical_ids.add(mapped_id)
        ntsb_date = _parse_date(row.get("date"))
        best_decision = None
        best_incident = None
        if ntsb_date:
            best_decision, best_incident = _best_dedupe_match(
                aircraft_id=mapped_id,
                ntsb_date=ntsb_date,
                ntsb_operator=row.get("operator"),
                ntsb_location=row.get("location"),
                ntsb_fatalities=fatalities_like_import(row.get("fatalities")),
                window_days=window_days,
            )

        if best_incident and best_decision:
            out["dedupe_repasse_closest_asn_match"] = {
                "incident_id": best_incident.id,
                "date": str(best_incident.date),
                "operator": best_incident.operator,
                "location": best_incident.location,
                "fatalities": best_incident.fatalities,
                "asn_url": best_incident.asn_url,
                "decision": asdict(best_decision),
            }
        else:
            out["dedupe_repasse_closest_asn_match"] = None

        if best_decision and best_decision.asn_covered:
            out["dedupe_repasse_status"] = "skip_asn_covered"
            skipped_asn_covered_repasse += 1
            if (original_unknown or not original_had_dedupe) and len(
                newly_deduped_samples
            ) < sample_size:
                newly_deduped_samples.append(
                    {
                        "source_record_id": row.get("source_record_id"),
                        "make_model": make_model,
                        "mapped_model_name": entry.canonical_model_name,
                        "mapped_aircraft_id": mapped_id,
                        "original_unknown_aircraft": original_unknown,
                        "closest_asn_match": out["dedupe_repasse_closest_asn_match"],
                    }
                )
            newly_deduped_count += 1
        else:
            out["dedupe_repasse_status"] = "import"
            still_viable_count += 1

        normalized.append(out)

    report = {
        "working_link_total": len(working_rows),
        "newly_deduped_count": newly_deduped_count,
        "still_viable_count": still_viable_count,
        "import_candidates_after_dedupe_repasse": still_viable_count,
        "skipped_unmapped": skipped_unmapped,
        "skipped_pending_create": skipped_pending_create,
        "skipped_asn_covered_repasse": skipped_asn_covered_repasse,
        "distinct_canonical_aircraft_ids": len(distinct_canonical_ids),
        "distinct_canonical_model_names": len(distinct_canonical_names),
        "window_days": window_days,
        "samples": {"newly_deduped_repasse": newly_deduped_samples},
        "notes": {
            "newly_deduped_count": (
                "Working-link rows ASN-covered after mapped aircraft_id dedupe "
                "(includes rows that skipped dedupe at original audit due to unknown_aircraft)."
            ),
            "skip_pending_create": (
                "create_approved catalog pages not yet in DB; dedupe deferred until import creates them."
            ),
        },
    }
    return report, normalized


def write_jsonl(path: Path | str, rows: List[Dict[str, Any]], header_lines: List[str]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for line in header_lines:
            f.write(line + "\n")
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
