#!/usr/bin/env python3
"""
NTSB Aviation Crash Data Downloader
====================================
Downloads all NTSB aviation incident records from a start date to end date,
in chunks that stay under the 10,000 record export limit.

Uses the CAROL Query API directly (no browser automation needed).

Usage:
  python3 ntsb_data_downloader.py
  python3 ntsb_data_downloader.py --start 1985-01-01 --end 2025-12-31 --limit 9000
"""

import json
import subprocess
import os
import sys
import time
import argparse
import zipfile
from datetime import datetime, timedelta
from pathlib import Path


API_BASE = "https://data.ntsb.gov/carol-main-public/api"
DELAY_BETWEEN_CALLS = 12  # seconds between API calls to avoid rate limiting


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def curl_post(url, data):
    """Make a POST request with curl. Returns (response_text, error_string)."""
    result = subprocess.run(
        ["curl", "-s", "--max-time", "300",
         "-X", "POST", url,
         "-H", "Content-Type: application/json",
         "-d", data],
        capture_output=True, text=True
    )
    return result.stdout, result.stderr


def curl_post_binary(url, data, output_path):
    """Make a POST request with curl, save binary output to file."""
    result = subprocess.run(
        ["curl", "-s", "--max-time", "300",
         "-X", "POST", url,
         "-H", "Content-Type: application/json",
         "-d", data,
         "--output", output_path],
        capture_output=True, text=True
    )
    return result.stdout, result.stderr


def create_session(max_retries=3):
    """Create a new CAROL session and return the session ID."""
    for attempt in range(max_retries):
        resp, _ = curl_post(f"{API_BASE}/Session/CreateSession", "")
        resp_text = resp.strip()
        if resp_text.isdigit():
            return resp_text
        if "403" in resp_text or "forbidden" in resp_text.lower():
            wait = 30 * (attempt + 1)
            log(f"  Rate limited on session creation (attempt {attempt+1}/{max_retries}). Waiting {wait}s...")
            time.sleep(wait)
        else:
            log(f"  Unexpected session response: {resp_text[:200]}")
    raise RuntimeError("Failed to create session after retries")


def count_records(session_id, date_from, date_to):
    """Count aviation records for a given date range (fast, returns count only)."""
    query = {
        "ResultSetSize": 1,
        "ResultSetOffset": 0,
        "SortColumn": None,
        "SortDescending": False,
        "QueryGroups": [{
            "QueryRules": [
                {
                    "FieldName": "Mode",
                    "Operator": "is",
                    "Values": ["Aviation"],
                    "Columns": ["Event.Mode"]
                },
                {
                    "FieldName": "EventDate",
                    "Operator": "is in the range",
                    "Values": [date_from, date_to],
                    "Columns": ["Event.EventDate"]
                }
            ],
            "AndOr": "And"
        }],
        "AndOr": "And",
        "TargetCollection": "cases",
        "SessionId": session_id
    }

    resp, _ = curl_post(f"{API_BASE}/Query/Main", json.dumps(query))
    try:
        resp_data = json.loads(resp)
        return resp_data.get("ResultListCount", 0)
    except json.JSONDecodeError:
        if "403" in resp:
            raise RuntimeError("Rate limited/blocked by NTSB (Cloudflare 403)")
        return -1


def find_batch_end_date(session_id, start_date, end_date, max_records):
    """
    Binary search to find the latest date where the record count from start_date
    is at or just below max_records.
    
    Returns (optimal_end_date, actual_count).
    """
    # First check: is the full range already under the limit?
    count = count_records(session_id, start_date, end_date)
    time.sleep(DELAY_BETWEEN_CALLS)
    if count <= max_records:
        return end_date, count

    # Binary search for the right cutoff
    start = datetime.strptime(start_date, "%Y-%m-%d")
    low = start
    high = datetime.strptime(end_date, "%Y-%m-%d")
    best_date = None
    best_count = 0

    iterations = 0
    while low <= high and iterations < 60:
        iterations += 1
        mid = low + (high - low) // 2
        mid_str = mid.strftime("%Y-%m-%d")

        count = count_records(session_id, start_date, mid_str)
        
        # Handle rate limiting
        if "403" in str(count) or count < 0:
            log(f"    Rate limited during binary search. Waiting 60s...")
            time.sleep(60)
            continue

        time.sleep(DELAY_BETWEEN_CALLS)

        if count <= max_records:
            if count > best_count:
                best_count = count
                best_date = mid_str
            low = mid + timedelta(days=1)
        else:
            high = mid - timedelta(days=1)

        if iterations % 5 == 0:
            log(f"    Binary search: day {(mid - start).days}, count={count}")

    return best_date, best_count


