"""Import ASRS rows from Hugging Face dataset or DBOL CSV into asrs_report."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app import db
from app.ingestion.asrs_aircraft_match import (
    build_aircraft_index,
    load_asrs_overrides,
    match_asrs_make_model,
)
from app.models import Aircraft, AsrsReport

HF_DATASET = "elihoole/asrs-aviation-reports"

HF_FIELD_ACN = "acn_num_ACN"
HF_FIELD_MAKE_MODEL = "Aircraft 1.2_Make Model Name"
HF_FIELD_PHASE = "Aircraft 1.9_Flight Phase"
HF_FIELD_FACTORS = "Assessments_Contributing Factors / Situations"
HF_FIELD_PRIMARY = "Assessments.1_Primary Problem"
HF_FIELD_SYNOPSIS = "Report 1.2_Synopsis"
HF_FIELD_DATE = "Time_Date"


@dataclass
class ImportStats:
    seen: int = 0
    imported: int = 0
    duplicate: int = 0
    unmatched: int = 0
    skipped: int = 0


def parse_report_year(date_raw: str | None) -> int | None:
    if not date_raw:
        return None
    digits = re.sub(r"\D", "", str(date_raw))
    if len(digits) >= 4:
        year = int(digits[-4:])
        if 1950 <= year <= 2100:
            return year
    if len(digits) == 6:
        yy = int(digits[-2:])
        return 1900 + yy if yy >= 50 else 2000 + yy
    return None


def parse_factors_raw(raw: str | None) -> str:
    if not raw or not str(raw).strip():
        return json.dumps([])
    parts = [p.strip() for p in re.split(r"[;,]", str(raw)) if p.strip()]
    return json.dumps(parts)


def normalize_row(raw: dict, source: str) -> dict | None:
    acn = str(raw.get("acn") or "").strip()
    if not acn:
        return None
    return {
        "acn": acn,
        "aircraft_make_model_raw": (raw.get("make_model") or "").strip() or None,
        "primary_problem": (raw.get("primary_problem") or "").strip() or None,
        "contributing_factors": parse_factors_raw(raw.get("contributing_factors")),
        "phase_of_flight": (raw.get("phase_of_flight") or "").strip() or None,
        "report_year": raw.get("report_year"),
        "synopsis": (raw.get("synopsis") or "").strip() or None,
        "source": source,
    }


def row_from_hf_record(record: dict) -> dict | None:
    return normalize_row(
        {
            "acn": record.get(HF_FIELD_ACN),
            "make_model": record.get(HF_FIELD_MAKE_MODEL),
            "primary_problem": record.get(HF_FIELD_PRIMARY),
            "contributing_factors": record.get(HF_FIELD_FACTORS),
            "phase_of_flight": record.get(HF_FIELD_PHASE),
            "report_year": parse_report_year(record.get(HF_FIELD_DATE)),
            "synopsis": record.get(HF_FIELD_SYNOPSIS),
        },
        source="huggingface",
    )


def row_from_csv_record(record: dict) -> dict | None:
    lowered = {k.strip().lower(): v for k, v in record.items()}

    def pick(*names: str) -> str | None:
        for name in names:
            val = lowered.get(name.lower())
            if val is not None and str(val).strip():
                return str(val).strip()
        return None

    return normalize_row(
        {
            "acn": pick("acn", "acn_num_acn", "accession number"),
            "make_model": pick(
                "aircraft 1.2_make model name",
                "make model name",
                "aircraft make model",
            ),
            "primary_problem": pick("assessments.1_primary problem", "primary problem"),
            "contributing_factors": pick(
                "assessments_contributing factors / situations",
                "contributing factors / situations",
                "contributing factors",
            ),
            "phase_of_flight": pick("aircraft 1.9_flight phase", "flight phase"),
            "report_year": parse_report_year(pick("time_date", "date", "report date")),
            "synopsis": pick("report 1.2_synopsis", "synopsis"),
        },
        source="dbol_csv",
    )


def iter_hf_rows():
    from datasets import load_dataset

    for split in ("train", "validation", "test"):
        ds = load_dataset(HF_DATASET, split=split)
        for record in ds:
            row = row_from_hf_record(record)
            if row:
                yield row


def iter_csv_rows(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for record in reader:
            row = row_from_csv_record(record)
            if row:
                yield row


def import_asrs_rows(
    rows,
    *,
    apply: bool,
    overrides_path: Path | None = None,
) -> ImportStats:
    stats = ImportStats()
    aircraft_rows = Aircraft.query.all()
    index = build_aircraft_index(aircraft_rows)
    overrides = load_asrs_overrides(overrides_path) if overrides_path else {}
    existing = {r.acn for r in AsrsReport.query.with_entities(AsrsReport.acn).all()}

    for row in rows:
        stats.seen += 1
        acn = row["acn"]
        if acn in existing:
            stats.duplicate += 1
            continue

        aircraft_id = match_asrs_make_model(
            row.get("aircraft_make_model_raw") or "",
            index,
            overrides,
        )
        if aircraft_id is None:
            stats.unmatched += 1

        if not apply:
            stats.imported += 1
            continue

        db.session.add(
            AsrsReport(
                acn=acn,
                aircraft_make_model_raw=row.get("aircraft_make_model_raw"),
                primary_problem=row.get("primary_problem"),
                contributing_factors=row.get("contributing_factors"),
                phase_of_flight=row.get("phase_of_flight"),
                report_year=row.get("report_year"),
                synopsis=row.get("synopsis"),
                source=row.get("source") or "huggingface",
                imported_at=datetime.now(timezone.utc).replace(tzinfo=None),
                aircraft_id=aircraft_id,
            )
        )
        existing.add(acn)
        stats.imported += 1

    if apply:
        db.session.commit()
    return stats


def format_stats(stats: ImportStats) -> str:
    return (
        f"seen={stats.seen} imported={stats.imported} "
        f"duplicate={stats.duplicate} unmatched={stats.unmatched} skipped={stats.skipped}"
    )
