#!/usr/bin/env python3
"""Export final FAA AIDS import list (NTSB final-import JSONL shape)."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/logs/faa_aids_enrichment_final_import_01Jun2026.jsonl"
DEFAULT_DEDUPE = ROOT / "data/logs/faa_aids_dedupe_audit.jsonl"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def _dedupe_index(path: Path) -> Dict[str, Dict[str, Any]]:
    return {r["c5"]: r for r in _load_jsonl(path) if r.get("c5")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output JSONL path",
    )
    parser.add_argument("--dedupe-audit", type=Path, default=DEFAULT_DEDUPE)
    parser.add_argument(
        "--date-suffix",
        default=date.today().strftime("%d%b%Y"),
        help="Used in default filename when --out omitted",
    )
    args = parser.parse_args()

    import os
    import sys

    sys.path.insert(0, str(ROOT))
    os.environ.setdefault(
        "DATABASE_URL",
        f"sqlite:///{ROOT / 'data/aircraft_safety_v3.db'}",
    )

    from app import create_app
    from app.models import IncidentSource

    dedupe = _dedupe_index(args.dedupe_audit)
    app = create_app()

    rows_out: List[Dict[str, Any]] = []
    with app.app_context():
        sources = (
            IncidentSource.query.filter_by(source_name="FAA_AIDS", is_active=True)
            .order_by(IncidentSource.source_record_id.asc())
            .all()
        )
        for source in sources:
            incident = source.incident
            if incident is None:
                continue
            data = source.source_data or {}
            faa_mm = data.get("faa_aids_make_model") or ""
            c5 = source.source_record_id
            audit = dedupe.get(c5, {})
            closest = audit.get("closest_asn_incident_id")
            rows_out.append(
                {
                    "aircraft_id": audit.get("mapped_aircraft_id"),
                    "bucket": "faa_aids_import",
                    "closest_asn_match": (
                        {"asn_incident_id": closest, **audit.get("score_detail", {})}
                        if closest
                        else None
                    ),
                    "date": incident.date.isoformat() if incident.date else None,
                    "fatalities": incident.fatalities,
                    "imported_aircraft_id": incident.aircraft_id,
                    "imported_incident_id": incident.id,
                    "link_reason": audit.get("dedupe_status"),
                    "link_viable": True,
                    "location": incident.location,
                    "make_model": faa_mm,
                    "faa_aids_url": source.source_url,
                    "operator": incident.operator,
                    "source_record_id": c5,
                    "unknown_aircraft": False,
                }
            )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    with args.out.open("w", encoding="utf-8") as f:
        f.write(
            f"# Final FAA AIDS import — audit shape + imported_* ids ({today})\n"
            f"# Rows: {len(rows_out)}\n"
        )
        for row in rows_out:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {"output": str(args.out), "rows": len(rows_out)},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
