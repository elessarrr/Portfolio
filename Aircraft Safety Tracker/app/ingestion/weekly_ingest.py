"""Weekly ingestion orchestrator (PRD 0012, Task 4.0).

Runs the two perpetual sources and records run state:
  - NTSB: monthly avdata .mdb adapter (`app.ingestion.clients.ntsb_bulk`) → NTSBImporter
  - ASN:  re-scrape Boeing/Airbus + import (existing `scripts/` entrypoints)

Each source is retried up to 3 times with a delay (PRD: "retry up to 3 times,
then log and skip until next scheduled run"). If any source exhausts its
retries the run is marked `partial`, otherwise `ok`; `last_run_at` always
advances. Designed to run on GitHub Actions writing to Railway Postgres.

Source callables are injectable for testing; defaults do the real work.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from app import db
from app.models import IngestionState

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
NTSB_MAPPING_PATH = ROOT / "data/config/ntsb_make_model_to_aircraft.jsonl"


def _run_with_retry(
    fn: Callable[[], object],
    name: str,
    *,
    max_retries: int = 3,
    delay: int = 60,
    sleep: Callable[[float], None] = time.sleep,
) -> Tuple[Optional[object], bool]:
    """Run `fn` up to `max_retries` times. Returns (result, succeeded)."""
    for attempt in range(1, max_retries + 1):
        try:
            result = fn()
            logger.info("ingest source %s succeeded on attempt %d/%d", name, attempt, max_retries)
            return result, True
        except Exception:
            logger.exception("ingest source %s failed on attempt %d/%d", name, attempt, max_retries)
            if attempt < max_retries:
                sleep(delay)
    logger.error("ingest source %s exhausted %d retries — skipping until next run", name, max_retries)
    return None, False


def ingest_ntsb() -> Dict[str, object]:
    """Default NTSB source: fetch new monthly records and import them."""
    from app.ingestion.clients.ntsb_bulk import (
        existing_ntsb_source_ids,
        fetch_new_ntsb_records,
    )
    from app.ingestion.importers.ntsb_importer import NTSBImporter

    existing = existing_ntsb_source_ids()
    records = fetch_new_ntsb_records(existing)
    importer = NTSBImporter(records=records, mapping=str(NTSB_MAPPING_PATH))
    written = importer.run()
    summary = {
        "fetched": len(records),
        "written": written,
        "skipped_unmapped": len(importer.skipped_unmapped),
        "skipped_unresolved": len(importer.skipped_unresolved),
    }
    # Unmapped make/model strings are silently dropped by the importer — surface
    # them prominently so the mapping file can be extended (PRD FR-1.9).
    if importer.skipped_unmapped:
        logger.warning(
            "NTSB skipped %d unmapped make/model string(s): %s",
            len(importer.skipped_unmapped),
            sorted(set(importer.skipped_unmapped))[:20],
        )
    logger.info("NTSB ingest: %s", summary)
    return summary


def ingest_asn() -> Dict[str, object]:
    """Default ASN source: re-scrape Boeing/Airbus and import into the DB."""
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import import_data
    import scrape_airbus
    import scrape_boeing

    scrape_boeing.main()
    scrape_airbus.main()
    import_data.main()
    logger.info("ASN ingest: scrape + import complete")
    return {"asn": "complete"}


def _upsert_ingestion_state(status: str, now: datetime) -> IngestionState:
    state = IngestionState.query.first()
    if state is None:
        state = IngestionState()
        db.session.add(state)
    state.last_run_at = now
    state.last_run_status = status
    db.session.commit()
    return state


def run_ingest(
    *,
    ntsb_fn: Callable[[], object] = ingest_ntsb,
    asn_fn: Callable[[], object] = ingest_asn,
    max_retries: int = 3,
    delay: int = 60,
    sleep: Callable[[float], None] = time.sleep,
    now: Optional[datetime] = None,
) -> Dict[str, object]:
    """Run all sources with retry, then upsert IngestionState.

    Returns a summary dict including overall `status` ('ok' | 'partial').
    """
    now = now or datetime.utcnow()
    results: Dict[str, object] = {}
    all_ok = True

    for name, fn in (("ntsb", ntsb_fn), ("asn", asn_fn)):
        result, ok = _run_with_retry(
            fn, name, max_retries=max_retries, delay=delay, sleep=sleep
        )
        results[name] = {"ok": ok, "result": result}
        all_ok = all_ok and ok

    status = "ok" if all_ok else "partial"
    _upsert_ingestion_state(status, now)
    results["status"] = status
    logger.info("weekly ingest finished: status=%s", status)
    return results
