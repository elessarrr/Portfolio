#!/usr/bin/env python
"""FR-1: Inventory FAA AIDS fields in DB and latest ASIAS ZIP."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.spikes.faa_aids_spike_lib import (  # noqa: E402
    ARTIFACTS,
    LATEST_AIDS_ZIP_NAME,
    LATEST_AIDS_ZIP_URL,
    URL_LIKE_KEY_RE,
    ZIP_CACHE,
    resolve_latest_aids_zip_url,
)
from app.ingestion.bulk.faa_aids_bulk import (  # noqa: E402
    download_aids_zip_bytes,
    extract_aids_zip_bytes,
    iter_aids_records,
)


def _collect_keys(obj, prefix="", keys=None):
    keys = keys or set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            full = f"{prefix}.{k}" if prefix else k
            keys.add(full)
            _collect_keys(v, full, keys)
    elif isinstance(obj, list) and obj:
        _collect_keys(obj[0], prefix, keys)
    return keys


def inventory_db(session) -> dict:
    from app.models import IncidentSource

    rows = (
        session.query(IncidentSource)
        .filter_by(source_name="FAA_AIDS", is_active=True)
        .limit(100)
        .all()
    )
    all_keys = set()
    urlish_keys = set()
    for row in rows:
        data = row.source_data if isinstance(row.source_data, dict) else {}
        for k in _collect_keys(data):
            all_keys.add(k)
            if URL_LIKE_KEY_RE.search(k):
                urlish_keys.add(k)

    total = (
        session.query(IncidentSource)
        .filter_by(source_name="FAA_AIDS", is_active=True)
        .count()
    )
    with_url = (
        session.query(IncidentSource)
        .filter_by(source_name="FAA_AIDS", is_active=True)
        .filter(IncidentSource.source_url.isnot(None))
        .filter(IncidentSource.source_url != "")
        .count()
    )
    examples_with = (
        session.query(IncidentSource)
        .filter_by(source_name="FAA_AIDS", is_active=True)
        .filter(IncidentSource.source_url.isnot(None))
        .filter(IncidentSource.source_url != "")
        .limit(3)
        .all()
    )
    examples_without = (
        session.query(IncidentSource)
        .filter_by(source_name="FAA_AIDS", is_active=True)
        .filter(
            (IncidentSource.source_url.is_(None)) | (IncidentSource.source_url == "")
        )
        .limit(3)
        .all()
    )

    def _ex(r):
        return {
            "id": r.id,
            "source_record_id": r.source_record_id,
            "source_url": r.source_url,
            "c5": (r.source_data or {}).get("c5") if isinstance(r.source_data, dict) else None,
        }

    return {
        "active_rows": total,
        "rows_with_source_url": with_url,
        "sampled_rows": len(rows),
        "distinct_source_data_keys": sorted(all_keys),
        "url_like_keys": sorted(urlish_keys),
        "examples_with_url": [_ex(r) for r in examples_with],
        "examples_without_url": [_ex(r) for r in examples_without],
    }


def inventory_zip() -> dict:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    ZIP_CACHE.mkdir(parents=True, exist_ok=True)

    template = (os.environ.get("FAA_AIDS_ZIP_URL_TEMPLATE") or "").strip()
    zip_url = LATEST_AIDS_ZIP_URL
    zip_source = "LATEST_AIDS_ZIP_URL constant (ASIAS a2020_26)"
    if template:
        zip_source = f"FAA_AIDS_ZIP_URL_TEMPLATE (year-only not used; direct URL preferred)"

    zip_path = ZIP_CACHE / LATEST_AIDS_ZIP_NAME
    if not zip_path.exists():
        print(f"Resolving fresh download URL for {LATEST_AIDS_ZIP_NAME} …")
        try:
            zip_url = resolve_latest_aids_zip_url()
            zip_source = "ASIAS download page (fresh blob ck)"
        except Exception as exc:
            print(f"WARN: could not refresh blob URL ({exc}); trying cached constant")
        print(f"Downloading {LATEST_AIDS_ZIP_NAME} …")
        import httpx

        with httpx.Client(
            follow_redirects=True,
            timeout=120.0,
            headers={"User-Agent": "AircraftSafetyTracker/1.0"},
        ) as client:
            client.get("https://www.asias.faa.gov/apex/f?p=100:189::::NO")
            resp = client.get(zip_url)
            resp.raise_for_status()
            data = resp.content
        zip_path.write_bytes(data)
    else:
        print(f"Using cached {zip_path}")

    from app.ingestion.bulk.faa_aids_bulk import extract_aids_zip_bytes, iter_aids_records

    extract_dir = ZIP_CACHE / "extracted"
    paths = extract_aids_zip_bytes(zip_path.read_bytes(), extract_dir)
    headers = []
    url_cols = {}
    row_count = 0
    for rec in iter_aids_records(paths):
        row_count += 1
        if not headers:
            headers = list(rec.keys())
            for h in headers:
                if URL_LIKE_KEY_RE.search(h):
                    url_cols[h] = 0
        for h in url_cols:
            val = (rec.get(h) or "").strip()
            if val and ("http" in val.lower() or "www." in val.lower()):
                url_cols[h] += 1
        if row_count >= 5000:
            break

    return {
        "zip_path": str(zip_path),
        "zip_url": zip_url,
        "zip_source_note": zip_source,
        "faa_aids_zip_url_template_in_env": bool(template),
        "rows_scanned": row_count,
        "columns": headers,
        "url_like_columns_nonempty_in_sample": url_cols,
    }


def main():
    from run import app
    from app import db

    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    with app.app_context():
        db_info = inventory_db(db.session)

    try:
        zip_info = inventory_zip()
    except Exception as exc:
        zip_info = {
            "error": str(exc),
            "zip_path": None,
            "note": "Manual download from https://www.asias.faa.gov/apex/f?p=100:189::::NO",
        }

    # Compare column sets
    db_cols = set(db_info["distinct_source_data_keys"])
    zip_cols = set(zip_info.get("columns") or [])
    overlap = sorted(db_cols & zip_cols)
    only_db = sorted(db_cols - zip_cols)[:50]
    only_zip = sorted(zip_cols - db_cols)[:50]

    out = {
        "database": db_info,
        "latest_zip": zip_info,
        "comparison": {
            "overlapping_columns_count": len(overlap),
            "only_in_db_sample": only_db,
            "only_in_zip": only_zip,
            "url_columns_in_zip": zip_info.get("url_like_columns_nonempty_in_sample"),
        },
        "field_map_importer": {
            "c5": "source_record_id (control number)",
            "c9": "date",
            "c203": "registration",
            "c23": "make (partial make_model)",
            "c24": "model (partial make_model)",
            "c14": "city",
            "c13": "state",
            "c76": "fatalities",
            "c119": "description/narrative",
            "c120": "operator",
        },
    }

    out_path = ARTIFACTS / "faa-aids-inventory.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(
        f"DB: {db_info['active_rows']} active FAA_AIDS, "
        f"{db_info['rows_with_source_url']} with source_url"
    )
    if zip_info.get("error"):
        print(f"ZIP: download failed — {zip_info['error']}")
    else:
        print(
            f"ZIP: scanned {zip_info['rows_scanned']} rows, "
            f"{len(zip_info.get('columns') or [])} columns"
        )


if __name__ == "__main__":
    main()
