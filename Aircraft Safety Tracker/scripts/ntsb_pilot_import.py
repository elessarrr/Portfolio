#!/usr/bin/env python3
"""NTSB pilot import: select 30 rows, import on pilot DB clone, verify (FR-20)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_V3_DB = ROOT / "data/aircraft_safety_v3.db"
DEFAULT_PILOT_DB = ROOT / "data/aircraft_safety_v3_pilot.db"
DEFAULT_NORMALIZED = ROOT / "data/logs/ntsb_enrichment_audit_rows_normalized.jsonl"
DEFAULT_FULL_JSON = ROOT / "data/raw/ntsb_records_full.json"
DEFAULT_MAPPING = ROOT / "data/config/ntsb_make_model_to_aircraft.jsonl"
DEFAULT_MANIFEST = ROOT / "data/logs/ntsb_pilot_import_manifest.jsonl"
DEFAULT_REPORT = ROOT / "data/logs/ntsb_pilot_import_report.json"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: List[Dict[str, Any]], header: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for h in header:
            f.write(h + "\n")
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def select_pilot_rows(
    normalized_rows: List[Dict[str, Any]],
    *,
    known_limit: int = 25,
    mapped_limit: int = 5,
) -> List[Dict[str, Any]]:
    importable = [
        r for r in normalized_rows if r.get("dedupe_repasse_status") == "import"
    ]
    known = [r for r in importable if not r.get("unknown_aircraft")]
    mapped_pool = [r for r in importable if r.get("unknown_aircraft")]

    if len(known) < known_limit:
        raise ValueError(
            f"Need {known_limit} known-aircraft import rows; found {len(known)}"
        )

    selected_known = known[:known_limit]

    by_page: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in mapped_pool:
        by_page[row.get("mapped_model_name") or ""].append(row)
    pages = sorted(by_page.keys(), key=lambda p: -len(by_page[p]))

    selected_mapped: List[Dict[str, Any]] = []
    for page in pages:
        if len(selected_mapped) >= mapped_limit:
            break
        selected_mapped.append(by_page[page][0])

    if len(selected_mapped) < mapped_limit:
        raise ValueError(
            f"Need {mapped_limit} mapped import rows; found {len(selected_mapped)}"
        )

    chosen = selected_known + selected_mapped
    for row in chosen:
        row["pilot_cohort"] = (
            "known_aircraft" if not row.get("unknown_aircraft") else "mapped_string"
        )
    return chosen


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


def clone_pilot_db(source: Path, dest: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Source DB not found: {source}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    shutil.copy2(source, dest)


def run_import(
    manifest: List[Dict[str, Any]],
    full_index: Dict[str, Dict[str, Any]],
    mapping_path: Path,
) -> Dict[str, Any]:
    from app import db
    from app.ingestion.importers.ntsb_importer import NTSBImporter

    records: List[Dict[str, Any]] = []
    missing: List[str] = []
    for row in manifest:
        sid = row["source_record_id"]
        raw = full_index.get(sid)
        if not raw:
            missing.append(sid)
            continue
        records.append(merge_raw_with_audit(raw, row))

    if missing:
        raise ValueError(f"Missing raw records for: {missing}")

    importer = NTSBImporter(records=records, mapping=mapping_path)
    written = importer.run()
    return {
        "requested": len(manifest),
        "written": written,
        "skipped_unmapped": importer.skipped_unmapped,
        "skipped_unresolved": importer.skipped_unresolved,
        "missing_raw": missing,
    }


def verify_import(manifest: List[Dict[str, Any]], window_days: int = 7) -> Dict[str, Any]:
    from app import db
    from app.ingestion.dedupe.ntsb_asn import score_ntsb_vs_asn
    from app.models import Aircraft, Incident, IncidentSource

    issues: List[Dict[str, Any]] = []
    checked = 0

    for row in manifest:
        sid = row["source_record_id"]
        source = IncidentSource.query.filter_by(
            source_name="NTSB", source_record_id=sid
        ).first()
        checked += 1
        if not source:
            issues.append({"source_record_id": sid, "issue": "missing_incident_source"})
            continue

        incident = source.incident
        aircraft = db.session.get(Aircraft, incident.aircraft_id)
        expected_page = row.get("mapped_model_name")
        if aircraft and expected_page and aircraft.model_name != expected_page:
            issues.append(
                {
                    "source_record_id": sid,
                    "issue": "wrong_aircraft_page",
                    "expected": expected_page,
                    "actual": aircraft.model_name,
                }
            )

        audit_url = row.get("ntsb_url")
        if audit_url and source.source_url != audit_url:
            issues.append(
                {
                    "source_record_id": sid,
                    "issue": "source_url_mismatch",
                    "expected": audit_url,
                    "actual": source.source_url,
                }
            )

        if not source.source_url:
            issues.append({"source_record_id": sid, "issue": "missing_source_url"})

        ntsb_make = (source.source_data or {}).get("ntsb_make_model")
        if ntsb_make and ntsb_make != row.get("make_model"):
            issues.append(
                {
                    "source_record_id": sid,
                    "issue": "make_model_metadata_mismatch",
                    "expected": row.get("make_model"),
                    "actual": ntsb_make,
                }
            )

        if incident.asn_url:
            issues.append(
                {
                    "source_record_id": sid,
                    "issue": "unexpected_asn_url_on_ntsb_only_row",
                    "asn_url": incident.asn_url,
                }
            )

        asn_on_page = (
            Incident.query.filter(
                Incident.aircraft_id == incident.aircraft_id,
                Incident.asn_url.isnot(None),
                Incident.id != incident.id,
            )
            .filter(
                Incident.date >= incident.date.fromordinal(
                    incident.date.toordinal() - window_days
                ),
                Incident.date <= incident.date.fromordinal(
                    incident.date.toordinal() + window_days
                ),
            )
            .all()
        )
        for asn_inc in asn_on_page:
            decision = score_ntsb_vs_asn(
                ntsb_date=incident.date,
                asn_date=asn_inc.date,
                ntsb_operator=incident.operator,
                asn_operator=asn_inc.operator,
                ntsb_location=incident.location,
                asn_location=asn_inc.location,
                ntsb_fatalities=incident.fatalities,
                asn_fatalities=asn_inc.fatalities,
            )
            if decision.asn_covered:
                issues.append(
                    {
                        "source_record_id": sid,
                        "issue": "asn_duplicate_candidate",
                        "asn_incident_id": asn_inc.id,
                        "decision": asdict(decision),
                    }
                )

    return {
        "checked": checked,
        "issues": issues,
        "passed": len(issues) == 0,
    }


def _app_context(database_url: str):
    os.environ["DATABASE_URL"] = database_url
    from app import create_app

    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    return app


def _run_subcommand(args: List[str], database_url: str) -> int:
    import subprocess

    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["PYTHONPATH"] = str(ROOT)
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), *args],
        env=env,
        cwd=str(ROOT),
    )
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="SQLite DATABASE_URL (required for import/verify).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_clone = sub.add_parser("clone-db", help="Copy v3 DB to pilot clone.")
    p_clone.add_argument("--source", type=Path, default=DEFAULT_V3_DB)
    p_clone.add_argument("--dest", type=Path, default=DEFAULT_PILOT_DB)

    p_select = sub.add_parser("select", help="Write 30-row pilot manifest.")
    p_select.add_argument("--normalized", type=Path, default=DEFAULT_NORMALIZED)
    p_select.add_argument("--out", type=Path, default=DEFAULT_MANIFEST)

    p_import = sub.add_parser("import", help="Import manifest rows on pilot DB.")
    p_import.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p_import.add_argument("--full-json", type=Path, default=DEFAULT_FULL_JSON)
    p_import.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)

    p_verify = sub.add_parser("verify", help="Verify pilot import results.")
    p_verify.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)

    p_run = sub.add_parser("run-all", help="clone → select → import → verify")
    p_run.add_argument("--source-db", type=Path, default=DEFAULT_V3_DB)
    p_run.add_argument("--pilot-db", type=Path, default=DEFAULT_PILOT_DB)
    p_run.add_argument("--normalized", type=Path, default=DEFAULT_NORMALIZED)
    p_run.add_argument("--full-json", type=Path, default=DEFAULT_FULL_JSON)
    p_run.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    p_run.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p_run.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    p_run.add_argument(
        "--skip-clone",
        action="store_true",
        help="Reuse existing pilot DB (after manual bootstrap/dedupe).",
    )

    args = parser.parse_args()

    if args.command == "clone-db":
        clone_pilot_db(args.source, args.dest)
        print(json.dumps({"cloned": str(args.dest)}, indent=2))
        return 0

    if args.command == "select":
        rows = select_pilot_rows(load_jsonl(args.normalized))
        write_jsonl(
            args.out,
            rows,
            [
                "# NTSB pilot import manifest (FR-20.1): 25 known + 5 mapped",
                f"# source: {args.normalized}",
            ],
        )
        print(json.dumps({"selected": len(rows), "out": str(args.out)}, indent=2))
        return 0

    if args.command in ("import", "verify"):
        if not args.database_url:
            print("ERROR: set DATABASE_URL or pass --database-url", file=sys.stderr)
            return 1
        app = _app_context(args.database_url)
        with app.app_context():
            if args.command == "import":
                manifest = load_jsonl(args.manifest)
                full_index = index_full_records(args.full_json)
                result = run_import(manifest, full_index, args.mapping)
                print(json.dumps(result, indent=2))
                return 0 if result["written"] == result["requested"] else 1

            manifest = load_jsonl(args.manifest)
            result = verify_import(manifest)
            print(json.dumps(result, indent=2))
            return 0 if result["passed"] else 1

    if args.command == "run-all":
        pilot_url = f"sqlite:///{args.pilot_db.resolve()}"
        if not args.skip_clone:
            clone_pilot_db(args.source_db, args.pilot_db)

        if _run_subcommand(["select", "--normalized", str(args.normalized), "--out", str(args.manifest)], pilot_url):
            return 1

        # Bootstrap create_approved pages (FR-20.0)
        import subprocess

        bootstrap_env = os.environ.copy()
        bootstrap_env["DATABASE_URL"] = pilot_url
        bootstrap_env["PYTHONPATH"] = str(ROOT)
        boot = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/bootstrap_ntsb_create_approved_pages.py"),
                "--mapping",
                str(args.mapping),
                "--report-out",
                str(ROOT / "data/logs/ntsb_bootstrap_create_approved_pilot.json"),
            ],
            env=bootstrap_env,
            cwd=str(ROOT),
        )
        if boot.returncode != 0:
            return boot.returncode

        # Optional dedupe re-pass on pilot DB (FR-20.0.5)
        dedupe_env = bootstrap_env.copy()
        dedupe = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/ntsb_dedupe_repass.py"),
                "--mapping",
                str(args.mapping),
                "--repasse-out",
                str(ROOT / "data/logs/ntsb_dedupe_repasse_pilot.json"),
                "--normalized-out",
                str(ROOT / "data/logs/ntsb_enrichment_audit_rows_normalized_pilot.jsonl"),
                "--summary-out",
                str(ROOT / "data/logs/ntsb_pre_import_summary_pilot.json"),
            ],
            env=dedupe_env,
            cwd=str(ROOT),
        )
        if dedupe.returncode != 0:
            return dedupe.returncode

        if _run_subcommand(["import", "--manifest", str(args.manifest), "--full-json", str(args.full_json), "--mapping", str(args.mapping)], pilot_url):
            return 1

        verify_code = _run_subcommand(["verify", "--manifest", str(args.manifest)], pilot_url)
        report_path = args.report_out
        manifest_rows = load_jsonl(args.manifest)
        report = {
            "pilot_db": str(args.pilot_db),
            "manifest_path": str(args.manifest),
            "selected_count": len(manifest_rows),
            "bootstrap_report": str(ROOT / "data/logs/ntsb_bootstrap_create_approved_pilot.json"),
            "dedupe_repasse_pilot": str(ROOT / "data/logs/ntsb_dedupe_repasse_pilot.json"),
        }
        if verify_code == 0:
            app = _app_context(pilot_url)
            with app.app_context():
                report["import"] = {"written": len(manifest_rows), "requested": len(manifest_rows)}
                report["verify"] = verify_import(manifest_rows)
        else:
            report["verify_exit_code"] = verify_code
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("w") as f:
            json.dump(report, f, indent=2, sort_keys=True)
        print(json.dumps(report, indent=2))
        return verify_code

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
