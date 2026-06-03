#!/usr/bin/env python3
"""ASN dedupe pass for FAA AIDS Boeing/Airbus export (PRD 0007 FR-6)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app
from app.ingestion.faa_aids_dedupe import (
    load_faa_jsonl,
    run_faa_dedupe_pass,
    write_audit_jsonl,
)
from app.ingestion.faa_aids_mapping import load_faa_aids_make_model_mapping

DEFAULT_RAW = ROOT / "data/raw/faa_aids_boeing_airbus.jsonl"
DEFAULT_MAPPING = ROOT / "data/config/faa_aids_make_model_to_aircraft.jsonl"
DEFAULT_OUT = ROOT / "data/logs/faa_aids_dedupe_audit.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--window-days", type=int, default=2)
    args = parser.parse_args()

    rows = load_faa_jsonl(args.input)
    mapping = load_faa_aids_make_model_mapping(args.mapping)

    database_url = os.environ.get("DATABASE_URL")
    app = create_app()
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    with app.app_context():
        audit_rows, report = run_faa_dedupe_pass(
            rows, mapping, window_days=args.window_days
        )

    write_audit_jsonl(args.out, audit_rows)
    summary = {**report, "output": str(args.out), "mapping": str(args.mapping)}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
