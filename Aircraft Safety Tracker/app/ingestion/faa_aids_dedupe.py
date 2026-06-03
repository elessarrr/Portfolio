"""FAA AIDS vs ASN dedupe pass (PRD 0007 FR-6)."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app import db
from app.ingestion.dedupe.ntsb_asn import fatalities_like_import, score_ntsb_vs_asn
from app.ingestion.faa_baseline_overlap import baseline_kind_for_incident, ntsb_incident_ids
from app.ingestion.faa_aids_mapping import FaaAidsMakeModelMapping
from app.ingestion.importers.faa_aids_importer import FAAAIDSImporter
from app.models import Incident


def load_faa_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def _faa_make_model(row: Dict[str, Any]) -> str:
    make = str(row.get("c23") or "").strip()
    model = str(row.get("c24") or "").strip()
    return (f"{make} {model}".strip() if model else make).strip()


def run_faa_dedupe_pass(
    rows: List[Dict[str, Any]],
    mapping: FaaAidsMakeModelMapping,
    *,
    window_days: int = 2,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    audit_rows: List[Dict[str, Any]] = []
    counts = {
        "total": 0,
        "baseline_covered": 0,
        "asn_covered": 0,
        "import": 0,
        "unmapped": 0,
    }

    for raw in rows:
        counts["total"] += 1
        parsed = FAAAIDSImporter.parse(raw)
        c5 = str(raw.get("c5") or "").strip()
        faa_mm = _faa_make_model(raw)

        if parsed is None:
            audit_rows.append(
                {
                    "c5": c5,
                    "faa_make_model": faa_mm,
                    "dedupe_status": "unmapped",
                    "closest_asn_incident_id": None,
                    "score_detail": {"reason": "parse_failed"},
                }
            )
            counts["unmapped"] += 1
            continue

        entry = mapping.get(faa_mm)
        if entry is None or entry.action == "skip":
            audit_rows.append(
                {
                    "c5": c5,
                    "faa_make_model": faa_mm,
                    "dedupe_status": "unmapped",
                    "closest_asn_incident_id": None,
                    "score_detail": {"reason": "no_mapping_or_skip"},
                }
            )
            counts["unmapped"] += 1
            continue

        entry = mapping.get(faa_mm)
        aircraft_id = mapping.lookup_aircraft_id_only(faa_mm)
        if aircraft_id is None and entry and entry.action == "create_approved":
            audit_rows.append(
                {
                    "c5": c5,
                    "faa_make_model": faa_mm,
                    "canonical_model_name": entry.canonical_model_name,
                    "dedupe_status": "pending_create",
                    "closest_asn_incident_id": None,
                    "score_detail": {"reason": "awaiting_bootstrap"},
                }
            )
            counts.setdefault("pending_create", 0)
            counts["pending_create"] += 1
            continue
        if aircraft_id is None:
            audit_rows.append(
                {
                    "c5": c5,
                    "faa_make_model": faa_mm,
                    "dedupe_status": "unmapped",
                    "closest_asn_incident_id": None,
                    "score_detail": {"reason": "unresolved_aircraft_id"},
                }
            )
            counts["unmapped"] += 1
            continue

        faa_date = parsed["date"]
        start = faa_date - datetime.timedelta(days=window_days)
        end = faa_date + datetime.timedelta(days=window_days)
        candidates = (
            Incident.query.filter(
                Incident.aircraft_id == aircraft_id,
                Incident.date >= start,
                Incident.date <= end,
            )
            .order_by(Incident.date.asc())
            .all()
        )

        ntsb_ids = ntsb_incident_ids()
        best_id: Optional[int] = None
        best_detail: Dict[str, Any] = {}
        covered = False
        covered_by: Optional[str] = None
        for cand in candidates:
            kind = baseline_kind_for_incident(cand, ntsb_ids)
            if kind is None:
                continue
            decision = score_ntsb_vs_asn(
                ntsb_date=faa_date,
                asn_date=cand.date,
                ntsb_operator=parsed.get("operator"),
                asn_operator=cand.operator,
                ntsb_location=parsed.get("location"),
                asn_location=cand.location,
                ntsb_fatalities=fatalities_like_import(parsed.get("fatalities")),
                asn_fatalities=fatalities_like_import(cand.fatalities),
            )
            detail = {
                "baseline_incident_id": cand.id,
                "baseline_kind": kind,
                "strong_count": decision.signals.strong_count(),
                "days_apart": decision.days_apart,
                "operator_ratio": decision.operator_ratio,
                "location_ratio": decision.location_ratio,
            }
            if decision.asn_covered:
                covered = True
                best_id = cand.id
                best_detail = detail
                if covered_by is None:
                    covered_by = kind
                elif covered_by != kind and kind != covered_by:
                    covered_by = "both"
                else:
                    covered_by = kind
                break
            if best_id is None or detail["strong_count"] > best_detail.get("strong_count", 0):
                best_id = cand.id
                best_detail = detail

        if covered:
            status = "baseline_covered"
            counts["baseline_covered"] = counts.get("baseline_covered", 0) + 1
            legacy = "asn_covered" if covered_by in (None, "asn", "both") else "ntsb_covered"
            counts[legacy] = counts.get(legacy, 0) + 1
        else:
            status = "import"
            counts["import"] += 1
        audit_rows.append(
            {
                "c5": c5,
                "faa_make_model": faa_mm,
                "mapped_aircraft_id": aircraft_id,
                "dedupe_status": status,
                "covered_by": covered_by,
                "closest_baseline_incident_id": best_id,
                "closest_asn_incident_id": best_id,
                "score_detail": best_detail,
            }
        )

    report = {
        **counts,
        "window_days": window_days,
    }
    return audit_rows, report


def write_audit_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# FAA AIDS dedupe audit — {len(rows)} rows\n")
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
