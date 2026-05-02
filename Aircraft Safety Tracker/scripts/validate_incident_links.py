#!/usr/bin/env python
"""
Weekly link re-validation job for PRD-0016 (NTSB Link Reliability).

Scans all IncidentSource records where source_url or report_url is non-null and
last_validated_at is null or older than 7 days. Validates each URL and updates the
database based on the result. Logs all outcomes to the LinkValidationLog table.

Validation rules (Section 9.1):
  - source_url broken [404/410] + report_url valid → promote report_url to source_url
  - Both broken → set both to null
  - source_url valid → no change
  - Update last_validated_at regardless of outcome

Usage:
  python scripts/validate_incident_links.py
  python scripts/validate_incident_links.py --dry-run
  python scripts/validate_incident_links.py --batch-size 100
  python scripts/validate_incident_links.py --max-records 1000
  python scripts/validate_incident_links.py --dry-run --batch-size 50

Cron schedule (recommended):
  0 2 * * 0 PYTHONPATH=/path/to/project /path/to/venv/bin/python /path/to/project/scripts/validate_incident_links.py
  (Runs every Sunday at 02:00 UTC)
"""

import argparse
import os
import sys
import time
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urlparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.ingestion.importers.base import validate_source_url, validate_pdf_url
from app.models import IncidentSource, LinkValidationLog


BATCH_SIZE = 100
STALE_DAYS = 7
LINK_BREAK_ALERT_ENABLED = os.environ.get("LINK_BREAK_ALERT_ENABLED", "").lower() in ("1", "true", "yes")
DOMAIN_DELAY = 0.3  # seconds between requests to the same domain

_domain_last_seen = {}


def _rate_limit(url: str) -> None:
    """Throttle requests per-domain to avoid IP bans."""
    if not url:
        return
    try:
        domain = urlparse(url).netloc.lower()
    except Exception:
        return
    now = time.monotonic()
    prev = _domain_last_seen.get(domain)
    if prev is not None:
        elapsed = now - prev
        if elapsed < DOMAIN_DELAY:
            time.sleep(DOMAIN_DELAY - elapsed)
    _domain_last_seen[domain] = time.monotonic()


def iter_stale_sources(batch_size: int = BATCH_SIZE, source_id: Optional[int] = None):
    """
    Yield IncidentSource records that need re-validation.

    Scope:
    - If source_id is provided, yields only that specific record (ignoring stale checks).
    - Otherwise:
      - source_url or report_url is non-null
      - last_validated_at is null OR older than STALE_DAYS days
      - Ordered by id for deterministic, restart-safe batching
    """
    if source_id is not None:
        record = IncidentSource.query.get(source_id)
        if record:
            yield [record]
        return

    cutoff = datetime.utcnow() - timedelta(days=STALE_DAYS)
    last_id = 0

    while True:
        batch = (
            IncidentSource.query
            .filter(
                (IncidentSource.source_url.isnot(None))
                | (IncidentSource.report_url.isnot(None))
            )
            .filter(
                (IncidentSource.last_validated_at.is_(None))
                | (IncidentSource.last_validated_at < cutoff)
            )
            .filter(IncidentSource.id > last_id)
            .order_by(IncidentSource.id.asc())
            .limit(batch_size)
            .all()
        )
        if not batch:
            break
        yield batch
        last_id = batch[-1].id


def _validate_primary_source_url(source: IncidentSource):
    """
    Validate source_url with source-aware rules.

    For NTSB rows, `source_url` commonly points to CAROL pages that can return
    HTTP 200 even when investigation content is unavailable. To avoid false
    positives, we intentionally skip NTSB CAROL source_url validation as a validity
    signal and rely on report_url flow instead.
    """
    is_ntsb = (source.source_name or "").upper() == "NTSB"
    if is_ntsb and source.source_url and "carol.ntsb.gov" in source.source_url.lower():
        return False, None, "skipped_ntsb_carol_source_url"

    _rate_limit(source.source_url)
    return validate_source_url(source.source_url)


