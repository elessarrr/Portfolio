#!/usr/bin/env python3
"""Build FAA AIDS make_model → aircraft mapping (catalog pages only, no bloat)."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, List, Set

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "data/logs/faa_aids_make_model_catalog.jsonl"
DEFAULT_OUT = ROOT / "data/config/faa_aids_make_model_to_aircraft.jsonl"
DEFAULT_DB = ROOT / "data/aircraft_safety_v3.db"
MAX_CATALOG_AIRCRAFT_ID = 113


def _load_jsonl(path: Path) -> List[dict[str, Any]]:
    rows: List[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def _load_asn_ntsb_catalog(db_path: Path) -> Set[str]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT model_name FROM aircraft WHERE id <= ? ORDER BY model_name",
        (MAX_CATALOG_AIRCRAFT_ID,),
    )
    names = {r[0] for r in cur.fetchall()}
    conn.close()
    return names


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--approved-date", default=date.today().isoformat())
    args = parser.parse_args()

    from app.ingestion.faa_variant_resolution import resolve_faa_canonical_model_name

    catalog_rows = _load_jsonl(args.catalog)
    catalog_names = _load_asn_ntsb_catalog(args.db)
    if not catalog_names:
        raise SystemExit(f"No catalog pages with id <= {MAX_CATALOG_AIRCRAFT_ID}")

    approved: List[dict[str, Any]] = []
    actions: dict[str, int] = {}
    for row in catalog_rows:
        faa_mm = row["faa_make_model"]
        page = resolve_faa_canonical_model_name(faa_mm, catalog_names)
        if page:
            entry = {
                "faa_make_model": faa_mm,
                "canonical_model_name": page,
                "action": "map_to_existing",
                "notes": f"{row.get('incident_count', 0)} FAA row(s); catalog id<={MAX_CATALOG_AIRCRAFT_ID}",
            }
        else:
            entry = {
                "faa_make_model": faa_mm,
                "canonical_model_name": faa_mm,
                "action": "skip",
                "notes": f"{row.get('incident_count', 0)} FAA row(s); no catalog match",
            }
        actions[entry["action"]] = actions.get(entry["action"], 0) + 1
        approved.append(entry)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        f.write(
            f"# FAA AIDS mapping — refined {args.approved_date} — "
            f"{len(approved)} entries — catalog-only targets\n"
        )
        for entry in approved:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "output": str(args.out),
                "entries": len(approved),
                "actions": actions,
                "catalog_pages": len(catalog_names),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
