"""Recompute asrs_report.aircraft_id after matcher changes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app import db
from app.ingestion.asrs_aircraft_match import (
    build_aircraft_index,
    load_asrs_overrides,
    match_asrs_make_model,
)
from app.models import Aircraft, AsrsReport


@dataclass
class RemapStats:
    total: int = 0
    unchanged: int = 0
    changed: int = 0
    cleared: int = 0


def remap_asrs_aircraft_ids(*, apply: bool, overrides_path: Path) -> RemapStats:
    aircraft_rows = Aircraft.query.all()
    index = build_aircraft_index(aircraft_rows)
    overrides = load_asrs_overrides(overrides_path)

    stats = RemapStats()
    for report in AsrsReport.query.order_by(AsrsReport.id):
        stats.total += 1
        new_id = match_asrs_make_model(
            report.aircraft_make_model_raw or "",
            index,
            overrides=overrides,
        )
        old_id = report.aircraft_id
        if new_id == old_id:
            stats.unchanged += 1
            continue
        if apply:
            report.aircraft_id = new_id
        if new_id is None and old_id is not None:
            stats.cleared += 1
        else:
            stats.changed += 1

    if apply:
        db.session.commit()
    return stats


def format_remap_stats(stats: RemapStats, *, apply: bool) -> str:
    mode = "APPLY" if apply else "DRY-RUN"
    return (
        f"remap_asrs_aircraft_ids [{mode}]: "
        f"total={stats.total} unchanged={stats.unchanged} "
        f"changed={stats.changed} cleared={stats.cleared}"
    )
