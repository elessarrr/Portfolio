#!/usr/bin/env python3
"""Bootstrap create_approved aircraft pages for FAA AIDS mapping (PRD 0007 FR-8)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app
from app.ingestion.faa_aids_mapping import (
    bootstrap_create_approved_pages,
    load_faa_aids_make_model_mapping,
)

DEFAULT_MAPPING = ROOT / "data/config/faa_aids_make_model_to_aircraft.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--report-out",
        type=Path,
        default=ROOT / "data/logs/faa_aids_bootstrap_create_approved.json",
    )
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    app = create_app()
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    mapping = load_faa_aids_make_model_mapping(args.mapping)
    with app.app_context():
        report = bootstrap_create_approved_pages(mapping, dry_run=args.dry_run)

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
