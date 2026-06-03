#!/usr/bin/env python3
"""Audit FAA AIDS source URLs for viability; write classified export + DB write-back."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DEFAULT_INPUT = ROOT / "data/logs/faa_aids_enrichment_final_import_01Jun2026.jsonl"
DEFAULT_OUT_TEMPLATE = ROOT / "data/logs/faa_aids_url_audit_{date}.jsonl"
DEFAULT_SUMMARY = ROOT / "data/logs/faa_aids_url_audit_summary.json"
DEFAULT_CONCURRENCY = 16
DEFAULT_TIMEOUT = 15
DEFAULT_URL_MODE = "brief"
BATCH_SIZE = 500
DEFAULT_JITTER_MS = (50, 200)

BUCKET_NOT_WORKING = "not_working"
BUCKET_BRIEF = "working_brief_report"
BUCKET_SEARCH = "working_search_prefill"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def _load_retry_rows(audit_path: Path) -> List[Dict[str, Any]]:
    failed = [r for r in _load_jsonl(audit_path) if r.get("bucket") == BUCKET_NOT_WORKING]
    if not failed:
        raise SystemExit(f"No {BUCKET_NOT_WORKING} rows in {audit_path}")
    return failed


def _resolve_audit_url(row: Dict[str, Any], url_mode: str) -> str:
    from app.ingestion.url_builders.faa_aids import (
        build_faa_aids_brief_report_url,
        build_faa_aids_search_url,
    )

    sid = row.get("source_record_id")
    if url_mode == "brief":
        return build_faa_aids_brief_report_url(sid) or ""
    stored = row.get("faa_aids_url") or row.get("source_url") or ""
    if stored:
        return stored
    return build_faa_aids_search_url(sid) or ""


def _make_check_fn(
    timeout: int,
    use_jitter: bool,
    jitter_ms: tuple[int, int],
    retry_once: bool,
    url_mode: str,
    user_agent_mode: str,
):
    from app.ingestion.url_builders.faa_aids_viability import (
        BROWSER_USER_AGENT,
        DEFAULT_USER_AGENT,
        HttpxUrlFetcher,
        validate_faa_aids_url_extended,
    )

    ua = BROWSER_USER_AGENT if user_agent_mode == "browser" else DEFAULT_USER_AGENT
    fetcher = HttpxUrlFetcher(timeout=timeout, user_agent=ua)

    def check(row: Dict[str, Any]) -> Dict[str, Any]:
        if use_jitter:
            time.sleep(random.uniform(jitter_ms[0], jitter_ms[1]) / 1000)
        url = _resolve_audit_url(row, url_mode)
        result = validate_faa_aids_url_extended(
            url,
            url_mode=url_mode,
            fetcher=fetcher,
            timeout=timeout,
            retry_once=retry_once,
        )
        return {
            "source_record_id": row.get("source_record_id"),
            "faa_aids_url": url,
            "url_mode": url_mode,
            "imported_incident_id": row.get("imported_incident_id"),
            "imported_aircraft_id": row.get("imported_aircraft_id"),
            "make_model": row.get("make_model"),
            "date": row.get("date"),
            "operator": row.get("operator"),
            "http_status": result.http_status,
            "link_viable": result.viable,
            "product_viable": result.product_viable,
            "link_reason": result.reason,
            "bucket": result.bucket,
            "checked_at": datetime.utcnow().isoformat() + "Z",
        }

    return check


def _apply_db_changes(
    results: List[Dict[str, Any]], app_ctx: Any, url_mode: str
) -> Dict[str, int]:
    from app.ingestion.url_builders.faa_aids_viability import db_should_remain_active
    from app.models import IncidentSource

    counters = {"true_to_false": 0, "false_to_true": 0, "unchanged": 0}
    with app_ctx.app_context():
        from app import db

        batch = []
        for result in results:
            src_id = result["source_record_id"]
            if not src_id:
                continue
            row = IncidentSource.query.filter_by(
                source_name="FAA_AIDS", source_record_id=src_id
            ).first()
            if row is None:
                continue
            new_active = db_should_remain_active(result["bucket"], url_mode)
            if row.is_active == new_active:
                counters["unchanged"] += 1
            elif row.is_active and not new_active:
                row.is_active = False
                row.last_updated = datetime.utcnow()
                counters["true_to_false"] += 1
                batch.append(row)
            else:
                row.is_active = True
                row.last_updated = datetime.utcnow()
                counters["false_to_true"] += 1
                batch.append(row)

            if len(batch) >= BATCH_SIZE:
                db.session.commit()
                batch.clear()

        if batch:
            db.session.commit()

    return counters


def _bucket_counts(results: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {BUCKET_BRIEF: 0, BUCKET_SEARCH: 0, BUCKET_NOT_WORKING: 0}
    for row in results:
        bucket = row.get("bucket", BUCKET_NOT_WORKING)
        if bucket in counts:
            counts[bucket] += 1
        else:
            counts[bucket] = counts.get(bucket, 0) + 1
    return counts


def _merge_audit_rows(
    base_path: Path,
    updates: List[Dict[str, Any]],
    merged_path: Path,
) -> None:
    by_id = {r["source_record_id"]: r for r in updates}
    lines_out: List[str] = []
    counts = {BUCKET_BRIEF: 0, BUCKET_SEARCH: 0, BUCKET_NOT_WORKING: 0}
    with base_path.open(encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            sid = row.get("source_record_id")
            if sid in by_id:
                row = by_id[sid]
            bucket = row.get("bucket", BUCKET_NOT_WORKING)
            if bucket in counts:
                counts[bucket] += 1
            lines_out.append(json.dumps(row, ensure_ascii=False))

    merged_path.parent.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    with merged_path.open("w", encoding="utf-8") as f:
        f.write(
            f"# FAA AIDS URL audit (merged) — {today} — {len(lines_out)} rows"
            f" — {counts[BUCKET_BRIEF]} {BUCKET_BRIEF}"
            f" — {counts[BUCKET_SEARCH]} {BUCKET_SEARCH}"
            f" — {counts[BUCKET_NOT_WORKING]} {BUCKET_NOT_WORKING}\n"
        )
        f.write(f"# Merged retry updates from {len(updates)} re-checked rows\n")
        for line in lines_out:
            f.write(line + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument(
        "--url-mode",
        choices=("search", "brief"),
        default=DEFAULT_URL_MODE,
        help="search=page 12 (prefill); brief=page 18 direct report (default)",
    )
    parser.add_argument(
        "--user-agent",
        choices=("default", "browser"),
        default="default",
        help="HTTP User-Agent: default=app UA; browser=Chrome-like UA (may reduce 403 blocks)",
    )
    parser.add_argument(
        "--no-403-backoff",
        action="store_true",
        help="Disable adaptive global backoff when 403 rate spikes (on by default)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only-active", action="store_true")
    parser.add_argument("--skip-liveness", action="store_true")
    parser.add_argument(
        "--no-jitter",
        action="store_true",
        help="Disable 50–200ms random delay before each request (on by default)",
    )
    parser.add_argument(
        "--jitter-min-ms",
        type=int,
        default=DEFAULT_JITTER_MS[0],
        help="Minimum jitter (ms) before each request (default: 50)",
    )
    parser.add_argument(
        "--jitter-max-ms",
        type=int,
        default=DEFAULT_JITTER_MS[1],
        help="Maximum jitter (ms) before each request (default: 200)",
    )
    parser.add_argument(
        "--no-retry",
        action="store_true",
        help="Disable single retry on transient 503/504/timeout",
    )
    parser.add_argument(
        "--retry-failures-from",
        type=Path,
        metavar="AUDIT_JSONL",
        help=f"Re-check only rows with bucket={BUCKET_NOT_WORKING} from a prior audit export",
    )
    parser.add_argument(
        "--merge-into",
        type=Path,
        metavar="AUDIT_JSONL",
        help="With --retry-failures-from: write full merged audit to this path",
    )
    args = parser.parse_args()

    today = date.today().isoformat()
    if args.retry_failures_from:
        all_rows = _load_retry_rows(args.retry_failures_from)
        out_path = args.out or ROOT / f"data/logs/faa_aids_url_audit_retry_{today}.jsonl"
    else:
        all_rows = _load_jsonl(args.input)
        out_path = args.out or Path(str(DEFAULT_OUT_TEMPLATE).replace("{date}", today))

    os.environ.setdefault(
        "DATABASE_URL",
        f"sqlite:///{ROOT / 'data/aircraft_safety_v3.db'}",
    )

    from app import create_app
    from app.ingestion.url_builders.faa_aids_viability import probe_asias_liveness
    from app.models import IncidentSource

    app = create_app()
    use_jitter = not args.no_jitter
    jitter_ms = (args.jitter_min_ms, args.jitter_max_ms)
    if jitter_ms[0] < 0 or jitter_ms[1] < 0 or jitter_ms[1] < jitter_ms[0]:
        raise SystemExit("--jitter-min-ms/--jitter-max-ms must be non-negative and min<=max")
    check_fn = _make_check_fn(
        timeout=args.timeout,
        use_jitter=use_jitter,
        jitter_ms=jitter_ms,
        retry_once=not args.no_retry,
        url_mode=args.url_mode,
        user_agent_mode=args.user_agent,
    )

    print("=" * 60)
    print(f"FAA AIDS URL Audit — {today}")
    print(f"Input:       {args.retry_failures_from or args.input}")
    print(f"Output:      {out_path}")
    print(f"URL mode:    {args.url_mode}")
    print(f"User-Agent:  {args.user_agent}")
    print(f"Concurrency: {args.concurrency}")
    print(f"Timeout:     {args.timeout}s")
    print(f"Jitter:      {use_jitter} ({jitter_ms[0]}–{jitter_ms[1]} ms)")
    print(f"Retry:       {not args.no_retry}")
    print(f"Dry run:     {args.dry_run}")
    print("=" * 60)

    print("\n[1/4] ASIAS liveness probe...")
    if args.skip_liveness:
        print("      --skip-liveness set. Skipping probe.")
    else:
        alive = probe_asias_liveness(timeout=args.timeout)
        if not alive:
            print("ERROR: ASIAS homepage not HTTP 2xx. Aborting.")
            return 2
        print("      ASIAS is reachable. Proceeding.")

    print("[2/4] Loading rows...")
    print(f"      {len(all_rows):,} rows to check.")

    if args.only_active and not args.retry_failures_from:
        with app.app_context():
            active_ids = {
                r.source_record_id
                for r in IncidentSource.query.filter_by(
                    source_name="FAA_AIDS", is_active=True
                ).with_entities(IncidentSource.source_record_id)
            }
        all_rows = [r for r in all_rows if r.get("source_record_id") in active_ids]
        print(f"      Filtered to {len(all_rows):,} active rows.")

    total = len(all_rows)
    results: List[Dict[str, Any]] = []
    errors = 0
    reason_counts: Dict[str, int] = {}
    bucket_counts = {BUCKET_BRIEF: 0, BUCKET_SEARCH: 0, BUCKET_NOT_WORKING: 0}

    print(f"[3/4] Checking {total:,} URLs...\n")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.time()
    window = deque(maxlen=200)
    backoff_seconds = 0.0

    with out_path.open("w", encoding="utf-8") as out_f:
        out_f.write(
            f"# FAA AIDS URL audit — {today} — {total} rows — url_mode={args.url_mode}\n"
        )
        out_f.write(
            f"# buckets: {BUCKET_BRIEF} | {BUCKET_SEARCH} | {BUCKET_NOT_WORKING}\n"
        )
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = {pool.submit(check_fn, row): row for row in all_rows}
            done = 0
            for future in as_completed(futures):
                done += 1
                try:
                    result = future.result()
                except Exception as exc:
                    errors += 1
                    orig = futures[future]
                    result = {
                        "source_record_id": orig.get("source_record_id"),
                        "faa_aids_url": _resolve_audit_url(orig, args.url_mode),
                        "url_mode": args.url_mode,
                        "imported_incident_id": orig.get("imported_incident_id"),
                        "imported_aircraft_id": orig.get("imported_aircraft_id"),
                        "make_model": orig.get("make_model"),
                        "date": orig.get("date"),
                        "operator": orig.get("operator"),
                        "http_status": None,
                        "link_viable": False,
                        "product_viable": False,
                        "link_reason": "fetch_exception",
                        "bucket": BUCKET_NOT_WORKING,
                        "checked_at": datetime.utcnow().isoformat() + "Z",
                        "_error": str(exc),
                    }

                results.append(result)
                out_f.write(json.dumps(result, ensure_ascii=False) + "\n")

                bucket = result.get("bucket", BUCKET_NOT_WORKING)
                if bucket in bucket_counts:
                    bucket_counts[bucket] += 1
                if not result.get("link_viable"):
                    r = result.get("link_reason") or "unknown"
                    reason_counts[r] = reason_counts.get(r, 0) + 1

                # Adaptive global backoff if we appear to be getting WAF-blocked (403 storm).
                if not args.no_403_backoff:
                    is_403 = result.get("http_status") == 403
                    window.append(is_403)
                    if len(window) == window.maxlen:
                        rate = sum(1 for x in window if x) / len(window)
                        if rate >= 0.60:
                            backoff_seconds = 2.0 if backoff_seconds == 0.0 else min(30.0, backoff_seconds * 1.5)
                            print(f"\n  Backoff: high 403 rate in last {len(window)} ({rate:.0%}); sleeping {backoff_seconds:.1f}s\n")
                            time.sleep(backoff_seconds)
                        elif rate < 0.20 and backoff_seconds > 0.0:
                            backoff_seconds = max(0.0, backoff_seconds - 2.0)

                if total <= 100 or done % max(1, total // 10) == 0 or done == total:
                    elapsed = time.time() - start_time
                    eta = (elapsed / done) * (total - done) if done < total else 0
                    print(
                        f"  {done:>5}/{total}  brief={bucket_counts[BUCKET_BRIEF]}"
                        f"  search={bucket_counts[BUCKET_SEARCH]}"
                        f"  not_working={bucket_counts[BUCKET_NOT_WORKING]}"
                        f"  elapsed={elapsed:.1f}s  eta={eta:.1f}s"
                    )

    elapsed_total = time.time() - start_time
    print(f"\n  Done in {elapsed_total:.1f}s")
    print(
        f"\n[4/4] Buckets: {BUCKET_BRIEF}={bucket_counts[BUCKET_BRIEF]}"
        f"  {BUCKET_SEARCH}={bucket_counts[BUCKET_SEARCH]}"
        f"  {BUCKET_NOT_WORKING}={bucket_counts[BUCKET_NOT_WORKING]}"
        f"  errors={errors}"
    )
    if reason_counts:
        for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
            print(f"    {reason:<30} {count:>6}")

    if args.retry_failures_from and args.merge_into:
        merged = args.merge_into
        if merged.resolve() == args.retry_failures_from.resolve():
            stem = args.retry_failures_from.stem
            merged = args.retry_failures_from.with_name(f"{stem}_merged.jsonl")
        _merge_audit_rows(args.retry_failures_from, results, merged)
        print(f"\n  Merged audit: {merged}")

    product_ok = bucket_counts[BUCKET_BRIEF]
    summary = {
        "audit_date": today,
        "input": str(args.retry_failures_from or args.input),
        "output": str(out_path),
        "url_mode": args.url_mode,
        "user_agent": args.user_agent,
        "backoff_on_403": (not args.no_403_backoff),
        "total_checked": total,
        "bucket_counts": bucket_counts,
        "product_viable_count": product_ok,
        "fetch_errors": errors,
        "reason_counts": reason_counts,
        "dry_run": args.dry_run,
        "concurrency": args.concurrency,
        "timeout": args.timeout,
        "jitter": use_jitter,
        "jitter_ms": list(jitter_ms),
        "retry_once": not args.no_retry,
        "elapsed_seconds": round(elapsed_total, 1),
    }

    if not args.dry_run:
        print("\n  Writing DB changes...")
        db_counts = _apply_db_changes(results, app, args.url_mode)
        summary["db_changes"] = db_counts
        print(f"    is_active True→False:  {db_counts['true_to_false']:,}")
        print(f"    is_active False→True:  {db_counts['false_to_true']:,}")
    else:
        print("\n  --dry-run: DB not updated.")

    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n  Summary: {args.summary_out}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
