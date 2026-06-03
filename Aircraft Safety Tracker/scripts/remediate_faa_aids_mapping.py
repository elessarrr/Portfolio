#!/usr/bin/env python3
"""Move FAA AIDS incidents off bootstrap bloat pages; apply refined mapping."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_MAPPING = ROOT / "data/config/faa_aids_make_model_to_aircraft.jsonl"
DEFAULT_DB = ROOT / "data/aircraft_safety_v3.db"
DEFAULT_REPORT = ROOT / "data/logs/faa_aids_mapping_remediation.json"
MAX_CATALOG_AIRCRAFT_ID = 113


def _load_mapping(path: Path) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            row = json.loads(line)
            out[row["faa_make_model"]] = row
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    mapping = _load_mapping(args.mapping)
    database_url = f"sqlite:///{args.db.resolve()}"
    os.environ["DATABASE_URL"] = database_url

    from app import create_app, db
    from app.ingestion.faa_aids_mapping import load_faa_aids_make_model_mapping
    from app.models import Aircraft, Incident, IncidentSource
    from sqlalchemy import case

    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    gate = load_faa_aids_make_model_mapping(args.mapping)

    moved = 0
    skipped_action = 0
    unresolved = 0
    deleted_aircraft = 0
    touched_aircraft: Set[int] = set()

    with app.app_context():
        catalog_by_name = {
            a.model_name: a.id
            for a in Aircraft.query.filter(Aircraft.id <= MAX_CATALOG_AIRCRAFT_ID).all()
        }

        sources = IncidentSource.query.filter_by(source_name="FAA_AIDS", is_active=True).all()
        for source in sources:
            data = source.source_data or {}
            faa_mm = data.get("faa_aids_make_model") or ""
            entry = mapping.get(faa_mm)
            if not entry or entry.get("action") == "skip":
                skipped_action += 1
                continue
            target_name = entry["canonical_model_name"]
            target_id = catalog_by_name.get(target_name)
            if target_id is None:
                target_id = gate.lookup_aircraft_id_only(faa_mm)
            if target_id is None:
                unresolved += 1
                continue
            incident = source.incident
            if incident.aircraft_id == target_id:
                continue
            touched_aircraft.add(incident.aircraft_id)
            touched_aircraft.add(target_id)
            if not args.dry_run:
                incident.aircraft_id = target_id
            moved += 1

        if not args.dry_run:
            db.session.commit()

        bloat_ids = [
            a.id
            for a in Aircraft.query.filter(Aircraft.id > MAX_CATALOG_AIRCRAFT_ID).all()
        ]
        for aid in bloat_ids:
            count = Incident.query.filter_by(aircraft_id=aid).count()
            if count == 0 and not args.dry_run:
                aircraft = db.session.get(Aircraft, aid)
                if aircraft:
                    db.session.delete(aircraft)
                    deleted_aircraft += 1
        if not args.dry_run:
            db.session.commit()

        for aid in touched_aircraft | set(catalog_by_name.values()):
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
        if not args.dry_run:
            db.session.commit()

    report = {
        "dry_run": args.dry_run,
        "incidents_moved": moved,
        "skipped_mapping": skipped_action,
        "unresolved_target": unresolved,
        "bloat_aircraft_deleted": deleted_aircraft,
        "mapping": str(args.mapping),
    }
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
