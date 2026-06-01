import argparse
import os
import sys
from typing import Dict, List

# Make project imports work when run from Planning/scripts.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from app import create_app, db
from app.ingestion.importers.base import normalize_make_model_for_storage, validate_series_model_name
from app.models import Aircraft


def clean_series_anomalies(*, dry_run: bool = True, batch_size: int = 500) -> Dict[str, int]:
    """
    One-time cleanup for malformed Aircraft series rows.

    Safe behavior:
    - Dry-run by default (no persistence).
    - Deletes only rows that are both malformed and orphaned (no incidents/variants).
    - Keeps malformed rows that are in use and reports them for manual follow-up.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    summary = {
        "scanned": 0,
        "valid_rows": 0,
        "invalid_rows": 0,
        "deleted_orphan_invalid_rows": 0,
        "kept_linked_invalid_rows": 0,
    }
    pending = 0

    for aircraft in Aircraft.query.order_by(Aircraft.id.asc()).yield_per(batch_size):
        summary["scanned"] += 1
        normalized_model_name = normalize_make_model_for_storage(aircraft.model_name or "")
        is_valid, _reason = validate_series_model_name(normalized_model_name)

        if is_valid:
            summary["valid_rows"] += 1
            continue

        summary["invalid_rows"] += 1
        has_incidents = aircraft.incidents.count() > 0
        has_variants = aircraft.variants.count() > 0
        if has_incidents or has_variants:
            summary["kept_linked_invalid_rows"] += 1
            continue

        db.session.delete(aircraft)
        summary["deleted_orphan_invalid_rows"] += 1
        pending += 1

        if not dry_run and pending >= batch_size:
            db.session.commit()
            pending = 0

    if dry_run:
        db.session.rollback()
    else:
        db.session.commit()

    return summary


def _print_summary(summary: Dict[str, int], dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"=== clean_series_anomalies ({mode}) ===")
    for key, value in summary.items():
        print(f"{key}: {value}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean malformed aircraft series rows from historical data.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist deletions. By default, runs in dry-run mode.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Commit checkpoint size for apply mode.",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        summary = clean_series_anomalies(
            dry_run=not args.apply,
            batch_size=args.batch_size,
        )
        _print_summary(summary, dry_run=not args.apply)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
