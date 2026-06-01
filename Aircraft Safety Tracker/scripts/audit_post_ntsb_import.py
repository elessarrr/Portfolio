#!/usr/bin/env python3
"""Post-import duplicate audit after NTSB bulk import (FR-22)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.ingestion.ntsb_post_import_audit import (
    audit_ntsb_vs_asn_duplicates,
    remediate_incident_duplicates,
    run_post_import_audit,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "data/logs/ntsb_post_import_audit.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--window-days",
        type=int,
        default=7,
        help="ASN candidate search window (default: 7, matches FR-4).",
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=DEFAULT_REPORT,
        help="JSON report path.",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=25,
        help="Max incident-duplicate rows in report payload.",
    )
    parser.add_argument(
        "--remediate",
        action="store_true",
        help="Delete NTSB incidents flagged as ASN duplicates, then re-audit.",
    )
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    app = create_app()
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    with app.app_context():
        report = run_post_import_audit(
            window_days=args.window_days,
            max_incident_duplicate_samples=args.max_samples,
        )
        if args.remediate and report["incident_duplicates_total"] > 0:
            remediation = remediate_incident_duplicates(
                audit_ntsb_vs_asn_duplicates(window_days=args.window_days)
            )
            report["remediation"] = remediation
            report = run_post_import_audit(
                window_days=args.window_days,
                max_incident_duplicate_samples=args.max_samples,
            )
            report["remediation"] = remediation

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    with args.report_out.open("w") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
