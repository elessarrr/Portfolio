#!/usr/bin/env python3
"""Download FAA AIDS bulk ZIP, parse CSV, export Boeing/Airbus rows to JSONL (PRD 0007 FR-2)."""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import os
import re
import sqlite3
import sys
import zipfile
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ingestion.importers.base import is_boeing_or_airbus_make_model

logger = logging.getLogger(__name__)

FAA_ACCIDENT_PAGE = "https://www.faa.gov/data_research/accident_incident/"
DEFAULT_OUT = ROOT / "data/raw/faa_aids_boeing_airbus.jsonl"
DEFAULT_CACHE_ZIP = ROOT / "data/raw/faa_aids_latest.zip"


def _looks_like_csv(text: str) -> bool:
    head = (text or "")[:500].lstrip().lower()
    if head.startswith("<html") or head.startswith("<!doctype"):
        return False
    return True


def _discover_zip_urls(html: str, base_url: str) -> List[str]:
    urls: List[str] = []
    for match in re.finditer(r'href=["\']([^"\']+\.zip)["\']', html, re.I):
        href = match.group(1)
        urls.append(urljoin(base_url, href))
    # Prefer AIDS bulk archives (a20xx pattern) over one-off incident zips
    urls.sort(
        key=lambda u: (
            0 if re.search(r"a20\d{2}", u, re.I) else 1,
            -len(u),
        )
    )
    return urls


def download_faa_aids_zip(
    *,
    cache_path: Path,
    zip_url: Optional[str] = None,
    timeout: float = 120.0,
) -> Path:
    if zip_url:
        candidates = [zip_url]
    else:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            resp = client.get(FAA_ACCIDENT_PAGE)
            resp.raise_for_status()
            if not _looks_like_csv(resp.text):
                candidates = _discover_zip_urls(resp.text, FAA_ACCIDENT_PAGE)
            else:
                candidates = []
        if not candidates:
            raise RuntimeError(
                "No .zip links found on FAA accident/incident page — pass --zip-url or --from-v2-db"
            )

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    last_error: Optional[Exception] = None
    for url in candidates:
        try:
            logger.info("Downloading %s", url)
            with httpx.Client(follow_redirects=True, timeout=timeout) as client:
                resp = client.get(url)
                resp.raise_for_status()
                content = resp.content
            if not content[:4] == b"PK\x03\x04":
                text = content[:500].decode("utf-8", errors="replace")
                if not _looks_like_csv(text):
                    raise ValueError(
                        "FAA returned HTML instead of CSV — check URL or try again"
                    )
            cache_path.write_bytes(content)
            return cache_path
        except Exception as exc:
            last_error = exc
            logger.warning("Download failed for %s: %s", url, exc)
    raise RuntimeError(f"All ZIP download attempts failed: {last_error}")


def _read_csv_from_zip(zip_path: Path) -> Tuple[List[Dict[str, str]], str]:
    with zipfile.ZipFile(zip_path) as zf:
        csv_names = [
            n
            for n in zf.namelist()
            if n.lower().endswith((".csv", ".txt", ".tab"))
        ]
        if not csv_names:
            raise ValueError(f"No CSV/TXT inside ZIP: {zip_path}")
        csv_names.sort(key=lambda n: (0 if "aids" in n.lower() else 1, -len(n)))
        name = csv_names[0]
        raw_bytes = zf.read(name)
    for encoding in ("utf-8", "latin-1"):
        try:
            text = raw_bytes.decode(encoding)
            if not _looks_like_csv(text):
                raise ValueError(
                    "FAA returned HTML instead of CSV — check URL or try again"
                )
            logger.info("Decoded CSV with encoding %s", encoding)
            break
        except UnicodeDecodeError:
            text = None
    else:
        text = raw_bytes.decode("latin-1", errors="replace")
        encoding = "latin-1(replace)"
        logger.info("Decoded CSV with encoding %s", encoding)

    delimiter = "\t" if text.count("\t") > text.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    rows = [dict(row) for row in reader]
    return rows, encoding


