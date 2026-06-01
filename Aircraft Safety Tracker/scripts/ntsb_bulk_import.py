#!/usr/bin/env python3
"""NTSB bulk import on real v3 DB: bootstrap → dedupe re-pass → import → stats (FR-21)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_V3_DB = ROOT / "data/aircraft_safety_v3.db"
DEFAULT_NORMALIZED = ROOT / "data/logs/ntsb_enrichment_audit_rows_normalized.jsonl"
DEFAULT_FULL_JSON = ROOT / "data/raw/ntsb_records_full.json"
DEFAULT_MAPPING = ROOT / "data/config/ntsb_make_model_to_aircraft.jsonl"
DEFAULT_AUDIT_ROWS = ROOT / "data/logs/ntsb_enrichment_audit_rows.jsonl"
DEFAULT_REPORT = ROOT / "data/logs/ntsb_bulk_import_report.json"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def index_full_records(path: Path) -> Dict[str, Dict[str, Any]]:
    with path.open() as f:
        records = json.load(f)
    index: Dict[str, Dict[str, Any]] = {}
    for raw in records:
        ntsb_num = (raw.get("cm_ntsbNum") or raw.get("ntsb_id") or "").strip()
        if ntsb_num:
            index[ntsb_num] = raw
    return index


def merge_raw_with_audit(
    raw: Dict[str, Any], audit_row: Dict[str, Any]
) -> Dict[str, Any]:
    merged = dict(raw)
    if audit_row.get("ntsb_url"):
        merged["_audit_source_url"] = audit_row["ntsb_url"]
    return merged


def import_candidates(normalized_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [r for r in normalized_rows if r.get("dedupe_repasse_status") == "import"]


def _app_context(database_url: str):
    os.environ["DATABASE_URL"] = database_url
    from app import create_app

    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    return app


def recalc_aircraft_stats(aircraft_ids: Iterable[int]) -> int:
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
    full_index: Dict[str, Dict[str, Any]],
    mapping_path: Path,
) -> Dict[str, Any]:
    from app import db
    from app.ingestion.importers.ntsb_importer import NTSBImporter
    from app.models import Incident, IncidentSource

    before_sources = IncidentSource.query.filter_by(source_name="NTSB").count()
    before_incidents = Incident.query.count()

    records: List[Dict[str, Any]] = []
    missing: List[str] = []
    for row in candidates:
        sid = row["source_record_id"]
        raw = full_index.get(sid)
        if not raw:
            missing.append(sid)
            continue
        records.append(merge_raw_with_audit(raw, row))

    if missing:
        raise ValueError(f"Missing raw records for: {missing[:10]}{'...' if len(missing) > 10 else ''}")

    importer = NTSBImporter(records=records, mapping=mapping_path)
    written = importer.run()

    after_sources = IncidentSource.query.filter_by(source_name="NTSB").count()
    after_incidents = Incident.query.count()

    from sqlalchemy import distinct

    aircraft_ids = {
        row[0]
        for row in db.session.query(distinct(Incident.aircraft_id))
        .join(IncidentSource)
        .filter(IncidentSource.source_name == "NTSB")
        .all()
        if row[0] is not None
    }

    stats_updated = recalc_aircraft_stats(aircraft_ids)

    return {
        "requested": len(candidates),
        "written": written,
        "skipped_unmapped": importer.skipped_unmapped,
        "skipped_unresolved": importer.skipped_unresolved,
        "ntsb_sources_before": before_sources,
        "ntsb_sources_after": after_sources,
        "ntsb_sources_created": after_sources - before_sources,
        "incidents_before": before_incidents,
        "incidents_after": after_incidents,
        "incidents_created": after_incidents - before_incidents,
        "aircraft_stats_recalced": stats_updated,
        "distinct_aircraft_ids": len(aircraft_ids),
    }


def _sqlite_url(db_path: Path) -> str:
    return f"sqlite:///{db_path.resolve()}"


def _run_step(cmd: List[str], database_url: str) -> int:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(cmd, env=env, cwd=str(ROOT))
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="SQLite DATABASE_URL (defaults to data/aircraft_safety_v3.db).",
    )
    parser.add_argument("--db-path", type=Path, default=DEFAULT_V3_DB)
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import", help="Import dedupe_repasse_status=import rows.")
    p_import.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="SQLite DATABASE_URL.",
    )
    p_import.add_argument("--normalized", type=Path, default=DEFAULT_NORMALIZED)
    p_import.add_argument("--full-json", type=Path, default=DEFAULT_FULL_JSON)
    p_import.add_argument(
        "--mapping",
        type=Path,
        default=DEFAULT_MAPPING,
        help="Required gate file: data/config/ntsb_make_model_to_aircraft.jsonl (FR-17).",
    )
    p_import.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    p_import.add_argument(
        "--verify-idempotent",
        action="store_true",
        help="Run import twice; second pass should create 0 new IncidentSource rows.",
    )

    p_run = sub.add_parser(
        "run-all",
        help="bootstrap → dedupe re-pass → import → idempotent verify",
    )
    p_run.add_argument("--db-path", type=Path, default=DEFAULT_V3_DB)
    p_run.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    p_run.add_argument("--audit-rows", type=Path, default=DEFAULT_AUDIT_ROWS)
    p_run.add_argument("--full-json", type=Path, default=DEFAULT_FULL_JSON)
    p_run.add_argument("--normalized", type=Path, default=DEFAULT_NORMALIZED)
    p_run.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    p_run.add_argument(
        "--skip-bootstrap",
        action="store_true",
        help="Skip bootstrap if pages already exist.",
    )

    args = parser.parse_args()
    if args.command == "import":
        database_url = args.database_url or _sqlite_url(DEFAULT_V3_DB)
    else:
        database_url = getattr(args, "database_url", None) or _sqlite_url(args.db_path)

    if args.command == "import":
        app = _app_context(database_url)
        with app.app_context():
            normalized = load_jsonl(args.normalized)
            candidates = import_candidates(normalized)
            full_index = index_full_records(args.full_json)
            result = run_bulk_import(candidates, full_index, args.mapping)
            result["normalized_path"] = str(args.normalized)
            result["mapping_path"] = str(args.mapping)

            if args.verify_idempotent:
                before = result["ntsb_sources_after"]
                second = run_bulk_import(candidates, full_index, args.mapping)
                result["idempotent_rerun"] = {
                    "written": second["written"],
                    "ntsb_sources_created": second["ntsb_sources_created"],
                    "incidents_created": second["incidents_created"],
                    "passed": second["ntsb_sources_created"] == 0
                    and second["incidents_created"] == 0
                    and second["written"] == result["written"],
                    "ntsb_sources_unchanged_count": before,
                }

        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        with args.report_out.open("w") as f:
            json.dump(result, f, indent=2, sort_keys=True)
        print(json.dumps(result, indent=2))
        if result["written"] != result["requested"]:
            return 1
        if args.verify_idempotent and not result.get("idempotent_rerun", {}).get(
            "passed"
        ):
            return 1
        return 0

    if args.command == "run-all":
        db_url = _sqlite_url(args.db_path)
        py = sys.executable

        if not args.skip_bootstrap:
            code = _run_step(
                [
                    py,
                    str(ROOT / "scripts/bootstrap_ntsb_create_approved_pages.py"),
                    "--mapping",
                    str(args.mapping),
                    "--report-out",
                    str(ROOT / "data/logs/ntsb_bootstrap_create_approved.json"),
                ],
                db_url,
            )
            if code != 0:
                return code

        code = _run_step(
            [
                py,
                str(ROOT / "scripts/ntsb_dedupe_repass.py"),
                "--mapping",
                str(args.mapping),
                "--audit-rows",
                str(args.audit_rows),
                "--repasse-out",
                str(ROOT / "data/logs/ntsb_dedupe_repasse.json"),
                "--normalized-out",
                str(args.normalized),
                "--summary-out",
                str(ROOT / "data/logs/ntsb_pre_import_summary.json"),
            ],
            db_url,
        )
        if code != 0:
            return code

        code = _run_step(
            [
                py,
                str(ROOT / "scripts/ntsb_bulk_import.py"),
                "import",
                "--normalized",
                str(args.normalized),
                "--full-json",
                str(args.full_json),
                "--mapping",
                str(args.mapping),
                "--report-out",
                str(args.report_out),
                "--verify-idempotent",
            ],
            db_url,
        )
        return code

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
