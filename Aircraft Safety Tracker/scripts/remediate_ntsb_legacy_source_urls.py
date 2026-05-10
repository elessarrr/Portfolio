#!/usr/bin/env python
"""
Comments for context:
- Project context: PRD-0019 source-link remediation found that NTSB `source_url`
  values were uniformly set to CAROL detail pages, even for historical accidents
  that are served by the legacy brief system.
- Problem this script solves: perform a one-time, idempotent rewrite of affected
  NTSB `IncidentSource.source_url` rows using a vetted mapping file that resolves
  identifiers (`cm_ntsbNum` / `cm_mkey`) to legacy `ev_id`.
- Safety model:
  1) Dry-run by default (no writes unless `--apply` is passed).
  2) Rewrites only rows that currently point to CAROL details.
  3) Skips rows with no mapping, malformed mapping, or already-correct URL.
"""

import argparse
import csv
import os
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Add project root so `app` imports work when this script is executed directly.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import IncidentSource

CAROL_PREFIX = "https://carol.ntsb.gov/investigations/detail/"
LEGACY_TEMPLATE = "https://www.ntsb.gov/Pages/brief.aspx?ev_id={ev_id}&key=0"


def _clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_ev_id(value: Any) -> Optional[str]:
    text = _clean_text(value)
    if not text:
        return None
    if not text.isdigit():
        return None
    return text


def _candidate_value(row: Dict[str, str], keys: List[str]) -> Optional[str]:
    for key in keys:
        if key in row:
            value = _clean_text(row.get(key))
            if value:
                return value
    return None


