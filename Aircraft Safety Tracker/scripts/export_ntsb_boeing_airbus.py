"""Export Boeing/Airbus NTSB records from v2 DB for enrichment audit (FR-7.1 bootstrap)."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from typing import Any, Dict, List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ingestion.importers.base import is_boeing_or_airbus_make_model


def _parse_source_data(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        return json.loads(raw)
    raise ValueError(f"Unexpected source_data type: {type(raw)}")


def _is_boeing_airbus_record(record: Dict[str, Any]) -> bool:
    vehicles = record.get("cm_vehicles") or []
    vehicle = vehicles[0] if vehicles else {}
    make = vehicle.get("make") or ""
    model = vehicle.get("model") or ""
    make_model = f"{make} {model}".strip() if make or model else record.get("make_model")
    return is_boeing_or_airbus_make_model(make_model)


def export_ntsb_boeing_airbus(db_path: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT source_data
        FROM incident_source
        WHERE source_name = 'NTSB'
        ORDER BY id ASC
        """
    )

    exported: List[Dict[str, Any]] = []
    for row in cur:
        record = _parse_source_data(row["source_data"])
        if _is_boeing_airbus_record(record):
            exported.append(record)

    conn.close()
    return exported


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export Boeing/Airbus NTSB source_data records from v2 SQLite DB."
    )
    parser.add_argument(
        "--db",
        default="data/aircraft_safety.db",
        help="Path to v2 SQLite database. Default: data/aircraft_safety.db",
    )
    parser.add_argument(
        "--out",
        default="data/raw/ntsb_records_full.json",
        help="Output JSON path. Default: data/raw/ntsb_records_full.json",
    )
    args = parser.parse_args()

    records = export_ntsb_boeing_airbus(args.db)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(records, f)

    summary = {
        "db_path": args.db,
        "output_path": args.out,
        "exported_count": len(records),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
