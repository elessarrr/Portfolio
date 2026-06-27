#!/usr/bin/env python3
"""Weekly ingest entrypoint (PRD 0012).

Sets up the Flask app context (using DATABASE_URL from the environment, e.g. the
Railway Postgres connection string set as a GitHub Actions secret) and runs the
orchestrator in `app.ingestion.weekly_ingest`.

Source selection:
    NTSB runs in the cloud (data.ntsb.gov is reachable from GitHub Actions).
    ASN (aviation-safety.net) 403s datacenter IPs, so it is NOT in the cron —
    refresh it locally from a residential IP with `--with-asn` / `--asn-only`.

Usage:
    # GitHub Actions cron (NTSB only):
    PYTHONPATH=. python scripts/weekly_ingest.py

    # Local ASN refresh (run from home, writes to the same DATABASE_URL):
    PYTHONPATH=. python scripts/weekly_ingest.py --asn-only
    PYTHONPATH=. python scripts/weekly_ingest.py --with-asn   # NTSB + ASN
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("weekly_ingest")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the weekly ingest.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--with-asn",
        action="store_true",
        help="Also scrape ASN (run locally only — ASN 403s cloud IPs).",
    )
    group.add_argument(
        "--asn-only",
        action="store_true",
        help="Scrape ASN only, skip NTSB (local residential-IP refresh).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    from app import create_app
    from app.ingestion.weekly_ingest import run_ingest

    include_ntsb = not args.asn_only
    include_asn = args.with_asn or args.asn_only

    config_name = os.environ.get("FLASK_CONFIG", "production")
    app = create_app(config_name)
    with app.app_context():
        result = run_ingest(include_ntsb=include_ntsb, include_asn=include_asn)

    print(json.dumps(result, default=str, indent=2))
    # Non-zero exit on partial so the workflow surfaces a warning, but the DB
    # state is already committed and the next run will retry skipped sources.
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
