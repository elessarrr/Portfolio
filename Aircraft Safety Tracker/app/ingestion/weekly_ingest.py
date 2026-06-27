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


def existing_asn_urls() -> frozenset:
    """Return all non-null Incident.asn_url values already in the DB as a frozenset.

    Called once at the start of ingest_asn so the scrapers can skip detail fetches
    for incidents we already have — making weekly runs fast.
    """
    from app.models import Incident

    rows = db.session.query(Incident.asn_url).filter(Incident.asn_url.isnot(None)).all()
    return frozenset(r[0] for r in rows)


def _default_asn_callables() -> Tuple[Callable[..., int], Callable[..., int], Callable[[], object]]:
    """Lazily import the real scrape/import entrypoints from `scripts/`."""
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    import import_data
    import scrape_airbus
    import scrape_boeing

    return scrape_boeing.main, scrape_airbus.main, import_data.main


def ingest_asn(
    *,
    scrape_boeing_fn: Optional[Callable[..., int]] = None,
    scrape_airbus_fn: Optional[Callable[..., int]] = None,
    import_fn: Optional[Callable[[], object]] = None,
    known_urls_fn: Optional[Callable[[], frozenset]] = None,
) -> Dict[str, object]:
    """ASN source: incrementally scrape Boeing/Airbus and import new incidents.

    Loads all known Incident.asn_url values from the DB first, then passes that
    set to the scrapers so they skip the expensive detail fetch for already-stored
    incidents. On a typical weekly run this means only a handful of new incidents
    are actually fetched instead of the full corpus.

    NOTE: aviation-safety.net returns HTTP 403 to datacenter/cloud IPs — run this
    locally from a residential IP. A 0-incident result raises so a blocked run
    never silently reports success.
    """
    if scrape_boeing_fn is None or scrape_airbus_fn is None or import_fn is None:
        default_boeing, default_airbus, default_import = _default_asn_callables()
        scrape_boeing_fn = scrape_boeing_fn or default_boeing
        scrape_airbus_fn = scrape_airbus_fn or default_import
        import_fn = import_fn or default_import
        # Real path: reset to real scrapers (don't use default_import as a scraper)
        scrape_boeing_fn = default_boeing
        scrape_airbus_fn = default_airbus
        import_fn = default_import

    known_urls = (known_urls_fn or existing_asn_urls)()
    logger.info("ASN ingest: %d known URLs loaded — will skip these", len(known_urls))

    boeing = scrape_boeing_fn(known_urls=known_urls) or 0
    airbus = scrape_airbus_fn(known_urls=known_urls) or 0
    if boeing + airbus == 0:
        raise RuntimeError(
            "ASN scrape produced 0 incidents — source likely blocked (HTTP 403). "
            "Run the ASN refresh from a residential IP, not a cloud runner."
        )

    import_fn()
    logger.info("ASN ingest: scrape + import complete (boeing=%d, airbus=%d)", boeing, airbus)
    return {"asn": "complete", "boeing": boeing, "airbus": airbus}


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
    include_ntsb: bool = True,
    include_asn: bool = False,
    ntsb_fn: Callable[[], object] = ingest_ntsb,
    asn_fn: Callable[[], object] = ingest_asn,
    max_retries: int = 3,
    delay: int = 60,
    sleep: Callable[[float], None] = time.sleep,
    now: Optional[datetime] = None,
) -> Dict[str, object]:
    """Run the selected sources with retry, then upsert IngestionState.

    Defaults to NTSB-only: aviation-safety.net (ASN) 403s cloud IPs, so the
    GitHub Actions cron runs NTSB only. ASN is opt-in (`include_asn=True`) for
    local refreshes from a residential IP.

    Returns a summary dict including overall `status` ('ok' | 'partial').
    """
    now = now or datetime.utcnow()
    results: Dict[str, object] = {}
    all_ok = True

    sources: list[Tuple[str, Callable[[], object]]] = []
    if include_ntsb:
        sources.append(("ntsb", ntsb_fn))
    if include_asn:
        sources.append(("asn", asn_fn))

    for name, fn in sources:
        result, ok = _run_with_retry(
            fn, name, max_retries=max_retries, delay=delay, sleep=sleep
        )
        results[name] = {"ok": ok, "result": result}
        all_ok = all_ok and ok

    status = "ok" if all_ok else "partial"
    _upsert_ingestion_state(status, now)
    results["status"] = status
    logger.info("weekly ingest finished: status=%s (sources=%s)", status, [s[0] for s in sources])
    return results
