#!/usr/bin/env python3
"""
NTSB Aviation Crash Data Downloader v2
=======================================
Downloads remaining NTSB aviation records (from 1988-07-01 to 2025-12-31)
by calendar year. No binary search needed — each year has ~1500-2500 records.

Usage:
  python3 ntsb_data_downloader_v2.py
"""

import json
import subprocess
import os
import time
import zipfile
from datetime import datetime
from pathlib import Path


API_BASE = "https://data.ntsb.gov/carol-main-public/api"
DELAY = 5  # seconds between API calls
EXPORT_TIMEOUT = 300  # 5 minutes for export (large files take time)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def curl_post(url, data, timeout=30):
    resp = subprocess.run(
        ["curl", "-s", f"--max-time", str(timeout),
         "-X", "POST", url,
         "-H", "Content-Type: application/json",
         "-d", data],
        capture_output=True, text=True, timeout=timeout + 10
    )
    return resp.stdout.strip()


def create_session(retries=3):
    for i in range(retries):
        resp = curl_post(f"{API_BASE}/Session/CreateSession", "", timeout=30)
        if resp and resp.isdigit():
            return resp
        log(f"  Session creation failed (attempt {i+1}). Retrying in {10*(i+1)}s...")
        time.sleep(10 * (i + 1))
    raise RuntimeError("Failed to create session")


def count_records(session_id, date_from, date_to):
    query = {
        "ResultSetSize": 1, "ResultSetOffset": 0,
        "SortColumn": None, "SortDescending": False,
        "QueryGroups": [{"QueryRules": [
            {"FieldName": "Mode", "Operator": "is", "Values": ["Aviation"], "Columns": ["Event.Mode"]},
            {"FieldName": "EventDate", "Operator": "is in the range",
             "Values": [date_from, date_to], "Columns": ["Event.EventDate"]}
        ], "AndOr": "And"}],
        "AndOr": "And", "TargetCollection": "cases", "SessionId": session_id
    }
    resp = curl_post(f"{API_BASE}/Query/Main", json.dumps(query), timeout=30)
    if not resp or resp.startswith("<!"):
        return -1
    data = json.loads(resp)
    return data.get("ResultListCount", 0)


def download_batch(session_id, date_from, date_to, output_path, retries=3):
    output_path = output_path.resolve()
    export_query = {
        "ResultSetSize": 1, "ResultSetOffset": 0,
        "SortColumn": None, "SortDescending": True,
        "QueryGroups": [{"QueryRules": [
            {"FieldName": "Mode", "Operator": "is", "Values": ["Aviation"], "Columns": ["Event.Mode"]},
            {"FieldName": "EventDate", "Operator": "is in the range",
             "Values": [date_from, date_to], "Columns": ["Event.EventDate"]}
        ], "AndOr": "And"}],
        "AndOr": "And", "TargetCollection": "cases",
        "SessionId": session_id,
        "ExportFormat": "data"
    }

    zip_path = output_path.with_suffix(".zip")

    for attempt in range(retries):
        subprocess.run(
            ["curl", "-s", f"--max-time", str(EXPORT_TIMEOUT),
             "-X", "POST", f"{API_BASE}/Query/FileExport",
             "-H", "Content-Type: application/json",
             "-d", json.dumps(export_query),
             "--output", str(zip_path)],
            capture_output=True, text=True, timeout=EXPORT_TIMEOUT + 10
        )

        if not zip_path.exists():
            log(f"    Download attempt {attempt+1}: no file received")
            time.sleep(30 * (attempt + 1))
            continue

        zip_size = zip_path.stat().st_size
        if zip_size < 100:
            log(f"    Download attempt {attempt+1}: file too small ({zip_size} bytes)")
            os.remove(zip_path)
            time.sleep(30 * (attempt + 1))
            continue

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                json_files = [f for f in zf.namelist() if f.endswith('.json')]
                if not json_files:
                    log(f"    No JSON in zip: {zf.namelist()}")
                    os.remove(zip_path)
                    time.sleep(30 * (attempt + 1))
                    continue

                zf.extract(json_files[0], output_path.parent)
                extracted = output_path.parent / json_files[0]
                if extracted != output_path:
                    os.rename(extracted, output_path)

                with open(output_path, 'r') as f:
                    data = json.load(f)
                    record_count = len(data) if isinstance(data, list) else 0

                os.remove(zip_path)
                # Clean stray files
                for stray in output_path.parent.glob("cases*.json"):
                    if stray != output_path:
                        os.remove(stray)

                return record_count

        except (zipfile.BadZipFile, Exception) as e:
            log(f"    Download attempt {attempt+1}: {e}")
            if zip_path.exists():
                os.remove(zip_path)
            time.sleep(30 * (attempt + 1))

    return 0


def main():
    output_dir = Path("ntsb_data").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Batches: calendar year from July 1988 through 2025
    batches = [
        ("1988-07-01", "1988-12-31"),
    ]
    for year in range(1989, 2026):
        batches.append((f"{year}-01-01", f"{year}-12-31"))

    log(f"NTSB Data Downloader v2 (by calendar year)")
    log(f"  Batches: {len(batches)}")
    log(f"  Output: {output_dir}")
    log(f"  First batch: {batches[0]}")
    log("")

    session_id = create_session()
    log(f"  Session: {session_id}")
    log("")

    total_downloaded = 0
    session_refresh_counter = 0

    for i, (date_from, date_to) in enumerate(batches, 1):
        out_file = output_dir / f"ntsb_batch_{i:02d}_{date_from}_{date_to}.json"

        # Skip if already downloaded
        if out_file.exists():
            with open(out_file) as f:
                existing = len(json.load(f))
            log(f"[{i:02d}/{len(batches)}] SKIP (exists): {date_from} to {date_to} ({existing:,} records)")
            total_downloaded += existing
            continue

        # Refresh session every 10 batches
        session_refresh_counter += 1
        if session_refresh_counter >= 10:
            log(f"[{i:02d}/{len(batches)}] Refreshing session...")
            session_id = create_session()
            session_refresh_counter = 0
            time.sleep(DELAY)

        log(f"[{i:02d}/{len(batches)}] {date_from} to {date_to}")

        # Count
        count = count_records(session_id, date_from, date_to)
        time.sleep(DELAY)
        log(f"  Records: {count:,}")

        if count <= 0:
            log(f"  WARNING: No records, skipping download")
            continue

        # Download
        log(f"  Downloading...")
        downloaded = download_batch(session_id, date_from, date_to, out_file)

        if downloaded == 0:
            log(f"  WARNING: Download failed")
            continue

        file_mb = out_file.stat().st_size / (1024 * 1024)
        total_downloaded += downloaded
        log(f"  SUCCESS: {downloaded:,} records ({file_mb:.1f} MB)")
        log(f"  Saved: {out_file}")
        log("")

    log("=" * 60)
    log(f"COMPLETE: {total_downloaded:,} total records across {len(batches)} batches")
    log(f"Output: {output_dir}")
    log("=" * 60)


if __name__ == "__main__":
    main()
