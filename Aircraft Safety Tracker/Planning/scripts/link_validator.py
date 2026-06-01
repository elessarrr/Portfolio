import argparse
import os
import sys
import time
from datetime import datetime
from typing import Dict, Iterable, Optional, Tuple
from urllib.parse import urlparse

# Make project imports work when run from Planning/scripts.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from app import create_app, db
from app.ingestion.importers.base import validate_pdf_url, validate_source_url
from app.models import IncidentSource


def _extract_domain(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        return urlparse(url).netloc.lower() or None
    except Exception:
        return None


def _rate_limit(domain: Optional[str], last_seen: Dict[str, float], delay_seconds: float) -> None:
    if not domain or delay_seconds <= 0:
        return
    now = time.monotonic()
    previous = last_seen.get(domain)
    if previous is not None:
        elapsed = now - previous
        if elapsed < delay_seconds:
            time.sleep(delay_seconds - elapsed)
    last_seen[domain] = time.monotonic()


def iter_sources_for_validation(batch_size: int = 200) -> Iterable[IncidentSource]:
    last_id = 0
    while True:
        batch = (
            IncidentSource.query
            .filter(
                (IncidentSource.source_url.isnot(None))
                | (IncidentSource.report_url.isnot(None))
            )
            .filter(IncidentSource.id > last_id)
            .order_by(IncidentSource.id.asc())
            .limit(batch_size)
            .all()
        )
        if not batch:
            break
        for source in batch:
            yield source
        last_id = batch[-1].id


def _validate_source_record(source: IncidentSource) -> Tuple[bool, Optional[int], Optional[str]]:
    source_valid, source_status, source_error = validate_source_url(source.source_url)
    report_valid, report_status, report_error = validate_pdf_url(source.report_url)

    has_any_valid = source_valid or report_valid
    if has_any_valid:
        return True, source_status if source_valid else report_status, None
    return False, source_status if source_status is not None else report_status, source_error or report_error


def run_link_validator(
    *,
    dry_run: bool = True,
    batch_size: int = 200,
    per_domain_delay_seconds: float = 0.2,
    max_records: Optional[int] = None,
) -> Dict[str, int]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    if per_domain_delay_seconds < 0:
        raise ValueError("per_domain_delay_seconds must be non-negative")

    summary = {
        "processed": 0,
        "active_set_true": 0,
        "active_set_false": 0,
        "unchanged": 0,
    }
    pending = 0
    domain_last_seen: Dict[str, float] = {}

    for source in iter_sources_for_validation(batch_size=batch_size):
        domain = _extract_domain(source.source_url) or _extract_domain(source.report_url)
        _rate_limit(domain, domain_last_seen, per_domain_delay_seconds)

        is_active, _status, _error = _validate_source_record(source)
        previous_state = bool(source.is_active)

        if is_active != previous_state:
            if is_active:
                summary["active_set_true"] += 1
            else:
                summary["active_set_false"] += 1
            if not dry_run:
                source.is_active = is_active
                source.last_validated_at = datetime.utcnow()
                db.session.add(source)
                pending += 1
        else:
            summary["unchanged"] += 1
            if not dry_run:
                source.last_validated_at = datetime.utcnow()
                db.session.add(source)
                pending += 1

        summary["processed"] += 1
        if max_records and summary["processed"] >= max_records:
            break

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
    print(f"=== link_validator ({mode}) ===")
    for key, value in summary.items():
        print(f"{key}: {value}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate incident source links and soft-flag dead links via incident_source.is_active.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist updates. Default mode is dry-run.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Number of records per database commit checkpoint.",
    )
    parser.add_argument(
        "--per-domain-delay-seconds",
        type=float,
        default=0.2,
        help="Delay between validations for the same domain (rate limiting).",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Optional processing cap for quick manual verification.",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        summary = run_link_validator(
            dry_run=not args.apply,
            batch_size=args.batch_size,
            per_domain_delay_seconds=args.per_domain_delay_seconds,
            max_records=args.max_records,
        )
        _print_summary(summary, dry_run=not args.apply)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