def download_batch(session_id, date_from, date_to, output_path):
    """
    Download a batch of records as JSON and save to output_path.
    Returns the number of records downloaded.
    """
    output_path = output_path.resolve()

    export_query = {
        "ResultSetSize": 1,
        "ResultSetOffset": 0,
        "SortColumn": None,
        "SortDescending": True,
        "QueryGroups": [{
            "QueryRules": [
                {
                    "FieldName": "Mode",
                    "Operator": "is",
                    "Values": ["Aviation"],
                    "Columns": ["Event.Mode"]
                },
                {
                    "FieldName": "EventDate",
                    "Operator": "is in the range",
                    "Values": [date_from, date_to],
                    "Columns": ["Event.EventDate"]
                }
            ],
            "AndOr": "And"
        }],
        "AndOr": "And",
        "TargetCollection": "cases",
        "SessionId": session_id,
        "ExportFormat": "data"
    }

    zip_path = output_path.with_suffix(".zip")
    resp, err = curl_post_binary(
        f"{API_BASE}/Query/FileExport",
        json.dumps(export_query),
        str(zip_path)
    )

    # Check if downloaded successfully
    if not zip_path.exists():
        log(f"    ERROR: Zip file was not downloaded")
        return 0

    zip_size = zip_path.stat().st_size
    log(f"    Downloaded zip: {zip_size:,} bytes")

    if zip_size < 100:
        # Likely an error response
        log(f"    ERROR: Zip too small, likely an error response")
        try:
            with open(zip_path, 'rb') as f:
                content = f.read(500).decode('utf-8', errors='replace')
                log(f"    Response: {content[:300]}")
        except:
            pass
        if "403" in content if 'content' in dir() else False:
            log(f"    Rate limited/blocked. Need to wait longer.")
        return 0

    try:
        # Extract the JSON from the zip
        with zipfile.ZipFile(zip_path, 'r') as zf:
            json_files = [f for f in zf.namelist() if f.endswith('.json')]
            if not json_files:
                log(f"    ERROR: No JSON file in zip. Contents: {zf.namelist()}")
                return 0

            # Extract JSON file
            zf.extract(json_files[0], output_path.parent)
            extracted = output_path.parent / json_files[0]
            
            # Rename to our desired output path
            if extracted != output_path:
                os.rename(extracted, output_path)

            # Read and count records
            with open(output_path, 'r') as f:
                data = json.load(f)
                record_count = len(data) if isinstance(data, list) else 0
    except zipfile.BadZipFile:
        log(f"    ERROR: Not a valid zip file")
        return 0

    # Clean up the zip
    os.remove(zip_path)

    # Clean up any leftover files
    for leftover in output_path.parent.glob("cases*.json"):
        if leftover != output_path:
            os.remove(leftover)

    return record_count


def main():
    parser = argparse.ArgumentParser(description="Download NTSB aviation crash data")
    parser.add_argument("--start", default="1985-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2025-12-31", help="End date (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, default=9000, help="Max records per batch")
    parser.add_argument("--output", default=None, help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output).resolve() if args.output else Path(f"ntsb_data_{args.start}_{args.end}")
    output_dir.mkdir(parents=True, exist_ok=True)

    log(f"NTSB Aviation Data Downloader")
    log(f"  Date range: {args.start} to {args.end}")
    log(f"  Max records per batch: {args.limit}")
    log(f"  Delay between API calls: {DELAY_BETWEEN_CALLS}s")
    log(f"  Output directory: {output_dir}")
    log("")

    # Create session
    log("Creating API session...")
    session_id = create_session()
    log(f"  Session ID: {session_id}")
    log("")

    # Get total count
    log("Counting total records...")
    total_count = count_records(session_id, args.start, args.end)
    time.sleep(DELAY_BETWEEN_CALLS)
    log(f"  Total aviation records: {total_count:,}")
    
    if total_count == 0:
        log("  No records found!")
        return

    est_batches = (total_count // args.limit) + 1
    log(f"  Estimated batches: {est_batches}")
    log(f"  This will take roughly {est_batches * 5} minutes")
    log("")

    # Download in batches
    batch_num = 0
    current_start = args.start
    total_downloaded = 0

    while current_start <= args.end:
        batch_num += 1
        log(f"{'='*60}")
        log(f"BATCH {batch_num}/{est_batches+1}")
        log(f"  Starting from: {current_start}")
        log(f"  Finding optimal end date (binary search)...")

        # Recreate session before each batch (sessions may expire)
        log(f"  Creating fresh session for this batch...")
        session_id = create_session()
        time.sleep(DELAY_BETWEEN_CALLS)

        batch_end, batch_count = find_batch_end_date(
            session_id, current_start, args.end, args.limit
        )

        if batch_end is None:
            log(f"  ERROR: Could not find valid range from {current_start}")
            break

        log(f"  Range: {current_start} to {batch_end}")
        log(f"  Expected records: {batch_count:,}")
        log(f"  Starting download (this may take 1-5 minutes)...")

        batch_file = output_dir / f"ntsb_aviation_batch_{batch_num:03d}_{current_start}_{batch_end}.json"
        record_count = download_batch(session_id, current_start, batch_end, batch_file)
        
        if record_count == 0:
            log(f"  WARNING: Download returned 0 records, stopping")
            break

        total_downloaded += record_count
        file_size_mb = batch_file.stat().st_size / (1024 * 1024)
        log(f"  Downloaded: {record_count:,} records ({file_size_mb:.1f} MB)")
        log(f"  Saved to: {batch_file}")

        current_start = (datetime.strptime(batch_end, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

        # Pause between batches
        log(f"  Pausing before next batch...")
        time.sleep(15)
        log("")

    # Summary
    log("=" * 60)
    log(f"DOWNLOAD COMPLETE")
    log(f"  Batches: {batch_num}")
    log(f"  Total records: {total_downloaded:,}")
    log(f"  Expected: {total_count:,}")
    log(f"  Output: {output_dir}")
    log("=" * 60)


if __name__ == "__main__":
    main()
