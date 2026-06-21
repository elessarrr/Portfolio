#!/usr/bin/env python3
"""One-time copy of enriched v3 SQLite data into Railway Postgres.

Use after `flask db upgrade head` on an empty Postgres database.

Examples:
  # Dry-run (counts only):
  SQLITE_PATH=data/aircraft_safety_v3.db \\
  DATABASE_URL=postgresql://... \\
  PYTHONPATH=. python scripts/push_v3_sqlite_to_postgres.py --dry-run

  # Apply (destructive — truncates target tables first):
  railway run python scripts/push_v3_sqlite_to_postgres.py --apply
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg2
from psycopg2.extras import Json, execute_batch
from sqlalchemy import create_engine, text

BATCH_SIZE = 500

# Import models so metadata is registered
from app.models import (  # noqa: F401
    Aircraft,
    AircraftVariant,
    Incident,
    IncidentSource,
    ReportAnalysis,
    Request,
    SystemTag,
)

TABLES_IN_ORDER = (
    "report_analysis",
    "system_tag",
    "incident_source",
    "incident",
    "aircraft_variant",
    "aircraft",
    "request",
)

SEQUENCE_TABLES = (
    "aircraft",
    "aircraft_variant",
    "incident",
    "incident_source",
    "system_tag",
    "report_analysis",
    "request",
)

ALEMBIC_HEAD = "f6a7b8c9d0e1"


def _normalize_postgres_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def _row_dict(row) -> dict:
    return dict(row._mapping)


def _normalize_row(table: str, data: dict) -> dict:
    """Coerce SQLite types for Postgres (e.g. 0/1 → bool)."""
    if table == "incident_source":
        if data.get("is_active") is not None:
            data["is_active"] = bool(data["is_active"])
        raw = data.get("source_data")
        if raw is not None:
            if isinstance(raw, str):
                raw = json.loads(raw)
            data["source_data"] = Json(raw)
    return data


def _row_tuple(table: str, data: dict, columns: list[str]) -> tuple:
    normalized = _normalize_row(table, data)
    return tuple(normalized[c] for c in columns)


def _copy_table_batched(src_conn, pg_cur, table: str) -> int:
    rows = src_conn.execute(text(f"SELECT * FROM {table}")).fetchall()
    if not rows:
        return 0
    columns = list(rows[0]._mapping.keys())
    col_list = ", ".join(columns)
    placeholders = ", ".join("%s" for _ in columns)
    insert_sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
    batch = [_row_tuple(table, _row_dict(row), columns) for row in rows]
    execute_batch(pg_cur, insert_sql, batch, page_size=BATCH_SIZE)
    return len(batch)


def push_sqlite_to_postgres(*, sqlite_path: Path, postgres_url: str, apply: bool) -> None:
    sqlite_url = f"sqlite:///{sqlite_path.resolve()}"
    postgres_url = _normalize_postgres_url(postgres_url)

    src_engine = create_engine(sqlite_url)

    counts: dict[str, int] = {}
    with src_engine.connect() as src_conn:
        for table in TABLES_IN_ORDER:
            counts[table] = src_conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0

    print("Source SQLite:", sqlite_path)
    print("Row counts to copy:")
    for table in TABLES_IN_ORDER:
        print(f"  {table}: {counts[table]:,}")

    if not apply:
        target = postgres_url.split("@")[-1] if "@" in postgres_url else postgres_url
        print("\nTarget Postgres:", target)
        print("DRY-RUN — pass --apply to truncate target tables and copy data.")
        return

    if not postgres_url.startswith(("postgresql://", "postgres://")):
        raise SystemExit("Target must be a PostgreSQL DATABASE_URL.")

    pg_conn = psycopg2.connect(postgres_url, connect_timeout=30)
    pg_conn.autocommit = False
    try:
        with pg_conn.cursor() as pg_cur:
            pg_cur.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND pid <> pg_backend_pid()
                """
            )
            pg_conn.commit()

            pg_cur.execute("SET session_replication_role = replica")
            for table in TABLES_IN_ORDER:
                pg_cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            pg_conn.commit()

            with src_engine.connect() as src_conn:
                for table in TABLES_IN_ORDER:
                    n = _copy_table_batched(src_conn, pg_cur, table)
                    if n:
                        pg_conn.commit()
                        print(f"  copied {table}: {n:,}")

            for table in SEQUENCE_TABLES:
                pg_cur.execute(
                    f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table}', 'id'),
                        COALESCE((SELECT MAX(id) FROM {table}), 1),
                        (SELECT COUNT(*) > 0 FROM {table})
                    )
                    """
                )
            pg_cur.execute("DELETE FROM alembic_version")
            pg_cur.execute(
                "INSERT INTO alembic_version (version_num) VALUES (%s)",
                (ALEMBIC_HEAD,),
            )
            pg_cur.execute("SET session_replication_role = DEFAULT")
            pg_conn.commit()
        print(f"\nDone. Alembic stamped at {ALEMBIC_HEAD}.")
    except Exception:
        pg_conn.rollback()
        raise
    finally:
        pg_conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Copy v3 SQLite DB into Postgres")
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=ROOT / "data/aircraft_safety_v3.db",
        help="Source SQLite file (default: data/aircraft_safety_v3.db)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Truncate Postgres tables and copy (default: dry-run)",
    )
    args = parser.parse_args()

    postgres_url = os.environ.get("DATABASE_URL")
    if not postgres_url:
        raise SystemExit("DATABASE_URL is required (Railway Postgres connection string).")
    if not args.sqlite_path.is_file():
        raise SystemExit(f"SQLite file not found: {args.sqlite_path}")

    push_sqlite_to_postgres(
        sqlite_path=args.sqlite_path,
        postgres_url=postgres_url,
        apply=args.apply,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
