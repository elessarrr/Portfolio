#!/usr/bin/env python3
"""Bootstrap empty Aircraft catalog pages for create_approved mapping targets (FR-20.0)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.ingestion.ntsb_mapping import (
    bootstrap_create_approved_pages,
    load_ntsb_make_model_mapping,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAPPING = ROOT / "data/config/ntsb_make_model_to_aircraft.jsonl"
DEFAULT_REPORT_OUT = ROOT / "data/logs/ntsb_bootstrap_create_approved.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mapping",
        type=Path,
        default=DEFAULT_MAPPING,
        help="Approved ntsb_make_model_to_aircraft.jsonl gate file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report pages that would be created without writing to DB.",
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=DEFAULT_REPORT_OUT,
        help="JSON report path (default: data/logs/ntsb_bootstrap_create_approved.json).",
    )
    args = parser.parse_args()

    mapping = load_ntsb_make_model_mapping(args.mapping)
    database_url = os.environ.get("DATABASE_URL")
    app = create_app()
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    with app.app_context():
        report = bootstrap_create_approved_pages(mapping, dry_run=args.dry_run)
        report["mapping_path"] = str(args.mapping)

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    with args.report_out.open("w") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    summary = {
        "dry_run": report["dry_run"],
        "target_count": report["target_count"],
        "created_count": report["created_count"],
        "already_existed_count": report["already_existed_count"],
        "report_out": str(args.report_out),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
