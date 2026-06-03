#!/usr/bin/env python3
"""Set FAA_AIDS is_active from merged brief audit buckets (no HTTP). Ask-before-write."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BUCKET_BRIEF = "working_brief_report"


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--audit",
        type=Path,
        default=ROOT / "data/logs/faa_aids_url_audit_brief_2026-06-02_merged.jsonl",
    )
    parser.add_argument("--apply", action="store_true", help="Write is_active to DB")
    parser.add_argument(
        "--overlap-audit",
        type=Path,
        default=ROOT / "data/logs/faa_aids_baseline_overlap_audit.jsonl",
        help="Never set active for IDs listed here (FR-0 baseline duplicates)",
    )
    args = parser.parse_args()

    from app import create_app
    from app.models import IncidentSource

    rows = _load_jsonl(args.audit)
    overlap_ids: set[str] = set()
    if args.overlap_audit.exists():
        for row in _load_jsonl(args.overlap_audit):
            sid = row.get("source_record_id")
            if sid:
                overlap_ids.add(str(sid))
    stats = {"brief_active": 0, "non_brief_inactive": 0, "overlap_forced_inactive": 0, "missing": 0}

    database_url = os.environ.get("DATABASE_URL")
    app = create_app()
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    with app.app_context():
        for row in rows:
            sid = row.get("source_record_id")
            if not sid:
                continue
            source = IncidentSource.query.filter_by(
                source_name="FAA_AIDS", source_record_id=str(sid)
            ).first()
            if source is None:
                stats["missing"] += 1
                continue
            sid_str = str(sid)
            if sid_str in overlap_ids:
                want_active = False
                stats["overlap_forced_inactive"] += 1
            else:
                want_active = row.get("bucket") == BUCKET_BRIEF
            if want_active:
                stats["brief_active"] += 1
            else:
                stats["non_brief_inactive"] += 1
            if args.apply and source.is_active != want_active:
                source.is_active = want_active
        if args.apply:
            from app import db

            db.session.commit()

    print(json.dumps({"dry_run": not args.apply, **stats}, indent=2))
    if not args.apply:
        print("Re-run with --apply to update is_active.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
