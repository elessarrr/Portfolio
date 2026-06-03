#!/usr/bin/env python3
"""Migrate FAA_AIDS IncidentSource.source_url from page 12 (search) to page 18 (brief report).

Run after a brief-mode audit shows acceptable product_viable rate. Default is dry-run.

Examples:
    PYTHONPATH=. python scripts/migrate_faa_aids_urls_to_brief.py --dry-run
    PYTHONPATH=. python scripts/migrate_faa_aids_urls_to_brief.py --apply
    PYTHONPATH=. python scripts/migrate_faa_aids_urls_to_brief.py --apply \\
        --require-audit data/logs/faa_aids_url_audit_2026-06-01.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_DB = ROOT / "data/aircraft_safety_v3.db"
DEFAULT_REPORT = ROOT / "data/logs/faa_aids_url_migration_to_brief.jsonl"

BUCKET_BRIEF = "working_brief_report"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def _allowed_ids_from_audit(audit_path: Path) -> Set[str]:
    allowed: Set[str] = set()
    for row in _load_jsonl(audit_path):
        if row.get("bucket") == BUCKET_BRIEF:
            sid = row.get("source_record_id")
            if sid:
                allowed.add(str(sid))
    return allowed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--require-audit",
        type=Path,
        metavar="AUDIT_JSONL",
        help=f"Only migrate source_record_ids with bucket={BUCKET_BRIEF} in this audit export",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to DB (default: dry-run only)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Explicit dry-run (default when --apply is omitted)",
    )
    args = parser.parse_args()

    if args.apply and args.dry_run:
        raise SystemExit("Use either --apply or --dry-run, not both")

    dry_run = not args.apply
    allowed: Optional[Set[str]] = None
    if args.require_audit:
        allowed = _allowed_ids_from_audit(args.require_audit)
        print(f"Audit gate: {len(allowed):,} ids with bucket={BUCKET_BRIEF}")

    database_url = f"sqlite:///{args.db.resolve()}"
    os.environ["DATABASE_URL"] = database_url

    from app import create_app, db
    from app.ingestion.url_builders.faa_aids import build_faa_aids_brief_report_url
    from app.models import IncidentSource

    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    migrated = skipped = already_brief = gated = 0
    report_rows: List[Dict[str, Any]] = []

    with app.app_context():
        sources = (
            IncidentSource.query.filter_by(source_name="FAA_AIDS")
            .order_by(IncidentSource.source_record_id.asc())
            .all()
        )
        for source in sources:
            sid = source.source_record_id
            old_url = source.source_url or ""
            new_url = build_faa_aids_brief_report_url(sid)

            entry: Dict[str, Any] = {
                "source_record_id": sid,
                "incident_source_id": source.id,
                "old_url": old_url,
                "new_url": new_url,
                "action": "skip",
            }

            if not new_url:
                skipped += 1
                entry["action"] = "skip_no_id"
                report_rows.append(entry)
                continue

            if allowed is not None and sid not in allowed:
                gated += 1
                entry["action"] = "skip_audit_gate"
                report_rows.append(entry)
                continue

            if ":18:" in old_url and "AP_BRIEF_RPT_VAR" in old_url:
                already_brief += 1
                entry["action"] = "already_brief"
                report_rows.append(entry)
                continue

            if old_url == new_url:
                already_brief += 1
                entry["action"] = "already_brief"
                report_rows.append(entry)
                continue

            entry["action"] = "migrate" if not dry_run else "would_migrate"
            if not dry_run:
                source.source_url = new_url
                source.last_updated = datetime.utcnow()
                migrated += 1
            else:
                migrated += 1
            report_rows.append(entry)

        if not dry_run:
            db.session.commit()

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    with args.report_out.open("w", encoding="utf-8") as f:
        f.write(
            f"# FAA AIDS URL migration page12→page18 — dry_run={dry_run}"
            f" — migrated={migrated} gated={gated}\n"
        )
        for row in report_rows:
            if row["action"] in ("migrate", "would_migrate"):
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("=" * 60)
    print(f"FAA AIDS brief URL migration — {'DRY RUN' if dry_run else 'APPLIED'}")
    print(f"  Total FAA_AIDS sources: {len(sources):,}")
    print(f"  Would migrate / migrated: {migrated:,}")
    print(f"  Already page 18:          {already_brief:,}")
    print(f"  Skipped (audit gate):     {gated:,}")
    print(f"  Skipped (no id):          {skipped:,}")
    print(f"  Report:                   {args.report_out}")
    print("=" * 60)
    if dry_run:
        print("\nRe-run with --apply to write DB. Use --require-audit after brief-mode audit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
