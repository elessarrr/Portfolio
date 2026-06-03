#!/usr/bin/env python3
"""FAA AIDS bulk import with mapping gate (PRD 0007 FR-10)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_RAW = ROOT / "data/raw/faa_aids_boeing_airbus.jsonl"
DEFAULT_DEDUPE = ROOT / "data/logs/faa_aids_dedupe_audit.jsonl"
DEFAULT_MAPPING = ROOT / "data/config/faa_aids_make_model_to_aircraft.jsonl"
DEFAULT_REPORT = ROOT / "data/logs/faa_aids_bulk_import_report.json"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def index_raw(path: Path) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for row in load_jsonl(path):
        c5 = str(row.get("c5") or "").strip()
        if c5:
            index[c5] = row
    return index


def import_candidates(dedupe_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [r for r in dedupe_rows if r.get("dedupe_status") == "import"]


def recalc_aircraft_stats(aircraft_ids) -> int:
    from sqlalchemy import case

    from app import db
    from app.models import Aircraft, Incident

    updated = 0
    for aid in sorted(set(aircraft_ids)):
        aircraft = db.session.get(Aircraft, aid)
        if aircraft is None:
            continue
        stats = (
            db.session.query(
                db.func.count(Incident.id),
                db.func.coalesce(db.func.sum(Incident.fatalities), 0),
                db.func.coalesce(
                    db.func.sum(case((Incident.fatalities > 0, 1), else_=0)), 0
                ),
            )
            .filter_by(aircraft_id=aid)
            .first()
        )
        aircraft.total_incidents = stats[0] or 0
        aircraft.total_fatalities = int(stats[1] or 0)
        aircraft.fatal_incidents = int(stats[2] or 0)
        aircraft.last_updated = datetime.utcnow()
        updated += 1
    db.session.commit()
    return updated


def run_bulk_import(
    candidates: List[Dict[str, Any]],
    raw_index: Dict[str, Dict[str, Any]],
    mapping_path: Path,
    *,
    batch_size: int = 1000,
) -> Dict[str, Any]:
    from sqlalchemy import distinct

    from app import db
    from app.ingestion.importers.faa_aids_importer import FAAAIDSImporter
    from app.models import Incident, IncidentSource

    before_sources = IncidentSource.query.filter_by(source_name="FAA_AIDS").count()
    before_incidents = Incident.query.count()

    written_total = 0
    missing: List[str] = []
    for i in range(0, len(candidates), batch_size):
        batch = candidates[i : i + batch_size]
        records = []
        for row in batch:
            c5 = row["c5"]
            raw = raw_index.get(c5)
            if not raw:
                missing.append(c5)
                continue
            records.append(raw)
        if not records:
            continue
        importer = FAAAIDSImporter(records=records, mapping=mapping_path)
        written_total += importer.run()

    after_sources = IncidentSource.query.filter_by(source_name="FAA_AIDS").count()
    after_incidents = Incident.query.count()

    aircraft_ids = {
        row[0]
        for row in db.session.query(distinct(Incident.aircraft_id))
        .join(IncidentSource)
        .filter(IncidentSource.source_name == "FAA_AIDS")
        .all()
        if row[0] is not None
    }
    stats_updated = recalc_aircraft_stats(aircraft_ids)

    return {
        "rows_read": len(candidates),
        "imported": written_total,
        "missing_raw": len(missing),
        "faa_sources_before": before_sources,
        "faa_sources_after": after_sources,
        "faa_sources_created": after_sources - before_sources,
        "incidents_before": before_incidents,
        "incidents_after": after_incidents,
        "incidents_created": after_incidents - before_incidents,
        "aircraft_pages_updated": stats_updated,
        "distinct_aircraft_ids": len(aircraft_ids),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--dedupe-audit", type=Path, default=DEFAULT_DEDUPE)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    dedupe_rows = load_jsonl(args.dedupe_audit)
    candidates = import_candidates(dedupe_rows)
    raw_index = index_raw(args.raw)

    database_url = os.environ.get("DATABASE_URL")
    app = __import__("app", fromlist=["create_app"]).create_app()
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    with app.app_context():
        first = run_bulk_import(
            candidates, raw_index, args.mapping, batch_size=args.batch_size
        )
        second = run_bulk_import(
            candidates, raw_index, args.mapping, batch_size=args.batch_size
        )

    report = {
        "first_pass": first,
        "second_pass_idempotent": {
            "faa_sources_created": second["faa_sources_created"],
            "incidents_created": second["incidents_created"],
        },
        "mapping": str(args.mapping),
        "dedupe_audit": str(args.dedupe_audit),
    }
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
