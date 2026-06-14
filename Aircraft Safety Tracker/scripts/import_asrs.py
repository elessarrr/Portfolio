#!/usr/bin/env python3
"""Import ASRS reports from Hugging Face or DBOL CSV exports.

Examples:
  pip install -r requirements-ingest.txt
  PYTHONPATH=. python scripts/import_asrs.py --source huggingface --dry-run
  PYTHONPATH=. python scripts/import_asrs.py --source huggingface --apply
  PYTHONPATH=. python scripts/import_asrs.py --csv data/raw/asrs/export.csv --apply
  PYTHONPATH=. python scripts/import_asrs.py --csv-dir data/raw/asrs/ --apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app, db
from app.ingestion.asrs_import import format_stats, import_asrs_rows, iter_csv_rows, iter_hf_rows, require_asrs_table
from app.models import AsrsReport, Aircraft


def _coverage_report() -> str:
    matched = (
        db.session.query(AsrsReport.aircraft_id, db.func.count(AsrsReport.id))
        .filter(AsrsReport.aircraft_id.isnot(None))
        .group_by(AsrsReport.aircraft_id)
        .all()
    )
    if not matched:
        return "coverage: 0 aircraft with matched ASRS rows"
    names = {a.id: a.model_name for a in Aircraft.query.all()}
    lines = [f"coverage: {len(matched)} aircraft with n>0"]
    top = sorted(matched, key=lambda x: -x[1])[:15]
    for aircraft_id, count in top:
        lines.append(f"  {names.get(aircraft_id, aircraft_id)}: n={count}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import ASRS reports into asrs_report")
    parser.add_argument("--source", choices=("huggingface",), help="Bulk import from HF dataset")
    parser.add_argument("--csv", type=Path, help="Single DBOL CSV export")
    parser.add_argument("--csv-dir", type=Path, help="Directory of DBOL CSV exports")
    parser.add_argument(
        "--overrides",
        type=Path,
        default=ROOT / "data/config/asrs_make_model_to_aircraft.jsonl",
        help="Optional make/model override JSONL",
    )
    parser.add_argument("--apply", action="store_true", help="Write to DB (default dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Explicit dry-run")
    args = parser.parse_args()

    if not args.source and not args.csv and not args.csv_dir:
        parser.error("Provide --source huggingface and/or --csv / --csv-dir")
    if args.apply and args.dry_run:
        parser.error("Use only one of --apply or --dry-run")

    apply = args.apply
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"import_asrs [{mode}]")

    app = create_app("development")
    with app.app_context():
        require_asrs_table()
        rows = []
        if args.source == "huggingface":
            rows.extend(iter_hf_rows())
        if args.csv:
            rows.extend(iter_csv_rows(args.csv))
        if args.csv_dir:
            for path in sorted(args.csv_dir.glob("*.csv")):
                rows.extend(iter_csv_rows(path))

        stats = import_asrs_rows(rows, apply=apply, overrides_path=args.overrides)
        print(format_stats(stats))
        if apply:
            print(_coverage_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
