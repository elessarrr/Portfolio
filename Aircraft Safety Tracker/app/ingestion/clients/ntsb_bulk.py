"""NTSB bulk incremental fetch via monthly avdata Microsoft Access updates.

PRD 0012, Task 3.0. Approach B (chosen 2026-06-21): the only stable, official
NTSB data product is the avdata download set (https://data.ntsb.gov/avdata).
The CAROL JSON backend is undocumented/brittle (see Task 3.1 research; the
`Main` query rejects every column name with no discoverable config), so we use
the published files instead.

Data shape (verified against a live up01JUN.zip on 2026-06-21):
  - Files: full `avall.zip` (~95 MB) + rolling weekly updates `up<DD><MON>.zip`
    for DD in {01,08,15,22} (~0.5 MB each). We pull the most recently dated
    weekly update and diff against the DB, so the exact file picked is safe.
  - Format: Microsoft Access `.mdb`; parsed with `mdbtools` (`mdb-export`).
  - `events` table: ntsb_no, ev_id, ev_date, ev_city, ev_state, inj_tot_f, ...
  - `aircraft` table: ev_id, Aircraft_Key, acft_make, acft_model, oper_name, ...
  - `acft_make`/`acft_model` are UPPERCASE, e.g. "BOEING"/"737" — and
    `"{make} {model}"` ("BOEING 737") is exactly the key format used by
    data/config/ntsb_make_model_to_aircraft.jsonl, so existing NTSBImporter
    mapping applies unchanged. Unrecognised strings → importer.skipped_unmapped.

Pure transforms (`parse_latest_update_url`, `build_records`, `diff_new_records`)
are unit-tested offline; the mdbtools/HTTP I/O is isolated in `fetch_new_ntsb_records`.

Runs on GitHub Actions (mdbtools installs via apt) and writes to Railway Postgres.
"""

from __future__ import annotations

import csv
import io
import logging
import re
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set
from urllib.parse import urljoin

from app.ingestion.importers.base import is_boeing_or_airbus_make_model

logger = logging.getLogger(__name__)

AVDATA_BASE = "https://data.ntsb.gov"
AVDATA_LISTING_URL = "https://data.ntsb.gov/avdata"

# Matches one listing row: filename, modified date, and download href.
_ROW_RE = re.compile(
    r'id="fileName">\s*(?P<name>up\d{2}[A-Z]{3}\.zip)\s*</td>.*?'
    r'id="fileDate">\s*(?P<date>[\d/]+\s+[\d:]+\s*[AP]M)\s*</td>.*?'
    r'href="(?P<href>[^"]+)"',
    re.S,
)


def parse_latest_update_url(listing_html: str) -> str:
    """Return the download URL of the most recently dated weekly `up*.zip`.

    Ignores the full `avall.zip` snapshot. Raises if no weekly update is found.
    """
    best_date: Optional[datetime] = None
    best_href: Optional[str] = None
    for m in _ROW_RE.finditer(listing_html):
        try:
            when = datetime.strptime(m.group("date").strip(), "%m/%d/%Y %I:%M:%S %p")
        except ValueError:
            continue
        if best_date is None or when > best_date:
            best_date = when
            best_href = m.group("href")
    if not best_href:
        raise ValueError("No weekly NTSB update file found in avdata listing")
    return urljoin(AVDATA_BASE, best_href)


