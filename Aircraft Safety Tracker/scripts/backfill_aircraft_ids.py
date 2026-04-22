import argparse
import json
import os
import sys
from collections import Counter
from typing import Any, Dict, Optional

# Add project root to path so "app" imports work when running as a script.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.ingestion.importers.base import DataSourceImporter
from app.models import Aircraft, Incident, IncidentSource


class BackfillResolver(DataSourceImporter):
    """
    Thin adapter around DataSourceImporter so we can reuse resolve_aircraft()
    without duplicating resolver logic in this script.
    """

    source_name = "BACKFILL"

    def fetch(self):
        return []

    def parse(self, raw_record):
        return None

    def upsert(self, parsed_record):
        return None


def _normalize_source_name(source_name: Optional[str]) -> str:
    if source_name in ("NTSB", "FAA_AIDS", "FAA_SDR"):
        return source_name
    return "other"


def _as_dict(source_data: Any) -> Dict[str, Any]:
    """
    IncidentSource.source_data can be dict/JSON/text depending on ingest path.
    Normalize it to a dict so extraction logic is stable.
    """
    if isinstance(source_data, dict):
        return source_data
    if isinstance(source_data, str):
        try:
            decoded = json.loads(source_data)
            return decoded if isinstance(decoded, dict) else {}
        except Exception:
            return {}
    return {}


def _first_non_empty(*values: Any) -> Optional[str]:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def extract_make_model_from_source(source_data: Any) -> Optional[str]:
    """
    Field order is intentionally strict per PRD:
    1) make_model
    2) make + model
    3) acft_make + acft_model
    """
    payload = _as_dict(source_data)

    make_model = _first_non_empty(payload.get("make_model"))
    if make_model:
        return make_model

    make = _first_non_empty(payload.get("make"))
    model = _first_non_empty(payload.get("model"))
    if make or model:
        combined = " ".join(part for part in (make, model) if part).strip()
        if combined:
            return combined

    acft_make = _first_non_empty(payload.get("acft_make"))
    acft_model = _first_non_empty(payload.get("acft_model"))
    if acft_make or acft_model:
        combined = " ".join(part for part in (acft_make, acft_model) if part).strip()
        if combined:
            return combined

    return None


def _is_boeing_or_airbus(make_model: str) -> bool:
    model = (make_model or "").strip().lower()
    return model.startswith("boeing") or model.startswith("airbus")


def _print_batch_checkpoint(batch_index: int, scanned: int, linked: int, unresolved: int) -> None:
    print(
        f"[checkpoint] batch={batch_index} scanned={scanned} "
        f"linked={linked} unresolved={unresolved}"
    )


def link_orphan_incidents(batch_size: int = 500, dry_run: bool = False) -> Dict[str, Any]:
    """
    Core linking function designed for testability and safe re-runs.

    Idempotency:
    - Scans only incidents with aircraft_id IS NULL.
    - Updates aircraft_id only when resolver returns a valid aircraft id.
    - Safe to run repeatedly; already-linked incidents are skipped by query design.

    Transaction behavior:
    - Non-dry-run: commits every batch_size processed rows.
    - Dry-run: performs full logic but rolls back all writes at the end.
    """
    resolver = BackfillResolver()

    known_aircraft_ids = {
        row_id for (row_id,) in db.session.query(Aircraft.id).all()
    }

    summary = {
        "total_processed": 0,
        "total_newly_linked": 0,
        "total_skipped_already_linked": 0,
        "total_unresolved": 0,
        "total_ignored": 0,
        "aircraft_rows_auto_created": 0,
        "source_counts": Counter({"NTSB": 0, "FAA_AIDS": 0, "FAA_SDR": 0, "other": 0}),
    }

    query = (
        Incident.query
        .filter(Incident.aircraft_id.is_(None))
        .filter(Incident.sources.any())
        .order_by(Incident.id.asc())
    )

    batch_index = 0
    batch_scanned = 0
    batch_linked = 0
    batch_unresolved = 0

    for incident in query.yield_per(batch_size):
        summary["total_processed"] += 1
        batch_scanned += 1

        # Defensive guard: query excludes linked rows, but keep explicit skip accounting.
        if incident.aircraft_id is not None:
            summary["total_skipped_already_linked"] += 1
            continue

        sources = (
            IncidentSource.query
            .filter_by(incident_id=incident.id)
            .order_by(IncidentSource.id.asc())
            .all()
        )

        selected_make_model = None
        selected_source_name = "other"
        for source in sources:
            extracted = extract_make_model_from_source(source.source_data)
            if extracted:
                selected_make_model = extracted
                selected_source_name = _normalize_source_name(source.source_name)
                break

        summary["source_counts"][selected_source_name] += 1

        if not selected_make_model:
            summary["total_ignored"] += 1
        else:
            parsed_record = {"make_model": selected_make_model}
            aircraft_id = resolver.resolve_aircraft(parsed_record)
            if aircraft_id:
                incident.aircraft_id = aircraft_id
                summary["total_newly_linked"] += 1
                batch_linked += 1
                if aircraft_id not in known_aircraft_ids:
                    known_aircraft_ids.add(aircraft_id)
                    summary["aircraft_rows_auto_created"] += 1
            else:
                if _is_boeing_or_airbus(selected_make_model):
                    summary["total_unresolved"] += 1
                    batch_unresolved += 1
                else:
                    summary["total_ignored"] += 1

        if batch_scanned >= batch_size:
            batch_index += 1
            _print_batch_checkpoint(batch_index, batch_scanned, batch_linked, batch_unresolved)
            if not dry_run:
                db.session.commit()
            batch_scanned = 0
            batch_linked = 0
            batch_unresolved = 0

    # Flush trailing batch checkpoint for visibility.
    if batch_scanned > 0:
        batch_index += 1
        _print_batch_checkpoint(batch_index, batch_scanned, batch_linked, batch_unresolved)

    if dry_run:
        # Revert all writes (incident links + auto-created aircraft rows).
        db.session.rollback()
    else:
        db.session.commit()

    return summary


def print_summary(summary: Dict[str, Any], dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "LIVE"
    print("\n=== backfill_aircraft_ids summary ===")
    print(f"mode: {mode}")
    print(f"total_processed: {summary['total_processed']}")
    print(f"total_newly_linked: {summary['total_newly_linked']}")
    print(f"total_skipped_already_linked: {summary['total_skipped_already_linked']}")
    print(f"total_unresolved: {summary['total_unresolved']}")
    print(f"total_ignored: {summary['total_ignored']}")
    print(f"aircraft_rows_auto_created: {summary['aircraft_rows_auto_created']}")
    print("source_counts:")
    print(f"  NTSB: {summary['source_counts'].get('NTSB', 0)}")
    print(f"  FAA_AIDS: {summary['source_counts'].get('FAA_AIDS', 0)}")
    print(f"  FAA_SDR: {summary['source_counts'].get('FAA_SDR', 0)}")
    print(f"  other: {summary['source_counts'].get('other', 0)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill incident.aircraft_id for orphan incidents using resolver logic."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of incidents processed per batch/commit checkpoint.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run linking logic and print what would change without committing.",
    )
    args = parser.parse_args()

    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be a positive integer")

    app = create_app()
    with app.app_context():
        summary = link_orphan_incidents(batch_size=args.batch_size, dry_run=args.dry_run)
        print_summary(summary, dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
