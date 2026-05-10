import argparse
import os
import sys
from typing import Any, Dict

# Add project root so `app` imports work when this script is executed directly.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import Incident, IncidentSource


def migrate_asn_incident_sources(batch_size: int = 500, dry_run: bool = False) -> Dict[str, Any]:
    """
    One-time data migration for ASN source unification.

    Goal:
    - Ensure every ASN-backed incident (incident.asn_url is set) also has an
      IncidentSource row with source_name='ASN'.

    Idempotency guarantees:
    - Only scans incidents with asn_url present and no existing ASN IncidentSource.
    - Re-checks for existing ASN source per incident before insert.
    - Safe to rerun; previously migrated incidents are skipped.

    Transaction behavior:
    - Commits every `batch_size` inserted rows in live mode.
    - Rolls back everything in dry-run mode.
    """
    summary: Dict[str, int] = {
        "total_processed": 0,
        "total_created": 0,
        "total_skipped_existing_asn_source": 0,
        "total_skipped_duplicate_source_record_id": 0,
    }

    # Query only incidents that still require migration work.
    query = (
        Incident.query
        .filter(Incident.asn_url.isnot(None))
        .filter(Incident.asn_url != "")
        .filter(~Incident.sources.any(IncidentSource.source_name == "ASN"))
        .order_by(Incident.id.asc())
    )

    pending_inserts = 0

    for incident in query.yield_per(batch_size):
        summary["total_processed"] += 1
        asn_url = (incident.asn_url or "").strip()
        if not asn_url:
            # Defensive guard for odd whitespace-only values.
            continue

        existing = IncidentSource.query.filter_by(
            incident_id=incident.id,
            source_name="ASN",
        ).first()
        if existing:
            summary["total_skipped_existing_asn_source"] += 1
            continue

        existing_by_url = IncidentSource.query.filter_by(
            source_name="ASN",
            source_record_id=asn_url,
        ).first()
        if existing_by_url:
            # source_record_id is unique per source_name. If another incident already
            # owns this ASN URL, skip safely instead of raising an IntegrityError.
            summary["total_skipped_duplicate_source_record_id"] += 1
            continue

        source = IncidentSource(
            incident_id=incident.id,
            source_name="ASN",
            source_url=asn_url,
            source_record_id=asn_url,
            source_data={"asn_url": asn_url},
            confidence_level="High",
        )
        db.session.add(source)
        summary["total_created"] += 1
        pending_inserts += 1

        if pending_inserts >= batch_size:
            if not dry_run:
                db.session.commit()
            pending_inserts = 0

    if dry_run:
        db.session.rollback()
    else:
        db.session.commit()

    return summary


def print_summary(summary: Dict[str, Any], dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "LIVE"
    print("\n=== migrate_asn_to_incident_source summary ===")
    print(f"mode: {mode}")
    print(f"total_processed: {summary['total_processed']}")
    print(f"total_created: {summary['total_created']}")
    print(f"total_skipped_existing_asn_source: {summary['total_skipped_existing_asn_source']}")
    print(f"total_skipped_duplicate_source_record_id: {summary['total_skipped_duplicate_source_record_id']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate ASN incidents to IncidentSource rows in idempotent batches."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of records per commit batch.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute migration logic but rollback changes before exit.",
    )
    args = parser.parse_args()

    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be a positive integer")

    app = create_app()
    with app.app_context():
        summary = migrate_asn_incident_sources(
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )
        print_summary(summary, dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
