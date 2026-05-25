"""Copy the trusted ASN-only baseline from the v2 DB into the clean v3 DB.

This script intentionally copies no IncidentSource rows. The v3 branch starts
with main-style ASN links only; NTSB and FAA are added later by tested importers.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DB = ROOT / "data" / "aircraft_safety.db"
DEFAULT_TARGET_DB = ROOT / "data" / "aircraft_safety_v3.db"

EXPECTED_AIRCRAFT = 1266
EXPECTED_INCIDENTS = 1796
EXPECTED_INCIDENT_SOURCE = 0
EXPECTED_BREAKDOWN = {"Airbus": 1484, "Boeing": 312}

AIRCRAFT_COLUMNS = (
    "id",
    "manufacturer",
    "model_name",
    "icao_code",
    "years_in_service",
    "total_incidents",
    "fatal_incidents",
    "total_fatalities",
    "ai_summary",
    "last_updated",
)

INCIDENT_COLUMNS = (
    "id",
    "aircraft_id",
    "date",
    "operator",
    "location",
    "fatalities",
    "description",
    "asn_url",
    "incident_type",
)


def connect_readonly(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(f"source DB not found: {path}")
    uri = f"file:{path}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def connect_writable(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(f"target DB not found: {path}")
    return sqlite3.connect(path)


def quote_columns(columns: Sequence[str]) -> str:
    return ", ".join(columns)


def placeholders(columns: Sequence[str]) -> str:
    return ", ".join("?" for _ in columns)


def rows_for_columns(
    conn: sqlite3.Connection,
    table: str,
    columns: Sequence[str],
    where: str | None = None,
) -> Iterable[tuple]:
    sql = f"SELECT {quote_columns(columns)} FROM {table}"
    if where:
        sql = f"{sql} WHERE {where}"
    return conn.execute(sql)


def insert_rows(
    conn: sqlite3.Connection,
    table: str,
    columns: Sequence[str],
    rows: Iterable[tuple],
) -> int:
    sql = (
        f"INSERT OR IGNORE INTO {table} "
        f"({quote_columns(columns)}) VALUES ({placeholders(columns)})"
    )
    before = conn.total_changes
    conn.executemany(sql, rows)
    return conn.total_changes - before


def scalar(conn: sqlite3.Connection, sql: str) -> int:
    value = conn.execute(sql).fetchone()[0]
    return int(value or 0)


def manufacturer_breakdown(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        """
        SELECT a.manufacturer, COUNT(*)
        FROM incident i
        JOIN aircraft a ON i.aircraft_id = a.id
        GROUP BY a.manufacturer
        ORDER BY a.manufacturer
        """
    ).fetchall()
    return {manufacturer: int(count) for manufacturer, count in rows}


def verify(conn: sqlite3.Connection) -> None:
    aircraft_count = scalar(conn, "SELECT COUNT(*) FROM aircraft")
    incident_count = scalar(conn, "SELECT COUNT(*) FROM incident")
    incident_source_count = scalar(conn, "SELECT COUNT(*) FROM incident_source")
    missing_asn = scalar(
        conn,
        "SELECT COUNT(*) FROM incident WHERE asn_url IS NULL OR asn_url = ''",
    )
    breakdown = manufacturer_breakdown(conn)

    print(f"aircraft={aircraft_count}")
    print(f"incidents={incident_count}")
    print(f"incident_source={incident_source_count}")
    print(f"missing_asn_url={missing_asn}")
    print(f"manufacturer_breakdown={breakdown}")

    failures = []
    if aircraft_count != EXPECTED_AIRCRAFT:
        failures.append(f"expected {EXPECTED_AIRCRAFT} aircraft, got {aircraft_count}")
    if incident_count != EXPECTED_INCIDENTS:
        failures.append(f"expected {EXPECTED_INCIDENTS} incidents, got {incident_count}")
    if incident_source_count != EXPECTED_INCIDENT_SOURCE:
        failures.append(
            f"expected {EXPECTED_INCIDENT_SOURCE} incident_source rows, got {incident_source_count}"
        )
    if missing_asn != 0:
        failures.append(f"expected 0 incidents missing asn_url, got {missing_asn}")
    if breakdown != EXPECTED_BREAKDOWN:
        failures.append(f"expected breakdown {EXPECTED_BREAKDOWN}, got {breakdown}")

    if failures:
        raise RuntimeError("; ".join(failures))


def copy_asn_baseline(source_db: Path, target_db: Path) -> None:
    with connect_readonly(source_db) as source, connect_writable(target_db) as target:
        target.execute("PRAGMA foreign_keys = ON")

        aircraft_inserted = insert_rows(
            target,
            "aircraft",
            AIRCRAFT_COLUMNS,
            rows_for_columns(source, "aircraft", AIRCRAFT_COLUMNS),
        )
        incident_inserted = insert_rows(
            target,
            "incident",
            INCIDENT_COLUMNS,
            rows_for_columns(
                source,
                "incident",
                INCIDENT_COLUMNS,
                "asn_url IS NOT NULL AND asn_url != ''",
            ),
        )
        target.commit()

        print(f"inserted_aircraft={aircraft_inserted}")
        print(f"inserted_incidents={incident_inserted}")
        verify(target)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy ASN-linked aircraft incidents from v2 DB into clean v3 DB."
    )
    parser.add_argument("--source-db", type=Path, default=DEFAULT_SOURCE_DB)
    parser.add_argument("--target-db", type=Path, default=DEFAULT_TARGET_DB)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        copy_asn_baseline(args.source_db, args.target_db)
    except Exception as exc:
        print(f"copy_v2_to_v3 failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
