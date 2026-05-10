#!/usr/bin/env python
"""
Backfill script: rewrite NTSB IncidentSource.source_url to canonical docket URL.

URL strategy (matches PRD-0014 task 4 decision):
  Canonical: https://data.ntsb.gov/Docket/?NTSBNumber={ntsb_number}

Identifier priority:
  1) source.source_record_id
  2) source.source_data['cm_ntsbNum']

Update policy:
  - Write only when a better canonical URL can be built AND differs from current.
  - --dry-run mode: scan and report without writing.
  - Always idempotent (no duplicate rows, no partial writes).

Usage:
  python scripts/backfill_ntsb_source_urls.py
  python scripts/backfill_ntsb_source_urls.py --dry-run
  python scripts/backfill_ntsb_source_urls.py --batch-size 1000
  python scripts/backfill_ntsb_source_urls.py --dry-run --batch-size 500
"""

import argparse
import os
import sys
from typing import Any, Dict, Iterable, List, Optional

# Add project root to path so "app" imports work when running as a script.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import IncidentSource


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _first_non_empty(*values: Any) -> Optional[str]:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def build_canonical_ntsb_details_url(source: IncidentSource) -> Optional[str]:
    """
    Recompute canonical NTSB details URL from persisted identifiers.

    Priority:
    1) `source.source_record_id`
    2) `source.source_data['cm_ntsbNum']`
    """
    payload = _as_dict(source.source_data)
    ntsb_number = _first_non_empty(source.source_record_id, payload.get("cm_ntsbNum"))
    if not ntsb_number:
        return None
    return f"https://data.ntsb.gov/Docket/?NTSBNumber={ntsb_number}"


def iter_ntsb_sources_in_batches(batch_size: int = 500) -> Iterable[List[IncidentSource]]:
    """
    Yield NTSB IncidentSource rows in deterministic id-ordered batches.

    Why this exists:
    - Historical NTSB rows are large in volume (~82k rows).
    - Loading all rows in memory at once is risky and slow.
    - The backfill workflow needs predictable, restart-safe chunking.
    - After each batch we commit, so a interrupted run can resume safely.

    Id ordering ensures the same rows are always in the same batch position
    regardless of when the script is run.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be a positive integer")

    last_id = 0
    while True:
        batch = (
            IncidentSource.query
            .filter(IncidentSource.source_name == "NTSB")
            .filter(IncidentSource.id > last_id)
            .order_by(IncidentSource.id.asc())
            .limit(batch_size)
            .all()
        )
        if not batch:
            break

        yield batch
        last_id = batch[-1].id


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Rewrite NTSB IncidentSource.source_url to canonical docket URL.\n"
            "Write mode: updates source_url when a better canonical URL is buildable.\n"
            "Dry-run mode: scans and reports without writing."
        )
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of NTSB rows per batch (default: 500).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Scan and report what would be updated without writing to the database. "
            "Recommended for first run to preview impact."
        ),
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        total = 0
        batches = 0
        canonical_buildable = 0
        canonical_unbuildable = 0
        rows_updated = 0
        rows_skipped = 0

        for batch in iter_ntsb_sources_in_batches(batch_size=args.batch_size):
            batches += 1
            total += len(batch)

            for row in batch:
                canonical_url = build_canonical_ntsb_details_url(row)
                current_url = (row.source_url or "").strip()

                if not canonical_url:
                    # Can't build a canonical URL — leave as-is.
                    canonical_unbuildable += 1
                    rows_skipped += 1
                    continue

                canonical_unbuildable  # no-op; kept for scan count

                if canonical_url == current_url:
                    # Already canonical — nothing to do.
                    canonical_buildable += 1
                    rows_skipped += 1
                    continue

                # canonical_url differs from current_url — apply the update.
                canonical_buildable += 1

                if not args.dry_run:
                    row.source_url = canonical_url
                    db.session.add(row)

                rows_updated += 1

            if not args.dry_run:
                db.session.commit()

            mode = "[DRY-RUN]" if args.dry_run else "[COMMIT ]"
            print(
                f"{mode} batch={batches} scanned={total} "
                f"updated={rows_updated} skipped={rows_skipped}"
            )

        print("\n=== NTSB source_url backfill summary ===")
        print(f"mode: {'DRY-RUN' if args.dry_run else 'COMMIT'}")
        print(f"batches_scanned:   {batches}")
        print(f"rows_scanned:     {total}")
        print(f"canonical_found:  {canonical_buildable}")
        print(f"unbuildable:      {canonical_unbuildable}")
        print(f"rows_updated:     {rows_updated}")
        print(f"rows_skipped:     {rows_skipped}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
