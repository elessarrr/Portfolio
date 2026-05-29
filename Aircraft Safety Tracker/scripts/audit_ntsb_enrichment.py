"""Audit NTSB enrichment vs ASN baseline (no writes).

Reads a local NTSB records JSON file, parses records using the v3 NTSB importer contract,
evaluates ASN dedupe coverage, and optionally validates resolved NTSB URLs.

Outputs a reviewable report (counts + sample rows per bucket) for product approval
before write-path insertion.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.ingestion.dedupe.ntsb_asn import score_ntsb_vs_asn
from app.ingestion.importers.base import find_boeing_airbus_aircraft_id, normalize_make_model
from app.ingestion.importers.ntsb_importer import NTSBImporter
from app.ingestion.url_builders.ntsb import resolve_ntsb_source_url
from app.ingestion.url_builders.ntsb_viability import validate_ntsb_url
from app.models import Incident


def _load_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON list of NTSB records")
    return data


def _candidate_asn_incidents(aircraft_id: int, ntsb_date, window_days: int):
    lo = ntsb_date.fromordinal(ntsb_date.toordinal() - window_days)
    hi = ntsb_date.fromordinal(ntsb_date.toordinal() + window_days)
    return (
        Incident.query.filter(
            Incident.aircraft_id == aircraft_id,
            Incident.asn_url.isnot(None),
            Incident.date >= lo,
            Incident.date <= hi,
        )
        .order_by(Incident.date.asc())
        .all()
    )


def _best_dedupe_match(
    *,
    aircraft_id: int,
    ntsb_date,
    ntsb_operator,
    ntsb_location,
    ntsb_fatalities,
    window_days: int,
):
    candidates = _candidate_asn_incidents(aircraft_id, ntsb_date, window_days)
    best_decision = None
    best_incident: Optional[Incident] = None

    for inc in candidates:
        decision = score_ntsb_vs_asn(
            ntsb_date=ntsb_date,
            asn_date=inc.date,
            ntsb_operator=ntsb_operator,
            asn_operator=inc.operator,
            ntsb_location=ntsb_location,
            asn_location=inc.location,
            ntsb_fatalities=ntsb_fatalities,
            asn_fatalities=inc.fatalities,
        )
        if not best_decision:
            best_decision, best_incident = decision, inc
            continue
        if decision.signals.strong_count() > best_decision.signals.strong_count():
            best_decision, best_incident = decision, inc
            continue
        if (
            decision.signals.strong_count() == best_decision.signals.strong_count()
            and decision.days_apart < best_decision.days_apart
        ):
            best_decision, best_incident = decision, inc

    return best_decision, best_incident


def _row_summary(
    *,
    parsed: Dict[str, Any],
    make_model: str,
    aircraft_id: Optional[int],
    ntsb_url: Optional[str],
    best_decision,
    best_incident: Optional[Incident],
    link_viable: Optional[bool] = None,
    link_reason: Optional[str] = None,
) -> Dict[str, Any]:
    row = {
        "date": str(parsed["date"]),
        "make_model": make_model,
        "operator": parsed.get("operator"),
        "location": parsed.get("location"),
        "fatalities": parsed.get("fatalities"),
        "source_record_id": parsed.get("source_record_id"),
        "ntsb_url": ntsb_url,
        "aircraft_id": aircraft_id,
        "unknown_aircraft": aircraft_id is None,
        "closest_asn_match": (
            {
                "incident_id": best_incident.id,
                "date": str(best_incident.date),
                "operator": best_incident.operator,
                "location": best_incident.location,
                "fatalities": best_incident.fatalities,
                "asn_url": best_incident.asn_url,
                "decision": asdict(best_decision),
            }
            if best_incident and best_decision
            else None
        ),
    }
    if link_viable is not None:
        row["link_viable"] = link_viable
        row["link_reason"] = link_reason
    return row


def _append_sample(bucket: List[Dict[str, Any]], row: Dict[str, Any], sample_size: int) -> None:
    if len(bucket) < sample_size:
        bucket.append(row)


class LinkCheckCache:
    def __init__(self, per_domain_delay: float = 0.2):
        self._cache: Dict[str, Tuple[bool, Optional[int], Optional[str]]] = {}
        self._last_seen: Dict[str, float] = {}
        self._per_domain_delay = per_domain_delay

    def check(self, url: Optional[str]) -> Tuple[bool, Optional[int], Optional[str]]:
        if not url:
            return False, None, "no_url"
        if url in self._cache:
            return self._cache[url]

        domain = urlparse(url).netloc.lower()
        if domain and self._per_domain_delay > 0:
            now = time.monotonic()
            previous = self._last_seen.get(domain)
            if previous is not None:
                elapsed = now - previous
                if elapsed < self._per_domain_delay:
                    time.sleep(self._per_domain_delay - elapsed)
            self._last_seen[domain] = time.monotonic()

        result = validate_ntsb_url(url)
        self._cache[url] = result
        return result


def run_audit(
    records: List[Dict[str, Any]],
    *,
    window_days: int = 7,
    sample_size: int = 10,
    include_unknown_aircraft: bool = False,
    check_links: bool = False,
    per_domain_delay: float = 0.2,
    max_link_checks: Optional[int] = None,
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "total_records": len(records),
        "parsed": 0,
        "skipped_not_boeing_airbus": 0,
        "skipped_missing_aircraft": 0,
        "unknown_aircraft_included": 0,
        "skipped_deduped_asn_covered": 0,
        "viable_unique": 0,
        "viable_with_working_link": 0,
        "viable_with_broken_link": 0,
        "skipped_unreleased_docket": 0,
        "link_checks_skipped": 0,
        "dedupe_limited_unknown_aircraft": 0,
        "samples": {
            "skipped_deduped_asn_covered": [],
            "unknown_aircraft_included": [],
            "viable_with_working_link": [],
            "viable_with_broken_link": [],
            "skipped_unreleased_docket": [],
        },
        "notes": {
            "unknown_aircraft_dedupe": (
                "When aircraft_id is not found in v3 DB, ASN dedupe is not run; "
                "records are included in viable_unique with unknown_aircraft=true (FR-6.2)."
            ),
        },
    }

    link_cache = LinkCheckCache(per_domain_delay=per_domain_delay) if check_links else None
    link_checks_done = 0

    for raw in records:
        parsed = NTSBImporter.parse(raw)
        if not parsed:
            report["skipped_not_boeing_airbus"] += 1
            continue
        report["parsed"] += 1

        make_model = normalize_make_model(parsed.get("make_model") or "")
        aircraft_id = find_boeing_airbus_aircraft_id(make_model)

        if not aircraft_id and not include_unknown_aircraft:
            report["skipped_missing_aircraft"] += 1
            continue

        ntsb_date = parsed["date"]
        ntsb_operator = parsed.get("operator")
        ntsb_location = parsed.get("location")
        ntsb_fatalities = parsed.get("fatalities")
        source_data = parsed.get("source_data") or {}
        ntsb_url = parsed.get("source_url") or resolve_ntsb_source_url(
            parsed.get("source_record_id"), source_data
        )

        best_decision = None
        best_incident = None

        if aircraft_id:
            best_decision, best_incident = _best_dedupe_match(
                aircraft_id=aircraft_id,
                ntsb_date=ntsb_date,
                ntsb_operator=ntsb_operator,
                ntsb_location=ntsb_location,
                ntsb_fatalities=ntsb_fatalities,
                window_days=window_days,
            )
        else:
            report["unknown_aircraft_included"] += 1
            report["dedupe_limited_unknown_aircraft"] += 1
            _append_sample(
                report["samples"]["unknown_aircraft_included"],
                _row_summary(
                    parsed=parsed,
                    make_model=make_model,
                    aircraft_id=None,
                    ntsb_url=ntsb_url,
                    best_decision=None,
                    best_incident=None,
                ),
                sample_size,
            )

        if best_decision and best_decision.asn_covered:
            report["skipped_deduped_asn_covered"] += 1
            _append_sample(
                report["samples"]["skipped_deduped_asn_covered"],
                _row_summary(
                    parsed=parsed,
                    make_model=make_model,
                    aircraft_id=aircraft_id,
                    ntsb_url=ntsb_url,
                    best_decision=best_decision,
                    best_incident=best_incident,
                ),
                sample_size,
            )
            continue

        report["viable_unique"] += 1

        if not check_links or not link_cache:
            continue

        if max_link_checks is not None and link_checks_done >= max_link_checks:
            report["link_checks_skipped"] += 1
            continue

        viable, _status, reason = link_cache.check(ntsb_url)
        link_checks_done += 1

        row = _row_summary(
            parsed=parsed,
            make_model=make_model,
            aircraft_id=aircraft_id,
            ntsb_url=ntsb_url,
            best_decision=best_decision,
            best_incident=best_incident,
            link_viable=viable,
            link_reason=reason,
        )

        if viable:
            report["viable_with_working_link"] += 1
            _append_sample(report["samples"]["viable_with_working_link"], row, sample_size)
        else:
            report["viable_with_broken_link"] += 1
            _append_sample(report["samples"]["viable_with_broken_link"], row, sample_size)
            if reason == "docket_not_released":
                report["skipped_unreleased_docket"] += 1
                _append_sample(report["samples"]["skipped_unreleased_docket"], row, sample_size)

    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=os.environ.get("NTSB_INPUT") or "data/raw/ntsb_records.json",
        help="Path to NTSB records JSON (list of dicts).",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=7,
        help="ASN candidate search window around NTSB date (days). Default: 7",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=10,
        help="Sample rows per report bucket. Default: 10",
    )
    parser.add_argument(
        "--out",
        default="data/logs/ntsb_enrichment_audit.json",
        help="Write JSON report to this path.",
    )
    parser.add_argument(
        "--include-unknown-aircraft",
        action="store_true",
        help="Include Boeing/Airbus rows even when aircraft_id not in v3 DB (FR-6.1).",
    )
    parser.add_argument(
        "--check-links",
        action="store_true",
        help="HTTP-check resolved NTSB URLs for viability (FR-5.2).",
    )
    parser.add_argument(
        "--per-domain-delay",
        type=float,
        default=0.2,
        help="Seconds between requests to the same domain. Default: 0.2",
    )
    parser.add_argument(
        "--max-link-checks",
        type=int,
        default=None,
        help="Optional cap on link checks (for dev smoke runs).",
    )
    args = parser.parse_args()

    records = _load_json(args.input)
    app = create_app()

    with app.app_context():
        report = run_audit(
            records,
            window_days=args.window_days,
            sample_size=args.sample,
            include_unknown_aircraft=args.include_unknown_aircraft,
            check_links=args.check_links,
            per_domain_delay=args.per_domain_delay,
            max_link_checks=args.max_link_checks,
        )

    report["input_path"] = args.input
    report["options"] = {
        "window_days": args.window_days,
        "include_unknown_aircraft": args.include_unknown_aircraft,
        "check_links": args.check_links,
        "per_domain_delay": args.per_domain_delay,
        "max_link_checks": args.max_link_checks,
    }

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
