#!/usr/bin/env python3
"""Recompute asrs_report.aircraft_id from stored make/model raw strings.

Use after matcher rule changes — avoids re-downloading the HF dataset.

Examples:
  PYTHONPATH=. python scripts/remap_asrs_aircraft_ids.py --dry-run
  PYTHONPATH=. python scripts/remap_asrs_aircraft_ids.py --apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.ingestion.asrs_import import require_asrs_table
from app.ingestion.asrs_remap import format_remap_stats, remap_asrs_aircraft_ids


def main() -> int:
    parser = argparse.ArgumentParser(description="Recompute ASRS aircraft_id assignments")
    parser.add_argument("--apply", action="store_true", help="Write changes to DB")
    parser.add_argument("--dry-run", action="store_true", help="Explicit dry-run (default)")
    parser.add_argument(
        "--overrides",
        type=Path,
        default=ROOT / "data/config/asrs_make_model_to_aircraft.jsonl",
    )
    args = parser.parse_args()
    if args.apply and args.dry_run:
        parser.error("Use only one of --apply or --dry-run")

    apply = args.apply
    app = create_app("development")
    with app.app_context():
        require_asrs_table()
        stats = remap_asrs_aircraft_ids(apply=apply, overrides_path=args.overrides)
        print(format_remap_stats(stats, apply=apply))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
