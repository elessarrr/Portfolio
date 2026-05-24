#!/usr/bin/env python
"""FR-3.1: Export stratified 500-row FAA AIDS sample."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.spikes.faa_aids_spike_lib import SAMPLES  # noqa: E402

SAMPLE_PATH = SAMPLES / "faa-aids-url-sample-500.csv"
SAMPLE_SIZE = 500


def main():
    from run import app
    from app import db
    from sqlalchemy import text

    SAMPLES.mkdir(parents=True, exist_ok=True)

    sql = text(
        """
        WITH base AS (
            SELECT
                s.id AS incident_source_id,
                s.source_record_id,
                i.date,
                i.registration,
                i.fatalities,
                s.source_url,
                CAST(strftime('%Y', i.date) AS INTEGER) AS yr,
                CASE WHEN i.fatalities > 0 THEN 1 ELSE 0 END AS is_fatal,
                CASE
                    WHEN i.registration IS NULL OR TRIM(i.registration) = '' THEN 0
                    ELSE 1
                END AS has_reg
            FROM incident_source s
            JOIN incident i ON i.id = s.incident_id
            WHERE s.source_name = 'FAA_AIDS' AND s.is_active = 1
              AND s.source_record_id IS NOT NULL
              AND TRIM(s.source_record_id) != ''
        ),
        bucketed AS (
            SELECT *,
                NTILE(10) OVER (ORDER BY yr) AS year_bucket,
                ROW_NUMBER() OVER (
                    PARTITION BY yr / 5, is_fatal, has_reg
                    ORDER BY RANDOM()
                ) AS rn
            FROM base
        )
        SELECT incident_source_id, source_record_id, date, registration,
               fatalities, source_url, yr AS year
        FROM bucketed
        WHERE rn = 1
        LIMIT :lim
        """
    )

    with app.app_context():
        rows = db.session.execute(sql, {"lim": SAMPLE_SIZE}).fetchall()
        if len(rows) < SAMPLE_SIZE:
            extra = db.session.execute(
                text(
                    """
                    SELECT s.id, s.source_record_id, i.date, i.registration,
                           i.fatalities, s.source_url,
                           CAST(strftime('%Y', i.date) AS INTEGER)
                    FROM incident_source s
                    JOIN incident i ON i.id = s.incident_id
                    WHERE s.source_name = 'FAA_AIDS' AND s.is_active = 1
                    ORDER BY RANDOM()
                    LIMIT :lim
                    """
                ),
                {"lim": SAMPLE_SIZE - len(rows)},
            ).fetchall()
            seen = {r[0] for r in rows}
            for r in extra:
                if r[0] not in seen:
                    rows.append(r)
                if len(rows) >= SAMPLE_SIZE:
                    break

    with SAMPLE_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "incident_source_id",
                "source_record_id",
                "date",
                "registration",
                "fatalities",
                "source_url",
                "year",
            ]
        )
        for r in rows:
            date_val = r[2]
            if date_val and hasattr(date_val, "isoformat"):
                date_val = date_val.isoformat()
            w.writerow(
                [
                    r[0],
                    r[1],
                    date_val or "",
                    r[3] or "",
                    r[4] if r[4] is not None else "",
                    r[5] or "",
                    r[6] or "",
                ]
            )

    print(f"Wrote {len(rows)} rows to {SAMPLE_PATH}")


if __name__ == "__main__":
    main()