def _faa_make_model(row: Dict[str, str]) -> str:
    make = (row.get("c23") or "").strip()
    model = (row.get("c24") or "").strip()
    return f"{make} {model}".strip() if model else make


def _row_passes_boeing_airbus_filter(row: Dict[str, str]) -> bool:
    make = (row.get("c23") or "").strip()
    if not make:
        return False
    return is_boeing_or_airbus_make_model(_faa_make_model(row))


def _has_valid_c5(row: Dict[str, str]) -> bool:
    return bool((row.get("c5") or "").strip())


def _has_valid_date(row: Dict[str, str]) -> bool:
    return bool((row.get("c9") or "").strip())


def export_rows_from_csv(rows: Iterable[Dict[str, str]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    written: List[Dict[str, Any]] = []
    stats = {
        "total_csv_rows": 0,
        "boeing_airbus_written": 0,
        "skipped_not_boeing_airbus": 0,
        "skipped_no_c5": 0,
        "skipped_no_date": 0,
    }
    for row in rows:
        stats["total_csv_rows"] += 1
        if not _row_passes_boeing_airbus_filter(row):
            stats["skipped_not_boeing_airbus"] += 1
            continue
        if not _has_valid_c5(row):
            stats["skipped_no_c5"] += 1
            continue
        if not _has_valid_date(row):
            stats["skipped_no_date"] += 1
            continue
        written.append(dict(row))
        stats["boeing_airbus_written"] += 1
    return written, stats


def export_from_v2_db(db_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT source_data FROM incident_source WHERE source_name = 'FAA_AIDS' ORDER BY id"
    )
    written: List[Dict[str, Any]] = []
    stats = {
        "total_csv_rows": 0,
        "boeing_airbus_written": 0,
        "skipped_not_boeing_airbus": 0,
        "skipped_no_c5": 0,
        "skipped_no_date": 0,
        "source": "v2_db",
    }
    for row in cur:
        stats["total_csv_rows"] += 1
        record = json.loads(row["source_data"])
        csv_like = {k: str(v) if v is not None else "" for k, v in record.items()}
        if not _row_passes_boeing_airbus_filter(csv_like):
            stats["skipped_not_boeing_airbus"] += 1
            continue
        if not _has_valid_c5(csv_like):
            stats["skipped_no_c5"] += 1
            continue
        if not _has_valid_date(csv_like):
            stats["skipped_no_date"] += 1
            continue
        written.append(record)
        stats["boeing_airbus_written"] += 1
    conn.close()
    return written, stats


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# FAA AIDS Boeing/Airbus export — {today} — {len(rows)} rows\n")
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--zip-cache", type=Path, default=DEFAULT_CACHE_ZIP)
    parser.add_argument("--zip-url", help="Direct URL to FAA AIDS ZIP (skip discovery)")
    parser.add_argument(
        "--from-v2-db",
        type=Path,
        metavar="PATH",
        help="Bootstrap JSONL from v2 SQLite FAA_AIDS source_data (when FAA ZIP unavailable)",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Use existing --zip-cache file without downloading",
    )
    args = parser.parse_args()

    if args.from_v2_db:
        rows, stats = export_from_v2_db(args.from_v2_db)
    else:
        if args.skip_download and args.zip_cache.is_file():
            zip_path = args.zip_cache
        else:
            zip_path = download_faa_aids_zip(
                cache_path=args.zip_cache, zip_url=args.zip_url
            )
        csv_rows, encoding = _read_csv_from_zip(zip_path)
        stats = {"csv_encoding": encoding}
        rows, row_stats = export_rows_from_csv(csv_rows)
        stats.update(row_stats)

    if not rows:
        print(json.dumps({"error": "no Boeing/Airbus rows exported", **stats}, indent=2))
        return 1

    write_jsonl(args.out, rows)
    summary = {
        "output_path": str(args.out),
        "rows_written": len(rows),
        **stats,
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
