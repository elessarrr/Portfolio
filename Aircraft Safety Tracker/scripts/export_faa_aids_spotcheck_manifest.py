#!/usr/bin/env python3
"""Export every FAA_AIDS row from the DB for manual spot-checking in the app.

Writes JSONL + CSV with aircraft page path, incident id, source_record_id, and
whether the FAA link should appear (is_active on IncidentSource).

Usage:
  DATABASE_URL="sqlite:///$(pwd)/data/aircraft_safety_v3.db" \\
  PYTHONPATH=. python scripts/export_faa_aids_spotcheck_manifest.py

  # Random sample of 50 for a quick pass:
  PYTHONPATH=. python scripts/export_faa_aids_spotcheck_manifest.py --sample 50 --seed 42
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "data/logs/faa_aids_spotcheck_manifest.jsonl"
DEFAULT_CSV = ROOT / "data/logs/faa_aids_spotcheck_manifest.csv"
DEFAULT_AIRCRAFT = ROOT / "data/logs/faa_aids_spotcheck_aircraft_pages.jsonl"
DEFAULT_MERGED = ROOT / "data/logs/faa_aids_url_audit_brief_2026-06-02_merged.jsonl"

COLUMNS = [
    "source_record_id",
    "incident_id",
    "aircraft_id",
    "manufacturer",
    "model_name",
    "incident_date",
    "is_active",
    "audit_bucket",
    "should_show_faa_link",
    "app_aircraft_path",
    "faa_brief_url",
]


def _load_audit_buckets(path: Path) -> Dict[str, str]:
    buckets: Dict[str, str] = {}
    if not path.exists():
        return buckets
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        row = json.loads(line)
        sid = row.get("source_record_id")
        if sid:
            buckets[str(sid)] = str(row.get("bucket") or "")
    return buckets


def export_manifest(
    *,
    base_url: str = "http://127.0.0.1:5003",
    merged_audit: Optional[Path] = None,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    from app import create_app, db
    from app.models import Aircraft, Incident, IncidentSource

    buckets = _load_audit_buckets(merged_audit or DEFAULT_MERGED)
    app = create_app()
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    rows: List[Dict[str, Any]] = []
    by_aircraft: Dict[int, Dict[str, Any]] = {}

    with app.app_context():
        q = (
            db.session.query(IncidentSource, Incident, Aircraft)
            .join(Incident, IncidentSource.incident_id == Incident.id)
            .join(Aircraft, Incident.aircraft_id == Aircraft.id)
            .filter(IncidentSource.source_name == "FAA_AIDS")
            .order_by(Aircraft.model_name, Incident.date, IncidentSource.source_record_id)
        )
        for source, incident, aircraft in q.all():
            sid = str(source.source_record_id or "")
            bucket = buckets.get(sid, "")
            active = bool(source.is_active)
            should_show = active and bucket == "working_brief_report"
            path = f"/aircraft/{aircraft.id}"
            row = {
                "source_record_id": sid,
                "incident_id": incident.id,
                "aircraft_id": aircraft.id,
                "manufacturer": aircraft.manufacturer,
                "model_name": aircraft.model_name,
                "incident_date": incident.date.isoformat() if incident.date else None,
                "is_active": active,
                "audit_bucket": bucket or None,
                "should_show_faa_link": should_show,
                "app_aircraft_path": path,
                "app_aircraft_url": f"{base_url.rstrip('/')}{path}",
                "faa_brief_url": source.source_url,
            }
            rows.append(row)
            ac = by_aircraft.setdefault(
                aircraft.id,
                {
                    "aircraft_id": aircraft.id,
                    "manufacturer": aircraft.manufacturer,
                    "model_name": aircraft.model_name,
                    "app_aircraft_path": path,
                    "app_aircraft_url": row["app_aircraft_url"],
                    "faa_incident_count": 0,
                    "faa_active_link_count": 0,
                },
            )
            ac["faa_incident_count"] += 1
            if should_show:
                ac["faa_active_link_count"] += 1

    aircraft_pages = sorted(by_aircraft.values(), key=lambda x: (x["manufacturer"] or "", x["model_name"] or ""))
    return rows, aircraft_pages


def _write_jsonl(path: Path, rows: List[Dict[str, Any]], header_comment: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# {header_comment}\n")
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k) for k in COLUMNS})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--csv-out", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--aircraft-out", type=Path, default=DEFAULT_AIRCRAFT)
    parser.add_argument("--merged-audit", type=Path, default=DEFAULT_MERGED)
    parser.add_argument("--base-url", default="http://127.0.0.1:5003")
    parser.add_argument("--sample", type=int, default=0, help="Also write random sample JSONL (N rows)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rows, aircraft_pages = export_manifest(base_url=args.base_url, merged_audit=args.merged_audit)
    today = date.today().isoformat()

    _write_jsonl(args.out, rows, f"FAA AIDS spot-check manifest — {today} — n={len(rows)}")
    _write_csv(args.csv_out, rows)
    _write_jsonl(
        args.aircraft_out,
        aircraft_pages,
        f"FAA AIDS aircraft pages — {today} — n={len(aircraft_pages)}",
    )

    summary = {
        "export_date": today,
        "faa_incident_rows": len(rows),
        "aircraft_pages_with_faa": len(aircraft_pages),
        "rows_with_visible_link": sum(1 for r in rows if r["should_show_faa_link"]),
        "jsonl": str(args.out),
        "csv": str(args.csv_out),
        "aircraft_pages_jsonl": str(args.aircraft_out),
    }

    if args.sample > 0:
        rng = random.Random(args.seed)
        sample = rng.sample(rows, min(args.sample, len(rows)))
        sample_path = args.out.with_name(
            f"{args.out.stem}_sample{min(args.sample, len(rows))}{args.out.suffix}"
        )
        _write_jsonl(sample_path, sample, f"FAA AIDS spot-check sample — seed={args.seed} — n={len(sample)}")
        summary["sample_jsonl"] = str(sample_path)
        summary["sample_size"] = len(sample)

    summary_path = args.out.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
