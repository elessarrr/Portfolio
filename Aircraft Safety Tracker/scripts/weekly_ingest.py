#!/usr/bin/env python3
"""Weekly ingest entrypoint (PRD 0012) — run by the GitHub Actions schedule.

Sets up the Flask app context (using DATABASE_URL from the environment, e.g. the
Railway Postgres connection string set as a GitHub Actions secret) and runs the
orchestrator in `app.ingestion.weekly_ingest`.

Usage:
    PYTHONPATH=. python scripts/weekly_ingest.py
"""

from __future__ import annotations

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


def main() -> int:
    from app import create_app
    from app.ingestion.weekly_ingest import run_ingest

    config_name = os.environ.get("FLASK_CONFIG", "production")
    app = create_app(config_name)
    with app.app_context():
        result = run_ingest()

    print(json.dumps(result, default=str, indent=2))
    # Non-zero exit on partial so the workflow surfaces a warning, but the DB
    # state is already committed and the next run will retry skipped sources.
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