def load_legacy_mapping(mapping_csv_path: str) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, int]]:
    """
    Load mapping rows from CSV into lookup dictionaries.

    Supported headers for keys:
    - NTSB number: `cm_ntsbNum`, `source_record_id`, `ntsb_number`
    - MKey: `cm_mkey`, `mkey`
    - Legacy ID: `ev_id`, `legacy_ev_id`
    """
    mapping_by_ntsb: Dict[str, str] = {}
    mapping_by_mkey: Dict[str, str] = {}
    stats = {
        "rows_read": 0,
        "rows_usable": 0,
        "rows_skipped_missing_ev_id": 0,
        "rows_skipped_bad_ev_id": 0,
        "rows_skipped_missing_keys": 0,
        "duplicate_ntsb_keys": 0,
        "duplicate_mkey_keys": 0,
    }

    with open(mapping_csv_path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            stats["rows_read"] += 1

            ntsb_num = _candidate_value(row, ["cm_ntsbNum", "source_record_id", "ntsb_number"])
            mkey = _candidate_value(row, ["cm_mkey", "mkey"])
            raw_ev_id = _candidate_value(row, ["ev_id", "legacy_ev_id"])

            if raw_ev_id is None:
                stats["rows_skipped_missing_ev_id"] += 1
                continue

            ev_id = _normalize_ev_id(raw_ev_id)
            if ev_id is None:
                stats["rows_skipped_bad_ev_id"] += 1
                continue

            if not ntsb_num and not mkey:
                stats["rows_skipped_missing_keys"] += 1
                continue

            stats["rows_usable"] += 1

            if ntsb_num:
                if ntsb_num in mapping_by_ntsb and mapping_by_ntsb[ntsb_num] != ev_id:
                    stats["duplicate_ntsb_keys"] += 1
                mapping_by_ntsb[ntsb_num] = ev_id

            if mkey:
                if mkey in mapping_by_mkey and mapping_by_mkey[mkey] != ev_id:
                    stats["duplicate_mkey_keys"] += 1
                mapping_by_mkey[mkey] = ev_id

    return mapping_by_ntsb, mapping_by_mkey, stats


def iter_ntsb_sources(batch_size: int) -> Iterable[List[IncidentSource]]:
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


def _extract_keys(row: IncidentSource) -> Tuple[Optional[str], Optional[str]]:
    payload = row.source_data if isinstance(row.source_data, dict) else {}
    ntsb_num = _clean_text(row.source_record_id) or _clean_text(payload.get("cm_ntsbNum"))
    mkey = _clean_text(payload.get("cm_mkey"))
    return ntsb_num, mkey


def _legacy_url(ev_id: str) -> str:
    return LEGACY_TEMPLATE.format(ev_id=ev_id)


def remediate_ntsb_source_urls(
    mapping_by_ntsb: Dict[str, str],
    mapping_by_mkey: Dict[str, str],
    batch_size: int,
    apply_changes: bool,
) -> Dict[str, int]:
    summary = {
        "rows_scanned": 0,
        "rows_updated": 0,
        "rows_skipped_already_legacy": 0,
        "rows_skipped_not_carol": 0,
        "rows_skipped_no_mapping": 0,
        "rows_skipped_bad_ev_id": 0,
        "rows_with_mapping_by_ntsb": 0,
        "rows_with_mapping_by_mkey": 0,
        "batches": 0,
    }

    for batch in iter_ntsb_sources(batch_size=batch_size):
        summary["batches"] += 1

        for row in batch:
            summary["rows_scanned"] += 1
            current_url = _clean_text(row.source_url) or ""

            if current_url.startswith("https://www.ntsb.gov/Pages/brief.aspx?ev_id="):
                summary["rows_skipped_already_legacy"] += 1
                continue

            if not current_url.startswith(CAROL_PREFIX):
                summary["rows_skipped_not_carol"] += 1
                continue

            ntsb_num, mkey = _extract_keys(row)
            ev_id = None

            if ntsb_num and ntsb_num in mapping_by_ntsb:
                ev_id = mapping_by_ntsb[ntsb_num]
                summary["rows_with_mapping_by_ntsb"] += 1
            elif mkey and mkey in mapping_by_mkey:
                ev_id = mapping_by_mkey[mkey]
                summary["rows_with_mapping_by_mkey"] += 1

            if ev_id is None:
                summary["rows_skipped_no_mapping"] += 1
                continue

            ev_id = _normalize_ev_id(ev_id)
            if ev_id is None:
                summary["rows_skipped_bad_ev_id"] += 1
                continue

            target_url = _legacy_url(ev_id)
            if target_url == current_url:
                summary["rows_skipped_already_legacy"] += 1
                continue

            if apply_changes:
                row.source_url = target_url
                db.session.add(row)

            summary["rows_updated"] += 1

        if apply_changes:
            db.session.commit()

        mode = "[APPLY ]" if apply_changes else "[DRYRUN]"
        print(
            f"{mode} batch={summary['batches']} "
            f"scanned={summary['rows_scanned']} "
            f"updated={summary['rows_updated']} "
            f"no_mapping={summary['rows_skipped_no_mapping']}"
        )

    if not apply_changes:
        db.session.rollback()

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "One-time remediation for NTSB source_url routing. "
            "Default mode is dry-run; use --apply to persist changes."
        )
    )
    parser.add_argument(
        "--mapping-csv",
        required=True,
        help=(
            "Absolute or relative path to CSV mapping file with keys "
            "(cm_ntsbNum/source_record_id and/or cm_mkey) plus ev_id."
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of NTSB rows per DB batch (default: 500).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist URL updates. If omitted, script runs in dry-run mode.",
    )
    args = parser.parse_args()

    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be a positive integer")

    mapping_csv_path = os.path.abspath(args.mapping_csv)
    if not os.path.exists(mapping_csv_path):
        raise SystemExit(f"--mapping-csv not found: {mapping_csv_path}")

    mapping_by_ntsb, mapping_by_mkey, mapping_stats = load_legacy_mapping(mapping_csv_path)

    app = create_app()
    with app.app_context():
        summary = remediate_ntsb_source_urls(
            mapping_by_ntsb=mapping_by_ntsb,
            mapping_by_mkey=mapping_by_mkey,
            batch_size=args.batch_size,
            apply_changes=args.apply,
        )

    mode = "APPLY" if args.apply else "DRY-RUN"
    print("\n=== NTSB legacy source_url remediation summary ===")
    print(f"mode: {mode}")
    print(f"mapping_csv: {mapping_csv_path}")
    print(f"mapping_rows_read: {mapping_stats['rows_read']}")
    print(f"mapping_rows_usable: {mapping_stats['rows_usable']}")
    print(f"mapping_rows_skipped_missing_ev_id: {mapping_stats['rows_skipped_missing_ev_id']}")
    print(f"mapping_rows_skipped_bad_ev_id: {mapping_stats['rows_skipped_bad_ev_id']}")
    print(f"mapping_rows_skipped_missing_keys: {mapping_stats['rows_skipped_missing_keys']}")
    print(f"mapping_duplicate_ntsb_keys: {mapping_stats['duplicate_ntsb_keys']}")
    print(f"mapping_duplicate_mkey_keys: {mapping_stats['duplicate_mkey_keys']}")
    print(f"rows_scanned: {summary['rows_scanned']}")
    print(f"rows_updated: {summary['rows_updated']}")
    print(f"rows_skipped_already_legacy: {summary['rows_skipped_already_legacy']}")
    print(f"rows_skipped_not_carol: {summary['rows_skipped_not_carol']}")
    print(f"rows_skipped_no_mapping: {summary['rows_skipped_no_mapping']}")
    print(f"rows_skipped_bad_ev_id: {summary['rows_skipped_bad_ev_id']}")
    print(f"rows_with_mapping_by_ntsb: {summary['rows_with_mapping_by_ntsb']}")
    print(f"rows_with_mapping_by_mkey: {summary['rows_with_mapping_by_mkey']}")
    print(f"batches_processed: {summary['batches']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
