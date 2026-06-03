#!/usr/bin/env python3
"""Audit FAA AIDS rows that duplicate ASN or NTSB baseline incidents (PRD 0009 FR-0)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_AUDIT = ROOT / "data/logs/faa_aids_baseline_overlap_audit.jsonl"
DEFAULT_SUMMARY = ROOT / "data/logs/faa_aids_baseline_overlap_summary.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-out", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--window-days", type=int, default=2)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Set is_active=False on covered FAA sources (default: report only)",
    )
    parser.add_argument(
        "--rebuild-retry4-in",
        type=Path,
        metavar="MERGED_JSONL",
        help="After audit, write retry4 input from merged brief audit (excludes overlap rows)",
    )
    parser.add_argument(
        "--retry4-out",
        type=Path,
        default=ROOT / "data/logs/faa_aids_brief_retry4_in_2026-06-02.jsonl",
    )
    args = parser.parse_args()

    from app import create_app
    from app.ingestion.faa_baseline_overlap import (
        audit_faa_baseline_overlap,
        rebuild_retry4_input_jsonl,
        remediate_baseline_overlap,
    )
    from app.models import IncidentSource

    database_url = os.environ.get("DATABASE_URL")
    app = create_app()
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    with app.app_context():
        rows, counts = audit_faa_baseline_overlap(window_days=args.window_days)
        remediated = 0
        if args.apply and rows:
            print(f"Applying remediation to {len(rows)} covered FAA sources...")
            remediated = remediate_baseline_overlap(rows)
            counts["faa_remediated"] = remediated
            active_after = counts["faa_active_scanned"] - remediated
            counts["faa_still_active_after_remediate"] = active_after

        args.audit_out.parent.mkdir(parents=True, exist_ok=True)
        with args.audit_out.open("w", encoding="utf-8") as f:
            f.write(f"# FAA baseline overlap — {date.today().isoformat()} — n={len(rows)}\n")
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        summary = {
            "audit_date": date.today().isoformat(),
            "audit_out": str(args.audit_out),
            "apply": args.apply,
            **counts,
        }
        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        args.summary_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        if args.rebuild_retry4_in:
            active_ids = {
                str(s.source_record_id)
                for s in IncidentSource.query.filter_by(source_name="FAA_AIDS")
                .filter(IncidentSource.is_active.isnot(False))
                .all()
                if s.source_record_id
            }
            n = rebuild_retry4_input_jsonl(
                merged_audit_path=args.rebuild_retry4_in,
                overlap_audit_path=args.audit_out,
                output_path=args.retry4_out,
                active_source_ids=active_ids,
            )
            summary["retry4_input_rows"] = n
            summary["retry4_input_path"] = str(args.retry4_out)

    print(json.dumps(summary, indent=2))
    if not args.apply and rows:
        print("\nDry-run only. Re-run with --apply to deactivate covered FAA sources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