def validate_and_update(source: IncidentSource, dry_run: bool = False) -> LinkValidationLog:
    """
    Validate source_url and report_url for a single IncidentSource record.

    Returns a LinkValidationLog entry describing the outcome. Does NOT commit
    to the database — caller is responsible for batching commits.

    Validation pipeline (Section 9.1):
    - Non-NTSB:
      1. Validate source_url via HEAD request.
      2. If source_url broken and report_url exists → validate report_url.
         If report_url valid → promote it to source_url, clear report_url.
      3. If both broken → set both to null.
    - NTSB:
      1. Skip source_url validity signal (CAROL false-positive guard).
      2. Validate report_url as the primary signal when present.
      3. If report_url is absent → do not mutate URLs; only stamp validation time.
      4. If report_url is broken → set both links to null.
    - Always update last_validated_at.
    - Log result to LinkValidationLog.
    """
    old_source_url = source.source_url
    old_report_url = source.report_url

    source_url_valid, source_http, source_err = _validate_primary_source_url(source)
    _rate_limit(source.report_url)
    pdf_url_valid, pdf_http, pdf_err = validate_pdf_url(source.report_url)

    new_source_url = source.source_url
    new_report_url = source.report_url
    result = "unchanged"

    is_ntsb = (source.source_name or "").upper() == "NTSB"
    is_docket_url = source.source_url and "data.ntsb.gov/docket/" in source.source_url.lower()

    if is_ntsb:
        if is_docket_url:
            if not source_url_valid:
                new_source_url = None
                new_report_url = None
                result = "broken"
            elif source.report_url and not pdf_url_valid:
                new_source_url = None
                new_report_url = None
                result = "broken"
            else:
                result = "valid"
        elif not source.report_url:
            # No report_url to validate for NTSB CAROL; keep links unchanged and only
            # advance last_validated_at so CAROL source_url does not force a break.
            result = "unchanged"
        elif pdf_url_valid:
            result = "valid"
        else:
            new_source_url = None
            new_report_url = None
            result = "broken"
    elif source_url_valid:
        result = "valid"
    elif source.source_url and source.report_url and pdf_url_valid:
        new_source_url = source.report_url
        new_report_url = None
        result = "updated"
    else:
        new_source_url = None
        new_report_url = None
        result = "broken"

    log_entry = LinkValidationLog(
        incident_source_id=source.id,
        validated_at=datetime.utcnow(),
        old_source_url=old_source_url,
        old_report_url=old_report_url,
        new_source_url=new_source_url,
        new_report_url=new_report_url,
        result=result,
        http_status=(
            pdf_http if (is_ntsb and result == "valid")
            else (source_http if result in ("valid", "broken") else (pdf_http if pdf_url_valid else None))
        ),
        error_detail=(
            (source_err if (not source_url_valid and not is_ntsb) else None)
            or (pdf_err if result == "broken" and not pdf_url_valid else None)
            or ("ntsb_report_url_missing_skip" if is_ntsb and not source.report_url else None)
        ),
    )

    if not dry_run:
        source.source_url = new_source_url
        source.report_url = new_report_url
        if result == "broken":
            source.is_active = False
        elif result in ("valid", "updated"):
            source.is_active = True
        source.last_validated_at = datetime.utcnow()
        db.session.add(source)
        db.session.add(log_entry)

    return log_entry


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Re-validate NTSB/FAA/ASN source URLs in IncidentSource table.\n"
            "Write mode: updates URLs and logs outcomes to LinkValidationLog.\n"
            "Dry-run mode: validates and reports without writing."
        )
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Number of rows per batch (default: {BATCH_SIZE}).",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Stop after processing this many records (useful for quick smoke test).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report without writing to the database.",
    )
    parser.add_argument(
        "--id",
        type=int,
        default=None,
        help="Target a specific IncidentSource ID for validation.",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        total = 0
        batches = 0
        counters = {"valid": 0, "broken": 0, "updated": 0, "unchanged": 0}

        for batch in iter_stale_sources(batch_size=args.batch_size, source_id=args.id):
            batches += 1

            for source in batch:
                log_entry = validate_and_update(source, dry_run=args.dry_run)
                counters[log_entry.result] += 1
                total += 1

                if args.max_records and total >= args.max_records:
                    break

            if not args.dry_run:
                db.session.commit()

            mode = "[DRY-RUN]" if args.dry_run else "[COMMIT ]"
            print(
                f"{mode} batch={batches} scanned={total} "
                f"valid={counters['valid']} broken={counters['broken']} "
                f"updated={counters['updated']} unchanged={counters['unchanged']}"
            )

            if args.max_records and total >= args.max_records:
                break

        print("\n=== Link validation summary ===")
        print(f"mode: {'DRY-RUN' if args.dry_run else 'COMMIT'}")
        print(f"batches_scanned:  {batches}")
        print(f"records_processed: {total}")
        print(f"valid:   {counters['valid']}")
        print(f"broken:  {counters['broken']}")
        print(f"updated: {counters['updated']}")
        print(f"unchanged: {counters['unchanged']}")
        if LINK_BREAK_ALERT_ENABLED:
            print(f"alert: LINK_BREAK_ALERT_ENABLED=true — link break notifications are enabled")
        else:
            print(f"alert: LINK_BREAK_ALERT_ENABLED not set — no break notifications will be sent")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
