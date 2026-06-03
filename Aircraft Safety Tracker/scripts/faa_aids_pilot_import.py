#!/usr/bin/env python3
"""FAA AIDS pilot import on cloned v3 DB (PRD 0007 FR-9)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_V3 = ROOT / "data/aircraft_safety_v3.db"
DEFAULT_PILOT = ROOT / "data/aircraft_safety_v3_pilot.db"
DEFAULT_RAW = ROOT / "data/raw/faa_aids_boeing_airbus.jsonl"
DEFAULT_DEDUPE = ROOT / "data/logs/faa_aids_dedupe_audit.jsonl"
DEFAULT_MAPPING = ROOT / "data/config/faa_aids_make_model_to_aircraft.jsonl"
DEFAULT_REPORT = ROOT / "data/logs/faa_aids_pilot_import_report.json"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_V3)
    parser.add_argument("--pilot-db", type=Path, default=DEFAULT_PILOT)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--dedupe-audit", type=Path, default=DEFAULT_DEDUPE)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    if args.pilot_db.exists():
        args.pilot_db.unlink()
    shutil.copy2(args.db, args.pilot_db)

    raw_index = {r["c5"]: r for r in load_jsonl(args.raw) if r.get("c5")}
    candidates = [
        r
        for r in load_jsonl(args.dedupe_audit)
        if r.get("dedupe_status") == "import"
    ][: args.limit]

    database_url = f"sqlite:///{args.pilot_db.resolve()}"
    os.environ["DATABASE_URL"] = database_url

    from app import create_app
    from app.ingestion.importers.faa_aids_importer import FAAAIDSImporter
    from app.models import Incident, IncidentSource

    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    issues: List[str] = []
    sample_urls: List[str] = []

    with app.app_context():
        from app.ingestion.faa_aids_mapping import bootstrap_create_approved_pages, load_faa_aids_make_model_mapping

        mapping = load_faa_aids_make_model_mapping(args.mapping)
        bootstrap_create_approved_pages(mapping, dry_run=False)

        records = [raw_index[r["c5"]] for r in candidates if r["c5"] in raw_index]
        written = FAAAIDSImporter(records=records, mapping=args.mapping).run()

        for row in candidates[:5]:
            c5 = row["c5"]
            source = IncidentSource.query.filter_by(
                source_name="FAA_AIDS", source_record_id=c5
            ).first()
            if not source:
                issues.append(f"missing source for {c5}")
                continue
            if not source.source_url:
                issues.append(f"null url for {c5}")
            else:
                sample_urls.append(source.source_url)
            entry = mapping.get(row.get("faa_make_model") or "")
            if entry and source.incident.aircraft.model_name != entry.canonical_model_name:
                issues.append(
                    f"aircraft page mismatch {c5}: expected {entry.canonical_model_name!r} "
                    f"got {source.incident.aircraft.model_name!r}"
                )

    report = {
        "rows_attempted": len(candidates),
        "rows_imported": written,
        "verification_issues": issues,
        "sample_source_urls": sample_urls,
        "pilot_db": str(args.pilot_db),
    }
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