def _normalize_event_date(raw: Optional[str]) -> str:
    """Normalize NTSB ev_date to ISO `YYYY-MM-DD`.

    mdb-export emits dates like `MM/DD/YY 00:00:00` regardless of `-D`, so we
    parse defensively. Returns the original (stripped) string if unrecognised,
    letting the importer's own date parser reject it.
    """
    text = (raw or "").strip()
    if not text:
        return ""
    date_part = text.split(" ", 1)[0]
    for fmt in ("%m/%d/%y", "%m/%d/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_part, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_part


def build_records(
    events: Iterable[Dict[str, str]], aircraft: Iterable[Dict[str, str]]
) -> List[Dict[str, object]]:
    """Join NTSB `events` + `aircraft` exports into NTSBImporter-shaped records.

    One record per Boeing/Airbus aircraft row. Non-Boeing/Airbus rows and rows
    whose event is missing are skipped.
    """
    events_by_id = {e.get("ev_id"): e for e in events if e.get("ev_id")}
    records: List[Dict[str, object]] = []
    for acft in aircraft:
        ev = events_by_id.get(acft.get("ev_id"))
        if ev is None:
            continue
        make = (acft.get("acft_make") or "").strip()
        model = (acft.get("acft_model") or "").strip()
        make_model = f"{make} {model}".strip()
        if not is_boeing_or_airbus_make_model(make_model):
            continue

        ntsb_no = (ev.get("ntsb_no") or "").strip()
        if not ntsb_no:
            continue

        city = (ev.get("ev_city") or "").strip()
        state = (ev.get("ev_state") or "").strip()
        location = ", ".join(p for p in (city, state) if p) or None

        records.append(
            {
                "ntsb_id": ntsb_no,
                "event_date": _normalize_event_date(ev.get("ev_date")),
                "make_model": make_model,
                "fatalities": ev.get("inj_tot_f"),
                "location": location,
                "operator": (acft.get("oper_name") or "").strip() or None,
                # ev_id lands in source_data and enables the NTSB brief URL fallback.
                "ev_id": ev.get("ev_id"),
                "far_part": (acft.get("far_part") or "").strip() or None,
            }
        )
    return records


def diff_new_records(
    records: Iterable[Dict[str, object]], existing_ids: Set[str]
) -> List[Dict[str, object]]:
    """Keep only records whose `ntsb_id` is not already stored."""
    return [r for r in records if str(r.get("ntsb_id")) not in existing_ids]


def existing_ntsb_source_ids() -> Set[str]:
    """All NTSB `source_record_id` values currently in the DB."""
    from app.models import IncidentSource

    rows = (
        IncidentSource.query.with_entities(IncidentSource.source_record_id)
        .filter_by(source_name="NTSB")
        .all()
    )
    return {r[0] for r in rows if r[0]}


# --- I/O (isolated; mocked in tests) ---------------------------------------


def _http_get_bytes(url: str) -> bytes:  # pragma: no cover - thin network wrapper
    import httpx

    headers = {"User-Agent": "Mozilla/5.0 (AircraftSafetyTracker weekly ingest)"}
    resp = httpx.get(url, headers=headers, follow_redirects=True, timeout=120)
    resp.raise_for_status()
    return resp.content


def _http_get_text(url: str) -> str:  # pragma: no cover - thin network wrapper
    return _http_get_bytes(url).decode("utf-8", errors="ignore")


def _extract_mdb(zip_bytes: bytes, dest_dir: Path) -> Path:  # pragma: no cover - I/O
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        mdb_name = next((n for n in zf.namelist() if n.lower().endswith(".mdb")), None)
        if not mdb_name:
            raise ValueError("No .mdb file inside NTSB update zip")
        zf.extract(mdb_name, path=dest_dir)
        return dest_dir / mdb_name


def _mdb_export(mdb_path: Path, table: str) -> List[Dict[str, str]]:  # pragma: no cover - subprocess
    """Run `mdb-export` (mdbtools) and return rows as dicts. Dates as ISO."""
    out = subprocess.run(
        ["mdb-export", "-D", "%Y-%m-%d", str(mdb_path), table],
        check=True,
        capture_output=True,
        text=True,
    )
    return list(csv.DictReader(io.StringIO(out.stdout)))


def fetch_new_ntsb_records(
    existing_ids: Optional[Set[str]] = None,
) -> List[Dict[str, object]]:  # pragma: no cover - orchestration over mocked parts
    """Download the latest NTSB weekly update, parse it, and return new
    Boeing/Airbus records not already in the DB."""
    if existing_ids is None:
        existing_ids = existing_ntsb_source_ids()

    listing = _http_get_text(AVDATA_LISTING_URL)
    update_url = parse_latest_update_url(listing)
    logger.info("NTSB weekly update: %s", update_url)

    zip_bytes = _http_get_bytes(update_url)
    with tempfile.TemporaryDirectory() as tmp:
        mdb_path = _extract_mdb(zip_bytes, Path(tmp))
        events = _mdb_export(mdb_path, "events")
        aircraft = _mdb_export(mdb_path, "aircraft")

    records = build_records(events, aircraft)
    new_records = diff_new_records(records, existing_ids)
    logger.info(
        "NTSB bulk: %d Boeing/Airbus rows in update, %d new after diff",
        len(records),
        len(new_records),
    )
    return new_records
