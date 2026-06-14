"""ASRS coverage summary for PRD 0010 ship gate."""

from __future__ import annotations

import json
from pathlib import Path

from app import db
from app.models import Aircraft, AsrsReport

SHIP_GATE_MIN_AIRCRAFT = 10


def build_coverage_summary() -> dict:
    rows = (
        db.session.query(
            AsrsReport.aircraft_id,
            db.func.count(AsrsReport.id).label("n"),
        )
        .filter(AsrsReport.aircraft_id.isnot(None))
        .group_by(AsrsReport.aircraft_id)
        .order_by(db.desc("n"))
        .all()
    )
    names = {a.id: a.model_name for a in Aircraft.query.all()}
    by_aircraft = [
        {"aircraft_id": aircraft_id, "model_name": names.get(aircraft_id, str(aircraft_id)), "n": n}
        for aircraft_id, n in rows
    ]
    total_rows = AsrsReport.query.count()
    matched_rows = AsrsReport.query.filter(AsrsReport.aircraft_id.isnot(None)).count()
    unmatched_rows = total_rows - matched_rows
    aircraft_with_data = len(by_aircraft)

    return {
        "total_rows": total_rows,
        "matched_rows": matched_rows,
        "unmatched_rows": unmatched_rows,
        "aircraft_with_data": aircraft_with_data,
        "ship_gate_min_aircraft": SHIP_GATE_MIN_AIRCRAFT,
        "ship_gate_pass": aircraft_with_data >= SHIP_GATE_MIN_AIRCRAFT,
        "by_aircraft": by_aircraft,
    }


def write_coverage_summary(out_path: Path) -> dict:
    summary = build_coverage_summary()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2) + "\n")
    return summary
