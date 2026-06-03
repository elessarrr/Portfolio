#!/usr/bin/env python3
"""Post-import audit for FAA AIDS bulk import (PRD 0007 FR-11)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app
from app.ingestion.faa_aids_post_import_audit import run_post_import_audit

DEFAULT_REPORT = ROOT / "data/logs/faa_aids_post_import_audit.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remediate", action="store_true")
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    app = create_app()
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    with app.app_context():
        report = run_post_import_audit(remediate=args.remediate)

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
