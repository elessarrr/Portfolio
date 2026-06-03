#!/usr/bin/env python3
"""Sample N rows from merged audit JSONL with brief-report URLs (page 18 experiment).

Usage:
    PYTHONPATH=. python scripts/export_faa_aids_report_url_experiment.py
    PYTHONPATH=. python scripts/export_faa_aids_report_url_experiment.py --validate --concurrency 24
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_INPUT = ROOT / "data/logs/faa_aids_url_audit_merged_2026-06-01.jsonl"
DEFAULT_OUT = ROOT / "data/logs/faa_aids_report_url_experiment_200.jsonl"
DEFAULT_SAMPLE = 200
DEFAULT_SEED = 42


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--sample", type=int, default=DEFAULT_SAMPLE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--validate",
        action="store_true",
        help="HTTP-check brief report URLs (not search URLs)",
    )
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()

    from app.ingestion.url_builders.faa_aids import (
        build_faa_aids_brief_report_url,
        build_faa_aids_search_url,
    )

    all_rows = _load_jsonl(args.input)
    if len(all_rows) < args.sample:
        raise SystemExit(f"Input has only {len(all_rows)} rows; need {args.sample}")

    rng = random.Random(args.seed)
    picked = rng.sample(all_rows, args.sample)

    experiment: List[Dict[str, Any]] = []
    for row in picked:
        sid = row.get("source_record_id")
        experiment.append(
            {
                "source_record_id": sid,
                "faa_aids_search_url": build_faa_aids_search_url(sid),
                "faa_aids_report_url": build_faa_aids_brief_report_url(sid),
                "imported_incident_id": row.get("imported_incident_id"),
                "imported_aircraft_id": row.get("imported_aircraft_id"),
                "make_model": row.get("make_model"),
                "date": row.get("date"),
                "operator": row.get("operator"),
                "experiment": "page18_AP_BRIEF_RPT_VAR",
            }
        )

    if args.validate:
        from app.ingestion.url_builders.faa_aids_viability import (
            BUCKET_BRIEF_REPORT,
            HttpxUrlFetcher,
            validate_faa_aids_url_extended,
        )

        fetcher = HttpxUrlFetcher(timeout=args.timeout)

        def check(entry: Dict[str, Any]) -> Dict[str, Any]:
            url = entry["faa_aids_report_url"]
            try:
                result = validate_faa_aids_url_extended(
                    url,
                    url_mode="brief",
                    fetcher=fetcher,
                    timeout=args.timeout,
                    retry_once=True,
                )
            except Exception as exc:
                entry = dict(entry)
                entry.update(
                    {
                        "report_http_status": None,
                        "report_link_viable": False,
                        "report_link_reason": "fetch_error",
                        "bucket": "not_working",
                        "report_page_heuristic": "error",
                        "checked_at": datetime.utcnow().isoformat() + "Z",
                        "_error": str(exc),
                    }
                )
                return entry

            entry = dict(entry)
            entry.update(
                {
                    "report_http_status": result.http_status,
                    "report_link_viable": result.viable,
                    "report_link_reason": result.reason,
                    "bucket": result.bucket,
                    "product_viable": result.product_viable,
                    "report_page_heuristic": (
                        "brief_report"
                        if result.bucket == BUCKET_BRIEF_REPORT
                        else "search_or_other"
                    ),
                    "checked_at": datetime.utcnow().isoformat() + "Z",
                }
            )
            return entry

        print(f"Validating {len(experiment)} brief report URLs...")
        start = time.time()
        validated: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = [pool.submit(check, e) for e in experiment]
            done = 0
            for fut in as_completed(futures):
                validated.append(fut.result())
                done += 1
                if done % 20 == 0 or done == len(experiment):
                    print(f"  {done}/{len(experiment)}")
        experiment = validated
        elapsed = time.time() - start

        viable_n = sum(1 for e in experiment if e.get("product_viable"))
        brief_n = sum(1 for e in experiment if e.get("bucket") == BUCKET_BRIEF_REPORT)
        print(
            f"  Done in {elapsed:.1f}s — product_viable={viable_n}/{len(experiment)}"
            f" bucket={BUCKET_BRIEF_REPORT}={brief_n}/{len(experiment)}"
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    with args.out.open("w", encoding="utf-8") as f:
        f.write(
            f"# FAA AIDS brief report URL experiment — {today} — n={len(experiment)}"
            f" — seed={args.seed}\n"
        )
        f.write(
            "# Pattern: f?p=100:18:::NO::AP_BRIEF_RPT_VAR:{source_record_id}\n"
        )
        for entry in experiment:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
