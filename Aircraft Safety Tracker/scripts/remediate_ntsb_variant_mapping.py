#!/usr/bin/env python3
"""Remediate NTSB imports: variant pages vs family rollups (product 2026-06)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ingestion.ntsb_variant_resolution import (  # noqa: E402
    EC130_CREATE_MANUFACTURER,
    EC130_PAGE,
    is_generic_boeing_737,
    resolve_canonical_model_name,
)

DEFAULT_MAPPING = ROOT / "data/config/ntsb_make_model_to_aircraft.jsonl"
DEFAULT_DB = ROOT / "data/aircraft_safety_v3.db"
DEFAULT_REPORT = ROOT / "data/logs/ntsb_variant_mapping_remediation.json"


def _load_jsonl(path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    header: List[str] = []
    rows: List[Dict[str, Any]] = []
    with path.open() as f:
        for line in f:
            if line.startswith("#"):
                header.append(line.rstrip("\n"))
            elif line.strip():
                rows.append(json.loads(line))
    return header, rows


def _write_jsonl(path: Path, header: List[str], rows: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for h in header:
            f.write(h + "\n")
        if header and not header[-1].startswith("# remediation"):
            f.write("# remediation: variant series + EC130 page (2026-06)\n")
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _catalog_by_name(app) -> Dict[str, int]:
    from app.models import Aircraft

    with app.app_context():
        return {
            model_name: aircraft_id
            for aircraft_id, model_name in Aircraft.query.with_entities(
                Aircraft.id, Aircraft.model_name
            ).all()
        }


def _ensure_ec130_page(app, dry_run: bool) -> int:
    from app import db
    from app.models import Aircraft

    with app.app_context():
        existing = Aircraft.query.filter_by(model_name=EC130_PAGE).first()
        if existing:
            return existing.id
        if dry_run:
            return -1
        aircraft = Aircraft(manufacturer=EC130_CREATE_MANUFACTURER, model_name=EC130_PAGE)
        db.session.add(aircraft)
        db.session.commit()
        return aircraft.id


def _patch_mapping_rows(
    rows: List[Dict[str, Any]], catalog_by_name: Dict[str, int]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    updated: List[Dict[str, Any]] = []
    changes: List[Dict[str, Any]] = []
    for row in rows:
        mm = row["ntsb_make_model"]
        proposed = resolve_canonical_model_name(mm)
        if not proposed or proposed == row.get("canonical_model_name"):
            updated.append(row)
            continue
        new_row = dict(row)
        aid = catalog_by_name.get(proposed)
        if proposed == EC130_PAGE and aid is None:
            new_row["canonical_model_name"] = EC130_PAGE
            new_row["canonical_aircraft_id"] = None
            new_row["action"] = "create_approved"
            new_row["manufacturer"] = EC130_CREATE_MANUFACTURER
        else:
            new_row["canonical_model_name"] = proposed
            new_row["canonical_aircraft_id"] = aid
            new_row["action"] = "map_to_existing"
            new_row.pop("manufacturer", None)
        note = new_row.get("notes") or ""
        if "remediated_variant" not in note:
            new_row["notes"] = f"{note}; remediated_variant=2026-06".strip("; ")
        changes.append(
            {
                "ntsb_make_model": mm,
                "from": row.get("canonical_model_name"),
                "to": proposed,
            }
        )
        updated.append(new_row)
    return updated, changes


def _recalc_aircraft_stats(aircraft_ids: Set[int]) -> int:
    from sqlalchemy import case

    from app import db
    from app.models import Aircraft, Incident

    updated = 0
    for aid in sorted(aircraft_ids):
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


def _remediate_incidents(app, catalog_by_name: Dict[str, int], dry_run: bool) -> Dict[str, Any]:
    from app import db
    from app.models import Incident, IncidentSource
    moves: List[Dict[str, Any]] = []
    touched_aircraft: Set[int] = set()

    with app.app_context():
        sources = (
            IncidentSource.query.filter_by(source_name="NTSB")
            .join(Incident)
            .all()
        )
        for src in sources:
            inc = src.incident
            if inc is None:
                continue
            sd = src.source_data or {}
            mm = sd.get("ntsb_make_model") or sd.get("make_model")
            if not mm:
                continue
            target_name = resolve_canonical_model_name(mm)
            if not target_name:
                continue
            target_id = catalog_by_name.get(target_name)
            if target_id is None and target_name == EC130_PAGE:
                target_id = catalog_by_name.get(EC130_PAGE)
            if target_id is None:
                continue
            if inc.aircraft_id == target_id:
                continue
            moves.append(
                {
                    "source_record_id": src.source_record_id,
                    "incident_id": inc.id,
                    "make_model": mm,
                    "from_aircraft_id": inc.aircraft_id,
                    "to_aircraft_id": target_id,
                    "to_page": target_name,
                }
            )
            touched_aircraft.add(inc.aircraft_id)
            touched_aircraft.add(target_id)
            if not dry_run:
                inc.aircraft_id = target_id

        if not dry_run and moves:
            db.session.commit()
            _recalc_aircraft_stats(touched_aircraft)

    return {"incident_moves": moves, "move_count": len(moves)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL") or f"sqlite:///{DEFAULT_DB}",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--skip-db", action="store_true", help="Only rewrite mapping file.")
    args = parser.parse_args()

    os.environ["DATABASE_URL"] = args.database_url
    from app import create_app

    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = args.database_url

    ec130_id = None
    if not args.skip_db:
        ec130_id = _ensure_ec130_page(app, args.dry_run)

    catalog_by_name = _catalog_by_name(app)
    if ec130_id and ec130_id > 0:
        catalog_by_name[EC130_PAGE] = ec130_id

    header, rows = _load_jsonl(args.mapping)
    updated_rows, mapping_changes = _patch_mapping_rows(rows, catalog_by_name)

    if not args.dry_run:
        _write_jsonl(args.mapping, header, updated_rows)

    incident_report: Dict[str, Any] = {"skipped": args.skip_db}
    if not args.skip_db:
        # Reload mapping after write for incident pass
        if not args.dry_run:
            catalog_by_name = _catalog_by_name(app)
            if ec130_id and ec130_id > 0:
                catalog_by_name[EC130_PAGE] = ec130_id
        incident_report = _remediate_incidents(app, catalog_by_name, args.dry_run)

    report = {
        "dry_run": args.dry_run,
        "mapping_path": str(args.mapping),
        "mapping_changes_count": len(mapping_changes),
        "mapping_changes": mapping_changes,
        "ec130_aircraft_id": ec130_id,
        **incident_report,
    }
    if not args.dry_run:
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        with args.report_out.open("w") as f:
            json.dump(report, f, indent=2)

    print(json.dumps({k: v for k, v in report.items() if k != "mapping_changes"}, indent=2))
    print(f"mapping_changes: {len(mapping_changes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
